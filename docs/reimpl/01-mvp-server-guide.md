---
doc: reimpl-mvp
title: MVP Server Build Guide
summary: Concrete step-by-step walkthrough to stand up a minimal private backend that boots the client through login to a match — synthesizing the documented endpoints/flows. Implementation guidance, not original code.
keywords: [reimplementation, mvp, server, guide, build, dns, tls, sso, stub, walkthrough, preservation, how-to]
status: draft
updated: 2026-05-22
evidence: [E2, E3, E4, E5]
---

# MVP Server Build Guide

A concrete path to make the shipped client reach a match against a private
backend. This synthesizes the analysis docs (cited inline) into build steps. It
is **guidance** (what to implement and why), written from the documented
interface — no original game code is reproduced. Build in a clean room from
these specs (`methodology/clean-room.md`).

> Scope: restore **boot → login → reach a PvP match**. Cosmetics/store/loot/
> leaderboards can return stubs initially (`09-*` priorities).

## 0. Topology to recreate

```
client ──HTTPS──> SSO (token)           [login.eveonline.com/oauth/token]
client ──HTTPS──> VGS API (REST)        [{tenant}.valkyrieapi.com/...]  (NXDOMAIN now)
client ──WS─────> battle server (UE4 WebSocketNetDriver)  (allocated by VGS)
server ──HTTPS──> VGS API (battles lifecycle, JWT-auth)
```
Hosts: `valkyrieapi.com` is **NXDOMAIN** (clean redirect target); SSO host
`login.eveonline.com` is alive but Valkyrie origin is gone (`12-*`).

## 1. Redirect the client to your server (`04-*`, `12-*`)

- Point `login.eveonline.com`, `vgs-tq.eveonline.com`, and the
  `{tenant}.valkyrieapi.com` host(s) at your server (OS hosts file or a local
  resolver). Confirm the tenant subdomain the client uses via capture
  (`methodology/traffic-capture-plan.md`).
- Serve **TLS** the client trusts (OpenSSL/libcurl validates): install a local
  CA, or determine whether the client pins (open question). Plain redirect +
  trusted cert avoids binary patching.

## 2. SSO token endpoint (`03-*`, `12-*`, `13-*`)

`POST /oauth/token`, `application/x-www-form-urlencoded`, **HTTP Basic** client
auth required (return 401 without it — confirmed E4). Accept grants:
- `grant_type=steam_ticket&steam_ticket=…&intellectual_property=VALKYRIE&scope=…`
- `grant_type=password&oculus_user_id=…&oculus_nonce=…&oculus_callsign=…&…`
- `grant_type=refresh_token&refresh_token=…`

Validate (or stub) the platform ticket; mint a **JWT** access token + refresh
token carrying scopes `valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1
vgs.marketAccess.v1`. Respond JSON `{access_token, refresh_token, token_type:
"bearer", expires_in}`. You control the JWT key (client doesn't verify it; the
dedicated server you run will accept your key — `05-*`).

## 3. VGS REST: bootstrap to a pilot (`01-*`, `14-*`)

All under `{version}/valkyrie/…`, `Authorization: Bearer <JWT>`,
`application/json`, snake_case, **HATEOAS** (return `*_uri` links the client
follows). Return 401 on expired token to trigger refresh (`01-*`); tolerate
missing fields (client uses `FVkJsonObject`, `13-*`).

**Wrap every response in the envelope** (`13-*`):
`{ "uri": <self>, "verb": <method>, "message": "", "content": { <object> } }`
— the client reads `content`. Concrete object shapes for `content` are recovered
in `13-*` / catalogued in `schemas/vgs-rest.md`; the P0 ones:

```jsonc
// accounts -> content:
{ "pilot_uri": "<...>/pilots?pilot_id=1", "npe_completed": true,
  "eula_signed": true }
// pilot (GET pilots?pilot_id=) -> content: (subset; see 13-*)
{ "pilot_id": 1, "callsign": "Test", "gender": "...", "has_set_gender": true,
  "reputation_rank": 0, "league_score": 0, "balance": { ... },
  "hero_ships": [], "implants": [], "applied_pilot_cosmetics": [],
  "friends_uri": "...", "settings_uri": "...", /* ...the *_uri graph... */ }
// staticdata GetFileList -> content:
{ "files": [ { "filename": "...", "uri": "https://...", "checksum": "..." } ],
  "branch_name": "LIVE", "build_number": "..." }
```

Minimum chain:
1. **Client/signup** (`clients`/`signup`): accept the client fingerprint
   (`build_version`, `os_platform`, `hmd_type`, …); return OK + any bootstrap
   config. Gate version with care (`OutdatedClient`, `09-*`) — report compatible.
2. **Accounts** (`v2.0/valkyrie/accounts/`): return the account with a
   `pilot_uri` (and `npe_completed:true` to skip first-time flow, or false to
   exercise it), `eula_signed:true`.
3. **Pilot** (`%spilots?pilot_id=…`): return a pilot object with the core fields
   + the HATEOAS `*_uri` graph (`14-*`). Stub cosmetics/implants/upgrades as
   empty arrays; give a wallet (`balance`, Silver/Gold) and ranks.
4. **Static data** (`staticdata` → `GetFileList`): return `{ "files":[ {name,
   url, hash, version}… ] }` and serve each file (`10-*`). **P0** — the client
   likely blocks load without it.

## 4. Matchmaking → battle server (`05-*`, `06-*`, `14-*`)

1. **Session request** (`sessionrequests` / `sessions?version=…&session_type=…`):
   on a queue/playlist request, create/allocate a session.
2. **Battle server**: launch the shipped binary as a dedicated server
   (`-server -nullrhi -BATTLEID=… -BATTLESERVER_URI=ws://host:port -JWT=… -REGION
   -PUBLICIP -gamemode -teams/AI`, `05-*`). It registers locally
   (`localhost:10080`, `14-*`) and reports lifecycle (`LobbyStarted`/
   `MatchStarted`/… via `battles`, `05-*`).
3. Return the **server WS address + join token** to the client (the Plane1→Plane2
   seam). Client opens the UE4 `WebSocketNetDriver` connection (`02-*`).
4. **Reservation beacon**: run a UE4 `PartyBeaconHost` to accept the client's
   reservation (`ReservationAccepted`, `06-*`) before the full game connect.

## 5. In-match (`02-*`, `08-*`)

Engine-stock UE 4.14 over WebSockets handles replication/RPCs. Your dedicated
server (same binary/engine) provides this for free; implement only server-
authoritative gameplay rules as needed. Honor the network version
(UE 4.14.3 / CL 3195953, `engine/01-*`) so the handshake isn't rejected.

## 6. Keep it alive (`06-*`, `14-*`)

- Backend **heartbeat** (`heartbeat_uri`/`next_heartbeat_seconds`) — accept pings.
- Accept battle lifecycle reports; free slots on `PlayerDisconnected`, finalize
  on `MatchEnded` (post results/rewards, `11-*`).
- The **local Watchdog** (127.0.0.1:8080, `14-*`) is client-local — no backend
  work; just don't break it.

## 7. Stub the rest (P2/P3)

Virtual goods/store, loot capsules, cosmetics, challenges, leaderboards,
notifications → return empty/minimal valid JSON. Sinkhole Epic DataRouter +
client-event telemetry (`07-*`); accept client-events with optional throttle
hints (`14-*`).

## Hardest validations (do early)

- **JWT acceptance** end-to-end: client → VGS and dedicated-server → VGS must
  both accept your token (`05-*`, `09-*`).
- **Static data** completeness (step 3.4) — gating.
- **TLS trust** / cert pinning behavior (`04-*`).
- Exact **tenant** subdomain + any remaining response nesting — confirm by
  capture (`methodology/traffic-capture-plan.md`).

## Confidence

Steps are derived from interface evidence (E2/E3) + live E4 on the SSO. Exact
JSON nesting per resource is the main thing to firm up via capture before a
build will work end-to-end. This guide is the **map**; the territory needs one
capture pass per resource to finalize.
