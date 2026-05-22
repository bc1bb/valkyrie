---
doc: net-disasm
title: Disassembly-Recovered Fields & Method
summary: Targeted static disassembly (RIP-relative xref to UTF-16 grant strings) recovered new JSON fields (match-config, rank-up reward breakdown), the custom FVkJsonObject parser, and the PUT verb. client_id is runtime-built/non-pattern; and is NOT needed for re-implementation.
keywords: [disassembly, objdump, xref, rip-relative, fvkjsonobject, json fields, match config, rank up, put, client_id, method, e2, e3]
status: draft
updated: 2026-05-22
evidence: [E2, E3]
---

# Disassembly-Recovered Fields & Method

Because the Vk strings are **UTF-16** (`FString`), targeted disassembly can
anchor on a known wide string, find its RIP-relative cross-reference in `.text`,
and read the surrounding routine's other string constants. This recovered the
fields below (tier E3 — read from the request-builder routines).

## Method (reproducible, no symbols needed)

1. Find the `.rdata` VA of a UTF-16 anchor (e.g. `grant_type=steam_ticket`).
2. Byte-scan `.text` for a RIP-relative `disp32` whose target == that VA →
   the instruction (`lea reg,[rip+disp]`) referencing it.
3. Scan that routine's window for other `48/4C 8D 05+disp32` (`lea` of RIP) and
   decode the UTF-16 string at each target → the field/constant set the routine
   uses. (Script lives in the analysis notes; raw output stays git-ignored.)

Anchors used: `grant_type=steam_ticket` (→ SSO body builder @ ~`0x1420c6779`),
`grant_type=refresh_token` (→ a builder/parser @ ~`0x14208cc2b`).

## Recovered JSON fields (E3)

**Match / battle config** (session object, cf. `01-*`/`05-*`):
`goals_to_win`, `capture_speed`, `cooling_node_health`, `turrets_enabled`,
`shield_down_time`, `in_progress`, `team_0_pilot_id`, `team_1_pilot_id`
(per-team pilot id slots — note 0/1 team indexing matches `-NUMAITEAM0/1`).

**Rank-up / reward breakdown** (post-battle, cf. `11-*`):
`reputation`, `old_rank`, `new_rank`, and a points breakdown of
`base` + `bonus` + `boost` under an `event`. (Confirms rewards are an itemized
object, not a single number.)

## Confirmed mechanisms (E2/E3)

- **Custom JSON parser**: `FVkJsonObject` with a full typed getter set —
  `TryGetBoolField`, `TryGetNumberField`, `TryGetStringField`,
  `TryGetObjectField`, `TryGetObjectArrayField`, `TryGetStringArrayField`,
  `TryGetNumberArrayField`, `Find`. So responses contain **nested objects and
  arrays** (not flat), and the client **tolerates missing fields** (logs "Failed
  to find number field for field named '%s'" and continues) — a re-impl may omit
  unknown fields without crashing the client.
- **HTTP verb `PUT`** is used (alongside GET/POST) — some resources are updated
  via PUT (e.g. session/state mutations). A re-impl must route PUT.

## client_id: runtime-built, and NOT needed for re-implementation

A pattern scan of `.rdata` (ASCII + UTF-16) for an EVE-style credential found
**no client_id**: only an MD5-of-empty-string constant (`d41d8cd9…`), a base36
charset, and an unrelated UE4 GUID. The Basic-auth credential is assembled at
runtime from non-obvious constants (recovering the literal would need deeper
tracing of the `SetHeader("Authorization", …)` call).

> **Key insight:** the exact `client_id`/`client_secret` is **not required** to
> restore play. A preservation backend re-implements the **SSO too**, so it
> defines its own client-credential policy — it can accept any `Authorization:
> Basic` value the client sends (or ignore it). The credential only matters for
> talking to CCP's *original* (dead) SSO. So this is reclassified from a
> blocking unknown to **nice-to-have**. (See `03-*`, `12-*`.)

## Value

The disassembly method is now proven and can be pointed at any `Vk*Resource`
builder to recover its exact field set — the most productive remaining static
technique for fleshing out per-resource JSON schemas (tier E3), short of live
capture (E4).
