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
  triplet (user id + nonce + callsign) via the Oculus Platform SDK — the exact
  calls are **import-confirmed** (E1, `binary/01-*`/`07-*`): `ovr_User_GetID`
  (→ `oculus_user_id`), `ovr_User_GetUserProof` (→ `oculus_nonce`),
  `ovr_User_GetOculusID` (→ `oculus_callsign`); `ovr_User_GetAccessToken` is also
  available for token-based variants.
- The token endpoint **requires HTTP Basic auth** with the app's OAuth
  `client_id`/`client_secret` — **confirmed live (E4)**: an unauthenticated
  `POST /oauth/token` to the live host returns **401** (see
  `12-live-endpoint-observations.md`). The client must send
  `Authorization: Basic base64(client_id:client_secret)`. Exact credentials TBD
  (not obtainable by probing; needs binary/dynamic analysis).

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

**JWT internals are NOT in the client (E2/E3 — opaque token):** the client
treats `access_token` as an opaque **Bearer** credential — it does not decode or
validate the JWT (no `HS256`/`RS256`, base64url token-decode, or claim-name
handling in the binary; only the `-JWT` arg + `Bearer` usage exist). So the JWT
**claims and signing key were backend-internal** (validated by CCP's now-dead
VGS services) and aren't recoverable from the client — **nor needed**: a
re-implementation controls both token *minting* (its SSO) and *validation* (its
services + the dedicated server it runs), so it defines its own claims/algorithm/
key. The only hard requirement is that the *same* re-impl key signs and verifies.

**`client_id` RECOVERED (E3, disassembly):** the OAuth `client_id` is
**`valkyrieClient`**. Recovered by disassembling the Basic-auth construction
(`disasm_func.py` @ ~`0x1420c0100`): the routine loads `"valkyrieClient"`,
formats `"%s:%s"` (client_id:client_secret), base64-encodes it, and prepends
`Basic ` → `Authorization: Basic base64("valkyrieClient:<secret>")`.

**`client_secret` is empty / public-client (E3):** the second `%s` (secret)
defaults to the empty-string sentinel and **no client_secret string exists**
anywhere in the binary (searched 116k+ strings). So the credential is
effectively `valkyrieClient:` (empty secret) — a **public OAuth client**, normal
for the ticket/password grants here. (If a secret is injected at runtime from
config, it isn't compiled in; treat the client as public.) A re-implemented SSO
should accept `client_id=valkyrieClient` with no/empty secret.
