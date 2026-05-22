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
9. `networking/05-battle-server-launch.md` — dedicated server launch contract.
10. `networking/06-matchmaking-beacons.md` — reservation beacons + connection mgmt.
11. `networking/07-online-subsystem-and-telemetry.md` — custom OSS + Epic telemetry.
12. `networking/08-gameplay-replication.md` — in-match RPC surface.
13. `networking/09-session-lifecycle-and-roadmap.md` — capstone lifecycle + roadmap.
14. `networking/10-static-data-distribution.md` — static-data manifest + voice.

## Catalogue

| Doc | Area | Status | Summary |
|-----|------|--------|---------|
| `methodology/clean-room.md` | method | draft | Clean-room rules, evidence tiers, what may enter the repo. |
| `methodology/traffic-capture-plan.md` | method | draft | How to get E4 wire evidence via DNS redirect + TLS-terminating loopback stub. |
| `engine/01-engine-identification.md` | engine | verified | UE 4.14.3, codename Vk, module list, third-party libs. |
| `engine/02-module-glossary.md` | engine | draft | Navigational map: modules, networking classes, VkGame gameplay clusters. |
| `engine/03-input-peripherals.md` | engine | draft | Input surface: DirectInput HOTAS, TrackIR head tracking, Tobii eye tracking (all client-local). |
| `engine/04-game-modes.md` | engine | draft | Game-mode taxonomy (EVkGameModeType/SubLevels/CustomMatchType); PvP-vs-PvE backend-need split. |
| `binary/01-binary-overview.md` | binary | draft | PE layout, sections, build metadata, embedded toolchain. |
| `networking/00-architecture.md` | net | draft | Three planes: REST backend, WebSocket replication, Steam/Oculus platform. |
| `networking/01-rest-backend.md` | net | draft | VkRestUtils resource clients = backend REST API surface. |
| `networking/02-websocket-netdriver.md` | net | draft | UE4 HTML5Networking WebSocketNetDriver over libwebsockets. |
| `networking/03-authentication.md` | net | draft | OAuth2 via CCP SSO; steam_ticket/oculus/refresh grants; Bearer token, scopes. |
| `networking/04-backend-environments.md` | net | draft | TQ (prod) + Chaos/Havoc (test) host topology; SSO + VGS API hosts. |
| `networking/05-battle-server-launch.md` | net | draft | Dedicated server launch args: -BATTLEID/-BATTLESERVER_URI/-JWT/teams/AI. |
| `networking/06-matchmaking-beacons.md` | net | draft | UE4 PartyBeacon reservation flow; reconnect; heartbeat/watchdog; timeouts. |
| `networking/07-online-subsystem-and-telemetry.md` | net | draft | Custom OnlineSubsystemVk (identity/session/oculus/steam); Epic DataRouter telemetry. |
| `networking/08-gameplay-replication.md` | net | draft | In-match RPC surface: movement/combat/spectator/match-flow/vehicle/voice. |
| `networking/09-session-lifecycle-and-roadmap.md` | net | draft | Capstone: eConnectionState machine, failure modes, prioritized re-impl roadmap. |
| `networking/10-static-data-distribution.md` | net | draft | GetFileList manifest (files[] allow-list) + content download; VOIP note. |
| `networking/schemas/vgs-rest.md` | net | draft | Consolidated VGS REST reference: base/versioning, endpoints, object fields, MVP backend. |

## Evidence base so far

- ASCII string table of the shipping client (`analysis/raw/`, git-ignored).
- 13,222 embedded source-path strings (build-agent debug paths) → module map.
- PE section table via `objdump`.

## Resolved

- ✅ Backend hostnames: SSO `login.eveonline.com`, API `vgs-tq.eveonline.com`
  (+ Chaos/Havoc test envs). See `networking/04-backend-environments.md`.
- ✅ Auth flow: OAuth2, custom `steam_ticket` / Oculus `password` /
  `refresh_token` grants → Bearer token. See `networking/03-authentication.md`.
- ✅ Token format: **JWT** (per `-JWT=` server arg). Signing key still unknown.
- ✅ Battle-server launch contract: per-match dedicated server via `-BATTLEID`,
  `-BATTLESERVER_URI`, `-JWT`, team/AI/rank args. See `networking/05-*`.
- ✅ Client launch overrides: `-SSOTOKEN=`, `-offline`/`-online` confirmed.

- ✅ REST path namespace: `{version}/valkyrie/<resource>/…` (v1.0 & v2.0 mixed),
  e.g. `v2.0/valkyrie/accounts/`, `v2.0/valkyrie/stores/7/offers/`. See `01-*`.
- ✅ JSON model: snake_case fields, **HATEOAS** (`*_uri` link fields drive
  navigation); recovered id/config/stats/squad field sets. See `01-*`.

## Open questions (tracked, not yet answered)

- Remaining exact REST paths (pilots/battles/sessions/battleserver), HTTP verbs,
  and JSON schemas per `Vk*Resource` (some built by concat — need gdb capture).
- OAuth `client_id`/`client_secret` and whether token endpoint needs Basic auth.
- JWT signing algorithm + validation key (server-side trust anchor).
- How the active environment (TQ/Chaos/Havoc) is selected at runtime
  (NOT `-tq/-chaos/-havoc`; those were host-string substrings, debunked).
- WebSocket handshake subprotocol and message framing for replication.
- `-BATTLESERVER_URI=` exact scheme/host/port/path.
- TLS cert pinning behaviour (affects DNS-redirect feasibility).
