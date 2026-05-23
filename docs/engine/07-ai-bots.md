---
doc: engine-ai-bots
title: AI / Bot Subsystem (server-run)
summary: The VkAI* class cluster — server-spawned bots with behaviour states, navigation/formations, targeting, and the full ability/ultimate roster. Configured per match by launch args + session fields; runs on the dedicated server.
keywords: [ai, bots, vkaimanager, behaviour, navigation, formation, ability, ultimate, difficulty, dedicated server, match config, spawn]
status: draft
updated: 2026-05-23
evidence: [E1, E2]
---

# AI / Bot Subsystem (server-run)

EVE Valkyrie has substantial bot AI. It matters to preservation because **bots
run on the dedicated server** (server-authoritative, `08-*`/`15-*`) and are
**configured per match** by the launch args (`05-*`) and session fields
(`14-*`). Documented at the architecture level (class/enum structure); we do not
RE behaviour-tree assets.

## Server/match integration (the networking angle)

The dedicated battle server spawns/manages bots via `VkAIManager`, driven by:
- Launch args (`05-*`): `-NUMAI`, `-NUMAITEAM0/1`, `-AIChars0/1`, `-AIVEHICLE`,
  `-AIABILITY`.
- Session/match fields (`14-*`): `num_ai_per_team`, `clones_per_team`,
  `ai_difficulty`, `ai_pilots`.

So a re-implemented orchestrator fills these to control bot count/skill/loadout;
the server binary does the rest. PvE modes (`Survival`/`Scout`/`Virus`, `engine/
04-*`) are bot-heavy and largely standalone.

## Architecture (class cluster, E1)

| Concern | Classes |
|---------|---------|
| Management | `VkAIManager` (spawn/lifecycle), `VkAIController` (per-bot brain). |
| Behaviour | `VkAIBehaviourComponent`; `EVkAIBehaviourState` = Attacking, Capturing, Defending, Fleeing, Mining, Retreating, Scripted, Wandering; `EVkAIBehaviourStyle` = Attacker, AttackerVehiclesOnly. |
| Targeting | `VkAIChooseTargetComponent`, `VkAITargetPriority`. |
| Navigation | `VkAINavigationSystem`, `VkAINavigationData(Asset)`, `VkAIPathFinder`, `VkAIPathComponent`, `VkAIObstacleAvoidance`, `VkAIScriptedPath`, `VkAIScriptedOrbitPath`. |
| Formations | `VkAIFormationControl`. |
| Combat | `VkAIWeaponsComponent`, `VkAIWeaponData`, `VkAIVehicleHandlingComponent`. |
| Abilities | `VkAIAbilitiesComponent`, `VkAIAbilityControl`, specific `VkAICaptureDroneControl`/`VkAIEMPControl`. |
| Data | `VkAICharactersData` (rosters, cf. `-AIChars`). |

## Ability / ultimate roster (`EVkAIAbilityType`, E2)

Bots (and, by extension, the shared gameplay ability set) use:
`CaptureDrone`, `CounterMeasures`, `EMP_Mines`, `EMS`, `MicroWarpDrive`,
`Mines`, `SpiderBot`, and ultimates `Ultimate_EMP`, `Ultimate_NovaBomb`,
`Ultimate_ShieldStripper`, `Ultimate_OverCharge`. Ability lifecycle
(`EVkAIAbilityState`): `Unarmed → CanDeploy → ShouldDeploy → Deploying →
CoolDown`. (This enumerates the game's ability roster at the type level.)

## Target selection — weighting model (E2)

`VkAIChooseTargetComponent` / `VkAITargetPriority` score candidate targets as a
**weighted sum of bias factors** and pick the best; a deadlock guard prevents
oscillation. Factor names recovered (the float *weights* are balance/pak):

| Factor | Bias |
|--------|------|
| `FavourDamagingTarget` | Stick with a target you're already damaging. |
| `FavourAlreadyLockedTarget` | Hysteresis — prefer the current lock. |
| `FavourAheadTarget` | Prefer targets ahead (in the bot's forward arc). |
| `FavourTeamTarget` | Focus-fire what the team is engaging. |
| `FavourPlayersOverBots` | Prefer human players over other bots. |
| `FavourPlayersAbility` | Bias toward players (e.g. using/threatened by abilities). |

**Deadlock guard:** `PotentialDeadLockTimer` + `DeadLockDetectionTime` detect a
bot flip-flopping between equally-weighted targets and break the tie (the
`DeadLockTarget` log dumps these alongside the Favour weights). So the AI picks a
target by max weighted score, with anti-oscillation. (Engine-local; runs on the
server with the bot logic.)

## Re-implementation relevance

- A re-impl server inherits the bot logic from the shipped binary — no need to
  reimplement AI; just pass the right `num_ai_per_team`/`ai_difficulty`/roster
  config in the session + launch args.
- For PvP-only restoration, bots are optional (set counts to 0). For PvE modes,
  bots are the content — but those are standalone and need minimal backend.

## Out of scope

Behaviour-tree tuning, navigation meshes, and ability balance values are asset/
content (excluded). This doc covers only the code architecture and the
server-config surface.
