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
| Client binary    | `VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe` (~62 MB)|

## Documentation map

Start at **`docs/00-INDEX.md`** — every doc carries a token-saver YAML header
(`summary`, `keywords`, `status`) so an LLM can decide relevance before reading.

## Status

Early. Networking architecture mapped from binary metadata; protocol details
in progress. See `docs/00-INDEX.md` for per-area status.
