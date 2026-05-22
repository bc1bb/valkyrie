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
7. `networking/03-authentication.md` — OAuth2 / CCP SSO login handshake.
8. `networking/04-backend-environments.md` — host topology (TQ/Chaos/Havoc).

## Catalogue

| Doc | Area | Status | Summary |
|-----|------|--------|---------|
| `methodology/clean-room.md` | method | draft | Clean-room rules, evidence tiers, what may enter the repo. |
| `engine/01-engine-identification.md` | engine | verified | UE 4.14.3, codename Vk, module list, third-party libs. |
| `binary/01-binary-overview.md` | binary | draft | PE layout, sections, build metadata, embedded toolchain. |
| `networking/00-architecture.md` | net | draft | Three planes: REST backend, WebSocket replication, Steam/Oculus platform. |
| `networking/01-rest-backend.md` | net | draft | VkRestUtils resource clients = backend REST API surface. |
| `networking/02-websocket-netdriver.md` | net | draft | UE4 HTML5Networking WebSocketNetDriver over libwebsockets. |
| `networking/03-authentication.md` | net | draft | OAuth2 via CCP SSO; steam_ticket/oculus/refresh grants; Bearer token, scopes. |
| `networking/04-backend-environments.md` | net | draft | TQ (prod) + Chaos/Havoc (test) host topology; SSO + VGS API hosts. |

## Evidence base so far

- ASCII string table of the shipping client (`analysis/raw/`, git-ignored).
- 13,222 embedded source-path strings (build-agent debug paths) → module map.
- PE section table via `objdump`.

## Resolved

- ✅ Backend hostnames: SSO `login.eveonline.com`, API `vgs-tq.eveonline.com`
  (+ Chaos/Havoc test envs). See `networking/04-backend-environments.md`.
- ✅ Auth flow: OAuth2, custom `steam_ticket` / Oculus `password` /
  `refresh_token` grants → Bearer token. See `networking/03-authentication.md`.

## Open questions (tracked, not yet answered)

- Exact REST paths, HTTP verbs, JSON schemas per `Vk*Resource`.
- OAuth `client_id`/`client_secret` and whether token endpoint needs Basic auth.
- Token format (JWT vs opaque) and how downstream services validate it.
- How the active environment (TQ/Chaos/Havoc) is selected at runtime.
- WebSocket handshake subprotocol and message framing for replication.
- Matchmaking/battle-server allocation handshake (Plane 1 → Plane 2 seam).
- TLS cert pinning behaviour (affects DNS-redirect feasibility).
