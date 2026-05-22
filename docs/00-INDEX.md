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

## Start here

**`STATUS.md`** — preservation status & confidence map (what's known at what
evidence tier, what's blocking, prioritized next actions). Best entry point for
a re-implementer; this INDEX is the full catalogue.

## Reading order

1. `methodology/clean-room.md` — rules everyone must follow.
2. `engine/01-engine-identification.md` — what engine/version, why it matters.
3. `binary/01-binary-overview.md` — the client executable at a glance.
4. `networking/00-architecture.md` — the big picture of how the game talks online.
5. `networking/01-rest-backend.md` — the REST backend resource surface.
6. `networking/02-websocket-netdriver.md` — realtime gameplay replication transport.
7. `networking/03-authentication.md` — OAuth2 / CCP SSO login handshake.
   (For the actionable build path, jump to `reimpl/01-mvp-server-guide.md`.)
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
| `engine/05-local-persistence.md` | engine | draft | Local save/settings: VkPersistentData (_pers.data), VkPersistentStats, settings UObjects; cache vs backend authority. |
| `engine/06-rendering-audio-vr.md` | engine | draft | Middleware: Oculus/SteamVR HMD, forward+InstancedStereo+MultiRes+volumetric rendering, Wwise+Oculus HRTF audio. |
| `engine/07-ai-bots.md` | engine | draft | Server-run bot AI (VkAI* cluster): behaviour states, navigation, abilities/ultimates; configured by match params. |
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
| `networking/11-progression-economy-model.md` | net | draft | Backend player-state: Silver/Gold currency, rewards, ranks, loadout/cosmetic/implant/hero-ship data. |
| `networking/12-live-endpoint-observations.md` | net | **verified** | E4: DNS + live probes — SSO/token endpoint alive behind Cloudflare, 401 confirms Basic client auth; Chaos DNS alive, Havoc gone. |
| `networking/13-disassembly-recovered.md` | net | draft | E3: disasm method + recovered fields (match-config, rank-up rewards), FVkJsonObject, PUT verb; client_id not needed for re-impl. |
| `networking/14-vgs-api-surface.md` | net | draft | **Full recovered API surface**: multi-tenant URLs (valkyrieapi.com), all resources/paths, pilot HATEOAS graph, stats/cosmetic/mode taxonomies, client fingerprint, local watchdog + battleserver reg. |
| `networking/15-anticheat-integrity.md` | net | draft | No EAC/BattlEye; only Steam VAC (passive) + engine NetChecksum/SecurityViolation + server-authoritative play. Private server not blocked by AC. |
| `networking/schemas/vgs-rest.md` | net | draft | Consolidated VGS REST reference: base/versioning, endpoints, object fields, MVP backend. |
| `reimpl/01-mvp-server-guide.md` | reimpl | draft | **Actionable build walkthrough**: redirect→SSO→pilot→staticdata→matchmaking→battle server→in-match→keepalive; what to stub. |
| `gameplay/00-overview.md` | gameplay | living | Gameplay systems map (VkGame ~1562 classes) — entry point for whole-game RE. |
| `gameplay/01-player-ship-control.md` | gameplay | draft | Player/ship control (controller/pawn/vehicle/movement/cockpit/launch) + full scoring-event taxonomy. |
| `gameplay/02-combat.md` | gameplay | draft | Combat: weapon taxonomy/firing, projectiles vs lock-on missiles, turrets, multi-channel damage model, hit/critical points, shields, explosions; firing RPCs. |
| `gameplay/03-abilities.md` | gameplay | draft | Abilities/ultimates/buffs: VkAbility_*/VkUltimate_* rosters, activation/cooldown lifecycle, per-ability state machines, loadout slots. |
| `gameplay/04-mode-mechanics.md` | gameplay | draft | Mode mechanics: capture points, carrier-assault state machine, relics, clone-vat respawn, teams, MatchSettings→game_mode_settings mapping. |
| `gameplay/05-vr-ui.md` | gameplay | draft | VR UI/HUD: diegetic cockpit HUD (radar/brackets/crosshair), head-selectable front-end framework, smart-pings (networked), AVkUIGameState bridge. |
| `gameplay/06-pilot-loadout.md` | gameplay | draft | Client loadout/customization: EVkInventorySlot, hero-ship/cosmetic/upgrade/implant model, local persistence; consumes backend (networking/11). |
| `gameplay/07-brackets.md` | gameplay | draft | NEGATIVE finding: no tournament-bracket system; "brackets" = HUD reticles. Competitive = leagues/leaderboards. |
| `gameplay/08-framework.md` | gameplay | draft | Framework glue: Vk GameInstance/GameMode/GameState triad (incl. GameLift mode), VkCore, FVkJsonObject, client static-data binding. |
| `gameplay/09-spectator.md` | gameplay | draft | Spectator system: pawn/HUD/camera, server-authoritative view-target flow, showfloor/kiosk; KillCam=clone-vat screen; no replay system. |
| `gameplay/10-world-spawning.md` | gameplay | draft | World/level sublevel streaming (VkMapLoader), player-start/launch-tube spawning, spawn-point groups, respawn-map, world bounds. |
| `gameplay/11-effects.md` | gameplay | draft | Effects driver (EffectManager command-list + subsystems) & animation drivers — code layer, not VFX assets. |
| `gameplay/12-tacticalmap-comms.md` | gameplay | draft | Tactical map (clone-vat screen) + networked quick-chat (comm wheel/VO) + call-ins (EMP/OverShield/RepairBots). |
| `gameplay/13-frontend-flow.md` | gameplay | draft | Front-end menu flow: 3 scene managers (Login/HUB/BattleCarousel), screen catalogue, navigation mapped to connection states + backend. |
| `reference/enums.md` | reference | living | Enum/type lookup index (~116 EVk* enums) — name→purpose→doc; find which doc covers a given enum/state-machine. |
| `reference/rpcs.md` | reference | living | RPC inventory (~170 Server/~120 Client/~10 Multicast) by theme; the replication call-contract + the _Validate (server-validation) pattern. |

## Phase status

**Static-analysis phase (tier E1/E2): essentially complete for networking.**
The shipped client's strings/structure have been mined across the whole
backend/online surface (auth, environments, REST paths+query+JSON model, launch
contract, beacons, replication, OSS, telemetry, lifecycle, static-data,
progression/economy, HTTP lifecycle, modes, social). Broad re-sweeps now return
only minor overlaps. **Next phase = E4 (live capture / gdb dynamic analysis)**
to resolve the remaining wire-level unknowns (below). See
`methodology/traffic-capture-plan.md`.

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

- ✅ **(E4, live)** SSO `login.eveonline.com/oauth/token` is **alive**, POST-only,
  and **requires HTTP Basic client auth** (401 unauthenticated). Prod hosts sit
  behind Cloudflare; Chaos test DNS still resolves; Havoc gone. See `12-*`.

## Open questions (tracked, not yet answered)

- ✅ **Most REST paths + per-resource field sets recovered** from the backend
  FString cluster — see `14-vgs-api-surface.md` (resources, path templates,
  pilot HATEOAS graph, stats/cosmetic/mode vocab). Also surfaced: **multi-tenant
  URL scheme** (`{tenant}.valkyrieapi.com`), a **local Watchdog process**
  (127.0.0.1:8080), and **battle-server local registration** (localhost:10080).
- ✅ **Full JSON object model recovered** (E3, `13-*`): common envelope +
  pilot, session, rewards, squad, leaderboard, challenge, auth-token,
  client-event, battle-server registration, static-data manifest, store
  offer/purchase. Field sets + grouping sufficient to scaffold a re-impl.
- Remaining: exact value types / deep nesting per object — best finalized by one
  captured response each (E4); all hosts dead except the eveonline.com edge.
- ~~OAuth client_id/secret values~~ → **reclassified nice-to-have** (`13-*`): a
  re-implemented SSO defines its own client-credential policy, so CCP's original
  values aren't needed to restore play. Basic-auth requirement is confirmed (E4).
- JWT signing algorithm + validation key (server-side trust anchor).
- How the active environment (TQ/Chaos/Havoc) is selected at runtime
  (NOT `-tq/-chaos/-havoc`; those were host-string substrings, debunked).
- WebSocket handshake subprotocol and message framing for replication.
- `-BATTLESERVER_URI=` exact scheme/host/port/path.
- TLS cert pinning behaviour (affects DNS-redirect feasibility).
