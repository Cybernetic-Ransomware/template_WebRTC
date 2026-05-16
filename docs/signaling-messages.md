# Signaling Messages — Design Decisions

`backend/webrtc_template/signaling/messages.py`

This document traces the design of the WebSocket message layer from a naive first draft to the production-ready version. Each section captures one decision point: the problem, the choice, and the trade-off.

---

## The starting point

A naïve implementation uses plain dataclasses with a `match/case` dispatcher:

```python
@dataclass
class OfferMessage:
    type: str = "offer"
    sdp: str = ""
    to: str | None = None

def parse_message(data: dict) -> Any:
    match data["type"]:
        case "offer": return OfferMessage(sdp=data["sdp"], to=data.get("to"))
        ...
```

This works. Every decision below asks: *what breaks when this runs in production?*

---

## Decision 1 — `type` as `ClassVar`, not an instance field

**Problem:** `type` identifies the class, not an individual instance. Keeping it as an instance field lets callers write `OfferMessage(type="join")` — an object that is logically contradictory to its own type.

**Decision:** `type: ClassVar[Literal["offer"]] = "offer"`

`@dataclass` omits `ClassVar` fields from `__init__`, `__repr__`, and `__eq__`. The field exists on the class, not on instances.

**Trade-off:** `self.type` still works via Python's attribute lookup chain (instance → class). No API change for readers; writers are blocked at construction time.

---

## Decision 2 — `msgspec.Struct` instead of dataclasses

**Problem:** `@dataclass` does not validate field types at runtime. `OfferMessage(sdp=123)` creates a structurally invalid object and `__post_init__` with `if not self.sdp` misses it — `123` is truthy.

**Decision:** Replace all dataclasses with `msgspec.Struct`.

msgspec validates types at decode/convert time at the C level. `str` fields reject `int` values. Required fields (no default) raise `ValidationError` when absent. The entire `from_dict` / `__post_init__` machinery disappears.

```python
# Before: 6 lines of boilerplate per class
def __post_init__(self) -> None:
    if not isinstance(self.sdp, str) or not self.sdp:
        raise ValueError(...)

# After: the type annotation is the validation
class OfferMessage(msgspec.Struct, ...):
    sdp: NonEmptyStr  # enforced by msgspec at decode time
```

**Trade-off:** `msgspec` becomes a hard dependency. In exchange, you get ~10–50× faster serialization vs Pydantic and runtime safety at the network boundary.

---

## Decision 3 — `NonEmptyStr` via `Annotated`

**Problem:** `str` allows empty strings. `room: str` would accept `{"room": ""}` silently.

**Decision:**
```python
NonEmptyStr = Annotated[str, msgspec.Meta(min_length=1)]
```

Constraints live in the type system, not in imperative checks. The annotation is the documentation.

**Trade-off:** `NonEmptyStr` is not a real type — it is an annotation alias. IDE auto-complete shows `str`, not `NonEmptyStr`. Acceptable for a boundary type.

---

## Decision 4 — Tagged union dispatch

**Problem:** A `_PARSERS: dict[str, Callable]` registry (or `match/case`) must be maintained alongside the class definitions — two places for one fact.

**Decision:** `tag_field="type"` on each Struct + `WSRMessage: TypeAlias = A | B | C`

```python
class OfferMessage(msgspec.Struct, tag="offer", tag_field="type", ...):
    ...

msg = msgspec.convert(data, WSRMessage)  # dispatches by "type" field automatically
```

msgspec reads the `"type"` field and routes to the correct Struct internally. The registry is gone.

**Trade-off:** The dispatch mechanism is now implicit (inside msgspec), not explicit (visible in Python code). This is the right trade-off for a stable, well-tested library.

---

## Decision 5 — `frozen=True` and `forbid_unknown_fields=True`

**Problem:** Mutable message objects can be silently modified after parsing. Unknown fields in the input pass through undetected.

**Decision:**
- `frozen=True`: structs are immutable after construction — prevents handler code from accidentally mutating network data.
- `forbid_unknown_fields=True`: any extra key in the JSON raises `ValidationError` immediately.

**Exception:** `IceCandidateInit` does **not** use `forbid_unknown_fields`. The WebRTC spec evolves and browsers may send new fields before the server is updated. Rejecting them would silently break ICE negotiation on future browser versions.

---

## Decision 6 — `WSR_DECODER` / `WSR_ENCODER` singletons

**Problem:** `msgspec.json.decode(raw, type=WSRMessage)` re-compiles the type schema on every call.

**Decision:**
```python
WSR_DECODER: msgspec.json.Decoder[WSRMessage] = msgspec.json.Decoder(WSRMessage)
WSR_ENCODER: msgspec.json.Encoder = msgspec.json.Encoder()
```

The schema is compiled once at module import. Each `.decode()` call reuses the compiled path. At ICE candidate volume (5–20 messages/s per peer, many peers), this is measurable.

**Usage in server:**
```python
# instead of json.loads() + msgspec.convert():
msg = WSR_DECODER.decode(ws_raw_bytes)
```

---

## Decision 7 — No `parse_message` wrapper

**Problem:** A wrapper that only re-raises `msgspec.ValidationError` as `ValueError` degrades the error message without adding abstraction value.

**Decision:** Callers use `WSR_DECODER.decode()` or `msgspec.convert(data, WSRMessage)` directly and catch `msgspec.ValidationError`.

`msgspec.ValidationError` already includes the field path (`$.sdp`, `$.candidate.sdpMLineIndex`) — more useful than a generic `ValueError("invalid message")`.

---

## Decision 8 — `candidate: str` allows empty string (intentionally)

The ICE `candidate` field inside `IceCandidateInit` is typed as `str`, not `NonEmptyStr`. An empty string is a valid WebRTC signal meaning "end of candidates for this generation."

```json
{ "candidate": "", "sdpMid": "0" }
```

This looks like a bug. It is not.

**Spec reference:** https://www.w3.org/TR/webrtc/#dom-rtcicecandidateinit-candidate

---

## Decision 9 — `WSRMessage` not `Message`

`Message` collides with broker messages, domain events, actor messages, and command objects in larger systems. IDE auto-complete becomes ambiguous after the first year.

`WSRMessage` (WebSocket Relay/Room/Realtime) is scoped to this subsystem and does not collide.

---

## Final shape

```
IceCandidateInit   msgspec.Struct  — typed ICE candidate payload (lenient)
JoinMessage        msgspec.Struct  — room join request
LeaveMessage       msgspec.Struct  — disconnect signal (marker type)
OfferMessage       msgspec.Struct + _RoutingMixin
AnswerMessage      msgspec.Struct + _RoutingMixin
IceCandidateMessage msgspec.Struct + _RoutingMixin

WSRMessage         TypeAlias — union of all five message types
WSR_DECODER        singleton — compiled JSON → WSRMessage deserializer
WSR_ENCODER        singleton — WSRMessage → JSON serializer
```
