---
doc: status
title: Preservation Status & Confidence Map
summary: Bird's-eye view for a re-implementer — what's known at what evidence tier (E4 verified → E5 inferred), what's blocking vs done, and the prioritized next actions. Snapshot of project completeness.
keywords: [status, confidence, evidence, coverage, summary, handoff, priorities, blocking, verified, capture]
status: living
updated: 2026-05-24
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
| Binary/runtime deps + import surface | ✅ complete | E1 | Manifest (exact middleware versions), full import table (WS2_32/WinINet/Vulkan/MediaFoundation/PhysX), version resource. `binary/01-*`,`02-*` |
| Platform SDK call surface (Oculus/Steam) | ✅ complete | E1 | Entitlement, identity→grant bridge, IAP, SteamGameServer (same-binary server). `07-*` |
| Backend hosts / DNS topology | ✅ complete | **E4** | SSO alive (Cloudflare); `valkyrieapi.com` NXDOMAIN; Chaos DNS up. `12-*` |
| Auth — endpoint, POST-only, Basic-auth req'd | ✅ verified | **E4** | Live 401 confirms Basic client auth. `03-*`,`12-*` |
| Auth — grants, scopes | ✅ strong | E2/E3 | Grant bodies + token resp recovered. |
| Auth — client_id | ✅ **recovered** | **E3** | `valkyrieClient`, empty secret (public client) — disasm. `03-*` |
| Auth — JWT internals | ✅ resolved | E3 | Opaque to client; backend-only; re-impl defines own. `03-*` |
| REST resources + path templates | ✅ strong | E2/E3 | `{tenant}.valkyrieapi.com`, `{ver}/valkyrie/...`. `14-*` |
| REST JSON object model (12 objects) | ✅ strong | **E3** | Field sets + grouping recovered by disasm. `13-*` |
| HTTP verbs per resource | ◑ approximate | E3 | GET/POST/PUT/DELETE mapped (windowed). `14-*` |
| Response envelope `{uri,verb,message,content}` | ✅ strong | E3 | Recurs across parsers. `13-*` |
| Matchmaking (PartyBeacon) + reservation | ✅ strong | E2/E5 | Engine-stock beacon + Vk request types. `06-*` |
| Battle-server launch + lifecycle + reg | ✅ strong | E2/E3 | Args, `FVkBattlesResource`, localhost reg. `05-*`,`14-*` |
| Realtime transport (WebSocket NetDriver) | ✅ strong | E1/E2 | HTML5Networking + libwebsockets. `02-*` |
| Control-channel handshake (NMT_*) | ✅ strong | E2/E5 | UE4 sequence; WS subprotocol resolved (empty/default). `02-*` |
| In-match RPC surface | ✅ strong | E2 | Categorized; server-authoritative. `08-*` |
| Progression / economy / cosmetics | ✅ strong | E2/E3 | Silver/Gold, rewards object, taxonomies. `11-*`,`13-*` |
| Telemetry / watchdog | ✅ complete | E2 | Epic DataRouter (skip) + local watchdog. `07-*`,`14-*` |
| Anti-cheat / integrity | ✅ complete | E1/E2 | No EAC/BattlEye; VAC + server authority. `15-*` |
| Static-data manifest + GetFileList completion | ✅ complete | **E4** | `files[{filename,uri,checksum}]+branch/build`; completion `0x14209b550` succeeds live, fires its delegate, files byte-identical to pak. **NOT the wall** (Session-3 "completion-notify gap" was a probe misread, retracted). `10-*`, `reimpl/04-*` |
| Login state machine + **menu reached** | ✅ **MENU REACHED** | **E4** | Client boots→logs in→**renders the interactive main menu** (2D). Lone blocker: secondary gate `GameInstance+0x19d0` (state-2 handler); forcing it cascades login→menu, stable. **Natural trigger is client/VR-platform-bound (OSS login-complete that never fires in 2D), NOT server-fixable** — see below. `reimpl/04-*` S4–S5, `reimpl/07-*` |
| Local persistence / settings | ✅ complete | E2 | Cache, not authoritative. `engine/05-*` |

### Gameplay / client architecture (whole-game RE)

| Area | Coverage | Top tier | Notes / gap |
|------|----------|----------|-------------|
| Player/ship control + scoring | ✅ strong | E1/E2 | Controller/pawn/vehicle/movement/cockpit; `VkPlayerScoreObjective_*`. `gameplay/01` |
| Combat / weapons / damage | ✅ strong | E1/E2 | Weapon taxonomy, multi-channel damage, hit/crit points, missile homing. `gameplay/02` |
| Abilities / ultimates / buffs | ✅ strong | E2 | Full rosters + per-ability state machines. `gameplay/03` |
| Game-mode mechanics | ✅ strong | E1/E2 | Capture pts, `EArmadaState`, clones, MatchSettings map. `gameplay/04` |
| VR UI / HUD | ✅ strong | E1/E2 | HSOG framework, radar/brackets, smart-ping. `gameplay/05` |
| Pilot / loadout / cosmetics (client) | ✅ strong | E2 | Slots, hero-ship/cosmetic/upgrade/implant model. `gameplay/06` |
| Tournament brackets | ✅ N/A | E2 | Confirmed absent (HUD reticles only). `gameplay/07` |
| Framework (GameMode/State/Instance, Core) | ✅ strong | E1/E2 | Vk triad incl. GameLift mode; FVkJsonObject. `gameplay/08` |
| Spectator / observer | ✅ strong | E2/E5 | View-target flow, showfloor; no replay. `gameplay/09` |
| World / levels / spawning | ✅ strong | E1/E2 | Sublevel streaming, launch-tube spawn, bounds. `gameplay/10` |
| Effects (driver) / animation | ◑ driver-only | E1/E2 | Command-list manager; assets out of scope. `gameplay/11` |
| Tactical map / comms (quick-chat, call-ins) | ✅ strong | E2 | Networked; tac-map=clone-vat screen. `gameplay/12` |
| Front-end / menu flow | ✅ strong | E1/E2 | 3 scene managers, screen catalogue, nav flow. `gameplay/13` |
| AI / bots | ✅ strong | E1/E2 | Behaviour FSM, navigation, ability roster. `engine/07` |
| Input peripherals / rendering-audio-VR | ✅ complete | E1/E2 | HOTAS/TrackIR/Tobii; Oculus/SteamVR, Wwise. `engine/03`,`06` |
| Enum/type index (116 enums) | ✅ index | E2 | Lookup map. `reference/enums.md` |

**Whole-client RE is comprehensive at the architecture/interface level.** What's
*not* covered (by design or tier): exact field offsets / replicated-property
layouts (need real disassembly w/o symbols), algorithm internals, and all
asset/content/balance in the `.pak` (out of scope).

## Live client bring-up (E4, 2026-05-23/24) — the MVP backend boots the client to its MENU

The clean-room MVP backend (`reimpl/mvp-server`) drives the **shipped client**
(native Windows, RTX 4070, no VR, 2D mode) live, redirected via hosts + a local CA,
**all the way to the interactive main menu** (Session 4, 2026-05-24). Prerequisite
unblock: the 2017 OpenSSL **SHA-NI crash** on modern CPUs, fixed with
`OPENSSL_ia32cap=:~0x20000000`. The client completes the **entire REST login
bootstrap** and, with one secondary gate satisfied, renders the menu:

```
client-event(startup) → /oauth/token (steam_ticket) → /auth → /clients (registered)
→ /pilots/1 → /pilot-lookup → vgs-tq accounts → GET /staticdata (GetFileList)
→ [static data completes] → store offers → new-player flow → MAIN MENU
```

Walls broken: `/clients` (non-empty `Location` header); `/staticdata` framing (bare
top-level `files`); the static-data catalog (recovered from the client's own pak,
md5-verified byte-identical, 43/43); and **the login wall itself**. The Session-3
"static-data completion never fires / listener NULL" diagnosis was a **probe misread
and is retracted** — static-data completes correctly. The genuine blocker is a single
**secondary gate byte `GameInstance+0x19d0`** checked by the state-2 ("DOWNLOADING
STATIC DATA") handler `0x1406ec6a0`. A safe Frida force of that byte cascades the whole
login forward (store/purchases/new-player) and the client **reaches the menu, stable
for minutes** (screenshot `mvp-server/logs/menu_reached.png`). **Current task:** set
`GameInstance+0x19d0` *naturally* — it's gated on the online/session state reaching
"ready" so the store/catalog subsystem attaches and ticks (`reimpl/07-*`). Full trace:
`reimpl/04-live-bringup-log.md` (Session 4).

## Blocking-vs-done for restoring multiplayer

**Done (enough to build):** host topology, auth contract, REST surface + object
model + verbs, matchmaking/beacon flow, battle-server launch+lifecycle, realtime
transport + handshake shape, anti-cheat posture (none blocking). The
`reimpl/01-mvp-server-guide.md` is buildable from current docs.

**Needs one live capture each (E4) to finalize — not blocking design, only
exact bytes:**
- Per-resource JSON **value types / deep nesting** (names+grouping known, E3).
- `NMT_Login` join auth: the backend token (JWT/session) carried in the connect
  login options (`02-*`); exact wire layout still needs capture. *(Corrected: the
  earlier "CapToken capability-token" reading was an OpenSSL SET-OID false
  positive — see `02-*`.)*
- ~~Whether the active **tenant** subdomain is fixed or derived.~~ **Resolved
  (E2):** config-driven — `-TENANT=` arg + `VkGame_TenantDomains` mapping, carried
  as `valkyrie.tenant` property (`04-*`). Capture only needed for the exact value.

**Resolved since (E3, via disassembly):** `client_id`=`valkyrieClient` (public,
empty secret); WebSocket subprotocol (empty/default); JWT opaque-to-client. A
function-level disassembler is now available (`analysis/scripts/disasm_func.py`,
Capstone) — the remaining E3 items above are tractable with it, not only E4.

## Recommended next actions (priority)

1. **(RESOLVED — not server-fixable.)** Reaching the menu without a client nudge
   was traced to a dead end: `GameInstance+0x19d0` is set only by the store-catalog
   subsystem callback, which is driven by an internal work-queue populated by the
   **OnlineSubsystem login-complete event** — reflection/VR-platform-bound, and it
   never fires in 2D/no-VR. No REST response triggers it (`reimpl/04-*` S5,
   `reimpl/07-*`). The realistic clean boot path is a documented runtime gate-patch
   (our own loader sets `+0x19d0` / NOPs the read at `0x1406ec6fa`) — **deferred by
   decision** (documented known-limitation, client left unmodified).
2. **Exercise the menu** (reachable via the runtime force; the client is the oracle):
   drive the front-end flows and capture exact request/response shapes for store
   offers, `hero_survival`, `sessionrequests`, friends/challenges — converting E3
   schemas to E4 from a live, menu-stable client.
3. Stand up the **battle server + PartyBeacon host**; confirm the WS handshake.
4. Fill meta (store/loot/leaderboards/challenges) from the recovered objects.

## What this project is NOT (scope)

Asset/resource RE is out of scope (per project brief). Gameplay-logic balance
(ship stats, ability tuning) is documented only at the data-shape level. The
focus is the **networking/backend protocol** needed to restore online play.
