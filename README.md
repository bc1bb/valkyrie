# EVE: Valkyrie – Warzone — Preservation & Documentation Project

> Clean-room technical documentation of the EVE: Valkyrie – Warzone client,
> aimed at understanding and (eventually) re-implementing the now-defunct
> online backend so the game remains playable after official server shutdown.

## What this repo IS

- **Documentation only.** Prose descriptions of how the game works technically:
  network architecture, backend protocol surface, engine layout, file formats.
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

- **Auth** — OAuth2 / CCP SSO, `steam_ticket`/Oculus/`refresh_token` grants, JWT.
- **Environments** — Tranquility (prod) + Chaos/Havoc (test); SSO + VGS hosts.
- **REST (VGS)** — `{version}/valkyrie/...` namespace, query params, snake_case
  JSON object model with HATEOAS `*_uri` links; consolidated in
  `docs/networking/schemas/vgs-rest.md`.
- **Matchmaking** — UE4 PartyBeacon reservation protocol; dedicated battle-server
  launch contract; reconnect + heartbeat.
- **Realtime** — UE4 `WebSocketNetDriver` (libwebsockets) replication + RPC surface.
- **OSS & telemetry** — custom `OnlineSubsystemVk`; Epic DataRouter (non-essential).
- **Lifecycle & roadmap** — `eConnectionState` machine + prioritized re-impl plan.

**Remaining** unknowns are wire-level (exact remaining paths, full JSON schemas,
JWT signing key, WebSocket subprotocol) — they need live capture / dynamic
analysis, planned in `docs/methodology/traffic-capture-plan.md`.

See `docs/00-INDEX.md` for the full catalogue and per-area status.
