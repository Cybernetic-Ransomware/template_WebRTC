from webrtc_template.signaling.messages import WSRMessage
from webrtc_template.signaling.room import Room


async def handle(room: Room, peer_id: str, message: WSRMessage) -> None:
    raise NotImplementedError