---
doc: ref-rpcs
title: RPC Inventory Reference
summary: Categorized inventory of the replicated RPCs (~170 Server, ~120 Client, ~10 Multicast) — the wire-behavior a re-implemented server must implement. Every gameplay Server RPC has a _Validate companion (UE4 WithValidation = server-side validation).
keywords: [rpc, server, client, multicast, replication, validate, withvalidation, reference, inventory, wire contract]
status: living
updated: 2026-05-22
evidence: [E2]
---

# RPC Inventory Reference

The replication contract's **call** half (the **state** half — replicated
properties — is in `networking/08-*`). Recovered from the binary (E2): ~170
`Server*`, ~120 `Client*`, ~10 `Multicast*` RPCs. This indexes the meaningful
Vk-specific ones by theme; engine-stock UE4 RPCs (movement plumbing,
map-change, possession, localized messages) are noted as such.

## Key pattern: server-side validation

**Every gameplay `Server*` RPC has a `_Validate` companion** — UE4
`UFUNCTION(Server, WithValidation)`. The server validates each client request
before applying it; a failed `_Validate` disconnects the client. This is the
**cheat-resistance layer** (`networking/15-*`): a re-implemented server must
implement these validations to be authoritative. (E.g. `ServerFireShot` +
`ServerFireShot_Validate`.)

## Server RPCs (client → server, authoritative) — Vk gameplay

| Theme | RPCs (`Server` prefix dropped; each has `_Validate`) |
|-------|------|
| **Weapons/combat** | `StartFire`, `StopFire`, `FireShot`, `FireProjectile`, `BeginFiringMine`, `HandleFiring`, `NumHits` (hit reconciliation), `OnTargetSet`, `ToggleWeaponHitCountDebug` |
| **Abilities** | `EMPSelf` (+ per-ability via generic ability activation) |
| **Movement** | `Move`, `MoveDual`, `MoveDualHybridRootMotion`, `MoveOld`, `MovementMode`, `Rotation`, `VelZ` (UE4 CharacterMovement family + Vk 6-DoF additions) |
| **Spawn/launch** | `SetReadyToLaunch`, `SetStartPointGroupToRespawnAt`, `SetSelectedVehiclePreview`, `UpdateLevelVisibility` |
| **Match/objective** | `EndMatch`, `EndMatchInstantly`, `KillEnemyCarrier`, `DropPickup`, `ShowFloorEndMatch` |
| **Spectator** | `ViewSelf`, `ViewNextPlayer`, `ViewPrevPlayer`, `SpectatorChangeTarget`, `SelectSpectatorTarget`, `SetSpectatorLocation`, `SetSpectatorWaiting`, `VerifyViewTarget`, `UpdateCamera`, `UpdateCameraPOV`, `Camera`, `ForwardView` |
| **Comms** | `SendQuickChatMessage`, `RequestCallIn`, `SendSmartPing`, `AddPing`, `MutePlayer` |
| **Session/beacon** | `CancelReservationRequest` (+ PartyBeacon, `06-*`) |
| **Input/framework** (engine-stockish) | `ActionPressed`, `ActionReleased`, `Interrupt`, `AcknowledgePossession`, `CheckClientPossession(Reliable)`, `ChangeName`, `NotifyLoadedWorld`, `Exec`, `Pause` |

## Client RPCs (server → one client) — Vk-relevant

| Theme | RPCs (`Client` prefix dropped) |
|-------|------|
| **Match/result** | `GameEnded`, `EndOnlineSession`, `SetAudioWinState` |
| **HUD/notify** | `DisplayCockpitMessage`, `ReceiveData`, `ReceiveLocalizedMessage`, `TeamMessage`, `ErrorUpdateRateLimit`, `SetHUD` |
| **Reservation/beacon** | `ReservationResponse`, `CancelReservationResponse`, `SendReservationFull`, `SendReservationUpdates`, `StartOnlineSession` |
| **Targeting** | `NumHits` (reconcile), `CachedLockedTarget`, `CachedLockingTarget`, `CurrentSpectatorTarget`, `SetViewTarget` |
| **Map/travel** (engine-stock) | `PrepareMapChange`, `CommitMapChange`, `CancelPendingMapChange`, `SetNextMap`, `NextMapURL`, `LeaveServerAndGoToNextMap`, `OnConnected`, `UpdateLevelStreamingStatus` |
| **Camera/cinematic** (engine-stock) | `SetCameraFade`, `SetCameraMode`, `SetCinematicMode`, `SpawnCameraLensEffect`, `SetLocation`, `SetRotation` |

## Multicast RPCs (server → all clients)

`Multicast_OnPing_*` (smart-ping broadcast: Attack/Defend/Danger/AssistMe/
Decline), `MulticastBeginStickyLock`/`MulticastEndStickyLock` (target lock
broadcast), `MulticastSendTargetConfirmed`, `MulticastObjectiveCompletionDenied`,
`MulticastOnTimeBonusReceived`, `MulticastTimeToLive`. These are unreliable
cosmetic/event broadcasts (the authoritative state rides replicated properties).

## Re-implementation value

This + the replicated-property list (`08-*`) is the **complete wire contract**.
A re-impl server built on UE 4.14 inherits the transport; it must (1) accept &
`_Validate` the Server RPCs, (2) drive replicated properties authoritatively,
(3) send the Client/Multicast RPCs at the right moments. Engine-stock RPCs come
free with the engine; the Vk-specific gameplay/comms/beacon RPCs are the work.

## Notes

- Counts include `_Validate`/`_Implementation` companions and a few
  false-positives (field names matching the prefix); the themed lists above are
  the de-duplicated meaningful set.
- Hit reconciliation (`Server`/`Client`+`NumHits`) is the client-reported-hit →
  server-verified flow — important for fair, cheat-resistant combat (`02-*`).
