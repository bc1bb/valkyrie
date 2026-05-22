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

## Tooling available on this machine (assessed 2026-05-22)

- **Runner: Proton Experimental** is bundled inside the Steam snap
  (`steamapps/common/Proton - Experimental`). The Windows client can be launched
  through it on Linux — so the E4 loopback path is **feasible** here without a
  separate Wine install. (Standalone `wine`/`wine64` are NOT on PATH.)
- **Capture/stub:** `tcpdump` (raw), `nc`, `python3` (write a stub
  HTTPS/WebSocket server), `strace` (observe `connect()`/DNS), `gdb` (inspect the
  JWT-validation path dynamically). `objdump`/`strings` already used for static.
- **Missing:** `mitmproxy`/`mitmdump` (no `pip`/`sudo` in this env yet) — either
  install via a venv/system package when network/permissions allow, or hand-roll
  a TLS-terminating stub in `python3` (`ssl` + `http.server` + a `websockets`
  shim) using a locally-generated CA the client's OpenSSL is told to trust.

### Practical first experiment (cheapest signal)

Run the client under Proton with `strace`/`tcpdump` and **no** backend redirect,
just to capture **DNS lookups + TLS SNI + connection order** (which hosts it
hits, in what sequence) — this validates the host topology (`04-*`) and the
`eConnectionState` ordering (`09-*`) without needing to decrypt anything. Then
escalate to the redirect+TLS-terminating stub for payload-level detail.

## Probe results — run #1 (2026-05-22, `analysis/scripts/capture_launch.sh`)

First bounded launch (Proton Experimental, `strace -f -e trace=network`, 75s cap):

- **Proton runs** the client via the Steam Linux Runtime
  (`pressure-vessel` → `srt-bwrap` sandbox → bundled Wine). The launch path and
  env (`STEAM_COMPAT_DATA_PATH`, `STEAM_COMPAT_CLIENT_INSTALL_PATH`) are correct.
- Launching the game **also brings up the Steam client** (steamwebhelper etc.);
  a logged-in Steam session is present on this host.
- **The game process exited (code 5) before any backend networking.** The only
  network syscalls captured (~23) were Steam-runtime **internal Unix-socket**
  fd-passing — **zero `connect()` to any internet IP, zero DNS queries** for
  `login.eveonline.com` / `vgs-tq.eveonline.com`.

**Interpretation:** in this headless/no-VR context the client aborts during
early init (likely missing HMD/`d3d`/display or a Steam-app-context check)
*before* it constructs `OnlineSubsystemVk` and issues the SSO call. So no E4
backend evidence yet.

**Confirmed launch flags (E2, from binary strings):** `-nullrhi` (null
renderer — no GPU/HMD), `-server` (headless dedicated-server mode), `-game`
(client), `-vr`, `-d3d11`/`-d3d12`/`-opengl` (RHI selection). These are
stock-UE4 flags but their presence confirms the binary supports a **headless
path**.

**What a networked capture needs (next-run prerequisites):**
1. The game must survive init far enough to reach OnlineSubsystem login. Two
   paths, headless-first:
   - **`-server -nullrhi`** (recommended): runs the **dedicated server** with no
     renderer/HMD. The dedicated server authenticates to the backend with its
     `-JWT` (`05-*`) and resolves the VGS host — a clean, UI-free capture target
     whose outbound DNS/`connect()` is the first real E4 datapoint. Feed it a
     synthesized `-BATTLEID/-BATTLESERVER_URI/-JWT` arg set.
   - **client** path: provide a display/`Xvfb` (present here), launch via Steam's
     app id so the Steam API context initializes, add `-nullrhi`/`-vr`-off to
     dodge the HMD requirement, and let the `steam_ticket` grant fire the SSO call.
2. Once it reaches login, the `steam_ticket` grant fires the HTTPS call to the
   SSO host — that DNS lookup/`connect()` is the first real E4 datapoint, even
   though the dead server won't answer (the *attempt* confirms host + ordering).
3. For payloads, add the redirect + TLS-terminating stub (above).

> Note: do not repeatedly spawn full game launches in a tight automation loop —
> each pulls up the whole Steam+Proton+Wine stack. Run launch probes
> deliberately, one at a time, with a hard timeout and process cleanup after.

## Clean-room boundary

Capturing the client's *own emitted traffic* and our *own stub's* behaviour is
observation of interfaces — admissible E4 evidence. We still never copy game
code or assets into the repo; only distilled protocol facts enter the docs.

## Output

Each capture session should yield edits to docs 01–05/10 turning hypotheses into
`verified` facts, and ideally a machine-readable schema file under
`docs/networking/schemas/` (our own description, not captured bytes).
