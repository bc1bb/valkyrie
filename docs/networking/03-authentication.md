---
doc: net-auth
title: Authentication & SSO (OAuth2)
summary: Login is OAuth2 against CCP SSO (login.eveonline.com/oauth/token); custom grant_types exchange a Steam ticket or Oculus identity for a Bearer access+refresh token with valkyrie scopes.
keywords: [auth, oauth2, sso, login, eveonline, token, bearer, steam_ticket, oculus, refresh_token, grant_type, scope, 2fa]
status: draft
updated: 2026-05-22
evidence: [E2]
---

# Authentication & SSO

The client authenticates via **OAuth2** against **CCP's SSO** service. The
token endpoint, grant types, parameters, and scopes are all visible as embedded
format strings (E2). This is the highest-value find for re-implementation: the
auth handshake is fully specified below.

## Token endpoint

- Production (Tranquility): `https://login.eveonline.com/oauth/token`
- Test (Chaos):  `https://chaoslogin.testeveonline.com/oauth/token`
- Test (Havoc):  `https://havoclogin.testeveonline.com/oauth/token`

Standard OAuth2 `POST /oauth/token` with `application/x-www-form-urlencoded`
body. Response is JSON containing `access_token`, `refresh_token`, `token_type`
(Bearer), `expires_in` (all confirmed as strings in the binary).

## Grant types (form bodies, E2)

The client uses **custom OAuth2 grant types** to bridge platform identity into a
Valkyrie session token. Three grants observed:

**1. Steam → token**
```
grant_type=steam_ticket
&steam_ticket=<hex Steamworks session ticket>
&intellectual_property=VALKYRIE
&scope=valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1 vgs.marketAccess.v1
```

**2. Oculus → token**
```
grant_type=password
&oculus_user_id=<uint64>
&oculus_nonce=<nonce>
&oculus_callsign=<display name>
&intellectual_property=VALKYRIE
&scope=valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1 vgs.marketAccess.v1
```

**3. Refresh**
```
grant_type=refresh_token&refresh_token=<refresh token>
```

Notes:
- `intellectual_property=VALKYRIE` namespaces the request to this title.
- The Steam ticket is obtained via Steamworks `GetAuthSessionTicket`; the Oculus
  triplet (user id + nonce + callsign) via the Oculus Platform SDK.
- The token endpoint very likely requires HTTP **Basic** auth with the app's
  OAuth `client_id`/`client_secret` (standard CCP SSO; the binary references
  `client_id` and `Authorization: Basic`). Exact client credentials TBD.

## Scopes requested

| Scope | Grants access to |
|-------|------------------|
| `valkyrie.userLogin.v1` | Core login / player identity for Valkyrie. |
| `vgs.valkyrieVirtualStore.v1` | Virtual Goods Store (catalog, owned goods). |
| `vgs.marketAccess.v1` | Market/transaction access. |

`vgs` = the backend platform host family (see `04-backend-environments.md`).

## Using the token

Backend REST calls (`VkRestUtils`) attach the token as a Bearer credential:
- `Authorization: Bearer <access_token>` (also seen as `auth=Bearer %s`).
- `VkAuthHttpRequest` is the request wrapper that injects this header;
  `VkSSOHttpRequest` performs the token-endpoint exchange itself.

## Error conditions (E2)

The client recognizes these auth failures (verbatim error semantics):
- 2nd-factor (2FA) auth failure.
- expired auth code.
- invalid auth code.

This implies the SSO also supports an interactive authorization-code path (web
login with optional 2FA), in addition to the platform-ticket grants above.

## Re-implementation note

A replacement SSO need only: accept `POST /oauth/token` with the three grant
types, validate (or stub) the platform ticket, and return a signed Bearer token
+ refresh token carrying the three scopes. Downstream services must accept that
token. **Token format: JWT** — confirmed by the dedicated-server `-JWT=` launch
arg (see `05-battle-server-launch.md`); a re-implemented SSO should mint JWTs.
The signing algorithm and validation key remain to be determined.

**`client_id` not in static strings (E2 negative result):** `client_id` appears
only as a request *field name* — no literal client_id/secret VALUE is embedded
as a recoverable string. So the OAuth client credential is either a compiled-in
constant (raw bytes in `.text`/`.rdata`, not a tidy string) or assembled at
runtime. Recovering it needs the dynamic/gdb path
(`methodology/traffic-capture-plan.md`), or derivation from a captured
`Authorization: Basic …` header on the token request.
