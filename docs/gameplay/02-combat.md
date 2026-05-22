---
doc: gameplay-combat
title: Combat & Weapons
summary: The VkWeapon*/VkProjectile/VkMissile*/VkTurret/VkDamage*/VkShield/VkExplosion class cluster — weapon-type taxonomy & firing, projectiles vs lock-on missiles, turrets, the multi-channel (shield/armour/hull/energy) damage model with hit-points & critical-hit-points, regenerating shields, and radial-damage explosions. Server-authoritative.
keywords: [combat, weapons, projectile, missile, targeting, lock-on, homing, turret, damage, shield, armour, hull, hitpoint, critical, explosion, radial damage, decloak, buff beam, salvo]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E3]
---

# Combat & Weapons

The shoot-and-be-shot loop layered on the ship-control core
(`01-player-ship-control.md`). Like all gameplay it is **server-authoritative**
(`networking/08-*`, `networking/15-*`): the client requests fire and predicts
effects; the **server resolves hits and applies damage**, then replicates the
result. Documented at the code/architecture level only — no balance values,
meshes, FX, or audio (those live in the `.pak`; out of scope).

Evidence: **E1** = embedded source paths (`analysis/raw/srcpaths.txt`); **E2** =
extracted enum/field strings (`analysis/raw/strings_all.txt`,
`strings_utf16.txt`); **E3** = disassembly via `recover_object.py` (anchors
confirmed to xref the binary; these symbols are looked up indirectly, so the
field constants come from the string evidence rather than a linear load list).

## Class cluster (E1/E2)

### Weapons & firing

| Class / struct | Role |
|----------------|------|
| `AVkWeapon` / `VkWeapon` | Base weapon actor (attached to a ship/turret muzzle). |
| `VkWeapon_Projectile` | Fires travelling projectiles (`AVkProjectile`). |
| `VkWeapon_Missile` | Fires lock-on / homing missiles (`AVkMissileActor`). |
| `VkWeapon_DepthCharge` | Deployable depth-charge / mine-style weapon (`VkDepthChargeConfig`, `VkDepthChargeInstance`, `VkDepthChargeEffects`). |
| `VkWeaponData` | Per-weapon config base. Subtypes carry the **weapon-type taxonomy** (below). |
| `VkProjectileWeaponData`, `VkArcingProjectileWeaponData` | Straight vs arcing projectile weapons. |
| `VkBeamWeaponData` (`VkBeamHitTargetData`) | Continuous beam weapon. |
| `VkInstantHitWeaponData` (`VkInstantHitEffectData`) | Hitscan / instant-hit weapon. |
| `VkMissileWeaponConfig` | Missile-launcher config (storage/salvo/regen, below). |
| `VkClusterBombWeaponConfig` | Cluster-bomb weapon (spawns child projectiles). |
| `VkWeaponMuzzles` (`_MeshSockets`, `_VkEffect`), `VkSocketMuzzleData`, `VkEffectMuzzleData`, `VkWeaponMuzzleEffects` | Muzzle/socket binding & muzzle FX; `GetMuzzleLocation`/`GetMuzzleDirection`. |
| `VkWeaponSpreadData` | Accuracy/spread cone. |
| `VkWeaponHeatData` | Heat / overheat model. |
| `VkWeaponAttachInfo`, `VkWeaponMeshShootContraints` [sic], `VkWeaponConfig` | Attach points & firing constraints. |
| `VkWeaponTargetInfo`, `VkVehicleTargetInfo`, `VkTurretTargetInfo`, `VkTargetData`, `VkTargetingData`, `VkTargetingBehaviour` | Per-weapon/owner target selection & current-target tracking. |
| `VkScriptedFiringBase` + `…BulletProjectiles` / `…BeamWeapon` / `…BuffBeamWeapon` / `…InstantHitWeapon` / `…Missiles` | Scripted (AI/cinematic/turret) firing drivers, one per weapon family — mirrors the player weapon-type set. |

### Projectiles & explosions

| Class / struct | Role |
|----------------|------|
| `AVkProjectile`, `VkLightweightProjectile` | Spawned projectile actor (full and lightweight variants). |
| `VkProjectileManager` / `AVkProjectileManager` | Pooled spawn/lifecycle of projectiles (perf-oriented batching). |
| `VkProjectileEffectsData` | Projectile FX/tracers. |
| `AVkBombBase`, `AVkBombShip`, `AVkBombSpline`, `AVkEMPBomb`, `AVkNovaBomb` | Bomb-class ordnance (incl. the `Ultimate_NovaBomb` payload, cf. `engine/07-*`). |
| `AVkExplosion` / `VkExplosion`, `VkExplosionComponent`, `VkPostExplosionAnimater` [sic] | Explosion actor/component on detonation/death. |
| `AVkRadialDamage` / `VkRadialDamage` | Area-of-effect damage volume (`ApplyRadialDamage`, `ApplyRadialDamageWithFalloff`). |
| `VkTeamBaseShipExplosionStyle` | Carrier/base-ship death explosion styling. |

### Targeting, lock-on & missiles

| Class / struct | Role |
|----------------|------|
| `VkTargetLockComponent`, `VkTargetLockBracketComponent` | Acquire & hold a lock; HUD lock bracket. |
| `VkTargetLeadingComponent`, `VkTargetLeadingBracketComponent` | Lead-reticle (aim-ahead) for travelling projectiles. |
| `VkMissileLockBracketComponent`, `VkMissileLockConfig`, `VkLockedTarget` | Missile lock acquisition/config; resolved locked target. |
| `VkMissileCrosshair` / `AVkMissileCrosshair` (`…Audio`, `…Element`, `…StickyLockAnim`), `AVkSuperMissilesCrosshair` | Missile reticle + "sticky lock" feedback. |
| `VkBuffBeamLockSystem`, `VkBuffBeamLockConfig`, `VkBuffBeamLockedTarget`, `VkBuffBeamLockTierData` | Lock system for the friendly **buff beam** (shield/armour repair beam). |
| `AVkLockableCrosshair`, `AVkLockOnBeamCrosshair`, `VkLockOnBeamCrosshair*` | Generic lockable crosshair + lock-on-beam reticle (incl. lock-on / shot-failed anims). |
| `VkMissileWarningDisplay(Base/Instanced)` / `AVkMissileWarningDisplay*`, `VkMissileWarningIcon`, `VkMissileWarningMainIcon`, `VkMissileIconElement`, `VkBracketIconMissile` | Incoming-missile warning HUD. |
| `VkBracketIconBuffBeam`, `VkBracketStateTakingDamage`, `VkWeaponBracketInfo` | Other combat HUD brackets (buff-beam, taking-damage). |

### Turrets

| Class | Role |
|-------|------|
| `AVkTurret` / `VkTurret` | Base turret actor. |
| `AVkSentryTurret` | Stationary auto-firing sentry. |
| `AVkDestructibleTurret` | Destructible turret (scores `TurretDestroyed`). |
| `VkTurretOwnerFixed`, `VkTurretOwnerChangeable` | Fixed vs capturable/player-controllable ownership (cf. `TurretControlKillBonus`/`TurretAssist`). |
| `AVkTurretStart`, `AVkTurretTarget`, `VkTurretSocket`, `VkTurretInfo`, `VkTurretsArray` | Turret placement, target, sockets, registry. |
| `AVkMiningTurretTarget`, `VkMiningTurretRef` | Mining-mode turret targets (cf. `EVkAIBehaviourState::Mining`, `engine/07-*`). |

### Damage & shields

| Class / struct | Role |
|----------------|------|
| `VkDamageComponent` | Per-actor health/damage owner; tracks hit-points and routes incoming damage. |
| `AVkHitPoint` | Discrete destructible **hit point** sub-actor (multi-part ships / boss / objective targets). |
| `VkHitPointDisplay`, `VkHitPointRef` | Hit-point HUD/refs. |
| `VkDamageModifier`, `VkDamageModifiersPerType`, `VkMarkedTargetDamageModifier`, `VkBuffBeamDamageModifier`, `VkBuffBeamDamageTierData` | Damage scaling: per-damage-type, "marked target" bonus, buff-beam (de)buff tiers. |
| `VkDelayedDamageEffect`, `VkDelayedDamageEvent`, `AVkDelayedDamageManager` | Damage-over-time / scheduled damage application. |
| `VkRecentDamage`, `VkRecentDamageRecord`, `VkDamageRecords`, `VkDamageTypeKillerInfo` | Recent-damage ledger for assists/kill attribution (feeds the scoring taxonomy, `01-*`). |
| `VkDamageFXElement` | Damage HUD/FX feedback. |
| `VkShieldInstComponent`, `VkVehicleShield` | Regenerating shield layer on a ship (cf. `01-*`). |
| `VkShieldStateChangeParams`, `VkShieldActiveEffect`, `VkShieldEffectOptions`, `VkShieldEffectMaterialOptions` | Shield state/visual effects. |
| `VkShieldBreak`, `VkShieldBreakParamBase/Float/Vector` | Shield-break (depletion) event params. |

## Enums (E2)

| Enum | Values | Meaning |
|------|--------|---------|
| `EVkWeaponState` | `Idle`, `PreFire`, `Firing` | Weapon firing state machine. |
| `EVkFireLoop` | `None`, `FirstPerson`, `ThirdPerson` | Which fire loop/FX context is active. |
| `EVkMuzzleFireMode` | `Sequential`, `Simultaneous` | Multi-muzzle firing order (alternate vs all-at-once). |
| `EVkWeaponHitType` | `Direct`, `Partial` | Resolved hit quality (full vs glancing/partial). |
| `EVkMissileLockAvailability` | `Unavailable`, `Unlocked`, `Locked` | Missile lock status against the current target. |
| `EVkHomingState` | `Launching`, `Tracking`, `LostTarget`, `Disrupted` | In-flight homing-missile state. |
| `EVkHomingEvent` | `HitTarget`, `HitNonTarget`, `Missed`, `LostTarget`, `Disrupted` | Homing-missile outcome event. |
| `EVkHomingEMPInteraction` | `Ignore`, `Disrupt`, `Destroy` | How a homing projectile reacts to EMP (counter-measure interaction). |
| `EVkDelayedDamageEventType` | `PointDamage`, `RadialDamage` | Scheduled-damage application kind (single-target vs area). |
| `EVkTargetZone` | `Zone_None`, `Zone_A`, `Zone_B`, `Zone_C` | Hit-zone / target-region classification. |
| `EVkMiniOverShieldState` | `Idle`, `SearchingForTarget`, `LockingTarget`, `Active`, `Cooldown` | "Mini over-shield" ability lifecycle. |
| `EVkTeamBaseShipShieldState` | `Active`, `Draining`, `Deactivated` | Carrier/base-ship shield phase (objective-driven). |
| `EVkCloakState` | `Unavailable`, `Available`, `Active`, `Cooldown` | Cloak ability state (relates to **decloak-on-damage**). |
| `EVkECMState` | `Idle`, `Firing`, `CoolDown` | ECM (counter-measures) state. |
| `EVkDronesState` | `Idle`, `Charging`, `Engaging`, `Disengaging` | Combat-drone deployment state. |

Damage-channel scoring events (`EVkPlayerScoreEvent`, full list in `01-*`):
`HitPointDestroyed`, `HitPointAssist`, plus `CriticalHitPointDestroyed`,
`TurretDestroyed`, `TurretAssist`, `TurretControlKillBonus`, `DroneDestroyed`,
`EMPSuccess`, `ECMSuccess`, `Repair`.

## Mechanics (analytical, from E2 field evidence)

### Firing & hit resolution (server-authoritative)
Combat RPCs over the WebSocket NetDriver (`networking/08-*`):
`ServerStartFire` / `ServerStopFire` gate continuous fire;
`ServerFireShot` and `ServerFireProjectile` are the per-shot/per-projectile
requests. The server is the authority on whether a shot connects:
`ServerNumHits` / `ClientNumHits` and the debug toggle
`ServerToggleWeaponHitCountDebug` indicate the **client reports/predicts hits
but the server reconciles the authoritative hit count** — the key cheat-resistance
boundary for a re-implementation. Multi-muzzle weapons fire per
`EVkMuzzleFireMode`; accuracy degrades via `VkWeaponSpreadData`
(`SpreadIncrementPerShot`, `MaxSpread`, `TimeToMaxSpread`, `TimeToResetSpread`)
and weapons can overheat via `VkWeaponHeatData` (`HeatGainPerSecond`,
`HeatLossPerSecond`). The HUD reflects these as `EVkCrosshairMeshState`
sub-states (`SpreadValue`, `HeatValue`, `ChargeValue`, `LockValue`).

### Projectiles vs missiles
- **Projectiles** (`VkWeapon_Projectile` → `AVkProjectile`/
  `VkLightweightProjectile`, pooled by `VkProjectileManager`): travel with a
  finite `ProjectileLife`, carry a `ProjectileClass`, and register near-misses
  via `ProjectileNearMissDistance`. Lead-aim is assisted by
  `VkTargetLeadingComponent`. Arcing variants use `VkArcingProjectileWeaponData`;
  cluster munitions (`VkClusterBombWeaponConfig`) split into child projectiles
  with their own `ClusterProjectile{Shield,Armour}DamageAmount` and
  `ClusterProjectileExplosionRadius`.
- **Missiles** (`VkWeapon_Missile` → `AVkMissileActor`): require a **lock**
  (`VkTargetLockComponent` / `VkMissileLockConfig`, gated by
  `EVkMissileLockAvailability` and `MaxLockDistance`). Lock acquisition is timed
  (`TierTimeToLock`) and the launcher meters ammo: `MaxStoredMissiles`,
  `MaxMissilesPerSalvo`, regen via `SecsToRegenOneMissile`. In flight a missile
  runs the `EVkHomingState` machine and resolves with an `EVkHomingEvent`;
  counter-measures intervene per `EVkHomingEMPInteraction`
  (`Ignore`/`Disrupt`/`Destroy`). Lock/launch are replicated
  (`RequestLock`, `MulticastBeginStickyLock`/`MulticastEndStickyLock`,
  `MulticastSendTargetConfirmed`, `ServerOnTargetSet`).
- **Buff beam** (`VkBuffBeamLockSystem` etc.): a *friendly* lock-on beam that
  repairs allies (`AllyShieldRepairRate`, `AllyArmourRepairRate`,
  `AllyEnergyRepairRate`) in tiers (`VkBuffBeamLockTierData`,
  `VkBuffBeamDamageTierData`) — the support counterpart to offensive weapons,
  scoring `Repair` (`01-*`).

### Damage model — multiple channels + hit points
Damage is **multi-channel**, not a single HP bar. Incoming damage carries a
`DamageType` (`DamageTypeClass`) with a `DamageCauser`/`OwningWeapon`, and is
applied through `VkDamageComponent` against, separately:
- **Shield** (`ShieldDamageAmount`, `EnemyShieldDamageRate`, `ShieldAmount`),
- **Armour** (`ArmourDamageAmount`, `EnemyArmourDamageRate`, `ArmourBuffAmount`),
- **Hull** (`HullDamage`, `HullAmount`),
- **Energy / capacitor** (`EnemyEnergyDamageRate`, `EnergyRechargeAmountPerSecond`).

`VkDamageModifiersPerType` (and the `DamageModifiersPerTypeMap`) scales damage
by type; additional modifiers stack: `VkMarkedTargetDamageModifier` (bonus vs a
"marked" target, `TargetMarkedTime`), `VkBuffBeamDamageModifier`,
`FriendlyFireDamageMultiplier`, and curve-based falloff
(`DamageOverDistanceMultiplierCurve`, `DamageOverTimeMultiplierCurve`).
**Hit points**: larger/objective entities are built from discrete `AVkHitPoint`
sub-actors (`InitialiseHitPoints`, `GetTotalHitPoints`, `GetNumHitPoints`);
each is destructible and may be a **critical hit point** (`CriticalHitPoint`,
`NumHitPointsRemainingForCritical`, `GetRemainingCriticalHitPointHealth`).
Destroying ordinary vs critical hit points scores `HitPointDestroyed` vs
`CriticalHitPointDestroyed` (assists thresholded by
`DamagePercentForHitPointAssist` / `…CriticalHitPointAssist`). This is the boss/
carrier/objective destruction mechanic. Recent-damage records
(`VkRecentDamage`, `VkDamageTypeKillerInfo`) drive kill/assist attribution feeding
the scoring taxonomy in `01-*`.

### Shields & regeneration
The ship shield (`VkShieldInstComponent`/`VkVehicleShield`, `01-*`) starts at
`InitialShield` and regenerates after a delay: `ShieldReplenishRate` /
`ShieldReplenishDelay` (and the generic `HealthReplenishRate`/`…Delay`,
`RechargeDelay`). Energy regen is similar (`EnergyRechargeAmountPerSecond`,
`RechargeAmountPerSecond`). Over-shield variants exist (`OverShieldPercentage`,
`EVkMiniOverShieldState`). `EVkTeamBaseShipShieldState`
(`Active`→`Draining`→`Deactivated`) gates the carrier/base-ship shield in
objective modes — i.e. the base ship is only damageable once its shield is
drained. Shield depletion fires `VkShieldBreak` (state/effect params).

### Explosions
On detonation/death an `AVkExplosion` spawns and `AVkRadialDamage` applies
area damage via `ApplyRadialDamageWithFalloff` over `DamageInnerRadius`/
`DamageOuterRadius` with `DamageFalloff` (optionally inverse-squared,
`bUseInverseSquaredFalloff`), plus physics impulse (`DamageImpulse`,
`bExplosionCanHurtInstigator`). `EVkDelayedDamageEventType` (`PointDamage`/
`RadialDamage`) routes scheduled detonations (mines/bombs).

### Decloak-on-damage
Taking enough damage forces a cloaked ship to decloak: `DecloakDamageThreshold`
+ `DecloakDamageTime` against `EVkCloakState`. (The cloak ability itself is in
the abilities subsystem, `03-abilities.md` planned; see also `engine/07-*` for
the AI ability roster.)

## Combat parameters (E2)

Tunable property names (values are balance/pak, out of scope) — deepening the
damage model:
- **Damage channels** (separate pools; cf. `OnRep_` shield/energy in
  `networking/08`): **Shield** (`ShieldAmount`/`ShieldBuffAmount`; break cycle
  `ShieldDownTime`→`ShieldReplenishDelay`→`ShieldRearmTime`), **Armour**
  (`ArmourBuffAmount`, `ArmourRepairRate`, `ArmourDamage`), **Hull** (`HullAmount`,
  `HullRepair`, `HullDamage`; collision via `HullCollisionEvent`/`HullScrape*`),
  plus **Energy** (`gameplay/01`). Shields regen after a delay; armour/hull repair
  at a rate.
- **Damage typing:** `DamageModifiersPerType`(`Map`), `DamageMultiplier`,
  `DamageFalloff`, `DamagePerSecond` — damage scaled by a per-type modifier map
  and range falloff (with `EVkTargetZone` / marked-target modifiers).
- **Weapons:** cooldown (`CooldownDuration`/`CooldownRemaining`), **heat**
  (`HeatGainPerSecond` — overheating), `DamageAmount`, `DamageRadius` (splash);
  crosshair reflects heat/cooldown (`EVkCrosshairMeshState`).

So the damage model is **stacked pools** (Shield→Armour→Hull, + Energy for
abilities) with per-type modifiers, range falloff, regen/repair timers, and
heat-limited weapons. A re-impl server applies damage through this pipeline; the
numeric tuning lives in the pak.

## Aim assist (E2)

A distance-scaled **aim-assist** aids targeting (gamepad/VR): `AimAssistMinDistance`/
`AimAssistMaxDistance` (the band where assist applies) and `AimAssistAngleByDistance`
(assist strength/angle scales with target range), plus `AimAdjust`/`AimOffset`.
This is a client-side aiming aid; the server stays authoritative on hit
resolution (`ServerNumHits`/`ClientNumHits` reconciliation). A re-impl keeps it
client-local — it affects feel, not server-side fairness.

## Re-implementation / preservation relevance
- The **entire combat resolution runs on the dedicated server binary** (fire
  gating, hit/`NumHits` reconciliation, multi-channel damage, hit-point/critical
  destruction, shield/energy regen, radial damage). A preservation **server**
  re-uses this shipped logic; a re-implemented **backend** needs none of it — it
  only ingests the resulting match-result/scoring report (`networking/13-*`,
  `11-*`).
- The **client** runs prediction + all FX/HUD (crosshairs, lock brackets,
  missile-warning, damage FX) locally as shipped. Only the server-side
  hit/damage authority matters for match integrity (`networking/15-*`).
- This doc enumerates the **combat interface** (weapon families, lock/homing
  state machines, damage channels, scoring hooks) a clean-room server must
  reproduce to make matches behave correctly.

## Open questions
- Exact field layout per `VkWeaponData` subtype and replicated combat properties
  (needs class-layout analysis; `recover_object.py` confirms the anchors xref
  but does not emit a linear field list for these symbols).
- Precise hit-resolution model: does the server raycast/sweep authoritatively, or
  validate client-reported hits within tolerance (the `ServerNumHits`/`ClientNumHits`
  split suggests reconciliation)?
- All numeric balance (damage amounts, rates, radii, lock/regen times,
  spread/heat curves) — content in the `.pak`, out of scope (asset RE).
- Whether `EVkTargetZone` (`Zone_A/B/C`) implies directional/locational damage
  multipliers, or is purely a HUD/targeting region classifier.
