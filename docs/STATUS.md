---
doc: status
title: Preservation Status & Confidence Map
summary: Bird's-eye view for a re-implementer — what's known at what evidence tier (E4 verified → E5 inferred), what's blocking vs done, and the prioritized next actions. Snapshot of project completeness.
keywords: [status, confidence, evidence, coverage, summary, handoff, priorities, blocking, verified, capture]
status: living
updated: 2026-05-22
---

# Preservation Status & Confidence Map

A re-implementer's orientation: how complete each area is and how trustworthy.
Evidence tiers (see `methodology/clean-room.md`): **E1** build metadata · **E2**
embedded strings/symbols · **E3** static disassembly · **E4** live observation ·
**E5** inference from public UE4. Higher = more certain about *behaviour*.

## Confidence by area

| Area | Coverage | Top tier | Notes / gap |
|------|----------|----------|-------------|
| Engine identity (UE 4.14.3, codename Vk) | ✅ complete | E1 | Verified from `Build.version` + paths. |
| Backend hosts / DNS topology | ✅ complete | **E4** | SSO alive (Cloudflare); `valkyrieapi.com` NXDOMAIN; Chaos DNS up. `12-*` |
| Auth — endpoint, POST-only, Basic-auth req'd | ✅ verified | **E4** | Live 401 confirms Basic client auth. `03-*`,`12-*` |
| Auth — grants, scopes, JWT | ✅ strong | E2/E3 | Grant bodies + token resp recovered. client_id values N/A for re-impl. |
| REST resources + path templates | ✅ strong | E2/E3 | `{tenant}.valkyrieapi.com`, `{ver}/valkyrie/...`. `14-*` |
| REST JSON object model (12 objects) | ✅ strong | **E3** | Field sets + grouping recovered by disasm. `13-*` |
| HTTP verbs per resource | ◑ approximate | E3 | GET/POST/PUT/DELETE mapped (windowed). `14-*` |
| Response envelope `{uri,verb,message,content}` | ✅ strong | E3 | Recurs across parsers. `13-*` |
| Matchmaking (PartyBeacon) + reservation | ✅ strong | E2/E5 | Engine-stock beacon + Vk request types. `06-*` |
| Battle-server launch + lifecycle + reg | ✅ strong | E2/E3 | Args, `FVkBattlesResource`, localhost reg. `05-*`,`14-*` |
| Realtime transport (WebSocket NetDriver) | ✅ strong | E1/E2 | HTML5Networking + libwebsockets. `02-*` |
| Control-channel handshake (NMT_*) | ◑ engine-stock | E2/E5 | Sequence from UE4; subprotocol value needs capture. `02-*` |
| In-match RPC surface | ✅ strong | E2 | Categorized; server-authoritative. `08-*` |
| Progression / economy / cosmetics | ✅ strong | E2/E3 | Silver/Gold, rewards object, taxonomies. `11-*`,`13-*` |
| Telemetry / watchdog | ✅ complete | E2 | Epic DataRouter (skip) + local watchdog. `07-*`,`14-*` |
| Anti-cheat / integrity | ✅ complete | E1/E2 | No EAC/BattlEye; VAC + server authority. `15-*` |
| Static-data manifest | ✅ confirmed | E3 | `files[{filename,uri,checksum}]+branch/build`. `10-*` |
| Local persistence / settings | ✅ complete | E2 | Cache, not authoritative. `engine/05-*` |

## Blocking-vs-done for restoring multiplayer

**Done (enough to build):** host topology, auth contract, REST surface + object
model + verbs, matchmaking/beacon flow, battle-server launch+lifecycle, realtime
transport + handshake shape, anti-cheat posture (none blocking). The
`reimpl/01-mvp-server-guide.md` is buildable from current docs.

**Needs one live capture each (E4) to finalize — not blocking design, only
exact bytes:**
- Per-resource JSON **value types / deep nesting** (names+grouping known, E3).
- `NMT_Login` exact **join-token placement** + WebSocket **subprotocol** value.
- Whether the active **tenant** subdomain is fixed or derived.

**Not needed:** CCP's `client_id`/`client_secret` (re-impl SSO sets own policy).

## Recommended next actions (priority)

1. **Capture one session** (`methodology/traffic-capture-plan.md`): redirect +
   TLS stub OR gdb on `Vk*HttpRequest`/`SetHeader` — converts the E3 schemas to
   E4 and nails value types + the join token. Highest leverage.
2. Build the **P0 backend** (SSO + accounts + pilot + static-data) per
   `reimpl/01-*` and iterate against the client (it's the spec oracle).
3. Stand up the **battle server + PartyBeacon host**; confirm the WS handshake.
4. Fill meta (store/loot/leaderboards/challenges) from the recovered objects.

## What this project is NOT (scope)

Asset/resource RE is out of scope (per project brief). Gameplay-logic balance
(ship stats, ability tuning) is documented only at the data-shape level. The
focus is the **networking/backend protocol** needed to restore online play.
