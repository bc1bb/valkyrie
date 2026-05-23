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
OpenSSL — corroborated by libcurl's import fingerprint in `binary/01-*`). Each
`Vk*Resource` class wraps one backend resource. Their existence and naming (E1)
directly enumerates the backend API surface. Exact paths, verbs, and JSON
schemas are not yet captured (open questions).

> **Two HTTP paths coexist** (import-table evidence, `binary/01-*`): the VGS REST
> client here rides **libcurl**, while UE 4.14's stock HTTP module is **WinINet**-
> backed (`WININET.dll` imports) — so engine-level HTTP such as Epic's telemetry
> DataRouter (`07-*`) can use WinINet independently of VkRestUtils' libcurl.

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

## Confirmed REST path structure (E2)

Path templates recovered from embedded format strings (the leading `%s` is the
VGS base URL, e.g. `https://vgs-tq.eveonline.com/`). The API namespaces under a
**`{version}/valkyrie/...`** prefix, with versions mixed **per resource**:

| Path template (after base URL) | Resource | Version |
|--------------------------------|----------|---------|
| `v2.0/valkyrie/accounts/` | Accounts (identity/profile root). | v2.0 |
| `v2.0/valkyrie/stores/7/offers/` | Store offers (store id `7`). | v2.0 |
| `v1.0/valkyrie/notifications/oculus` | Notifications (Oculus channel). | v1.0 |
| `…hero_leaderboard/{id}?{query}` | Hero (ship) leaderboard. | — |
| `…hero_survival_leaderboard/{a}/{b}` | Survival-mode leaderboard. | — |
| `…wormhole_leaderboard/{id}?{query}` | Wormhole-mode leaderboard. | — |

Observations:
- **Versioning is per-resource** (`v1.0` and `v2.0` coexist) — a re-implemented
  backend must route both prefixes.
- The `valkyrie/` segment namespaces this title within the shared VGS platform
  (consistent with `intellectual_property=VALKYRIE` in the OAuth grant, `03-*`).
- `stores/7` implies numeric store ids; leaderboards are keyed by mode + id with
  a query string (paging/scope).
- Other resources (`pilots`, `battles`, `sessions`, `battleserver`) follow the
  same `{version}/valkyrie/<resource>/...` shape by inference (E5) but their
  exact templates are not all present as static strings (built by concatenation)
  — confirm via the gdb path in `methodology/traffic-capture-plan.md`.

## JSON object model & HATEOAS pattern (E2)

Backend JSON uses **snake_case** field names. A large share are **`*_uri`
fields** — the API is **hypermedia/HATEOAS-driven**: a response embeds URIs that
point to related resources, and the client follows those rather than building
paths itself. This is *why* most exact paths aren't static strings in the binary
(they arrive at runtime in `_uri` fields). A re-implemented backend must return
these URIs so the client can navigate.

**Link fields (`*_uri`) observed:** `pilot_uri`, `pilots_uri`, `session_uri`,
`squad_uri`, `squad_pilot_uri`, `squad_join_uri`, `squad_invites_uri`,
`loot_capsule_uri`, `hero_rewards_uri`.

**Identity / reference fields:** `pilot_id`, `my_pilot_id`, `pilot_ids`,
`team_id`, `squad_id`, `squad_leader_id`, `battle_id`, `battleserver_id`,
`session_id`, `steam_id`.

**Match / session config fields:** `session_type`, `max_players`, `max_pilots`,
`min_pilot_rank`, `max_pilot_rank`, `num_ai_per_team`, `clones_per_team`,
`battles_required`, `time_to_battle_join`. (These mirror the dedicated-server
launch args in `05-*` — the REST session object carries the same knobs the
server is then launched with.)

**Progression / stats fields:** `reputation_rank`, `league_score`,
`hero_ship_stats`, `team_stats`, `implant_seconds`, `applied_pilot_cosmetics`,
`stats_updated`.

**Client-identification fields** (sent to backend, likely on client/auth calls):
`client_id`, `build_version`, `os_platform` — let the backend gate by client
build/platform (cross-ref `VkClientResource`, `OutdatedClient` in `09-*`).

**Analytics event naming:** events follow `event.<area>.<action>` (e.g.
`event.training_mode.completed`) — Epic DataRouter payloads (`07-*`).

**Account/lifecycle state flags:** `npe_completed` (New Player Experience /
tutorial done — gates first-time flow) and `battle_completed` (match-end signal
that drives the post-match results/progression POST). A re-implemented backend
should persist `npe_completed` per account and accept a `battle_completed`
report at match end.

**Squad fields:** `squad_id`, `squad_version`, `squad_leader_id`,
`squad_leader_callsign`, plus the squad `*_uri` links above.

> Implication for re-implementation: model resources as JSON objects with an
> `id`, their data fields, and `*_uri` links to children/related resources. The
> client drives navigation off those links, so the **link graph** (which
> resource embeds which `_uri`) matters as much as individual schemas. Capturing
> one real response per resource (gdb path, `methodology/traffic-capture-plan.md`)
> would pin the exact field sets.

## Confirmed query parameters (E2)

Recovered from embedded query-string format templates. Resource keys are
**snake_case**:

| Param | Used by / meaning |
|-------|-------------------|
| `pilot_id=<int>` | Single-pilot lookup. |
| `pilot_ids=<csv>` | Batch pilot lookup. |
| `session_type=<str>` | Session resource filter (match type). |
| `group=<str>` | Grouping selector (e.g. leaderboard group). |
| `friendly_name=<str>` (`friendlyName`) | Display-name lookup/set. |
| `recent=<str>` | Recency filter. |
| `version=<str/int>`, `app=<str>`, `user=<str>` | Client/version/user scoping. |

**Paging / filtering vocabulary** (case varies — query vs. JSON field):
`offset`, `limit`, `count`, `filter`, `period`, `scope`, `page`, `page_size`,
`max_results`. A re-implemented backend should honour `offset`+`limit` (and/or
`page`+`page_size`) paging on list endpoints (leaderboards, pilots, offers).

Auth-bearing params already covered in `03-authentication.md`
(`steam_ticket`, `refresh_token`, `oculus_user_id`/`oculus_nonce`/`oculus_callsign`).

## Virtual goods purchase states (`EInAppPurchaseState`, E2)

`VkVirtualGoods` / `VkLootCapsuleResource` transactions resolve into a UE4
purchase-state enum: `Success`, `Failed`, `Cancelled`, `Invalid`, `NotAllowed`,
`AlreadyOwned`, `Restored`, `Unknown`. A re-implemented store must drive
transactions to one of these terminal states (engine-stock semantics).

## Request lifecycle & error handling (E2)

The HTTP layer builds on UE4's **`HttpRetrySystem`** (engine-stock retry/backoff)
with `HttpConnectionTimeout` / `HttpSendTimeout` bounds. Observed behaviors a
re-implemented backend must play nicely with:

- **Token-expiry refresh-and-retry:** a request can fail specifically *because
  the auth token expired*. On that condition the client refreshes via the
  `refresh_token` grant (`03-*`) and retries the original request. → A backend
  should return a clear "expired/unauthorized" signal (e.g. HTTP 401) so this
  path triggers, rather than a generic failure.
- **Allowed (non-fatal) error codes:** some requests treat certain HTTP error
  codes as *expected/allowed* (handled, not surfaced as failures) — e.g. a
  "not found" on an optional resource. Per-resource tolerance; a backend
  returning these won't break the client.
- **Slow-request handling:** a request "taking too long" is flagged (timeout
  watchdog) and may be retried/abandoned per the retry policy.
- **Terminal states:** request sent → succeeded | failed (incl. "response code
  said error"). `VkAuthHttpRequest` wraps the token-refresh-on-expiry logic.

> Re-impl guidance: use standard HTTP status semantics — 2xx success, **401 for
> expired/invalid token** (triggers refresh), 404 etc. for optional-resource
> "allowed" cases. The client's retry layer is engine-stock and forgiving.

## Crash reporting (engine-stock, E2)

Crashes are handled by UE4's shipped **`CrashReportClient.exe`**
(`CrashReporterSettings`, `crashreports`) → Epic's crash backend. **Non-essential
and irrelevant to preservation** — like DataRouter telemetry (`07-*`), it can be
ignored/blocked. Not part of the game backend.

## Known unknowns (to resolve by traffic capture / static analysis)

- Base URL(s) and per-resource path templates.
- HTTP verbs and required headers (auth header name, content type).
- JSON request/response schemas and field names.
- Token format (JWT? opaque?) and refresh flow.
- Whether `VkBattleServerResource` returns a WebSocket URL + join token, and
  its exact shape (this is the seam between Plane 1 and Plane 2).
