---
doc: net-vgs-surface
title: VGS REST API — Full Recovered Surface
summary: Comprehensive API surface recovered from the binary's backend FString cluster — multi-tenant URL scheme, resources/paths, content types, pilot HATEOAS graph, session/battle objects, full stats vocabulary, cosmetic & game-mode taxonomies, client fingerprint, local Watchdog & battle-server registration.
keywords: [vgs, rest, api, tenant, valkyrieapi, paths, resources, pilot, session, battle, stats, cosmetics, watchdog, battleserver, fingerprint, throttle, fstring]
status: draft
updated: 2026-05-23
evidence: [E2, E3]
---

# VGS REST API — Full Recovered Surface

Recovered in one pass from the contiguous backend `FString` constant cluster in
`.rdata` (UTF-16). This is the most complete view of the API; it supersedes the
partial lists in `01-*` and enriches the schema in `schemas/vgs-rest.md`. All
items are embedded string constants (E2/E3) — field/path/type identifiers, not
captured payloads.

## Multi-tenant URL scheme (NEW)

The backend is **multi-tenant**. URLs are built from a template
`{scheme}://{tenant}.{domain}/{path}/` (format `%s://%s.%s/%s/`), with:
- Tenant token injected as `{'valkyrie.tenant':'%s'}`; config key
  `VkGame_TenantDomains`; bare `tenant` field.
- **Domains (NEW):** `valkyrieapi.com`, `evevalkyrie.com` (in addition to the
  `eveonline.com` SSO/VGS hosts in `04-*`). So production API calls likely target
  `https://<tenant>.valkyrieapi.com/<resource>/`.
- **DNS status (E4, `12-*`):** both `valkyrieapi.com` and `evevalkyrie.com` are
  now **NXDOMAIN** — the dedicated Valkyrie backend domain is gone. This means
  the *real* VGS API was on `valkyrieapi.com` (not `eveonline.com`, which only
  survives via EVE Online's wildcard). `valkyrieapi.com` is a clean redirect
  target for a private server.
- Local/dev: `http://localhost:10080/%s/` (battle-server reg) and
  `http://127.0.0.1:8080/...` (watchdog) appear for local runs.

## Content types

- `application/json` (REST bodies), `application/x-www-form-urlencoded` (OAuth).
- **Versioned vendor media type:** `application/vnd.ccp.eve.VgsSale-v1+json`
  (the store/sales resource uses CCP vendor MIME versioning).

## Auth construction (completes `03-*`/`13-*`)

Credential built as `%s:%s` (client_id:client_secret) → base64 → `Basic %s`
header (`Authorization`). Tokens: `access_token`, `refresh_token`, `expires_in`,
`bearer`/`token`/`auth`, `authenticated`, `provider`, `oculus_user_id`/
`oculus_id`/`steam_id`.

## Resources & path templates

| Resource | Path / template |
|----------|-----------------|
| Accounts | `v2.0/valkyrie/accounts/` |
| Pilots | `%spilots?pilot_id=%d`, `?pilot_id=%i`, `%spilot-lookup`, `%spilot-status?pilot_ids=%s` |
| Sessions | `sessions`, `sessions?version=%s&session_type=%s`, `sessionrequests` |
| Battles | `battles`, `battle_uri` |
| Battle servers | `battleservers` |
| Squads | `squads` |
| Clients | `clients`, `client-event`, `signup` |
| Static data | `staticdata` |
| Store/sales | `v2.0/valkyrie/stores/7/offers/`, `sales/`, `products`, `items` |
| Leagues | `%sleagues?%s` |
| Challenges | `challenges` |
| Notifications | `v1.0/valkyrie/notifications/oculus` |
| Leaderboards | `%shero_leaderboard[/%d]?%s`, `%swormhole_leaderboard[/%d]?%s`, `%shero_survival/%d`, `%shero_survival_leaderboard/%s/%s%s` |

Common query params: `region=%s`, `&pilots=`, `?team=`, `&sortby=`,
`leaderboard=`, `host_pilot_ids=%s`, `password=%s`, `?properties=`, `version=%s`,
`&%s`, `%s=%s`.

### Entry-points vs HATEOAS — a key fact for a re-impl (E2/E3)

Only a **handful of paths are hardcoded** in the client (the literals above:
`/oauth/token`, `v2.0/valkyrie/accounts/`, `%spilots?pilot_id=`, `v2.0/valkyrie/
stores/7/offers/`, `v1.0/valkyrie/notifications/oculus`, the leaderboard
templates). **Everything else is followed from `*_uri` links** the server returns
(HATEOAS, `13-*`: the pilot object alone carries ~20 `*_uri` links). Two
consequences for a private backend:
- It must serve the few **entry-point** paths at the exact literals above.
- For all other resources it **controls the paths itself** — the client uses
  whatever absolute/relative `*_uri` the server emits, so the link graph need not
  match CCP's original paths. This greatly relaxes route-fidelity requirements.

**Version coexistence:** `v1.0` and `v2.0` prefixes both appear (accounts/stores
are `v2.0`; notifications `v1.0`) — version is **per-resource**, not global. A
re-impl should honor the literal version in each entry-point path.

### HTTP verbs per resource (E3, approximate)

Recovered per resource by disassembling each request builder (tight-window read
of the verb string at the request-setup site, `disasm_func.py`/`recover_object.py
--verbs`):

| Resource | Verb | Note |
|----------|------|------|
| `accounts` | GET | Fetch account. |
| `pilots` / `pilot-status` | GET | Read pilot(s). |
| `sessions` | GET | Find/list sessions (matchmaking read). |
| `sessionrequests` | POST | Create a matchmaking request. |
| `battleservers` | POST | Register/allocate a battle server. |
| `staticdata` | GET | Fetch static-data manifest/files. |
| `leagues` | GET | Read leagues (a DELETE — "leave" — also exists). |
| `challenges` | POST | Report challenge progress/completion. |
| `client-event` | POST | Submit telemetry events. |
| (session/state updates) | PUT | `PUT` seen in session-ish builders (`13-*`). |

So: **reads = GET** (accounts/pilots/sessions/staticdata/leagues), **creates/
reports = POST** (sessionrequests/battleservers/challenges/client-event),
**updates = PUT**, plus a **DELETE** (leave league). A re-impl routes all four.

## Pilot object — HATEOAS link graph

Identity/state: `pilot_id`/`my_pilot_id`, `pilot_name`/`callsign`/`unique_name`,
`gender` (`gender.Male`/`Female`, `has_set_gender`), `reputation`/
`reputation_rank`/`reputation_score`, `league`/`league_score`/`league_position`,
`balance`, `trueskill`, `global_booster`, `last_battle_updated`, `eula_signed`,
`npe_completed`/`npe_skipped`.

Link fields (`*_uri`): `pilots_uri`, `pilot_url`, `hero_stats_uri`,
`hero_rewards_uri`, `hero_active_battles_uri`, `hero_upgrades_uri`,
`hero_cosmetics_uri`, `applied_hero_cosmetics_uri`, `hero_xp_transfer_uri`,
`friends_uri`, `cosmetics_uri`, `pilot_cosmetic_uri`, `pilot_cosmetic_variant_uri`,
`applied_pilot_cosmetics_uri`, `gender_uri`, `npe_complete_uri`, `training_uri`,
`recall_uri`, `eula_uri`, `settings_uri`, `collectibles_uri`, `invites_uri`,
`battle_uri`, `heartbeat_uri`.

## Session / lobby object

`session_id`/`session_uri`, `session_type`, `mode`/`game_mode`/`mode_name`/
`game_mode_unique_name`, `map`/`map_name`/`map_asset_name`/`map_unique_name`,
`region`/`preferred_region`/`default_region`, `status`, `is_joinable`,
`is_private`/`is_friends_only`/`visible_to_friends`, `is_showfloor`/
`showfloor_spectator`, `current_players`/`max_players`, `current_spectators`/
`max_spectators`/`is_spectator`/`max_pilots`, `owner_callsign`/`owner_platform`,
`host_pilot_id`/`host_pilot_ids`, `min_pilot_rank`/`max_pilot_rank`,
`time_to_battle_join`, `battle_id`/`battleserver_id`, `custom_settings`.

**Game-mode settings (custom-match toggles):** `disable_shields`, `no_radar`,
`friendly_fire`, `no_ultimates`, `no_mods`, `turrets_enabled`, `goals_to_win`,
`capture_speed`, `cooling_node_health`, `shield_down_time`, `num_ai_per_team`,
`clones_per_team`, `ai_difficulty`, `game_mode_settings`.

## Battle stats / scoring vocabulary

Score components: `Score_Kills`, `Score_Assists`, `Score_Repairing`,
`Score_DroneDestroyed`, `Score_ObjectiveCaptures`, `Score_CarrierNodeDamage`,
`Score_CarrierCoreDamage`, `Score_Other`; bonuses `Bonus_BattleCompleted`,
`Bonus_BattleWin`. Stat counters: `kills`/`deaths`/`assists`/`captures`/
`pvp_kills`/`drone_kills`/`carrier_kills`/`node_kills`/`emps`/`repairs`/`wins`/
`losses`/`winloss`/`kd`/`kd_ratio`/`wave`/`wave_reached`/`round_time`/
`play_seconds`/`points`/`loot_score`. Grouped as `battle_stats`/`player_stats`/
`team_stats`. Rank-up: `old_rank`/`new_rank`/`old_score`/`new_score`/`base`/
`bonus`/`boost`/`first_win`/`xp`/`spent_xp`/`level`.

## Cosmetic & loot taxonomy

- Hero (ship) cosmetics: `heroCosmeticType.cockpit`, `heroCosmeticType.paintJob`,
  `heroCosmeticType.decal`; `hero_ships`/`hero_ship_name`/`hero_ship_stats`.
- Pilot cosmetics: `pilotCosmeticType.suit`, `pilotCosmeticType.helmet`.
- Loot capsules: `lootCapsule.bronze`/`silver`/`gold`; `loot_capsule_type_name`,
  `capsules_earned`, `capsule_awarded`, `loot_score_capsules`,
  `reputation_capsules`, `challenge_capsules`.
- Implants: `implants`/`active_implants`/`implant_seconds`/`implant_type_name`/
  `implant_count`. Upgrades: `upgrades`/`upgrade_name`/`hero_upgrades_uri`.
- Collectibles, fragments, echoes, boosters (`booster_name`/`multiplier`).

## Client signup / fingerprint (sent to `clients`/`signup`)

**Request body (E3, recovered parse order via `recover_object.py cpu_brand`):**
```
{ app_guid, run_number, locale, distribution_platform,
  cpu_vendor, cpu_brand, gpu_brand, num_cores, physical_memory_gb,
  client_type, preferred_region, app_info }
```
Plus the broader fingerprint fields seen in the cluster: `client_id`,
`os_platform`/`platform`, `build_version`/`build_number`/`branch`/`branch_name`/
`changelist`, `deprecated_version`, `hmd_type`, `is_2d`, `machine_id`,
`computer_name`, `command_line`, `process_id`, `instance_name`.

A re-impl `clients`/`signup` endpoint must **accept** this body (it can ignore
most fields) and return OK + bootstrap config; gate on `build_version`/
`deprecated_version` only if you want version control (`OutdatedClient`, `09-*`).

**Response object (E3, recovered via `recover_object.py build_version`):** the
`clients` reply echoes the fingerprint and adds identity + a wallet —
`{ id, href, client_id, build_version, os_platform, computer_name, hmd_type,
is_2d, currency, balance }`. So the `/clients` response **seeds the client's
wallet** (`currency`/`balance`) and returns a self-`href` + `id`. Note version
gating is hard: *"Cannot register client (incompatible build)"* /
`ClientOutdated` / `ClosedConnectionsDueToIncompatibleVersion` — a re-impl should
report a **compatible** build or the client refuses to register/connect.

## Client-event telemetry + throttling

`client-event` endpoint with `event_name`/`event_type`/`severity`/`details`/
`parameters`/`object`/`info`. **Rate-limited:** the client backs off when
throttled ("We are being throttled! ... I can send events again in %d seconds";
"Cannot send Client Event '%s'. We are being throttled until %s"). A re-impl
should accept these events and may return throttle hints.

## Local Watchdog process (NEW)

A **separate local watchdog process** monitors the game for crashes/hangs:
- Game registers: `http://127.0.0.1:8080/register/%i` ("Registered with Watchdog
  process as PID: %i.").
- Liveness ping: `http://127.0.0.1:8080/alive/%i`; failure → "Watchdog process
  failed to respond." Distinct from the backend `heartbeat_uri`/
  `next_heartbeat_seconds` (that's the backend session keepalive, `06-*`).

## Battle-server local registration (NEW)

The dedicated battle server registers locally via `http://localhost:10080/%s/`
and exposes `battleservers` fields: `public_ip`, `port`, `instance_name`,
`process_id`, `command_line`, `host_pilot_id`, `map_unique_name`,
`game_mode_unique_name`, `running`. Ties to the launch contract (`05-*`): an
orchestrator launches the server, which then registers itself.

## Re-implementation impact

This is enough to scaffold most of the VGS API: the resource list, path
templates, content types, the multi-tenant host scheme, and per-object field
sets. Combine with the schema reference (`schemas/vgs-rest.md`, to be updated)
and the MVP order (`09-*`). Remaining gaps are exact response nesting and value
semantics — best closed by one captured response per resource (E4) or further
disassembly (E3, `13-*`).
