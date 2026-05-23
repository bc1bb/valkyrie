---
doc: status
title: Preservation Status & Confidence Map
summary: Bird's-eye view for a re-implementer — what's known at what evidence tier (E4 verified → E5 inferred), what's blocking vs done, and the prioritized next actions. Snapshot of project completeness.
keywords: [status, confidence, evidence, coverage, summary, handoff, priorities, blocking, verified, capture]
status: living
updated: 2026-05-23
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
| Static-data manifest | ✅ confirmed | E3 | `files[{filename,uri,checksum}]+branch/build`. `10-*` |
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

## Blocking-vs-done for restoring multiplayer

**Done (enough to build):** host topology, auth contract, REST surface + object
model + verbs, matchmaking/beacon flow, battle-server launch+lifecycle, realtime
transport + handshake shape, anti-cheat posture (none blocking). The
`reimpl/01-mvp-server-guide.md` is buildable from current docs.

**Needs one live capture each (E4) to finalize — not blocking design, only
exact bytes:**
- Per-resource JSON **value types / deep nesting** (names+grouping known, E3).
- `NMT_Login` join auth = a **capability token** (`CapToken`/`AuthToken`,
  signed/encrypted — `02-*`); exact wire layout/signing still needs capture.
- Whether the active **tenant** subdomain is fixed or derived.

**Resolved since (E3, via disassembly):** `client_id`=`valkyrieClient` (public,
empty secret); WebSocket subprotocol (empty/default); JWT opaque-to-client. A
function-level disassembler is now available (`analysis/scripts/disasm_func.py`,
Capstone) — the remaining E3 items above are tractable with it, not only E4.

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
