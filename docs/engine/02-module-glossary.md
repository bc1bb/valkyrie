---
doc: engine-glossary
title: Module & Subsystem Glossary
summary: Navigational reference — the Vk C++ modules, the networking classes (cross-linked to deep docs), and the VkGame gameplay subsystem clusters by class-name prefix.
keywords: [glossary, reference, modules, classes, subsystems, navigation, vkgame, vkplayer, vkvr, weapons, ai, index]
status: draft
updated: 2026-05-22
evidence: [E1]
---

# Module & Subsystem Glossary

A map of the codebase's shape (from ~13k embedded source paths, E1). Networking
classes link to their deep docs; gameplay clusters are navigational only (we are
not RE-ing gameplay/assets, per project scope).

## C++ modules

| Module | Files | Purpose | Deep doc |
|--------|------:|---------|----------|
| `VkGame` | ~1562 | All gameplay (pawns, AI, weapons, UI, modes). | clusters below |
| `VkRestUtils` | ~148 | REST backend client (`Vk*Resource`). | `networking/01`, `03`, `10` |
| `VkStaticData` | ~44 | Static data loading/exposure. | `networking/10` |
| `OnlineSubsystemVk` | ~38 | Custom OSS (identity/session/oculus). | `networking/07` |
| `VkCore` | ~22 | Shared core utilities. | — |
| `VkFramerateStats` | ~6 | Perf telemetry. | `networking/07` |
| `OnlineSubsystemVkSteam` | ~2 | Steam ticket bridge. | `networking/07` |

Plugins: `DirectInputPlugin` (HOTAS/joystick), `TrackIR` (head tracking),
`TobiiEyetracking` (eye tracking) — peripheral input, not networking.

Shipped third-party middleware (exact versions in `binary/02-shipped-runtime-
manifest.md`): OpenVR v1.0.2, Steamworks v1.32, PhysX 3 + APEX (Clothing/
Destructible) physics, NvVolumetricLighting, Oculus Wwise spatializer, Ogg/Vorbis,
Tobii — all client/engine-local, no backend relevance.

## Networking class quick-reference

| Class | Role | Doc |
|-------|------|-----|
| `VkHttpRequest` / `VkAuthHttpRequest` / `VkSSOHttpRequest` | HTTP plumbing + auth/SSO. | `01`, `03` |
| `Vk*Resource` (Pilot/Session/Battle/BattleServer/Client/StaticData/Challenge/Implant/Cosmetic/LootCapsule…) | REST resource clients. | `01` |
| `VkVirtualGoods`, `VkLeaderboards` | Store, leaderboards. | `01` |
| `VkWatchDog` + `FHeartBeatThread` | Heartbeat/keepalive. | `06` |
| `OnlineIdentityVk` / `OnlineSessionVk` / `VkOculusPlatform` | OSS interfaces. | `07` |
| `PartyBeaconClient/Host/State` | Reservation matchmaking (engine-stock). | `06` |
| `WebSocketNetDriver` / `WebsocketConnection` | Replication transport (engine-stock). | `02` |

## VkGame gameplay subsystem clusters (by class-name prefix)

Navigational only — these describe what the gameplay module contains:

| Prefix | ~Count | Subsystem |
|--------|-------:|-----------|
| `VkPlayer*` | 42 | Player controller/state/pawn/camera. |
| `VkVr*` | 22 | VR UI / interaction / HMD-specific. |
| `VkAI*` | ~25 | Bot AI: controllers, behaviour, navigation, abilities, formations. |
| `VkWeapon*` | 7 | Weapons. |
| `VkVehicle*` | 6 | Ships ("vehicles"). |
| `VkTarget*`, `VkMissile*` | 8 | Targeting & missiles. |
| `VkCapture*` | 4 | Capture-point game mode. |
| `VkCockpit*` | 3 | In-ship cockpit UI/items. |
| `VkAbility*`, `VkUltimate*`, `VkBuff*` | several | Active abilities / ultimates / buffs. |
| `VkInventory*`, `VkUpgrade*`, `VkImplant*` | several | Progression/loadout items. |
| `VkSpectator*`, `VkTeam*`, `VkMap*` | several | Spectating, teams, maps. |
| `VkClone*`, `VkSpider*`/`VkSpiderbots*` | several | Specific gameplay actors. |

## How to use this glossary

Start here to locate a topic, then jump to the `networking/` deep doc for
protocol detail, or to `09-session-lifecycle-and-roadmap.md` for the big picture
and re-implementation order.
