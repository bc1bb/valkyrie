---
doc: net-matchmaking
title: Matchmaking, Reservation Beacons & Connection Management
summary: Match join uses UE4's stock PartyBeacon reservation protocol (reserve a slot on a battle server before full connect); plus a heartbeat thread and reconnect request type for connection resilience.
keywords: [matchmaking, beacon, partybeacon, reservation, reconnect, heartbeat, watchdog, EClientRequestType, slot, lobby, connection]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# Matchmaking, Reservation Beacons & Connection Management

## Reservation beacons (UE4 PartyBeacon — engine-stock, E5)

Before a client makes a full gameplay connection to a battle server, it
**reserves a player slot** using Unreal Engine 4's **Online Beacon /
PartyBeacon** subsystem. Evidence (E2): `PartyBeaconClient`, `PartyBeaconHost`,
`PartyBeaconState` symbols are present; the reservation request/response
vocabulary is the standard UE4 beacon protocol.

A beacon is a lightweight, separate UE4 `NetDriver` connection (here also over
the WebSocket transport) used purely for pre-game negotiation — distinct from
the in-match replication connection.

### Reservation request types (`EClientRequestType`, E2)

| Value | Meaning |
|-------|---------|
| `EmptyServerReservation` | Reserve slots on a fresh/empty server (create a new match). |
| `ExistingSessionReservation` | Reserve slots on an already-running session (join in progress). |
| `ReservationUpdate` | Modify an existing reservation (party size change). |
| `Reconnect` | Re-establish a reservation after a drop (resume an in-progress match). |
| `NonePending` | Idle / no request outstanding. |

### Reservation responses (`EPartyReservationResult`, E2/E5)

Full result enum observed (a host beacon must return these with UE4 semantics):

| Result | Meaning |
|--------|---------|
| `NoResult` | Initial / none yet. |
| `RequestPending` | Reservation in flight. |
| `RequestTimedOut` | No host response in time. |
| `ReservationAccepted` | Slot(s) granted. |
| `ReservationDenied` | Refused (generic). |
| `ReservationDenied_Banned` | Refused — player banned (Vk-relevant policy hook). |
| `ReservationDuplicate` | Already reserved. |
| `ReservationNotFound` | No matching reservation (e.g. on update/cancel). |
| `ReservationRequestCanceled` | Client withdrew the request. |
| `IncorrectPlayerCount` | Party size invalid for the request. |
| `PartyLimitReached` | Server/party capacity exceeded. |
| `BadSessionId` | Session id unknown/invalid. |
| `GeneralError` | Unspecified failure. |

The connection itself is tracked by `EBeaconConnectionState`
(`Pending → Open → Closed`, plus `Invalid`).

### Flow (E5, engine-stock semantics)

1. Client opens a beacon connection (`PartyBeaconClient`) to the battle server.
2. Sends a `ReservationRequest` (a party of player ids/auth, with a request type
   from the table above).
3. Host (`PartyBeaconHost` + `PartyBeaconState`) checks capacity/validity →
   replies `ReservationAccepted` (with remaining time / slot info) or a failure.
4. On accept, the client tears down the beacon and opens the **full game
   connection** (Plane 2 WebSocket NetDriver) to play.

This sits between Plane 1 (REST `VkBattleServerResource` allocation) and Plane 2
(replication). REST gives the server address; the beacon claims a seat on it.

## Connection management

### Heartbeat (`FHeartBeatThread`, E2)

A dedicated heartbeat thread keeps connections alive / detects death. This is
the runtime arm of the `VkWatchDog` REST resource (`01-rest-backend.md`):
periodic liveness signalling so the backend can reap dead sessions and the
client can detect a silent server loss.

### Reconnect (E2)

`EClientRequestType::Reconnect` plus `EClientRequestType::ExistingSessionReservation`
let a dropped client **rejoin a match already in progress** by re-reserving its
slot on the same battle server, rather than being treated as a brand-new join.

### Timeouts (E2, engine-stock)

UE4 beacon timeouts apply: `BeaconConnectionInitialTimeout` (handshake) and
`BeaconConnectionTimeout` (established). A logout-on-session-timeout path
(`bLogoutOnSessionTimeout`) and `ENetworkFailure::ConnectionTimeout` govern
disconnect handling. A re-implemented host should honour these so the client's
state machine progresses normally.

## Squads / parties

A **squad** (party) groups players who matchmake and reserve slots together.
`VkSquadNode` is the squad data structure; an `IdleSquadMember`
`eConnectionState` (`09-*`) marks a client idling as a non-leader squad member
(the leader drives matchmaking; members follow into the reserved slots). The
PartyBeacon `ReservationRequest` carries the whole party as one reservation,
which is why `IncorrectPlayerCount` / `PartyLimitReached` are possible results.

## Playlists & search state

Matchmaking is organized into **playlists** (`Playlist`) — curated sets of
game modes/maps a player can queue for (e.g. a ranked playlist vs. a casual
one). The client surfaces a `Searching` state while a request is outstanding
(this is the `FindingSession` `eConnectionState`, `09-*`). A re-implemented
matchmaker should accept a playlist selector and resolve it to a mode + map +
rank band for the session/battle-server it allocates.

A server clock reference (`ServerTime`) is also exposed — used to align
client/server timing (cf. the `ServerTimeStamp`/`ClientTimeStamp` movement
replication in `08-*`); a backend should provide an authoritative time source.

## Custom / private sessions

A `CustomSession` / `custommatch` path exists for private/custom matches
(distinct from public matchmaking). The `JoiningCarousel` state is the
ship/loadout selection lobby entered before launch in either path. Custom
sessions likely skip skill-based public matchmaking and let a leader invite a
specific party, then allocate a battle server the same way (`05-*`).

## Re-implementation value

The matchmaking/join handshake is **engine-stock UE4 PartyBeacon** — a private
server can reuse UE 4.14's beacon host implementation directly and only needs to
supply capacity/auth policy. The Vk-specific surface here is thin: which request
types are used and that the beacon rides the WebSocket transport.

## Open questions

- Whether reservation auth carries the JWT or a separate per-player join token.
- Party/group support: max party size, cross-platform party composition.
- Exact heartbeat interval and the watchdog's REST shape.
