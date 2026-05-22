---
doc: gameplay-spectator
title: Spectator / Observer / Replay
summary: The in-match spectator/observer subsystem — VkSpectator* pawn/HUD/camera classes, the server-authoritative view-target (ServerView*/ServerSpectator*) flow, static showcase cameras, spectator slots & state flags, showfloor/kiosk and clone-vat spectating; UE4's DemoNetDriver/replay code is present but appears unused by the game.
keywords: [spectator, observer, camera, view target, target switching, showfloor, kiosk, clonevat, killcam, replay, demo, demonetdriver, scoreboard, game feed]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# Spectator / Observer / Replay

EVE Valkyrie has a first-class **spectator (observer) subsystem**: a player can
join a session as a non-combatant and watch the match through other players'
ships, free static showcase cameras, or a steerable free-look camera, with a
dedicated spectator HUD (target name/score, team scores, game feed, scoreboard).
There is also a **showfloor / kiosk** spectator variant for demo/event builds
and a **clone-vat** in-world spectating mode. All evidence here is embedded
symbols/strings (**E2**); the replay/demo conclusions are **E5** (engine-stock
inference). Source lives under `VkGame/Source/VkGame/Private/Spectator/`
(confirmed file: `VkSpectatorOptionsMenuItemWidget.cpp`) plus
`Private/UI/TacticalMap/` for the clone-vat side.

Cross-refs: spectator RPCs in `networking/08-gameplay-replication.md`; spectator
session fields in `networking/14-vgs-api-surface.md`; showfloor RPCs/launch in
`networking/08`/`13`/`14`; clone-vat / KillCam UI in `gameplay/05-vr-ui.md`;
game modes in `engine/04-game-modes.md`.

## Class surface (E2)

| Class | Role (inferred) |
|-------|-----------------|
| `AVkSpectatorPawn` (+ `ASpectatorPawn`, `USpectatorPawnMovement`) | The observer pawn — possessed by a spectating controller; movable free-look camera body. Hooks `OnMapLoadedEvent`, `OnPlayerStateReceived`. Built on UE4's stock `ASpectatorPawn`/`USpectatorPawnMovement`. |
| `AVkUISpectatorPawn` | A UI/menu-context spectator pawn (front-end / results viewing). Distinct input map (`UISpectatorPawn_LookUp`, `UISpectatorPawn_Turn`). |
| `AVkSpectatorHUD` / `UVkSpectatorHUDWidget` | The spectator HUD actor + its root widget. `InitialiseSpectatorHUD`; widget reacts to `OnPlayerStateAdded/Removed/TeamSet` and drives `MoveSpectatorTarget`. Blueprint asset `/Game/Blueprints/SpectatorUIHUD_BP`. |
| `UVkSpectatorGameModeWidget` | Per-game-mode spectator HUD overlay (mode-specific readouts). |
| `UVkSpectatorOptionsMenuItemWidget` | Spectator options/pause-menu item widget (reacts to `OnLastInputDeviceChanged` — KBM vs pad). The one file confirmed in `srcpaths`. |
| `UVkSpectatorStatics` | Blueprint-callable static helper library (the `GetCurrentSpectator*` / `GetSpectatorTarget*` / `GetSpectatorTeam*` accessors below). |
| `UVkSpectatorModeCamera` | The spectator camera model (free-look / orbit / showcase behaviour). |
| `UVkDebugSpectatorCameraModifier`, `AVkDebugSpectatorActor`, `AVkAIDebugSpectatorActor` | Developer/debug fly-cam + AI-debug observer (`bDebugSpectatorAttached`, `SetDebugSpectatorAttached`). Not a player-facing feature. |
| `AVkSpectatorResultsUI` / `AVkUISpectatorResultsMode` | End-of-match results screen presented to spectators. Blueprint `/Game/Blueprints/SpectatorResultsHUD_BP`; showfloor variant `ShowfloorResultsHUD_BP`. |

### Enums

- `EVkSpectatorMenuMode { NoMenu, PauseMenu, Scoreboard }` — what the spectator's
  on-screen menu is currently showing. Driven by `GetCurrentSpectatorMenuMode` /
  `SetCurrentSpectatorMenuMode` and the `OnSpectatorMenuChangeEvent`.

### Blueprint events (delegate signatures, E2)

`OnSpectatorTargetChanged` (`VkSpectatorTargetChanged`), `OnSelectSpectatorTargetEvent`
(`VkSelectSpectatorTargetEvent`), `OnSpectatorKillEvent` (`VkSpectatorKillEvent`),
`OnSpectatorCapturedPointEvent` (`VkSpectatorCapturedPointEvent`),
`OnSpectatorMenuChangeEvent` (`VkSpectatorMenuChange`),
`OnSpectatorToggleGameFeedEvent` (`VkOnSpectatorToggleGameFeedEvent`),
`OnSpectatorGenericEvent` (`VkSpectatorGenericEvent`),
`BlueprintOnSpectatorViewTargetChanged`. These let HUD blueprints react to
spectator state without C++ changes — i.e. the spectator UI is largely
data/event-driven.

## The view-target (observer) flow (E2)

Spectating is **server-authoritative**: the client requests a view target, the
server validates and assigns it, then replicates the chosen target back. This is
a Vk extension layered on UE4's stock spectator/view-target plumbing.

### Server RPCs (client → server)

| RPC (+ `_Validate`) | Origin | Purpose (inferred) |
|---------------------|--------|--------------------|
| `ServerSpectatorChangeTarget` | Vk | Request switching the watched player. |
| `ServerSelectSpectatorTarget` | Vk | Select a specific spectator target. |
| `ServerSetSpectatorWaiting` | Vk | Mark spectator as waiting (e.g. between rounds / no valid target). |
| `ServerSetSpectatorLocation` | Vk | Push the spectator's chosen free-cam location to the server (so others can see / for verification). |
| `ServerViewSelf` / `ServerViewNextPlayer` / `ServerViewPrevPlayer` | UE4-stock | Cycle the view target (engine `APlayerController` spectator RPCs). |
| `ServerVerifyViewTarget` | UE4-stock | Server re-confirms the client's current view target is legitimate. |
| `ServerUpdateCamera` / `ServerUpdateCameraPOV` | UE4-stock | Replicate the spectator camera POV to the server. |
| `PauseSpectatorTargetSwitching` (+`_Validate`) | Vk | Server-side toggle that locks target switching (`bIsSpectatorTargetSwitchingPaused`); used during scripted moments (e.g. KillCam / end-of-match). |
| `SetDebugSpectatorAttached` (+`_Validate`) | Vk (debug) | Attach the debug fly-cam. |

### Client / replicated state (server → client)

- `ClientSetSpectatorWaiting` — server tells client to enter the waiting state.
- `ClientCurrentSpectatorTarget` / `ReplicatedCurrentSpectatorTarget`
  (`OnRep_ReplicatedCurrentSpectatorTarget`) — the authoritative current target,
  replicated down; `NewSpectatorTarget` / `PreviousSpectatorTarget` track the
  transition.
- `ReplicatedSpectatorTargetEnergy` / `SpectatorTargetEnergy`
  (`OnRep_ReplicatedSpectatorTargetEnergy`) — the watched ship's energy/shield
  value mirrored for the spectator HUD.
- `OnlySpectator` (`OnRep_OnlySpectator`, `bOnlySpectator`) — replicated flag:
  this connection is spectator-only.
- `SpectatorTargetHeadPosition` / `SpectatorTargetHeadRotation` — the target
  player's HMD pose, replicated so a spectator can optionally see through the
  target's head orientation (VR-aware spectating).
- `LastSpectatorStateSynchTime`, `LastSpectatorSyncLocation`,
  `LastSpectatorSyncRotation` — throttle/sync bookkeeping for the
  `ServerSetSpectatorLocation` push.

### HUD / statics accessors (client-side, E2)

`UVkSpectatorStatics` exposes the read API the HUD/blueprints call:
`GetCurrentSpectatorTarget`, `GetCurrentSpectatorControllers`,
`GetCurrentSpectatorCamera`, `GetCurrentSpectatorMenuMode`, `GetSpectatorPawn`,
`GetNumSpectators`/`NumSpectators`, `GetSpectatorTargetName`,
`GetSpectatorTargetScore`, `GetSpectatorTeamID`/`GetSpectatorTeamName`/
`GetSpectatorTeamScore`. Target selection helpers:
`GetNextViewableSpectatorTarget`, `GetPreviousViewableSpectatorTarget`,
`GetFirstViewableSpectatorTargetFromTeamArray`, `ViewNextSpectatorTarget`,
`MoveSpectatorTarget`. On switch, the HUD does a fade transition
(`FadeInSpectatorTarget`, `SpectatorTargetFadeTime`, `SpectatorTargetFadeHoldTime`).

### Capability / eligibility (E2)

`CanSpectate`, `CanSpectateAI`, `CanPlayerBeSpectated`, `MustSpectate`,
`IsSpectator`/`is_spectator`/`bIsSpectator`, `IsSpectatorCamReady`,
`IsSpectatorTargetSwitchingPaused`. `bStartPlayersAsSpectators` makes everyone
spawn as spectators (showfloor/idle states). Note `CanSpectateAI` — AI bots can
be spectated, not just human players.

## Spectator cameras (E2)

Two camera styles coexist:

1. **Free-look / through-target cameras** — driven by `UVkSpectatorModeCamera`
   on the `AVkSpectatorPawn`, with mouse/stick look. `SpectatorCameraComp`,
   `SpectatorCameraMod`, `CurrentSpectatorCamera`, `IsSpectatorCamReady`,
   `SpectatorResetCameraToDefaultPosition`.
2. **Static showcase cameras** — fixed cameras placed in the level. A defined
   set `Spectator_Camera_A` / `_B` / `_C` (group `Spectator_Cameras` /
   `SpectatorTable`), selected via `GetStaticSpectatorCameraFromIndex` and
   `OnSelectSpectatorCameraHotspot`, hot-keyed (camera A/B/C bindings below).
   These give broadcast-style fixed angles of the arena.

## Spectator input bindings (E2)

KBM/pad action names (the spectator has its own input context):
`SPECTATOR_NEXTTARGET` / `SPECTATOR_PREVIOUSTARGET` (cycle who you watch);
`SPECTATOR_SWITCHTOCAMERAA/B/C` (jump to static cameras); `SPECTATOR_NEXTMENUITEM`
/ `SPECTATOR_PREVIOUSMENUITEM` + `Spectator_PauseMenu{Up,Down,Left,Right}`
(menu nav); `SPECTATOR_TOGGLEHUD`, `SPECTATOR_TOGGLEGAMEFEED` (show/hide HUD &
event feed); `SPECTATOR_ROTATEX/Y` + `SPECTATOR_ROTATEMOUSEX/Y` +
`SPECTATOR_LOOKACTIVE` (look control); `SPECTATOR_ZOOM` / `SPECTATOR_MOUSEZOOM`
(zoom); `SPECTATOR_RESETCAMERA`; plus `Spectator_Quit` / `Spectator_QuitConfirm`.
Pitch invert is configurable (`bSpectatorPitchInvertEnabled`,
`bMouseSpectatorPitchInvertEnabled`).

## Showfloor / kiosk spectating (E2)

A dedicated **showfloor** (trade-show / demo-kiosk) path reuses the spectator
system. The session carries `is_showfloor` and `showfloor_spectator`
(`networking/14`); the match-flow RPCs `ServerShowFloorStart`,
`ServerShowFloorEndMatch`, `ServerShowFloorAIAdd` drive a self-running
demo/attract match (`networking/08`). Showfloor uses its own results screen
(`ShowfloorResultsHUD_BP`, `ShowFloorResultsScreenURL`), an empty staging map
(`ShowFloorEmptyMapURL`), and a launch entry `ShowFloorLaunch` /
`CloneVatLaunchAllowed`. Combined with `bStartPlayersAsSpectators`, this lets a
kiosk run continuous AI-vs-AI battles that bystanders observe. Asset/object
visibility differs in this mode (`bHideInShowfloor`,
`bHideAllAttachedObjects_Showfloor`, `bNotInShowfloor`, `IsShowfloor`).

## Clone-vat spectating & KillCam (E2)

Separate from the free-cam spectator, the **clone-vat** (the in-world spawn /
results theatre, `gameplay/05-vr-ui.md`) has its own spectating state:
`bIsSpectatingCloneVat` / `IsSpectatingCloneVat` (`CloneVatSpectator`). The
clone-vat "screen" can show different content via
`EVkCloneVatScreenType { NotSet, ShipSelect, TacticalMap, KillCam, PauseScreen,
EndOfMatch, Max }`. **KillCam is one of these clone-vat screen states**, not an
independent replay system — it is a presentational mode of the clone-vat UI
(`AVkCloneVatUI`), driven by live/replicated state, that shows the player's
death. Connection URL options gate these: `?SpectatorOnly=1` and
`?SpectatorOnly=1?CloneVatOnly=1` (the latter restricts a connection to clone-vat
spectating only).

## Replay / demo recording — engine-stock, apparently unused (E5)

UE4's full replay machinery **is compiled into the binary**, but only as
**stock engine code with no Vk integration found**:

- `DemoNetDriver` (`Engine/.../DemoNetDriver.cpp`), the HTTP & Null replay
  streamers (`HttpNetworkReplayStreaming`, `NullNetworkReplayStreaming`),
  `UGameInstance::StartRecordingReplay` / `StopRecordingReplay` / `PlayReplay` /
  `RecordReplay`, `EDemoPlayFailure{Generic, DemoNotFound, Corrupt, InvalidVersion}`,
  and the `demo.*` console vars (`demo.RecordHz`, `demo.EnableCheckpoints`,
  `demo.GotoTimeInSeconds`, `DemoPlayTimeDilation`, …).
- Launch/console args are the **engine defaults**: `-REPLAY=`, `DemoRec[=]`,
  `DEMOPLAY`, `DEMOREC`, and `-noreplays` ("Rejected due to -noreplays option").
- `ReplaySpectatorPlayerControllerClass` and `SpectatingPlayerController` are
  **stock `UWorld`/`AGameMode` properties**, and `UDemoNetDriver::SpawnDemoRecSpectator`
  is the engine's replay-spectator spawner — present because the engine module
  is, not wired to Vk's `VkSpectator*` classes.

No `Vk`-prefixed replay/demo class, command, or asset path exists. The game's
spectating is **live** (server-authoritative view targets over the WebSocket
NetDriver), not recorded-demo playback. There is no evidence of a player-facing
"watch this match later / save replay" feature in the shipped client. (A
re-implementation could *enable* UE4 demo recording for free, since the engine
code is there, but the original game does not appear to use it.)

## Relevance to a re-implementation

- A re-impl battle server must accept and **validate** the Vk spectator RPCs
  (`ServerSpectatorChangeTarget`, `ServerSelectSpectatorTarget`,
  `ServerSetSpectatorWaiting`, `ServerSetSpectatorLocation`,
  `PauseSpectatorTargetSwitching`) and **replicate** `ReplicatedCurrentSpectatorTarget`
  / `ReplicatedSpectatorTargetEnergy` / `OnlySpectator` /
  `SpectatorTargetHead{Position,Rotation}` back to spectators. The stock
  `ServerView*`/`ServerVerifyViewTarget`/`ServerUpdateCamera*` are inherited from
  UE4 4.14.
- The matchmaking/session layer must honour the spectator slot fields:
  `is_spectator`, `current_spectators`, `max_spectators` (+`showfloor_spectator`,
  `is_showfloor`) — `networking/14`. Spectator joins consume a spectator slot,
  not a player slot.
- HUD/menu/camera logic is **client-local** (the `VkSpectator*` widgets,
  `UVkSpectatorStatics`, static `Spectator_Camera_A/B/C`) — it works from
  replicated state and needs no extra server endpoints.
- Showfloor is an optional, self-running demo mode; not required for normal
  multiplayer parity.

## Open questions

- Exact field layout of `AVkSpectatorPawn` / `AVkSpectatorHUD` / the replicated
  spectator props (`recover_object.py` returns 0 fields for these reflected
  UObjects; needs deeper E3 class-layout work).
- Server policy: who is allowed to spectate (any joiner vs. friends/party only),
  and whether `current_spectators`/`max_spectators` are enforced backend-side vs
  battle-server-side.
- Whether `SpectatorTargetHead{Position,Rotation}` is always replicated or only
  when a spectator is actively viewing that target (bandwidth concern).
- Whether the static showcase cameras (`Spectator_Camera_A/B/C`) are
  per-map level placements or a fixed engine-side set.
