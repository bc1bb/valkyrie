---
doc: reimpl-staticdata-lifecycle
title: Static-Data Resource & Manager Lifecycle — Who Sets the "Ready" Listener
summary: Clean-room trace of the GetFileList (static-data manifest) request/response lifecycle in the shipped client. Identifies the GetFileList request builder, the FVKStaticDataResource constructor, the static-data singleton manager, and the generic "+0x20/+0x30" delegate-container idiom the completion handler uses to notify "static data ready". Corrects the earlier assumption that the completion's `this` is the resource: it is in fact the singleton MANAGER. Establishes that the manager's listener slot IS installed inside the request builder (by a delegate-assign helper) from a delegate the caller passes, IF that source delegate is bound. Explains why the notify is skipped and what to change.
keywords: [staticdata, getfilelist, resource, manager, singleton, listener, delegate, completion, notify, lifecycle, constructor, builder, ready, wall, e4]
status: draft
updated: 2026-05-24
evidence: [E4]
---

# Static-Data Resource & Manager Lifecycle

All offsets are runtime virtual addresses; image base 0x140000000. This documents
observed control flow in the local binary in prose; no copyrighted bytes are
reproduced. It supersedes one assumption from earlier notes (see "Correction").

## Cast of objects

Three distinct heap objects are involved in the static-data manifest fetch. Earlier
notes conflated the first two.

1. **Static-data singleton manager** — produced by the lazy accessor at
   `0x14209cb20` (allocates 0xe0 bytes, caches the pointer in a global). Its
   constructor zero-initializes a generic delegate-container at offsets **+0x20
   (delegate pointer)** and **+0x30 (bound flag / count)**, both start NULL/0. This
   is the object whose `+0x20`/`+0x30` decide whether "static data ready" is
   announced. There are only two callers of the accessor: the GetFileList trigger
   (`0x1420d69c5`) and the per-file download loop (`0x1420d7a69`).

2. **FVKStaticDataResource** (the HTTP request object) — a 0x130-byte object
   allocated and constructed *inside the request builder* (`new` at
   `0x14209b2a8`, ctor `0x142084880`, base ctor `0x142084ec0`, vtable
   `0x143111db0`). In THIS object, `+0x20` and `+0x30` are **string buffers**, not
   a listener: the builder writes the HTTP method ("GET") into a string at
   `[resource+0x20]` (`0x14209b3b3`) and the URL path ("vkpilot/staticdata...")
   into a string at `[resource+0x30]` (`0x14209b49b`). The ctor argument `1` is
   stored at `+0x128`, not at `+0x20/+0x30`.

3. **The caller's response delegate** — a small functor the GetFileList trigger
   builds on its stack, capturing the login-flow step object and the manifest
   handler callback `0x1420d7470`. This is the thing that ultimately must end up in
   the manager's listener slot.

## The "+0x20 / +0x30" delegate-container idiom

This pair appears all over the static-data code as a uniform single-slot delegate
holder: `+0x20` = pointer to a bound functor object, `+0x30` = a non-zero "is
bound" flag. The notify pattern (read it at `0x14209bc6c` in the completion, and
identically at `0x14209a924` in the per-file dispatch) is always:

- `if (holder+0x30 == 0) skip;`
- else fetch `holder+0x20`, call functor vtable **+0x38** (a "should I fire?"
  predicate), then functor vtable **+0x68** (the actual notification), and on
  teardown release via **+0x48** and clear `+0x20`/`+0x30`.

So a NULL `+0x20` / zero `+0x30` simply means *no delegate is bound to that slot*,
and every notify against it is silently skipped.

## The request builder (`0x14209b280`, returns at `0x14209b54a`)

Entry: `rcx` = the login-flow static-data step's `this` … but the caller actually
passes `rcx` = the **manager** and `rdx` = the **caller's response delegate**
(see "Trigger" below). Prologue at `0x14209b280`; `mov r12, rcx` at `0x14209b2a0`
captures the manager as the bind target.

The builder's first action is the listener install:

- `call 0x140b0ac10` at `0x14209b2a3`, with `rcx` still = manager and `rdx` still =
  the caller's delegate (neither is reloaded before the call). `0x140b0ac10` is a
  **delegate move/assign**: dest=`rcx`, src=`rdx`. If `src+0x30 != 0` (the source
  delegate is bound) it invokes `src.vtable[0x50]` with `rdx`=dest, which installs
  the functor into the destination's `+0x20` and sets dest `+0x30`. If the source
  is *not* bound (`src+0x30 == 0`) it instead *clears* the destination (releases
  `dest+0x20`, sets `dest+0x30 = 0`). **This is what wires the manager's "ready"
  listener — conditional on the caller's delegate being bound.**

Then the builder: allocates and constructs the FVKStaticDataResource (`0x142084880`),
wraps it in an 0x18-byte refcounted holder (vtable `0x142b51980`), fills the HTTP
method/URL strings (resource `+0x20`/`+0x30`), and finally:

- `lea rcx,[resource+0xb0]; mov rdx,r12; lea r8,[rip+0x58] (=0x14209b550); call 0x1420809a0`
  (`0x14209b4e7`) — binds the completion `0x14209b550` to **target `r12` = the
  manager** via the resource's request-delegate holder at `+0xb0`.
- `mov rax,[resource]; mov rcx,resource; call [rax+8]` (`0x14209b4fd`) — fires the
  request through the resource vtable+8.

The delegate-bind helper `0x1420809a0` (dest holder=`rcx`, captured `this`=`rdx`,
fn=`r8`) builds a functor (vtable `0x143112300`) capturing `this=r12`(manager) and
`fn=0x14209b550`. So when the HTTP response arrives, the completion runs with
`rcx = the manager`.

## The completion handler (`0x14209b550`)

`mov r15, rcx` at `0x14209b58a`: **`r15` = the completion's `this` = the manager**
(the bind target r12), *not* the FVKStaticDataResource. It parses the manifest and
registers files, then reaches the notify block at `0x14209bc6c`, which runs the
+0x20/+0x30 idiom on `r15` (the manager). If `[manager+0x30]==0` the whole "static
data ready" announcement is skipped — and that is the observed wall.

## Correction to earlier notes

Earlier RE recorded that the completion's `this` is the FVKStaticDataResource and
that `res+0x20`/`res+0x30` are its listener. That is not what the code does:

- The completion's `this`/`r15` is the **singleton manager** (`0x14209cb20`
  output), whose `+0x20`/`+0x30` are the generic delegate holder.
- The **resource's** own `+0x20`/`+0x30` are HTTP request *strings* ("GET" and the
  URL), so reading those would (in a real request) be NON-null and unrelated to the
  notify decision.

A live probe that read "+0x20/+0x30" on the resource pointer would see strings; one
that read them on the manager would see the listener. The notify gate keys off the
manager.

## The GetFileList trigger (`0x1420d6930`)

This builds the caller's response delegate on its stack (`[rsp+0x40]`/`[rsp+0x20]`):
functor vtable `0x142f333c0`→`0x142f33430`, captured `this` = its own `rcx`
(`[delegate+8]`), callback fn `0x1420d7470` (`[delegate+0x10]`), refcount via
`0x140927150`, and crucially sets the **bound flag** (`[rsp+0x50] = 3`,
i.e. delegate+0x30 = bound). It then `call 0x14209cb20` (manager), `mov rcx, manager`,
`lea rdx, delegate`, and `call 0x14209b280` (the builder). So the source delegate
handed to the builder IS bound, which means in a normal run `0x140b0ac10` installs
it into the manager and the later notify fires `0x1420d7470` (the manifest handler
that drives the per-file downloads via `0x14209a8c0`).

## Why the notify is skipped in our run

Mechanically, the manager listener is set inside the builder from the caller's
delegate, and the caller does mark that delegate bound. So at the binary level the
slot *should* be populated by the time the completion runs. For it to be observed
NULL/0 at completion, one of the following must hold in our live run:

1. **(Most likely) The probe inspected the wrong object.** The notify gate is on the
   MANAGER (`r15`), whose `+0x20/+0x30` is the listener; the resource's
   `+0x20/+0x30` are HTTP strings. If the live probe used the resource pointer (the
   earlier assumption), a "NULL/0 listener" reading is a measurement artefact, not
   the true gate state. Re-probe `+0x20/+0x30` on `r15` at `0x14209bc6c`.

2. The source-delegate "install" (`src.vtable[0x50]` inside `0x140b0ac10`) is itself
   predicated on a runtime condition that was false (e.g. a subsystem-enabled /
   license / "should subscribe" check), so the manager's slot was left cleared.

3. The manager instance at completion differs from the one the listener was
   installed on (re-creation/teardown between request and response).

Distinguishing these is a one-line live check (item 1) before any server change.

## Concrete next step

- **First (no server change):** at the completion notify gate `0x14209bc6c`, probe
  `[r15+0x30]` and `[r15+0x20]` where `r15` is the manager (the completion's `rcx`),
  NOT the FVKStaticDataResource. Also probe the source delegate's `+0x30` at the
  builder entry (`0x14209b2a3`) and whether `0x140b0ac10` takes its install branch
  (`src.vtable[0x50]`) vs. its clear branch (`0x140b0aca6`). This resolves whether
  the listener is genuinely never installed or merely mis-measured.
- **If the install branch is genuinely skipped**, the trigger to fix is upstream of
  this request: ensure the login flow reaches the state that builds a *bound*
  response delegate before issuing GetFileList. That is driven by the prior REST
  steps (clients/registration/connect), so the server-side lever is to make the
  immediately-preceding step return whatever the client needs to advance into the
  static-data step with its delegate bound — not anything in the static-data HTTP
  response body itself (the manifest parse already succeeds).

## Key VAs

- Manager singleton accessor: `0x14209cb20` (ctor zero-inits +0x20/+0x30).
- GetFileList request builder: `0x14209b280` … ret `0x14209b54a`.
- Delegate move/assign (installs manager listener): `0x140b0ac10`.
- Delegate-bind helper (binds completion to manager): `0x1420809a0`.
- Completion handler: `0x14209b550`; notify gate `0x14209bc6c` (`r15` = manager).
- FVKStaticDataResource ctor `0x142084880`, base ctor `0x142084ec0`, vtable
  `0x143111db0`; resource +0x20/+0x30 = HTTP method/URL strings.
- GetFileList trigger (builds bound response delegate): `0x1420d6930`; manifest
  handler callback `0x1420d7470`; per-file dispatch `0x14209a8c0`.
