---
doc: gameplay-brackets
title: Tournament / Brackets
summary: No tournament/competition-bracket subsystem ships in this title; every "bracket" symbol is a HUD reticle/target marker. Competitive standing is the league/leaderboard backend instead.
keywords: [tournament, bracket, competition, league, leaderboard, bracket editor, element, seeding, ladder, naming collision, hud bracket]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

## Summary (read this first)

**There is no tournament-/competition-bracket subsystem in the shipped client.**
This doc was scoped on the assumption that the `Vk*Bracket*` symbol family might
encode competition brackets (seeding, knockout rounds, ladders). The evidence
shows it does not. **Every `bracket` symbol in the binary refers to a *HUD
reticle / target marker*** — the world-space UI shapes drawn around enemy ships,
objectives, turrets, capture points and missile locks. That subsystem is
documented in [`gameplay/05-vr-ui.md`](05-vr-ui.md), not here.

Competitive *standing* exists, but it is a separate, backend-driven concept:
the **league / leaderboard** model (no bracket structure, no head-to-head tree).
See [`networking/11`](../networking/11-progression-economy-model.md) and
[`networking/14`](../networking/14-vgs-api-surface.md).

This document records the negative finding, disambiguates the naming collision,
and points to where the real systems live so a re-implementer does not waste
effort building a tournament engine that the game never had.

> Correction note: [`05-vr-ui.md`](05-vr-ui.md) (in its "Targeting brackets"
> section) speculated that `VkBracketEditorActor` / `FVkBracketElementStructType`
> were a "tournament-bracket side (tournament ladders)" deferred to this doc.
> That speculation is **wrong** — those symbols are part of the HUD bracket
> system (see below). No tournament ladder exists.

## What was searched (E1 strings, E2 srcpaths)

| Probe | Result |
|---|---|
| `tournament` | 0 hits except the engine artifact URL `http://www.unrealtournament3.com/` (stock UE4). |
| `seeding`, `bracket_seed`, `seed_number` | 0 hits. |
| `competition`, `playoff`, `knockout`, `elimination`, `quarterfinal`, `semifinal`, `grand_final`, `round_of` | 0 hits. |
| `ladder`, `ranked bracket`, `bracket match`, `prize`, `qualifier` (competition sense) | 0 hits. (`qualifier` hits are X.509/LDAP cert noise — `Policy Qualifier CPS`, `generationQualifier`.) |
| `bracket` in `backend_fstrings.txt` (REST/event surface) | **0 hits** — no bracket entity is ever sent to or read from the backend. |
| `EVkUIBracketElementStates` (anchor from task brief) | 0 hits; the actual enum is `EVkUIBracketStates` (a HUD enum). |

The absence of any backend bracket field is the strongest signal: a real
tournament system in a UE4 online title requires server-authoritative bracket
state (matchups, advancement). None exists in the request/event string set that
otherwise enumerates pilots, sessions, leagues, and leaderboards.

## The `Vk*Bracket*` symbol family is the HUD, not a tournament

All bracket source files live under one folder, `Private/Brackets/` (E2), and
all are HUD/reticle components:

| Source (E2) | Role |
|---|---|
| `Brackets/VkUIBracketComponent.cpp` | Base world-space bracket widget on a tracked object. |
| `Brackets/VkTargetLockBracketComponent.cpp` | Target-lock reticle bracket. |
| `Brackets/VkTargetLeadingBracketComponent.cpp` | Lead-pip ("shoot ahead") bracket. |
| `Brackets/VkMissileLockBracketComponent.cpp` | Missile-lock-on bracket. |
| `Brackets/VkCapturePointBracketComponent.cpp` | Objective / capture-point bracket. |
| `Brackets/VkBracketEditorActor.cpp` | **Design-time layout actor** for placing HUD bracket *elements* (see below). |

Supporting HUD-bracket identifiers found in the binary (E1) — these are all
visual/material/placement properties, conclusively HUD, not competition:
`BracketColour`, `BracketColourCurve`, `BracketFont`, `BracketMaterial`,
`BracketMaterialOverride`, `BracketDynamicMaterials`, `BracketIcons`
(`bUseBracketIcons`), `bAffectsEnemyBracketRange`, `bHideWhenBracketObstructed`,
`OverriddenBracketRange`, `ReticleBracket`, `HitPointBracket`,
`CoolingNodeBracket`, `AVkBracketManager`, `UVkBountyBracketComponent`,
`UVkUICapturingTurretBracketComponent`, the deprecated
`UDEPRECATED_Vk*TurretBracketComponent` set, and the cvar
`r.EnableBracketsInScreenShots` ("Enable / Disable Ship Brackets in
Screenshots"). A `VkBracketSmartPing` even attaches a ping marker to a HUD
bracket.

### `FVkBracketElementStructType` — a HUD element type tag, not a competitor record

The struct named in the task brief, `FVkBracketElementStructType`, is part of the
HUD bracket editor, not a tournament data structure. Its companions in the
binary are `AddUIBracketElement`, `VkUIBracketElement`, and
`UVkBracketElementComponent` (E1) — i.e. it describes a single visual *element*
inside a HUD bracket widget. The only member tokens recovered for it are an
enum-style type tag:

| `FVkBracketElementStructType` member tokens (E1) | Reading |
|---|---|
| `Type` | The element's discriminator field. |
| `TYPE_BASE`, `TYPE_UI`, `TYPE_MAX` | UE4-style enum bounds for that `Type` (base / UI element / sentinel). |

`TYPE_UI` / `TYPE_BASE` / `TYPE_MAX` is the autogenerated `_BASE`/`_MAX` bracket
of a small `UENUM`; there are **no** competitor/seed/score fields, no opponent
references, and no advancement state. This is structurally incompatible with a
tournament bracket and fully consistent with a HUD-element type tag.

### HUD bracket enums (for completeness — see `05-vr-ui.md`)

| Enum (E1) | Note |
|---|---|
| `EVkUIBracketElementType` (`_MAX`) | Kind of HUD bracket element. |
| `EVkUIBracketStates` (`_MAX`) | HUD bracket display state machine. |

The `VkBracketEditorActor` error strings confirm the editor's purpose is HUD
layout, e.g. *"Could not find reference screen size component or editor component
on actor — cannot add bracket elements"* and *"Fullscreen bracket %s component is
not centred, this may result in strange bracket elements"* (E1). These reference
*screen size* and *centring* — screen-space HUD placement, not match scheduling.

## Where competitive structure actually lives

The game's competitive ranking is the **league** model and the
**leaderboards** — flat ranked lists, not brackets:

| Backend identifier (E1 `backend_fstrings.txt`) | Meaning |
|---|---|
| `leagues`, `Leagues`, `show_leagues`, `%sleagues?%s` | League listing endpoint. `leagues` GET/DELETE (DELETE ≈ leave league). |
| `league`, `league_score`, `league_position` | A pilot's current league, competitive score, and rank within it. |
| `hero_leaderboard_stats`, `%shero_leaderboard/%d?%s`, `%shero_leaderboard?%s` | Per-hero (ship) leaderboard. |
| `%shero_survival_leaderboard/%s/%s%s`, `%swormhole_leaderboard/%d?%s`, `%swormhole_leaderboard?%s` | Mode-specific leaderboards (survival, wormhole). |
| `leaderboard=` | Generic leaderboard query param. |

Steam-side leaderboard mirroring exists too
(`FOnlineAsyncTaskSteamRetrieveLeaderboard(Entries)`,
`FOnlineAsyncTaskSteamUpdateLeaderboard`), again a flat score list.

These are documented in detail in
[`networking/11`](../networking/11-progression-economy-model.md) (`league_score`
in the progression model) and
[`networking/14`](../networking/14-vgs-api-surface.md) (the `leagues` endpoint
and pilot fields). The closest thing to "grouping players for competition" is
**custom matches** — `EVkCustomMatchType` = `PUBLIC` / `FRIENDS` / `PRIVATE`
visibility on a session (see [`engine/04-game-modes.md`](../engine/04-game-modes.md))
— which is lobby visibility, still not a bracket.

## Relevance to a re-implementation

- **Do not build a tournament/bracket service.** Nothing in the client requests,
  parses, displays, or persists tournament brackets, seeds, or match trees.
- To reproduce competitive standing, implement the **leagues + leaderboard**
  REST surface (see `networking/11`, `networking/14`) and the Steam leaderboard
  tasks — flat ranked lists keyed by `league_score` / per-mode score.
- The `Vk*Bracket*` C++ family is a **client-local HUD** concern; reproduce it
  per [`05-vr-ui.md`](05-vr-ui.md). It has no server contract.

## Open questions

- None material to a backend re-implementation. The negative finding is robust:
  no tournament symbols in code paths *or* in the backend string surface.
- Minor: whether any unshipped/editor-only tournament tooling existed in the
  original project is unknowable from the shipped binary; if it did, it left no
  runtime trace. Treat "tournaments" as out of scope for this title.
