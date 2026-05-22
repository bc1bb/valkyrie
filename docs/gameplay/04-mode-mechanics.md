---
doc: gameplay-mode-mechanics
title: Game-Mode Mechanics
summary: The in-match objective systems that implement the modes in 04-game-modes.md — capture points, carrier/base-ship assault, relics, the clone-vat respawn pool, teams, the per-mode AVkGameMode/GameState classes, sub-level objective sets, warp gates, and the win-condition/scoring tie-in.
keywords: [capture point, carrier, base ship, cooling node, hit point, relic, pursuit, extraction, clone vat, respawn, team, sublevel, warp gate, wormhole, virus, survival, objective, mining, win condition, game mode settings]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E3]
---

# Game-Mode Mechanics

`engine/04-game-modes.md` enumerates the mode *names* (`EVkGameModeType` /
`EVkGameModeSubLevels`). This doc covers the **objects that implement** those
modes — the actors, components, enums and game-mode classes the server runs
during a match. All identifiers are embedded class/enum/field-name symbols
recovered from the binary (E1; enum value lists E2). Backend tunables are
cross-referenced from `networking/14-vgs-api-surface.md` (`game_mode_settings`,
E3). Cross-refs: scoring taxonomy lives in `gameplay/01-player-ship-control.md`;
session/match-config plumbing in `networking/14-*` and `networking/13-*`.

## Game-mode / game-state class hierarchy (E1)

Each mode is an `AVkGameMode_*` subclass (server-authoritative rules engine),
usually paired with an `AVkGameState_*` (replicated match state) and a HUD
"panel" actor (`AVk*Panel`) that shows mode-specific status.

| Class | Mode it implements (`EVkGameModeType`) |
|-------|----------------------------------------|
| `AVkGameModeBase` → `AVkGameMode` | Common base (match lifecycle, teams, scoring). |
| `AVkGameMode_Control` | `Control` / `Control_SinglePoint` — capture & hold point(s). |
| `AVkGameMode_Armada` (+ `_Chronicle`) | `Armada` / `Base*` — carrier (base-ship) assault. |
| `AVkGameMode_Bomb` | `Bomb` — has `WinningTeamSetCallback`. |
| `AVkGameMode_Bounty` (+ `_Bounty`) | `Bounty` — target-kill. |
| `AVkGameMode_Pursuit` | `Extraction` — relic carry/deliver (see Relics). |
| `AVkGameMode_Virus` | `Virus` — infection tag. |
| `AVkGameMode_PvE_WavesOfAI` | `Survival` — survive escalating AI waves. |
| `AVkGameMode_LimitedRespawns` | finite clone pool variant (TDM/Control with clone budget). |
| `AVkGameMode_HighestScore` / `AVkGameMode_Maelstrom` / `AVkGameMode_Playground` | score-rush / sandbox variants. |
| `AVkGameMode_Challenge` | time-trial / objective challenge (`EVkChallengeMode*`, `engine/04-*`). |
| `AVkGameMode_NPE2_*`, `_Prologue`, `_Holodeck`, `_NPE_TestArena` | tutorial / narrative (standalone). |
| `AVkGameMode_GameLift` | dedicated-server (AWS GameLift) wrapper. |

Match-state classes: `AVkGameState` (base) and specializations
`AVkGameState_Armada`, `AVkGameState_Pursuit`, `AVkGameState_Challenge`,
`AVkGameState_PvEBase`, `AVkGameState_PvE_WavesOfAI`, `AVkGameState_Matinee`.
Common fields: `bMatchEnded`/`bHasMatchEnded`, `GetResultsWinningTeam`,
team-score replication (`OnRep_TeamScores`, `MyTeamScore`/`EnemyTeamScore`).

## Teams & ownership (E1)

- `EVkTeam` (small fixed team enum, `EVkTeam_MAX`); team identity is a
  `GenericTeamId` (`ForceTeamNum`, `DefaultTeamIDInEditor`,
  `bUseTeamNumberBalancing`, `ChooseTeamForController`).
- `ETeamAttitude` { `Friendly`, `Hostile`, `Neutral` } — relationship test
  between actors (drives targeting, friendly-fire, HUD colour).
- **`IVkTeamOwnerInterface`** — `GetOwningTeamID` / `SetOwningTeamID`. The
  generic "which team controls this object" contract, implemented by capture
  points, turrets and base ships. Capturable objects replicate ownership via
  `OwningTeamId` + `OnRep_OwningTeamIdChanged` / `OnRep_OwningTeamChanged`, with
  `InitialOwningTeamId` and `CachedOwningTeamID`.
- `VkPlayerState` carries the player's team and per-team saved scores
  (`GetSavedScoreTeamIDForIndex`); `AVkPlayerController::OnTeamIDUpdated` reacts
  to team assignment.

## Capture points (Control; "Mines" maps) (E1)

Implemented by `AVkCapturePointBase` / `AVkCapturePointActor`, managed by
`UVkCapturePointManager` (+ a `_TimedLock` variant) and surfaced through
`CapturePointHUD` / `CapturePointIndicator`. A point is a `TeamOwnerInterface`
object whose ownership shifts based on which team's actors are inside it.

Capture-detection is pluggable via a component family
(`UVkCapturePointComponentBase` and subclasses):

| Component | Capture trigger |
|-----------|-----------------|
| `UVkCapturePointComponent_PlayerProximity` | player ships within radius. |
| `UVkCapturePointComponent_DroneProximity` | drones within radius. |
| `UVkCapturePointComponentBase_NumActors` | count of contesting actors (`NumActors`). |
| `UVkCapturePointComponent_Dummy` | inert / placeholder. |
| `UDEPRECATED_VkDockableCapturePointComponent` | legacy "dock to capture" (deprecated). |

Core capture loop (method/field symbols):
- `EPlayerCaptureState` { `None`, `Capturing`, `Defending` } — per-player role
  at a point.
- Contest tracking: `ContestingActors` / `PreviousContestingActors`,
  `UpdateAllContestingActors`, `IsActorContesting`, and per-team tallies
  `NumContestingActors_Team0` / `_Team1`.
- Rate & geometry: `GetNewCaptureRate` computes capture speed from the contesting
  tally (what the backend `capture_speed` / `MatchSettings_CA_CaptureSpeed`
  scales); `CaptureDistanceMetres` / `CaptureDistanceScale` size the capture
  volume. `bDetectNeutrals` toggles whether non-team actors count.
- **Match timing params (E2):** `RoundTime`/`RoundTimer`/`TimeRemaining` (round
  clock), `RespawnTime` (clone-vat respawn delay). Values are balance/pak;
  `RoundTimer`/`ClonesPerTeam` map to `MatchSettings_*` (`networking/14`).
- Outcome events: `OnCapturePointCaptured`, `AllCapturePointsOwnedAudio` /
  `AllCapturePointsLostAudio`, plus the scoring hooks
  `VkPlayerScoreObjective_Capture` (instant capture) and
  `_CapturePointScoreTicker` (per-tick hold income, event
  `EVkPlayerScoreEvent::CapturePointScoreTick`).

The `Mines_SingleCapturePoint` vs `Mines_ThreeCapturePoints` sub-levels (E2) are
the same machinery composited with one vs three capture-point actors.

## Carrier / base-ship assault (Armada, Base, Base_PVP) (E1)

The "carrier assault" objective is a destructible team **base ship**
(`AVkTeamBaseShip`, `BaseShipData`); destroying the enemy's wins the match. A
mode opts into this with `bGameModeUsesCarrierHealth` /
`bUseCarrierHealthForEOM` (end-of-match driven by carrier health).

Damage model — a carrier exposes addressable sub-targets (`AVkHitPoint`,
`AVkHitPoint::OnHealthChanged`, `bHitPointDamageable`):
- **Cooling nodes** — outer targets (`CoolingNodeBracket`, `CoolingNodesRemaining`,
  backend `cooling_node_health` / `MatchSettings_CA_CoolingNodeHealth`).
- **Critical hit point / core** (`CriticalHitPoint`, `CarrierCoreDamage`,
  `CarrierNodeDamage`) — the vulnerable core revealed after nodes fall.
- **Outer shields** — gated by a downtime window (`shield_down_time` /
  `ShieldDownTime` / `MatchSettings_CA_CarrierShieldDowntime`;
  `UVkCarrierShieldDrainEffect`; `EVkTeamBaseShipShieldState` { `Active`,
  `Draining`, `Deactivated` }).
- **Sentry turrets** — `MatchSettings_CA_CarrierTurrets` (backend
  `turrets_enabled`); turrets are themselves team-owned
  (`OnTurretOwningTeamChanged`).

The progression is an explicit state machine, **`EArmadaState`**:
`WAITING_FOR_GAME_TO_START` → `OUTER_SHIELDS_ENABLED` → `SENTRYGUNS_EXPOSED` →
`HITPOINTS_EXPOSED` → `CRITICAL_HITPOINT_IDENTIFIED` →
`CRITICAL_HITPOINT_DESTROYED` → `CARRIER_DESTROYED` → `DESTRUCTION_COMPLETE`
(`CurrentArmadaState`; HUD bar `EArmadaBarState` { `None`, `HitPoints`, `Core`,
`Dead` }). `AVkGameMode_Armada_Chronicle::TriggerEndOfMatch` ends the match when
a team's carrier is destroyed (logs a warning if called before either falls).
`CarrierHealthPercentToStopLogin` stops clone-vat respawns once a carrier is
near death. Scoring tie-in: `VkPlayerScoreObjective_CarrierDefence`,
`_CarrierDestroyed`, `_CriticalHitPointDestroyed`, `_HitPointDestroyed` /
`_HitPointAssist` (and backend `Score_CarrierNodeDamage` / `Score_CarrierCoreDamage`,
`carrier_kills`/`node_kills`).

## Relics — Extraction / Pursuit (E1)

`AVkGameMode_Pursuit` (state `AVkGameState_Pursuit`) implements the carry-the-relic
objective. A relic is a pickup that ships grab, carry, and deliver:
- Actors: `AVkRelicSpawner`, `AVkRelicPickup`, `AVkRelicDropLocation`,
  `AVkAIScriptedRelicDropPath` (scripted AI drop route).
- Holder tracking: `RelicHolder(s)`, `OnRep_RelicHolders`,
  `OnRelicHolderChanged`. Carrying a relic penalises the ship
  (`RelicHolderEnergyUseMultiplier`) and tags it (`RelicHolderShipTrail`).
- Lifecycle events (`AVkGameMode_Pursuit`): `OnRelicPickedUpBy`,
  `OnRelicDroppedBy`, `OnRelicExpired`, plus `SpawnFirstRelic` /
  `SpawnNewRelicFrom` and `UpdateRelicGameModeActors` (rebinds spawners↔drop
  locations). `AVkRelicSpawner::OnRelicHolderDied` re-drops on carrier death;
  `bDropPickupOnBeginPlay`, `bOnlyDropPickupsFromOtherTeamKills` configure drops.
- `EVkRelicDistanceCategory` { `Short`, `Medium`, `Long` } classifies relic
  distance (HUD/AI). Dynamic-music states `Extraction{Friendly,Enemy}HasRelic`.
- Win/score: backed by `goals_to_win` / `MatchSettings_Extraction_GoalsToWin`
  (deliveries needed). Scoring: `VkPlayerScoreObjective_PickupRelic`,
  `_Harvest` (event `EVkPlayerScoreEvent::Harvest`), and `_CaptureRelicScore` /
  "Delivered The Relic". Related mining objects (`AVkMiningLaser`,
  `AVkMiningTurretTarget`, `EVkAIBehaviourState::Mining`) feed the Harvest path.

## Clone-vat respawn system (E1)

A pilot is a **clone**; respawning launches a new clone ship from the team's
"clone vat", which is also the between-lives spectator/UI space. This is the
respawn-pool mechanic (the backend `clones_per_team` is the team's clone budget;
`AVkGameMode_LimitedRespawns` enforces a finite pool — cf.
`MatchSettings_Control_ClonesPerTeam` / `MatchSettings_TDM_ClonesPerTeam`).

- Actors/managers: `AVkCloneVatPawn`, `AVkCloneVatPilotsManager` (syncs remote
  pilots' gender/skin/state/team into the vat — `ReceivedRemote*`),
  `AVkCloneVatShipManager`, `AVkCloneVatWaveTimer` (spawn-wave cadence),
  `AVkCloneVatUI` (`OnSpawned`, `OnMatchEnded`).
- Ship spawn state `EVkCloneVateShipState` { `NotPresent`, `Inbound`, `Present`,
  `Outbound`, `NotSet` } — animates a clone ship arriving in / leaving the vat.
- Vat UI screens `EVkCloneVatScreenType` { `ShipSelect`, `KillCam`,
  `TacticalMap`, `PauseScreen`, `EndOfMatch` } — what the dead/spawning player
  sees. `CloneVatLaunchAllowed` gates whether launch is permitted (e.g.
  suppressed by `CarrierHealthPercentToStopLogin`, end-of-match).
- Scoring tie-in: `VkPlayerScoreObjective_SpawnInShip` (launching from the vat).
  "LostBattleWith1CloneLeft" indicates clone count as a tiebreaker/telemetry.

## Virus (infection) (E1)

`AVkGameMode_Virus` (state surfaced via `AVkPlayerState_Virus`,
`AVkVirusPanel`). A subset of players spawn infected (`InitialVirusCarriers`);
the virus spreads on contact and is the "it" tag. Players manage an antidote
(`OnPlayerAntidoteDepleted`); objective locations are `AVkVirusObjectiveLocation`
(`UpdateObjectiveActors`). Infected-AI behaviour uses
`UVkAIBehaviourComponent_Virus` / `UVkAIChooseTargetComponent_Virus`. End-states
(dynamic music): `VirusEndOfMatchAllInfected`, `…FailToInfectAll`, `…Survived`.
Scoring: `VkPlayerScoreObjective_SpawnWithVirus` / `_SpawnWithoutVirus` /
`_AvoidVirus`. Sub-level objective set `EVkGameModeSubLevels::VirusObjectives`.

## Survival — waves of AI (E1)

`AVkGameMode_PvE_WavesOfAI` / `AVkGameState_PvE_WavesOfAI` run escalating AI
waves ("Triggering Next Wave: %d"; `AddAIVehicleToNextWave`,
`AVkCloneVatWaveTimer`). Progress is tracked as a wave count
(`ReachedSurvivalWave`; backend `wave`/`wave_reached`, `hero_survival`
leaderboards in `networking/14-*`). `bSurvival_IsProMode` is a difficulty toggle
(cf. `ai_difficulty`/`num_ai_per_team`). PvE/standalone — minimal backend (see
`engine/04-*` mode→backend-need split).

## Warp gates / wormholes (E1)

`AVkWarpGate` is a trigger volume (`BeginTriggerOverlap` / `EndTriggerOverlap`)
applying `VkWarpGateEngineModifiers` to a ship that enters — i.e. a
traversal/boost portal used by maps and the `WarpGates` sub-level. Distinct from
the **wormhole** *session* concept (`bWormholeSession` / `bIsWormholeVersion`,
`sessiontype.wormhole`, `wormhole_leaderboard`): a wormhole is a special
session/event type (a rotating PvE encounter with its own leaderboard) rather
than an in-match objective. The warp-gate actor may appear inside such sessions
but is a generic map element.

## Win conditions & match settings (E1 + E3)

Modes resolve a winner one of three ways, all converging on
`GetResultsWinningTeam` / `bMatchEnded`:

| Mechanism | Driven by |
|-----------|-----------|
| Score/goal limit | `goals_to_win`, `GetTargetScore`/`GetTeamScore`, `bEndAtMaxScore` (e.g. Extraction deliveries, Control hold-score). |
| Objective destroyed | carrier health (`bUseCarrierHealthForEOM`, `EArmadaState::CARRIER_DESTROYED`). |
| Timer expiry | `RoundTimer` (`MatchSettings_Control_RoundTimer` / `…_TDM_RoundTimer`); team with higher score at time-out wins. |

The custom-match `game_mode_settings` block (`networking/14-*`, E3) maps 1:1 to
these in-match tunables. Recovered UI labels (`FVKVrUi_MatchSettings_*`,
element types `TOGGLE`/`NUMBER`/`PERCENT`/`DURATION`/`LIST`) confirm the binding:

| Backend field (`game_mode_settings`) | In-match meaning | Mode label |
|--------------------------------------|------------------|------------|
| `capture_speed` | capture-rate scalar (`GetNewCaptureRate`) | `MatchSettings_CA_CaptureSpeed` |
| `cooling_node_health` | carrier node HP | `MatchSettings_CA_CoolingNodeHealth` |
| `shield_down_time` | carrier shield-down window | `MatchSettings_CA_CarrierShieldDowntime` |
| `turrets_enabled` | carrier sentry turrets on/off | `MatchSettings_CA_CarrierTurrets` |
| `clones_per_team` | respawn-pool size | `MatchSettings_{Control,TDM}_ClonesPerTeam` |
| `goals_to_win` | deliveries/score to win | `MatchSettings_Extraction_GoalsToWin` |
| `num_ai_per_team`, `ai_difficulty` | AI count / difficulty | (Survival/PvE, `bSurvival_IsProMode`) |
| `disable_shields`, `no_radar`, `friendly_fire`, `no_ultimates`, `no_mods` | global rule toggles | `CustomMatchSettings_Option{Enabled,Disabled}` |

## Challenges (client objective tracking)

Challenges are meta objectives ("do X for a reward"), distinct from match win
conditions. Client side: `VkChallengeObjective` tracks progress against criteria
`EVkChallengeModeSuccessCriteria` (AllObjectivesCompleted / AllTagged… /
AnyTagged…) and `EVkChallengeModeTimerStartCondition` (OnLaunchFinished /
OnAnyObjectiveCompleted / OnTaggedObjectiveCompleted) — see `engine/04-*`.
Definitions/progress/rewards come from the backend `challenges` resource
(`networking/14-*`: `challenge_id`/`name`/`difficulty_name`/`progress`/`rewards`/
objective `max_*` thresholds). A re-impl backend serves challenge definitions
and accepts progress/completion; the client evaluates criteria locally.

## Re-implementation relevance

- **All of this is server-side** and ships in the game binary; a re-implemented
  **backend does not run these mechanics**. The backend's only contract is to
  (a) carry the `game_mode_settings` block when creating/allocating a session
  (`networking/14-*`) and pass it to the battle server via the launch args
  (`networking/05-*`), and (b) accept the resulting match-result report
  (`networking/13-*`). The table above is the authoritative key→meaning map a
  backend needs to round-trip those settings correctly.
- A re-implemented **dedicated server** (or single binary) does run them; this
  doc is the structural map of the systems it must instantiate per mode
  (game-mode class + state + objective actors + clone-vat + team ownership).
- PvE modes (`Survival`, `Virus` PvE, `NPE_*`, narrative) are largely
  standalone — minimal/no backend, consistent with `engine/04-*`.

## Open questions

- Exact numeric defaults/ranges for each `game_mode_settings` value (balance
  data; lives in the pak — out of scope, asset RE).
- Whether `Bomb`/`Bounty`/`Maelstrom`/`HighestScore` carry their own
  `MatchSettings_*` keys beyond the shared toggles (only CA/Control/TDM/Extraction
  match-setting labels were recovered).
- The constructor-anchor recovery tool returns no ordered field list for these
  classes (anchors resolve to vtable/RTTI sites, 0 parsed fields), so per-class
  field *offsets/order* are unconfirmed — only the symbol names above are
  evidenced. Field order would need targeted disassembly (E3) or `.uasset`
  reflection data.
- Relic↔mining relationship: `Harvest` scoring and `AVkMiningLaser` suggest a
  mining/harvest variant feeding Extraction; the precise mode mapping is
  unconfirmed.
