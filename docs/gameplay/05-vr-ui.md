---
doc: gameplay-vr-ui
title: VR UI / HUD / Interaction
summary: The diegetic, world-space VR UI — the in-cockpit HUD (radar, brackets, crosshair, orientation circle, warnings) and the head-look-selectable front-end scene framework (VkVrUi*), plus smart-pings (the one networked UI element).
keywords: [vr ui, hud, gaze, head-look, head-selectable, radial menu, selection wheel, radar, ping, smart ping, cockpit ui, world-space, diegetic, brackets, crosshair, orientation circle, scene manager]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# VR UI / HUD / Interaction

EVE Valkyrie is **VR-first**, so its UI is overwhelmingly **diegetic /
world-space**: in-flight info is rendered as cockpit-mounted holographic
instruments and as 3D markers floating on contacts in the world; menus are a 3D
"hangar" the player navigates by **head-look** (look at an object → it
highlights → confirm). There is almost no flat 2D screen-space HUD. This splits
into two clusters:

- **In-flight HUD** (`Private/UI/HUD/`, `Private/Cockpit/`, `Private/Brackets/`,
  `Private/UI/Crosshair/`) — what you see while flying.
- **Front-end VR UI** (`Private/UI/VrUi/`) — the menu/scene framework
  (`VkVrUi*`): login, hangar, loadout, results, store, etc.

Almost all of it is **client/engine-local** (rendered locally from replicated
state); the lone exception with its own network path is the **smart-ping**
system (RPCs, below). Interaction model details:

- **Head-look selection** (HMD/look ray) drives the front-end — see below.
- **Eye-tracking gaze** (Tobii GTOM gaze-to-object) is a *separate* channel that
  scores in-world targets and feeds foveated DoF (`engine/03-input-peripherals.md`).
  GTOM is for in-flight target resolution / rendering, head-look is for menu
  selection; they are distinct.
- The **orientation circle** (spatial attitude reference) and the **cockpit**
  shell are documented in `gameplay/01-player-ship-control.md`; here we cover the
  HUD widgets that live on them.
- VR rendering (stereo, forward shading, foveation) is in
  `engine/06-rendering-audio-vr.md`.

## In-flight HUD widgets (E1/E2)

| Class | Role |
|-------|------|
| `AVkHUD` | Root HUD actor; owns/coordinates the in-cockpit widget set. |
| `AVkHoloDisplay` | Cockpit holographic target readout — current target health/shield/overshield. `EVkHoloDisplayElementOptions{Health, Shield, Overshield}`; hooks `UpdateCurrentTarget`, `NotifyPawnKilled`. |
| `AVkRadar` + `AVkDetectionSystem` | 3D radar / contact display. `AVkDetectionSystem` is the sensor/detection model feeding the radar. `EVkRadarObjectStates{Vehicle, Missile, Important, Disabled}` classify a blip; `EVkRadarObjectTransitionStates{TransitionIn, TransitionOut, LoopingAnim, NoAnim, Dead}` animate it. `RadarRange`, `VkRadarStateOptions`/`VkRadarStateTransition`, `VkRadarTrackedObject(Options)`. |
| `AVkObjectMultiTracker` / `UVkObjectMultiTrackerComp` | Tracks a *set* of world objects for HUD display (`TrackedObjects`, `NonVisualTrackedObjects`, `UpdateTrackedObjectState`) — generalized contact tracking the radar/brackets build on. |
| `AVkCompass` | Heading/bearing indicator. |
| `AVkOrientationCircle` (+ `_LocatorBase`, `AVkRespawnMapLocator`) | Attitude/orientation ring with positional **locators** (capture points, base ships, players, respawn map). `AngleBetweenLocators`, `AvailablePlayerLocators`, `CapturePointLocators`, `BaseShipLocators`; `bIsCurrentlyOnOrientationCircle`. (Comfort/UX element; see `gameplay/01-*`.) |
| `AVkMissileWarningDisplay` / `*Base` / `*Instanced` | Incoming-missile warning. `OnMissileWarningStarted/Range/Ended`. The `Instanced` variant is the InstancedStereo-friendly draw path. |
| `AVkBoxStatusBar` | Generic status/health bar element (`OnRepair`). |
| `AVkKillAssistDisplay` (+ `*Base`) | Kill/assist feedback popups. |
| `AVkDeployableHUD` | HUD for deployable pickups/items (`NotifyItemPickedUp`, `NotifyItemExpired`). |
| `AVkSpiderbotsUI` | HUD readout for the Spiderbots ability/deployable. |
| `AVkUpgradeUI` (`UVkUpgradeUI`) | In-cockpit upgrade/loadout icon meshes (`SetupIconMeshes`, mounted to cockpit sockets). |
| `AVkAbilityHUDItem` | Per-ability cockpit indicator (cooldown/charge), under `Private/Cockpit/`. |
| `AVkTacticalMap`, `AVkCloneVatUI`, `AVkCloneVat{Pilots,Ship}Manager`, `AVkCloneVatWaveTimer`, `AVkCloneVatPawn` | Larger "screen"-style world UI: the **clone-vat** spawn/results theatre and tactical map. `EVkCloneVatScreenType{EndOfMatch, KillCam, …}`, `EVkCloneVateShipState{Inbound, Outbound, Present, NotPresent, …}`. Receives remote player state/gender/skin/team. |

### Targeting brackets & crosshair (E1/E2)

3D markers anchored to world objects (targets, lock zones, capture points).

| Class | Role |
|-------|------|
| `VkUIBracketComponent` | Base **world-space bracket** widget attached to a tracked object. `EVkUIBracketElementType`, `EVkUIBracketStates` drive element/state; `GetUIBracketComponent`, `CachedUIBracketComponent`, `BracketComponentClass`. |
| `VkTargetLockBracketComponent` | The target-lock reticle bracket. `OnTargetLockAcquired/Changed/Lost`; `CachedTargetLock`. |
| `VkTargetLeadingBracketComponent` (+ `VkTargetLeadingComponent`) | Lead-pip ("shoot ahead of a moving target") bracket. `AddTargetLeadingElement`. |
| `VkMissileLockBracketComponent` | Missile-lock-on bracket. `EVkMissileLockAvailability{Unavailable, Unlocked, Locked}`; `MissileLockConfig`, `MissileLockSpinRate`, `MissileLockTransitions`, `MissileLockWarning`, `OnMissileLocked`. (`ADEPRECATED_VkMissileLock_UI` is an older retired version.) |
| `VkCapturePointBracketComponent` | Bracket marking objective/capture points. |
| `AVkCrosshair` (+ `UVkCrosshairAnimComponent`) | The aiming crosshair. `EVkCrosshairMeshState` is a rich state enum: `CurrentlyFiring`, `ChargeValue`, `HeatValue`, `SpreadValue`, `LockValue`, `HitIndicator`, `EstimatedTimeUntilNextShot`, plus shield/capacitor drain-or-repair states (`CanDrainShield`, `CanRepairCapacitor`, `Draining`, `Repairing`, …). |
| `AVkLockOnBeamCrosshair`, `AVkMissileCrosshair` | Weapon-specific crosshair variants (lock-on beam, missiles). |

The bracket/leading/lock widgets are tightly coupled to the combat & weapon
systems (`02-combat.md`). Note: **all** `Vk*Bracket*` symbols here are HUD
reticles/markers — `VkBracketEditorActor` is a design-time **HUD-layout** actor
and `FVkBracketElementStructType` is a HUD element-type tag (verified in
`07-brackets.md`). There is **no** tournament/competition-bracket system in this
title; competitive structure is leagues/leaderboards (`networking/11`, `14`).

## Smart pings / comms (E1/E2) — the networked UI element

The only UI subsystem that crosses the network. Players issue contextual "smart
pings" (a comms/quick-chat wheel) that replicate to teammates.

| Class | Role |
|-------|------|
| `AVkPingManager` | Server-side ping orchestrator. RPCs: `ServerSendSmartPing` (+ `_Validate`), `ClientRecieveSmartPing`, `Multicast_OnPing_*`. |
| `UVkSmartPingData`, `IVkSmartPingInterface`, `VkSmartPing(Info)`, `VkSmartPingAnimInfo`, `VkBracketSmartPing` | Ping data/interface, the world marker, its anim, and a bracket-attached ping. |
| `EVkSmartPingType{Attack, Defend, Danger, AssistMe}` | The ping vocabulary (the comms wheel options). |

Because pings are server-validated RPCs (`ServerSend…_Validate`) they ride the
gameplay replication channel — cross-ref `networking/08-gameplay-replication.md`.
A preservation **server** must relay/validate these; everything else in this doc
the server can ignore. Default ping assets live at
`/Game/UI/SmartPings/Default_SmartPings`.

## Front-end VR UI: the head-look scene framework (E1/E2)

The menus are a 3D environment the player browses by **looking** at objects. The
core is the **Head-Selectable Object Group (HSOG)** pattern: a group owns
selectable 3D objects; the player's head/look ray hits one, it glows, and a
confirm input selects it.

### Interaction core

| Class / symbol | Role |
|----------------|------|
| `AVkVrUiHeadSelectableObjectGroup` (`HeadLookGroup`, `SelectableObjectGroupClass`) | A group of head-selectable 3D objects; performs the `HeadSelectionTrace` (look ray) and manages focus. |
| `IVkVrUiHeadSelectableObjectGroupCommunicationInterface` | The selection event protocol between group and elements: `LookAt_FromGroup`, `LookAway_FromGroup`, `Selection_FromGroup`, `Selection_FromElement`, `MouseDown_FromElement`, `AdvanceRequest_FromGroup`. |
| `AVkFrontEndHeadSelectableObject`, `AVkFrontEndHeadSelectSpot`, `UVkFrontEndHeadSelectableComponent(_Mesh)`, `UVkVrUiHeadSelectableAssistComponent` | The selectable objects/spots and their components; the *Assist* component aids selection (snap/dwell help). `GetHeadSelectSpot`. |
| `EVkHeadSelectableGlowType{Material, SphereGlow, Transitional}`, `VkHeadSelectableGlowOptions`, `GlowType` | Visual feedback styles when an object is looked-at. |
| `AVkVrUiHSOG_SelectionWheelPrompt`, `AVkVrUiScene_SelectionWheelWithInfoHSOG` | The **selection wheel** (radial menu) — `MenuSelectionWheel`, `MenuRotateSelectionWheel`, `SelectionWheelLeft/Right` (the closest thing to a classic radial menu, used for menu choices). |

Head-look here is distinct from the in-flight `LookInput` (HMD look that aims the
ship; `SetIgnoreLookInput`/`ClientIgnoreLookInput`/`bNewLookInput`) and from
Tobii gaze (target scoring/DoF). All three are local input channels feeding
different consumers.

### Scenes & the scene manager

| Class / symbol | Role |
|----------------|------|
| `AVkVrUiSceneBase` (+ `AVkVrUiDecorationSceneBase`, `VkVrUiSceneBaseAsyncAsset`) | Base for a UI "scene" (a screen/state of the 3D menu); `OnStartupPhaseChanged`; assets stream async. |
| `VkVrUiSceneManager` / `VkVrUiSceneManager_HUB` | Scene stack/navigation. The **HUB** manager is the main hangar / "Proving Grounds" home (`…_HUB_ProvingGrounds{Body,Context,Launch,Title}`). `ActiveScene`, `OnSceneTransition_Manager`, `OnSceneTransitionFailed_Manager`. |
| `UVkVrUiSceneTransition` (`VkHoloSceneTransition`) | Animated transitions between scenes. |
| `EVkVrUiJumpSceneType{Forward, Backward, Insert}` | Navigation direction in the scene stack. |
| `EVkVrUiAnchorPoint{TopLeft … CentreCentre … BottomRight}` | World-space anchor for positioning UI elements around the player. |
| `EVkVrUiQuitType{RETURN_TO_MAIN_MENU, FORCE_RETURN_TO_MAIN_MENU, RELOGIN, QUIT_GAME, FORCE_QUIT}` | Quit/exit flow outcomes. |
| `UVkVrUiVehicleMeshComponent` | Renders the player's **ship** as a 3D preview in front-end scenes (loadout/customisation). |

### Concrete scenes / HSOGs (representative, E1/E2)

The `VkVrUiScene_*` and `AVkVrUiHSOG_*` families implement each menu. Examples:

- **Onboarding / auth:** `VkVrUiScene_Login`, `VkVrUiScene_EULA`,
  `VkVrUiScene_Marketing`, `VkVrUiScene_GenderSelect`.
- **Hangar / progression:** `VkVrUiScene_HeroUpgradeTree` (+
  `VkVrUiHSOG_HeroUpgradeNode_{Base,StartNode,EndNode}`), `VkVrUiScene_Boosters`,
  `VkVrUiScene_Quartermaster`, `VkVrUiScene_ExteriorCustomisation`,
  `AVkVrUiHSOG_PilotCustomisation_*`, `AVkVrUiHSOG_LoadoutData`/`ShipInfo`.
- **Matchmaking / social:** `VkVrUiHSOG_JoinSession`, `VkVrUiScene_Squad`,
  `AVkVrUiHSOG_CustomMatch_*` (lobby/host/spectator), `AVkVrUiHSOG_MatchSetup`,
  `AVkVrUiHSOG_NextBattlePreview`, `AVkVrUiHSOG_DailyChallenge*`.
- **Rewards / results:** `VkVrUiScene_Results`, `VkVrUiScene_LootOpening`,
  `AVkVrUiHSOG_ResultsScreen*`, `AVkVrUiHSOG_Rewards_AnimatingBar*`.
- **PvE / minigame:** `VkVrUiScene_PVE_ModeDisplay_NPE`, `VkVrUiScene_ShipHunt`,
  `AVkVrUiHSOG_SurvivalLeaderboard`, `AVkVrUiHSOG_Wormhole_*`.
- **Misc:** `VkVrUiScene_QuitConfirm`, `AVkVrUiHSOG_ControlPrompt`,
  `AVkVrUiHSOG_SettingsOption`, `AVkVrUiHSOG_CAT_Popup`.

Several `ADEPRECATED_VkVrUiScene_Settings_*` (GamepadSetup, JoystickSelector,
KeyBinding) are retired earlier settings screens — historical.

### UI ↔ backend bridge: `AVkUIGameState` (E1/E2)

`AVkUIGameState` is the glue between the front-end UI and the
backend/matchmaking/session layer — it drives what the hangar shows and triggers
joining a battle.

- `HandleBackendDataChange` reacts to backend data updates (progression,
  currency, inventory) so the front-end reflects server state.
- `LoadServerMap()` performs the map transition into a battle (creates/compares
  the `MapLoader` URL).
- `EVkUIGameStateConnectionState{Idle, IdleSquadMember, FindingSession,
  FoundSession, BattleFound, ConnectingToServer, WaitingForRunningBattle,
  JoiningCarousel, MapTransition, CustomSession, ConnectionFailed, Quitting}` —
  the front-end's view of the connect/matchmaking flow.

This is where the UI meets the networking docs: matchmaking/beacons
(`networking/06-*`), session lifecycle (`networking/09-*`), battle-server launch
(`networking/05-*`), and progression/economy (`networking/11-*`).

## Re-implementation / preservation relevance

- **Mostly client-local.** The HUD, brackets, crosshair, orientation circle, and
  the entire `VkVrUi*` front-end render from replicated/local state and need
  **no** server support — a preservation client runs them as shipped.
- **Two real touch-points for a server:**
  1. **Smart pings** — `ServerSendSmartPing`(`_Validate`) → `Multicast_OnPing_*`
     / `ClientRecieveSmartPing` must be relayed/validated like any gameplay RPC
     (`networking/08-*`).
  2. **`AVkUIGameState`** consumes backend data (`HandleBackendDataChange`) and
     the matchmaking/session flow; its connection-state machine must be satisfied
     by the re-implemented backend (`networking/06-*`, `09-*`) and battle launch
     (`networking/05-*`) for the front-end to leave the hangar and enter a match.
- Otherwise the VR UI is **architecture, not asset RE** — the visuals/meshes/
  animations live in the `.pak` and are out of scope.

## Open questions

- Exact head-look selection tuning (dwell time / trace cone / assist snap
  behavior of `UVkVrUiHeadSelectableAssistComponent`) — not exposed as plain
  strings; would need disassembly of the group's trace routine.
- Whether the radar's contact set is purely a client view of replicated actors or
  also fed by the server-side `AVkDetectionSystem` (sensor model) — confirm at
  runtime; affects whether stealth/detection is server-authoritative.
- `EVkUIBracketElementType` / `EVkUIBracketStates` member names (the enum exists
  but members weren't recoverable from strings) — confirm by disassembly if the
  bracket state machine matters for re-impl.
- Precise division of in-flight `LookInput` (ship aim) vs Tobii gaze vs head-look
  selection at the input-routing layer — partially in `engine/03-*`; the in-cockpit
  combination is worth a focused pass.
