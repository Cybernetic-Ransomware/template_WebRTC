import asyncio

import msgspec.json
from aiohttp import WSCloseCode
from aiohttp.web import WebSocketResponse


class Room:
    def __init__(self, room_id: str, mode: str) -> None:
        self.room_id = room_id
        self.mode = mode
        self._peers: dict[str, WebSocketResponse] = {}
        self._lock = asyncio.Lock()

    @property
    def peer_ids(self) -> list[str]:
        return list(self._peers.keys())

    @property
    def size(self) -> int:
        return len(self._peers)

    async def try_add_peer(self, peer_id: str, ws: WebSocketResponse) -> list[str] | None:
        """Atomically check+add. Returns snapshot of existing peers on success, None on collision."""
        async with self._lock:
            if peer_id in self._peers:
                return None
            existing = list(self._peers.keys())
            self._peers[peer_id] = ws
            return existing

    def remove_peer(self, peer_id: str) -> None:
        self._peers.pop(peer_id, None)

    def get_ws(self, peer_id: str) -> WebSocketResponse | None:
        return self._peers.get(peer_id)

    async def broadcast(self, message: dict, exclude_id: str | None = None) -> None:
        payload = msgspec.json.encode(message)
        for pid, ws in list(self._peers.items()):
            if pid != exclude_id and not ws.closed:
                await ws.send_bytes(payload)

    async def relay(self, to_peer_id: str, message: dict) -> None:
        ws = self._peers.get(to_peer_id)
        if ws and not ws.closed:
            await ws.send_bytes(msgspec.json.encode(message))

    async def close_all(self) -> None:
        for ws in list(self._peers.values()):
            if not ws.closed:
                await ws.close(code=WSCloseCode.GOING_AWAY)
