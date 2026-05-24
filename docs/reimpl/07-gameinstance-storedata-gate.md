---
doc: reimpl-gameinstance-storedata-gate
title: The GameInstance+0x19d0 "Store Subsystem Ready" Gate
summary: Clean-room trace of the secondary login gate that blocks the transition out of "DOWNLOADING STATIC DATA" (state 2) into "DOWNLOADING STORE DATA" (state 3). The static-data step handler, once its own completion boolean is set, additionally requires a byte at GameInstance+0x19d0 to be non-zero before advancing; otherwise it dwells 30s and fails. That byte is zero-initialized in the GameInstance constructor and is set to 1 by exactly one writer, a delegate callback bound on the store/catalog data subsystem that the GameInstance keeps at +0x18c0. The delegate runs only after that subsystem has been created and wired, which itself only happens once a per-frame update routine observes the GameInstance is in the right session/online state. The actionable consequence: +0x19d0 is the client's internal "the store/catalog subsystem exists and produced its first update" signal, gated upstream on the online/session state machine reaching the point where the store subsystem is instantiated. Records every VA in the chain.
keywords: [gameinstance, storedata, login, gate, delegate, store-subsystem, catalog, 0x19d0, 0x18c0, multicast, state-machine, online-subsystem]
status: living
updated: 2026-05-24
evidence: [E4]
---

# The GameInstance+0x19d0 "Store Subsystem Ready" Gate

All addresses are virtual addresses in the shipped client (image base
`0x140000000`). This is our own prose description of observed control flow; no
copyrighted bytes are reproduced.

## 0. Context — where this gate sits

The login state machine (object `login`, ticked by `0x1406e9200`; state enum at
`login+0x890`) reaches state 2, "DOWNLOADING STATIC DATA", handled by
`0x1406ec6a0`. That handler waits for its own per-step completion boolean
(`login+0x899`, set by the static-data-complete delegate) and a minimum dwell.
Once both hold it does NOT advance directly; it performs a **secondary gate**:

- It calls the GameInstance accessor `0x1404e6650` (returns the GameInstance in
  `rax`).
- It reads the byte at `GameInstance+0x19d0` (the read instruction is at
  `0x1406ec6fb`).
- If that byte is zero it keeps waiting; the 30s dwell timer then trips the
  login-failed path (state 9). If it is non-zero it sets `login+0x890 = 3`
  ("DOWNLOADING STORE DATA").

So `GameInstance+0x19d0` is a precondition to ENTER the store-data step. The
question this document answers is: what sets it, and under what condition.

## 1. The GameInstance accessor and the global it reads — `0x1404e6650`

`0x1404e6650` is a thin accessor. It loads the global pointer at
**`0x1438568b8`**, calls a lazy get/initializer (`0x1404e17d0`) on it, then
returns the pointer read back from `0x1438568b8`. That global holds the single
process GameInstance (a `VkGameInstance`, UE 4.14.3). Every reference to
`GameInstance+0xNNN` below is an offset into the object stored at `0x1438568b8`.

## 2. Writers of GameInstance+0x19d0 — there are only two, and only one sets it

A byte-pattern scan of `.text` for the displacement `0x000019d0` used as a
ModRM disp32 found these encodings touching `+0x19d0`:

| VA            | instruction (paraphrased)        | meaning            |
|---------------|----------------------------------|--------------------|
| `0x1404d9ab3` | `mov byte [obj+0x19d0], bpl` (bpl=0) | constructor clears it to 0 |
| `0x1404ee426` | `mov byte [this+0x19d0], 1`       | the only real setter |
| `0x1406ec6fb` | reads `[GameInstance+0x19d0]`     | the login gate (read) |

### 2a. The constructor write — `0x1404d9ab3`

`0x1404d9ab3` lives inside the GameInstance/online-data subobject constructor
that begins around `0x1404d9935`. That constructor initializes a large block of
fields (it embeds the region literals "eu-west-1", "us-east-1", and a
`_Safe_Empty_String_` sentinel — i.e. an AWS-region/online configuration
object) and, among the rest, zero-initializes `+0x19d0`, sets the adjacent
`+0x19d4 = 1`, etc. So the field's default value after construction is **0**.
This confirms the gate is "closed" until something explicitly opens it.

### 2b. The only setter — `0x1404ee426`, inside the delegate `0x1404ee230`

The lone instruction that stores 1 into `+0x19d0` is `0x1404ee426`, inside a
function whose prologue is at **`0x1404ee230`**. In this function `this` (`rdi`)
is the GameInstance. Key facts about it:

- Its first action is to read the subobject pointer at `GameInstance+0x18c0`
  and **return early if that pointer is null** (the branch at `0x1404ee248`
  jumps straight to the epilogue, skipping the write). So the write happens iff
  `GameInstance+0x18c0 != 0`.
- When the subobject is present, the body iterates a small array held by that
  subobject (a count at `subobj+0x60`, a buffer at `subobj+0x58`), compares an
  embedded build/version literal ("15.01.20"), copies/stores a current value
  into `GameInstance+0x628`/`+0x620`, flips some global UI booleans, and then —
  on every path that reaches the tail — executes `mov byte [this+0x19d0], 1`
  at `0x1404ee426`. The write is unconditional once the early null-check passes.
- The function is never reached by a direct `E8 call`. Its address is taken once,
  as a `lea` at `0x1404f2c18` (see section 3), where it is **bound as a delegate
  callback** on the `+0x18c0` subobject. In other words `0x1404ee230` is an
  event handler that the store/catalog subsystem invokes when it updates.

**Conclusion of step 2:** `+0x19d0` is set to 1 the first time the store/catalog
data subsystem (held at `GameInstance+0x18c0`) fires the update/ready delegate
that `0x1404ee230` is subscribed to. The semantic meaning is "the store/catalog
subsystem exists and has produced (at least) its first update".

## 3. How the +0x18c0 subobject and the setter delegate get wired — `0x1404f2b50`

The setter `0x1404ee230` only ever runs because of the wiring done in the
function at **`0x1404f2b50`**. That function takes the GameInstance as `this`
(`rbx`) and a new subobject pointer as `rdx`, and:

1. Stores the subobject into `GameInstance+0x18c0` (`0x1404f2b6e`), early-outs if
   it was already set to the same value.
2. Binds four delegates on the subobject. The relevant one for this document is
   the delegate slot at `subobject+0x720`, to which it binds the GameInstance
   callback **`0x1404ee230`** (the lea at `0x1404f2c18`, bound via
   `0x1425061b0`). The other slots (`+0x790`, `+0x7d0`, `+0x8c0`) bind sibling
   GameInstance callbacks `0x1404ee4d0`, `0x1404ef4d0`, `0x1404ee840`.
3. Immediately calls `0x14209cc40` — a lazy singleton getter for another
   store/catalog-related global subsystem (allocates at `0x143ab9358`). This is
   the same store/catalog loader the state-3 ("DOWNLOADING STORE DATA") handler
   relies on, which ties the `+0x18c0` subobject firmly to the store-data phase.

So `0x1404f2b50` is the moment the store/catalog subsystem is *attached* to the
GameInstance and the `+0x19d0` setter is *armed*.

## 4. What triggers the attach — the online/session update routine

`0x1404f2b50` has exactly two `E8` callers: `0x140364ce2` and `0x140477098`.
The traced one, `0x140364ce2`, sits inside a small helper at `0x140364ca0`
that:

- Is itself a bound delegate (its address is taken as a `lea` at `0x14036a9ef`).
- Runs only when an input boolean is true and an `edx` selector is zero, and
  only when a virtual call `[vtable+0x690]` on the calling subsystem returns
  true (an "is this state/session ready" predicate).
- Then: gets the store-subsystem registry singleton (`0x14209ca30`, global
  `0x143ab9360`), derives the concrete subobject from it (`0x1420967d0`, which
  indexes a slot and returns null when the slot index is the `-1` sentinel),
  fetches the GameInstance (`0x1404e6650`), and calls `0x1404f2b50` to attach
  the subobject and arm the delegate.

The delegate `0x140364ca0` is registered by the large per-frame update routine
at **`0x14036a670`** (registration block around `0x14036a95f`). That routine is
a session/online-state pump over a subsystem object (`r15`) and only reaches the
registration when:

- `r15+0x870 != 0` (a session/online sub-state is active), AND
- the global flag at `0x143851965` is set, AND
- the `[vtable+0x690]` "ready" predicate is true, AND
- the store-subsystem registry slot is still unset (`registry+0x10 == -1`, i.e.
  the subobject has not been created yet), AND
- the GameInstance pointer is non-null.

When all hold, it binds `0x140364ca0`; the next time that delegate fires, the
chain in section 3 runs, the subobject lands at `GameInstance+0x18c0`, the
setter delegate is armed, and the first store/catalog update then sets
`GameInstance+0x19d0 = 1`.

## 5. Semantic summary

`GameInstance+0x19d0` is the client's internal "store/catalog data subsystem is
present and has produced its first update" flag. It is:

- Cleared to 0 in the GameInstance/online-config constructor (`0x1404d9ab3`).
- Set to 1, exactly once, by the store-subsystem update delegate `0x1404ee230`
  (write at `0x1404ee426`), but only after that subsystem exists at
  `GameInstance+0x18c0`.
- The subsystem is attached and the delegate armed by `0x1404f2b50`, driven from
  the online/session update pump `0x14036a670` once the session reaches the
  state where the store/catalog subsystem is instantiated.

It is therefore NOT directly the completion of a single REST call. It is one step
**downstream** of the online/session state machine advancing far enough to spin
up the store/catalog subsystem. The static-data step blocks until that subsystem
comes alive and ticks once.

## 6. Implication for the emulator (server-side lever)

The static-data step cannot advance until the online/session subsystem decides
to instantiate the store/catalog subsystem, which is gated on the session being
in the post-login "ready" state (the `r15+0x870` sub-state and the
`[vtable+0x690]` predicate in `0x14036a670`). In practice that readiness is
reached when the earlier login REST exchanges (the account/pilot/clients/entry
flow) complete with shapes the client accepts, so that the online subsystem
transitions into the session-ready state and creates the store subsystem.

Concretely, the most promising single change is to make the REST response that
the online subsystem consumes to mark the session "ready" return a shape that
drives `r15+0x870` non-zero (i.e. fully satisfy the post-authentication
account/pilot/session-establish call rather than just the static-data fetch).
Because the `+0x18c0` subobject is also where the state-3 store/catalog loader
(`0x14209cc40`) operates, serving a non-empty, well-formed store/catalog payload
on that subsystem's first fetch is what makes the update delegate fire naturally
and set `+0x19d0`. The actionable next probe is to confirm live which REST call
flips `r15+0x870` (the online-session sub-state) and whether the store subsystem
issues its own catalog request once attached.

## Online/session ready sub-state (+0x870)

This section traces the upstream gate from section 4 — the `r15+0x870`
sub-state, the co-gating global, and the `[vtable+0x690]` predicate — down to a
concrete semantic. All offsets below are into the **online/session subsystem
object** (the pump's `r15`), a distinct object from the GameInstance.

### A. The pump's `r15` object and the four co-gates (`0x14036a670`)

The pump receives its object in `rcx`/`r15` from a per-frame tick. Its only two
`E8` callers are `0x14032a4c7` and `0x1407ec9f7`; the traced one is inside a
tick body that, just before the call, touches the same object's `+0x220`
(an int state == 1), `+0x4b0` (a sub-pointer), `+0xbff`, `+0xcfc`. That same
object is constructed at `0x140359060` (it embeds the literals `/Script/VkGame`,
`Normal`, `Colour`; its vtable pointer is `0x14283da60`, stored at
`0x140359050`). So `r15` is a UObject-derived online/session subsystem owned
elsewhere, not a plain GameInstance member.

The pump reaches the store-attach registration (binding `0x140364ca0` at the
`lea` `0x14036a9ef`) only when ALL of:

1. `byte [r15+0x870] != 0` — checked three times (`0x14036a812`, `0x14036a856`,
   `0x14036a942`). This is the session "ready" sub-state.
2. `byte [0x143851965] != 0` — checked at `0x14036a95f`.
3. virtual `[vtable+0x690]` returns true — called at `0x14036a9a9`.
4. the store-registry slot is still the `-1` sentinel — `cmp [reg+0x10], -1`
   at `0x14036a9d4` (registry from `0x14209ca30`).
5. GameInstance non-null (`0x1404e6650` at `0x14036a9de`).

### B. `+0x870` is a byte sub-state, zero-init, set by exactly one routine

`+0x870` on this object is a single byte (read with `cmp byte`/`grp1 imm8`,
written byte-wide). It is zero-initialized in the constructor
(`0x1403591d2`, `mov byte [rsi+0x870], bpl` with bpl=0, in the same constructor
that zeroes `+0x830`/`+0x834`/`+0x8c8`).

The one routine that sets it to 1 is **`0x1402f0d00`** (write at `0x1402f0d59`,
`mov byte [rbx+0x870], 1`). Its logic:

- Early-out unless `byte [this+0x858] != 0` (`0x1402f0d06`).
- Early-out if `byte [this+0x870] != 0` already (`0x1402f0d12`) — i.e. fire once.
- Otherwise it resolves a delegate/callback object (`+0xa08`, falling back to
  `+0xa00`), reads a payload pointer (`+0x878`), invokes a virtual
  `[vtable+0x4f0]` passing the int at `+0x85c`, clears `+0x868`, then sets
  `+0x870 = 1`.

So **`+0x870` becomes ready as a pure consequence of `+0x858` being set.**
`+0x858` is the actual arming flag; `+0x870` is a derived "I have fired the
ready notification" latch.

`0x1402f0d00` has one caller, `0x1402e4f60` (a session method that calls it at
its prologue then continues into other per-tick work over `+0x978`/`+0x980`),
whose only caller is `0x14080b446` — a per-frame tick of the session object
(`r14`; touches `+0x1a8` state, `+0x220`, `+0x9d8`, `+0x9f0`). It calls
`0x1402e4f60` each frame whenever `+0x9d8 != 0`. Net: every tick the client
checks "is `+0x858` set and `+0x870` not yet latched?"; the first tick after
`+0x858` goes non-zero flips `+0x870`, which (with the other co-gates) lets the
pump attach the store subsystem.

### C. What `+0x858` is, and how it gets set

`+0x858` is also a single byte on this object, zero-init in the constructor
(`0x1402e27c3`/`0x140359090`). It reads as a boolean in several places:
`0x1402ec196` (a per-frame routine that, when `+0x858` is set, walks an actor
list via `+0x128` and runs `0x1402e89a0` to compute something) and the setter
guard `0x1402f0d07`. Semantically it is the "this session/online object is now
live/established" flag — the per-frame session work and the ready-notification
both gate on it.

Crucially, there is **no plain C++ store of a constant into `+0x858`** anywhere
in `.text` except the constructors (which clear it). The only standalone byte
writer is a UE reflected-property setter thunk at `0x1403aeb70`
(`mov byte [rdx+0x858], r8b; ret`) — one of a table of generated
`UPROPERTY` bool setters (siblings at `+0x7cc`, `+0x82c`, `+0x92d`). This means
`+0x858` is a **reflected/notified boolean**: it is flipped through the UE
reflection/delegate machinery (a property write or a bound multicast), driven by
the OnlineSubsystem login/session-state callback — not by a hardcoded handler of
one specific REST body. In other words, `+0x858` tracks the OnlineSubsystem's
own "logged in / session valid" event, which the OSS raises after the login
handshake completes, not after any single `/staticdata`-style fetch.

### D. The co-gates are launch-config, not server-driven

- Global `byte [0x143851965]` is **not** set by any login response. It is a
  startup command-line/config flag. The function at `0x140393440` parses a set
  of launch switches (calling parser `0x1409d6630` for strings `dev`,
  `soaktest`, `aisoaktest`, …) and at `0x14039345f` writes
  `byte [0x143851965]` from the result of the switch whose name string is at
  `0x14284f600` = UTF-16 `"vr"`. So `0x143851965` is the **VR-mode flag**: the
  store-attach path co-requires the client to be running in VR (`-vr`/HMD
  present). Adjacent bytes `0x143851962`/`0x143851963` are the `dev`/`soaktest`
  flags from the same parser.
- The predicate `[vtable+0x690]` is `0x1403646a0`: it returns true iff
  `qword [r15+0x500] != 0` (a sub-handler pointer). `+0x500` is populated when
  the session object's handler/child object is created during online init; it is
  a client-internal lifecycle pointer, not a response field.

### E. Server-observable trigger — conclusion

The lever that flips `+0x870` (and thus opens the store-attach in the pump) is
**`+0x858`, the OnlineSubsystem "session established / logged-in" event**, which
the client raises through its reflection/delegate path once the OSS login
handshake completes — i.e. once the early auth/session REST exchange resolves
into a valid logged-in session, NOT when `/staticdata` returns. Concretely, the
REST steps that drive the OSS to "logged in" are the front of the flow:
`POST /oauth/token` → `POST /auth` → `POST /clients` (which must return an
accepted client/session) → the account/pilot calls, culminating in
`POST /sessionrequests` establishing the session object. `+0x858` is the
client-side reflection of that session being accepted; the static-data step then
finds `+0x870` already latched (or about to latch on the next tick) and
advances.

This means the wall is **not** a missing field in the `/staticdata` response.
It is that the OnlineSubsystem never reaches its "logged-in/session-valid" state
(so `+0x858` is never set), because one of the front-of-flow calls
(`/clients` accept, `/sessionrequests`, or the heartbeat `PUT /clients` that
keeps the session valid) is not returning the shape that makes the OSS mark the
session established. Two co-gates must additionally hold for the store to
attach: the client must be in **VR mode** (`-vr`, the `0x143851965` flag) and the
session handler at `+0x500` must exist.

### F. Concrete MVP-server change to try

1. Ensure `POST /clients` returns an accepted/registered client object (with the
   session/client id the client expects) and that the heartbeat
   `PUT /clients/{id}` keeps returning success — a rejected or empty `/clients`
   leaves the OSS un-established so `+0x858` never flips.
2. Make `POST /sessionrequests` return a fully-formed session-established
   response (a granted session with id/token), since this is the call that
   completes the OSS login on this object. This is the single most likely
   `+0x858` trigger.
3. Keep serving the rest of the front flow (`/oauth/token`, `/auth`,
   `/pilots/1`, `/accounts/`) with the shapes already accepted, so the OSS
   proceeds to the session-establish step at all.

(The store/catalog payload at `/stores/7/offers/` matters only AFTER attach, for
the section-2 delegate to flip `+0x19d0`; it does not gate `+0x858`.)

### G. Single best live probe to confirm

Read `byte [r15+0x858]` (the session object) at runtime across the REST flow:
breakpoint or poll on the setter `0x1402f0d00` (entry) and log whether
`[rbx+0x858]` is non-zero. The first REST response after which `+0x858` becomes
non-zero is the precise trigger. Practically: set a one-shot hardware/exec
breakpoint at `0x1402f0d59` (the `+0x870 = 1` store) and capture the call stack +
the most recent completed REST request — that stack frame's originating online
callback names the exact endpoint/event. Equivalently, watch `+0x858` flip while
diffing against the sequence of served responses; expect it to coincide with the
`/sessionrequests` (or `/clients`) completion, NOT `/staticdata`. Also confirm
the client is launched with `-vr` (or an HMD active) so the `0x143851965` gate
is satisfied — otherwise the store will never attach even with `+0x870` set.

## OSS logged-in trigger (+0x858) and store-loader preconditions

This section deepens sections A–G with fresh disassembly of (1) the exact write
mechanism of `OSS+0x858`, (2) the tick/latch gating, and (3) the real store
loader `0x14209cce0`. All VAs are in the shipped client (image base
`0x140000000`); this is our own prose, no copyrighted bytes reproduced.

### H. `OSS+0x858` is one byte of an `{bool, int}` login-status pair, written only via reflection

The OSS object (constructor `0x140359060`, vtable `0x14283da60`, embeds
`/Script/VkGame`) lays its login-status fields out as a small struct:

- The constructor zero-initializes them with an 8-byte store
  `mov qword [rsi+0x858], 0` at `0x140359090` (covering the byte `+0x858` and
  the int `+0x85c` together), followed by `+0x860` and `+0x868` (also via
  `0x1402e27c3`/`0x1402e27d1` in the sibling constructor path). So `+0x858`
  (bool) and `+0x85c` (int) are adjacent fields of one status struct — a
  `{bLoggedIn:bool, LocalUserNum/Status:int}` shape, the classic UE OnlineSubsystem
  Identity login-state pair.
- The latch `0x1402f0d00` reads BOTH: it early-outs unless `byte [this+0x858]!=0`
  (`0x1402f0d06`), and when it fires it reads `dword [this+0x85c]` (`0x1402f0d42`)
  and passes it as the argument to the virtual `[callbackobj+0x4f0]`
  (`0x1402f0d48`) — i.e. it forwards the int (the local-user/status code) into a
  delegate broadcast. This is the OSS "login complete -> notify" hop.
- A `.text`-wide scan for the displacement `0x858` (and `0x85c`) confirms that on
  the OSS object the ONLY writers are the constructors (which clear the pair) and
  the generated UPROPERTY bool-setter thunk `0x1403aeb70`
  (`mov byte [rdx+0x858], r8b; ret`). Every other `+0x858` access in `.text`
  belongs to a different UObject class that happens to reuse offset 0x858
  (e.g. a CDO default-property block at `0x1403a26e6` that bulk-sets bools incl.
  `+0x858=1` on a settings object; a destructor at `0x1402c4ef1` that treats
  `+0x858` as a sub-object pointer and frees it). None of those touch the OSS
  vtable-`0x14283da60` object — they are noise from offset aliasing.
- The thunk `0x1403aeb70` is never reached by `E8`/`lea` in `.text`; its address
  appears exactly once as a data pointer in `.rdata` at `0x14281c060` (a
  generated native-function/property pointer table). It is therefore invoked
  purely through UE reflection: a `UProperty`/`UFunction` write or a bound
  multicast delegate flips `+0x858`. There is no hand-written
  `mov [oss+0x858],1`. **Conclusion: `+0x858` is the OnlineSubsystem Identity
  "logged-in" boolean, raised through the reflection/delegate path when the OSS
  login handshake completes — not by any hardcoded handler keyed to a single
  REST body.**

### I. The tick is NOT conditionally gated — the latch is self-gating on +0x858

Disassembly of the OSS tick `0x1402e4f60` shows it calls the latch
`0x1402f0d00` **unconditionally at its prologue** (`0x1402e4f77`), every time the
tick runs, before doing its other per-frame work (`0x1402e65d0`, an array walk
over `+0x978`/`+0x980`, etc.). The tick's own caller `0x14080b446` runs it each
frame whenever `+0x9d8 != 0`. So the reason the latch "is never called" in our
run is NOT that the tick withholds the call — the call happens every frame; it is
that the latch immediately early-returns because `byte [this+0x858]==0`
(`0x1402f0d06 -> 0x1402f0d60`). The latch is purely self-gated on `+0x858`. Once
`+0x858` becomes non-zero, the very next tick latches `+0x870=1` (`0x1402f0d59`),
broadcasts the login-complete delegate, and the store-attach pump (`0x14036a670`,
section A) can proceed. **There is no additional state machine to satisfy here:
flipping `+0x858` is necessary and (with the VR co-gate) sufficient to open the
store-attach.**

### J. The real store loader `0x14209cce0` is a query-string builder, gated only by object existence

`0x14209cce0` has a single `E8` caller, `0x142092f81`, inside the store/session
"version request" builder (the function around `0x142092e80`). That builder:

- Assembles a request PATH from the wide literal `sessionrequests`
  (`0x143107ba8`, loaded at `0x142092ef5`/`0x142092f21`) into the request object
  at `[rsi+0x10..]`.
- Calls `0x14209cce0` (`0x142092f81`) to APPEND a query string to that path. The
  loader builds `?version=…&region=…&session_type=…` from wide literals
  `version` (`0x143106938`), `-REGION=` (`0x143106a18`), `region`
  (`0x143106aa8`/`0x143106b08`), and `session_type` (`0x143106b40`). The query is
  written back to `[rsi+0x40]`.
- Then sets up a completion handler at `[rsi+0xb0]` (delegate body `0x1420b1ef0`,
  bound via `0x142081120` at `0x142092faa`) and issues the request through the
  request object's own vtable (`call [rax+8]` at `0x142092fbc`).

The loader's only branching preconditions are region-source selectors, NOT login
gates:

- `cmp dword [this+0x98], 1; jg …` (`0x14209cda8`) and `cmp dword [this+0x98], 0;
  je …` (`0x14209ced1`): `[this+0x98]` selects WHERE the region string comes from
  — a `-REGION=` command-line override (read via `0x1409e5610` at `0x14209cdd3`)
  vs. a stored region at `[this+0x90]` vs. a default literal at `0x1427bbd50`
  (`0x14209cee3`). It does not gate whether the fetch happens.
- The session-type segment is appended from `[this+0xa0]` (`0x14209cf9e`).

So `0x14209cce0` has **no OSS-logged-in / bearer-token precondition of its own**.
It runs to completion as soon as its `this` (the store/session "version" request
object) exists. That object only exists once the store subsystem has been
attached to the GameInstance (section 3), which is downstream of `+0x870`, which
is downstream of `+0x858`. In other words the store fetch is gated transitively
by `+0x858`, not by any field the loader itself checks. The `Authorization`
bearer (the OAuth `access_token` parsed at `0x1420c0308` into the token global
`0x143ab9558`, and the `authenticated`/`authorization` request params assembled
at `0x1420b0293`/`0x142092xx`) is attached by the HTTP layer when the request is
actually sent — it is not a branch inside `0x14209cce0`.

### K. Server-observable trigger — refined conclusion

The single lever remains `OSS+0x858`. Because it is reflection-written and the
OSS object is the UE OnlineSubsystem identity object, `+0x858` flips when the OSS
"login complete" event resolves successfully. The REST surface that produces that
event is the front-of-flow auth/session exchange, NOT `/staticdata` and NOT the
later `/stores/...` catalog. The token plumbing we already serve
(`POST /oauth/token` -> `access_token` cached at `0x143ab9558`) is consumed by the
request builders as a bearer, but the OSS marks itself logged-in only after the
session-establish call the identity layer is waiting on resolves into a valid,
accepted session. On this code path the session-establish call is the
`sessionrequests` request that `0x142092e80`/`0x14209cce0` build (path literal
`sessionrequests`, `0x143107ba8`) — i.e. **`POST /sessionrequests` returning an
accepted/granted session is the most likely `+0x858` trigger**, with
`POST /clients` (accepted client) as the necessary precursor that lets the flow
reach the session-establish step at all. Two co-gates still hold independently of
the server (section D): the client must be in VR mode (`0x143851965`, the `-vr`
switch) and the session sub-handler at `+0x500` must exist.

### L. Concrete MVP-server change to make

1. Serve `POST /sessionrequests` (the literal path the store/session builder
   constructs, query `?version=&region=&session_type=`) with a fully-formed
   "session granted" JSON object (session id/token + the `authenticated`-style
   acceptance the response parser expects). This is the call that drives the OSS
   identity to logged-in and is the single highest-value change.
2. Ensure `POST /clients` returns an accepted client (with the id/Location the
   client expects) and that the heartbeat `PUT /clients/{id}` keeps succeeding —
   a rejected/empty `/clients` stops the flow before it reaches
   `/sessionrequests`, so `+0x858` never gets a chance to flip.
3. Keep `POST /oauth/token` returning a valid `access_token` (already cached at
   `0x143ab9558`) and keep `/auth`, `/pilots/1`, `/accounts/` returning the
   accepted shapes, so the identity layer proceeds to the session-establish step.
4. Launch the client in VR (`-vr`/HMD) so the `0x143851965` co-gate is satisfied;
   otherwise the store will never attach even after `+0x858`/`+0x870` are set.
5. Only AFTER attach does the store/catalog payload matter: serve a non-empty,
   well-formed catalog on the store subsystem's first fetch so the section-2
   delegate `0x1404ee230` fires and sets `GameInstance+0x19d0 = 1`.

### M. Residual uncertainty

- The exact UFunction/UProperty (the reflected name) that the thunk `0x1403aeb70`
  is bound to was not recovered from static init; the thunk is generic
  (writes any object's `+0x858`) and its naming lives in `Z_Construct`-style
  startup registration via FName tables, which this pass did not unwind. The
  behavioral identification (OSS Identity "logged-in" bool) is solid from the
  latch's use of the `{+0x858,+0x85c}` pair and the `/Script/VkGame` OSS class,
  but the precise login-complete delegate handler that does the reflected write
  is inferred, not disassembled end-to-end.
- Whether `+0x858` is set by the `/sessionrequests` completion specifically vs.
  an earlier `/clients`/`/auth` step is inferred from the path literal the same
  module builds and from section E; it should be confirmed live with the
  one-shot breakpoint at `0x1402f0d59` (section G) correlated to the last served
  REST response. The disassembly proves the *mechanism* and *preconditions*
  precisely; the *exact endpoint* is the one item best nailed by the live probe.

## Store-attach -> catalog-fetch precondition (decisive)

This section answers THE ONE QUESTION with fresh disassembly that follows the
*actual* control flow from the store-attach point to the store-catalog HTTP
fetch. It REFINES (and in one place corrects) the model in sections A–M: the
`/stores/.../offers` GET is NOT issued autonomously by the store subsystem when
it is attached; it is issued by the **login state machine itself**, and only
after the static-data step has completed. All VAs are in the shipped client
(image base `0x140000000`); own prose, no copyrighted bytes reproduced.

### N. The actual store-catalog HTTP request issuer — `0x14209f650`

The real GET for the store catalog is built by `0x14209f650`. It:

- Allocates a 0x130-byte HTTP request object (`0x1417c0d00`), vtable
  `0x143111f10`.
- Writes the method literal `GET` (wide, `0x14310f9b8`) into the request's
  method string at `+0x20` (`0x14209f77e`/`0x14209f788`).
- Copies the caller-supplied URL path (in `rdx`/`rbp`) into the request's URL
  string at `+0x30` (`0x14209f7b5`).
- Binds the response handler `0x14209ed00` into the request's completion holder
  at `+0xb0` (`lea r8,[0x14209ed00]` at `0x14209f7c4`, bound via `0x1420809a0`),
  sets request mode `+0xa8 = 3`, and **fires the request** through the request
  vtable `call [rax+8]` at `0x14209f816`.

The URL path itself is assembled by `0x14209eb60` from the wide template
`v2.0/valkyrie/stores/7/offers/` (`0x14310f658`; the literal embeds a fixed
store id `7`), then handed to `0x14209f650` (`call 0x14209f650` at `0x14209ecbf`).
`0x14209eb60` has NO `E8` callers — its address is taken once and it is reached
by a tail `jmp` (see O). The catalog response parser is `0x14209ed00` (it reads
the offers payload via the request object's response accessor `[vtable+0x50]`).

`0x14209f650`'s only other caller is `0x14209f4ff` (inside the response parser
`0x14209ed00` — i.e. follow-up/paged fetch), confirming `0x14209f650` is the
single catalog-GET issuer. It has **no OSS-logged-in / bearer-token branch of its
own**: it unconditionally allocates, sets GET + URL, and sends. The bearer is
attached later by the HTTP layer. So the catalog GET is gated entirely by *who
calls the kick*, not by a guard inside the issuer.

### O. WHO issues the catalog GET — the login state machine, not the subsystem

`0x14209eb60` (URL builder) is referenced once, from a thin thunk at
`0x1420d6a70`. That thunk: gets the store subsystem singleton (`0x14209cc40`),
registers a delegate `0x1420d73c0` at `singleton+0x80` (`0x142080d60`), gets the
singleton again, and tail-`jmp`s into `0x14209eb60`. So `0x1420d6a70` is the
"kick the store /offers fetch" entry.

`0x1420d6a70` is reached by a tail `jmp` from exactly one place:
**`0x1406ec757`, inside the login state-machine handler `0x1406ec6a0`** — the
"DOWNLOADING STATIC DATA" / state-3 handler. (There is one apparent second
reference at `0x14167e659`; disassembly shows it is a `je` branch target, a
scanner false positive, not a code reference to `0x1420d6a70`.)

Adjacent to it, `0x1406ec101` (inside the state-2 handler `0x1406ec060`,
"CHECKING ACCESS") tail-`jmp`s `0x1420d6930` — the **GetFileList / static-data**
trigger (doc 05). So the two login states drive two different fetches:

| Login state | Handler | Entry gate | Tail-kicks |
|-------------|---------|-----------|------------|
| 2 "CHECKING ACCESS" | `0x1406ec060` | `[login+0x898] != 0` | `0x1420d6930` GetFileList (static data) |
| 3 "DOWNLOADING STATIC DATA" | `0x1406ec6a0` | `[login+0x899] != 0` AND `GameInstance[+0x19d0] != 0` | `0x1420d6a70` store `/stores/7/offers/` GET |

The login object is `login` (state enum `login+0x890`, ticked by `0x1406e9276`;
jump-table at `0x1406e928b`, bounds `<= 0xa`). The store /offers GET is therefore
the LAST of the two; it is structurally unreachable until the static-data step
both completes (`+0x899`) and the GameInstance store gate opens (`+0x19d0`).

### P. The two state gates and who sets them

- **`login+0x898`** (gates kicking GetFileList): set by the small completion
  callback `0x1406df640` (`mov byte [rcx+0x898],1` at `0x1406df646`) — the
  "CHECKING ACCESS / privileges" REST step's result delegate.
- **`login+0x899`** (gates kicking the store /offers GET): set by the
  static-data fetch result callback `0x1406e5780`, which is bound to the
  static-data manager at `mgr+0x270` when state 2 kicks GetFileList
  (`0x1406ec0db`/`0x1406ec0e8`). On success (`dl != 0`) it does
  `mov byte [login+0x899],1` (`0x1406e578d`); on failure it shows
  `LoginMessage_StaticDataDownloadFailed` / "A NETWORK ERROR HAS OCCURRED" and
  sets `login+0x890 = 9` (fail). **This is the live wall: the GetFileList
  completion never fires "success", so `+0x899` is never set.**
- The symmetric store /offers result callback is `0x1406e5850` (bound at
  `mgr+0x2b0` when state 3 kicks the GET): success sets `login+0x89a = 1` and
  forwards via `[handler+0x610]`; failure shows
  `LoginMessage_StoreDataDownloadFailed`. This confirms `/stores/7/offers/` is a
  bona fide post-static-data login step with its own success/fail latch.

### Q. The fetch-issuing function and its guards (answer a)

- Fetch issuer: **`0x14209f650`** (GET, URL `v2.0/valkyrie/stores/7/offers/`
  built by `0x14209eb60`, response parser `0x14209ed00`). It has **no internal
  precondition** — no OSS-login check, no token check, no region/version check.
- The real guard is at the **caller** (`0x1406ec6a0`, state 3): the GET is kicked
  iff `byte [login+0x899] != 0` (static-data success) AND
  `byte [GameInstance+0x19d0] != 0` (store subsystem produced its first update,
  per section 2). Both must hold; otherwise the state dwells and trips the
  30s login-failed path.

### R. The missing precondition in our run (answer b)

`byte [login+0x899]` is never set, because the static-data GetFileList completion
(`0x1406e5780`) never runs with success. Equivalently: the **static-data
download never reports "complete"** — the exact wall recorded in memory
(`staticdata-completion-wall`). The `/stores/7/offers/` GET is one step DOWNSTREAM
of that and is consequently never issued — which precisely matches the live fact
"no `/stores/...` HTTP fetch ever happens." Note the catalog GET does NOT depend
on `sessionrequests`: the `sessionrequests` builder (`0x142092d00`/`0x142092e80`,
sections J/K) is a separate matchmaking/session request issued elsewhere
(`0x142096a50`), not the store-catalog GET.

`GameInstance+0x19d0` is the secondary gate (sections 2–4): set only by
`0x1404ee230` when the store subobject at `GameInstance+0x18c0` fires its update
delegate. In the current run we cannot even observe whether `+0x19d0` would set,
because state 3 is never entered (it requires `+0x899` first). So the *binding*
missing precondition is `+0x899` (static-data completion); `+0x19d0` is a
follow-on gate that only becomes relevant once static data completes.

### S. Classification (answer c): SERVER-OBSERVABLE (A), with one platform co-gate

The store-catalog fetch precondition is **(A) SERVER-OBSERVABLE in its binding
link**: the gate that is actually blocking is `login+0x899` = "GetFileList /
static-data download completed successfully", which is driven entirely by the
client's static-data HTTP exchange and its completion delegate. Per doc 05, that
completion's "ready" notify is wired from a *bound* response delegate the login
flow installs; making the immediately-preceding REST steps return shapes that let
the login flow enter the static-data state with its delegate bound, and serving a
well-formed GetFileList manifest that the parser accepts to completion, causes
`0x1406e5780` to run with success and set `+0x899`. No client/VR identity is
required to set `+0x899`.

The precise server change to unblock the catalog fetch:

1. Drive the login flow through the privileges/access step so `+0x898` is set
   (its completion `0x1406df640` runs), letting state 2 kick GetFileList.
2. Serve the static-data manifest (`GetFileList`, the `vkpilot/staticdata...`
   request from doc 05) so its completion (`0x14209b550`) runs to the notify and
   the bound delegate `0x1406e5780` fires success -> `+0x899 = 1`. This is the
   single highest-value change.
3. Then serve `GET v2.0/valkyrie/stores/7/offers/` (note: fixed path with store
   id `7`, method GET, not the `sessionrequests` POST) with a non-empty,
   well-formed offers payload, so the catalog GET's response parser
   (`0x14209ed00`) succeeds, `0x1406e5850` sets `+0x89a`, and the flow leaves
   state 3.

The ONE genuinely **client/platform-bound co-gate (B)** is the secondary
`GameInstance+0x19d0` gate that also fences state 3: per sections 2–4 and D, the
store subobject only attaches (so the `+0x19d0` setter is armed) when the
online/session pump `0x14036a670` sees its co-gates, one of which is the global
VR-mode flag `0x143851965` (the `-vr`/HMD switch, set by the launch-arg parser
`0x140393440`). No server response can satisfy that flag — the client must run in
VR mode (or be patched). So the full answer is: the *binding* missing
precondition is server-observable (static-data completion -> `+0x899`), but the
follow-on `+0x19d0` gate additionally requires the platform/VR co-gate to have
attached the store subsystem.

### T. Confidence and residual uncertainty (answer d)

- High confidence (direct disassembly): the catalog GET issuer (`0x14209f650`),
  the URL template (`v2.0/valkyrie/stores/7/offers/`), the kick path
  (`0x1420d6a70` <- tail-jmp from state-3 handler `0x1406ec6a0`), the two state
  gates (`+0x898`/`+0x899`), their setters (`0x1406df640`, `0x1406e5780`), and the
  fact the GET has no internal login/token guard. The state-2/state-3 mapping to
  GetFileList vs. `/stores/.../offers` is established from the tail-jmp targets and
  the on-screen login message literals ("DOWNLOADING STATIC DATA",
  "...StaticDataDownloadFailed", "...StoreDataDownloadFailed").
- The binding wall = `+0x899` not set (static-data never completes) is consistent
  with the live observation and with doc 05's analysis of why the GetFileList
  completion's notify is skipped.
- Residual uncertainty: exactly which prior REST step must succeed for the login
  flow to enter state 2 with a *bound* static-data delegate is the same open item
  doc 05 flags (item: confirm the install branch of `0x140b0ac10` is taken live).
  That is the one remaining live probe; the static-binary control flow from
  static-data completion to the catalog GET is now fully resolved.
