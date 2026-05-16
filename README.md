# WebRTC Template

![Python](https://img.shields.io/badge/python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=for-the-badge&logo=aiohttp&logoColor=white)
![aiortc](https://img.shields.io/badge/aiortc-FF6B35?style=for-the-badge&logo=webrtc&logoColor=white)
![Vite](https://img.shields.io/badge/vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/docker-0db7ed?style=for-the-badge&logo=docker&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-FCC21B?style=for-the-badge&logo=ruff&logoColor=black)
![UV](https://img.shields.io/badge/UV-DE5FE9?style=for-the-badge&logo=python&logoColor=white)

A reusable WebRTC signaling + media template demonstrating three connection topologies, from simplest to most complex.
Designed as a learning artifact — each module introduces exactly one new problem.

## Topologies

### P2P 1:1 — direct connection
```
[Peer A] <──── WebSocket signaling ────> [Peer B]
         <──── WebRTC direct media ─────>
```
Pure passthrough: the server relays offer/answer/ICE but never touches media.

### Mesh — full N×N grid
```
        [Peer A]
       /         \
[Peer B] ─────── [Peer C]
```
Each peer maintains one `RTCPeerConnection` per every other peer.
The server routes directed signaling messages; media flows peer-to-peer.

### SFU — server-forwarded unit
```
[Peer A] ──┐
[Peer B] ──┼──> [aiortc SFU] ──> all subscribers
[Peer C] ──┘
```
Each participant connects once to the server. The server (aiortc) subscribes to
each participant's tracks and forwards them to all others — one `RTCPeerConnection`
per client, regardless of room size.

## Features

- WebSocket signaling server (aiohttp) with room management and mode dispatch
- Three topology modes selectable via query parameter: `?mode=p2p|mesh|sfu`
- msgspec-validated message types — protocol violations close the connection with RFC 6455 code 1007
- SFU mode implemented with aiortc — Python as a real WebRTC peer
- HTTPS in development via Caddy `tls internal` (no manual cert setup)
- TURN relay via coturn — works across restrictive NATs and firewalls
- Vanilla JS frontend with Vite, one page per topology mode

## Requirements

- Python ≥ 3.14
- [uv](https://github.com/astral-sh/uv) package manager
- Docker Desktop / Docker + Compose (for full stack)
- A modern browser with WebRTC support

## Environment Variables

Copy `docker/.env.template` to `docker/.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `HOST` | no | Bind address (default: `0.0.0.0`) |
| `PORT` | no | Signaling server port (default: `8080`) |
| `STUN_URL` | no | STUN server URL (default: Google STUN) |
| `TURN_URL` | no | TURN server URL (default: `turn:coturn:3478`) |
| `TURN_USERNAME` | yes | TURN server username |
| `TURN_PASSWORD` | yes | TURN server password |

## Getting Started

### Docker (full stack)

```bash
cp docker/.env.template docker/.env        # fill in TURN credentials
docker compose up --build
```

Open `https://localhost` in your browser. Accept the self-signed certificate (Caddy `tls internal`).

| Mode | URL |
|---|---|
| P2P 1:1 | `https://localhost/#/p2p?room=demo` |
| Mesh | `https://localhost/#/mesh?room=demo` |
| SFU | `https://localhost/#/sfu?room=demo` |

### Backend only (dev)

```bash
uv sync
cp .env.example .env
uv run python -m webrtc_template
```

The signaling server starts on `http://localhost:8080`.
WebSocket endpoint: `ws://localhost:8080/ws?room=<id>&mode=<p2p|mesh|sfu>&peer_id=<id>`
ICE servers endpoint: `GET http://localhost:8080/ice-servers`

## Linting

```bash
uv run ruff format .
uv run ruff check .
```

## Learning Guide

The codebase is structured so each layer can be read independently:

| File | What to learn |
|---|---|
| `signaling/messages.py` | msgspec tagged unions, `NonEmptyStr`, frozen structs, decoder singletons |
| `signaling/room.py` | async broadcast, peer registry pattern |
| `signaling/server.py` | aiohttp WS lifecycle, RFC 6455 close codes, dispatch table |
| `modes/p2p.py` | P2P constraints, passthrough relay |
| `modes/mesh.py` | directed signaling, N×N connection management |
| `modes/sfu.py` | aiortc as a WebRTC peer, track forwarding, `MediaRelay` |
| `frontend/lib/peer.js` | `RTCPeerConnection` setup, trickle ICE |
| `frontend/modes/p2p.js` | perfect negotiation pattern (polite/impolite peer) |
| `frontend/modes/mesh.js` | managing a `Map<peerId, RTCPeerConnection>` |
| `frontend/modes/sfu.js` | single connection, multiple remote tracks |

Architecture decisions are documented in `docs/`.

## Useful Links

- [aiohttp WebSocket docs](https://docs.aiohttp.org/en/stable/web_reference.html#websockets)
- [aiortc docs](https://aiortc.readthedocs.io/)
- [WebRTC spec — RTCIceCandidateInit](https://www.w3.org/TR/webrtc/#dom-rtcicecandidateinit)
- [RFC 6455 — WebSocket close codes](https://www.rfc-editor.org/rfc/rfc6455#section-7.4.1)
- [Perfect negotiation pattern — MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation)
- [coturn docs](https://github.com/coturn/coturn/wiki)
- [Caddy `tls internal`](https://caddyserver.com/docs/caddyfile/directives/tls)
- [uv docs](https://docs.astral.sh/uv/)