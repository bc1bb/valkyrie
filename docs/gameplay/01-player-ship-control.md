---
doc: gameplay-player-ship
title: Player / Ship Control & Scoring
summary: How a player flies a ship — VkPlayerController/VkPawn/VkVehicle + movement components (flight model), cockpit, carrier launch, orientation; plus the full VkPlayerScoreObjective_* scoring-event taxonomy.
keywords: [player, ship, vehicle, pawn, controller, movement, flight, cockpit, launch tube, orientation, scoring, score objective, killstreak, capture]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Player / Ship Control & Scoring

The core "fly a ship" loop. Server-authoritative (`networking/08-*`); the client
predicts and the server corrects (engine-stock + Vk RPCs).

## Control & pawn hierarchy (E1)

| Class | Role |
|-------|------|
| `VkPlayerControllerBase` → `VkPlayerController` | Player input → ship control; possesses the pawn. |
| `VkPawn` | Base pawn. |
| `VkVehicle` | The flyable ship pawn (a "vehicle"). |
| `VkVehicleBaseMovementComponent` / `VkVehicleNewMovementComponent` | Flight model / movement physics (two generations — "New" likely the shipped 6-DoF space-flight model; "Base" the predecessor). |
| `VkVehicleShield` | Per-ship shield (regenerating health layer). |
| `VkVehicleUpgradeData` | Per-ship upgrade/loadout data (cf. backend `hero_upgrades`, `networking/11-*`). |
| `VkPlayerState` | Replicated per-player state (score, team, etc.). |
| `VkPlayerStart` | Spawn point. |

Input comes from gamepad / VR controllers / HOTAS (`engine/03-input-peripherals.md`):
the controller maps axes (pitch/roll/yaw/throttle) into the movement component.

## Flight model — parameters (E2)

The 6-DoF flight model's **tunable parameter set** (property names recovered;
the float *values* are balance data in the pak, out of scope). This describes
*how* the model works:

- **Linear:** `BaseSpeed`/`BaseSpeedUU`, `AccelerationRate`/`Acceleration`
  (+ `AccelerationDifferenceTriggerAmount`). Speed-based, accelerates toward a
  target speed.
- **Rotation = torque-based with curves & constraints:** per-axis `Pitch`/`Yaw`/
  `Roll` with `…MaximumTorque`, `…InterpCurve`/`…Curve`, `…Constraints`
  (`PitchMax`/`PitchMin` clamp), `…AggressivenessPercentage`, `…Modulation`,
  `…Invert` (invert option), `BaseTurnRate`, `AngularVelocity(Strength/Target)`.
  So input drives torque through a response curve toward an angular-velocity
  target, clamped to per-axis limits.
- **Boost:** `BoostThrust`/`BoostSpeed`, `BoostEnergyUsagePerSecond`,
  `BoostTime`/`BoostPercentage` — a timed speed/thrust burst drawing Energy.
- **Brake:** `BrakeForceMaxScalar`, `BrakeAggressivenessPercentage`,
  `BrakeEnergyUsagePerSecond`, `BrakeCooldownSeconds` — energy-gated, cooldowned.
- **Energy pool (`EnergyComponent`):** a shared resource —
  `EnergyRechargeAmountPerSecond`, `EnergyUsePerSecond`/`EnergyUseOnActivate`/
  `EnergyRequired` — that **gates boost, brake, and abilities** (the `Energy`
  replicated property, `08-*`; abilities in `gameplay/03`).
- **Assist:** `DriftCorrection`/`DriftCorrectionPercentage` (auto drift-correct).

This is an arcade-leaning 6-DoF model: curve-shaped torque rotation with clamps,
a unified Energy budget for boost/brake/abilities, and drift assist. A re-impl
server (same engine) runs it; the balance *values* live in the pak.

## Cockpit & launch (E1)

- `VkCockpit` / `VkCockpitItem` / `VkCockpitAssetGroup` — the in-ship cockpit
  (VR-rendered instruments/UI attached to the ship; gaze/Tobii interacts, `03-*`).
- `VkLaunchTube` / `VkLaunchTubeMeshActor` — the **carrier launch sequence** (the
  signature "launch from the carrier tube" intro to a life/spawn).
- `VkOrientationCircle` (+ `_LocatorBase`) — the spatial orientation indicator
  (horizon/attitude reference in 360° space; a key VR-comfort/UX element).
- `VkWarpGate` — warp-gate actor (map traversal / mode element).

## Camera / view modes (E1/E2)

- **View modes** `EVkViewMode` = **FirstPerson** (in-cockpit, the default VR
  view), **ThirdPerson** (external chase), **Both** — toggled by
  `EVR_ToggleCameraMode` (`engine/03-*`).
- **Cameras:** `AVkPlayerCamera` (+ `UVkCameraComponent`) the gameplay camera;
  `AVkVrUiPlayerCamera` the front-end/hangar camera (`gameplay/13`);
  `UVkSpectatorModeCamera` spectating (`gameplay/09`); `AVkFlyCameraController`
  a free-fly/debug cam; `VkCameraLight` a camera-attached light.
- **Death cam / killcam:** `AVkDeathCamera` + `AVkKillerShipViewerUI` show your
  killer's ship on death — a **live** "who killed you" view (not a recorded
  replay; the game has no demo-replay system, `gameplay/09`).

Camera is client-local; the server replicates view-target for spectating
(`networking/08-*` `ServerView*`).

## Scoring system (E1/E2)

`VkPlayerScoreObjectiveManager` drives a large family of
`VkPlayerScoreObjective_*` events — the authoritative list of scorable actions.
These map to the `objective_*`/`Score_*` fields in the match-result report
(`networking/13-*`). Recovered events:

- **Kills/combat:** `Kills`, `FirstBlood`, `Multikill`, `KillStreak`/
  `EndKillStreak`, `Death`/`EndDeathStreak`, `NemesisKill`, `AvengeKill`,
  `NearKillAssist`, `Assist`, `TeamKill`, `DevKill`.
- **Objective/mode:** `Capture`, `PursuitCapture`, `CapturePointScoreTicker`,
  `CarrierDefence`, `CarrierDestroyed`, `CriticalHitPointDestroyed`,
  `HitPointDestroyed`/`HitPointAssist`, `BossShipDestroyed`, `PickupRelic`,
  `Harvest`, `AvoidVirus`/`SpawnWithVirus`.
- **Support/utility:** `Repair`, `EMPSuccess`, `ECMSuccess`, `MWDActivated`,
  `TurretAssist`/`TurretControlKillBonus`/`TurretDestroyed`,
  `DroneDestruction`, `SpiderbotKill`.
- **Lifecycle:** `SpawnInShip`.

This taxonomy defines what the server scores during a match and reports to the
backend (drives rewards, `networking/11-*`).

**Scoring parameters (E2):** each event has a point value (values are balance/
pak): `PointsForBossShip`, `PointsPerRing` (wormhole), `PointsPerSalvage`
(salvage), `ScorePerLoot`, `ScorePerSuccessfulRepair`, `ScorePerSuccess`, plus a
`Multiplier` (streak/bonus scaling) and `PointsRequirement` thresholds. The
server awards these per scored event; totals feed the match-result report
(`networking/13-*`) and rewards.

## Re-implementation / preservation relevance

- A re-implemented **server** runs this logic (it ships in the binary); the
  backend only needs to accept the resulting match-result report (`networking/
  13-*`) and reply with rewards.
- The flight model and cockpit are **client/engine-local**; a preservation
  client runs them as shipped. Only the server-authoritative scoring/validation
  matters for match integrity (`networking/15-*`).

## Open questions

- Exact 6-DoF flight parameters (accel/turn/boost/MWD) — balance values, in the
  pak (out of scope; asset RE).
- Which movement component ships active (`Base` vs `New`) — confirm at runtime.
