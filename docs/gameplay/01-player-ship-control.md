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

## Cockpit & launch (E1)

- `VkCockpit` / `VkCockpitItem` / `VkCockpitAssetGroup` — the in-ship cockpit
  (VR-rendered instruments/UI attached to the ship; gaze/Tobii interacts, `03-*`).
- `VkLaunchTube` / `VkLaunchTubeMeshActor` — the **carrier launch sequence** (the
  signature "launch from the carrier tube" intro to a life/spawn).
- `VkOrientationCircle` (+ `_LocatorBase`) — the spatial orientation indicator
  (horizon/attitude reference in 360° space; a key VR-comfort/UX element).
- `VkWarpGate` — warp-gate actor (map traversal / mode element).

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
