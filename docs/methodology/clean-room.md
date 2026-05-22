---
doc: method-cleanroom
title: Clean-Room Methodology
summary: Rules for documenting the game without copying its code; evidence tiers; what may be committed.
keywords: [clean-room, methodology, copyright, evidence, legal, ethics]
status: draft
updated: 2026-05-22
---

# Clean-Room Methodology

We document **observable behaviour and interfaces**, not creative expression.
Goal: a specification complete enough that an independent implementer could
build a compatible server *without ever reading game code or assets*.

## The two-room model (for any future re-implementation)

- **Documentation room (this repo):** observes the client — its network
  traffic, its embedded interface descriptions, its file formats — and writes
  neutral specifications. May look at the binary.
- **Implementation room (separate, future):** reads ONLY this repo's specs.
  Never touches the original binary, assets, or decompiler output.

Keeping the rooms separate is what makes a re-implementation defensible.

## What MAY enter this repo

- Prose descriptions of architecture, protocols, message flows, state machines.
- Tables of endpoint names, field names, enum values, status codes.
- Our own diagrams, our own analysis scripts.
- Short factual identifiers (class names, paths) as **evidence citations**.

## What may NOT enter this repo

- Game binaries, DLLs, `.pak`, movies, assets — anything shipped (git-ignored).
- Raw string dumps, raw disassembly/decompilation listings (git-ignored under
  `analysis/raw/`).
- Verbatim copyrighted text/code beyond minimal identifiers needed as evidence.

## Evidence tiers (cite the tier in each claim)

| Tier | Source | Confidence |
|------|--------|------------|
| E1 | Embedded build metadata / source-path strings | High for *structure*, not behaviour |
| E2 | Embedded format strings, symbol/import names | Medium-high |
| E3 | Static disassembly of a specific routine | Medium (easy to misread) |
| E4 | Observed live network traffic (capture) | Highest for protocol truth |
| E5 | Inference / analogy to public UE4 4.14 behaviour | Hypothesis only |

Prefer E4 for protocol claims once captures are possible. Until then, label
protocol statements as derived from E1/E2/E5 and mark `status: draft`.

## On the Unreal Engine baseline

The client is stock-ish **UE 4.14.3**. UE4 source is publicly available under
Epic's license. Engine-level networking behaviour (NetDriver, replication,
RPC framing) can be described from public UE4 knowledge (tier E5) — that is
not CCP's proprietary work. We separate **engine-stock** behaviour from
**Vk-specific** behaviour (the `Vk*`/`OnlineSubsystemVk` modules) in every doc.
