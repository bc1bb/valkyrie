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
