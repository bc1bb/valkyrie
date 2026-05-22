---
doc: gameplay-effects
title: Effects (VFX Driver) & Animation
summary: The code layer that lets gameplay trigger/queue visual+audio effects — the VkEffectManager actor/component + a command-list action enum, the UVkEffect* spawn/instancing family and effect sub-systems, and the skeletal-animation driver classes (AnimInstances, animation components). DRIVER code only; particle/mesh/anim assets live in the pak and are out of scope.
keywords: [effects, vfx, effect manager, command list, effect subsystem, instanced effect, temporary effects, animation, anim instance, animation component, montage, explosion, activatable effect, crosshair anim, spline]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E3]
---

# Effects (VFX Driver) & Animation

This document covers the **code architecture** that drives in-world effects and
skeletal animation in `VkGame` — i.e. *how gameplay code asks for an effect to
play and how that request is managed/instanced*, plus the animation-driver
classes that pose skeletal meshes. It is layered on the rendering/audio
middleware in `engine/06-rendering-audio-vr.md` (D3D11/12 forward shading,
Wwise/`AkAudio`, Oculus spatializer) and the foveated/multi-res path in
`engine/03-input-peripherals.md` / NVIDIA Multi-Res notes.

## Scope note — driver, not assets (clean-room)

What is documented here are **factual interface elements** — class, component,
sub-system and enum *names* recovered from embedded symbol/string evidence. The
actual visual content these classes play back — particle systems, emitters,
materials, meshes, animation sequences/montages, curves, timing and art tuning
values — are **shipped in the `.pak`** and are deliberately **out of scope**.
Where a `UVkEffect*`/`UVk*AnimInstance` class clearly *wraps* such an asset, only
the wrapper class is named; the asset it references is not reproduced.

Evidence keys (same convention as `gameplay/02-combat.md`):
**E1** = embedded source paths (`analysis/raw/srcpaths.txt`);
**E2** = extracted symbol/field strings (`analysis/raw/strings_all.txt`);
**E3** = `analysis/scripts/recover_object.py`. Note: for the effect/animation
classes below, `recover_object.py` confirms the symbol **anchors xref the
binary** but returns **0 structured fields** (the property/vtable layout is not
linearly recoverable for these types). Class names therefore rest on E1/E2; no
field-level layout is asserted from E3.

Confirmed source files (E1), under `VkGame/Source/VkGame/Private/`:

| File | Folder |
|---|---|
| `Effects/VkInstancedEffect.cpp` | Effects |
| `Effects/VkTemporaryEffectsSubSystem.cpp` | Effects |
| `Effects/VkExplosion.cpp` | Effects (see `02-combat`) |
| `Effects/VkExplosionComponent.cpp` | Effects (see `02-combat`) |
| `Effects/VkPostExplosionAnimater.cpp` [sic] | Effects (see `02-combat`) |
| `Effects/VkShieldInstComponent.cpp` | Effects (see `02-combat` / `01-*`) |
| `Effects/VkVehicleShield.cpp` | Effects (see `02-combat` / `01-*`) |
| `Animation/VkSpiderBotAnimationComponent.cpp` | Animation |

## 1. Effect-management layer

The central piece is an **effect manager** that gameplay uses to drive effects,
exposed both as a world actor and as an attachable component, and fed by a
**command-list** of typed actions.

### Manager actor / component (E2)

| Symbol | Likely role |
|---|---|
| `AVkEffectManager` | World actor that owns/serves effect requests. |
| `UVkEffectManagerComponent` | Per-actor component façade onto the manager (lets an owning actor enqueue effect work). |
| `AVkEffectsManager` | Plural-named manager actor (sibling/aggregate; distinct symbol from `AVkEffectManager`). |
| `FVkEffectManagerResource` | Plain struct — a resource handle/record the manager tracks (e.g. an allocated effect instance/slot). |

> The presence of *both* `AVkEffectManager` (singular) and `AVkEffectsManager`
> (plural) as distinct symbols is recorded as observed; their division of labour
> is not asserted (open question).

### Command list (E2)

Effect work is expressed as **command-list items** carrying an **action** enum:

| Symbol | Kind | Notes |
|---|---|---|
| `VkEffectManagerCommandListItem` | struct | One entry in the manager's command list — a queued effect operation. |
| `FVkEffectManagerCommandListAction` | enum | The action/opcode of a command-list item. |

Enumerators of `FVkEffectManagerCommandListAction` recovered from strings (E2):

| Enumerator | Meaning (interface-level) |
|---|---|
| `Invalid` | Sentinel / unset action. |
| `Initialize` | Bring an effect (slot/resource) up. |
| `Deinitialize` | Tear an effect down. |
| `FVkEffectManagerCommandListAction_MAX` | UE-generated count sentinel (confirms this is a `UENUM`). |

**Interpretation (architecture).** This is a classic *deferred-command* design:
gameplay does not poke renderer/audio objects directly; it appends
`VkEffectManagerCommandListItem`s (each tagged with an
`FVkEffectManagerCommandListAction`) which `AVkEffectManager` /
`UVkEffectManagerComponent` drains, allocating/freeing `FVkEffectManagerResource`
records. The `Initialize`/`Deinitialize` pair is the lifecycle the manager
applies to each managed effect; the list lets many requests be batched and
applied at a controlled point in the frame (relevant to the stereo/multi-res
render path, `engine/06-*`/`engine/03-*`). Only `Invalid`/`Initialize`/
`Deinitialize`(+`_MAX`) are evidenced — any further opcodes are an open question.

## 2. Effect spawn & instancing family (`UVkEffect*`, E2)

A broad family of `UVkEffect*` classes provides the concrete, in-world effect
primitives the manager (and gameplay) instantiate. These are the **renderable
effect wrappers** (the asset each wraps is out of scope, per scope note).

### Core / roots

| Symbol | Likely role |
|---|---|
| `UVkEffect` | Base effect class. |
| `UVkEffectRootComponent` | Root scene component an effect attaches under. |
| `UVkEffectMesh` | Mesh-backed effect primitive. |
| `AVkEffectActor` | Standalone effect actor (effect placed/owned in the world). |
| `AVkRuntimeEffectActor` | Runtime-spawned effect actor variant. |

### Instancing / sizing (batched effect rendering)

| Symbol | Likely role |
|---|---|
| `UVkInstancedEffect` | Instanced effect (E1: `VkInstancedEffect.cpp`) — many copies via instancing. |
| `UVkEffectInstancedStaticMeshComponent` | ISM-component specialization for effect meshes. |
| `UVkEffectFixedInstancedStaticMeshComponent` | Fixed/preallocated-count instanced-mesh variant. |
| `UVkEffectFixedSize` / `UVkEffectDynamicSize` | Fixed- vs dynamic-sized effect (pooling vs growth). |
| `UVkEffectFixedInstanceSubSystem` | Sub-system managing the fixed-instance pool. |

### Effect sub-systems

| Symbol | Likely role |
|---|---|
| `UVkEffectSubSystem` | Aggregate effect sub-system. |
| `UVkTemporaryEffectsSubSystem` | Manages short-lived/one-shot effects (E1: `VkTemporaryEffectsSubSystem.cpp`). |
| `UVkEffectLightSubSystem` | Manages effect-driven dynamic lights. |

> String fragments seen near the temporary-effects path (E2) —
> `SpawnedTemporaryEffects`, `UltimateTemporaryEffects1P` / `…3P` — indicate the
> temporary-effects sub-system tracks spawned instances and distinguishes
> **first-person (cockpit, `1P`) vs third-person (`3P`)** variants, consistent
> with the VR cockpit/exterior split (`gameplay/05-vr-ui.md`). The specific
> effects named are content and are not enumerated here.

### Domain-specific effect wrappers (named for completeness; behaviour owned elsewhere)

These appear in the same `UVkEffect*`/`*Effect` namespace but their *gameplay*
meaning is documented in the cross-referenced docs — listed here only so the
effect-class inventory is complete:

| Symbol | Owning doc |
|---|---|
| `UVkActivatableEffect` (+ `EVkActivatableEffectState`, enum `…_MAX`) | `gameplay/03-abilities.md` — do **not** re-document the activatable-effect state machine here. |
| `UVkSimpleEffect`, `UVkCockpitEffect` | generic/cockpit one-shots (cf. `05-vr-ui`). |
| `UVkSenseOfSpeedEffect`, `UVkMWDBubbleEffect`, `UVkNpcBoosterEffect` | speed/boost feedback (cf. `01-player-ship-control`). |
| `UVkOrientationLockedEffect` | orientation-locked overlay effect (VR). |
| `UVkProjectileLightEffect`, `UVkWeaponMuzzles_VkEffect`, `UVkEffectTurret` | weapon/projectile FX (cf. `02-combat`). |
| `UVkCarrierShieldDrainEffect` | carrier/shield-drain FX (cf. `02-combat`, mode mechanics `04-*`). |

## 3. Explosion & shield effects → see combat

Explosion and shield *visual* drivers physically live in this `Effects/` folder
(E1) but their behaviour is documented with combat:

- `AVkExplosion` / `VkExplosion`, `UVkExplosionComponent`, and
  **`UVkPostExplosionAnimater`** [sic — the engine spelling] — the
  post-explosion "animater" that plays out an explosion's aftermath VFX. See
  `gameplay/02-combat.md` (explosions / radial damage).
- `UVkShieldInstComponent`, `UVkVehicleShield` and the shield-effect param
  structs (`VkShieldActiveEffect`, `VkShieldEffectOptions`,
  `VkShieldEffectMaterialOptions`, `VkShieldStateChangeParams`, `VkShieldBreak*`)
  — regenerating-shield visual layer. See `gameplay/02-combat.md` and
  `gameplay/01-player-ship-control.md`. **Not repeated here.**

## 4. Animation driver classes

The animation layer is standard UE4 skeletal animation: per-skeleton
**`AnimInstance`** subclasses (the AnimBP "brain") plus bespoke **animation
components** that drive transforms procedurally. Asset-side AnimBP graphs,
sequences and montages are in the pak (out of scope).

### AnimInstances (E2)

| Symbol | Drives |
|---|---|
| `UVkWeaponAnimInstance` | Weapon skeletal animation (recoil/cycle poses). |
| `UVkSpiderBotAnimInstance` | "Spider bot" enemy/drone rig. |
| `UVkHeavyDroneAnimInstance` | Heavy-drone rig. |

(Spider-bot/heavy-drone are AI units — cf. `engine/07-ai-bots.md`.)

### Animation components (E1/E2)

| Symbol | Role |
|---|---|
| `UVkSpiderBotAnimationComponent` | Spider-bot animation component (E1: `VkSpiderBotAnimationComponent.cpp`) — by far the most-referenced anim symbol (E2), i.e. the main bespoke procedural-animation driver. |
| `UVkCrosshairAnimComponent` | Animates the crosshair (cf. crosshair cluster `AVkCrosshair`, `UVkCrosshairMesh`, `UVkCrosshairRippleComponent`; HUD/VR-UI, `gameplay/05-vr-ui.md`). |
| `UVkAnimSplineComponent` | Spline-driven animation (pose/move along a spline; cf. `UVkSplineComponent`, `AVkChallengeSpline`, `AVkHoloGateSplineActor`). |
| `AVkAIAnimScriptedPath` | Actor playing a scripted, animation-driven path (cf. AI, `engine/07-*`). |

### Front-end / UI animation (E2)

| Symbol | Role |
|---|---|
| `UVkFrontEndAnimationStyleAsset` | Data-asset selecting front-end (menu) animation *style* — a style/config wrapper; the animations themselves are assets. |
| `AVkVrUiHSOG_Rewards_AnimatingBar` (+ `_Rank`, `_Loot`) | VR-UI reward-screen animating bar actors (cf. `gameplay/05-vr-ui.md`, brackets/rewards `gameplay/07-*`). |

> **Montages:** no `UVkAnimMontage`/`*Montage` *class* symbol was found in
> evidence (the only `Notify`-adjacent symbol is the unrelated cockpit delegate
> `VkCockpitNotifyMoveStateChange__DelegateSignature`). Montage playback, if
> used, is therefore via **stock UE `UAnimMontage`** assets driven from the
> AnimInstances above rather than a Vk-subclassed montage type. Recorded as a
> finding, not asserted as design.

## Relevance to the preservation effort

- **Server-authoritative split.** Gameplay (`02-combat`, `03-abilities`) is
  server-resolved; the **client** runs this effect/animation layer to *present*
  results. A faithful reimpl can stub `AVkEffectManager` /
  `UVkEffectManagerComponent` as a queue that accepts
  `VkEffectManagerCommandListItem`s and applies
  `Initialize`/`Deinitialize` — gameplay logic does not depend on the VFX
  content, only on the trigger interface.
- **Asset independence.** Because the manager and `UVkEffect*` classes are thin
  wrappers over pak assets, the *code* contract can be reconstructed and tested
  with placeholder visuals; no copyrighted art is required to exercise the
  trigger/lifecycle paths.
- **1P/3P + VR coupling.** The temporary-effects `1P`/`3P` split and
  `UVkOrientationLockedEffect`/`UVkCockpitEffect` show effects are
  view-context-aware — important when reasoning about the stereo/foveated render
  path (`engine/03-*`, `engine/06-*`).

## Open questions

- Division of responsibility between `AVkEffectManager` and `AVkEffectsManager`
  (singular vs plural) — separate systems, or wrapper/aggregate?
- Full enumerator set of `FVkEffectManagerCommandListAction` (only
  `Invalid`/`Initialize`/`Deinitialize`+`_MAX` evidenced — is there a `Play`/
  `Update`/`Tick`-style opcode, or is per-frame work implicit once initialized?).
- Field layout of `VkEffectManagerCommandListItem` / `FVkEffectManagerResource`
  (E3 yields no fields — what does an item carry: effect id, transform, owner,
  context?).
- Whether `UVkEffectManagerComponent` is the *sole* gateway for gameplay, or
  whether sub-systems (`UVkTemporaryEffectsSubSystem`,
  `UVkEffectLightSubSystem`) are also driven directly.
- Audio coupling: how effect triggers post Wwise/`AkAudio` events
  (`engine/06-*`) — no Vk effect↔`AkComponent` bridge symbol was found in
  evidence.
