---
doc: gameplay-world-spawning
title: World, Levels & Spawning
summary: How a match level is composed and how pilots spawn into it — VkMapLoader sub-level streaming for per-mode objective sets, VkPlayerStart launch-tube spawn points and start-point-group selection (the ServerSetStartPointGroupToRespawnAt RPC), the respawn-map selection state machine, and the in-match flight world-bounds / out-of-bounds warning (distinct from the VR play-area guardian).
keywords: [world, level, sublevel, streaming, map loader, spawn, respawn, player start, launch tube, start point group, respawn map, kill volume, world bounds, out of bounds, boundary, play area, turret start, boss ship start]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E5]
---

# World, Levels & Spawning

How a match's playable space is assembled and how a pilot is placed (and
re-placed) inside it. Identifiers are class/enum/field symbols recovered from
the binary: E1 = recovered source paths, E2 = embedded strings, E5 =
engine-stock UE 4.14 reused verbatim. The mode *names* and objective sub-level
*set* live in `engine/04-game-modes.md` (`EVkGameModeSubLevels`); the *objects*
that implement objectives (capture points, carriers, clone-vat) live in
`gameplay/04-mode-mechanics.md`; the spawn point class first appears in
`gameplay/01-player-ship-control.md`; the spawn/level RPCs are catalogued in
`networking/08-gameplay-replication.md`.

Server-authoritative throughout: the battle server owns map load, spawn
selection and bounds enforcement; clients stream levels and predict/animate
(engine-stock model, `networking/08-*`).

## Source clusters (E1)

The dedicated `World/` and `PlayerStart/` folders are small — most "world"
logic is engine-stock UE4 plus a thin Vk layer:

| Source path (`VkGame/Source/VkGame/Private/`) | Role |
|----------------------------------------------|------|
| `World/VkMapLoader.cpp` | Map / sub-level load orchestration. |
| `World/VkMapLoadingData.cpp` | Load-screen/loading-state data (`/Game/Movies/MapLoadingData`). |
| `PlayerStart/VkPlayerStart.cpp` | Spawn-point actor (+ launch-tube spawning). |
| `PlayerStart/VkLaunchTube.cpp` | The carrier launch-tube actor a pilot fires from. |
| `PlayerStart/VkLaunchTubeMeshActor.cpp` | Launch-tube visual mesh actor. |

## Level composition & streaming (E2 + E5)

A match level is a **persistent level** plus streamed **sub-levels** that supply
the per-mode objective set. The sub-level *catalogue* is the
`EVkGameModeSubLevels` enum (`engine/04-*`): `CarrierVolumes`, `Mines`
(+ `Mines_SingleCapturePoint`, `Mines_ThreeCapturePoints`), `Relics`, `Scout`,
`Survival`, `VirusObjectives`, `WarpGates`. The same persistent map is composited
with a different sub-level (e.g. one vs three capture points) to realise a mode
variant.

**Vk streaming layer (E2):** `VkMapLoader` drives a list of sub-levels to load
and waits for them before the match starts:
- `SubLevelsToLoad`, `SubLevelName`, `bWaitingForSubLevel`,
  `SubLevelLoadTimeout`, `SubLevelTimeoutTimer` — the load-and-wait gate.
- `OnSubLevelLoaded` callback (e.g. `AVkGameMode_Challenge::OnSubLevelLoaded`)
  fires per sub-level so a mode can finish setup once its objective chunk is in.
- `VkMapLoadingData` / `/Game/Movies/MapLoadingData` — the loading-screen data
  shown while streaming (`bStartedLoadMapMovie`). Recovered `VkMapLoader` field
  hint: `game` (the only field the constructor-anchor tool resolves).
- `AVkUIGameState::LoadServerMap()` is the entry point that creates a `MapLoader`
  for the battle URL; it short-circuits if the requested URL already matches the
  current battle map ("URL is the same as battle so quitting LoadServerMap").

**Engine-stock streaming underneath (E5):** the usual UE 4.14 level-streaming
machinery is reused verbatim — `StreamingLevels`/`StreamingLevelNames`,
`LoadStreamLevel`/`StreamLevelIn`/`StreamLevelOut`, `FlushLevelStreaming`,
`ALevelStreamingVolume` (+ `bUseClientSideLevelStreamingVolumes`),
`ELevelVisibility` { `Hidden`, `Visible` }, and the replicated visibility RPCs
`ServerUpdateLevelVisibility` / `ClientUpdateLevelStreamingStatus` /
`ClientFlushLevelStreaming` (the `ServerUpdateLevelVisibility` RPC is also listed
in `networking/08-*`). A re-implemented **server on the same engine inherits all
of this**; only the `VkMapLoader` sub-level list/timeout policy is Vk-specific.

## Player start points & launch tubes (E1 + E2)

A spawn point is `AVkPlayerStart` (extends engine `APlayerStart`). Its signature
Vk behaviour is that each start point owns a **launch tube** — the carrier tube
the ship fires out of when a life begins (the cockpit/launch intro in
`gameplay/01-*`):

- `LaunchTubeClass` / `EditorPreviewLaunchTubeClass` — the tube actor class to
  spawn for this start point.
- `AVkPlayerStart::CreateLaunchTube()` spawns an `AVkLaunchTube`
  (visual: `AVkLaunchTubeMeshActor`) at the start point; `DelayedDestroyLaunchTube()`
  tears it down after launch. Diagnostics confirm the lifecycle ("Spawned /
  Destroying launch tube '%s' for PlayerStart '%s'", "Failed to spawn launch
  tube").
- A start point **without** a tube class is a known failure mode: *"Startpoint
  %s has no LaunchTubeClass - Player probably started with a black screen!"* —
  i.e. the launch-tube view is the player's spawn camera, so a tubeless start
  yields no view.

Other map-placed "start" actors spawn non-player entities at level positions:
`AVkTurretStart` (sentry turrets, cf. carrier turrets in `gameplay/04-*`) and
`AVkBossShipStart` (PvE boss-ship spawn). `UVkMovingSpawnManagerComponent`
indicates at least one spawn source can move (a moving spawn volume/anchor) —
detail beyond the name is unconfirmed.

## Spawn selection & start-point groups (E2 + E5)

Two layers cooperate to choose *where* a pilot (re)spawns.

**Engine-stock selection (E5):** UE4's GameMode override path —
`ChoosePlayerStart` / `FindPlayerStart` / `K2_FindPlayerStart`,
`RestartPlayerAtPlayerStart` / `RestartPlayerAtTransform`, keyed by
`PlayerStartTag` / `PlayerStartName`. Start points are *rated* and the
best-rated one is chosen; the recovered warning *"Warning - PATHS NOT DEFINED or
NO PLAYERSTART with positive rating"* and *"Player start not found, failed to
RestartPlayerAtPlayerStart"* are the stock failure paths. `RestartPlayerAtTransform`
guards against restarting a spectator-only player.

**Vk start-point groups (E2):** spawn points are organised into **groups**, and
the group a player respawns from is replicated/selectable:
- `ServerSetStartPointGroupToRespawnAt` (+ `_Validate`) — the server RPC the
  client calls to pick its respawn group (`StartPointGroupToRespawnAt` is the
  stored selection). This is the spawn-side companion to team assignment via the
  `-InitialPlayerTeam=` launch arg (`networking/05-battle-server-launch.md`) and
  is listed under match-flow RPCs in `networking/08-*`.
- `bIgnoreSpawnPointTeamID` — a toggle to disregard a spawn point's team
  ownership when selecting (some modes spawn team-agnostically).
- `SpawnPoints`, `VkSpawnPointSocket`, `bRenderSpawnPoints` (debug visualisation)
  — the spawn-point set and an attach socket / debug-draw flag.

So: the **server** picks the team and the engine rates/chooses a start point
within the selected **start-point group**; the player can request a different
group (e.g. front vs rear of the map) via `ServerSetStartPointGroupToRespawnAt`,
subject to `_Validate`. This couples to the clone-vat respawn flow in
`gameplay/04-*` (a respawn launches a new clone ship from a start point's tube).

## Respawn-map (between-lives spawn UI) (E2)

While dead/awaiting launch, the pilot uses a **respawn map** — the tactical
spawn-selection view (one of the clone-vat screens, `EVkCloneVatScreenType::TacticalMap`
in `gameplay/04-*`). It is a small client state machine, `EVkRespawnMapState`:
`WaitingForSelection` → `WaitingForServerAcknowledgeSpawn` → `Spawned` →
`TickingRemainingTime` / `WaitingForRemainingTimeUpdate` → `FadingOut`. Driven by
`UpdateRespawnMapState` / `EndRespawnMapState` / `bIsInRespawnMapState`, with the
map's actors paused while shown (`RespawnMapActorTickDisabled`,
`RespawnMapComponentsHidden`/`…TickDisabled`, `RespawnMapFrozenActors`).
`AVkRespawnMapLocator` is the per-start-point marker on that map
(`OnPlayerLoadoutInfoChanged`); the `Even/OddStartPoint` + `Even/OddEndPoint`
fields (alongside `ConnectionLine*`, `RadiusOffset`, `PlanetHeightCurve`) are the
locator's connection-line rendering parameters, not the group-selection logic
itself. The `WaitingForServerAcknowledgeSpawn` state is the client-side view of
the server-authoritative `ServerSetStartPointGroupToRespawnAt` round-trip above.

## World bounds — in-match flight boundary (E2)

The playable flight volume is bounded by an **out-of-bounds warning** system that
warns a straying pilot and (implicitly) turns them back / kills the ship if they
do not return:
- `GetOutOfBoundsWarning` / `SetOutOfBoundsWarning`, `InsertOutOfBoundsWarning` /
  `RemoveOutOfBoundsWarning` — the warning-state plumbing (HUD/cockpit warning).
- State labels `OutOfBoundsSafe`, `OutOfBoundsInitialWarning`,
  `OutOfBoundsFinalWarning` — escalating proximity-to-edge warning levels
  (these cluster near AI/boss-ship symbols, i.e. the gameplay flight boundary).
- `DbEnableWorldBoundsChecks` — a debug toggle gating the world-bounds check.
- A render mask (`OutOfBoundsMask`, `VisualizeOutOfBoundsPixels`) drives the
  edge-of-world screen effect.

Engine-stock kill volumes also exist (`AKillZVolume`, `KillZ` / `NoKillZ`,
`KillZDamageType` — E5) as a hard backstop, but the gameplay edge is the
graduated out-of-bounds warning rather than an instant kill plane.

> **Disambiguation — game world-bounds vs VR play-area:** a *second*, unrelated
> boundary system exists: the **VR room-scale guardian** (`EBoundaryType`
> { `Boundary_Outer`, `Boundary_PlayArea` }, `UOculusRiftBoundaryComponent`,
> `UVkCockpitVRBoundaryComponent`, `CheckIfPointWithinPlayArea`,
> `GetPlayAreaDimensions`, `OnOuterBoundaryTriggered`/`…Returned`,
> `OnHMDCrossesBoundary`). That is the Oculus/SteamVR physical-space guardian for
> the seated/standing player (a VR-comfort concern, `engine/06-rendering-audio-vr.md`),
> **not** the in-match ship flight boundary documented above. They share the word
> "boundary" but are different subsystems; do not conflate them.

## Re-implementation / preservation relevance

- **Level streaming & spawn selection are server-side and ship in the binary.**
  A re-implemented **backend does not run them**: it only supplies the map/mode
  (the `-gamemode=` / map URL launch args, `networking/05-*`) and team
  (`-InitialPlayerTeam=`) when allocating the battle server. The server then
  loads the persistent level + the mode's `EVkGameModeSubLevels` chunk via
  `VkMapLoader` and rates/chooses start points itself.
- A re-implemented **dedicated server** (same engine) inherits all UE4
  level-streaming, `ChoosePlayerStart` rating, and kill-volume logic for free;
  the Vk-specific work is the `VkMapLoader` sub-level list/timeout, the
  launch-tube spawn (`AVkPlayerStart::CreateLaunchTube`), the start-point-group
  selection RPC, and the out-of-bounds warning thresholds.
- All client-visible parts (launch-tube animation, respawn map, boundary
  effects, VR guardian) are client/engine-local — a preservation client runs
  them as shipped.

## Open questions

- The actual map list and which persistent level pairs with which sub-level set
  — that is **content/asset RE** (lives in the `.pak`), explicitly out of scope.
- Numeric world-bounds extents and the initial/final warning distances/timers —
  balance/config data in assets (out of scope).
- Start-point-group membership model: how points are tagged into groups and the
  exact rating function inputs (team, group, occupancy) — only the symbol names
  above are evidenced; field offsets/order are unconfirmed (the constructor
  anchor for `VkPlayerStart` resolves 0 ordered fields, consistent with the
  `gameplay/04-*` anchor caveat). Would need targeted disassembly (E3) or
  `.uasset` reflection data.
- `UVkMovingSpawnManagerComponent` — whether moving spawns are used in shipped
  modes (e.g. a moving carrier) is unconfirmed beyond the class name.
- Whether the out-of-bounds final state deals lethal damage (via `KillZ`-style
  path) or only forces a turn-around — not determinable from strings alone.
