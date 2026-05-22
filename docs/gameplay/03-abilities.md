---
doc: gameplay-abilities
title: Abilities, Ultimates & Buffs
summary: The player ability system — VkAbility_* active-ability roster + VkUltimate_* roster, the VkActivatableEffect activation/cooldown lifecycle, per-ability state machines, the loadout slot model (EVkInventorySlot), and specific abilities (SpiderBot, Micro-Warp-Drive, EMP/ECM/EMS, BuffBeam).
keywords: [abilities, ultimate, buff, cooldown, charge, activatable effect, spiderbot, emp, ecm, ems, micro warp drive, mwd, nova bomb, overcharge, shield stripper, buffbeam, loadout slot]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Abilities, Ultimates & Buffs

Each ship carries an **active ability** and an **ultimate** alongside its
primary weapon. This subsystem covers their classes, the shared
activation/cooldown lifecycle, the per-ability state machines, and the specific
gameplay devices. It is mostly **client/engine-local presentation + state**
sitting on top of server-authoritative gameplay (`networking/08-*`); the
dedicated server runs the authoritative effect logic (the same roster the bots
use, `engine/07-ai-bots.md`). We document the code architecture only — balance
numbers (cooldown seconds, radii, damage) are content in the `.pak` (out of
scope).

## Loadout slot model (`EVkInventorySlot`, E2)

A ship loadout has three activatable slots: `Fire` (primary weapon), `Ability`
(one active ability), `Ultimate` (one charge-gated ultimate). `VkAbilityInfo` /
`VkAbilityScreenInfo` describe an ability for the front-end loadout screens;
`InventorySlotData` + `InventorySlotActivationCondition` gate when a slot may
fire. The loadout itself is selected through the `Loadout*` UI family and
enforced server-side via the vehicle-selection RPCs (`networking/08-*`,
`networking/11-*` for the backend `hero_upgrades` that tune it).

## Activation/cooldown lifecycle (`VkActivatableEffect`, E1/E2)

There is no single `VkAbilityBase`; instead every ability/ultimate is its own
`VkAbility_*` / `VkUltimate_*` class that realises a shared **activatable
effect** contract. The canonical lifecycle enum is
`EVkActivatableEffectState`:

`Idle → Activating → Active → Deactivating → Dead`

This is the player-facing analogue of the bots' `EVkAIAbilityState`
(`Unarmed → CanDeploy → ShouldDeploy → Deploying → CoolDown`,
`engine/07-ai-bots.md`) — the AI enum models *deciding to deploy*; the
`VkActivatableEffect` enum models *the effect's runtime once deployed*.

Timing/charge state is carried in a consistent field vocabulary (E2):
`Cooldown` / `CooldownTime` / `CooldownDuration`, `CooldownRemaining`,
`CooldownEndTime`, `ActivationTime` / `ActivationTimer`, `ChargeTime` /
`chargeTimer` / `ChargeValue`, `Duration` / `DurationRemaining`, `Recharge`
(`RechargeDelay`, `RechargeAmountPerSecond`), `Uses`. Ultimates additionally
track `UltimateCharge` (a charge meter that fills over the match) and reference
their concrete class via `UltimateClass`. There are upgrade hooks
(`CooldownTimeUpgradeRTPC`, `DurationUpgradeRTPC`) that scale these values from
the upgrade/loadout data.

### HUD / presentation classes (E1/E2)

| Class | Role |
|-------|------|
| `VkAbilityHUDItem` | The ability's HUD widget (icon + state). |
| `VkCooldownTimerBar` | Cooldown-progress bar (`CooldownProgress`, `CooldownTimerElementIdentifier`). |
| `VkUltimateBaseUI` | Ultimate charge/ready presentation. |
| `VkBracketStateAbilityIcon` | Ability icon used in tournament-bracket UI. |
| `VkCrosshairMeshState` | Crosshair states feeding back ability/weapon readiness — `ChargeValue`, `TimeUntilCooldown`, `CanDrainShield`/`CanRepairShield`/`CanDrainCapacitor`/`CanRepairCapacitor` (used by drain/repair-type abilities), `CantActivate`, etc. |

## Active-ability roster (`VkAbility_*`, E1/E2)

The player active-ability set is broader than the bots' 7-entry
`EVkAIAbilityType` (the AI enum is the subset bots actually deploy). Recovered
classes:

| Class | Purpose (interface-level) | State enum (E2) |
|-------|---------------------------|-----------------|
| `VkAbility_EMP` | Electro-magnetic pulse — disables/disrupts enemy systems. | (homing variant `EVkHomingEMPInteraction`) |
| `VkAbility_ECM` / `VkAbility_ECMSphere` | Electronic counter-measures — defeats incoming missile locks (sphere = area form). | `EVkECMState` = Idle, Firing, CoolDown |
| `VkAbility_EMS` | EMS device (area emitter; `VkEMS`, `VkEMSEffectsOptions`). | — |
| `VkAbility_CloakingDevice` | Stealth/cloak. | `EVkCloakState` = Unavailable, Available, Active, Cooldown |
| `VkAbility_OverShield` | Deployable extra shield layer. | — |
| `VkAbility_MiniOverShield` | Targeted/auto mini-shield (locks onto a ship). | `EVkMiniOverShieldState` = Idle, SearchingForTarget, LockingTarget, Active, Cooldown |
| `VkAbility_SelfRepair` | Self-repair/heal. | — |
| `VkAbility_BuffBeam` | Tethered support beam — repairs allies / damages enemies (see below). | `EBuffBeamDamageState` = Neutral, Repair, Damage |
| `VkAbility_MarkTarget` | Tags an enemy (recon/assist). | — |
| `VkAbility_Sonar` | Reveals nearby enemies (ping). | — |
| `VkAbility_HUDScrambler` | Scrambles the enemy HUD. | — |

State changes are surfaced through multicast delegates
(`VkAbility_ECMStateChangedSignature`, `VkECMSuccessSignature`,
`VkEMSActorOverlapSuccessSignature`) so the HUD/audio and the scoring system
react.

Not realised as `VkAbility_*` classes but present in the shared roster as
deployable devices: **CaptureDrone** (`VkCaptureDroneUI`,
`EVkCaptureDroneState` = Moving, TurningToMove, TurningToTarget, Beaming;
captures objectives), **Mines** (`VkMineData`), **CounterMeasures** (flares/
decoys), and **SpiderBot** / **Micro-Warp-Drive** (own clusters below). These
match the bot roster (`engine/07-ai-bots.md`); `VkAICaptureDroneControl` /
`VkAIEMPControl` are the AI wrappers around the same devices.

## Ultimate roster (`VkUltimate_*`, E1/E2)

Ultimates are charge-gated (`UltimateCharge`) and many share a bomb base. The
AI roster (`EVkAIAbilityType`) lists four — `Ultimate_EMP`, `Ultimate_NovaBomb`,
`Ultimate_ShieldStripper`, `Utlimate_OverCharge` (sic, the binary misspells
"Ultimate") — but the client defines a wider set of `VkUltimate_*` classes:

| Class | Purpose (interface-level) |
|-------|---------------------------|
| `VkUltimateBase` (+ `VkUltimate_BombBase`) | Base ultimate; bomb-type base for the projectile ultimates. |
| `VkUltimate_EMP` / `VkUltimate_EMPBomb` | Large-area EMP ultimate. |
| `VkUltimate_NovaBomb` | Heavy explosive bomb (`NovaBombControl`). |
| `VkUltimate_ShieldStripper` | Strips enemy shields. |
| `VkUltimate_OverCharge` | Weapon overcharge buff (`OverChargeControl`, `OverchargeStateChangedSignature`, `OverchargeLimit`/`OverchargeTimer`/`OverChargeCurve`). |
| `VkUltimate_Invulnerability` | Temporary invulnerability buff. |
| `VkUltimate_OverShield` | Large over-shield buff. |
| `VkUltimate_RemoveOverheating` | Clears weapon heat (`OverheatBegin`/`OverheatEnd`, `OverheatingSettings`). |
| `VkUltimate_SuperMissile` | Powerful guided missile. |
| `VkUltimate_Projectile` | Generic projectile-launch ultimate base. |

`VkUltimate_OverCharge`, `VkUltimate_Invulnerability`, `VkUltimate_OverShield`
and `VkUltimate_RemoveOverheating` are *buffs/self-effects*; the EMP/Nova/
ShieldStripper/SuperMissile/Projectile group are *offensive deployables*.

## Buffs / activatable effects (E1/E2)

"Buff" here = a timed self/ally modifier riding the `VkActivatableEffect`
lifecycle. The most developed buff device is the **BuffBeam** (the support
"buff/repair beam"), a tethered beam that repairs allies or damages enemies
depending on lock state:

| Class | Role |
|-------|------|
| `VkBuffBeamLockSystem` (`VkBuffBeamLockConfig`, `VkBuffBeamLockedTarget`, `VkBuffBeamLockTierData`) | Target-locking — `LockTier`/`LockTime`/`LockTimer`, multi-target lock, `lockTierChangedSignature`. |
| `VkBuffBeamDamageModifier` (`VkBuffBeamDamageTierData`) | Applies the per-tier effect — `RepairRate` (allies) vs `DamageRate`/`DamageRateToOverlappingVehicles` (enemies); `EBuffBeamDamageState` = Neutral/Repair/Damage. |
| `VkBuffBeamCrosshair`, `VkBuffBeamAudio(Options)`, `VkBuffBeamEffectData/Options` | HUD / audio / VFX presentation. |
| Delegates | `VkBuffBeamEventSignature`, `VkBuffBeamTargetLockSignature`, `VkBuffBeamTargetsUpdatedSignature`. |

Other on-ship buffs/self-effects use the same effect machinery:
`VkShieldActiveEffect`, `VkOrientationLockedEffect`, `VkSenseOfSpeedEffect`,
plus the buff-type ultimates above (OverCharge/Invulnerability/OverShield/
RemoveOverheating). (Generic VFX classes `VkEffect*`/`VkTemporaryEffectsSubSystem`
are the rendering layer, `engine/06-*`, not the gameplay effect.)

## Specific abilities

### SpiderBot (`VkSpiderBot*`, E1/E2)

A deployable attach-and-attack drone. State machine `EVkSpiderBotState` =
`Idle → Attacking / Healing → Kill / Expired` (so a spiderbot can either attack
an enemy or heal a friendly, then either scores a kill or times out). Classes:
`VkSpiderBotData` (config), `VkSpiderBotAnimationComponent` /
`VkSpiderBotAnimInstance` / `VkSpiderBotAnimSlot` / `VkSpiderBotSocket` (rig),
`VkSpiderBotEffectSettings` / `VkSpiderBotMaterialTintSettings` (VFX),
`VkSpiderbotsUI` (HUD). Destroying one scores `SpiderbotKill`
(`EVkPlayerScoreEvent::SpiderbotKill`, `VkPlayerScoreObjective_SpiderbotKill`,
`gameplay/01-*`). Enemy/friendly spiderbots are AI target types
(`EVkAITargetType::Enemy/FriendlySpiderbot`).

### Micro-Warp-Drive (`VkMicroWarpDrive`, E1/E2)

A short burst/dash mobility ability. Classes: `VkMicroWarpDrive`,
`VkMicroWarpDriveUI`, `VkMWDBubbleEffect`, with state surfaced via
`VkMWDModeStateChangedSignature`. Cooldown/duration fields are MWD-prefixed
(`MWDCooldown`, `MWDCooldownTimer`, `MWDCooldownTimeUpgradeRTPC`,
`MWDDurationTimeUpgradeRTPC`, plus warning audio `MWDCooldownWarningAudio`).
Activating it scores `MWDActivated` (`VkPlayerScoreObjective_MWDActivated`).
**Distinct from `VkWarpGate`** — the map warp-gate actor / `WarpGates` mode
sub-level (`EVkGameModeSubLevels::WarpGates`, `VkWarpGateEngineModifiers`); the
MWD is the player ability, the warp gate is a level fixture (`gameplay/01-*`).

### EMP / ECM / EMS (E1/E2)

The electronic-warfare family. **EMP** (`VkAbility_EMP`, ultimate
`VkUltimate_EMP`/`VkUltimate_EMPBomb`) applies a "disable" — fields distinguish
direct vs partial hits: `DisableAmountPerDirectHit` /
`DisableAmountPerPartialHit` (and `…DoneForDirectHit`/`…DoneForPartialHit`),
`DisableDuration`. A homing EMP resolves per target via `EVkHomingEMPInteraction`
= `Destroy`, `Disrupt`, `Ignore`. Successful EMP scores `EMPSuccess`
(`VkPlayerScoreObjective_EMPSuccess`).

**ECM** (`VkAbility_ECM` / `VkAbility_ECMSphere`) is the defensive counter to
missile locks — `EVkECMState` = Idle/Firing/CoolDown, success tracked by
`ECMSuccess`/`ECMSuccessesRequired`/`ECMSuccessSignature` and scored as
`ECMSuccess` (`VkPlayerScoreObjective_ECMSuccess`). **EMS** (`VkAbility_EMS`,
`VkEMS`) is an area emitter that fires `VkEMSActorOverlapSuccessSignature` on
overlapping ships. These tie into the missile-lock states
(`EVkMissileLockAvailability` = Unavailable/Unlocked/Locked) handled by combat
(`gameplay/02-combat` planned).

## Ability parameters (E2)

Tunable property names (values are balance/pak, out of scope): `ActiveTime`
(how long an ability stays active), `CooldownDuration`/`CooldownTime` (recharge
after use), `cost`/`CostDisplayMode` (Energy cost — drawn from the shared
`EnergyComponent`, `gameplay/01`). **Ultimates** charge instead of cooldown:
`ChargeValue`/`ChargeTime`/`ChargeCurve` accrue an `UltimateCharge` (from combat
score/events) until full, then the ultimate is deployable. So: active abilities
= Energy-cost + cooldown; ultimates = charge-gated. A re-impl server tracks
Energy, cooldown timers, and ultimate charge per pilot (replicated, `08-*`).

## Re-implementation relevance

- A re-implemented **server** inherits the authoritative ability logic from the
  shipped binary (it is the same roster the bots run, `engine/07-ai-bots.md`);
  the backend only configures loadouts (`networking/11-*` `hero_upgrades`,
  ability/ultimate per `EVkInventorySlot`) and accepts the resulting
  score-events (`EMPSuccess`/`ECMSuccess`/`MWDActivated`/`SpiderbotKill`/…) in
  the match report (`networking/13-*`).
- Ability *activation* is a server-authoritative gameplay action: the client
  drives the `VkActivatableEffect` lifecycle/HUD locally and predicts, but the
  server resolves effects (consistent with server-validated fire,
  `networking/08-*`, `networking/15-*`). A re-impl must reproduce cooldown/charge
  gating server-side to stay cheat-resistant.
- All HUD/VFX/audio classes (`VkAbilityHUDItem`, `VkCooldownTimerBar`,
  `VkSpiderbotsUI`, `VkMWDBubbleEffect`, BuffBeam presentation) are
  client-local; a preservation client runs them as shipped.

## Open questions

- The exact base/interface relationship of `VkActivatableEffect` to each
  `VkAbility_*`/`VkUltimate_*` (composition vs inheritance) — needs class-layout
  analysis; no single `VkAbilityBase` was found in symbols.
- Which abilities/ultimates are *actually equippable per ship* vs legacy/unused
  (the class set exceeds the bot enum; the live loadout catalogue is data-driven
  via `VkAbilityInfo`/backend, not in symbols).
- Replicated property layout for an active effect (charge/cooldown sync between
  server and client) — see `networking/08-*` open question on per-pawn property
  layout.
- Balance values (cooldown seconds, charge rates, radii, disable amounts) — in
  the `.pak`/upgrade data (asset RE, out of scope).
