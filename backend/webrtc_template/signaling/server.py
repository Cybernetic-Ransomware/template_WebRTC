import json
import logging

import aiohttp_cors
import msgspec
from aiohttp import WSCloseCode, WSMsgType, web

from webrtc_template.config import config
from webrtc_template.modes import MODE_HANDLERS
from webrtc_template.signaling.manager import manager
from webrtc_template.signaling.messages import WSR_DECODER
from webrtc_template.signaling.room import Room

ALLOWED_MODES: frozenset[str] = frozenset(MODE_HANDLERS)

logger = logging.getLogger(__name__)


async def ice_servers_handler(request: web.Request) -> web.Response:
    # TODO: add Auth0 authentication
    return web.json_response({"iceServers": config.ice_servers})


async def _setup_peer(
    ws: web.WebSocketResponse,
    room: Room,
    room_id: str,
    peer_id: str,
    mode: str,
) -> None:
    existing_peers = room.peer_ids
    room.add_peer(peer_id, ws)
    await ws.send_str(json.dumps({
        "type": "room-info",
        "room": room_id,
        "mode": mode,
        "peers": existing_peers,
        "your_id": peer_id,
    }))
    await room.broadcast({"type": "peer-joined", "peer_id": peer_id}, exclude_id=peer_id)


async def _message_loop(ws: web.WebSocketResponse, room: Room, peer_id: str) -> None:
    async for msg in ws:
        match msg.type:
            case WSMsgType.TEXT:
                try:
                    message = WSR_DECODER.decode(msg.data)
                except msgspec.ValidationError:
                    await ws.close(code=WSCloseCode.INVALID_TEXT)
                    break
                await MODE_HANDLERS[room.mode](room, peer_id, message)
            case WSMsgType.ERROR | WSMsgType.BINARY | WSMsgType.CLOSE:
                break


async def _teardown_peer(room: Room, room_id: str, peer_id: str) -> None:
    room.remove_peer(peer_id)
    await room.broadcast({"type": "peer-left", "peer_id": peer_id})
    manager.cleanup_empty(room_id)


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    room_id = request.rel_url.query.get("room", "").strip()
    mode = request.rel_url.query.get("mode", "p2p").strip()
    peer_id = request.rel_url.query.get("peer_id", "").strip()

    if not room_id or not peer_id:
        raise web.HTTPBadRequest(reason="room and peer_id are required")
    if mode not in ALLOWED_MODES:
        raise web.HTTPBadRequest(reason=f"mode must be one of {sorted(ALLOWED_MODES)}")

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    room = manager.get_or_create(room_id, mode)
    await _setup_peer(ws, room, room_id, peer_id, mode)
    try:
        await _message_loop(ws, room, peer_id)
    finally:
        await _teardown_peer(room, room_id, peer_id)

    return ws


def create_app() -> web.Application:
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    cors.add(app.router.add_get("/ice-servers", ice_servers_handler))
    app.router.add_get("/ws", ws_handler)
    return app
