---
doc: reimpl-login-statemachine
title: Login State Machine and the Static-Data "Ready" Gate
summary: Clean-room reconstruction of the client's login progression as a tick-driven state machine over a small enum field, dispatched through a jump table. Each step shows a localized message, subscribes a completion DELEGATE for the asynchronous work it kicks off, then POLLS a per-step boolean each tick until that delegate flips it. The "DOWNLOADING STATIC DATA" step (state 2) polls a boolean (login+0x899) that is only ever set by a static-data-complete delegate; that delegate is never broadcast in our bring-up (the resource's listener is NULL), so the boolean stays 0 and the 30s dwell timer (login+0x894 vs 30.0) trips the "A NETWORK ERROR HAS OCCURRED" failure. Documents every VA, the jump table, the three per-step booleans and their setter delegates, the timer constants, and the concrete levers to advance.
keywords: [login, state-machine, staticdata, jump-table, delegate, multicast, ready-flag, timeout, heartbeat, LoginMessage2, completion, gate]
status: living
updated: 2026-05-24
evidence: [E4]
---

# Login State Machine and the Static-Data "Ready" Gate

All addresses are virtual addresses in the shipped client (image base
`0x140000000`). This is our own description of observed control flow; no
copyrighted bytes are reproduced. The login-flow object pointer is referred to
below as `login`; its first-seen anchor field is the embedded subsystem pointer
`login+0x710`, the UI/widget object is `login+0x880`, the active message FText
slot is around `login+0x8b0`, the state enum is `login+0x890`, and the per-step
timer (a float accumulator, seconds) is `login+0x894`.

## 1. The tick / dispatch driver — `0x1406e9200`

The login object is ticked once per frame. The tick function at `0x1406e9200`:

1. Accumulates the frame delta into the per-step timer:
   `login+0x894 += dt` (`addss` against `login+0x894`, then stored back). This
   is the single timer the step handlers compare against; it is NOT reset to
   zero on every state change in a way that resets the static-data wait — it is
   the same accumulator the failure branch reads.
2. Loads the state enum `login+0x890` (a 64-bit field, values `0..0xA`), bounds-checks
   `> 0xA`, and dispatches through a **jump table** at `0x1406e9344`
   (`movsxd`/`jmp rcx` against `base 0x140000000`).
3. Each table entry tail-jumps to a dedicated **step handler** with `rcx = login`.

Recovered jump-table targets (state value → handler):

| state | handler VA    | role / message shown                                   |
|------:|---------------|--------------------------------------------------------|
| 0     | `0x1406ec8e0` | initial / idle                                         |
| 1     | `0x1406ec060` | CHECKING ACCESS (`LoginMessage_Privileges`)            |
| 2     | `0x1406ec6a0` | DOWNLOADING STATIC DATA (`LoginMessage2`)              |
| 3     | `0x1406ec830` | DOWNLOADING STORE DATA (`LoginMessageDownloadStoreData`)|
| 4     | `0x1406ebf70` | (later step)                                           |
| 5     | `0x1406ec110` | privileges/headset branch (`LoginMessage4` "NO VR HEADSET")|
| 6     | `0x1406ece00` | (later step)                                           |
| 7     | `0x1406ecdc0` | (later step)                                           |
| 8/def | `0x1406ec270` | DONE (`LoginMessage3` "DONE")                          |

Each handler first calls the message setter `0x1406e7ed0(login, FText)` — this
writes the localized login message into the UI widget at `login+0x880`
(`+0x8b0` is the FText property it pushes). That is purely cosmetic; it does not
advance anything.

## 2. The uniform per-step pattern: subscribe a delegate, then POLL a boolean

The model is **subscribe + poll**, not pure-poll and not callback-only:

- A step kicks an asynchronous subsystem load and SUBSCRIBES a completion
  delegate (a member-function pointer bound to `login`) onto a multicast
  delegate on the subsystem.
- The completion delegate, when broadcast, sets a **per-step boolean** on
  `login` (and, on the failure overload, instead sets the failure message and
  state enum 9).
- The state handler for the WAITING step then POLLS that per-step boolean every
  tick and advances the enum only once it is set (subject to a 0.5s minimum
  dwell and a 30s timeout).

The three per-step booleans and the delegates that set them:

| step                 | polled boolean | completion delegate (sets it) | failure overload effect           |
|----------------------|----------------|-------------------------------|-----------------------------------|
| CHECKING ACCESS      | `login+0x898`  | `0x1406df640` (`byte[+0x898]=1`) | —                               |
| DOWNLOADING STATIC   | `login+0x899`  | `0x1406e5780` (success: `byte[+0x899]=1`) | else `LoginMessage_StaticDataDownloadFailed`, state=9 |
| DOWNLOADING STORE    | `login+0x89a`  | `0x1406e5850` (success: `byte[+0x89a]=1`) | else `LoginMessage_StoreDataDownloadFailed`, state=9 |

The static-data and store-data delegates share a signature `(this=login,
bool success)`: a non-zero `success` byte takes the "set my ready boolean and
return" path; a zero `success` takes the "set the *DownloadFailed* message and
state=9" path. So a single broadcast both unblocks the wait AND carries
the success/failure verdict — there is no separate error delegate.

### Where the delegates are subscribed (the listener binding)

The subsystem accessor `0x1420d6cf0` returns the global static/store-data
subsystem object at `0x143ab9858`. Subscriptions are added via the
delegate-bind helper `0x1419a9080(multicast, this, &fnptrDescriptor)`, which
constructs a `TBaseDelegate`-style record (vtable `0x1428435e0`) from the
(function pointer, `login`) pair and links it onto the multicast list.

- The **CHECKING ACCESS** handler (`0x1406ec060`), on its success transition,
  writes the static-data completion delegate `0x1406e5780` into a stack
  descriptor (`lea ...->0x1406e5780`), sets `login+0x890 = 2`, subscribes it on
  `subsystem(0x143ab9858)+0x270`, and tail-jumps to the **static-data load
  kicker** `0x1420d6930`. So the static-data completion listener is wired up at
  the moment we LEAVE "checking access" and ENTER "downloading static data".
- The **DOWNLOADING STATIC DATA** handler (`0x1406ec6a0`), on its success
  transition, writes the store-data completion delegate `0x1406e5850`, sets
  `login+0x890 = 3`, subscribes it on `subsystem+0x2b0`, and tail-jumps to the
  **store-data load kicker** `0x1420d6a70`.

`subsystem+0x270` is therefore the static-data "load-complete" multicast that,
when broadcast, must invoke `0x1406e5780` and flip `login+0x899`.

## 3. The DOWNLOADING STATIC DATA step in detail — `0x1406ec6a0`

Control flow of state-2's handler (the screen the client is stuck on):

1. Set the on-screen message to `LoginMessage2` ("DOWNLOADING STATIC DATA").
2. `comiss 0.5, [login+0x894]; jae return` — minimum dwell: if less than 0.5s
   has elapsed, return and keep waiting (constant at `0x1427ce048 = 0.5`).
3. `cmp byte [login+0x899], 0; je 0x1406ec75c` — **the poll**: if the
   static-data ready boolean is still 0, branch to the timeout check.
4. If the boolean is set: a secondary global gate is checked
   (`0x1404e6650()` game-instance accessor, then `byte [inst+0x19d0]`), and on
   success it advances — sets `login+0x890 = 3`, subscribes the store-data
   delegate at `+0x2b0`, and jumps to the store-data load kicker `0x1420d6a70`.
5. The timeout/failure block at `0x1406ec75c`:
   `comiss 30.0, [login+0x894]; jae return` — if fewer than 30s have elapsed,
   just return and keep showing "DOWNLOADING STATIC DATA" (constant at
   `0x1427bc2d4 = 30.0`). Once the timer exceeds 30s with the boolean still 0,
   it falls through to the failure path: sets `LoginMessage11`
   ("EVE: VALKYRIE - WARZONE LOGIN FAILED") / the generic terminal failure,
   writes `login+0x890 = 9`, and broadcasts a series of cleanup delegates
   (`login+0x8d0..+0x8f8` via `0x140571100`). State 9 is the terminal
   failed state; this is the observed "A NETWORK ERROR HAS OCCURRED" + DELETE.

(The dedicated `LoginMessage_StaticDataDownloadFailed` text is emitted by the
delegate's own failure overload at `0x1406e579a` when the completion is
broadcast with `success=0`; the *timeout* path instead emits the
`LoginMessage11` generic-failure text. Both routes converge on state 9.)

## 4. Why it stalls (ties to the known wall)

The static-data manifest IS fetched and parsed — the manifest-processing
routine `0x14209b550` runs and resolves files. But the subsystem's
"load-complete" multicast at `subsystem(0x143ab9858)+0x270` is never broadcast
to the subscribed delegate `0x1406e5780` (the resource's listener slot at
`resource+0x20` is NULL — see `staticdata-completion-wall`). Consequently:

- `0x1406e5780` never runs, so `login+0x899` is never set to 1.
- State 2 polls `login+0x899` every tick, sees 0, and waits.
- After 30s (`login+0x894 > 30.0`) the timeout branch fires and the login
  goes to state 9 / network-error. This is exactly the ~30s `heartbeat_seconds`
  window observed live.

The state machine is doing exactly what it should; the missing event is the
static-data completion BROADCAST, not anything in the login flow itself.

## 5. Concrete levers to advance past static data

In priority order, any ONE of these makes state 2 advance to state 3:

1. **Make the static-data resource fire its completion notify** (root-cause
   fix). The completion at `0x14209b550` must reach the broadcast of
   `subsystem(0x143ab9858)+0x270`, which invokes the subscribed delegate
   `0x1406e5780(login, success=1)` and sets `login+0x899=1`. This requires the
   resource's listener slot (`resource+0x20`) to be non-NULL — i.e. the
   subsystem must hold the subscription it expects. Investigate why the
   resource is created/resolved without its listener wired (manifest "complete"
   transition on the resource object), since the login-side subscription at
   `+0x270` IS present (installed by `0x1406ec060`). This is the clean fix and
   the one most likely to be a *server-shaped* manifest/response difference
   (the resource decides it is already satisfied from cache and skips the
   "complete" edge that would do the notify).

2. **Directly set `login+0x899 = 1`** (client-side poke / patch) at any time
   within the 30s window. The very next tick, state 2 will take its advance
   branch (provided the secondary `inst+0x19d0` gate is also non-zero) and move
   to DOWNLOADING STORE DATA. This is the minimal one-byte lever to prove the
   downstream flow and unblock store-data.

3. **Invoke the completion delegate directly**: call `0x1406e5780(login, 1)`.
   Equivalent effect to (2) but exercises the real success path; useful to
   confirm there is no other side effect required before state 3.

### What field must flip
`login+0x899` (one byte). It is the single static-data "ready" signal the login
tick polls. It is set ONLY by `0x1406e5780` with `success != 0`, which is
broadcast ONLY through the static-data subsystem's `+0x270` completion
multicast. Everything upstream (fetch, parse at `0x14209b550`, cache resolve)
already succeeds; the missing link is the broadcast → delegate → byte write.

## Appendix — key VAs

- Tick/dispatch driver: `0x1406e9200`; jump table base `0x1406e9344`.
- Message setter: `0x1406e7ed0(login, FText)`; writes UI at `login+0x880`.
- Step handlers: state1 `0x1406ec060`, state2 `0x1406ec6a0`,
  state3 `0x1406ec830`, state8/DONE `0x1406ec270`, headset `0x1406ec110`.
- Completion delegates: privileges `0x1406df640` (→`+0x898`),
  static-data `0x1406e5780` (success→`+0x899`, failure→`StaticDataDownloadFailed`/state9),
  store-data `0x1406e5850` (success→`+0x89a`, failure→`StoreDataDownloadFailed`/state9).
- Static-data subsystem (global): `0x143ab9858`; accessor `0x1420d6cf0`.
  Static-data completion multicast: `subsystem+0x270`; store-data: `subsystem+0x2b0`.
- Delegate-bind helper: `0x1419a9080` (TBaseDelegate vtable `0x1428435e0`).
- Load kickers: static-data `0x1420d6930` (→ `0x14209cb20`/`0x14209b280`),
  store-data `0x1420d6a70`.
- Manifest/completion processing: `0x14209b550` (listener slot `resource+0x20`).
- State fields on `login`: enum `+0x890`, timer `+0x894`, ready bools
  `+0x898`/`+0x899`/`+0x89a`, UI object `+0x880`, subsystem ptr `+0x710`.
- Timer constants: min dwell `0x1427ce048 = 0.5`; static-data timeout
  `0x1427bc2d4 = 30.0`; a longer `0x1427faab0 = 90.0` used elsewhere.
- FText key string VAs: `LoginMessage_Privileges 0x1429a0b28`,
  `LoginMessage2 0x1429a0b98`, `LoginMessageDownloadStoreData 0x14299a8b8`,
  `LoginMessage_StaticDataDownloadFailed 0x14299f640`,
  `LoginMessage_GenericTimeout 0x1429a0528`.
