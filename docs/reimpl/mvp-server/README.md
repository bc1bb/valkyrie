---
doc: reimpl-mvp-server
title: MVP Private Backend — Reference Implementation
summary: A runnable clean-room minimal backend (Python stdlib) implementing the documented SSO + envelope-wrapped VGS REST contract, with an in-process self-test (8/8 passing) and a Proton launch-diagnostic wrapper. Built from docs/networking + reimpl/01-02; no game code reused.
keywords: [reimplementation, server, mvp, sso, jwt, rest, envelope, hateoas, tls, selftest, proton, launch, reference]
status: draft
updated: 2026-05-23
evidence: [E2, E3, E4]
---

# MVP Private Backend — Reference Implementation

A **runnable** minimal backend that serves the contract documented in
`networking/01-14` + `reimpl/01-02`. Clean-room: written from the interface docs,
no game code reused. It is the concrete companion to `reimpl/01-mvp-server-guide.md`.

## Files

| File | What |
|------|------|
| `server.py` | The backend: HTTPS, `POST /oauth/token` (Basic `valkyrieClient` → HS256 JWT), envelope-wrapped VGS REST (accounts/pilot/staticdata/clients/sessions/battleservers), permissive stub + request logging for everything else. |
| `selftest.py` | Starts the server in-process and exercises the contract (8 checks). **Result: 8/8 pass.** |

## Run

```bash
# 1. local CA + server cert covering the VGS/SSO hosts (one-time)
mkdir -p certs && cd certs
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/CN=Valkyrie Local CA" -out ca.crt
# server cert with SANs: login.eveonline.com, vgs-tq.eveonline.com,
#   tq.valkyrieapi.com, valkyrieapi.com, localhost, 127.0.0.1  (see san.cnf)
# ... openssl x509 -req ... -extfile san.cnf -extensions v3 -out server.crt
cd ..

# 2. run (high port for unprivileged; use 443 on a host with root + DNS redirect)
VK_PORT=8443 python3 server.py

# 3. validate the contract
python3 selftest.py     # -> "8 passed, 0 failed"
```

## What it proves (E4, validated 2026-05-23 on this machine)

The contract is internally consistent and serveable: SSO mints a bearer JWT and
rejects missing Basic auth (401); accounts→`pilot_uri`; the pilot object carries
a 21-link HATEOAS graph + wallet; `staticdata GetFileList` returns `{files,
branch_name, build_number}`; `battleservers` returns a `battleServerUri` (the
Plane-1→Plane-2 seam); TLS validates against the local CA when addressed as
`login.eveonline.com`. All 8 self-test checks pass.

## What is still NOT proven (needs the real client as oracle — see `02-*` bucket B)

This validates the backend **against a mock client**, not the shipped game. The
remaining unknowns (exact JSON value-types/nesting, TLS pinning, the `NMT_Login`
join-token bytes) need the real client driving it. On the analysis machine the
client **could not be brought up** — see the launch diagnostic below.