---
doc: gameplay-frontend-flow
title: Front-End / Menu Flow
summary: The VR meta/menu UX layer — the catalogue of head-look "scene" screens (login, hangar, Quartermaster store, squads, progression, matchmaking, results) and the navigation flow between them, driven by three scene managers and tied to the EVkUIGameStateConnectionState matchmaking machine and the VGS backend resources.
keywords: [front-end, menu, hangar, scene, screen, login, eula, gender, quartermaster, store, squads, progression, upgrade tree, boosters, customisation, matchmaking, next battle, carousel, results, rewards, loot, leagues, leaderboards, navigation, hsog, scene manager, hub, proving grounds, connection state]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Front-End / Menu Flow

This is the **meta / out-of-battle UX layer**: the 3D "hangar" the player
navigates by head-look between matches, and the path login → hangar →
loadout/store/squads → matchmaking → battle → results. It documents the
**screens** and the **navigation flow**, not the framework — the head-selectable
machinery (HSOG, `AVkVrUiSceneBase`, `VkVrUiSceneManager`, the
`AVkUIGameState` bridge, `EVkUIGameStateConnectionState`) is described once in
`gameplay/05-vr-ui.md` and cross-referenced here. Each screen is a
`VkVrUiScene_*` (a scene/state of the 3D menu) composed of `AVkVrUiHSOG_*`
head-selectable object groups; all class/enum names below are interface symbols
recovered from the binary (E1/E2).

## Scene managers (the three top-level contexts)

A **scene manager** owns a stack of scenes for one phase of the front-end and
drives transitions (`OnSceneTransition_Manager` / `OnSceneTransitionFailed_Manager`,
`EVkVrUiJumpSceneType{Forward,Backward,Insert}`). Three concrete managers exist,
matching the three macro-phases of the meta layer:

| Manager | Phase / context |
|---------|-----------------|
| `AVkVrUiSceneManager_Login` | Boot/auth/onboarding context (login, EULA, gender, marketing). |
| `AVkVrUiSceneManager_HUB` | The main **hangar / "Proving Grounds" home** and everything reachable from it (loadout, store, squads, progression, matchmaking entry). Sub-anchors `…_HUB_ProvingGrounds{Title,Body,Context,Launch}`; `bIsProvingGrounds`. `ReturnToHUB` is the universal "back to hangar" action. |
| `AVkVrUiSceneManager_BattleCarousel` (`_Next`, `_RequireInstall`) | The **ship/loadout-pick carousel lobby** entered just before a match launches — the UI face of the `JoiningCarousel` connection state. `BattleCarouselTopSceneRef`. |

The hangar's home/landing menu is `VkVrUiScene_TopMenu` (`_Base`, `_BC`,
`_Wormhole` variants; `TopMenu_Open`, `MatchmakingTopMenuRef`,
`TopMenu_MustBeSquadLeader` — i.e. matchmaking launch is gated on being squad
leader). `SceneManager_*` also fields out-of-band events that interrupt any
scene: `SceneManager_SquadInvitation` / `_AcceptInvitation` / `_InviteAcceptFailed`
(incoming squad invites) and `SceneManager_ControllerReconnect*` (controller
dropout). Animated scene-to-scene transitions use `UVkVrUiSceneTransition` /
`VkHoloSceneTransition`.

## Boot cinematics (E1)

Before the front-end scenes, two cooked **`.mp4`** movies play
(`VkGame/Content/Movies/`): `Generic_Launch_SEQ` (startup/legal sting) and
`Introduction_Cinematic`. Playback is via UE4's **Media Foundation** player
(`MF.dll`/`MFPlat.DLL` delay-loaded, `binary/01-*`) — i.e. the engine startup-
movie path, not a gameplay scene. Local-only, no backend.

## Screen catalogue

Grouped by phase. "Drives" lists the backend resource(s) the screen reads or
mutates — see `networking/14-vgs-api-surface.md` for the resources and
`networking/11-progression-economy-model.md` for the economy model.

### Onboarding / auth (`SceneManager_Login`)

| Scene | Purpose | Drives (backend) |
|-------|---------|------------------|
| `VkVrUiScene_Login` | Sign-in / platform auth entry. | OAuth token (`networking/03`), `VkClientResource` bootstrap, `clients`/`signup`. |
| `VkVrUiScene_EULA` | EULA accept/decline gate. `EULA_ACCEPT`/`EULA_DECLINE`/`EULA_Quit`, `EULAVersion`, `EULAAcceptTime`. | Pilot `eula_signed` / `eula_uri`. |
| `VkVrUiScene_GenderSelect` | One-time pilot gender choice. | Pilot `gender` / `has_set_gender` / `gender_uri`. |
| `VkVrUiScene_Marketing` | Marketing / event message popup. `bMarketingMessageSeen`, `MarketingFirstSeenTime`. | Local flag; content from backend. |

After these the new-player experience (NPE) routes into the **Proving Grounds**
intro battle (`npe_completed` / `npe_skipped` / `npe_complete_uri`,
`NpeVO_AfterProvingGrounds`); the `Login` manager hands off to the `HUB` manager
once the pilot is authenticated and onboarded.

### Hangar home & meta (`SceneManager_HUB`)

| Scene | Purpose | Drives (backend) |
|-------|---------|------------------|
| `VkVrUiScene_TopMenu` | Hangar landing menu — hub for matchmaking, loadout, store, squads, progression, settings. | — (navigation root) |
| `VkVrUiScene_HeroHanger` | Hero-ship hangar view (browse/select ships). | `hero_ships`, `hero_ship_stats`. |
| `VkVrUiScene_HeroLoadouts` / `VkVrUiScene_ShipSelectBase` | Ship + loadout selection (Fire/Ability/Ultimate slots). | Pilot loadout (`gameplay/06`). |
| `VkVrUiScene_HeroUpgradeTree` | Per-ship upgrade tech-tree (nodes via `AVkVrUiHSOG_HeroUpgradeNode_{Base,StartNode,EndNode}`). | `hero_upgrades_uri`, `upgrades`. |
| `VkVrUiScene_HeroXPTransfer` | Transfer/spend hero XP. | `hero_xp_transfer_uri`, `spent_xp`. |
| `VkVrUiScene_ExteriorCustomisation` | Ship cosmetics (cockpit / paint-job / decal). | `hero_cosmetics_uri`, `applied_hero_cosmetics_uri`, `heroCosmeticType.*`. |
| `VkVrUiScene_PilotCustomisation_Base` | Pilot avatar cosmetics (suit / helmet). | `cosmetics_uri`, `applied_pilot_cosmetics_uri`, `pilotCosmeticType.*`. |
| `VkVrUiScene_Boosters` | XP/reputation booster activation. | `global_booster`, `booster_name`/`multiplier`. |
| `VkVrUiScene_Quartermaster` | The **store** front (the Quartermaster vendor); offers/products. `GetQuartermasterPromptType`, `VkVrUi_Quartermaster_Prompt`. | `stores/7/offers/`, `sales/`, `products`, `items` (vendor MIME `…VgsSale-v1+json`). |
| `VkVrUiScene_Shop` / `VkVrUiScene_GoldPacks` / `VkVrUiScene_LootPurchase` | Sub-store screens — generic shop, premium-currency ("gold") packs, direct loot-capsule purchase. `GoldPackCostDefault`, `k_EResultShoppingCartNotFound`. | `balance`, store offers, `lootCapsule.*`. |
| `VkVrUiScene_Leagues` / `VkVrUiScene_Leaderboards` | Competitive standing — league position and leaderboards. | `leagues`, `league`/`league_score`/`league_position`; `hero_leaderboard`, `wormhole_leaderboard`, `hero_survival_leaderboard`. |
| `VkVrUiScene_Rewards_Main` (`_Gallery`, `_Ships`, `_SpoilsOfWar`) | Rewards/collection gallery (owned ships, spoils-of-war). | `hero_rewards_uri`, `collectibles_uri`. |
| `VkVrUiScene_Settings` (+ `_Audio`/`_Graphics`/`_Controller`/`_ControllerConfigs`/`_Resolution`/`_About`/`_PSGameplay`) | Options menus. (`…GamepadSetup`/`JoystickSelector`/`KeyBinding` are retired earlier variants.) | Local settings (`settings_uri`). |

Daily/recurring meta: `AVkVrUiHSOG_DailyChallenge` (+ `_FrontInfo`) surfaces
`challenges` capsules (`challenge_capsules`).

### Social / squads (`SceneManager_HUB`)

| Scene | Purpose | Drives (backend) |
|-------|---------|------------------|
| `VkVrUiScene_Squad` | Squad/party management — view members, invite, kick, leave. Sub-scenes `_Kick`/`_KickConfirmation`/`_Leave`/`_LeaveConfirmation`. `CreateSquad*`, `AcceptSquadInvite`/`DeclineSquadInvite`, `MaxPartySize`. | `squads`, `invites_uri`, `friends_uri`. |

Squad membership flips the connection state to `IdleSquadMember` (a squad member
who is idle while the **leader** drives matchmaking — hence
`TopMenu_MustBeSquadLeader`). The squad/party reservation uses the PartyBeacon
(`APartyBeaconClient`/`Host`, `EPartyReservationResult`) — see
`networking/06-matchmaking-beacons.md`; Steam/Oculus platform invites enter via
`FOnlineAsyncEventSteam(Lobby)InviteAccepted` (`networking/07`).

### Matchmaking entry & "next battle" (`SceneManager_HUB` → carousel)

| Scene / HSOG | Purpose | Drives (backend) |
|--------------|---------|------------------|
| `AVkVrUiHSOG_NextBattlePreview` | The "next battle" panel on the hangar menu — shows search/queue status and the upcoming match. State labels mirror the connection machine: `NextBattlePreview_Idle` → `_Searching` / `_Finding` → `_WaitingForBattle` → `_WaitingForRunningBattle`; `TimeToNextBattle`. | `sessionrequests` → `sessions` → `battles`. |
| `AVkVrUiHSOG_JoinSession` (`VkVrUiHSOG_JoinSession`) | Drives the actual session join from the menu. `HSOGJoinSession_Launch`, `_WaitingForLaunch`, `_LeaveMatchmaking`, `_LeaveSession`; `OnJoinSessionComplete` (via `UJoinSessionCallbackProxy`). | `VkBattleServerResource` (`battle_uri`, reservation). |
| `AVkVrUiHSOG_SessionSwitch` | Switch between/return to an active session. | `hero_active_battles_uri`. |
| `VkVrUiScene_MatchSetup` / `AVkVrUiHSOG_MatchSetup`, `AVkVrUiHSOG_GameModeDescription` | Mode/map selection + mode description before queuing. | `game_mode_unique_name`, `map_unique_name`. |
| `VkVrUiScene_CustomMatch_Entry` / `_Lobby` (`_Host`/`_Guest`) | Custom/private match lobby. HSOGs: `_LobbyHost_MatchSettings`, `_Lobby_AddPlayer`, `_Lobby_SpectatorList`, `_Lobby_WaitingScreen`; `VkVrUiScene_ConfirmStartMatch`. | `sessions` with `custom_settings` / `game_mode_settings` (`disable_shields`, `friendly_fire`, `num_ai_per_team`, …); `is_private`, `host_pilot_ids`, `password`. |

Custom match is the `CustomSession` connection-state branch; standard
matchmaking flows through `FindingSession`/`FoundSession`/`BattleFound`.

### Solo / PvE & minigames

| Scene | Purpose | Drives (backend) |
|-------|---------|------------------|
| `VkVrUiScene_LocalBattles` (`_FirstTime`/`_PVE`/`_Survival`/`_Training`) | Single-player / co-op battle picker. | `training_uri`, local battle config. |
| `VkVrUiScene_PVE_ModeDisplay` (`_NPE`/`_Recall`/`_Scout`/`_Survival`/`_Training`/`_Top`), `VkVrUiScene_PVE_Map_{Base,Scout,Survival}` | PvE mode/map briefing screens (Recall, Scout, Survival, Training, NPE). | `recall_uri`, `hero_survival`. |
| `VkVrUiScene_ShipHunt` | The "Ship Hunt" minigame. | — (local). |
| `AVkVrUiHSOG_Wormhole*` (`_Closed`/`_Opening`/`_Wormhole`, `…ClosedTitle`), `VkVrUiScene_TopMenu_Wormhole` | Wormhole event mode entry/state. | `wormhole_leaderboard`. |
| `AVkVrUiHSOG_SurvivalLeaderboard` | Survival co-op leaderboard. | `hero_survival_leaderboard`. |

### Post-battle results & rewards (`SceneManager_HUB` on return)

| Scene / HSOG | Purpose | Drives (backend) |
|--------------|---------|------------------|
| `VkVrUiScene_Results` / `AVkVrUiHSOG_ResultsScreen` (`_TeamScore`, `_LimitedRespawn`) | End-of-match scoreboard. `LastBattleResultsScreen`, `Left/RightResultsScreen`. | `battle_stats`/`player_stats`/`team_stats`, `Score_*`/`Bonus_*` (`networking/14`). |
| `VkVrUiScene_SurvivalResults` | Survival-mode results. | survival stats (`wave_reached`, …). |
| `AVkVrUiHSOG_Rewards_AnimatingBar` (`_Loot`, `_Rank`), `_LocationBar`, `_UpgradeOverviewBar` | Animated XP/rank/loot progress bars. `Rewards_MatchScore`/`_WinBonus`/`_CompletionBonus`/`_FirstWinScore`; `AnimatingBar_Loot_LootAwarded`. | `old_rank`/`new_rank`, `xp`, `first_win`, `capsules_earned`. |
| `VkVrUiScene_LootOpening` (+ `_RewardAlreadyReceived`, `_RewardFailure_{Title,Context}`), `VkVrUiScene_Loot` / `VkVrUiScene_LootPurchase`, `AVkVrUiHSOG_LootMenu` | Loot-capsule opening "reveal" theatre. Reward-type variants: `…BasicTraining`/`…CombatArena`/`…ProvingGrounds`. | `lootCapsule.{bronze,silver,gold}`, `capsule_awarded`, `loot_score_capsules`. |

The clone-vat **end-of-match theatre** (`AVkCloneVatUI`,
`EVkCloneVatScreenType{EndOfMatch,KillCam}`) is the in-world results staging that
precedes the return to the hangar results scene — documented in
`gameplay/05-vr-ui.md`.

### Player-info / shared HSOG building blocks

Reused across many scenes (data-binding object groups, not standalone screens):
`AVkVrUiHSOG_PlayerInfo`, `_PlayerCurrency` (shows `balance`), `_PlayerCharacter`,
`_PilotData`/`_PilotLevelData`/`_PilotGameModeData`/`_PilotMesh`, `_LoadoutData`,
`_ShipInfo`, `_PlayerRotatable`/`_ProgressionRotatable` (turntable previews;
ship preview via `UVkVrUiVehicleMeshComponent`), `VkVrUiScene_PlayerDetail` /
`VkVrUiScene_PlayerPerformanceSelection`. Generic prompts:
`AVkVrUiHSOG_SettingsOption`, `AVkVrUiHSOG_ControlPrompt`, `AVkVrUiHSOG_CAT_Popup`,
`AVkVrUiHSOG_SelectionWheelPrompt` (the radial selection wheel).

## Navigation flow

```
[SceneManager_Login]                         [SceneManager_HUB]                              [BattleCarousel]
 Login ─▶ EULA ─▶ GenderSelect ─▶ Marketing ─▶ TopMenu (hangar home) ───────────────┐
   │  (auth, eula_signed, has_set_gender)        │   ▲                               │
   │                                             │   │ ReturnToHUB                   │
   └─(NPE not done)─▶ Proving Grounds intro ─────┘   │                               │
                                                     ├─ HeroHanger / HeroLoadouts / UpgradeTree / Customisation  (loadout & build)
                                                     ├─ Quartermaster / Shop / GoldPacks / LootPurchase          (store)
                                                     ├─ Squad (invite / kick / leave)                            (party)
                                                     ├─ Boosters / Rewards / Leagues / Leaderboards / DailyChallenge (meta)
                                                     ├─ LocalBattles / PVE_ModeDisplay / ShipHunt / Wormhole     (solo/PvE)
                                                     │
                                                     └─ MatchSetup ─▶ NextBattlePreview ─▶ JoinSession ──────────▶ Battle Carousel
                                                                       (queue status)        (reserve+join)         (ship pick) ─▶ map
                                                                                                                                    │
                              ┌─────────────────────────────────────────────────────────────────────────────────── in-match ◀────┘
                              ▼
                        Results ─▶ Rewards (rank/loot bars) ─▶ LootOpening ─▶ ReturnToHUB (TopMenu)
```

- **Onboarding gate (one-time):** Login → EULA → GenderSelect → Marketing →
  (NPE / Proving Grounds). Returning players with `eula_signed`, `has_set_gender`,
  `npe_completed` skip straight to the hangar.
- **Hangar hub:** `TopMenu` is the spoke centre; every meta screen returns to it
  via `ReturnToHUB`. Loadout/store/squad/progression are all reachable here and
  none requires leaving the hangar.
- **Into a match:** `MatchSetup` (mode/map) → `NextBattlePreview` (queue;
  `Idle→Searching→WaitingForBattle→WaitingForRunningBattle`) →
  `JoinSession` (reserve + join) → **Battle Carousel** (ship/loadout pick) →
  map transition. Custom matches fork through `CustomMatch_Lobby` instead.
- **Out of a match:** the client returns to the `HUB` manager and shows
  `Results` → `Rewards` (animating rank/loot bars) → optional `LootOpening`,
  then back to `TopMenu`.
- **Quit / exit:** `VkVrUiScene_QuitConfirm` resolves to
  `EVkVrUiQuitType{RETURN_TO_MAIN_MENU, FORCE_RETURN_TO_MAIN_MENU, RELOGIN,
  QUIT_GAME, FORCE_QUIT}` (`RELOGIN` re-enters the `Login` manager).

## Tie-in to the connection-state machine

The front-end's match-related scenes are the visible face of
`EVkUIGameStateConnectionState` (`gameplay/05-vr-ui.md`), which itself maps onto
the lower-level `eConnectionState` lifecycle (`networking/09-session-lifecycle-and-roadmap.md`).
The screen ↔ state correspondence:

| Connection state | Front-end screen(s) |
|------------------|---------------------|
| `Idle` | `TopMenu` (hangar home), `NextBattlePreview_Idle`. |
| `IdleSquadMember` | `Squad` / `TopMenu` as a non-leader party member. |
| `FindingSession` | `NextBattlePreview_Finding/_Searching`, `JoinSession`. |
| `FoundSession` / `BattleFound` | `NextBattlePreview_WaitingForBattle`. |
| `ConnectingToServer` | `JoinSession` (`HSOGJoinSession_WaitingForLaunch`). |
| `WaitingForRunningBattle` | `NextBattlePreview_WaitingForRunningBattle`. |
| `JoiningCarousel` | `SceneManager_BattleCarousel` (ship/loadout pick). |
| `MapTransition` | scene fade; `AVkUIGameState::LoadServerMap` (`MapLoader`). |
| `CustomSession` | `CustomMatch_Lobby` (`_Host`/`_Guest`). |
| `ConnectionFailed` | error popups (`CustomMatchGuest_JoinSessionError*`, `SceneManager_InviteAcceptFailed`). |
| `Quitting` | `QuitConfirm` → `AVkUIGameState::OnEntered_Quitting`; then `Results`. |

`AVkUIGameState::HandleBackendDataChange` re-renders the hangar whenever backend
data (pilot, currency, inventory, league) updates, so the screens always reflect
server state; `AVkUIGameState::LeaveSession` backs out of a queued/active match.

## Backend resources the front-end drives

Summary of which VGS resources (`networking/14-vgs-api-surface.md`) the meta UI
consumes, beyond the per-screen "Drives" columns above:

- **Pilot** (`pilots`, HATEOAS `*_uri` graph): identity, gender, reputation,
  league, balance, EULA/NPE flags — the spine the whole hangar reads.
- **Stores/sales** (`stores/7/offers/`, `sales/`, `products`, `items`): the
  Quartermaster and its sub-shops.
- **Squads** (`squads`, `invites_uri`, `friends_uri`) + PartyBeacon: the social
  screens.
- **Sessions/battles** (`sessionrequests` → `sessions` → `battles` →
  `battleservers`): matchmaking entry and `NextBattlePreview`/`JoinSession`.
- **Leagues / leaderboards** (`leagues`, `hero_leaderboard`, `wormhole_leaderboard`,
  `hero_survival_leaderboard`): competitive screens.
- **Loot / rewards / challenges** (`lootCapsule.*`, `hero_rewards_uri`,
  `challenges`): the post-battle and daily screens.
- **Static data** (`staticdata`, `networking/10`): mode/map/cosmetic catalogues
  the menus enumerate.

## Re-implementation / preservation relevance

- The front-end is **client/engine-local** rendering (`gameplay/05-vr-ui.md`): a
  preservation client runs all of these scenes as shipped. No screen needs bespoke
  server code beyond the data it reads.
- What a private backend must satisfy is the **data** behind the screens: serve a
  `pilots` object (with the `*_uri` link graph), `staticdata`, and stub
  stores/squads/leagues/leaderboards/loot so the hangar populates without errors —
  see the MVP order in `networking/09` (P0 boot/auth, P3 meta can be stubbed).
- To let the player **leave the hangar into a match**, the matchmaking chain
  (`networking/06`) and battle-server launch (`networking/05`) must drive
  `EVkUIGameStateConnectionState` through `FindingSession → … → JoiningCarousel →
  MapTransition`; otherwise `NextBattlePreview`/`JoinSession` stall in their
  waiting states.
- Onboarding gates are **server-flagged**: `eula_signed` / `has_set_gender` /
  `npe_completed` must be returned (or accepted via `eula_uri` / `gender_uri` /
  `npe_complete_uri`) or the client loops the EULA/GenderSelect/NPE screens.

## Open questions

- The exact scene **stack/transition graph** within each manager (which scene
  pushes which, and the `EVkVrUiJumpSceneType` Insert cases) — only the screen set
  and high-level routing are recoverable from strings; the precise wiring is in
  `VkVrUiSceneManager*`/`AVkUIGameState` logic (disassembly, `networking/13`).
- Whether `NextBattlePreview` polls REST (`sessionrequests`) on a timer or is
  pushed via the backend (`heartbeat_uri` / notifications) to advance its state —
  affects how a re-impl signals "battle ready" (`TimeToNextBattle`).
- Which scenes are reachable on each platform/build (PS-specific
  `…Settings_PSGameplay`, `EULA_PSNId_Relogin`; `_BC` = "Combat Arena"? vs
  Wormhole event variants of `TopMenu`) — confirm against build flags.
- The store taxonomy detail (offer/product/cart structure behind
  `Quartermaster`/`GoldPacks`/`LootPurchase`; `k_EResultShoppingCartNotFound`) —
  needs a captured `stores/.../offers` response (E4).
