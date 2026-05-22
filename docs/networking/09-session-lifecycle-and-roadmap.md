---
doc: net-lifecycle-roadmap
title: End-to-End Session Lifecycle & Re-Implementation Roadmap
summary: Capstone — the client connection state machine (eConnectionState) stitched to every networking plane, plus a prioritized roadmap for a minimal viable private server.
keywords: [lifecycle, state machine, eConnectionState, roadmap, re-implementation, mvp, server, flow, capstone, failure]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# End-to-End Session Lifecycle & Re-Implementation Roadmap

This capstone ties the planes (`00-architecture.md`) to the **client connection
state machine** (`eConnectionState`, E2) and ranks the work to bring multiplayer
back. Read the per-area docs (01–08) for detail.

## Client connection state machine (`eConnectionState`, E2)

Observed states (the high-level multiplayer flow the UI drives):

```
Idle ─▶ FindingSession ─▶ FoundSession ─▶ BattleFound ─▶ ConnectingToServer
  ▲                                                          │
  │                                              WaitingForRunningBattle
  │                                                          │
  └────────────── Quitting ◀── MapTransition ◀──────────────┘
```

Plus: `ConnectionFailed` (error branch from any connect step), `CustomSession`
(private/custom match path), `JoiningCarousel` (the ship/loadout selection
"carousel" lobby), `IdleSquadMember` (idle while in a squad/party).

Mapping each state to the planes:

| State | What happens | Doc |
|-------|--------------|-----|
| `Idle` / `IdleSquadMember` | Logged in (JWT held), in menus/party. | 03, 07 |
| `FindingSession` | REST matchmaking request. | 01 (`VkSessionRequestResource`) |
| `FoundSession` / `BattleFound` | Backend allocated a battle + server. | 01 (`VkBattleServerResource`), 05 |
| `ConnectingToServer` | Reservation beacon → open WebSocket NetDriver. | 06, 02 |
| `WaitingForRunningBattle` | Joined; waiting for match start. | 08 (match-flow RPCs) |
| `JoiningCarousel` | Ship/loadout pick before launch. | 08 (`ServerSetSelectedVehiclePreview`) |
| `MapTransition` | Travel into/out of the match map. | 02 (control channel) |
| `ConnectionFailed` | Any failure (see `ENetworkFailure`). | below |
| `Quitting` | Tear down, post results. | 01 (results/leaderboards) |

## Failure modes (`ENetworkFailure`, engine-stock E5)

`ConnectionLost`, `ConnectionTimeout`, `PendingConnectionFailure`,
`FailureReceived`, `NetDriverCreateFailure`, `NetDriverListenFailure`,
`NetGuidMismatch`, `NetChecksumMismatch`, **`OutdatedClient` / `OutdatedServer`**.

> **Version gating matters:** `OutdatedClient`/`OutdatedServer` means the
> control-channel handshake rejects version-mismatched peers. A private server
> must report a compatible network/engine version (UE 4.14.3, CL 3195953) or
> the client refuses to connect. See `engine/01-engine-identification.md`.

## Re-implementation roadmap (priority order)

**P0 — Boot & authenticate**
1. Stand up an SSO endpoint: `POST /oauth/token` accepting the `steam_ticket`,
   Oculus `password`, and `refresh_token` grants; mint a JWT with the three
   `valkyrie`/`vgs` scopes. (`03-authentication.md`)
2. Redirect `login.eveonline.com` + `vgs-tq.eveonline.com` to it (DNS/hosts +
   a trusted TLS cert). (`04-backend-environments.md`)
3. Serve `VkClientResource` bootstrap, `VkPilotResource` (a profile), and
   `VkStaticDataResource` (whatever payload the client must load).

**P1 — Reach a match**
4. Implement the matchmaking chain: `VkSessionRequestResource` →
   `VkSessionResource` → `VkBattleServerResource` returning a server address +
   join token. (`01`, `05`)
5. Launch the shipped binary as a dedicated server with the `-BATTLEID /
   -BATTLESERVER_URI / -JWT / mode / team / AI` args. (`05`)
6. Implement (or reuse UE4) the **PartyBeacon host** to accept reservations.
   (`06`)

**P2 — Play**
7. Let the client open the WebSocket NetDriver to the server; rely on
   engine-stock UE 4.14 replication for movement/RPCs. (`02`, `08`)
8. Implement server-authoritative gameplay RPCs (fire resolution, match flow,
   spectator, loadout validation). (`08`)
9. Heartbeat/watchdog + reconnect so sessions are stable. (`06`)

**P3 — Meta (non-blocking)**
10. Stub/empty `VkVirtualGoods`, `VkLootCapsuleResource`, cosmetics, challenges,
    leaderboards initially; flesh out later. (`01`)
11. Sinkhole Epic DataRouter telemetry. (`07`)

## The two hardest unknowns (need live capture, E4)

- **JWT signing/validation**: which key the backend (and dedicated server) trust.
  Without it, the client may accept a self-signed token but the dedicated server
  might reject it (or vice-versa). Capture or static analysis of the validation
  path is the critical-path task.
- **VGS REST path templates + JSON schemas**: resource names are known; exact
  paths/verbs/bodies are not. A man-in-the-middle TLS capture of a (historical)
  session, or deeper static analysis of `VkRestUtils`, is the way in.

## Status of the documentation effort

Networking architecture is mapped end-to-end at the **interface level** (planes,
hosts, auth, launch contract, beacons, OSS, replication, lifecycle). The next
tier is **wire-level detail** (exact paths, JSON, JWT internals), which largely
requires live traffic (tier E4) rather than static strings.
