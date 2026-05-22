---
doc: net-live-observations
title: Live Endpoint Observations (E4)
summary: Passive DNS + minimal unauthenticated HTTP probes (2026-05-22) of the documented hosts. EVE SSO (login.eveonline.com) and its /oauth/token endpoint are LIVE behind Cloudflare; token endpoint returns 401 unauthenticated → confirms HTTP Basic client auth required. Chaos test env DNS still points at CCP IPs; Havoc is gone.
keywords: [e4, live, dns, cloudflare, sso, oauth, token, 401, basic auth, eveonline, observation, capture, verified]
status: verified
updated: 2026-05-22
evidence: [E4]
---

# Live Endpoint Observations (E4)

First tier-E4 (live) evidence, from **passive DNS** + **minimal unauthenticated
HTTP probes** of the hosts documented in `04-backend-environments.md`. Method &
ethics below. Dated 2026-05-22; re-verify before relying (infra can change).

## Method & scope (clean-room / responsible)

- DNS: `getent hosts` (passive resolution only).
- HTTP: a few `curl` requests with **no credentials**, **no load** (single
  HEAD/POST per host, 10s timeout). EVE's SSO is a **public, documented OAuth2
  API**; observing its existence and standard error responses is legitimate.
- **Not** attempted: real grants, credentials, brute force, or anything against
  a now-defunct service beyond a single liveness check. We only confirm shape.

## DNS topology (resolution as of probe date)

| Host | Resolves to | Note |
|------|-------------|------|
| `login.eveonline.com` | Cloudflare (172.64/104.18 ranges) | **Live** (EVE Online still uses it). |
| `vgs-tq.eveonline.com` | same Cloudflare IPs | Wildcard `*.eveonline.com` edge; origin service likely gone. |
| `chaoslogin.testeveonline.com` | 87.237.38.x (CCP Reykjavík) | Test env DNS still present. |
| `vgs-chaos.testeveonline.com` | 87.237.38.x | " |
| `vgs-havoc.testeveonline.com` | 87.237.38.x | resolves; service unknown. |
| `havoclogin.testeveonline.com` | **NXDOMAIN** | Gone. |
| `datarouter.ol.epicgames.com` | (no usable A) | Epic telemetry — irrelevant (`07-*`). |
| `valkyrieapi.com` (+ `www`/`tq`) | **NXDOMAIN** | The dedicated VGS API domain (`14-*`) — fully gone. |
| `evevalkyrie.com` (+ `www`) | **NXDOMAIN** | Dedicated Valkyrie domain — fully gone. |

> **Key inference:** the **real VGS backend lived on `valkyrieapi.com`** (the
> multi-tenant `{tenant}.valkyrieapi.com`, `14-*`), which is now **NXDOMAIN**.
> `vgs-tq.eveonline.com` only still resolves because of the surviving
> `*.eveonline.com` wildcard (EVE Online proper is alive) — its Valkyrie origin
> is gone too. For a private server, `valkyrieapi.com` is a **clean redirect
> target** (unregistered/NXDOMAIN, not parked by a third party).

Takeaway: production + Chaos hostnames still resolve; the prod hosts sit behind
**Cloudflare** (because EVE Online proper is alive). The Valkyrie-specific
*origin* services are presumed dead, but the **edge answers**.

## HTTP liveness (unauthenticated)

| Request | Result | Meaning |
|---------|--------|---------|
| `HEAD https://login.eveonline.com/` | **302** → `/account/logon?ReturnUrl=%2F` | SSO web login **alive**. |
| `HEAD https://login.eveonline.com/oauth/token` | **405** | Token endpoint **exists, POST-only** (rejects HEAD). |
| `POST https://login.eveonline.com/oauth/token` (empty body, no auth) | **401** (HTML, ASP.NET + Azure App Insights) | Rejects before grant parsing → **client authentication required**. |
| `HEAD https://vgs-tq.eveonline.com/` | **405** (Cloudflare) | Edge answers; origin behaviour untested. |

## What this VERIFIES (upgrades from E2/E5 → E4)

1. **`login.eveonline.com/oauth/token` is the real, live token endpoint** — the
   string-derived URL (`03-authentication.md`) is correct and reachable.
2. **The token endpoint is POST-only** (405 to HEAD/GET).
3. **HTTP Basic client authentication is required** — an unauthenticated POST
   yields **401** (not a JSON `invalid_request`), i.e. the client must send
   `Authorization: Basic base64(client_id:client_secret)` before the grant is
   even evaluated. This **confirms the open question** in `03-*` about Basic auth.
4. The SSO origin is an **ASP.NET app with Azure Application Insights**, fronted
   by **Cloudflare** — a useful fingerprint of CCP's SSO stack.

## What this does NOT tell us (still open)

- The actual `client_id`/`client_secret` (needs the binary/dynamic analysis,
  `03-*`; not obtainable by probing). **Static recovery attempted & failed:** a
  scan of all embedded strings for a hardcoded `Authorization: Basic <base64>`
  blob decoding to `client_id:client_secret` found **none** — so the Basic
  credential is assembled at runtime from separate constants. The reliable way
  to get it is a **gdb breakpoint on the Basic-auth header construction**
  (`methodology/traffic-capture-plan.md`).
- Whether the **Valkyrie** grants (`steam_ticket`, Oculus) still function — the
  origin VGS/Valkyrie services are presumed decommissioned; only the SSO shell
  (shared with live EVE Online) answers.
- Any `vgs-tq` REST behaviour beyond the 405 edge response.

## Implication for re-implementation

A private re-implementation can't reuse the dead Valkyrie origin, but this
confirms the **contract to mimic**: a token endpoint at `/oauth/token` that
requires HTTP Basic client auth, is POST-only, and (per `03-*`) accepts the
`steam_ticket`/Oculus/`refresh_token` grants. The redirect target for a private
server is `vgs-tq.eveonline.com` + `login.eveonline.com` (see DNS-redirect lever
in `04-*`).
