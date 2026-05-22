---
doc: net-battleserver
title: Dedicated Battle-Server Launch Contract
summary: The backend spins up a dedicated UE4 game-server process per match, passing match identity, JWT, public IP/region, team & AI config via command-line args (-BATTLEID, -BATTLESERVER_URI, -JWT, -PUBLICIP, -REGION, -NUMAITEAM*, etc).
keywords: [battle server, dedicated server, launch args, command line, matchmaking, jwt, battleid, region, publicip, teams, ai, orchestration]
status: draft
updated: 2026-05-22
evidence: [E2]
---

# Dedicated Battle-Server Launch Contract

The same client executable doubles as a **dedicated game server** (standard UE4
pattern). The backend match-orchestration layer launches a server process for
each match and configures it via **command-line arguments** (E2 — all observed
as `-NAME=` parameter strings in the binary). This is the contract a
re-implemented orchestrator must reproduce to host matches.

## Match identity & transport args

| Arg | Meaning |
|-----|---------|
| `-BATTLEID=` | Unique id of the battle/match instance. |
| `-BATTLESERVER_URI=` | URI the server binds/advertises (the WebSocket endpoint clients connect to). |
| `-BATTLE_URI=` / `-uri=` | Battle resource URI (REST handle for this battle on the backend). |
| `-InstanceId=` | Server instance id (orchestration bookkeeping). |
| `-SessionId=` / `-SESSIONID=` | Session id (ties to `VkSessionResource`). |
| `-SessionName=`, `-SessionOwner=` | Session display/owner metadata. |
| `-PUBLICIP=` | Public IP the server advertises to clients. |
| `-REGION=` | Datacenter/region the instance runs in. |
| `-SteamConnectIP=` | Steam connect address (for Steam-presence "join"). |

## Auth args

| Arg | Meaning |
|-----|---------|
| `-JWT=` | **JSON Web Token** — confirms backend tokens are JWTs. Server-side credential to authenticate to the backend. |
| `-SSOTOKEN=` | SSO token (client-side; lets a client start already-authenticated). |

> **Token format resolved:** the presence of `-JWT=` (plus the OAuth2 flow in
> `03-authentication.md`) indicates the backend access token is a **JWT**
> (signed, self-describing). A re-implemented SSO should mint JWTs.

## Match configuration args

| Arg | Meaning |
|-----|---------|
| `-gamemode=` / `-ForceMode=` | Game mode selection for the match. |
| `-InitialPlayerTeam=`, `-TEAM=` | Team assignment. |
| `-NUMAI=`, `-NUMAITEAM0=`, `-NUMAITEAM1=` | Bot counts (total / per team). |
| `-AIChars0=`, `-AIChars1=` | AI character rosters per team. |
| `-AIVEHICLE=`, `-AIABILITY=` | AI ship/ability config. |
| `-MINPILOTRANK=`, `-MAXPILOTRANK=` | Rank band for the match (matchmaking). |
| `-PLAYERNAME=` | Player display name. |

## How it fits the session lifecycle

This is the realization of the Plane-1 → Plane-2 seam (`00-architecture.md`):

1. Client calls REST matchmaking (`VkSessionRequestResource`).
2. Backend allocates a battle server via `VkBattleServerResource`, launching a
   dedicated server process with the args above (`-BATTLEID`, `-BATTLESERVER_URI`,
   `-JWT`, team/AI/rank config…).
3. Server boots, binds the `-BATTLESERVER_URI` WebSocket endpoint, authenticates
   to the backend with its `-JWT`.
4. Backend returns the server's address (+ a client join token) to the client.
5. Client connects (Plane 2 WebSocket NetDriver) and the match runs.

## Battle lifecycle reporting (server → backend, E2/E3)

Once running, the dedicated server reports match lifecycle to the backend via
`FVkBattlesResource` (the `battles` resource, `14-*`). Operations observed:

| Event | Meaning |
|-------|---------|
| `LobbyStarted` | Pre-match lobby is up (players assembling). |
| `MatchStarted` | Match began. |
| `PlayerJoined` / `PlayerDisconnected` | Per-player presence in the battle. |
| `SetMaxPlayers` | Capacity update. |
| `MatchNotJoinable` | Battle closed to new joins. |
| `MatchEnded` | Normal completion (→ results/rewards, `11-*`). |
| `MatchKilled` | Abnormal termination. |
| `EndBattle` | Final teardown / deallocation. |

So the backend tracks battle state from these server callbacks (plus the local
registration in `14-*` and the heartbeat in `06-*`). A re-implemented backend
must accept these lifecycle reports to keep its session/battle records correct
(e.g. free the slot on `PlayerDisconnected`, finalize on `MatchEnded`).

## Re-implementation value

A private orchestrator can host matches by: launching the shipped server binary
with a synthesized arg set (real `-BATTLEID`/`-BATTLESERVER_URI`, a self-minted
`-JWT`, and the desired mode/team/AI config), then handing the client the
server address. Most match parameters are plain values — no proprietary
encoding observed at the command-line layer.

## Open questions

- Exact format of `-BATTLESERVER_URI=` (scheme `ws`/`wss`, host:port, path).
- JWT claims/signing algorithm and which key the server validates against.
- Whether the client join token differs from the server's `-JWT`.
- Full enum of `-gamemode=` values (cross-ref with static data tables).
