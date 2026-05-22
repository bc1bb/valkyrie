# EVE: Valkyrie – Warzone — Preservation & Documentation Project

> Clean-room technical documentation of the EVE: Valkyrie – Warzone client,
> aimed at understanding and (eventually) re-implementing the now-defunct
> online backend so the game remains playable after official server shutdown.

## What this repo IS

- **Documentation only.** Prose descriptions of how the game works technically:
  network architecture, backend protocol surface, engine layout, gameplay
  systems, file formats.
- **Goal: the whole client RE'd and clean-room documented** — networking first
  (now comprehensive), then the full gameplay/client architecture
  (`docs/gameplay/`). Asset/content RE (the 30 GB pak) stays out of scope.
- Produced under **clean-room principles** (see `docs/methodology/clean-room.md`).

## What this repo IS NOT

- It contains **no copyrighted game files**. The shipped game tree
  (`WindowsNoEditor/`) and all raw byte dumps are git-ignored. See `.gitignore`.
- We do **not** redistribute binaries, assets, or extracted strings.

## The subject

| Field            | Value                                                     |
|------------------|-----------------------------------------------------------|
| Title            | EVE: Valkyrie – Warzone                                   |
| Engine           | Unreal Engine **4.14.3** (CompatibleChangelist 3195953)  |
| Project codename | `Vk` (branch `LIVE`)                                      |
| Build date       | 2017-12-06 (shipping exe)                                 |
| Platform here    | Windows x64 (`WindowsNoEditor`), shipped via Steam        |
| Steam App ID     | `688480` (Steam buildid `2347437`)                        |
| Client binary    | `VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe` (~62 MB)|

## Documentation map

Start at **`docs/00-INDEX.md`** — every doc carries a token-saver YAML header
(`summary`, `keywords`, `status`) so an LLM can decide relevance before reading.

## Status

Networking documented **end-to-end at the interface level** from static
analysis of the shipped client (no live servers exist). Covered:

- **Auth** — OAuth2 / CCP SSO; `steam_ticket`/Oculus/`refresh_token` grants; JWT.
  **Verified live (E4):** `login.eveonline.com/oauth/token` still answers,
  POST-only, requires HTTP Basic client auth (401 unauthenticated).
- **Environments / DNS** — Tranquility (prod) + Chaos (test) DNS still resolve;
  the real backend domain `valkyrieapi.com` is **NXDOMAIN** (gone). Multi-tenant
  URLs `{tenant}.valkyrieapi.com`.
- **REST (VGS)** — full resource/path surface, query params, HTTP verbs, and the
  **complete JSON object model recovered via disassembly** (12 objects + the
  `{uri,verb,message,content}` envelope). Consolidated in
  `docs/networking/schemas/vgs-rest.md`; full surface in `…/14-vgs-api-surface.md`.
- **Matchmaking** — UE4 PartyBeacon reservation protocol; dedicated battle-server
  launch contract + lifecycle reporting (`FVkBattlesResource`); reconnect + heartbeat.
- **Realtime** — UE4 `WebSocketNetDriver` (libwebsockets) replication + RPC surface.
- **OSS / telemetry / watchdog** — custom `OnlineSubsystemVk`; Epic DataRouter
  (non-essential); a local Watchdog process (`127.0.0.1:8080`).
- **Lifecycle & build** — `eConnectionState` machine; prioritized roadmap; an
  actionable **MVP server build guide** (`docs/reimpl/01-mvp-server-guide.md`).

**Remaining** unknowns are narrow: exact value types / deep object nesting and
the WebSocket subprotocol — needing one live capture per resource (E4), planned
in `docs/methodology/traffic-capture-plan.md`. The client-credential **values**
aren't required (a re-implemented SSO sets its own policy).

See `docs/00-INDEX.md` for the full catalogue and per-area status.
