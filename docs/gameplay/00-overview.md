---
doc: gameplay-overview
title: Gameplay Systems Map
summary: Index/map of the client gameplay architecture (the VkGame module, ~1562 classes) by subsystem — player/ship control, combat, abilities, scoring, modes, VR UI, etc. Entry point for the whole-game RE.
keywords: [gameplay, overview, map, systems, vkgame, ship, combat, abilities, scoring, modes, vr, index]
status: living
updated: 2026-05-22
evidence: [E1]
---

# Gameplay Systems Map

The networking layer is documented under `docs/networking/`. This area
(`docs/gameplay/`) documents **how the game plays** — the client-side gameplay
architecture in the `VkGame` module (~1562 C++ classes). Scope per project:
code architecture & systems (clean-room), **not** asset/content RE (meshes,
audio, balance values in the `.pak`).

Method: class clusters (E1 source paths) + enums/fields (E2 strings) +
`recover_object.py`-style disassembly (E3) where structure matters.

## Subsystem catalogue (by class cluster)

| Subsystem | Key classes | Doc |
|-----------|-------------|-----|
| **Player / ship control** | `VkPlayerController`, `VkPawn`, `VkVehicle`, `Vk*MovementComponent`, `VkCockpit`, `VkLaunchTube`, `VkOrientationCircle` | `01-player-ship-control.md` |
| **Scoring** | `VkPlayerScoreObjective_*` (40+), `VkScore`, `VkPlayerScoreObjectiveManager` | `01-*` (scoring section) |
| **Combat / weapons** | `VkWeapon*`, `VkProjectile`, `VkMissile*`, `VkTarget*`, `VkTurret`, `VkDamage*`, `VkShield`, `VkExplosion*` | `02-combat.md` (planned) |
| **Abilities / ultimates** | `VkAbility*`, `VkUltimate`, `VkBuff*`, `VkSpiderbots`, `VkWarp`(MWD) | `03-abilities.md` (planned) |
| **Game-mode mechanics** | `VkCapture*`, `VkRelic`, `VkClone*`, `VkTeam`, `VkMap*`, `VkWarpGate` | `04-mode-mechanics.md` (planned); modes taxonomy in `engine/04-*` |
| **AI / bots** | `VkAI*` (~25) | `engine/07-ai-bots.md` (done) |
| **VR UI / interaction** | `VkVr*` (~22), `VkRadial`, `VkRadar`, `VkPing` | `05-vr-ui.md` (planned) |
| **Pilot / cosmetics (client)** | `VkPilot`, `VkInventory*`, `VkUpgrade`, cosmetic asset groups | `06-pilot-loadout.md` (planned); backend in `networking/11-*` |
| **Tournament / brackets** | `VkUIBracketComponent`, `VkBracketEditorActor`, `FVkBracketElementStructType` | `07-brackets.md` (planned) |
| **Framework / misc** | `VkGame*` (mode/state), `VkObject`, `VkGeometry`, `VkPost`(process), `VkQuick*` | as needed |

## Cross-references

- Networking/back-end for these systems: `docs/networking/` (esp. `08-*`
  replication of gameplay, `11-*` progression, `14-*` API fields).
- Input devices that drive ship control: `engine/03-input-peripherals.md`.
- Rendering/VR pipeline: `engine/06-rendering-audio-vr.md`.
- Game modes (what they are): `engine/04-game-modes.md`.

## Status

Gameplay RE in progress (networking complete). Docs added per subsystem; this
map updates as each is documented. The goal is the **whole** client RE'd and
clean-room documented.
