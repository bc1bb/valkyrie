---
doc: reimpl-gaps
title: Server-Build Gap Analysis — What's Left & How to Close It
summary: For someone actually building the private server — the remaining unknowns sorted into (A) still recoverable from the binary now, (B) needs the live client/runtime as an oracle, (C) needs the original dead servers (lost — must be re-invented). Each with the method to close it.
keywords: [reimplementation, gaps, unknowns, roadmap, server, build, capture, disassembly, blocking, method, what to document next]
status: draft
updated: 2026-05-23
evidence: [E2, E3, E4, E5]
---

# Server-Build Gap Analysis — What's Left & How to Close It

Companion to `reimpl/01-mvp-server-guide.md` (the build steps) and
`networking/09-session-lifecycle-and-roadmap.md` (priorities). This doc answers a
narrower question: **what still needs documenting/determining to actually build
the server, and how would you close each gap.** Sorted by *how* it's obtainable,
because that dictates who can do it and when.

Most of the protocol is documented; the server simulation ships in the binary
(`05-*`/`08-*`). The gaps below are the delta between "comprehensive paper spec"
and "compiles + the client reaches a match."

## A. Still recoverable from the binary now (static — no servers needed)

These can be documented today with the existing tools (`recover_object.py`,
`disasm_func.py`, string mining). Worth doing; tractable.

| Gap | Why it matters to a server | Method to close |
|-----|----------------------------|-----------------|
| ~~**Exact REST route templates**~~ **(largely closed)** | The server must route the real paths. | **Done (E2/E3, `14-*`):** only a few **entry-points** are hardcoded; everything else is HATEOAS `*_uri` the server controls. Base URL `{scheme}://{tenant}.{domain}/{version}/valkyrie/{resource}`; versions are per-resource (v1.0/v2.0). |
| **server→VGS call set** (what the *dedicated server* itself POSTs) | A re-impl backend must accept the server's lifecycle/registration calls, not just the client's. | Partly done (`battles` lifecycle, `battleservers` reg — `05-*`/`13-*`); finish by disasm of the server-only resources. |
| **HTTP status → client behavior contract** | Knowing 401→refresh, 409→conflict, version-gate etc. lets the server drive client flows deterministically. | String/disasm pass on the response handlers (partial: 401-refresh, incompatible-build gating known). |
| ~~**WebSocket connect URL format**~~ **(closed for URL; token still open)** | The Plane-1→Plane-2 handoff; the server hands the client this URL. | **Done (E2, `02-*`/`05-*`):** backend returns `battleServerUri`; client `ConnectToBattle` → UE4 `Browse`/`PendingNetGame` opens the `WebSocketNetDriver` (`host:port`). It's a **stock UE4 connect URL** — return a reachable `ws(s)://host:port`. (The join *token* placement in `NMT_Login` is still bucket-B.) |
| **Static-data file taxonomy** (what *categories* of files `GetFileList` returns) | Static data is **P0** (likely gates load). Names recovered; the set/contents aren't. | Disasm the static-data loader's expected `StaticDataUniqueName`s; the file *contents* are in the pak (out of scope) but the **list shape** is recoverable. |
| **Remaining per-resource field sets** (thin resources) | Completeness of the object model. | `recover_object.py` on any not-yet-anchored resource (the object model is already audited "complete" in `13-*`, but value-types remain — see B). |

## B. Needs the live client as an oracle (runtime — client runs, servers don't)

These can't be read reliably from strings; you get them by **running the shipped
client against your own stub and observing what it sends/rejects**. This is the
real time-sink and the highest-value next step.

| Gap | Why it blocks a working build | Method to close |
|-----|-------------------------------|-----------------|
| **Exact JSON value types & nesting per resource** | Field *names*+grouping are known (E3), but a wrong type/nesting makes the client reject a response. | Stand up the stub (`reimpl/01-*`), point the client at it, iterate on each rejected response. **The** convergence loop. |
| **TLS trust / cert pinning** | Determines whether a local CA suffices or you need a binary shim. | Run the client against a local TLS endpoint; observe accept/reject (`04-*`). |
| **Tenant subdomain actually used** | The server must answer on the right host. | Config-driven (`-TENANT=`/`VkGame_TenantDomains`, `04-*`) — confirm the concrete value at runtime. |
| **NMT_Login join-token wire layout** | The dedicated server admits the client based on it. | Capture the WS connect locally once the client reaches Plane 2. |
| **Client boot/launch path** | Headless/Proton launches stalled in analysis; you need the client to *run* to do any of the above. | A VR-capable Windows host is the path of least resistance; document the working launch invocation. |

> The whole of (B) collapses once you have **one** thing: the client booting and
> talking to a stub you control. That single milestone de-risks the entire
> estimate. It is the recommended next action.

## C. Lost with the servers — must be *re-invented*, not recovered

The original behavior here is gone (dead backend) and isn't in the client. A
private server **defines its own** policy; there's nothing to document beyond
"you choose."

- **JWT signing key/algorithm** — you mint your own (the client doesn't verify;
  your dedicated server accepts your key, `03-*`/`05-*`).
- **OAuth `client_secret`** — irrelevant; `client_id=valkyrieClient` is a public
  client with empty secret (`13-*`).
- **Matchmaking skill/rank algorithm** — invent any policy; the client only needs
  a session allocated (`06-*`).
- **Economy balance** (prices, reward curves, drop tables) — pick your own; these
  were server-side business logic (`11-*`).
- **Backend persistence schema** — your design choice; only the *response shapes*
  are constrained (A/B above).

## What "done enough to play" actually requires

From `09-*` priorities, crossed with the above:

1. **SSO** (A-complete) — buildable now.
2. **clients/accounts/pilot/static-data** bootstrap (A-known shapes, B value-types)
   — buildable as stubs now; firm up by iteration.
3. **session→battle-server launch + PartyBeacon** (A/engine-stock) — buildable now.
4. **In-match** (engine-stock, free) — runs as shipped.
5. Everything else (store/loot/leaderboards/challenges/daily-challenges) — stubs.

So: **(A) is documentation work that can proceed immediately; (B) is gated only
on running the client once; (C) is not "documentation" at all — it's design
freedom.** The most valuable next deliverable is not more docs but the **first
bring-up** (a minimal SSO + stub backend + a booting client), which converts the
(B) unknowns from "blocked" to "iterate."

## Test-harness docs that would help (not yet written)

- A **fixture set** of canned envelope+content responses per P0 resource (from
  `13-*` shapes) to seed the stub.
- A **launch runbook** for the dedicated server (`05-*` args) and for the client
  (the working boot invocation, once found).
- A **request log/diff harness** spec: capture what the client sends to the stub,
  diff against expected, to drive the (B) iteration loop.
