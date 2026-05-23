---
doc: net-environments
title: Backend Environments & Hosts
summary: Three CCP server environments (Tranquility=prod, Chaos & Havoc=test); each pairs an SSO login host with a VGS backend-API host. DNS redirect of these is the lever for a private server.
keywords: [environments, hosts, tranquility, tq, chaos, havoc, vgs, eveonline, testeveonline, dns, endpoints, backend]
status: draft
updated: 2026-05-23
evidence: [E2]
---

# Backend Environments & Hosts

The client embeds endpoints for **three CCP environments**. Each environment
pairs a **login/SSO host** with a **VGS backend-API host**. ("VGS" is the
backend platform — Virtual Goods / game services; the OAuth scopes are
`vgs.*`.) "TQ" = **Tranquility**, CCP's long-standing production cluster name.

| Environment | Login / SSO host | Backend API (VGS) host |
|-------------|------------------|------------------------|
| **Tranquility (production)** | `login.eveonline.com` | `vgs-tq.eveonline.com` |
| **Chaos (test)** | `chaoslogin.testeveonline.com` | `vgs-chaos.testeveonline.com` |
| **Havoc (test)** | `havoclogin.testeveonline.com` | `vgs-havoc.testeveonline.com` |

- All endpoints are HTTPS (`https://`). TLS via OpenSSL (libcurl).
- SSO host serves `/oauth/token` (see `03-authentication.md`).
- VGS host is the base URL for the `Vk*Resource` REST calls
  (see `01-rest-backend.md`). Per-resource path templates still TBD.

## Why this is the key lever for preservation

All of these hosts are **dead** (servers shut down). To make the client connect
to a re-implemented server, the practical approaches are:

1. **DNS / hosts redirect** of `vgs-tq.eveonline.com` and `login.eveonline.com`
   to a local re-implemented backend, **plus** a TLS cert the client trusts
   (OpenSSL cert verification — may require a local CA or a build that relaxes
   verification). This avoids binary patching.
2. **Binary patch** the embedded host strings to point at a local server (more
   invasive; affects clean-room separation — prefer option 1).

## Tenant / environment selection (E2)

The VGS backend is **multi-tenant** under `{tenant}.valkyrieapi.com` (+
`evevalkyrie.com`; `14-*`). The active tenant/environment is **configurable, not
hardcoded** — resolved (E2):

- **`-TENANT=` launch arg** selects the tenant at startup.
- **`VkGame_TenantDomains`** config key holds the **tenant → domain mapping**
  (the table the client uses to turn a tenant name into a hostname).
- The chosen tenant is carried as a property **`{'valkyrie.tenant':'%s'}`**
  (sent to the backend / stamped on requests).
- **`VkGame_Version`** config key carries the build version (cf. server-side
  `-BuildName=`, `05-*`).

**Preservation upshot:** because the tenant/domain is config-driven, pointing the
client at a private backend can be done by adding a tenant entry to
`VkGame_TenantDomains` (or passing `-TENANT=`) that resolves to a host you
control — alongside (or instead of) DNS redirection. This is cleaner than binary
patching.

## Open questions

- Exact VGS REST base path (e.g. is there a `/v1/` or service prefix after host).
- Whether the realtime game-server (WebSocket) address is fully dynamic from
  `VkBattleServerResource`, or also environment-pinned.
- TLS specifics: does the client pin certs, or accept any CA-valid cert?
- Where `VkGame_TenantDomains` is stored (likely an `.ini` inside the pak — out
  of scope to extract, but the mechanism is known).
