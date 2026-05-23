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
pattern) — now **import-confirmed** (E1): the EXE links the Steamworks
**game-server** half (`SteamGameServer`, `SteamGameServer_Init`,
`SteamGameServerStats`, `SteamGameServerNetworking`, `SteamMatchmakingServers`;
`binary/01-*`/`07-*`), not just the client SDK, so one binary serves both roles.
The backend match-orchestration layer launches a server process for each match
and configures it via **command-line arguments** (E2 — all observed as `-NAME=`
parameter strings in the binary). This is the contract a re-implemented
orchestrator must reproduce to host matches.

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
| `-TENANT=` | Backend **tenant** selector (→ `{tenant}.valkyrieapi.com`, `04-*`). |
| `-BuildName=` | Build/version label the server reports (cf. `VkGame_Version`). |
| `-NOSTEAM` | Disable Steam init (run without the Steam client/game-server). |

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

## Hosting: AWS GameLift (E2)

The dedicated battle servers run on **Amazon GameLift** (managed dedicated-server
fleet hosting). Evidence: `AVkGameMode_GameLift`, **`GameLiftServerSDK`** linked
in, and a configurable port range `MinGameLiftPort`/`MaxGameLiftPort`. So the
original `VkBattleServerResource` allocation (`01-*`) was backed by GameLift:
the backend requests a game session from a GameLift fleet, GameLift launches the
server process on a fleet host (with the launch args in this doc), the server
calls the GameLift Server SDK to register/activate, and GameLift returns the
host IP + port.

**Preservation implication:** a private re-implementation does **not** need
GameLift — it can launch the shipped server binary directly (the launch
contract above) and feed the client the resulting `public_ip`+`port` via
`VkBattleServerResource`. The GameLift SDK calls on the server side can be
stubbed/ignored (or the `-server` binary may run without them). GameLift is just
how CCP *operated* the fleet, not a client-side requirement.

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

## Server startup behaviour (E2, log strings)

Diagnostic strings expose the server boot/registration path:
- **Steam game-server init:** the server initializes the Steam **game-server**
  SDK (`SteamGameServer*`, `07-*`); failure logs *"Failed to initialize game
  server with Steam!"* and *"[OnlineSubsystemSteam].GameVersion is not set.
  Server advertising will fail"* — so Steam server advertising needs a GameVersion
  (cf. `-BuildName=`/`VkGame_Version`). `-NOSTEAM` bypasses this (useful for a
  private host not registering with Steam).
- **Self-registration:** the server auto-logs-in and registers itself; failure
  logs *"Autologin attempt failed, unable to register server!"* and
  *"BattleServer Resource Creation/Update FAILED"* (the `battleservers` POST/PUT,
  `13-*`/`14-*`).
- **Offline/dev fallback:** *"Battle Resource Creation FAILED: Using fake battle
  id"* — when battle-resource creation fails, the server falls back to a
  synthesized ("fake") battle id and runs anyway. Useful for a standalone/offline
  bring-up of the server without a full backend.
- **Rewards path guard:** *"Failed to find objective manager for pilot, couldn't
  send battle rewards!"* — confirms the score→reward seam (`VkPlayerScoreObjective`
  manager feeds the match-result report, `gameplay/01`/`11-*`).
- **Team fill:** *"Failed to assign player to team - probably no spaces left on
  server"* — server-side team assignment with capacity limits.

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
