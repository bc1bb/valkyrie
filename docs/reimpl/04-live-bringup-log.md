---
doc: reimpl-live-bringup
title: Live Client Bring-Up Log — First End-to-End Login Against a Private Backend
summary: Live bring-up of the SHIPPED client against the clean-room MVP backend (native Windows, RTX 4070, no VR). Session 1 reached client-registration; SESSION 2 (dated section at the end) BROKE THE /clients WALL and four more, driving the client through the full REST bootstrap and static-data load. /clients needed a non-empty Location header; staticdata must be bare; and the REAL static-data catalog was recovered from the client's OWN shipped pak via a pure-Python pak reader. The current wall is a post-registration "connection-ready" ~30s timeout (no socket, no failing call, no error delegate). Records the verified flow, the OpenSSL/SHA-NI fix, launch recipe, all fixes, tools, and the precise remaining wall.
keywords: [bringup, live, oracle, sso, steam_ticket, clients, registration, location-header, staticdata, pak, getfilelist, heartbeat, sha-ni, openssl, ia32cap, frida, stalker, capture, wall, e4]
status: living
updated: 2026-05-24
evidence: [E4]
---

# Live Client Bring-Up Log

First session driving the **shipped client** (not a mock) against the clean-room
MVP backend (`reimpl/mvp-server`) on a native-Windows / RTX 4070 box with **no VR
headset**. This converts large parts of the paper spec from E2/E3 to **E4 (live
observation)**. Everything below is our own observation of the client's behaviour
and of our own server; no copyrighted bytes are reproduced.

## Milestone: the client boots and logs in (no VR)

Previously the project could not run the client at all. It now boots to its
networking stage in **2D mode** (`hmd_type:"None"`, `is_2d:true`) with no headset,
and drives this sequence against our redirected hosts (all → 127.0.0.1:443):

1. `POST vkpilot.live-valkyrieapi.com/live/client-event` — startup telemetry (fire-and-forget; answer bare `204`).
2. `POST login.eveonline.com/oauth/token` — `grant_type=steam_ticket` + a **real Steamworks ticket** + `intellectual_property=VALKYRIE` + the three `valkyrie/vgs` scopes. We mint an HS256 JWT. **(E4 — confirms `03-authentication.md` end-to-end.)**
3. `POST /live/auth` `{token:<JWT>, provider:"signup"}` → we return the **enveloped** pilot (`{uri,verb,status,message,content:<pilot>, token, provider, signup}`). **Client accepts it** — emits an `"authenticated"` telemetry checkpoint and switches to `Authorization: bearer`.
4. `POST /live/clients` — client registration (rich fingerprint: `client_type`, `preferred_region`, `app_guid`, `distribution_platform:"platform.vive"`, real CPU/GPU, `build_version:"CL 1219446 : LIVE"`). **← current wall.**

Key environment facts confirmed live:
- **Backend domain is `live-valkyrieapi.com`** (the live VGS tenant host
  `vkpilot.live-valkyrieapi.com`), distinct from the telemetry host
  `vkpilot.valkyrieapi.com`. Path namespace is `/live/` (env = live).
- **Launch must go through Steam** — a bare-exe launch never obtains a Steamworks
  auth-session ticket, so the `steam_ticket` grant has nothing to send and SSO
  never fires. Via Steam the ticket is present and SSO succeeds.
- No login-time realtime/notification socket is opened; the only realtime path is
  the in-match `WebSocketNetDriver` (P1). **Proven (E4):** a Frida
  `connect()`/`WSAConnect` trace on a fresh launch (other local projects stopped)
  showed the client make **9 outbound connections, all to 127.0.0.1:443, none to
  26000** — so the client speaks ONLY to the backend on 443; the 26000 traffic
  seen earlier was an unrelated co-resident process. The wall is entirely the
  `/clients` HTTP exchange.

## The unblocker: 2017 OpenSSL SHA-NI crash on modern CPUs

The shipped client's statically-linked 2017-era OpenSSL selects a **SHA-1 SHA-NI
(SHA extensions) assembly** path on CPUs that advertise SHA support. Its Windows
build violates 16-byte stack alignment in that path → `movaps` general-protection
fault → **`0xC0000005` at exe RVA `0x4d463`** on the **first TLS handshake**. In
2017 no consumer CPU had SHA extensions, so this path was never exercised; modern
CPUs (e.g. Alder Lake) take it and crash. Symptom: with the backend reachable the
client connects then crashes ~4 s in, before any HTTP request.

**Fix (verified):** set `OPENSSL_ia32cap=:~0x20000000` in the client's
environment (clears CPUID7.EBX bit 29 = SHA), forcing the older SSSE3/AVX SHA-1
path. Persist it as a user env var so a Steam-launched game inherits it (restart
Steam after setting). This is THE prerequisite to running the title on current
hardware. Diagnosed from the WER minidump (`analysis/scripts/parse_minidump.py`)
+ disassembly of the fault site.

## Working launch recipe (no VR)

1. `OPENSSL_ia32cap=:~0x20000000` present in the process env (user env var; restart Steam).
2. Redirect to 127.0.0.1 (hosts file) + a locally-trusted CA cert covering:
   `login.eveonline.com`, `vkpilot.valkyrieapi.com`, `vkpilot.live-valkyrieapi.com`
   (cert SANs incl. `*.valkyrieapi.com`, `*.live-valkyrieapi.com`). The client's
   HTTP validates against the **Windows cert store** (CurrentUser\Root suffices).
3. Run `reimpl/mvp-server/server.py` on :443 (TLS 1.2 cap for the old client).
4. Launch via Steam (`steam://rungameid/688480`). If the repo holds the game files
   moved out of the Steam library, a directory junction at the Steam `installdir`
   → the repo lets Steam launch the repo copy.

## The remaining wall: `/clients` registration (HONEST status)

The client **re-POSTs `/live/clients` ~3×/cycle then resets the whole bootstrap**
(re-sends startup telemetry, increments `run_number`), never advancing to
pilot/accounts/staticdata and never emitting a `"registered"` checkpoint.

What is **verified by live capture** (do not re-litigate):
- A **TLS-decrypted loopback capture** (server-side `SSLKEYLOGFILE` via `VK_KEYLOG`
  + Wireshark on `\Device\NPF_Loopback`) proves the client **receives a clean
  `HTTP/1.1 200`, correct `Content-Length`, and the exact valid JSON**
  (`{"client_id":1 (number), "pilot_id":1, "pilot_uri":...}`) and closes the
  connection cleanly (FIN/FIN, client-initiated). So it is **not** a transport,
  framing, body-shape, status-code, keep-alive, or cert problem.
- Ruled out by iteration: bare vs enveloped body; `client_id` number vs string;
  200 vs 201; `Connection: close` vs keep-alive; `pilot_uri` path vs query style;
  echoing `X-Correlation-Id`; the realtime/26000 theory.

**RETRACTED — the "Frida disproof" was an RVA bug, not a code-path finding
(2026-05-23).** This section previously claimed the static `/clients` handler at
`0x1420b7d70` was misidentified because Frida hooks "never fired." That was
**wrong**: the hooks used the WRONG RVAs. The functions are at absolute VAs
`0x1420b7d70` / `0x1420b85a8` / `0x1420b7b40` / `0x142038010`; with image base
`0x140000000` their RVAs are **`0x20b7d70` / `0x20b85a8` / `0x20b7b40` /
`0x2038010`**. `frida_clients.py` hooked `base+0xb7d70` etc. (the leading `0x2`
hex digit was dropped), i.e. VA `0x1400b7d70` — an unrelated/cold address — so
nothing fired (the `recv` control hook fired fine, hiding the mistake). The
static handler at `0x1420b7d70` is **correct** (re-confirmed by disassembly: it is
the sole completion bound at the `/clients` builder `0x1420b6e9c`, reads the
`Location` header + body, and gates on `client_id != -1` before logging
`"registered"`). `frida_clients.py` and `docs/networking/16` have been corrected.
**Re-run with `base+0x20b7d70` and it WILL fire.** The genuinely-open question
(why the client loops despite a passing body) is therefore *still* to be answered
live — but now by hooking the RIGHT address and reading which arm it takes
(gate pass → `"registered"`/continuation, vs null-`Response` → transport-fail
`0x20b7b40`), not by re-searching for a "real" handler that was never lost.

Also observed: the client's HTTP uses **async I/O** (`recv` is never called →
`WSARecv`/overlapped, consistent with statically-linked libcurl/OpenSSL, not the
loaded WinINet).

## Precise next step (for a live session with the user present)

1. Relaunch via Steam so a **fresh `/clients`** is issued (the in-game error
   screen stops auto-retrying after a few attempts; a tap of Enter on the dialog
   re-attempts `/clients` *sometimes*, but a clean relaunch is reliable).
2. With Frida already attached (it works here), **Stalker-trace** the module
   around the `/clients` HTTP completion, or hook the real HTTP-completion site,
   to find the actual handler and the true success/transition condition — then
   read what field/state/header it really requires. The MVP backend can then be
   corrected and the client should advance to the pilot/staticdata load and the
   main menu.

## Tooling proven this session (reusable)

- `analysis/scripts/parse_minidump.py` — WER minidump → exception + registers + module list.
- `analysis/scripts/frida_clients.py` / `http_stack_id.py` — live hooking (Frida 17 works on this client; use `Process.getModuleByName(...).base` for RVAs).
- TLS-decrypted loopback capture: server `keylog_filename` (`VK_KEYLOG`) + `dumpcap -i \Device\NPF_Loopback` + `tshark -o tls.keylog_file:...`.
- `reimpl/mvp-server/sink.py` — logging TCP sink for probing unexpected ports.

---

# Session 2 (2026-05-23): the `/clients` wall broken + four more — login bootstrap solved through static data

This session drove the client far past `/clients`. Five distinct walls were
root-caused and fixed; the client now completes the entire REST bootstrap and
loads its static-data catalog. Each fix is reflected in `reimpl/mvp-server/server.py`.
Launch args observed (UE4 crash context, E4): `-steam -2d -tenant=live`,
**UE 4.14.3 Shipping**.

## Full live login flow now reached (E4)

```
client-event(startup) → POST /oauth/token → POST /live/auth → POST /live/clients(registered)
→ GET /live/pilots/1 → POST /live/pilot-lookup → GET vgs-tq.eveonline.com/v2.0/valkyrie/accounts/
→ GET /live/staticdata (manifest) → [static data resolved from local pak]
→ PUT /live/clients/1 ×N (heartbeat) → DELETE /live/clients/1  ← CURRENT WALL ("Network error")
```

Per-endpoint **framing differs**: `/auth`, `/pilots`, `/accounts`, `/pilot-lookup`
are accepted **enveloped** (`{uri,verb,status,message,content,…}`); `/clients`
and `/staticdata` (GetFileList) require **bare** top-level bodies.

## Wall 1 — `/clients` registration: a non-empty `Location` header is REQUIRED

Confirmed the handler is `0x1420b7d70` (RVA `0x20b7d70`) by re-running Frida with
the corrected RVA + a Stalker call-trace of the function. Disassembly of the real
flow (which diverges from `networking/16` §1):

- After the HTTP-409 check the handler calls **`GetHeader("Location")`** and
  **case-insensitively compares the value to the empty string** (ref byte at
  `0x143103ed3` == `0x00`). If `Location` is empty/absent → `je 0x1420b86d2` →
  it **skips the body parse entirely** (`call 0x142038010` at `0x1420b7f66` never
  runs) and broadcasts FAILURE via `0x142095a10` with the resource state still `1`
  (`success=((state&~8)==0)` is false) → the client retries 3× then resets.
- A **non-empty `Location`** makes it fall through, parse the bare body, read
  `client_id` via `TryGetNumberField` (`0x140a1f650`) → `[r15+0x14]`, pass the
  `client_id != -1` gate, log `"registered"`, and build the pilot-load
  continuation from `pilot_uri`.

**`networking/16`'s "empty/absent Location is fine" was BACKWARDS.** Fix: `/clients`
returns `200` + `Location: <client-resource-uri>` + bare top-level numeric
`client_id`. Verified live: PARSE/GATE/`"registered"`/continuation all fire; the
client then issues `GET /live/pilots/1` — its first request ever past registration.

## Wall 2 — `staticdata` (GetFileList) must be BARE

The GetFileList parser wants a **top-level `files` array** ("No 'files' array in
response to GetFileList", `networking/10`); `StaticDataDownloadFailed` is
login-blocking. Enveloping hid `files` inside `content` → the client retried then
`DELETE`d its registration ("Network error"). Fix: serve `staticdata` **bare**.

## Wall 3 — static-data CONTENT: recovered the REAL catalog from the client's own pak

Static data is a versioned, keyed catalog the client needs to build the menu.
Rather than guess it, it was recovered from the shipped pak:

- **`WindowsNoEditor/VkGame/Content/Paks/VkGame-WindowsNoEditor.pak`** is a UE4
  pak **version 3, UNENCRYPTED** (no encryption markers in the exe), 22 494 files,
  mount `../../../`.
- It ships the genuine **`VkGame/Content/StaticData/**/*.json`** as **plain
  uncompressed JSON** (43 files: Currency, GameMode/GameModes+Wormholes,
  HeroShips/{Covert,Fighter,Heavy,Support,NPC,NonTechTreeShips}, Maps, Implants,
  Leagues, Reputation, Scoring, Popups, PilotCosmetics, HeroCosmetics, IAP,
  GlobalBoosters, LootCapsules, Platforms, DailyChallenges, RewardTiers — each
  with a `Schema.json`).
- **Format:** top-level `{schema, uniqueName, dbID, displayName, <categoryArray>}`;
  entries keyed by `uniqueName`/`dbID` (e.g. `currency.visk`, `shipclass.Fighter`).
- New pure-Python tools (no UnrealPak needed): `analysis/scripts/pak_list.py`
  (parse footer→index, list files) and `pak_extract.py` (extract uncompressed
  entries; data at `offset + 53` for v3 method=0). Extracted to
  `reimpl/mvp-server/staticdata_real/`.
- `server.py` now builds the GetFileList manifest from those files (md5 checksums —
  md5 is the accepted algorithm) and serves each file's raw bytes at
  `/live/staticdata/<relpath>`. The client's filenames match our relative paths.
- A user-supplied copy of the same `StaticData/` tree is **byte-identical** to the
  pak extraction (independent confirmation).

**Key behaviour:** because our manifest checksums equal the md5 of the pak files,
which are the client's OWN local copies, the client compares, sees a match, and
**uses its local static data without downloading anything** — correct behaviour.

## Wall 4 — `heartbeat_seconds` controls the give-up timeout

The pilot/client objects carry `heartbeat_seconds`. Setting it to `30` made the
client send **6** `PUT /clients/1` heartbeats (~30 s) before giving up, vs **3**
(~15 s) at the default — so this value sets the **timeout window** of the final
wall (below). The 5 s PUT interval is separate/fixed.

## CURRENT WALL — a post-registration "connection-ready" timeout (NOT static data)

After the (locally-resolved) static-data load, the client makes **no new request
types** — it just heartbeats `PUT /live/clients/1` for `heartbeat_seconds`, then
`DELETE`s its registration and shows **"Network error"** (followed by a secondary
null-singleton crash at exe RVA `0x23f983`, deref of null global `0x143899158` — a
teardown symptom, not the cause).

Proven by a safe Frida probe (`analysis/scripts/connection_probe.py`,
function-entry hooks + `Thread.backtrace` + ws2_32 export hooks):
- **No socket** — every `connect`/`WSAConnect` is to `127.0.0.1:443` (the REST
  calls; we send `Connection: close` so each is a fresh socket). No game/chat/
  notification socket is opened in this phase. (The Session-1 "only :443" claim
  was taken *before* `/clients` was fixed, so the client never reached here — this
  re-confirms it properly.)
- The "Network failure" UI delegate handler `0x1404735f0` (subscribed to
  `[global 0x143a9ee18 + 0x850]`, success pair `0x140474140` at `+0x7e0`) **never
  fires** — so the error is NOT that path. It is a **silent login-state-machine
  timeout**: the client waits `heartbeat_seconds` for an internal "ready"
  transition that never arrives.
- Identical outcome with an EMPTY static-data stub and the FULL real catalog →
  the wall is **not** static-data content.

**Next investigation (deferred):** find what flips the client to "ready/connected"
within the heartbeat window — hook the `PUT /clients/1` completion + the
give-up/`DELETE` path with backtraces, or test whether the heartbeat response must
convey a state field. Candidates: a `state`/`status` field in the `/clients` or
heartbeat response; an account-state/entitlement field in the `vgs-tq` accounts
response (currently a stub); or an internal completion the client polls for.

## Tooling added this session (reusable)

- `analysis/scripts/pak_list.py` — list a UE4 v3 pak's file index (footer→index parse).
- `analysis/scripts/pak_extract.py` — extract uncompressed pak entries by path substring.
- `analysis/scripts/clients_stalker.py` — Stalker call-trace of a function (SAFE: JITs a copy, no code patching) — used to recover the real `/clients` handler flow.
- `analysis/scripts/connection_probe.py` — connect/WSAConnect + delegate-handler backtraces (SAFE).
- `analysis/scripts/disasm_func.py` — works on this box with Capstone 5.0.7 (Python 3.14).

**Frida safety note (learned the hard way):** hook only **function-entry**
addresses and read **registers**; do NOT call vtable functions from a hook
(crashes with a jump-to-0) and do NOT inline-hook mid-function/guessed addresses
(corrupts the relocated code → crash). Stalker is the safe way to trace flow.

---

# Session 3 (2026-05-24): the static-data wall localized to a completion-notification gap

This session attacked the post-registration wall hard. It did **not** fall, but it
was converted from "a mysterious silent ~30 s timeout" into a **precisely-located
completion-notification gap** in the static-data resource, with the exact next RE
target identified. Every empirical avenue and several disassembly layers are
recorded below so the next session starts at the frontier, not the dead ends.

## The wall is the static-data step (confirmed), not a generic post-login wait

The full live request sequence, identical every launch (E4):

```
client-event(startup) → POST /oauth/token → POST /live/auth
→ POST /live/clients (registered) → GET /live/pilots/1 → POST /live/pilot-lookup
→ GET vgs-tq…/v2.0/valkyrie/accounts/ → GET /live/staticdata (GetFileList manifest)
→ [files resolve from the local pak; 0 downloads when md5 matches]
→ PUT /live/clients/1 ×~6 (heartbeat, ~heartbeat_seconds) → DELETE /live/clients/1
→ "A NETWORK ERROR HAS OCCURRED"
```

The on-screen message stays on **"DOWNLOADING STATIC DATA"** the whole time (so the
active step is static data, confirmed by the user). The terminal error is
`LoginMessage_StaticDataDownloadFailed` / `LoginMessage_GenericTimeout` (both map to
the FText "A NETWORK ERROR HAS OCCURRED"). The `PUT /clients/1` beats are just the
keepalive running while the login state machine waits for a "static-data ready"
transition that never arrives; after `heartbeat_seconds` it gives up and `DELETE`s.

## Login-flow vocabulary recovered (FText keys → display text, E2)

Order (by chained keys + the live screens): `LoginMessage_Privileges` ("CHECKING
ACCESS") → `LoginMessage2` ("DOWNLOADING STATIC DATA") → `LoginMessageDownloadStoreData`
("DOWNLOADING STORE DATA") → `LoginMessage7` ("CHECKING FOR PURCHASES") →
`LoginMessage14` ("CONNECTING TO THE CLOUD"). Failure/terminal: `LoginMessage_StaticDataDownloadFailed`
and `LoginMessage_GenericTimeout` both = "A NETWORK ERROR HAS OCCURRED";
`LoginMessage10`="SSO LOGIN FAILED", `5`="LOGIN FAILED", `12`="LOGIN FAILED - INVALID
USERNAME/PASSWORD", `8`="NO OCULUS ENTITLEMENT", `4`="NO VR HEADSET DETECTED",
`1`="OFFLINE PLAY REQUESTED". The client **never reaches** store-data/purchases — it
dies on static data.

## The GetFileList completion `0x14209b550` — read instruction-level (E3)

Located via direct xrefs to the manifest field strings `branch_name` (`0x143105f30`,
read at `0x14209b68c`) and `build_number` (`0x143105f60`, at `0x14209b6fb`) — the
`FVKStaticDataResource` log strings ("No 'files' array in response to GetFileList"
`0x143106700`, "File object didn't contain required fields" `0x1431063e0`, "filename"
`0x143106ea8`) are **linker-pooled and have NO direct xref**, which is why earlier
string-anchored searches failed. The completion (`this`=`r15`, Request=`r12`,
Response=`r14`/`r8`) does, in order:

1. **Null-Response guard** (`cmp [r8],0; je 0x14209bc6a`) → transport-failure path.
2. Reset a per-resource int32 array (`data=[r15+0xd0]`, count `[r15+0xd8]`) to `-1`.
3. `GetContentAsString` (vtbl `+0x50`) → parse body via **`0x142038010`** into a
   `FVkJsonObject` at `[rbp+0x60]`. (So the manifest IS parsed by `0x142038010`; a
   Frida arg-sniff of that function earlier missed it because the body sits behind
   stack-held `FString` pointers, not in a directly-readable register.)
4. Read **`branch_name`** + **`build_number`** (string getters); used only to log
   `"CL %d : %s"` — **not a gate**.
5. `TryGetObjectArrayField("files")` (`0x142038840`); if absent → skip the loop.
6. **files loop:** per entry read **`filename`/`checksum`/`uri`** (all three required,
   else the entry is skipped — that's the "File object didn't contain required fields"
   path); register each valid entry via `0x1420829e0` into the manager at `resource+0x90`
   and append to a local list `[rbp+0x80]` (count `[rbp+0x88]`).
7. **Success gate (`0x14209bc50`): `bl = (Response != null) && ([rbp+0x88] − [rbp+0xb4] > 0)`.**
   `[rbp+0x88]` = count of valid file entries (26); `[rbp+0xb4]` is init-0 and never
   rewritten → **`bl = 1` = SUCCESS** (confirmed live: probe read `successGate=PASS(1)`).
8. **Listener-notify block** (`0x14209bc6c`): `cmp [r15+0x30],0; je 0x14209bd30` — only
   if `res+0x30 != 0` does it call the listener at `[res+0x20]` (vtbl `+0x38/+0x48/+0x68`).

## The decisive live finding (probe `staticdata_probe.py` v4 @ `0x14209b550`)

- `successGate = PASS(1)` — GetFileList **succeeds**.
- **`listener[this+0x20] = NULL` and `res+0x30 = 0`** at completion → step 8's
  notify block is **SKIPPED**. GetFileList completes but **notifies no one**.
- A 32-slot int32 array at `[res+0xd0]`/`[res+0xd8]` held 17 non-`-1` members, static
  over 40 s. Initially mis-read as the file tracker — but its count is 32 while the
  manifest has 26, so it is **not** the manifest download tracker; disregard it.

## Ruled out this session (live A/B — do NOT re-test)

- File **content** (empty stub vs full catalog — identical outcome).
- File **count / `Schema.json`**: manifest of 43 (incl. 17 `Schema.json`) vs 26 (data
  only) — both stall; the client fetches exactly the 26 data files and never requests
  a `Schema.json`. Excluding them from the manifest did not help.
- **Download vs cache-hit**: `VK_SD_FORCE_DOWNLOAD=1` (cache-bust md5 so all 26 download
  with valid integrity) vs off (0 downloads, all cache-hit) — both stall identically.
- A required **`Location` response header** (the `/clients` fix): added to the manifest
  AND every file response — no change. GetFileList does not share that gate.
- A **new socket** ("connecting to the cloud" to an un-redirected host): Frida
  connect/WSAConnect — every connection is `127.0.0.1:443`.
- **md5 / extraction correctness**: re-extracted all 43 StaticData JSONs from the live
  `VkGame-WindowsNoEditor.pak` and md5-compared to `reimpl/mvp-server/staticdata_real/`
  → **43/43 exact match, 0 mismatch**. Our served bytes ARE the client's pak bytes, so
  the cache-hit (0-download) behaviour is correct and integrity is a non-issue.

## Correction to prior sessions

`0x143a9ee18` is **GEngine** (UE4 global engine). `+0x7e0` = `TravelFailureEvent`,
`+0x850` = `NetworkFailureEvent` — BOTH engine *failure* multicast delegates
(subscribed handlers `0x140474140` / `0x1404735f0`); there is **no "success pair."**
Neither fires at login (no map travel), consistent with the silent timeout. The
earlier "connection-singleton success/failure" framing (Session 1/2 / memory) was a
misread and is retracted.

## Refined wall + the exact next target

GetFileList succeeds and the files resolve correctly from the pak, but the static-data
resource's **completion notification never fires** (`res+0x20` listener NULL /
`res+0x30 == 0`) → the login/frontend flow is never told "static data ready" → it sits
on "DOWNLOADING STATIC DATA" until the `heartbeat_seconds` timeout. **Next session:
find what SETS `res+0x20` (the completion listener/delegate) and `res+0x30` on
`FVKStaticDataResource` — i.e. how the login flow subscribes to the "done" signal —
and why it is unset at completion.** Likely the login flow must attach a listener that
depends on a field we do not yet supply (in the pilot / accounts / clients responses),
or it polls a resource "ready" state we never set. Trace writes to `[res+0x20]` /
`[res+0x30]`, and disassemble the resource constructor and the frontend static-data
step. Resource completion = `0x14209b550`; manager init `0x142094440`; per-file
register `0x1420829e0`.

## Tooling added/used this session

- `analysis/scripts/staticdata_probe.py` — SAFE Frida resource-state probe: hooks the
  GetFileList completion `0x14209b550`, confirms the success gate live, resolves the
  listener vtable methods, and polls the resource's per-file state array. (Evolved
  through v1–v4; v4 is the resource-state reader.)
- `analysis/scripts/scan_callers.py` — byte-scan `.text` for `E8` callers + RIP-relative
  `lea`/`mov` loads of a target VA (used to xref strings and the binder glue).
- Server: `reimpl/mvp-server/server.py` gained `VK_SD_FORCE_DOWNLOAD` (env-gated, off by
  default — appends a newline to each served file so its md5 differs from the pak copy,
  forcing a real download+validate while keeping integrity valid) and now advertises
  only the 26 catalog files in GetFileList (excludes the 17 `Schema.json`). The
  `Location` header on `/staticdata` responses was a disproven experiment (can be reverted).

---

# Session 4 (2026-05-24): MAIN MENU REACHED — the wall was one game-instance byte, not static data

This session **broke the login wall and reached the interactive main menu** (2D,
RTX 4070, no VR). It also **retracts the entire Session-3 framing**: the static-data
"completion never fires / listener NULL" story was a *measurement error*, not a real
defect. Static-data completion works end to end. The true wall was a single secondary
gate byte on the game instance.

## The retraction (important — do not revive the old theory)

The Session-3 probe read `this+0x20` at the manifest completion `0x14209b550`
*assuming `this` is the static-data resource*. It is actually the static-data
**manager**. A corrected live probe (`analysis/scripts/login_advance_probe.py`,
function-entry hooks + memory reads only) shows at that completion:
`this(mgr)+0x20` is a **valid listener pointer**, `+0x30 == 3` (bound), the login
completion delegate `0x1406e5780(login, success=1)` **fires**, and the login flag
`login+0x899` ("static data done") **is set to 1 naturally**. So static data
completes correctly. The old "listener NULL" reading was reading a string buffer on
the wrong object.

## The real wall (E4, instruction-level + live-confirmed)

The login flow is a small state machine: object `login`, ticked by `0x1406e9200`;
state enum at `login+0x890`; per-step timer at `login+0x894`; jump table `0x1406e9344`.
Observed states: 0 → 1 **CHECKING ACCESS** (`0x1406ec060`) → 2 **DOWNLOADING STATIC
DATA** (`0x1406ec6a0`) → 3 **DOWNLOADING STORE DATA** (`0x1406ec830`) → 4 → 7 → (8
done). Each step shows a message, waits a 0.5 s min-dwell (`0x1427ce048`), then
advances when its "done" byte is set; on a 30 s timeout (`0x1427bc2d4`) it drops to
state 9 ("LOGIN FAILED" / the on-screen "A NETWORK ERROR HAS OCCURRED").

The state-2 handler requires **two** conditions to advance to state 3:
1. `login+0x899 != 0` — static-data done. **Satisfied live.**
2. A **secondary gate**: `call 0x1404e6650` (game-instance accessor) then
   `cmp byte [rax+0x19d0], 0` — i.e. **`GameInstance+0x19d0 != 0`**. **NOT satisfied
   live** → falls into the 30 s timeout branch → state 9.

So `byte899` was a red herring; the lone blocker is `GameInstance+0x19d0`.

## The decisive experiment → the menu

A safe Frida single-byte write — forcing `GameInstance+0x19d0 = 1` at state 2, with
no other change — cascaded the **entire** login forward:

```
state 2 -> 3 (login+0x89a "store done" set naturally) -> 4 (login+0x89b set) -> 7
```

The client then fetched `GET vgs-tq/v2.0/valkyrie/stores/7/offers/`, emitted
new-player checkpoints (`NewPlayerSelectedMale`), fetched `GET /live/hero_survival/1`,
reached `POST /live/sessionrequests`, and **rendered the interactive main menu**
(screenshot `mvp-server/logs/menu_reached.png`), heartbeating `PUT /live/clients/1`
every 5 s — **stable for ~3 minutes with clean 200s, no crash** (it later closed with
no WER dump; benign). Conclusion: **every login step except this one byte already
completes against the MVP stub.** The MVP backend is, modulo this gate, sufficient to
boot the shipped client to its menu.

## What sets `GameInstance+0x19d0` naturally (the clean, Frida-free fix — in progress)

RE of the setter (clean-room, `reimpl/07-gameinstance-storedata-gate.md`): the only
real writer is `0x1404ee426` inside `0x1404ee230`, the **store/catalog subsystem's
update/ready callback** (delegate at `subobj+0x720`, `subobj = GameInstance+0x18c0`).
It runs only when that subobject is attached and ticks; the attach (`0x1404f2b50`,
which also calls the store loader `0x14209cc40`) is driven by the **online/session
update pump `0x14036a670`** once the session sub-state is "ready"
(`session+0x870 != 0`, global byte `0x143851965` set, a vtable predicate true). So
`+0x19d0` means *"the store/catalog subsystem exists and has ticked"* — one step
downstream of the **online/session state machine** reaching post-login ready. The
open task is to find which server-observable response/field flips `session+0x870` so
the store subsystem attaches on its own. That makes the menu reachable with no Frida.

## Tooling added this session (reusable)

- `analysis/scripts/login_advance_probe.py` — login-state probe + safe one-byte
  force-write: hooks the tick driver `0x1406e9200` (state/timer/flags), the manifest
  completion `0x14209b550` (re-reads the manager listener — disproving the NULL
  theory), the login completion delegate `0x1406e5780`, and the game-instance
  accessor `0x1404e6650`; forces `GameInstance+0x19d0=1` to confirm the cascade.
- `analysis/scripts/scan_19d0.py` — classify read/write instruction encodings of a
  struct displacement (find writers of a field offset).
- `analysis/scripts/find_wstr.py`, `find_disp.py`, `read_f32.py` — PE-aware string/
  displacement/float locators.

---

# Session 5 (2026-05-24): the `+0x19d0` natural trigger traced to a VR-platform login — NO pure-server fix

Goal this session: set `GameInstance+0x19d0` *naturally* (no Frida) so the menu is
reached with a server change alone. Outcome: the trigger was traced end-to-end and
shown to be **client/VR-platform-bound, not server-observable.** This is a documented
known-limitation, not a remaining server task. (Decision: stop here; do not patch the
client. A runtime gate-patch is the realistic clean boot path but was deferred.)

## The natural-trigger chain (clean-room RE + live, decisive)

```
GameInstance+0x19d0 (the login wall)
  ← set ONLY by the store/catalog subsystem update callback 0x1404ee230
    (byte-scan: 0x1404ee426 is the sole `mov byte[+0x19d0],1`; bound as a delegate
     at store-attach via the lea at 0x1404f2c18)
  ← fires only after the store offers catalog LOADS
  ← the /stores/7/offers GET issuer 0x14209f650 (URL builder 0x14209eb60,
     parser 0x14209ed00); initial-request fn 0x14209ea60, paginate fn at 0x14209f4ff
  ← dispatched by an internal subsystem WORK-QUEUE processor 0x1407f01e0
     (iterates items at [this+0xab8], stride 0x1b0) — sole caller of 0x14209ea60
  ← the queue is populated only once the online/OSS layer reaches post-login "ready"
  ← OnlineSubsystem "logged-in" latch: tick 0x1402e4f60 calls latch 0x1402f0d00
     EVERY frame; latch self-gates on byte[OSS+0x858] then forwards into the
     login-complete delegate (call [cb+0x4f0] @0x1402f0d48)
  ← OSS+0x858 is written ONLY through the reflected UPROPERTY bool-setter thunk
     0x1403aeb70 (no static store) — i.e. on the OSS login-complete event.
```

The state-3 kick `0x1420d6a70` (tail-jmp'd from the state-2 handler at the 2→3 edge)
is a *separate, later* store load that itself requires `+0x19d0` already set — so it
is NOT the first-time trigger (chicken-and-egg). The first-time trigger is the
work-queue dispatch driven by the OSS login.

## Live evidence (read-only probes)

- `+0x858` reflected setter `0x1403aeb70` **never fires** across a full login
  (states 0→1→2→9). So the OSS login-complete event never happens in 2D.
- The candidate `-vr`/HMD global `0x143851965` reads **1** at login time, and the
  store subobject **attach** `0x1404f2b50` **does** run — so those co-gates are
  satisfied; the missing thing is purely the OSS login-complete → queue → load.
- Static-data **does** complete (`login+0x899=1`); the only unsatisfied state-2 gate
  is `GameInstance+0x19d0` (re-confirmed). Forcing that byte alone reaches the menu
  (Session 4).

## Conclusion (E4 + E3): platform-bound, not server-fixable

The login path expects a **VR-platform identity login** (the VkGame OnlineSubsystem
reporting logged-in via UE reflection) to complete; that drives the work-queue that
loads the store catalog, whose update callback sets the gate byte. In **2D / no-VR /
no-headset**, that platform login never completes, so the gate stays 0. **No REST
response our backend can send triggers it** — the catalog GET has no server-checkable
precondition of its own, and the client never issues a `/sessionrequests` during
login. The clean-room MVP backend is otherwise sufficient: every REST step the client
makes (oauth/auth/clients/pilots/pilot-lookup/accounts/staticdata + heartbeats) is
satisfied, and the only blocker is this client-side platform gate.

**Clean boot path — BUILT & VERIFIED (`tools/vk_boot_patch`):** a tiny dependency-free
Rust `.exe` that NOPs the gate's conditional jump in **live process memory** (never
touches the game file): at main-module RVA `0x6ec701` the bytes `74 59` (`je <timeout>`)
→ `90 90`, with original-byte verification (refuses to write on a non-matching build)
and a `--revert`. Verified end-to-end with **NO Frida**: backend on :443 → run patcher →
launch via Steam → the client logs in, fetches `/stores/7/offers` + `/hero_survival/1`,
and **renders the main menu** (`mvp-server/logs/menu_via_patcher.png`; patcher confirmed
reading `74 59` then writing `90 90` against the live process). This is the standard,
reversible preservation technique for a platform-gated VR-only title run in 2D — we ship
only our own tool, never any game bytes. (Note: after reaching the menu the client
auto-closes after a few minutes with no crash dump — a separate menu-phase/new-player-flow
behavior, not a login issue.)

## Frida safety lesson (reusable)

Hooking the OnlineSubsystem **constructor** `0x140359060` (a very early init path)
**crashes the 2017 binary on attach** (observed twice: the game process exits before
any hook fires). Capture early objects from a later tick instead (e.g. vtable-scan the
args of `0x1402e4f60`), and **attach only once the process is stable** (RAM > ~400 MB,
past the fragile init window) — `oss_login_poll.py` does both. The login-tick
(`0x1406e9200`) and resource-completion hooks used earlier are safe.

## RE docs produced (clean-room, copyright-free)

`reimpl/05-staticdata-resource-lifecycle.md`, `reimpl/06-login-statemachine-staticdata.md`,
`reimpl/07-gameinstance-storedata-gate.md` (sections A–T cover the GameInstance gate,
the online/session ready sub-state, the OSS logged-in trigger, and the decisive
store-attach→fetch precondition). Probes: `login_advance_probe.py`, `oss_ready_probe.py`,
`oss_login_poll.py`; scanners `scan_19d0.py`/`scan_858.py`/`scan_870.py`/`scan_glob.py`.
