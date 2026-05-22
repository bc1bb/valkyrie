---
doc: ref-enums
title: Enum / Type Reference Index
summary: Navigational index of the key EVk* enums recovered across the project (116 total) — name → purpose → doc that covers it. Look here to find which doc details a given enum/state-machine.
keywords: [enum, reference, index, evk, types, state machine, glossary, lookup]
status: living
updated: 2026-05-22
evidence: [E2]
---

# Enum / Type Reference Index

A lookup index for the ~116 `EVk*` enums found in the client (E2). This lists
the architecturally significant ones with a one-line purpose and the doc that
documents their values/role. Full value lists live in the linked docs; this is
the "which doc?" map.

## Framework / modes / session

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkGameModeType` | The game modes (Control/Base/TDM/…) | `engine/04-game-modes` |
| `EVkGameModeSubLevels` | Objective-set sublevels composited per mode | `engine/04`, `gameplay/10` |
| `EVkCustomMatchType` | Custom-match visibility (PUBLIC/FRIENDS/PRIVATE) | `engine/04` |
| `EVkCustomMatchHostState` | Custom-match host state machine | `gameplay/04`, `13` |
| `EVkMatchSettingsType` | Per-mode match-setting categories | `gameplay/04` |
| `EVkUIGameStateConnectionState` (`eConnectionState`) | Client connect/menu state machine | `networking/09`, `gameplay/13` |
| `EVkValidTeam` | Team identity | `gameplay/04` |

## Player / scoring / stats

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkPlayerScoreEvent` | Scorable events (kills/objectives/…) | `gameplay/01` |
| `EVkBackEndPlayerStatsRefresh_DataType` | Which stat blocks refresh from backend | `networking/11`, `gameplay/01` |
| `EVkViewMode` | Camera/view mode | `gameplay/01`, `09` |
| `EVkRespawnMapState` | Between-lives spawn-select state machine | `gameplay/10` |
| `EVkBoxStatsOption` | Stat-display options | `gameplay/05` |

## Combat / weapons / damage

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkWeaponState`, `EVkMuzzleFireMode` | Weapon firing state/mode | `gameplay/02` |
| `EVkWeaponHitType`, `EVkTargetZone` | Hit classification / hit zone | `gameplay/02` |
| `EVkHomingState`, `EVkHomingEvent`, `EVkHomingEMPInteraction` | Missile homing lifecycle | `gameplay/02` |
| `EVkMissileLockAvailability` | Missile-lock availability | `gameplay/02`, `05` |
| `EVkCrosshairMeshState` | Crosshair visual state (heat/spread/lock) | `gameplay/05` |
| `EVkTeamBaseShipShieldState` | Carrier/base-ship shield gate | `gameplay/04` |
| `EVkCloakState`, `EVkTargetType`/`EVkAITargetType` | Cloak / targeting | `gameplay/02`, `engine/07` |

## Abilities / ultimates / effects

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkAIAbilityType` | Deployable ability roster (shared) | `engine/07`, `gameplay/03` |
| `EVkAIAbilityState` | Bot ability deploy-decision lifecycle | `engine/07` |
| `EVkActivatableEffectState` | Player ability runtime lifecycle | `gameplay/03`, `11` |
| `EVk_MWDMode` | Micro-Warp-Drive mode | `gameplay/03` |
| `EVkCloakState`, `EVkECMState`, `EVkMiniOverShieldState`, `EVkCaptureDroneState`, `EVkDronesState`, `EVkSpiderBotState` | Per-ability state machines | `gameplay/03` |
| `FVkEffectManagerCommandListAction` | Effect-manager command opcodes | `gameplay/11` |

## Mode mechanics

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkCapturePointState` / `EPlayerCaptureState` | Capture-point state | `gameplay/04` |
| `EArmadaState` | Carrier-assault state machine | `gameplay/04` |
| `EVkCloneVatScreenType`, `EVkCloneVateShipState` | Clone-vat respawn UI/state | `gameplay/04`, `09` |
| `EVkRelicDistanceCategory`, `EVkSalvageType` | Relic/extraction & salvage | `gameplay/04` |
| `EVkPickupState` | World pickup state | `gameplay/04` |

## AI

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkAIBehaviourState`, `EVkAIBehaviourStyle` | Bot behaviour FSM / archetype | `engine/07` |
| `EVkAIPathState`, `EVkAIPathFindState` | Bot navigation/pathing | `engine/07` |
| `EVkBrainSection` | AI "brain" decision sections | `engine/07` |

## UI / VR / radar / comms

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkRadarObjectStates`, `EVkRadarObjectTransitionStates` | Radar contact states | `gameplay/05` |
| `EVkSmartPingType` | Smart-ping categories | `gameplay/05` |
| `EVkVrUiAnchorPoint`, `EVkVUiSceneStartupPhase`, `EVkVrUiQuitType`, `EVkFEAssetType` | Front-end VR scene framework | `gameplay/05`, `13` |
| `EVkControllerScreenOptionTypes` | Controller/settings screen options | `gameplay/13` |
| `EVkCATMessageVisualType`, `EVkCATMessageActionType` | "CAT" combat-alert/notification messages | `gameplay/05` |
| `EVkWarningVolume_WarningLevel` | Out-of-bounds warning levels | `gameplay/10` |
| `EVkQuickChatMessage`, `EVkQuickChatMenuSegment`, `EVkQuickChatTeamMember` | Quick-chat comm wheel | `gameplay/12` |
| `EVkVoiceClipSpeaker`, `EVkVoiceClipUIState` | VO speaker/clip state | `gameplay/12` |
| `EVkRecommendedTransitionType` | Camera/scene transitions | `gameplay/13` |

## Loadout / cosmetics / economy

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkInventorySlot` | Loadout slots (Fire/Ability/Ultimate) | `gameplay/03`, `06` |
| `EVkCosmeticItemType`, `EVkPilotCustomisationType`, `EVkCustomisationType` | Cosmetic item/customisation types | `gameplay/06` |
| `EVkUpgradeType`, `EVkUpgradePropertyType`, `EVkShipModificationType` | Upgrade/stat modification | `gameplay/06` |
| `EVkPurchasedItemType`, `EVkTierType` | Purchase classification / rarity | `gameplay/06`, `networking/11` |
| `EVkMaterialProperty`, `EVkMaterialSwitchType` | Cosmetic material params | `gameplay/06` |

## Platform / data

| Enum | Purpose | Doc |
|------|---------|-----|
| `EVkSoftwarePlatform`, `EVkLoadScreenPlatform` | Platform (Steam/Oculus) branching | `networking/03`, `07` |
| `EVkDataChunkID`, `EVkDataChunkID` / static-data links | Static-data chunking | `networking/10`, `gameplay/08` |

## Notes

- This index is selective (~60 of 116). Narrative/cutscene & one-off UI enums
  (e.g. `EVkShipyardCh1_State`, `EVkBrainSection` variants) are omitted or only
  noted; see the subsystem doc for full value lists.
- Values were read from the binary's RTTI/format strings (E2). A few names carry
  the binary's own typos (e.g. `CloneVate`, `Utlimate_OverCharge`) — preserved
  as-found for grep-ability.
