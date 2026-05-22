---
doc: gameplay-framework
title: Game Framework, State & Core
summary: The UE4 GameInstance/GameMode/GameState hierarchy specialized for Vk (the per-process / per-match / replicated-state glue), the shared VkCore + VkStaticData client modules, and the static-data → gameplay binding — i.e. the architectural glue that ties the gameplay subsystems together.
keywords: [game mode, game state, game instance, framework, core, static data, object, geometry, post process, gameplay statics, blueprint function library, json object, map loader, glue]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Game Framework, State & Core

This is the **architectural glue** beneath the gameplay subsystems mapped in
`gameplay/00-overview.md`: the UE4 framework triad (`GameInstance` /
`GameMode` / `GameState`) subclassed for Vk, the shared utility modules
(`VkCore`, `VkStaticData`, plus Blueprint-callable "statics" libraries), and a
few cross-cutting actors/components (geometry, object tracking, post-FX). It is
the layer the other docs lean on — not a gameplay mechanic itself.

Scope notes / non-repetition:
- The **mode taxonomy enums** (`EVkGameModeType`, `EVkGameModeSubLevels`,
  `EVkCustomMatchType`, the Challenge enums) are in `engine/04-game-modes.md` —
  not repeated here; this doc covers the **mode/state C++ class hierarchy**.
- The **client connection state machine** (`AVkUIGameState`,
  `EVkUIGameStateConnectionState`) is in `gameplay/05-vr-ui.md`, and the
  net-level `eConnectionState` lifecycle is in `networking/09-*` — referenced,
  not repeated.
- **Backend** static-data distribution (`VkStaticDataResource`, `GetFileList`)
  is in `networking/10-*`; here we document the **client-side consumption**
  classes (`VkStaticDataManager` / `VkStaticDataItem` / `UVkStaticDataStatics`).

Evidence: source-path clustering (E1, `srcpaths.txt`) and symbol/format strings
(E2, `strings_all.txt`); class names are interface facts.

## 1. The UE4 framework triad, Vk-specialized

UE4 splits "the glue" three ways, and Vk subclasses each (symbols carry the
stock `U`/`A` prefixes):

| Stock UE4 base | Vk subclass | Lifetime / role |
|----------------|-------------|-----------------|
| `UGameInstance` | `UVkGameInstance` (also `UPlatformGameInstance`) | **One per process** — survives map travel; owns app-global state, login/online glue, the bridge from the platform launcher to the running game. |
| `AGameModeBase` / `AGameMode` | `AVkGameModeBase` → `AVkGameMode` → mode-specific subclasses | **Server-authoritative match rules** for one level; exists only where authority does (host/dedicated). |
| `AGameStateBase` / `AGameState` | `AVkGameState` → mode-specific subclasses (+ `AVkUIGameState`) | **Replicated match state** — the shared, networked view every client reads. |

`UVkGameInstance` is confirmed as a symbol in the binary, though its source file
was not captured in `srcpaths.txt` (the engine's stock `GameInstance.cpp` build
path is present; the Vk subclass is referenced by class name only). Treat it as
the process-global owner consistent with UE4's standard pattern.

### 1.1 GameMode hierarchy (`VkGame/.../GameMode/`, E1+E2)

The base `AVkGameModeBase` / `AVkGameMode` (e.g. `AVkGameMode::LoadMapForLocalClient`,
the `VkLoader` path) is specialized per game mode. Recovered subclass symbols
(E2) — a superset of the files in `srcpaths.txt` (E1), since some are
Blueprint-derived or only present as symbols:

- **PvP objective:** `_Control`, `_TDM`, `_Bomb`, `_Bounty` (`_Bounty_Bounty`),
  `_Maelstrom`, `_Salvage`, `_HighestScore`.
- **Large-scale / fleet:** `_Armada`, `_Armada_Chronicle`.
- **PvE / co-op:** `_PvEBase` → `_PvE_ContinuousAI`, `_PvE_WavesOfAI`,
  `_PvE_Shipyard_Ch1`; `_Scout`, `_Virus`, `_Pursuit`.
- **Tutorial / NPE:** `_NPE2_Base` → `_NPE2_FighterAdvanced`,
  `_NPE2_HeavyAdvanced`, `_NPE2_SupportAdvanced`, `_NPE2_FreeFlight`;
  `_NPE_TestArena`.
- **Narrative / sandbox:** `_Prologue`, `_Playground`, `_Holodeck`.
- **Shared mechanics base:** `_LimitedRespawns` (respawn-capped rounds),
  `_Challenge` (time-trial/objective challenges, see `engine/04-*`).
- **Hosting variant:** `_GameLift` — a GameMode flavour tied to the AWS GameLift
  battle-server path (cf. `networking/05-*` battle-server launch).

> `AVkGameModePanel` / `AVkGameModePanel_LimitedRespawns` are the in-world
> mode-info panel actors (UI display of the active rules), not the rule classes.

These correspond 1:1 with the `EVkGameModeType` values catalogued in
`engine/04-*`; the class is the **behavioural** implementation, the enum is the
**vocabulary** the session/matchmaking layer uses.

### 1.2 GameState hierarchy (`VkGame/.../Network/VkGameState.cpp`, E1+E2)

`AVkGameState` (under `Private/Network/` — i.e. treated as the replicated
networking surface) is subclassed in parallel with the modes:
`_Armada`, `_Challenge` (`NotifyTimeBonusApplied`, `NotifyTimerStarted`),
`_Pursuit`, `_PvEBase`, `_PvE_WavesOfAI`, `_NPE2_Base`,
`_NPE2_FighterAdvanced`, `_NPE2_HeavyAdvanced`, `_NPE_FreeFlight`,
`_Matinee` (cutscene/cinematic state). A re-implemented host replicates the
relevant `AVkGameState` subclass; clients only read it.

`AVkUIGameState` (`Private/Network/VkUIGameState.cpp`) is the **front-end**
GameState bridging UI ↔ backend/matchmaking (`HandleBackendDataChange`,
`LoadServerMap()`, the `EVkUIGameStateConnectionState` machine). It is fully
documented in `gameplay/05-vr-ui.md`; it belongs here only as the UI member of
the GameState family.

### 1.3 World loading (`VkGame/.../World/`, E1+E2)

`AVkGameMode::LoadMapForLocalClient` and `AVkUIGameState::LoadServerMap()` drive
travel through:

| Class | Role |
|-------|------|
| `VkMapLoader` | Creates/compares the map-travel URL (loads a new level only when the target differs from the current battle URL — "MapLoader URL is the same as battle so quitting"). |
| `VkMapLoadingData` | Loading-screen / transition data (e.g. the `MapLoadingData` movie asset) shown during travel. |

This is the seam between the front-end (`MapTransition` connection-state) and
arriving in a battle level under the appropriate `AVkGameMode`/`AVkGameState`.

## 2. Static-function libraries ("statics", `VkGame/.../GameMode|Stats/`)

UE4 `UBlueprintFunctionLibrary`-style stateless helpers exposing engine/Vk
operations to Blueprints and C++:

| Class | Role |
|-------|------|
| `UVkGameplayStatics` | General gameplay helpers (Vk's analogue of `UGameplayStatics`). Confirmed members include `UpdateGameStateForAudio()` (drives the dynamic-music/audio state from match state) and `ApplyInterpMaterialParamTo` (material-parameter interpolation). |
| `UVkStaticDataStatics` | Blueprint accessor that **exposes the loaded static data to gameplay** (the `Static_Data` category). The read-side counterpart to the `VkStaticData` module below. |

## 3. Gameplay stats (`VkGame/.../Stats/VkGameplayStats.cpp`, E2)

`AVkGameplayStats` is the per-match event/stats logger (kills, deaths, weapon
usage). It defines its own logging enums — `EVkDeathLogOption` and
`EVkHomingEvent` (`VkGameplayStats.EVkDeathLogOption` / `…EVkHomingEvent`) — and
guards against malformed input ("Null weaponType logged"). It feeds the
end-of-match summary / telemetry; cf. scoring (`gameplay/01-*` scoring section)
and telemetry (`networking/07-*`). Distinct from `VkFramerateStats` (a separate
module: client-side FPS/perf instrumentation).

## 4. VkCore — shared core utilities (`VkGame/Source/VkCore/`, E1+E2)

The smallest shared module captured. Notable type:

| Class | Role |
|-------|------|
| `FVkJsonObject` | A wrapper/helper over UE4 `FJsonObject` with typed, fail-soft accessors — `Find`, `TryGetBoolField`, `TryGetNumberField`, `TryGetNumberArrayField`, `TryGetObjectArrayField`, etc. (each logs a named-field miss instead of asserting). |

`FVkJsonObject` is the common JSON-reading primitive underneath the REST
resources (`networking/01-*`, `14-*`) and the static-data parsing below — it
explains the consistent "field named '%s'" diagnostics across those layers.
(`VkRestUtils` and `OnlineSubsystemVk(Steam)` are sibling shared modules, but
those are documented in `networking/`.)

## 5. VkStaticData — client-side static-data consumption (`VkGame/Source/VkStaticData/`, E1+E2)

Where the downloaded static-data files (manifest fetch = `networking/10-*`)
become queryable game data on the client:

| Class | Role |
|-------|------|
| `VkStaticDataManager` | The client registry/cache of loaded static data — holds the parsed item set and serves lookups. Populated from the files delivered by `VkStaticDataResource` / `GetFileList` (`networking/10-*`). |
| `VkStaticDataItem` | One static-data record (a balance/catalog/config entry). |
| `UVkStaticDataStatics` | Blueprint-facing accessor over the manager (§2) — how gameplay/UI read static data without touching the network layer. |

### 5.1 Static-data binding fields (E2)

Gameplay assets reference static data by stable key rather than embedding
values. Recovered field/identifier names:

- `StaticDataLink` / `StaticDataLinks` — link(s) from an asset to its
  static-data record(s).
- `ShipClassStaticDataLink`, `UpgradeStaticDataLink` — typed links (ship class,
  upgrade) into the catalog.
- `StaticDataUniqueName` — the unique key used to resolve a record.
- `StaticDataMapName` — static data keyed per map.
- `About_StaticDataVersion`, `LoginMessage_StaticDataDownloadFailed` — version
  surfacing and the failure path (a failed static-data download blocks login).

This confirms the **content/code split**: balance and catalog values live in
static data (server-served, versioned), and gameplay classes hold only *links*
to them — consistent with the project's "architecture, not asset values" scope.

## 6. Cross-cutting framework actors/components

Glue actors/components that don't belong to one gameplay subsystem:

| Class | Module/dir | Role |
|-------|-----------|------|
| `UVkGeometry` / `UVkGeometryComponent` | `VkGame/.../Engine/` | Vk geometry abstraction — `AddVkGeometry` / `RemoveVkGeometry`, `FillGeometryPayload`. |
| `UVkGeometrySubSystem` | `VkGame/.../Engine/` | Central registry/subsystem tracking active `VkGeometry` (the add/remove target above). |
| `AVkObjectMultiTracker` / `UVkObjectMultiTrackerComp` | `VkGame/.../UI/HUD` + `…/UI/Utility` | Tracks multiple world objects for HUD bracketing/targeting (a multi-target tracker; ties into the brackets/radar UI, `gameplay/05-*`). |
| `UVkPostExplosionAnimater` | `VkGame/.../Effects/` | Drives post-explosion animation/effect sequencing (a post-event FX animator, not a render post-process pass). |

`UVkGameUserSettings` (`VkGame/.../LocalPlayer/`) is the Vk `UGameUserSettings`
subclass (video/quality/etc.); it is part of the client framework but the
settings/persistence story is owned by `engine/05-local-persistence.md`.

## 7. Relevance to preservation / re-implementation

- **GameMode = server's job; GameState = what's replicated.** A re-implemented
  host instantiates the right `AVkGameMode` subclass per mode and replicates the
  matching `AVkGameState`; clients only need to *receive* a coherent GameState
  (cf. `networking/08-*`).
- **`VkStaticDataManager` makes static data a P0 dependency on the client too:**
  the backend must serve the manifest/files (`networking/10-*`), but the client
  won't progress past login if the manager can't populate
  (`LoginMessage_StaticDataDownloadFailed`). Re-implementers must satisfy both
  ends.
- **`UVkGameInstance` is mostly local** (process-global state, platform glue);
  no special server support beyond what login/online already require.
- **VkCore / geometry / object-tracker / post-FX are client-local** glue with no
  backend dependency — they run as shipped under a preservation client.

## 8. Open questions

- `UVkGameInstance`'s exact responsibilities (login orchestration vs. just
  state container) — its source wasn't in `srcpaths.txt`; only the class symbol
  is confirmed.
- `VkStaticDataItem` internal schema (does it generically wrap a `FVkJsonObject`
  per record, or are there typed item subclasses per catalog?).
- Whether `VkStaticDataManager` persists/validates static data on disk
  (overlaps the `engine/05-*` cache question and the `networking/10-*` hash/
  version open item).
- Division of labour between `AVkGameMode` subclasses and their paired
  `AVkGameState` subclasses (some modes have a GameMode but no distinct
  GameState symbol, implying shared/base state reuse).
