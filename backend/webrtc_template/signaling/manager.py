from webrtc_template.signaling.room import Room


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def get_or_create(self, room_id: str, mode: str) -> Room:
        if room_id not in self._rooms:
            self._rooms[room_id] = Room(room_id, mode)
        return self._rooms[room_id]

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def cleanup_empty(self, room_id: str) -> None:
        room = self._rooms.get(room_id)
        if room and room.size == 0:
            del self._rooms[room_id]

    def room_count(self) -> int:
        return len(self._rooms)

    async def shutdown(self) -> None:
        for room in list(self._rooms.values()):
            await room.close_all()


manager = RoomManager()
