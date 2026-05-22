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

### Why a custom OSS

UE4 normally picks one platform OSS (Steam, Oculus, etc.). Valkyrie instead
runs **its own OSS** so that — regardless of store (Steam or Oculus) — all
session/identity logic funnels through the CCP backend. The platform OSS is
used only to mint a platform ticket; `OnlineIdentityVk` exchanges it for the
backend JWT, and `OnlineSessionVk` talks to the Vk REST + beacon layer.

This is the integration seam a private server must satisfy: emulate what
`OnlineIdentityVk`/`OnlineSessionVk` expect from the backend, and the engine
side behaves normally.

## Telemetry / Analytics (engine-stock, E2/E5)

Analytics use Unreal's **`AnalyticsProviderET`** ("ET" = Epic Telemetry),
posting events to **Epic's DataRouter**:

- Endpoint: `https://datarouter.ol.epicgames.com/datarouter/api/v1/public/data`
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

- The exact UE4 interfaces `OnlineSubsystemVk` implements beyond identity/
  session/presence (friends? external UI? voice via the Oculus spatializer?).
- How `OnlineSessionVk` maps `CreateSession`/`FindSessions`/`JoinSession` to the
  REST resources + PartyBeacon (the precise call sequence).
- Whether presence is backend-driven or platform-driven.
