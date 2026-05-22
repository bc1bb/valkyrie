---
doc: engine-gamemodes
title: Game Mode Taxonomy
summary: Enumerated game modes (EVkGameModeType), objective sub-levels (EVkGameModeSubLevels), and custom-match visibility (EVkCustomMatchType) — the valid mode values a backend's session/matchmaking layer must recognize.
keywords: [game modes, gametype, control, carrier, tdm, survival, scout, extraction, wormhole, virus, bomb, custom match, friends, private, public, pve, pvp]
status: draft
updated: 2026-05-22
evidence: [E2]
---

# Game Mode Taxonomy

Recovered from the `EVkGameModeType` / `EVkGameModeSubLevels` /
`EVkCustomMatchType` enums (E2). These are the mode values that the session/
matchmaking layer references (the `-gamemode=` launch arg in `05-*` and the
`session_type` REST field in `01-*`). A re-implemented backend must accept the
relevant values when creating/allocating sessions.

## `EVkGameModeType` — top-level modes

| Value | Category (inferred) |
|-------|---------------------|
| `Control`, `Control_SinglePoint` | PvP objective — capture/hold point(s). |
| `Base`, `Base_PVP` | Carrier/base assault (attack the enemy carrier). |
| `TDM`, `TDM_SinglePlayer` | Team Deathmatch (MP / vs-AI). |
| `Bomb` | Bomb/charge objective. |
| `Bounty` | Bounty (target-kill) objective. |
| `Convoy` | Escort/convoy objective. |
| `Armada` | Large-scale / fleet mode. |
| `Extraction` | Extraction objective (PvE-style). |
| `Survival`, `Scout`, `Virus` | PvE / co-op scenarios. |
| `Training`, `NPE_TestArena` | Tutorial / New-Player-Experience. |
| `Prolog`, `CutScene`, `Recall_Shipyard1`, `Recall_Shipyard3` | Narrative / campaign ("Recall" story) & non-combat scenes. |

> The PvE/narrative modes (`Survival`, `Scout`, `Virus`, `Prolog`, `Recall_*`,
> `CutScene`, `*SinglePlayer`) run **standalone** and need little/no backend —
> consistent with the "PVE on dedicated server is standalone-only" warning seen
> in the binary. The PvP modes (`Control`, `Base_PVP`, `TDM`, `Bomb`, `Bounty`,
> `Convoy`, `Armada`) are the ones requiring matchmaking + a battle server.

## `EVkGameModeSubLevels` — objective sub-areas / streamed level chunks

`CarrierVolumes`, `Mines` (+ `Mines_SingleCapturePoint`,
`Mines_ThreeCapturePoints`), `Relics`, `Scout`, `Survival`, `VirusObjectives`,
`WarpGates`. These are sub-level / objective-set variants composited into a
match (e.g. a "Mines" map with one vs. three capture points). They explain the
`time_to_battle_join` / capture-point replication seen elsewhere.

## `EVkCustomMatchType` — custom match visibility

`PUBLIC`, `FRIENDS`, `PRIVATE` — the visibility/joinability of a custom session
(ties to the `CustomSession` path, `06-*`). A re-implemented backend's custom-
match creation should carry this visibility and gate joins accordingly.

## Challenge mode (`EVkChallengeModeSuccessCriteria` / `…TimerStartCondition`)

Challenges (`VkChallengeResource`, `01-*`) are parameterized by:
- success criteria: `AllObjectivesCompleted`, `AllTaggedObjectivesCompleted`,
  `AnyTaggedObjectiveCompleted`.
- timer start: `OnLaunchFinished`, `OnAnyObjectiveCompleted`,
  `OnTaggedObjectiveCompleted`.

This is the rule engine for time-trial / objective challenges; a backend serving
challenges supplies these parameters per challenge definition.

## Re-implementation value

Pin the **mode → backend-need** split: only PvP modes require the full
matchmaking/battle-server path; PvE/narrative modes are largely standalone. The
enum values here are the vocabulary the session/`-gamemode` plumbing expects.
