---
doc: net-bootstrap-realtime
title: Client Bootstrap, /clients Contract & Realtime Connection
summary: Full disassembly of the VkClientResource POST /clients response handler (@0x1420b7d70 == RVA 0x20b7d70), re-verified instruction-by-instruction 2026-05-23. IMPORTANT (CORRECTION #2): the prior Frida "disproof" that this handler never fires was an RVA bug — it hooked base+0xb7d70 instead of base+0x20b7d70 (dropped the leading 0x2). The handler is correct; re-hook at base+0x20b7d70.  The parse-level success contract is VERIFIED at instruction level and the client_id-as-string hypothesis is DISPROVEN — client_id is read with TryGetNumberField (cvttsd2si of a double), NOT TryGetStringField, so a top-level JSON number is the correct and accepted type. The SOLE success gate is `client_id != -1` (cmp dword [r15+0x14], -1; je skip); there are NO other ANDed required fields (pilot_id/pilot_uri/account_id/token/eula/npe are all read with tolerant TryGet* and never gate the branch; deprecated_version only selects success-state 0 vs 8, both broadcast success). Our MVP response satisfies the gate, so the live loop is NOT a parse rejection — it is below/after the parse: a transport-level completion failure (null Response → error helper 0x1420b7b40 → state 3..7 → broadcast success=false) or a stalled success continuation. Realtime: the binary contains NO 26000 string, NO game XMPP/notification endpoint; the 26000 TCP probes in the sink capture are not sourced from the Valkyrie REST layer.
keywords: [bootstrap, clients, vkclientresource, client_id, deprecated_version, 409, registered, connectionstate, realtime, presence, websocket, watchdog, retry, run_number, timeout, bWasSuccessful, 201, 26000, xmpp, e2, e3, e4]
status: draft
updated: 2026-05-23
evidence: [E2, E3, E4, E5]
---

> **2026-05-23 CORRECTION #3 (the `/clients` WALL IS BROKEN) — READ FIRST.**
> The real success gate is a **non-empty `Location` response header**, NOT (only)
> `client_id`. Verified by Frida Stalker call-trace + Capstone disasm of the
> confirmed handler `0x1420b7d70`: after the 409 check it calls
> `GetHeader("Location")` and case-insensitively compares the value to the **empty
> string** (the ref byte at `0x143103ed3` is `0x00`). If `Location` is empty/absent
> → `je 0x1420b86d2` → it **skips the body parse** (`call 0x142038010` at
> `0x1420b7f66` is never reached) and broadcasts FAILURE via `0x142095a10` with the
> resource state still `1` (`success=((state&~8)==0)` is false) → the client retries
> 3×/run then resets. A **non-empty `Location`** makes it fall through, parse the
> bare body, read `client_id` (number, `TryGetNumberField` `0x140a1f650` →
> `[r15+0x14]`), pass the `client_id != -1` gate, log "registered", and build the
> pilot-load continuation from `pilot_uri`. **So §1 below is wrong where it says
> "Empty/absent `Location` is fine (HATEOAS hop is optional)" — a non-empty
> `Location` is REQUIRED.** Fix applied to `reimpl/mvp-server/server.py`: `/clients`
> returns `200` + `Location: <client-resource-uri>` + bare top-level numeric
> `client_id`. Confirmed live (E4): client registered, then issued
> `GET /live/pilots/1` and `GET vgs-tq.eveonline.com/v2.0/valkyrie/accounts/` — the
> first requests it has ever made past registration. The Stalker call-trace also
> showed NONE of §1's other claimed callees (parser/getters/continuation/telemetry)
> actually run on the skip path — only the broadcast `0x2095a10` — i.e. the prior
> instruction-level §1 was disassembled imprecisely; trust this corrected flow.

> **2026-05-23 CORRECTION #2 (RVA arithmetic bug in the Frida "disproof") — READ FIRST.**
> The bring-up log (`docs/reimpl/04-live-bringup-log.md`) recorded that LIVE Frida
> hooks at `0xb7d70` / `0xb85a8` / `0xb7b40` / `0x38010` "never fire" during a real
> `/clients` completion, and concluded the static handler below was misidentified
> and "the real handler is unknown." **That conclusion is itself wrong — it was an
> RVA off-by-`0x2000000` mistake, not a code-path discovery.** The functions live
> at absolute VAs `0x1420b7d70`, `0x1420b85a8`, `0x1420b7b40`, `0x142038010`. With
> the documented image base `0x140000000`, their true module-relative **RVAs are**:
>
> | function | absolute VA | **correct RVA** | wrong RVA hooked |
> |---|---|---|---|
> | `/clients` completion handler | `0x1420b7d70` | **`0x20b7d70`** | `0xb7d70` |
> | success gate `cmp [r15+0x14],-1` | `0x1420b85a8` | **`0x20b85a8`** | `0xb85a8` |
> | transport-fail helper | `0x1420b7b40` | **`0x20b7b40`** | `0xb7b40` |
> | JSON-parse entry | `0x142038010` | **`0x2038010`** | `0x38010` |
> | pilot_uri continuation builder | `0x1420845d0` | **`0x20845d0`** | `0x845d0` |
>
> `analysis/scripts/frida_clients.py` did `Process.getModuleByName(exe).base.add(0x38010)`
> etc. — i.e. `base + 0xb7d70` = VA **`0x1400b7d70`**, an unrelated/cold address,
> so the hooks landed nowhere and never fired (while the `recv`/QPC control hook
> fired fine, masking the mistake). The leading `0x2` hex digit of the `0x20b…`
> RVA was dropped. **The static handler at `0x1420b7d70` was NOT disproven; it is
> the correct handler.** It was re-confirmed by disassembly 2026-05-23: it is the
> sole lea-load target of the completion bound at the `/clients` request builder
> (`0x1420b6e9c`, builder verified via the unique sent fields
> `distribution_platform`/`physical_memory_gb`/`preferred_region`/`client_type`),
> it reads the `Location` response header and parses the body, reads `client_id`/
> `pilot_id`/`pilot_uri`/`callsign`/`default_region`/`deprecated_version`/`popups`,
> and gates success on `client_id != -1` before logging `"registered"`. **Action:
> re-run Frida with the corrected RVAs above (especially `base+0x20b7d70`); it WILL
> fire this time.** The §1 contract below stands as VERIFIED.
>
> Caveat: this resolves *why the hooks didn't fire*; it does **not** by itself
> explain the live loop. Once `base+0x20b7d70` is confirmed firing, the next
> branch facts to capture live are: (a) does it reach the `cmp [r15+0x14],-1` at
> `0x1420b85a8` with `[r15+0x14] != -1` (gate passed) — log `r15+0x14`; (b) does it
> reach `"registered"` (`0x1420b85e3`) and build the continuation (`0x1420845d0`);
> or (c) does it take the null-`Response` path to `0x1420b87a7` → `0x1420b7b40`
> (transport fail). That single hook disambiguates parse-pass vs transport-fail vs
> stalled-continuation — the question the prior bad RVAs left open.
>
> **2026-05-23 CORRECTION (E3, full disasm).** The earlier conclusion that the
> client rejects `/clients` because it lacks a numeric top-level `client_id` is
> **necessary but not sufficient** and does NOT explain the live loop: the MVP
> backend already returns `client_id:1` (number, top level) with a non-409
> status, and instruction-level disassembly of the response handler confirms
> that body **passes every gate** in the handler. The loop is therefore not the
> handler rejecting our body. See the rewritten §1 and §3 below. The realtime
> §2 is also corrected: the 26000 traffic is real in the capture but is **not**
> emitted by any Valkyrie REST/notification code in the binary.
>
> **2026-05-23 RE-VERIFICATION (E3, every instruction of `0x1420b7d70` read).**
> Two specific hypotheses were tested against the bytes and **both resolved
> definitively**: (1) **`client_id` is read with `TryGetNumberField`, NOT
> `TryGetStringField`.** The getter is `0x140a1f650` (the number-field helper)
> and its result is consumed by `cvttsd2si eax, qword [rsp+0x50]` (truncate a
> *double* to int32). The companion log string is literally
> `FVkJsonObject::TryGetNumberField: Failed to find number field …`. So a JSON
> **number** is the correct, accepted type — sending the string `"-1"` (or any
> string) would FAIL this read. Our MVP's numeric `client_id` is read correctly.
> (2) **There is exactly ONE conditional gate to the success block:
> `cmp dword [r15+0x14], -1; je <skip>` at `0x1420b85a8`.** No other field is
> ANDed in. `pilot_id`/`pilot_uri`/`callsign`/`default_region`/`popups` are read
> with tolerant `TryGet*` and never branch; `deprecated_version` only chooses the
> success-state value (0 vs 8) — both are broadcast as success. There is **no**
> required `account_id`, token, `eula`, or `npe`. **Conclusion: the parse-level
> contract is a numeric top-level `client_id != -1` and nothing more — fully
> consistent with the prior §1. The live loop is therefore confirmed to live
> below/after the parse (transport completion failure or stalled continuation),
> NOT in the field reads.**

# Client Bootstrap, `/clients` Contract & Realtime Connection

This doc closes three questions about the post-login bootstrap: (1) what the
client requires from the `POST /live/clients` (`VkClientResource`) response;
(2) whether a persistent realtime/presence connection is opened at login and
where its endpoint comes from; (3) how a failure resets the bootstrap. Findings
are from targeted disassembly of the response handler plus the live capture
(2026-05-23) summarized in `12-*`/`07-*`.

Evidence tiers: **E2** embedded strings/structure, **E3** disassembly of the
parse routines, **E4** live client capture against our backend, **E5**
engine-stock UE 4.14 behaviour.

## 1. The `/clients` (`VkClientResource`) response contract

### Where it lives (E3)

The request builder assembles `app_info` (`app_guid`, `run_number`, `locale`,
`distribution_platform`, `cpu_vendor`, `cpu_brand`, `gpu_brand`, `num_cores`,
`physical_memory_gb`) plus top-level `client_type`, `preferred_region`, and a
trailing `vkpilot`/`parameters` — matching the live request body (E4). The
**response handler** is a distinct routine (the `VkClientResource` response
delegate). It is the gate that decides success vs. retry.

### Control flow recovered — instruction-level (E3, VERIFIED)

The response-completion delegate is the function at **`0x1420b7d70`**, bound to
the `/clients` POST request at `0x1420b6e9c` (`lea r8, 0x1420b7d70` →
`SetDelegate` glue `0x1420809a0`). Its parameters are `(this = VkClientResource,
Request, Response)`; it stores `this` in `r15`. The resource carries an `int32`
**state field at `[r15+0xa0]`** that the rest of the bootstrap polls. The handler
runs, in order:

1. **Init state to 1 (in-flight).** `mov dword [r15+0xa0], 1` on entry.
2. **Null-response guard.** `mov rcx,[Response]; test rcx,rcx; je 0x1420b87a7`.
   If the HTTP layer delivered **no response object** (UE4 passes a null/empty
   response when the request finished with `bWasSuccessful == false` — DNS/TLS/
   connection/parse failure at the transport), it jumps to an error helper
   (`0x1420b7b40`) that maps a failure category into state **3..7** and skips the
   body parse entirely. **This is the path a transport-level failure takes.**
3. **Read HTTP status** (`call [vtbl+0x40]` = `GetResponseCode`) and compare to
   **`0x199` (409)**. `cmp eax, 0x199; jne …`. **409 only** → state = **2**
   (conflict / incompatible build, pairs with `Cannot register client
   (incompatible build)` / `ClientOutdated`) and skip the success block. No other
   status value is inspected — **201 and 200 are treated identically** to any
   other non-409 code; the handler does NOT require exactly 200.
4. **Read the `Location` response header** (twice) and store it onto the resource
   if non-empty. Empty/absent `Location` is fine (HATEOAS hop is optional).
5. **Parse the body to a `FVkJsonObject`** via `0x142038010` → `0x140434870`.
   **VERIFIED:** this deserialises the **raw response body** into one JSON object
   and the field reads below run against that **top-level** object. It does **not**
   unwrap a `content` envelope first. So `/clients` wants the fields **bare at the
   body top level** (unlike `/auth`, which is read enveloped).
6. **Read fields** (each via the tolerant `TryGet*Field`; missing → logs
   `FVkJsonObject::TryGet…Field: Failed to find … field named '%s'` and
   continues). The getter *type* per field is now confirmed by the exact helper
   call and the consume-instruction (this is the decisive evidence against the
   "client_id is a string" hypothesis):
   - **`client_id`** — field name loaded at `0x1420b7f86`; getter
     **`call 0x140a1f650`** (the **number**-field helper, which invokes the JSON
     value's `as-number` virtual at `[vtbl+8]`); on success
     **`cvttsd2si eax, qword [rsp+0x50]`** (truncate a *double* → int32) → stored
     **int32 at `[r15+0x14]`**; the failure log is the literal
     `…TryGetNumberField: Failed to find number field…`. **→ JSON NUMBER, not
     string. A string value (e.g. `"1"` or `"-1"`) fails this read and leaves the
     `-1` sentinel.**
   - **`pilot_id`** — same number helper `0x140a1f650`, `cvttsd2si` → int32 at
     `[r15+0x18]`. (JSON number.)
   - **`pilot_uri`** — string helper **`0x142038980`** → `[r15+0x30]`.
   - **`callsign`** — string helper `0x142038980` → stack `[rbp-0x68]` (carried
     into the broadcast).
   - **`default_region`** — string helper `0x142038980` → `[r15+0x80]` (stored
     verbatim; never compared to the request's `preferred_region`).
   - **`deprecated_version`** — bool helper **`0x142038740`** into a 1-byte stack
     slot at `[rsp+0x30]`, **pre-zeroed → default `false`**.
   - **`popups`** — object-array helper **`0x142038840`**; if present, each
     element is read for **`unique_name`** + **`url`** (both via the string helper
     `0x142038980`) and appended to an array at `[r15+0x160]`. Absent/empty is
     fine.
   None of these reads branch the control flow — they only populate fields.
7. **Success gate = `client_id` ONLY (instruction-verified).** `[r15+0x14]` is
   pre-set to `-1` (`0xFFFFFFFF`). After all field reads, the single decisive
   branch is at **`0x1420b85a8`: `cmp dword [r15+0x14], -1; je 0x1420b869b`**. If
   still `-1` (read failed — field absent OR present-but-not-a-number), the entire
   success block is **skipped** and state stays **1**. There is **no other
   conditional ANDed into this branch** — no `pilot_id`/token/`eula`/`npe`/status
   check guards it. If a number was parsed (`client_id != -1`):
   - Compute success state from `deprecated_version`:
     `movzx eax,[rsp+0x30]; neg al; sbb ecx,ecx; and ecx,8; mov [r15+0xa0],ecx`
     → **state `0`** when `deprecated_version` is false/absent, **state `8`** when
     true. **Both are "success"** (see tail).
   - Log the **`"registered"`** checkpoint and send a `client-event` `Checkpoint`
     telemetry via `0x1420c0cc0` (telemetry only — does NOT itself fetch the pilot).
   - Allocate a 0x70-byte continuation object (`0x1417c0d00`), initialise it from
     `pilot_uri` (`0x1420845d0`), and bind three callbacks (`0x1420a7c00`,
     `0x1420a7ba0`, `0x1420a7da0`) — this is the request that actually loads the
     pilot, keyed off `pilot_uri`.
8. **Common tail (success and missing-`client_id` skip):** `0x1420b86e2`
   broadcasts the registration result on the resource's multicast delegate at
   `[r15+0xc0]` (`0x142095a10`): `test dword [r15+0xa0], 0xfffffff7; sete dl`
   computes **`success = ((state & ~8) == 0)`**, and `r8d = [r15+0x18]` passes
   **`pilot_id`**. So state 0/8 → **success=true + pilot_id**; state 1 (missing
   `client_id`) or state 2 (409) → **success=false**.
   **Note (corrected):** the **transport-failure path does NOT pass through this
   tail.** The null-`Response` guard (step 2) jumps to `0x1420b87a7`, which calls
   the error helper **`0x1420b7b40`** — that helper sets state **3..7** (mapping a
   failure category in `edx`) **and broadcasts `success=false` itself** on
   `[…+0xc0]`, then returns into the cleanup epilogue at `0x1420b8736` (below the
   main broadcast). Either way a transport failure broadcasts exactly one
   `success=false`.

**Net (instruction-verified): the parse handler's only hard requirements are
(a) a delivered (non-null) `Response` object — i.e. `bWasSuccessful == true` at
the UE4 HTTP layer; (b) HTTP status `!= 409`; (c) a top-level JSON-**number**
`client_id != -1`.** `deprecated_version` must be falsey/absent (else success
state is 8, still a success but flags an outdated build). Every other field is
optional/tolerated and never gates the branch. The MVP backend's response
(numeric top-level `client_id`, non-409, `deprecated_version:false`) meets all
three — so the gate is satisfied and the live loop is below/after this parse.

### What a re-impl backend MUST return for `/clients` (VERIFIED contract)

- **HTTP status:** any code **except 409**. `200`, `201`, and `204` are all
  accepted by the handler (only `0x199`/409 is branched). `201` is fine; you do
  **not** need exactly `200`. A `Location` header is read but optional.
- **Body framing:** **bare object, fields at the top level.** Do **not** rely on
  the common `{…,content:{…}}` envelope here — the handler parses the raw body and
  reads `client_id` bare (this differs from `/auth`, which IS enveloped). Putting
  `client_id` *only* inside `content` would leave it at `-1`. (Carrying it BOTH
  bare and in an envelope, as the current MVP does, is harmless — the bare copy is
  what's read.)
- **Required field:** **`client_id`: a JSON number ≠ -1** (read with
  `TryGetNumberField`, truncated to int32). This is the **sole** success gate.
  It MUST be a JSON number token — **not** a quoted string. (The client's own
  device-fingerprint request sends `client_id` as the string `"-1"`; that string
  form is what the *client* uploads to mean "no id yet" — the *response* must come
  back as a real number so the number getter succeeds.)
- **Recommended fields** (consumed by the follow-on step / tolerated if absent):
  `pilot_id` (number), `pilot_uri` (string), `callsign` (string),
  `default_region` (string), `deprecated_version: false`, `popups: []`.
  `default_region` is stored verbatim; nothing in the handler compares it to the
  request's `preferred_region`, so any string is accepted. `pilot_uri` is the
  one field the **success continuation** actually consumes (it is the URI the
  pilot-load request is built from), so it should be a usable absolute URI on a
  host the client can reach.

### Exact minimal response that reaches the `"registered"` / transition branch

Concretely, the smallest body that makes `0x1420b7d70` set success-state 0, log
`"registered"`, broadcast `(success=true, pilot_id)`, and build the pilot-load
continuation is just the numeric `client_id`:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: <exact>

{ "client_id": 1 }
```

Recommended fuller response (lets the success *continuation* proceed cleanly,
since it reads `pilot_uri`/`pilot_id`):

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: <exact>

{
  "client_id": 1,                                 // JSON number, != -1  (THE gate)
  "pilot_id": 1,                                  // JSON number
  "pilot_uri": "https://<same-host>/live/pilots/1", // string, absolute, reachable
  "callsign": "Pilot",                            // string
  "default_region": "eu-west-1",                  // string (any; not compared)
  "deprecated_version": false,                    // bool; false → success state 0
  "popups": []                                    // empty array is fine
}
```

Value **types** are load-bearing: `client_id`/`pilot_id` = numbers; the rest =
strings/bool/array as shown. A quoted `"client_id": "1"` would FAIL the number
getter and leave the `-1` sentinel → no transition.

### What the state machine does next after the success broadcast

After the broadcast at `[r15+0xc0]`, the handler has already (inside the success
block, before the broadcast) built a continuation object from **`pilot_uri`**
(`0x1420845d0`) with three bound callbacks. That continuation is the **pilot
load** — i.e. the next REST call the client makes on success is a **GET against
the `pilot_uri`** returned in this response (the "load pilot" hop), not a fixed
`/pilots` path. The expected on-the-wire follow-up is therefore a request to
whatever absolute URI you put in `pilot_uri`. (If `pilot_uri` is empty/missing
the continuation has nothing to fetch — supply an absolute, same-host URI.)
This is why, for the live test, the next thing to watch for is a GET to the
`pilot_uri` host/path. **Inferred** (the continuation's exact verb/headers were
not fully traced): it is the pilot-resource fetch keyed off `pilot_uri`.

### Why the live client still loops despite a valid `client_id` (E3 + E4)

This is the corrected core finding. The MVP backend returns HTTP 201 with a
top-level numeric `client_id:1` and `deprecated_version:false`, and the
disassembly above shows that body **passes every gate** — the handler would reach
the `"registered"` log, set state `0`, and broadcast success. **So the loop is
not the parse handler rejecting the body.** The observed live behaviour (3×
`/clients` re-POST at ~1–2 s spacing, then a full bootstrap reset re-sending
`startup` telemetry with `run_number++`) has the signature of a **timeout-driven
retry**, not an immediate parse rejection (a parse-level "no `client_id`" would
fall through cleanly and broadcast failure once, not retry on a timer).

The two remaining mechanisms consistent with all evidence (each a concrete test):

1. **The HTTP completion is arriving as `bWasSuccessful == false`** (null response
   → step 2 → state 3..7 → the higher layer retries on its timer, then resets).
   This is fully consistent with: only `/clients` looping while `/auth` and
   `/client-event` "work" (those are fire-and-mostly-forget — the client advances
   off them without strictly requiring a parsed 2xx body, so a marginal HTTP
   framing issue would not stall them but WOULD stall the one endpoint whose
   *parsed* result gates the state machine). **Prime suspects in the MVP's wire
   response, specifically for the `201`:** HTTP/1.1 keep-alive framing /
   `Content-Length` correctness on the 201; an empty or unexpected reason-phrase;
   or libcurl disliking the 201 + body + persistent-connection combination from
   Python's `http.server`. **Test:** (a) return **`200`** instead of `201` for
   `/clients`; (b) send `Connection: close` and ensure exact `Content-Length`;
   (c) capture with TLS keys (`SSLKEYLOGFILE`) and confirm the client ACKs and
   reads the full 201 body before it re-POSTs. If switching to 200 + `Connection:
   close` stops the loop, the gate was transport framing, not JSON.
2. **The registration-success broadcast fires but its subscriber (the next
   bootstrap step) is not the pilot GET we expected** — i.e. the continuation
   needs something we have not supplied and silently stalls until the watchdog/
   timeout resets login. The handler's success path only logs telemetry and
   broadcasts `[r15+0xc0]`; the actual "load pilot/menu" runs in a *separate*
   state-machine tick that polls `[…+0xa0]`. If that tick never sees state `0`
   (because the broadcast object differs, or because of mechanism #1), no GET is
   issued — matching the observation that **no pilots/accounts/staticdata GET is
   ever seen**. **Test:** the same TLS-key capture will show whether the client
   even finishes reading the 201; if it does and still loops, the stall is in the
   continuation and the next lever is the response *body* (e.g. supply a
   fully-qualified absolute `pilot_uri` on the SAME host the client is already
   talking to, and a non-empty `Location`).

**Single best concrete hypothesis to test first:** mechanism #1 — change
`/clients` to **HTTP 200** (not 201), add **`Connection: close`**, keep the bare
top-level `client_id` number, and re-capture. Rationale: the handler treats 200
and 201 identically *for parsing*, but the surrounding UE4 HTTP/libcurl layer and
Python's keep-alive 201 are the one wire-level thing that differs between the
looping `/clients` and the working `/auth` (200). This is cheap and falsifiable.

## 2. The realtime / presence connection

### Finding: there is NO login-time realtime/presence socket (E3/E2/E5) — reconfirmed

A sweep of the connection-state machine and the WebSocket/presence/notification
strings shows the only persistent realtime connection is the **in-match**
`WebSocketNetDriver` (Plane 2, `02-*`). Nothing opens a presence/notification
socket at login.

**2026-05-23 binary scan (E3, reconfirms).** A full byte scan of the shipped
binary for realtime/notification markers found: **`26000` — 0 occurrences**
(neither as ASCII nor UTF-16, neither as a string nor tied to a connect); exactly
**one `XMPP`** (UTF-16) token, which sits adjacent to `HTTP`, `None`,
`/Script/CoreUObject` and the literal `if OSS is server in PIE, OSS requests will
fail` — i.e. it is an **engine-stock OnlineSubsystem service-name** in a name
table, not a Valkyrie chat/notification endpoint (its single xref is a name
registration, not a socket connect); `heartbeat_uri` and `KeepAlive` appear once
each (the backend session keepalive in the pilot object / engine net-driver, not a
login socket). So there is **no game XMPP / notification / messaging server** the
client dials at login.

- **`EVkUIGameStateConnectionState`** (the client's connection-state enum, E2)
  has these values, in order: `Idle`, `IdleSquadMember`, `JoiningCarousel`,
  `CustomSession`, `FindingSession`, `FoundSession`, `WaitingForRunningBattle`,
  `BattleFound`, **`ConnectingToServer`**, **`ConnectionFailed`**, `Quitting`,
  `MapTransition`. The `ConnectingToServer`/`ConnectionFailed` states sit
  **after `BattleFound`** — i.e. they describe connecting to a **battle/game
  server during matchmaking**, not a login-time backend socket. There is **no**
  `ConnectingToBackend`/`ConnectingToPresence`/`Realtime` state.
- **`WebSocketPort` / `GamePort` / `BeaconPort`** (@ the `0x14324exxx` cluster)
  are **UE4 HTML5Networking config-property names** sitting next to
  `UWebSocketNetDriver` / `UWebSocketConnection` and the `Game`/`Party`/`Engine`
  net-driver definition names. They are **net-driver config keys**, not a
  backend-returned realtime endpoint. The match endpoint is delivered as
  **`battleServerUri`** in the battle-server allocation response (`02-*`/`05-*`),
  which feeds UE4's stock `Browse`/`UPendingNetGame` connect — host:port parsed
  from that URI. **The port is not a baked-in integer the client dials at login.**
- **Port 26000 — observed in the capture but NOT sourced from the Valkyrie REST
  layer.** The MVP `sink.py` capture (`logs/sink.log`, `logs/loopback.pcapng`)
  does show the client opening TCP to **:26000** after the `/clients` activity
  (`CONNECT from 127.0.0.1 … first=b''` — connects, sends nothing, waits for the
  server to speak; the pcap shows a sustained 26000↔client flow only because the
  sink held the socket open and emitted bytes). **However:** the string `26000`
  does not exist anywhere in the binary, no `ws://`/`wss://` literal or
  `realtime_uri`/`presence_uri`/`game_port`/`notification_uri` field exists, and
  the connection-state enum has no login-realtime state (below). Therefore the
  26000 probe is **not emitted by VkClientResource or any VGS REST/notification
  code**; the most likely source is a co-resident component (Steam networking /
  SteamNetworkingSockets — `SteamNetworking`/`P2P`/`Relay` tokens are present — or
  another local listener the broad sink attracted). It is **not** the cause of the
  `/clients` loop (the loop is timed and bound to the HTTP `/clients` cycle, see
  §1) and **not** a prerequisite for reaching the menu. The match WebSocket port
  still comes from `battleServerUri` (Plane 2), not a baked-in 26000.
- **`Presence`/`OnlinePresence`/`RichPresence`** strings are UE4's stock
  `OnlineSubsystem` presence (enum values `Online`/`Offline`/`Away`/
  `ExtendedAway`/`DoNotDisturb`, `EOnlinePresenceState`) — platform (Steam)
  rich-presence display, **not** a game realtime channel. No game presence socket.
- **`SessionServiceLog*` / `subscribe`** belong to `/Script/SessionMessages` —
  UE4's editor/SessionFrontend message-bus log subscription (E5). Irrelevant to
  the shipped login path.
- **`Watchdog`** ("Registered with Watchdog process as PID", "Battle Resource
  Created/FAILED") is the **dedicated battle-server's own process watchdog**
  (server-side), not a client login keepalive. (Reclassifies `VkWatchDog` in
  `01-*` from "client heartbeat" to "battle-server process watchdog".)

### Protocol (E5)

When a realtime connection *is* opened (only at match join), it is UE4's
HTML5Networking **WebSocket over TCP** (libwebsockets HTTP `Upgrade: websocket`
handshake), per `02-*` — no game-specific subprotocol required.

### Is it needed for the menu?

**No (P1).** Reaching the main menu requires only the REST chain
(telemetry → SSO → `/auth` → `/clients` → accounts/pilots/static-data). The
realtime/WebSocket connection is opened **only when entering a match**
(`ConnectingToServer` after `BattleFound`). **A re-impl can defer standing up any
realtime/game server** and still get the client to the menu; the realtime server
is needed only for actual matches (Plane 2).

## 3. Connection-state machine & failure → reset (E3/E4)

- The `/clients` handler walks the resource state at **`[this+0xa0]`**: **1** on
  entry (in-flight), **0** on success (or **8** if `deprecated_version` true),
  **2** on HTTP 409, **3..7** on transport failure categories (null response,
  step 2 above). The success path also logs the `"registered"` `client-event`
  checkpoint and broadcasts a `(success, pilot_id)` delegate at `[this+0xc0]`. A
  **separate** state-machine tick polls the state and drives the next bootstrap
  step — the handler itself does **not** issue the pilot GET.
- **Corrected:** the prior write-up said the loop is "the `/clients` parse failing
  for lack of a numeric `client_id`." That cannot be the live cause, because the
  MVP backend returns a numeric top-level `client_id` and (per §1) that body
  passes every gate. The observed loop (3× re-POST at ~1–2 s, then a full reset
  re-sending `startup` with `run_number++`, E4) is **timeout/retry-shaped**, which
  matches a **transport-level completion failure (state 3..7)** or a **stalled
  continuation after a true success broadcast** — see §1's two mechanisms and the
  test plan. It is **not** a realtime socket failing (finding #2: no login
  realtime socket exists).
- For completeness, the REST error-paths that *do* reset login are token-based
  (`03-*`/`01-*`): expired token → `refresh_token` grant; missing refresh token →
  `EVkVrUiQuitType::RELOGIN` ("Failed to find SSO refresh token … log in via
  launcher"). These are distinct from the `/clients` success gate.

## Verified vs. inferred

- **Verified (E3, FULL instruction-by-instruction disassembly @ `0x1420b7d70`,
  re-read 2026-05-23):** the `/clients` completion delegate is `0x1420b7d70`
  (bound at `0x1420b6e9c`); it special-cases **only HTTP 409** (`cmp eax,0x199` →
  state 2); it has a **null-`Response` / `bWasSuccessful==false` guard**
  (`mov rcx,[Response]; test; je 0x1420b87a7`) that routes transport failures to
  the error helper `0x1420b7b40` → states **3..7** **before** any field parse, and
  that helper **broadcasts `success=false` itself** (the transport path does NOT
  reach the main tail broadcast). It parses the **raw body** to one JSON object
  (`0x142038010`) and reads, at the **body top level** (no `content` unwrap):
  `client_id` (**number** getter `0x140a1f650` → `cvttsd2si` → int32 `[+0x14]`),
  `pilot_id` (number → `[+0x18]`), `pilot_uri` (string getter `0x142038980` →
  `[+0x30]`), `callsign` (string → stack), `default_region` (string → `[+0x80]`),
  `deprecated_version` (**bool** getter `0x142038740`, default false), `popups`
  (object-array getter `0x142038840`, elements `unique_name`+`url`). The **single
  success gate is `cmp dword [r15+0x14], -1; je 0x1420b869b`** — a numeric
  `client_id != -1`, with **no other field/condition ANDed in**; success state is
  **0** (or **8** if `deprecated_version` true — still broadcast as success). The
  success block logs `"registered"`, sends `client-event` telemetry (`0x1420c0cc0`),
  and builds the pilot-load continuation from `pilot_uri` (`0x1420845d0`). The
  result is broadcast as `(success = (state & ~8)==0, pilot_id)` on `[this+0xc0]`
  (`0x142095a10`). Missing/optional fields are tolerated; the `Location` header is
  read and optional. **200/201/204 are all accepted** (only 409 branches).
- **DISPROVEN (E3):** the hypothesis that `client_id` is read as a **string**
  (which would make a JSON number fail and leave the `-1` sentinel) is **false** —
  the getter is the number helper `0x140a1f650` and the value is consumed by
  `cvttsd2si` (double→int32), with the `TryGetNumberField` failure-log string. A
  top-level JSON **number** is the correct, accepted type; our MVP's numeric
  `client_id` IS read. The parse gate is therefore satisfied by the MVP body, and
  the live loop is **not** a `client_id` type/parse rejection.
- **Verified (E2/E3):** the connection-state enum (match states only, no login
  realtime state); `WebSocketPort`/`GamePort`/`BeaconPort` are net-driver config
  keys; presence strings are engine-stock `OnlineSubsystem`; **`26000` is absent
  from the binary** and the lone `XMPP` token is an engine name-table entry — no
  login notification/chat endpoint exists.
- **Verified (E4, prior + this capture):** request body shape; the timed
  retry/reset with `run_number++`; and the new fact that **the MVP's 201 +
  top-level numeric `client_id` body satisfies the parse handler yet the client
  still loops** — so the blocker is below/after the JSON parse, not the parse
  itself.
- **Inferred / best hypothesis (not yet re-tested live):** the loop is most
  likely a **transport-level completion failure** specific to the MVP's `201`
  response framing (HTTP/1.1 keep-alive from Python `http.server`), driving the
  null-response path → retry/reset; secondarily, a **stalled success
  continuation**. Switching `/clients` to **HTTP 200 + `Connection: close`** and
  re-capturing with TLS keys is the cheapest decisive test.
- **Could not determine statically:** which of the two mechanisms is active
  (requires a live capture with TLS key logging to see whether the client reads
  the full 201 body and what the HTTP completion status is); the exact value of
  `client_id` (any int != -1 should do); whether `default_region` must equal the
  requested `preferred_region` (handler stores it verbatim and never compares — so
  no, any string is accepted). The 26000 source is not the Valkyrie REST layer and
  is not a menu prerequisite.

## Action for the re-impl (next test, E4)

The parse contract is satisfied; the next test targets the **transport**, not the
JSON. Concretely, for `POST /live/clients`:
1. Return **HTTP `200`** (not 201) with **`Connection: close`** and an exact
   `Content-Length`, body = **bare object** with a top-level numeric
   **`client_id`** (plus `pilot_id` int, absolute `pilot_uri` on the same host,
   `default_region` string, `deprecated_version:false`, `popups:[]`, nested
   `vkpilot`/`balance`).
2. Re-capture with `SSLKEYLOGFILE` set; confirm whether the client **ACKs and
   reads the full body** before re-POSTing. If the loop stops → the gate was the
   201/keep-alive framing. If it still loops after a confirmed full read → the
   stall is in the success continuation; next lever is the response **body**
   (absolute same-host `pilot_uri`, non-empty `Location`), then trace the
   `[this+0xc0]` subscriber.
3. The realtime/26000 socket is **not** required to reach the menu — do not chase
   it for the bootstrap.
