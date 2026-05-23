---
doc: net-oss-telemetry
title: OnlineSubsystemVk Composition & Telemetry
summary: Custom UE4 OnlineSubsystem (OnlineIdentityVk/OnlineSessionVk/VkOculusPlatform + Steam bridge) wires platform identity into the backend; telemetry uses engine-stock AnalyticsProviderET to Epic's DataRouter.
keywords: [onlinesubsystem, oss, identity, session, oculus, steam, presence, telemetry, analytics, datarouter, epic, AnalyticsProviderET]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# OnlineSubsystemVk Composition & Telemetry

## The custom Online Subsystem

EVE Valkyrie ships a **custom UE4 OnlineSubsystem** named `Vk` that adapts the
engine's online interfaces to the CCP/Valkyrie backend. Components (E2):

| Class | UE4 interface role | Vk behaviour |
|-------|--------------------|--------------|
| `OnlineSubsystemVk` | `IOnlineSubsystem` root | Factory for the interfaces below; the `Vk` OSS module. |
| `OnlineIdentityVk` | `IOnlineIdentity` | Login/identity. Bridges platform login → the OAuth2 SSO token (`03-authentication.md`). Owns the local user's auth state. |
| `OnlineSessionVk` | `IOnlineSession` | Session create/find/join. Maps UE4 session ops onto REST session resources + reservation beacons. |
| `VkOculusPlatform` | (platform helper) | Wraps the Oculus Platform SDK (user id / nonce / callsign for the Oculus grant). |
| `OnlineSubsystemVkSteam` | platform bridge | Steam path: obtains the Steamworks session ticket for the `steam_ticket` grant. |

A **presence interface** (`GetPresenceInterface`) is also referenced — online
status / "in match" presence, surfaced to platform friends.

### Social: presence, friends, invites, voice (E2)

- **Presence** — `OnlinePresence` / `RichPresence`: the player's status (online,
  in-menu, in-match) is published as **platform rich presence** (Steam/Oculus),
  so platform friends see it. This is largely engine-stock `IOnlinePresence`
  driven by game state; not necessarily a separate backend presence service.
- **Friends** — `EVkFriendsListState` is a Vk-specific friends-list state
  machine (load/ready/error). The friends graph itself is most likely the
  **platform's** (Steam/Oculus) friends list, surfaced in-game.
- **Invites / squads** — `AcceptSquadInvite` + invite flow tie into the squad
  system (`06-*`): invite a friend → they join the squad → the squad reserves
  slots together via PartyBeacon.
- **Voice moderation** — `MuteRemoteTalker` / `UnmuteRemoteTalker` (engine-stock
  UE4 voice): per-player mute state (also noted in `08-*`).

Re-impl note: presence/friends ride the **platform** layer, so a backend
re-implementation needs little here — invites/squads are the part that touch the
game backend (session/reservation), and those are covered in `06-*`.

### OSS interface surface (E2) — deliberately minimal

`OnlineSubsystemVk` implements only a small set of UE4 `IOnline*` interfaces:

| Interface | Provider | Role |
|-----------|----------|------|
| Identity | `OnlineIdentityVk` | Login → backend JWT (`03-*`). |
| Session | `OnlineSessionVk` | Create/find/join session (→ REST + beacon). |
| Presence | `GetPresenceInterface` | Online/in-match status (platform rich presence). |
| Achievements | `GetAchievementsInterface` | Achievements (likely Steam/Oculus-backed). |

Plus a Steam helper async task **`FOnlineAsyncTaskVkSteamGetUserPrivilege`** —
a Steam **user-privilege / age-gate / multiplayer-allowed** check before online play.

**Notably ABSENT as OSS interfaces:** Friends, Party, Store, Leaderboards, Voice,
ExternalUI. Those features exist but are implemented through the **`VkRestUtils`
REST layer** (`01-*`/`14-*`: `VkVirtualGoods`, `VkLeaderboards`, squads, friends
via platform) rather than UE4 OSS interfaces. So a re-implementer integrating at
the OSS level only needs identity/session/presence/achievements; everything else
is plain REST.

### Why a custom OSS

UE4 normally picks one platform OSS (Steam, Oculus, etc.). Valkyrie instead
runs **its own OSS** so that — regardless of store (Steam or Oculus) — all
session/identity logic funnels through the CCP backend. The platform OSS is
used only to mint a platform ticket; `OnlineIdentityVk` exchanges it for the
backend JWT, and `OnlineSessionVk` talks to the Vk REST + beacon layer.

This is the integration seam a private server must satisfy: emulate what
`OnlineIdentityVk`/`OnlineSessionVk` expect from the backend, and the engine
side behaves normally.

## Platform-SDK call surface (E1, import-confirmed)

The delay-import tables (`binary/01-*`) name the **exact** platform-SDK entry
points the client calls — promoting several inferences above to E1 facts.

**Oculus Platform SDK** (`LibOVRPlatform64_1.dll`, 40 imports) — the `VkOculusPlatform`
backing:
- **Entitlement gate:** `ovr_Entitlement_GetIsViewerEntitled` — Oculus-store DRM
  (verify the user owns the title) before play.
- **Identity → backend bridge:** `ovr_User_GetLoggedInUser`, `…GetID`,
  `…GetOculusID`, `…GetAccessToken`, `…GetUserProof` (nonce). This is the
  concrete source of the **Oculus grant** material that `OnlineIdentityVk`
  exchanges for the VGS JWT (`03-authentication.md`): access-token + user-proof
  nonce + Oculus id/callsign.
- **Friends/presence:** `ovr_User_GetLoggedInUserFriends`, `ovr_User_GetPresence`,
  `…GetInviteToken` — confirms the friends/invite graph is **platform-sourced**.
- **In-app purchase (Oculus Store):** `ovr_IAP_GetProductsBySKU`,
  `ovr_IAP_GetViewerPurchases`, `ovr_IAP_LaunchCheckoutFlow`, Product/Purchase
  arrays + `ovr_Product_GetFormattedPrice`. So real-money purchases on the Oculus
  build go through **Oculus Store IAP** (by SKU), parallel to the in-game
  currency/store economy (`networking/11-*`). A preservation backend doesn't
  serve these — they were platform-store transactions.

**Steam SDK** (`steam_api64.dll`, 22 imports):
- **Client:** `SteamUser`, `SteamFriends`, `SteamUserStats`, `SteamRemoteStorage`
  (cloud saves), `SteamApps` (ownership/DLC), `SteamMatchmaking`, `SteamUtils`,
  `SteamAPI_RestartAppIfNecessary` (Steam DRM relaunch). The Steam session ticket
  for the `steam_ticket` grant comes from here.
- **Server:** `SteamGameServer`, `SteamGameServer_Init`, `SteamGameServerStats`,
  `SteamGameServerNetworking`, `SteamGameServerUtils`, `SteamMatchmakingServers` —
  the **game-server** half of the Steam SDK is in the *same* EXE. Strong evidence
  the dedicated battle server (`networking/05-*`) is this binary launched in
  server mode, registering with Steam's game-server backend.

**HMD service client** (`hmd_client.dll`, 8 imports): `hmdclientConnect`/
`Disconnect`/`RequestServerVersion`/`GetHMDInfo2000`/`GetHMDViewStatus`/
`GetTrackerStates` — an IPC client to a local **HMD runtime service** (connect →
query HMD info / tracker poses / view status). Despite the `ThirdParty/PS4` path
name (`binary/02-*`), the calls are a generic HMD-service IPC; recorded
factually, no PSVR-on-PC claim.

**Tobii** (`Tobii.GameIntegration.dll`): `Start`/`Stop`/`Update`,
`GetNewGazePoints`, `GetNewHeadPoses`, `GetUserPresence`, `UpdateInteraction`,
`InfiniteScreen*` — gaze + head-pose + presence + the "infinite screen"
extended-view feature (`engine/03-*`). **OpenVR** (`openvr_api.dll`) imports only
`VR_InitInternal`/`GetInitToken`/`IsInterfaceVersionValid`/`ShutdownInternal` —
the rest of SteamVR is reached through UE4's plugin internally.

## Telemetry / Analytics (engine-stock, E2/E5)

Analytics use Unreal's **`AnalyticsProviderET`** ("ET" = Epic Telemetry),
posting events to **Epic's DataRouter**:

- Endpoint: `https://datarouter.ol.epicgames.com/datarouter/api/v1/public/data`
- Query params: `SessionID`, `AppID`, `AppVersion`, `UserID`, `AppEnvironment`,
  `UploadType` (e.g. `?SessionID=…&AppID=…&AppEnvironment=…`). `AppEnvironment`
  carries the build's environment label (e.g. `Production`).
- Configured via `APIKeyET` (app key) + `APIServerET` (server URL) settings;
  the client errors if either is empty (`AnalyticsET: APIKey ... cannot be empty`).
- This is **separate from the game backend** — it is Epic's standard UE4
  analytics pipeline, not CCP infrastructure.

### Preservation note

The DataRouter is **non-essential** for playability. It can be ignored, blocked
(DNS sinkhole), or pointed at a stub that returns 200. It carries gameplay
telemetry, not auth or match state. (Note: `datarouter.ol.epicgames.com` may
still resolve, but sending it traffic is unnecessary and undesirable for a
preservation client.)

## Corrected earlier note

The `/v1/public/data` path seen in strings belongs to **Epic DataRouter**
(`datarouter/api/v1/public/data`), NOT the Vk/VGS REST API. The VGS backend's
own path templates remain undetermined (open question).

## Open questions

- How `OnlineSessionVk` maps `CreateSession`/`FindSessions`/`JoinSession` to the
  REST resources + PartyBeacon (the precise call sequence).

Resolved by the import surface above: friends/presence/invites are **platform-
sourced** (Oculus `ovr_User_*` / Steam `SteamFriends`); the Oculus grant material
is access-token + user-proof nonce (`03-*`); IAP is Oculus-Store-backed.
