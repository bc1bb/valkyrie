---
doc: net-replication
title: In-Match Gameplay Replication (RPC Surface)
summary: Categorized inventory of replicated RPCs over the WebSocket NetDriver — movement (engine-stock), combat, spectator, match-flow, vehicle, voice. Defines what a re-implemented game server must accept/emit.
keywords: [replication, rpc, server, client, multicast, movement, combat, spectator, vehicle, voice, gameplay, netdriver]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# In-Match Gameplay Replication (RPC Surface)

Once a client is connected to a battle server (Plane 2 WebSocket NetDriver,
`02-websocket-netdriver.md`), gameplay runs on the standard UE4 replication
model: replicated properties + Server/Client/Multicast RPCs. The RPC names below
(E2) describe the gameplay contract. Names with `_Implementation` suffixes are
UE4's generated RPC bodies.

> **Full inventories (reference):** the categorized sample below covers the
> notable RPCs; the **complete** RPC list (~170 Server / ~120 Client / ~10
> Multicast, + the `_Validate` server-validation pattern) is in
> `reference/rpcs.md`, and the full replicated-property + enum indexes are in
> the *Replicated properties* section here and `reference/enums.md`.

## Movement (engine-stock UE4 CharacterMovement, E5)

`ServerMove`, `ServerRotation`, `ServerVelZ`, `ServerBase`, `ServerTimeStamp` /
`ClientTimeStamp`, `ServerTrackPosition`, `ClientAdjustPosition`,
`ClientAdjustRootMotionSourcePosition`. This is UE4's client-predicted movement
with server correction — reusable verbatim from the engine. The server is
authoritative; clients send moves, server acks/corrects.

## Combat

`ServerStartFire`, `ServerStopFire`, `ServerSuicide`,
`ServerToggleWeaponHitCountDebug`. Fire control is server-validated (client
requests fire; server resolves hits — important for a cheat-resistant re-impl).

## Spectator / observer

`ServerViewSelf`, `ServerViewNextPlayer`, `ServerViewPrevPlayer`,
`ServerSpectatorChangeTarget`, `ServerSetSpectatorWaiting`,
`ServerSetSpectatorLocation`, `ServerVerifyViewTarget`, `ServerUpdateCamera`,
`ServerUpdateCameraPOV`. A full spectator camera system is replicated.

## Match flow / readiness

`ServerSetReadyToLaunch`, `ServerShowFloorStart`, `ServerShowFloorEndMatch`,
`ServerShowFloorAIAdd`, `ServerSetStartPointGroupToRespawnAt`,
`ServerUpdateState`, `ServerSetActive`, `ServerSetWantsActive`. The "ShowFloor"
RPCs hint at a demo/kiosk ("show floor") match-flow path alongside normal play.

## Vehicle / ship identity

`ServerSetSelectedVehiclePreview`, `ServerSetVehicleUniqueName`,
`ServerSetPlatformUniqueName`. "Vehicle" = the player's ship; selection/preview
is replicated to the server (loadout enforced server-side).

## Voice

`ServerUnmutePlayer` (and the implied mute counterpart) — UE4 voice mute state
is replicated. Voice itself likely rides the Oculus/Wwise audio path.

## Comms — quick-chat & call-ins (E2)

Team coordination is server-validated and replicated (see
`gameplay/12-tacticalmap-comms.md`):
- `ServerSendQuickChatMessage` (+ `_Validate`) — the comm-wheel quick-chat
  (`EVkQuickChatMessage` vocabulary), replicated via
  `VkQuickChatReplicatedMessageData`; surfaces as text + VO + over-bracket icons.
- `ServerRequestCallIn` (+ `_Validate`) — request a team **call-in** (deployable
  support: `VkCallIn_EMP` / `VkCallIn_OverShield` / `VkCallIn_RepairBots`),
  replicated via `bCallInActive`/`OnRep_CallInActive`, gated by a tier unlock.
- Smart-pings (`ServerSendSmartPing` / `Multicast_OnPing_*`) — see
  `gameplay/05-vr-ui.md`.

A re-implemented server must accept/validate these and multicast the result.

## Reservation bridge

`ServerUpdateReservationRequest` — the in-game RPC that feeds the PartyBeacon
`ReservationUpdate` flow (`06-matchmaking-beacons.md`), e.g. party changes
mid-session.

## AI / debug

`ServerToggleAILogging`, `ServerShowFloorAIAdd`. AI bots are server-spawned
(consistent with the `-NUMAI*`/`-AIChars*` launch args in `05-*`).

## Generic transport helpers

`ClientReceiveData`, `ClientRepObjRef`, `ClientActors`,
`ServerUpdateLevelVisibility` — UE4 plumbing for object refs, level streaming
visibility, and bulk client data delivery (engine-stock).

## Replicated properties (E2)

Beyond RPCs, the server replicates **state** to clients via `UPROPERTY(Replicated)`
fields. 174 distinct `OnRep_*` handlers were recovered (E2) — i.e. the replicated
properties a re-implemented server must maintain & push. Key ones by category
(`OnRep_` prefix dropped):

- **Match / team / objective:** `MatchState`, `Score`/`CurrentScore`/`TeamScores`,
  `TeamID`, `TeamRespawns`, `RelicHolders`, `PickupState`/`ActivePickups`,
  `OwningTeam(Id)Changed`/`OwningVehicle`, `ObjectiveCompletedBy`,
  `OnMissionStateUpdated`, `Team0/1MessageList` (quick-chat feed).
- **Combat / targeting:** `Target`/`TargetPawn`/`TargetLocation`,
  `LockingTarget`/`MarkedTarget`/`MaxLockTargets`, `TakenDamage`/`LastTakeHitInfo`,
  `HitCounter`/`HitPointsUpdated`, `CloakState`, `ShieldRearmTime`/`ShieldRepCounter`/
  `ShieldMaterial`, projectiles (`Destroyed`/`Disrupted`/`Countermeasured`/
  `Retargeted`/`ForceExpired`Projectiles), `WeaponConfig`/`ProjectileConfig`/
  `InstantHitConfig`, `Detected(Vehicles)`/`DetectionRange`.
- **Abilities / ultimate:** `Ultimate`/`UltimateTimer`, `Energy`,
  `OverChargeActive`/`OverchargeEnabled`/`OverShieldFromUltimate`,
  `DronesState`/`CanDropDrone`/`DroneOnCooldown`, `EMPActor`/`FireEMP`,
  `ReachedFullCharge`.
- **Movement / ship:** `ReplicatedMovement`/`ReplicatedBasedMovement` (engine-stock),
  `MovementStateChanged/Updated`, `ShipState`, `CurrentState`/`DesiredState`,
  `BeginLaunch`/`LaunchingPlayer`/`LaunchRequired`, `BoostingBroadcast`,
  `UseVehicleLights`.
- **Player / spectator / cosmetic:** `PlayerName`, `PlayerState`, `Gender`,
  `PilotCustomisationList`, `VehicleCosmeticUniqueName`/`DecalUniqueName`,
  `GameModeUniqueName`, `ReplicatedCurrentSpectatorTarget`/`…SpectatorTargetEnergy`,
  `OnlySpectator`, `SpectatorClass`.

A re-impl server (on the same engine) gets the replication machinery free; it
must set these properties authoritatively so clients' `OnRep_*` handlers fire.
The `*Config` properties (Weapon/Projectile/InstantHit) replicate per-shot
parameters — the server pushes the loadout-derived config to clients.

## Re-implementation value

The bulk of replication is **engine-stock UE 4.14** — a re-implemented server
built on the same engine inherits movement, channels, and RPC dispatch for
free. The Vk-specific work is the gameplay-logic RPCs (fire resolution, match
flow, spectator, loadout validation), which are server-authoritative and must
be reproduced to make matches behave correctly.

## Open questions

- Replicated property layout per ship/pawn (needs class-layout analysis).
- Anti-cheat / server-side validation strictness on `ServerMove`/fire.
- Whether voice audio is networked separately (VOIP) or platform-relayed.
