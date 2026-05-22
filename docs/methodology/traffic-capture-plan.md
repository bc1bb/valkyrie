---
doc: method-capture
title: Live Traffic Capture Plan (E4)
summary: How to obtain tier-E4 wire evidence (exact REST paths, JSON schemas, JWT internals, WebSocket frames) via DNS redirect + TLS interception against a controlled local backend — the bridge from static facts to a working spec.
keywords: [capture, mitm, tls, dns redirect, pcap, websocket, jwt, rest, methodology, e4, observation]
status: draft
updated: 2026-05-22
evidence: [E5]
---

# Live Traffic Capture Plan (E4)

The static analysis (docs 01–10) maps the networking **interfaces**. The
remaining unknowns are **wire-level** and need observed traffic (tier E4). This
plan stays clean-room: we observe the client's own behaviour; we do not read or
copy game code/assets.

## Why capture is needed

Open questions that only traffic resolves:
- Exact VGS REST path templates + HTTP verbs per `Vk*Resource` (`01`).
- JSON request/response schemas, incl. the `files[]` object (`10`).
- JWT header/claims/signing algorithm (`03`) and the validation key.
- `Sec-WebSocket-Protocol` value + UE4 control-channel login framing (`02`).
- `-BATTLESERVER_URI` concrete scheme/host/port (`05`).

## Constraint: the live servers are gone

Tranquility/Chaos/Havoc are dead, so a *pristine* online capture is no longer
possible. Two viable evidence sources:

1. **Archived captures** — any pre-shutdown PCAP/HAR a community member saved.
   TLS-encrypted ones need the session keys to decrypt (rarely kept), so these
   are usually opaque beyond SNI/host/timing. Still useful for host/timing maps.
2. **Loopback capture against our own stub backend** — the high-value path. We
   redirect the client to a local server we control, watch what it *requests*,
   and iterate the stub until the client advances. The client itself becomes the
   spec oracle: its requests reveal paths; its acceptance/rejection reveals
   required fields and JWT validation rules.

## Loopback method (recommended)

### 1. Redirect DNS
Point `login.eveonline.com` and `vgs-tq.eveonline.com` (and the DataRouter, to a
sink) at `127.0.0.1` via the OS hosts file or a local resolver.

### 2. Terminate TLS locally
Run a TLS-terminating proxy (e.g. `mitmproxy`/`mitmdump`) or a small HTTPS
server with a cert the client will trust. Trust options, least invasive first:
- Install a local CA into the OS/again-trust store the client's OpenSSL uses.
- If the client pins certs (open question, `04`), pinning must be located and a
  non-pinned path used — note this is a documentation finding, not a code edit.

### 3. Log everything
Capture full request lines, headers, and bodies. For the OAuth token call,
record the exact form body and the JSON response you must synthesize. For each
`Vk*Resource`, record method + path + body the client emits.

### 4. Iterate the stub
Return minimal valid responses; advance the client through `eConnectionState`
(`09`). Each rejection ("required fields", "not in file list", auth failure)
pinpoints a schema/JWT requirement. Document each resolved field back into the
relevant doc and flip its `status` toward `verified`.

### 5. WebSocket / replication
Once the client opens the NetDriver WebSocket, capture the HTTP Upgrade (the
`Sec-WebSocket-Protocol` value) and the first frames (UE4 control channel
`NMT_*` handshake). A local UE 4.14 dedicated server is the cleanest way to
observe well-formed framing to compare against.

## Tooling available on this machine

`tcpdump` (raw capture), `nc`, `python3` (write a stub HTTPS/WebSocket server),
`strace`/`ltrace` (observe syscalls/connects if running the client under Wine),
`gdb` (inspect the JWT validation path dynamically). `mitmproxy` would need
installing (no pip yet — use a venv or system package when network allows).

## Clean-room boundary

Capturing the client's *own emitted traffic* and our *own stub's* behaviour is
observation of interfaces — admissible E4 evidence. We still never copy game
code or assets into the repo; only distilled protocol facts enter the docs.

## Output

Each capture session should yield edits to docs 01–05/10 turning hypotheses into
`verified` facts, and ideally a machine-readable schema file under
`docs/networking/schemas/` (our own description, not captured bytes).
