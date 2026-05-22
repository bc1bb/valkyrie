---
doc: net-rest
title: REST Backend Surface (VkRestUtils)
summary: Inventory of the Vk*Resource REST client classes — the backend API surface the server must implement; per-resource purpose and re-impl priority.
keywords: [rest, http, libcurl, api, resources, auth, sso, battles, sessions, pilots, store, leaderboards, watchdog]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# REST Backend Surface — `VkRestUtils`

The `VkRestUtils` module is the client's HTTP(S) backend layer (libcurl +
OpenSSL). Each `Vk*Resource` class wraps one backend resource. Their existence
and naming (E1) directly enumerates the backend API surface. Exact paths,
verbs, and JSON schemas are not yet captured (open questions).

## HTTP plumbing classes

| Class | Role |
|-------|------|
| `VkHttpRequest` | Base wrapper around an HTTP request (likely over UE4 `IHttpRequest` or direct libcurl). |
| `VkAuthHttpRequest` | An HTTP request variant that attaches auth (session token/header). |
| `VkSSOHttpRequest` | Single-Sign-On flavored request — CCP SSO/token exchange. |

## Resource clients (the API surface)

| Resource class | Backend concern | Re-impl priority |
|----------------|-----------------|:---------------:|
| `VkClientResource` | Client/version handshake, bootstrap config. | **P0** (first call) |
| `VkSSOHttpRequest` / `VkAuthHttpRequest` | Auth: platform-ticket → session token. | **P0** |
| `VkPilotResource` | Player ("pilot") profile, progression, currency. | **P0** |
| `VkPilotSessionInterface` | Pilot's online session/presence state. | P1 |
| `VkStaticDataResource` | Download static game data (tables/config). | **P0** |
| `VkSessionResource` | A match/session object (state, players). | **P0** |
| `VkSessionRequestResource` | Request to join/create a session (matchmaking). | **P0** |
| `VkBattlesResource` | Battles (match listing / lifecycle). | P1 |
| `VkBattleServerResource` | Battle **server allocation** — returns the game-server endpoint. | **P0** (bridges to Plane 2) |
| `VkChallengeResource` | Challenges / objectives. | P2 |
| `VkLeaderboards` | Leaderboard read/write. | P2 |
| `VkVirtualGoods` | Store / purchasable goods catalog + transactions. | P2 |
| `VkLootCapsuleResource` | Loot boxes ("capsules") open/grant. | P2 |
| `VkImplantResource` | Implants (gameplay modifier items). | P2 |
| `VkPilotCosmeticResource` | Pilot cosmetic items. | P3 |
| `VkHeroCosmeticResource` | Ship/"hero" cosmetic items. | P3 |
| `VkWatchDog` | Connection watchdog / heartbeat / keepalive. | P1 |

## Priority rationale

To merely **boot to a usable state and start a match**, a server must answer:
`VkClientResource` (bootstrap), auth (SSO), `VkPilotResource` (a profile),
`VkStaticDataResource` (data the client needs to load), then the
session/battle-server allocation chain (`VkSessionRequestResource` →
`VkSessionResource` → `VkBattleServerResource`). Cosmetics/store/loot are
non-blocking for playability and can return empty/stub payloads initially.

## Virtual goods purchase states (`EInAppPurchaseState`, E2)

`VkVirtualGoods` / `VkLootCapsuleResource` transactions resolve into a UE4
purchase-state enum: `Success`, `Failed`, `Cancelled`, `Invalid`, `NotAllowed`,
`AlreadyOwned`, `Restored`, `Unknown`. A re-implemented store must drive
transactions to one of these terminal states (engine-stock semantics).

## Known unknowns (to resolve by traffic capture / static analysis)

- Base URL(s) and per-resource path templates.
- HTTP verbs and required headers (auth header name, content type).
- JSON request/response schemas and field names.
- Token format (JWT? opaque?) and refresh flow.
- Whether `VkBattleServerResource` returns a WebSocket URL + join token, and
  its exact shape (this is the seam between Plane 1 and Plane 2).
