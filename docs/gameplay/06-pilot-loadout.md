---
doc: gameplay-pilot-loadout
title: Pilot, Loadout & Customization (client)
summary: Client-side model of the pilot avatar, the 3+2-slot loadout (EVkInventorySlot Fire/Ability/Ultimate), hero-ship selection & upgrade trees, ship/pilot cosmetics (EVkCosmeticItemType/EVkCustomisationType), implants as timed gameplay modifiers, and the local persistent ownership store — i.e. how the in-game classes consume the progression/cosmetic data the backend serves.
keywords: [pilot, loadout, inventory, slot, hero ship, cosmetic, implant, upgrade, customization, tech tree, decal, skin, paintjob, helmet, suit, ownership, persistent data]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Pilot, Loadout & Customization (client)

The **client-side** representation of the pilot and everything equipped on the
ship: the cockpit pilot avatar, the loadout slot model, hero-ship selection and
its upgrade tree, ship/pilot cosmetics, implants (timed gameplay modifiers), and
the local persistent ownership store. This is the in-game consumer of the
backend progression/economy data — that data model (REST resources, currencies,
`hero_ships`/`applied_pilot_cosmetics`/`implants`/`upgrades`,
`heroCosmeticType.*`/`pilotCosmeticType.*` taxonomies) is documented in
[`networking/11-progression-economy-model.md`](../networking/11-progression-economy-model.md)
and [`networking/14-vgs-api-surface.md`](../networking/14-vgs-api-surface.md) and
is **not repeated here**. The loadout *slot* enum and ability/ultimate classes
that fill the slots are in [`gameplay/03-abilities.md`](03-abilities.md); the
ship/pawn/controller that wears the loadout are in
[`gameplay/01-player-ship-control.md`](01-player-ship-control.md).

Evidence: **E1** = embedded source paths (`analysis/raw/srcpaths.txt`); **E2** =
extracted enum/field/symbol strings (`analysis/raw/strings_all.txt`,
`strings_utf16.txt`). Class layouts (member order/inheritance) are not recovered;
relationships below are inferred from grouping and call-sites unless stated.
Asset *content* (the actual meshes/textures and balance values in the `.pak`) is
out of scope — only the C++ interface and the data flow are documented.

## 1. Source clusters (E1)

| File (under `VkGame/Source/VkGame/`) | Subsystem |
|---|---|
| `Private/Cockpit/VkPilot.cpp` | Pilot avatar actor (`AVkPilot`). |
| `Private/Cockpit/VkCosmeticItemData.cpp` | Cosmetic item definition (`UVkCosmeticItemData`). |
| `Private/Weapon/VkInventoryData.cpp`, `Private/Weapon/VkInventoryItem.cpp`, `Classes/Weapon/VkInventoryItem.h` | Loadout slot container + equippable item base. |
| `Private/Vehicle/VkVehicleUpgradeData.cpp` | Ship upgrade definition (`UVkVehicleUpgradeData`). |
| `Private/Vehicle/VkVehicleCosmeticAssetGroup.cpp` | Ship exterior cosmetic asset group. |
| `Private/Stats/VkPersistentStats_Cosmetics.cpp` | Cosmetic/crafting stat tracking. |
| `Private/UI/HUD/VkUpgradeUI.cpp` | In-cockpit upgrade-icon HUD (`AVkUpgradeUI`). |
| `Private/UI/VrUi/ObjectGroups/Progression/VkVrUiScene_HeroUpgradeTree.cpp`, `.../VkVrUiHSOG_HeroUpgradeNode_Base.cpp` | VR hero upgrade-tree screen + nodes. |
| `Private/UI/VrUi/ObjectGroups/ShipCustomisation/VkVrUiScene_ExteriorCustomisation.cpp` | VR ship-skin/decal screen. |
| (no dedicated `.cpp`; symbols only) `AVkVrUiScene_PilotCustomisation_Base` and `_CloseUp`/`_FullPilot`/`_PreviewModel_Base` | VR pilot-customisation screen family. |

The matching backend `Vk*Resource` REST classes (`VkPilotResource`,
`VkHeroShipResource`, `VkHeroCosmeticResource`, `VkPilotCosmeticResource`,
`VkImplantResource`, `VkLootCapsuleResource`, `VkChallengeResource`, all under
`VkGame/Source/VkRestUtils/Private/Pilot/`) feed these clients; they are the
subject of `networking/11`/`14`.

## 2. The pilot avatar (`AVkPilot`, E1/E2)

`AVkPilot` is the in-cockpit pilot model (the visible avatar, not the
`AVkPlayerState`/account). It is built from swappable **asset groups**:

| Class | Role |
|---|---|
| `UVkPilotAssetGroup` | Base group of pilot mesh/anim assets. |
| `UVkPilotAssetGroup_Body` | Body assets; `VkPilotBodyAssets`. Gender variants `Male_Body` / `Female_Body` (selected from the backend `gender` field, `networking/14`). |
| `UVkPilotAssetGroup_Head` | Head assets; `VkPilotHeadAssets`. |
| `VkPilotMeshData` | Resolved mesh data for spawning the avatar. |
| `VkPilotSetupInfo` | Setup descriptor used to assemble a pilot. |

The avatar's appearance is driven by the pilot-cosmetic selection (below); body
gender comes from the account's `has_set_gender`/`gender` state
(`ServerSetPilotGender` RPC, `networking/14`).

## 3. Loadout slot model (`EVkInventorySlot`, E2)

The equippable loadout is a fixed set of slots, enum `EVkInventorySlot`
(also summarised in `gameplay/03-abilities.md`):

| Value | Meaning |
|---|---|
| `Fire1` | Primary weapon. |
| `Fire2` | Secondary weapon. |
| `Ability1` | First active ability. |
| `Ability2` | Second active ability. |
| `Ultimate` | Charge-gated ultimate. |
| `EVkInventorySlot_MAX` | Sentinel. |

(`03-abilities.md` describes the 3-conceptual-slot Fire/Ability/Ultimate model;
the enum itself enumerates five entries — two fire, two ability, one ultimate.)
The corresponding **input** actions are a separate VR-input enum: `EVR_Fire1`,
`EVR_Fire2`, `EVR_Ability`, `EVR_Ability2`, `EVR_Ultimate` (plus `EVR_Boost`
etc.) — these map controller input to the slot that fires (input layer,
`engine/03-input-peripherals.md`).

### Inventory container & item (`UVkInventoryData` / `AVkInventoryItem`, E2)

| Class | Role / key fields (E2) |
|---|---|
| `UVkInventoryData` | The per-ship loadout asset. Holds `Slots` and `InventoryClasses` — the set of equippable item classes. Diagnostics: *"Inventory Data asset '%s' needs resaving!"*. |
| `AVkInventoryItem` | Base class for anything occupying a slot (weapons, abilities, ultimates, deployables). Key members: `InventoryClass`, `InventorySlot` (an `EVkInventorySlot`), `ActivationMethod` (`EVkActivationMethod` = `Default`/`HoldAndRelease`), `ActivationConditions`. Runtime API includes `GetInventorySlot`, `GetActivationMethod`, `IsActive`, `Interrupt`, `SetAbilityCooldown`, `ServerSetWantsActive`. |
| `VkInventorySlotData` | Per-slot data record. |
| `VkInventorySlotActivationCondition` (+ `EVkInventoryActivationCondition` = `NoCondition`/`BlockedByOnly`/`BlockedAndInterruptedBy`) | Gates when a slot may activate relative to other slots (`ActivationBlockedBy`, `ActivationInterrupts`, `ConditionSlot`). |
| `VkInventoryRadarInfo` | Radar/HUD info for a deployed inventory item. |
| `UVkInventoryItemMeshData` | 1P/3P mesh data (`Meshes1P`/`Meshes3P`). |

So a ship's loadout is an `UVkInventoryData` asset enumerating `Slots`, each slot
filled by an `AVkInventoryItem` subclass keyed to an `EVkInventorySlot`. The
concrete ability/ultimate classes that fill `Ability*`/`Ultimate` are the
`VkAbility_*`/`VkUltimate_*` roster in `03-abilities.md`. `UnlockInventoryItems`
gates which items are available to a pilot (driven by progression).

## 4. Hero ship selection & upgrades

A "hero ship" is the chosen playable ship. The client tracks per-ship state and
exposes a front-end loadout/upgrade UI.

### Per-ship runtime state (`VkHeroShipState`, E2)

`VkHeroShipState` (a value struct, persisted — see §7) carries:
`CurrentXP`, `CurrentLevel`, `ActiveUpgrades`, `PurchasedUpgrades`. The set is
stored as a keyed map (`HeroShipStates` / `HeroShipStates_Key`). So per ship the
client knows its XP/level and which upgrades are owned (`PurchasedUpgrades`) vs
currently equipped (`ActiveUpgrades`).

### Front-end loadout descriptor (`VkFrontEndHeroShipLoadout`, E2)

The loadout screen is data-driven by `VkFrontEndHeroShipLoadout`:
`DisplayName`, `ShipDescription`, `LoadoutDescription`, `LoadoutStats`,
`UpgradeStats`, the four stat axes `Attack`/`Defence`/`Mobility`/`Tec` (Tec =
"Technology"; note enum spelling `EVkShipModificationType::Tec`), the per-ship
baselines `ShipBaseAttack`/`ShipBaseDefence`/`ShipBaseMobility`/`ShipBaseTech`,
plus `HeroUpgrades` and nested `HeroShipLoadouts`. Stat axes are enumerated by:

`EVkShipModificationType` = `Attack`, `Defence`, `Mobility`, `Tec`.

`GetHeroShipDisplayName` resolves a ship's name; `ShipClassControlNode` /
`ShipClassName` and `shipclass.Fighter`/`Heavy`/`Support`/`Legendary` tag the
ship class. Legendary ships have extra framing
(`VkFrontEndHeroShipLegendaryFrameMapping`, `LegendaryFrame`,
`LegendarySkinUniqueName`).

### Upgrade definition (`UVkVehicleUpgradeData`, E2)

An upgrade is a typed property override applied to the ship/movement/weapon:

| Type/struct | Values / fields |
|---|---|
| `EVkUpgradeType` | `Vehicle`, `MovementComponent`, `InventoryItem` — what the upgrade modifies. |
| `EVkUpgradePropertyType` | `None`, `Float`, `Int`, `Bool`, `Colour`, `Effect`, `Material`, `StaticMesh`, `ProjectileClass`, `CrosshairClass`. |
| `VkUpgradePropertyDefinition` | `PropertyName` + `PropertyType` — names the property to override. |
| `VkUpgradeValues` | The typed value union: `FloatValue`/`IntValue`/`BoolValue`/`ColourValue`/`EffectValue`/`MaterialValue`/`StaticMeshValue`/`ProjectileClassValue`/`CrosshairClassValue`. |
| `VkPropertyUpgrade` (`PropertyUpgrades`) | One property override (carries `UpgradeIcon`). |
| `UVkVehicleUpgradeData` | The upgrade asset = a set of `PropertyUpgrades` plus `VehicleTechTreeName`. |

This is how the `hero_upgrades` the backend stores (`networking/11`) translate
into concrete gameplay changes: each owned upgrade is a `UVkVehicleUpgradeData`
whose `VkUpgradeValues` overwrite a named `EVkUpgradePropertyType` property on
the `EVkUpgradeType` target. Several ability/movement fields are explicitly
upgrade-driven (`CooldownTimeUpgradeRTPC`, `DurationUpgradeRTPC`,
`MWDCooldownTimeUpgradeRTPC`, etc., `03-abilities.md`). Diagnostic on partial
failure: *"Upgrade '%s' : One or more Inventory Item upgrades could not be
handled!"*.

### Upgrade UI

- `AVkUpgradeUI` — in-cockpit HUD that renders active upgrade icons on a base
  mesh (`SetupIconMeshes`, sockets per upgrade; `VkUpgradeIconsChangedSignature`
  fires on change).
- `AVkVrUiScene_HeroUpgradeTree` + node actors `AVkVrUiHSOG_HeroUpgradeNode_Base`
  / `_StartNode` / `_EndNode` — the VR tech-tree screen. `VkFrontEndHeroUpgrade`
  is the per-node front-end record (`Attack`/`Defence`/`Mobility`, +/-
  descriptions, `UpgradeStaticDataLink`). `AVkVrUiHSOG_PilotLevelData` tracks
  tree-wide state: `XPTransferUnlocked`, `AllUpgradesPurchased`,
  `PurchaseHoldFactor`. Purchasing is a hold-to-confirm action
  (`OnBeginPurchase`, `HeroUpgrade PurchaseConfirmationCallback`, failure
  strings `HeroUpgradePurchaseFail_Title`/`_Body`/`_OK`). Tech-tree visuals:
  `TechTreeName`/`TechTreeIcons`/`VkTechTreeIconSet`.

## 5. Cosmetics

Cosmetics split into **ship (hero) cosmetics** and **pilot cosmetics**, each
applied client-side from backend ownership/applied state.

### Cosmetic item definition (`UVkCosmeticItemData`, E2)

A single cosmetic item is a `UVkCosmeticItemData` with:
- `ItemType` (`EVkCosmeticItemType` = `StaticMesh`, `SkeletalMesh`, `Texture`,
  `Material`, `Cockpit`) and `ItemCategory`;
- the asset per type: `StaticMeshTemplate`, `SkeletalMeshTemplate`,
  `AnimBlueprint`, `Material`, `Texture`;
- placement: `AttachSocketName`, `RelativeTransform`.

Validation diagnostics confirm the type→template contract, e.g. *"Cosmetic Item
'%s' set to StaticMesh type, but no StaticMeshTemplate specified!"* and *"Cosmetic
Item '%s' could not find socket '%s' on cockpit mesh '%s'!"*.

### Ship/exterior cosmetics

- Asset grouping: `UVkVehicleCosmeticAssetGroup` (`AssetPropertyObjects`) groups
  the meshes/materials that make up a ship's exterior look.
- Customisation categories: `EVkCustomisationType` = `SKINS`, `DECALS` (the two
  exterior-customisation tabs; cf. backend `heroCosmeticType.paintJob` /
  `heroCosmeticType.decal` / `heroCosmeticType.vehicleCosmetic` /
  `heroCosmeticType.cockpit`, `networking/14`).
- VR screen: `AVkVrUiScene_ExteriorCustomisation` (strings
  `VrUi_ShipCustomisation_Apply`/`_Applied`/`_Owned`/`_Purchase`,
  `VrUi_ExteriorCustomisation_NoItems`).
- Front-end representation: `VkFrontendCosmeticDefinition` with
  `TextureRepresentation` / `MaterialRepresentation` / `MeshRepresentation`
  (how a cosmetic is previewed in the menu).

### Pilot cosmetics

- Categories: `EVkPilotCustomisationType` = `NOT_SET`, `SUIT`, `HELMET`,
  `ANIMATION` (cf. backend `pilotCosmeticType.suit` / `pilotCosmeticType.helmet`).
- VR screens: `AVkVrUiScene_PilotCustomisation_Base` (+ `_CloseUp`,
  `_FullPilot`, `_PreviewModel_Base`), HSOG variants
  `AVkVrUiHSOG_PilotCustomisation_CloseUp`/`_FullPilot`/`_PreviewModel_Base`.
  Strings `PilotCustomisation_Apply`/`_Applied`/`_Purchase`.
- The equipped set is a replicated list (see §6).

### Rarity tiers (E2)

Cosmetics and implants carry a rarity tier surfaced via per-category description
getters: `GetTierDescription_{category}_{Common|Rare|Epic}` for categories
`Decal`, `VehicleCosmetic`, `PilotBody`, `PilotHelmet`, `Implant`. So the rarity
ladder is **Common → Rare → Epic** (Legendary appears only as a *ship class*
`shipclass.Legendary`, not a cosmetic tier here).

## 6. Applying cosmetics & replication (E2)

Cosmetic application is a server-validated action so other clients render the
right look (kill-cams, spectator):

- **Cockpit cosmetics** are spawned by `AVkCockpit::SpawnAndAttachCosmeticItems`
  (attaches each `UVkCosmeticItemData` to its cockpit socket). Cockpit-upgrade
  cosmetics are handled by `ApplyCockpitUpgadeCosmeticItem` (sic — binary spells
  it "Upgade"), which size-matches `FirstPersonMeshAssets` vs `ExteriorMeshes`.
- **Pilot cosmetics** are a replicated list `PilotCustomisationList` on the
  pilot/pawn, set via the `ServerSetPilotCustomisationList` RPC
  (+ `_Validate`), with `OnRep_PilotCustomisationList` →
  `ApplyPilotCustomisationListVisuals` rebuilding the avatar.
  `VkOnRep_PilotCustomisationListSignature` notifies listeners. A second RPC
  `ServerSetPilotCosmetics` (+ `_Validate`) sets the pilot-cosmetic selection.
- The applied set is also exposed on `AVkPlayerState` as `AppliedPilotCosmetics`
  / `OwnedPilotCosmetics_Head` / `OwnedPilotCosmetics_Body` (replicated so peers
  can build the avatar), plus `OwnedImplants`.
- For death/kill presentation, `VkKilledByInfo` carries the killer's
  `VehicleUniqueName`, `VehicleCosmeticUniqueName`, `DecalUniqueName` so the
  kill-cam shows the correct ship/skin/decal.

Cosmetic *unique-name* strings follow a structured naming scheme (e.g.
`heroCosmetic.vehicleCosmetic.<Ship>_<Variant>_PJ_<…>` for paint jobs); the
scheme is an interface fact, the specific named assets are `.pak` content (out of
scope).

## 7. Implants — timed gameplay modifiers (E2)

Implants are **time-limited** gameplay buffs (not permanent cosmetics), matching
the backend's `implant_seconds` semantics (`networking/11`/`14`).

- State on `AVkPlayerState`: `bImplantActive`, `ActiveImplantSecondsRemaining`,
  `ImplantTimeUsedInSeconds`; initialised by `AVkPlayerState::InitImplant`
  (`InitImplant`). `ImplantUniqueName` identifies the equipped implant;
  `ImplantTimeString` formats the remaining time for UI.
- Ownership: `OwnedImplants` (replicated; persisted as `OwnedImplants` /
  `OwnedImplants_Key`, §8).
- Activation UI: `Implant ActivateConfirmationCallback`, failure strings
  `ImplantActivateFail_Title`/`_Body`/`_OK`, `NoImplantText`. Art:
  `VkImplantArtAsset` / `ImplantArtAssets`, `SelectionRing_Implant`.
- Rarity tiers Common/Rare/Epic via `GetTierDescription_Implant_*` (§5).

So an implant is a consumable timed modifier: the client counts down
`ActiveImplantSecondsRemaining` while `bImplantActive`, and the backend tracks
remaining seconds across sessions.

## 8. Local persistent ownership store (`VkPersistentData`, E2)

A **local** save file mirrors part of the pilot's owned/applied state (a cache
on top of the authoritative backend). Path template
`%s//CCP Games//Valkyrie//%s//_pers.data`; operations `PersistentData.Save` /
`.Load` / `.Clear`; a size guard exists
(*"Persistent data size is larger than the expected max size, please increase
the EXPECTED_SAVE_MAX_SIZE_BYTES"*) and corruption handling (*"Persistent Data
file was corrupt, resetting data"*, *"… not saved correctly. Deleting"*).

Persisted keyed collections (struct `VkPersistentData`):

| Key | Holds |
|---|---|
| `HeroShipStates` / `HeroShipStates_Key` | Per-ship `VkHeroShipState` (XP/level/owned+active upgrades, §4). |
| `OwnedImplants` / `OwnedImplants_Key` | Owned implants (§7). |
| `OwnedPilotCosmetics_Head` / `OwnedPilotCosmetics_Body` | Owned pilot cosmetics. |
| `PurchasedCosmeticItems` | Purchased cosmetic set. |
| `AppliedSkin` / `AppliedDecal` / `AppliedInterior` | Currently-applied ship cosmetics. |
| `bMarketingMessageSeen` / `MarketingFirstSeenTime`, `LastLeagueTypePlayerWasIn`, `ChallengeTracking`, `EndedChallenges`, `UserSettings`, `Recalls` | Misc local progression/UX state. |

The cosmetic/crafting *stats* sit in `VkPersistentStats_Cosmetics`:
`PurchasedCosmeticItems`, `AppliedSkin`/`AppliedDecal`/`AppliedInterior`,
`CraftedFighters`/`CraftedHeavies`/`CraftedSupports`/`CraftedCoreShips`,
`CollectedComponentSalvage`/`CollectedPrimeSalvage`. There is also a
`VkPilotCosmeticOwnershipState` struct for ownership bookkeeping. The "Purchased
item" classification enum is `EVkPurchasedItemType` = `SkillTreeItem`,
`LoadoutSlot`, `NumPersistentDataTypes` (`_MAX`) — i.e. purchasable items are
either skill-tree (upgrade) items or loadout slots.

## 9. Backend → client data flow (summary)

1. On login the pilot object + its HATEOAS links (`hero_upgrades_uri`,
   `hero_cosmetics_uri`, `applied_pilot_cosmetics_uri`, `cosmetics_uri`,
   `gender_uri`, …, `networking/14`) are fetched via the `Vk*Resource` layer.
   `AVkPlayerControllerBase::PilotResourceSet` marks the pilot data as loaded.
2. Owned/applied state populates the client structures above
   (`VkHeroShipState`, `OwnedImplants`, `AppliedPilotCosmetics`, owned cosmetics)
   and is mirrored into the local `VkPersistentData` cache (§8).
3. In the front-end the player selects a hero ship
   (`VkFrontEndHeroShipLoadout`), buys/equips upgrades
   (`UVkVehicleUpgradeData` via the hero-upgrade tree), and applies cosmetics
   (`ServerSetPilotCustomisationList` / `ServerSetPilotCosmetics`).
4. In battle the chosen ship's `UVkInventoryData` defines the `EVkInventorySlot`
   loadout; `AVkInventoryItem` subclasses (weapons + the `VkAbility_*`/
   `VkUltimate_*` roster) fill the slots; equipped `UVkVehicleUpgradeData`
   overrides apply; cosmetics spawn via `SpawnAndAttachCosmeticItems`; an active
   implant counts down (`ActiveImplantSecondsRemaining`).

## 10. Re-implementation / preservation relevance

- The **client classes are shipped** — a preservation client runs them as-is.
  What a private backend must supply is the *data shapes* these classes read:
  the pilot object with cosmetic/implant/upgrade/hero-ship collections and the
  `*_uri` links (`networking/11`/`14`). If those fields are absent or malformed,
  the customisation/upgrade UI (`AVkVrUiScene_HeroUpgradeTree`,
  `AVkVrUiScene_ExteriorCustomisation`, pilot-customisation scenes) can error;
  serving permissive defaults (all ships owned, empty applied-cosmetics, no
  active implant) is enough to reach a match (`networking/11` "Re-implementation
  value", roadmap `networking/09`).
- Cosmetic/loadout/upgrade *mutations* are **server-validated RPCs**
  (`ServerSetPilotCustomisationList`/`_Validate`, `ServerSetPilotCosmetics`,
  hero-upgrade purchase). A re-impl backend must accept the corresponding REST
  writes (apply-cosmetic, purchase-upgrade) and persist them; the battle server
  trusts the replicated `AVkPlayerState` cosmetic/implant fields for
  presentation.
- The local `_pers.data` cache is **client-local** and self-healing (corruption
  → reset); it is not a source of truth and need not be reproduced server-side,
  but a re-impl should expect the client to write it.
- Upgrades are pure property overrides (`EVkUpgradePropertyType` on
  `EVkUpgradeType` targets) — gameplay-affecting ones (cooldowns, movement,
  damage) must be honoured **server-side** to stay authoritative/cheat-resistant
  (consistent with `networking/08`, `networking/15`); cosmetic-only overrides
  (`Colour`/`Material`/`StaticMesh`/`Effect`) are client presentation.

## 11. Open questions

- Class layout/inheritance: whether `AVkInventoryItem` is the common base of the
  `VkAbility_*`/`VkUltimate_*`/`VkWeapon*` classes or a sibling that wraps them
  (needs layout analysis; symbols only show the shared API). See `03-abilities`
  open question on `VkActivatableEffect`.
- Exact replicated property layout of `PilotCustomisationList` /
  `AppliedPilotCosmetics` / `OwnedImplants` on `AVkPlayerState`/pawn (sync
  granularity) — see `networking/08` per-pawn property-layout open question.
- Which of `EVkUpgradeType::Vehicle`/`MovementComponent`/`InventoryItem` upgrades
  are server-authoritative vs cosmetic — overlaps the `hero_ship_stats`
  authoritative-vs-cosmetic open question in `networking/11`.
- Implant duration semantics on the client (`ActiveImplantSecondsRemaining`
  countdown vs `ImplantTimeUsedInSeconds` accrual) vs the backend
  `implant_seconds` (countdown vs expiry) — `networking/11` open question.
- `EVkPurchasedItemType` only enumerates `SkillTreeItem`/`LoadoutSlot`; how
  cosmetics/implants are classified for purchase (separate path vs not persisted
  under this enum) is unconfirmed.
- The full set of ship classes beyond `Fighter`/`Heavy`/`Support`/`Legendary`
  (and what `CraftedCoreShips`/`CollectedPrimeSalvage` "crafting"/"salvage"
  economy maps to) — partly content, partly the loot/economy surface
  (`networking/14`).
