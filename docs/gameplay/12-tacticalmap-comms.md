---
doc: gameplay-tacticalmap-comms
title: Tactical Map & Communications
summary: The situational-awareness tactical map (clone-vat screen), the networked quick-chat/comm-wheel + VO speaker system, and team call-ins (deployable EMP/OverShield/RepairBots support, server-requested).
keywords: [tactical map, minimap, situational, quick chat, comms wheel, voice clip, VO, speaker, call-in, reinforcement, deployable, ping, EMP, overshield, repair bots, tier, networked, RPC]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Tactical Map & Communications

Three loosely-related systems for **team coordination & situational awareness**
sit beside the in-flight HUD. None of them is the in-cockpit radar (that, plus
**smart-pings**, lives in `gameplay/05-vr-ui.md` — cross-ref'd, not repeated):

1. **Tactical map** — a large "screen"-style map of the whole battle, shown
   from the **clone-vat** (the respawn/staging pod), not the cockpit.
2. **Quick-chat / comm-wheel** — a radial menu of canned team messages, **state-
   replicated to the server** and echoed to teammates as text-feed entries, VO
   voice-clips, and over-target bracket icons.
3. **Call-ins** — team-wide deployable combat support (EMP / OverShield / Repair
   Bots), **requested via a server RPC**, gated by a per-team tier.

Evidence keys per repo convention: **E1** = client ASCII string table
(`analysis/raw/strings_all.txt`), **E2** = embedded build source paths
(`analysis/raw/srcpaths.txt`). Member layouts not recoverable from the string
table (the `recover_object.py` JSON-field heuristic does not apply to
reflection-populated USTRUCTs) are flagged as open questions.

Source modules (E2):

- `Private/UI/TacticalMap/VkCloneVatPilotsManager.cpp`,
  `…/VkCloneVatShipManager.cpp` (the `UI/TacticalMap/` folder)
- `Private/QuickChat/VkQuickChatManager.cpp`, `…/VkQuickChatMenu.cpp`
- `Private/CallIns/VkCallIn.cpp`; `Private/UI/HUD/VkDeployableHUD.cpp`

---

## 1. Tactical map (situational display)

The tactical map is `AVkTacticalMap`. It is **not** a cockpit instrument — it is
one of the screens presented in the **clone-vat**, the world-space pod the player
occupies between lives. The clone-vat's screen selector enumerates it directly:

`EVkCloneVatScreenType { NotSet, ShipSelect, TacticalMap, KillCam, EndOfMatch,
PauseScreen, Max }` (E1). So the player, while waiting in the vat, can switch the
pod's display to the tactical map, ship-select, the kill-cam, etc. The clone-vat
theatre itself (`AVkCloneVatUI`, `AVkCloneVat{Pilots,Ship}Manager`,
`AVkCloneVatWaveTimer`, `AVkCloneVatPawn`, `EVkCloneVateShipState`) is covered as
a HUD/scene cluster in `gameplay/05-vr-ui.md`; the clone-vat **respawn pool** and
its login gating are in `gameplay/04-mode-mechanics.md`. This doc owns the map.

### Map placement / transform (E1)

`AVkTacticalMap` is spawned from a blueprint asset and positioned in the pod:

| Field | Meaning |
|---|---|
| `TacticalMapBlueprint`, `TacticalMapBlueprint_Asset` | the map widget/actor class to instantiate. |
| `TacticalMapPosition`, `TacticalMapRotation`, `TacticalMapScale` | world transform of the map relative to the vat. |
| `UVkTacticalMapLaunchInfoScreenComponent` | a companion "launch info" sub-screen component shown alongside the map. |

### What the map renders — entity components (E1)

The map is populated by per-entity components, all subclasses of a base
`UVkTacticalMapComponent`. Each map blip/icon is one of these, attached to the
world entity it represents:

| Component | Represents (cross-ref) |
|---|---|
| `UVkTacticalMapComponent_Player` | a pilot ship (friendly/enemy contact). |
| `UVkTacticalMapComponent_BaseShip` | a team carrier / base ship — `AVkTeamBaseShip` (`gameplay/04-*`, carrier assault). |
| `UVkTacticalMapComponent_CapturePoint` | a control point — `AVkCapturePointActor` (`gameplay/04-*`, Control). |
| `UVkTacticalMapComponent_RelicDropLocation` | a relic drop site — `AVkRelicDropLocation` (`gameplay/04-*`, Extraction/Pursuit). |
| `UVkTacticalMapComponent_Turret` | a sentry turret (carrier-assault defences). |
| `UVkTacticalMapComponent_Geometry` | static level geometry / terrain backdrop drawn on the map. |

The set is **exactly the mode-objective entity list** in
`gameplay/04-mode-mechanics.md`, so the tactical map is a top-down projection of
the live objective/contact state — a strategic overview, distinct from the
forward-looking cockpit **radar** (`AVkRadar` / `AVkDetectionSystem`,
`gameplay/05-vr-ui.md`) and from the **orientation-circle locators** (capture
points / base ships / players, also `05-*`).

### Networked or local?

**Local render of replicated state.** No tactical-map-specific RPC appears in the
string table; the map components are driven by the same replicated actors
(players, capture points, relics, base ships, turrets) the rest of the HUD uses.
A re-implemented server needs to replicate those actors' transforms/team state —
nothing map-specific. (Some component visibility is gated by `bDisplayInCloneVat`
/ `bIsSpectatingCloneVat`, i.e. shown only on the vat screen.)

---

## 2. Quick-chat / comm-wheel (networked)

A radial **comm wheel** of preset team messages. Driver classes (E1/E2):

| Class | Role |
|---|---|
| `AVkQuickChatManager` | owns send/receive logic; `SendMessage()` (needs a local PlayerController), routes the outgoing message and the most-recent inbound request. |
| `AVkQuickChatMenu` | the radial wheel UI; segment selection + open/closed state. |
| `AVkQuickChatTextFeed` | scrolling text log of received messages (`OnMessageListUpdated`); rendered by `QuickChatFeedWidget` / `QuickChatFeed2DScrollBox` / `QuickChatScrollBox`. |
| `AVkVoiceClipUI` | the spoken VO + speaker-portrait overlay that plays for a message (below). |

### Wheel geometry & state (E1)

`EVkQuickChatMenuSegment { None, Top, TopRight, Right, BottomRight, Bottom,
BottomLeft, Left, TopLeft }` — an **8-direction** radial selection (plus center
`None`). Backed by `VkQuickChatMenuSegmentData`.

`EVkQuickChatMenuState { Closed, Open, LockedOut }` — `LockedOut` is a
cooldown/disable state (rate-limits spam). Settings: `bQuickChatEnabled`,
`bQuickChatAudioEnabled` (toggle the spoken VO), `QuickChatBracketDisplayTime`
(how long a request icon hovers over the requester's bracket).

Wheel input (VR + mouse), from the input-context enum (E1, see
`engine/03-input-peripherals.md`):
`EVR_QuickChatMenu`, axes `EVR_QuickChatSelectX/Y`, mouse variants
`EVR_MouseQuickChatSelectX/Y`.

### Message vocabulary (E1)

`EVkQuickChatMessage { None, Attack, Defend, AssistMe, GroupUp, OnMyWay, HealMe,
Thanks, GoodGame, GoodKill, ObjectiveA, ObjectiveB, ObjectiveC }` — combat
orders, social acknowledgements, and per-objective callouts (A/B/C correspond to
the three capture/objective markers in `gameplay/04-*`).

`EVkQuickChatMessageModifier { None, Attack, Defend }` — an optional intent
qualifier layered on a message (e.g. "Attack" vs "Defend" flavour of a target
callout).

`EVkQuickChatTeamMember { Default, Member1 … Member8 }` — lets a message be
**addressed to a specific teammate** (slots 1–8, i.e. up to an 8-player team)
rather than the whole team.

The `Attack / Defend / AssistMe` options **overlap with `EVkSmartPingType`**
(`gameplay/05-vr-ui.md`) — quick-chat and smart-ping are sibling comms channels
sharing a vocabulary: ping = a world-space marker, quick-chat = a message/VO line.

### Networked? — YES (E1)

Quick-chat is **server-relayed**, exactly like smart-pings:

| RPC / struct | Direction |
|---|---|
| `ServerSendQuickChatMessage` (+ `ServerSendQuickChatMessage_Validate`) | client → server, with the standard UE4 `_Validate` anti-cheat gate. |
| `VkQuickChatReplicatedMessageData` (reflected as `tVkQuickChatReplicatedMessageData`) | the replicated payload (sender, message id, modifier, target member). |
| `VkQuickChatMessageData` | the per-message definition/config record. |
| `MostRecentQuickChatRequest` | last inbound request the manager surfaces to UI. |

This is a **new entry for the RPC surface in `networking/08-gameplay-replication.md`**
(which currently lists only smart-ping + voice-mute on the comms side). A
re-implemented server must accept `ServerSendQuickChatMessage`, run validation,
and replicate `VkQuickChatReplicatedMessageData` to the team — directly analogous
to the smart-ping relay path (`05-*` / `08-*`).

### Three presentation channels for a received message

1. **Text feed** — `AVkQuickChatTextFeed` / `QuickChatFeedWidget`.
2. **Voice clip + portrait** — `AVkVoiceClipUI` plays a VO line with a speaker
   portrait. `EVkVoiceClipSpeaker { Anonymous, NoPortrait, Fatal, Ran, Kalloway,
   Nasker, Quartermaster, ShipyardCommander, WwiseOverride }` — the in-fiction
   commander/character voices (audio routed through Wwise, hence `WwiseOverride`;
   see `engine/06-rendering-audio-vr.md`). `EVkVoiceClipUIState { Invisible,
   FadingIn, Visible, FadingOut }`; supporting data `VkVoiceClipFlipbookData/
   Settings/Entry`, events `OnVoiceClipEnded` / `OnVOPlayChanged`
   (`VkVOPlayChangedEvent`). **Document the SYSTEM, not the audio assets** — the
   clips themselves live in the `.pak`/Wwise banks and are out of scope.
3. **Bracket request icon** — a request floats over the asker's targeting
   bracket: `VkBracketIconQuickChatRequest_AssistMe / _GroupUp / _HealMe`
   (the bracket system is `gameplay/07-brackets.md` / `05-*`).

### AI tie-in

`VkAIQuickChatOrder` — AI bots can issue/consume quick-chat orders (the same
order vocabulary drives bot behaviour). See `engine/07-ai-bots.md`.

---

## 3. Call-ins (team deployable support — networked)

**Call-ins are team-wide deployable combat-support effects** a player requests
into the match — closer to "tactical support / reinforcement" abilities than to
the personal abilities in `gameplay/03-abilities.md`. Base class `AVkCallIn`,
with three concrete shipped types (E1):

| Call-in | Effect (from naming + related systems) |
|---|---|
| `AVkCallIn_EMP` | area EMP — disables/scrambles enemy systems. Related effect plumbing: `ActiveEMPEffect`, `EMPEffectBegin/End`, `EMPEffectTemplateAlly/Enemy`, status bracket `VkBracketStatusIcon_EMP` (cross-ref combat/abilities). |
| `AVkCallIn_OverShield` | deployable shield buff (a team-support sibling of the personal `AVkAbility_OverShield` / `AVkUltimate_OverShield`; `bOverShieldActive`, `OverShieldDuration` in `gameplay/03-*`). |
| `AVkCallIn_RepairBots` | repair drones that heal allies (`UpdateParticleEffects`); related to the `RequiresHealing` bracket / `HealMe` quick-chat. |

Note these effects (EMP, OverShield) **also exist as personal abilities/
ultimates** elsewhere; the `AVkCallIn_*` variants are the **team-deployed**
versions surfaced through this subsystem. `ADEPRECATED_VkEMPRadar` is a separate,
retired EMP-radar feature — not a call-in.

### Activation, ownership, tiers (E1)

| Symbol | Meaning |
|---|---|
| `UVkCallInComponent` | the actor component that holds/activates a call-in (`CallInComponent`, `CallInClass`, `DebugCallInClass`); learns its owner via `OwningPlayerStateReceived`. |
| `CallingTeamId` | which **team** owns/triggered the call-in (effects apply per team). |
| `bCallInActive` / `OnRep_CallInActive` | replicated active flag (repnotify drives client FX on/off). |
| `ActivateCallIn` / `DeactivateCallIn` | lifecycle; assert if double-activated / deactivated-when-inactive. |
| `RequestCallIn` | local request entry point (→ server RPC, below). |
| `VkCallInTier` (reflected `tVkCallInTier`) + `VkCallInUnlockTierChangedSignature` | a **tiered unlock**: call-ins become available as a team/match reaches a tier (delegate fires on tier change). |
| `BlueprintClientCallInActivated` / `…Deactivated` | BP hooks for client-side activate/deactivate presentation. |

### World presentation: the deployable HUD (E1)

A triggered call-in manifests as a **deployable item in the world** that allies
can interact with, surfaced by `AVkDeployableHUD`
(`Private/UI/HUD/VkDeployableHUD.cpp`) via `NotifyItemDropped`,
`NotifyItemPickedUp`, `NotifyItemExpired`. `AVkDeployableHUD` is **generic** —
the same HUD serves other deployables (e.g. `AVkSpiderbotsUI` uses the same
notify hooks), so call-ins share the engine's "deployed pickup" lifecycle
(dropped → picked up / active → expired). `AVkCallInUI` is the call-in's own UI
widget; input context `EVR_CallIn` (E1) triggers a request.

### Networked? — YES (E1)

| RPC | Direction |
|---|---|
| `ServerRequestCallIn` (+ `ServerRequestCallIn_Validate`) | client → server: request to deploy a call-in (validated). |
| `OnRep_CallInActive` (prop `bCallInActive`) | server → clients: replicated active state driving FX. |

So call-in deployment is **server-authoritative**: the client asks
(`RequestCallIn` → `ServerRequestCallIn`), the server validates (tier/cooldown/
team) and flips the replicated `bCallInActive`, which repnotifies all clients to
play `BlueprintClientCallInActivated`. This is **another addition for
`networking/08-gameplay-replication.md`** (`ServerRequestCallIn` + the
`CallInActive` replicated property), alongside quick-chat above.

---

## Networked-vs-local summary

| System | Networked? | Wire surface (for `networking/08-*`) |
|---|---|---|
| Tactical map | No — local render of replicated objective/contact actors. | none map-specific. |
| Quick-chat / comm-wheel | **Yes** — server-relayed. | `ServerSendQuickChatMessage`(`_Validate`); replicate `VkQuickChatReplicatedMessageData`. |
| VO voice-clip playback | Local — triggered by the replicated quick-chat message; audio via Wwise. | none (rides quick-chat). |
| Call-ins | **Yes** — server-authoritative deploy. | `ServerRequestCallIn`(`_Validate`); replicated `bCallInActive` (`OnRep_CallInActive`). |

Both quick-chat and call-ins follow the **same `ServerXxx` + `_Validate`** pattern
as the already-documented smart-ping (`05-*`/`08-*`): the canonical Vk team-comms
RPC shape a re-implemented server must accept, validate, and re-broadcast.

---

## Relevance to re-implementation

- **Server must accept & relay** `ServerSendQuickChatMessage` and
  `ServerRequestCallIn` (both validated), replicating
  `VkQuickChatReplicatedMessageData` and the `CallInActive` state. Without these,
  team comms and support deploys are dead even though the rest of the match runs.
- **Tactical map needs no new server work** beyond replicating the objective/
  contact actors already required by `gameplay/04-*` — it is a pure client view.
- **Call-in tiering** (`VkCallInTier`) implies a server-tracked per-team
  unlock/availability gate; a re-impl must decide tier progression rules
  (likely match-time / objective-driven — confirm).
- These three are **additions to the RPC inventory in `08-*`**, which presently
  lists smart-ping + voice-mute only on the comms side.

---

## Open questions

- **Field layout of `VkQuickChatReplicatedMessageData` and `VkCallInTier`** — the
  reflected type names appear but member names were not recoverable from the
  string table (reflection-populated structs, not JSON parsers, so
  `recover_object.py` returns nothing). Confirm by disassembly: the replicated
  quick-chat payload's exact fields (sender id, `EVkQuickChatMessage`, modifier,
  `EVkQuickChatTeamMember`) and the tier struct's contents.
- **Tier-unlock rule for call-ins** — what advances `VkCallInTier` (match time,
  objective score, kills?) and whether it is per-team or per-player.
- **Whether quick-chat is broadcast via `Multicast_*` or per-client `Client*`** —
  only the `Server…` ingress is visible as a string; the egress relay shape
  (multicast vs targeted) needs disassembly (smart-ping uses `Multicast_OnPing_*`
  per `05-*`, so quick-chat likely mirrors it).
- **Call-in deploy mechanics** — whether `AVkCallIn_*` spawn as physical world
  pickups allies collect (the `AVkDeployableHUD` drop/pickup hooks suggest yes)
  or apply a team-wide effect on activation; and their cooldown/duration source.
- **VO speaker selection** — how a received `EVkQuickChatMessage` maps to a
  `EVkVoiceClipSpeaker` and clip (the mapping table is data/asset, likely in the
  `.pak`; out of scope but noted for completeness).
