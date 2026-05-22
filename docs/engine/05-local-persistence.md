---
doc: engine-persistence
title: Local Persistence & Settings
summary: Client-local on-disk state — VkPersistentData (_pers.data), VkPersistentStats, settings UObjects (audio/input/music), over UE4's stock SaveGame + .ini config. Backend remains authoritative for progression; local files are cache/settings.
keywords: [persistence, save, _pers.data, VkPersistentData, VkPersistentStats, settings, GameUserSettings, ini, savegame, local, cache]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E5]
---

# Local Persistence & Settings

How the client stores state on disk. Distinct from the backend (`networking/`):
the **backend is authoritative** for progression/economy (`networking/11-*`), so
these local files are best understood as **settings + cache**, not the source of
truth for owned items/currency.

## Vk-specific local state (E2)

| Class | Role |
|-------|------|
| `VkPersistentData` | Local persistent blob — the `_pers.data` files (observed path shape `Valkyrie/<…>/<id>/_pers.data`, i.e. per-user under a Valkyrie save dir). |
| `VkPersistentStats` / `UVkPersistentStats` | Locally-cached pilot stats. |
| `UVkAudioSettings` | Audio settings (volumes, output config). |
| `UVkInputSettings` | Input settings (bindings, deadzones — cf. `03-input-peripherals.md`). |
| `UVkDynamicMusicMapSettings` | Dynamic-music configuration. |

## UE4 stock mechanisms used (E5)

- **SaveGame system**: `CreateSaveGameObject`, `DoesSaveGameExist`, and the
  `CPF_SaveGame` property flag (marks which UPROPERTYs serialize into a save).
  Saves live under a `SaveGames/` directory in the user dir.
- **Config `.ini`**: `GameUserSettings.ini` (resolution/quality/etc.) and the
  engine/game ini stack (`Engine.ini`, `DefaultGame.ini`, …) for tunables and
  console variables.

## Where it lives (E5, Proton/Windows)

On the shipped Windows build these sit under the user's
`…/VkGame/Saved/` tree (UE4 default): `Saved/SaveGames/`, `Saved/Config/`,
plus the Valkyrie `_pers.data` blobs. Under Proton (this machine) that maps into
the compat prefix's emulated `Documents`/`AppData` (see `analysis/compatdata`,
git-ignored). A capture/inspection of these (without committing them) could
reveal the local-cache schema.

## Relevance to preservation

- **Settings** (audio/input/video) are fully local — no backend needed.
- **`_pers.data` / `VkPersistentStats`** are most likely a **cache/mirror** of
  backend pilot state for fast startup/offline display. A re-implemented backend
  is still the authority; the client re-syncs on login. So these files do **not**
  need to be understood to restore online play — they matter only for
  offline/standalone behaviour and would be regenerated from the backend.

## Open questions

- Exact `_pers.data` serialization (UE4 `FArchive` blob? versioned?).
- Whether any *authoritative* state lives only locally (unlikely given the
  server-authoritative backend, but worth a glance during capture).
