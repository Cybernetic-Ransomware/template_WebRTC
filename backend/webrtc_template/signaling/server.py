"""
WebSocket signaling server.

ADR:
- ws_handler split into _setup_peer / _message_loop / _teardown_peer: each function owns
  exactly one responsibility; try/finally stays in ws_handler because it owns the peer's
  room membership, not the loop or teardown functions.
- MODE_HANDLERS used directly for mode validation: ALLOWED_MODES frozenset was a redundant
  alias — dict lookup is O(1) and sorted(MODE_HANDLERS) produces the same error message.
- send_bytes + msgspec.json.encode: avoids dict→bytes→str→bytes round-trip. Clients receive
  BINARY frames and must decode ArrayBuffer to JSON (not plain string).
- Fixed window rate limiter (_MSG_RATE_LIMIT=50): allows up to 2× burst at window boundary.
  Acceptable for signaling — ICE negotiation bursts are short-lived and self-limiting.
  Token bucket would eliminate burst but adds complexity not justified here.
- Non-TEXT frames break the loop: BINARY closes with UNSUPPORTED_DATA (1003) — explicit
  protocol violation; CLOSE/ERROR break silently — aiohttp handles the handshake. Using
  continue would let clients hold the loop alive with binary spam indefinitely.
- JSON gate before WSR_DECODER.decode: lstrip().startswith("{") rejects non-object payloads
  in O(1) before msgspec allocates memory for a full parse. Tolerates leading whitespace.
- WSCloseCode choices: INVALID_TEXT (1007) for protocol violations, POLICY_VIOLATION (1008)
  for rate limit and duplicate peer_id, GOING_AWAY (1001) for server shutdown — each signals
  a distinct cause to the client reconnect logic.
- Handler exceptions caught in _message_loop: bare propagation disconnects the peer silently —
  teardown still runs (try/finally in ws_handler) but the root cause is lost. Caught with
  logger.exception (includes traceback) + close(INTERNAL_ERROR / 1011). BLE001 broad-except
  is intentional: mode handlers (especially SFU/aiortc) can throw unpredictably.
- TOCTOU fix via Room._lock + try_add_peer: ws.prepare() yields to event loop, so the
  check-then-add must be atomic. ws.prepare() runs first (before lock) because it is I/O;
  duplicate is closed with POLICY_VIOLATION (1008) after the handshake instead of HTTP 409,
  which is the only valid rejection point once prepare() has completed.
- heartbeat=30 + max_msg_size=64KB on WebSocketResponse: layer-1 flood protection;
  heartbeat detects dead peers, max_msg_size rejects oversized payloads before decode.
- on_shutdown hook calls manager.shutdown(): closes all WebSocket connections with
  GOING_AWAY before the process exits, preventing reconnect storms on SIGTERM.
- CORS origins from config.cors_origins: "*" in dev, explicit whitelist in prod.
  allow_credentials=True requires a non-wildcard origin to function in browsers.
"""
import logging

import aiohttp_cors
import msgspec
from aiohttp import WSCloseCode, WSMsgType, web
from time import monotonic

from webrtc_template.config import config
from webrtc_template.modes import MODE_HANDLERS
from webrtc_template.signaling.manager import manager
from webrtc_template.signaling.messages import WSR_DECODER
from webrtc_template.signaling.room import Room

# Fixed window rate limit — allows up to 2× burst at window boundary (50 msg at t=0.99s + 50 at t=1.01s).
# Acceptable for signaling: ICE negotiation bursts are short-lived and self-limiting.
_MSG_RATE_LIMIT = 50


logger = logging.getLogger(__name__)


async def ice_servers_handler(request: web.Request) -> web.Response:
    # TODO: add Auth0 authentication
    return web.json_response({"iceServers": config.ice_servers})


async def _setup_peer(
    ws: web.WebSocketResponse,
    room: Room,
    peer_id: str,
    existing_peers: list[str],
) -> None:
    await ws.send_bytes(msgspec.json.encode({
        "type": "room-info",
        "room": room.room_id,
        "mode": room.mode,
        "peers": existing_peers,
        "your_id": peer_id,
    }))
    await room.broadcast({"type": "peer-joined", "peer_id": peer_id}, exclude_id=peer_id)


async def _message_loop(ws: web.WebSocketResponse, room: Room, peer_id: str) -> None:
    handler = MODE_HANDLERS[room.mode]
    window_start = monotonic()
    message_counter = 0

    async for msg in ws:
        now = monotonic()
        if now - window_start > 1:
            window_start = now
            message_counter = 0

        message_counter += 1
        if message_counter > _MSG_RATE_LIMIT:
            logger.warning("peer=%s rate limit exceeded (%d msg/s)", peer_id, _MSG_RATE_LIMIT)
            await ws.close(code=WSCloseCode.POLICY_VIOLATION)
            break

        if msg.type == WSMsgType.BINARY:
            logger.warning("peer=%s sent binary frame on text-only protocol", peer_id)
            await ws.close(code=WSCloseCode.UNSUPPORTED_DATA)
            break
        if msg.type != WSMsgType.TEXT:
            break

        # TODO: queue bound — asyncio.Semaphore or receive_timeout to cap buffered messages
        if not msg.data.lstrip().startswith("{"):
            logger.warning("peer=%s invalid frame (not JSON object): %.40r", peer_id, msg.data)
            await ws.close(code=WSCloseCode.INVALID_TEXT)
            break
        try:
            message = WSR_DECODER.decode(msg.data)
        except msgspec.ValidationError as exc:
            logger.warning("peer=%s protocol violation: %s", peer_id, exc)
            await ws.close(code=WSCloseCode.INVALID_TEXT)
            break
        try:
            await handler(room, peer_id, message)
        except Exception:
            logger.exception("peer=%s handler error", peer_id)
            await ws.close(code=WSCloseCode.INTERNAL_ERROR)
            break


async def _teardown_peer(room: Room, room_id: str, peer_id: str) -> None:
    room.remove_peer(peer_id)
    try:
        await room.broadcast({"type": "peer-left", "peer_id": peer_id})
    except Exception:
        logger.exception("peer=%s broadcast peer-left failed", peer_id)
    finally:
        manager.cleanup_empty(room_id)


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    room_id = request.rel_url.query.get("room", "").strip()
    mode = request.rel_url.query.get("mode", "p2p").strip()
    peer_id = request.rel_url.query.get("peer_id", "").strip()

    if not room_id or not peer_id:
        raise web.HTTPBadRequest(reason="room and peer_id are required")
    if mode not in MODE_HANDLERS:
        raise web.HTTPBadRequest(reason=f"mode must be one of {sorted(MODE_HANDLERS)}")

    room = manager.get_or_create(room_id, mode)

    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=64 * 1024)
    await ws.prepare(request)

    existing_peers = await room.try_add_peer(peer_id, ws)
    if existing_peers is None:
        await ws.close(code=WSCloseCode.POLICY_VIOLATION)
        return ws

    await _setup_peer(ws, room, peer_id, existing_peers)
    try:
        await _message_loop(ws, room, peer_id)
    finally:
        await _teardown_peer(room, room_id, peer_id)

    return ws


async def _on_shutdown(app: web.Application) -> None:
    await manager.shutdown()


def create_app() -> web.Application:
    app = web.Application()
    app.on_shutdown.append(_on_shutdown)
    resource_options = aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
    origins = config.cors_origins
    cors_defaults = (
        {"*": resource_options}
        if origins == ["*"]
        else {origin: resource_options for origin in origins}
    )
    cors = aiohttp_cors.setup(app, defaults=cors_defaults)
    cors.add(app.router.add_get("/ice-servers", ice_servers_handler))
    app.router.add_get("/ws", ws_handler)
    return app
