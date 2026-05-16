"""
WebSocket message types for the signaling server.

ADR:
- msgspec.Struct instead of dataclasses: runtime type validation at network boundary —
  str fields reject int values, required fields enforced, no manual from_dict needed.
- WSRMessage union + msgspec.convert(data, WSRMessage): callers dispatch directly — no
  wrapper function needed. msgspec.ValidationError is descriptive enough on its own.
  "Message" avoided as a name — too generic, collides with broker/domain/actor message
  types in larger systems.
- NonEmptyStr (Annotated[str, msgspec.Meta(min_length=1)]): non-empty constraint
  in the type system, not imperative __post_init__ checks.
- frozen=True: message objects are immutable after parsing — prevents accidental mutation
  of network data in handlers.
- forbid_unknown_fields=True on message Structs (not IceCandidateInit): rejects unexpected
  fields from clients — enforces protocol contract. IceCandidateInit is lenient because
  the WebRTC spec evolves and browsers may add new fields before the server is updated.
- to_dict uses msgspec.to_builtins(self): serializes via msgspec instead of manual dict
  construction — single source of truth for field names.
"""
import msgspec
from typing import Annotated, Literal, TypeAlias

NonEmptyStr = Annotated[str, msgspec.Meta(min_length=1)]


class IceCandidateInit(msgspec.Struct, frozen=True):
    # empty string is a valid end-of-candidates signal, not a bug
    # https://www.w3.org/TR/webrtc/#dom-rtcicecandidateinit-candidate
    candidate: str
    sdpMid: str | None = None
    sdpMLineIndex: int | None = None
    usernameFragment: str | None = None


class _RoutingMixin:
    to: str | None

    def to_dict(self, from_peer: str) -> dict:
        d: dict = msgspec.to_builtins(self)
        d["from"] = from_peer
        if self.to is None:
            d.pop("to", None)
        return d


class JoinMessage(msgspec.Struct, tag="join", tag_field="type", frozen=True, forbid_unknown_fields=True):
    room: NonEmptyStr
    peer_id: NonEmptyStr
    mode: Literal["p2p", "mesh", "sfu"] = "p2p"


class LeaveMessage(msgspec.Struct, tag="leave", tag_field="type", frozen=True, forbid_unknown_fields=True):
    pass


class OfferMessage(_RoutingMixin, msgspec.Struct, tag="offer", tag_field="type", frozen=True, forbid_unknown_fields=True):
    sdp: NonEmptyStr
    to: str | None = None


class AnswerMessage(_RoutingMixin, msgspec.Struct, tag="answer", tag_field="type", frozen=True, forbid_unknown_fields=True):
    sdp: NonEmptyStr
    to: str | None = None


class IceCandidateMessage(_RoutingMixin, msgspec.Struct, tag="ice-candidate", tag_field="type", frozen=True, forbid_unknown_fields=True):
    candidate: IceCandidateInit
    to: str | None = None


WSRMessage: TypeAlias = (
    JoinMessage
    | LeaveMessage
    | OfferMessage
    | AnswerMessage
    | IceCandidateMessage
)

WSR_DECODER: msgspec.json.Decoder[WSRMessage] = msgspec.json.Decoder(WSRMessage)
WSR_ENCODER: msgspec.json.Encoder = msgspec.json.Encoder()
