# CLAUDE.md — WebRTC Template Project

## Project Overview

Reusable WebRTC signaling + media template demonstrating three connection topologies in order of complexity:
1. **P2P 1:1** — direct peer-to-peer, pure passthrough signaling
2. **Mesh** — full N×N mesh, directed passthrough signaling
3. **SFU** — server-mediated forwarding via aiortc (one RTCPeerConnection per participant to server)

This is a **learning project** — each module introduces exactly one new problem. The code is a teaching artifact as much as a working template.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, aiohttp (WS signaling), aiortc (SFU peer), msgspec (serialization) |
| Frontend | Vanilla JS + Vite (3 pages, one per mode) |
| Infra | Docker Compose: signaling backend + coturn (TURN) + Caddy (HTTPS via `tls internal`) |

## Package Manager

This project uses **uv**. Never use `pip` directly.

```bash
uv sync                  # install all dependencies
uv add <package>         # add production dependency
uv add --dev <package>   # add dev dependency
uv run <command>         # run command in project environment
uv run python -m webrtc_template  # start the server
```

## Repo Layout

```
backend/webrtc_template/
    config.py              # loads .env (PORT, TURN_*, ICE_SERVERS)
    __main__.py            # python -m webrtc_template entry point
    signaling/
        server.py          # aiohttp app + WS handler (setup / message-loop / teardown)
        messages.py        # msgspec Structs for all WS message types
        room.py            # Room: peer registry, broadcast, relay
        manager.py         # RoomManager: room registry + cleanup
    modes/
        __init__.py        # MODE_HANDLERS dispatch table
        p2p.py             # P2P handler (max 2 peers, passthrough)
        mesh.py            # Mesh handler (directed passthrough N×N)
        sfu.py             # SFU handler (aiortc peer per participant)

frontend/src/
    lib/signaling.js       # SignalingClient WS wrapper
    lib/peer.js            # RTCPeerConnection helper
    lib/media.js           # getUserMedia helpers
    lib/ui.js              # video grid renderer
    modes/{p2p,mesh,sfu}.js

docker/
    docker-compose.yml
    .env.template          # copy to .env and fill in credentials
    caddy/Caddyfile        # tls internal, reverse proxy
    coturn/turnserver.conf

docs/                      # Architecture Decision Records
```

## Code Conventions

### messages.py
- All WS message types are `msgspec.Struct` with `frozen=True`, `forbid_unknown_fields=True`, `tag_field="type"`
- `IceCandidateInit` is the exception: no `forbid_unknown_fields` — WebRTC spec evolves, browsers may add fields
- `NonEmptyStr = Annotated[str, msgspec.Meta(min_length=1)]` — constraints in the type system, not `__post_init__`
- `_RoutingMixin` holds `to_dict(from_peer)` shared by Offer/Answer/IceCandidate
- `WSR_DECODER` / `WSR_ENCODER` are module-level singletons — schema compiled once at import
- `IceCandidateInit.candidate: str` (not `NonEmptyStr`) — empty string is a valid end-of-candidates signal per WebRTC spec

### server.py
- `ws_handler` is orchestration only — lifecycle split into `_setup_peer`, `_message_loop`, `_teardown_peer`
- `ALLOWED_MODES = frozenset(MODE_HANDLERS)` — single source of truth, derived from the dispatch table
- `ValidationError` from msgspec → `ws.close(code=WSCloseCode.INVALID_TEXT)` (RFC 6455 code 1007) + break
- `try/finally` in `ws_handler` guarantees peer cleanup regardless of how the loop exits

### General
- No comments unless the WHY is non-obvious
- No `parse_message()` wrapper — callers use `WSR_DECODER.decode()` directly
- Auth0 authentication is a planned TODO (`ice_servers_handler` and `ws_handler`)

## Code Style

- All code, comments, and documentation must be written in **English**. No Polish in the codebase.
- Do not add decorative section separator comments such as `# ── SectionName ───────`.
- No `Co-Authored-By` trailers in commit messages.

## Git Workflow

The user runs all git commands — never execute `git add`, `git commit`, `git push` or similar without explicit instruction.

## Linting

Configured in `pyproject.toml`, run via ruff:

```bash
uv run ruff format .     # format
uv run ruff check .      # lint
```

## Architecture Decision Records

ADRs live in `docs/`. Check before making structural decisions.

| ADR | Status | Topic |
|-----|--------|-------|
| signaling-messages.md | Accepted | 9 design decisions for the WS message layer (msgspec, tagged union, singletons, NonEmptyStr, _RoutingMixin) |

New decisions should be documented as a markdown file in `docs/`.

## Learning Approach

This project uses **Learn by Doing**: at key design-decision points, the user implements 2–10 line code pieces before seeing the solution. These are marked `TODO(human)` in the code. Do not remove or implement `TODO(human)` markers without user contribution.

Remaining contribution points:
1. `modes/p2p.py` — logic for rejecting a 3rd peer (kick? error? queue?)
2. `frontend/modes/p2p.js` — `track` event handler (insert remote video into UI)
3. `frontend/modes/mesh.js` — `cleanupPeer(peerId)` teardown order
4. `backend/modes/sfu.py` — `attach_subscriber_tracks` renegotiation timing