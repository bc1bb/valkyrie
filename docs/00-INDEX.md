---
doc: index
title: Documentation Index
summary: Master index of all clean-room docs with per-area status and reading order.
keywords: [index, toc, status, overview]
status: living
updated: 2026-05-22
---

# Documentation Index

Token-saver convention: every doc starts with a YAML header. Read the header's
`summary` + `keywords` first; only open the body if relevant. `status` ∈
{stub, draft, verified, living}.

## Reading order

1. `methodology/clean-room.md` — rules everyone must follow.
2. `engine/01-engine-identification.md` — what engine/version, why it matters.
3. `binary/01-binary-overview.md` — the client executable at a glance.
4. `networking/00-architecture.md` — the big picture of how the game talks online.
5. `networking/01-rest-backend.md` — the REST backend resource surface.
6. `networking/02-websocket-netdriver.md` — realtime gameplay replication transport.

## Catalogue

| Doc | Area | Status | Summary |
|-----|------|--------|---------|
| `methodology/clean-room.md` | method | draft | Clean-room rules, evidence tiers, what may enter the repo. |
| `engine/01-engine-identification.md` | engine | verified | UE 4.14.3, codename Vk, module list, third-party libs. |
| `binary/01-binary-overview.md` | binary | draft | PE layout, sections, build metadata, embedded toolchain. |
| `networking/00-architecture.md` | net | draft | Three planes: REST backend, WebSocket replication, Steam/Oculus platform. |
| `networking/01-rest-backend.md` | net | draft | VkRestUtils resource clients = backend REST API surface. |
| `networking/02-websocket-netdriver.md` | net | draft | UE4 HTML5Networking WebSocketNetDriver over libwebsockets. |

## Evidence base so far

- ASCII string table of the shipping client (`analysis/raw/`, git-ignored).
- 13,222 embedded source-path strings (build-agent debug paths) → module map.
- PE section table via `objdump`.

## Open questions (tracked, not yet answered)

- Backend hostnames/endpoints (likely in config inside the 30 GB pak, or built
  from format strings at runtime). Not yet located.
- Exact REST paths, HTTP verbs, JSON schemas per resource.
- Auth flow: CCP SSO vs Oculus vs Steam ticket exchange ordering.
- WebSocket handshake subprotocol and message framing for replication.
- Matchmaking/battle-server allocation handshake.
