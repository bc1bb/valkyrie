---
doc: net-disasm
title: Disassembly-Recovered Fields & Method
summary: Targeted static disassembly (RIP-relative xref to UTF-16 grant strings) recovered new JSON fields (match-config, rank-up reward breakdown), the custom FVkJsonObject parser, and the PUT verb. client_id is runtime-built/non-pattern; and is NOT needed for re-implementation.
keywords: [disassembly, objdump, xref, rip-relative, fvkjsonobject, json fields, match config, rank up, put, client_id, method, e2, e3]
status: draft
updated: 2026-05-22
evidence: [E2, E3]
---

# Disassembly-Recovered Fields & Method

Because the Vk strings are **UTF-16** (`FString`), targeted disassembly can
anchor on a known wide string, find its RIP-relative cross-reference in `.text`,
and read the surrounding routine's other string constants. This recovered the
fields below (tier E3 — read from the request-builder routines).

## Method (reproducible, no symbols needed)

1. Find the `.rdata` VA of a UTF-16 anchor (e.g. `grant_type=steam_ticket`).
2. Byte-scan `.text` for a RIP-relative `disp32` whose target == that VA →
   the instruction (`lea reg,[rip+disp]`) referencing it.
3. Scan that routine's window for other `48/4C 8D 05+disp32` (`lea` of RIP) and
   decode the UTF-16 string at each target → the field/constant set the routine
   uses.

**Reproduce it:** `analysis/scripts/recover_object.py "<anchor>"` (committed, our
own tool) implements exactly this — e.g. `recover_object.py owner_callsign`
prints the session object. Point it at any resource-unique field to recover that
resource's structure; output is field-name identifiers only (raw goes to the
git-ignored `analysis/raw/` if you redirect it).

Anchors used: `grant_type=steam_ticket` (→ SSO body builder @ ~`0x1420c6779`),
`grant_type=refresh_token` (→ a builder/parser @ ~`0x14208cc2b`).

## Recovered JSON fields (E3)

**Match / battle config** (session object, cf. `01-*`/`05-*`):
`goals_to_win`, `capture_speed`, `cooling_node_health`, `turrets_enabled`,
`shield_down_time`, `in_progress`, `team_0_pilot_id`, `team_1_pilot_id`
(per-team pilot id slots — note 0/1 team indexing matches `-NUMAITEAM0/1`).

**Rank-up / reward breakdown** (post-battle, cf. `11-*`):
`reputation`, `old_rank`, `new_rank`, and a points breakdown of
`base` + `bonus` + `boost` under an `event`. (Confirms rewards are an itemized
object, not a single number.)

## Confirmed mechanisms (E2/E3)

- **Custom JSON parser**: `FVkJsonObject` with a full typed getter set —
  `TryGetBoolField`, `TryGetNumberField`, `TryGetStringField`,
  `TryGetObjectField`, `TryGetObjectArrayField`, `TryGetStringArrayField`,
  `TryGetNumberArrayField`, `Find`. So responses contain **nested objects and
  arrays** (not flat), and the client **tolerates missing fields** (logs "Failed
  to find number field for field named '%s'" and continues) — a re-impl may omit
  unknown fields without crashing the client.
- **HTTP verb `PUT`** is used (alongside GET/POST) — some resources are updated
  via PUT (e.g. session/state mutations). A re-impl must route PUT.

## client_id: runtime-built, and NOT needed for re-implementation

A pattern scan of `.rdata` (ASCII + UTF-16) for an EVE-style credential found
**no client_id**: only an MD5-of-empty-string constant (`d41d8cd9…`), a base36
charset, and an unrelated UE4 GUID. The Basic-auth credential is assembled at
runtime from non-obvious constants (recovering the literal would need deeper
tracing of the `SetHeader("Authorization", …)` call).

> **Key insight:** the exact `client_id`/`client_secret` is **not required** to
> restore play. A preservation backend re-implements the **SSO too**, so it
> defines its own client-credential policy — it can accept any `Authorization:
> Basic` value the client sends (or ignore it). The credential only matters for
> talking to CCP's *original* (dead) SSO. So this is reclassified from a
> blocking unknown to **nice-to-have**. (See `03-*`, `12-*`.)

## Pilot object — recovered parse order (E3)

Anchoring on pilot-unique fields (`has_set_gender`, `npe_complete_uri`,
`hero_xp_transfer_uri`) located the pilot parse routine; the ordered `lea`
field-string loads give the **parse-order field sequence** (strong structural
hint — `_uri` = HATEOAS links, plurals = collections/sub-objects):

```
# envelope / auth context (likely outer response wrapper)
message, content, token, provider, signup
# squad sub-object (pilot's current squad)
invites, squad_join_uri, squad_uri, squad_version,
squad_leader_id, squad_leader_callsign
# current session/battle summary (nested)
max_players, status, is_joinable
# pilot link graph (HATEOAS *_uri)
hero_xp_transfer_uri, friends_uri, cosmetics_uri, gender_uri,
collectibles_uri, npe_complete_uri, hero_rewards_uri, training_uri,
recall_uri, eula_uri, settings_uri, hero_upgrades_uri,
hero_cosmetics_uri, applied_hero_cosmetics_uri, invites_uri,
pilot_cosmetic_uri, pilot_cosmetic_variant_uri, applied_pilot_cosmetics_uri
# collections / sub-objects
challenges, implants, pilot_cosmetics, applied_pilot_cosmetics,
global_events, settings, hero_ships, hero_cosmetics,
applied_hero_cosmetics, loot_capsules, hero_ship_stats
# scalar identity / flags
callsign, pilot_name, gender, has_set_gender, npe_completed,
is_showfloor, showfloor_spectator, eula_signed, properties
```

This is the most complete single-resource structure recovered statically. The
grouping (links vs collections vs scalars) is reliable; precise object nesting
(which collection sits under which key) still benefits from one captured
response (E4). It directly fills step 3.3 of the build guide (`reimpl/01-*`).

## Session object — recovered (E3)

Anchor `owner_callsign` → session parse routine:
```
session_uri, pilots_uri,                       # self + players link
max_pilots, current_players,                   # player capacity
max_spectators, current_spectators,            # spectator capacity
owner_callsign, owner_platform,                # host identity
in_progress,                                   # state flag
custom_settings                                # nested game-mode toggles (14-*)
```
(Plus a `vkpilot` ref — likely a nested pilot summary per slot.) This is the
matchmaking result object the client reads to show/join a session.

## Post-battle rewards object — recovered (E3)

Anchor near `host_pilot_ids` → the rewards parse routine (driven by `MatchEnded`,
`05-*`):
```
# score breakdown
base, bonus, boost, event,
old_score, new_score,                          # rank-score delta
first_win,                                     # first-win bonus flag/amount
# grants
loot, loot_score_capsules,
reputation_capsules, challenge_capsules,
proving_grounds_reward_name
```
So the end-of-match payload itemizes the score math and the capsule/loot grants
(consistent with `11-*`). A re-impl returns this object after `battle_completed`.

## Common response envelope (NEW, E3)

The fields `verb`, `uri`, `content`, `message`, `status` recur across multiple
parse routines (squad, session-request, others). **Verified (E3):** in `.rdata`
these names are stored **adjacently** (the `uri`/`verb`/`content`/`status`
grouping recurs at ≥2 sites), the field-constant layout a compiler emits for a
single struct — confirming a **common response envelope** wrapping each resource:
```
{ "uri": <self link>, "verb": <method>, "status": <code/state>,
  "message": <info>, "content": { ...the actual resource object... } }
```
(In auth/signup responses the envelope also carries `token`/`provider`/`signup`.)
So clients read `content` for the resource and use `uri`/`verb` for the next
HATEOAS hop. A re-impl should wrap responses in this envelope. (Auth/signup
responses also carry `token`/`provider`/`signup` at this level.)

## Squad object — recovered (E3)

Anchor `squad_leader_callsign`:
```
# envelope: verb, uri, content, message, token, provider, signup
squad_uri, squad_version, squad_leader_id, squad_leader_callsign, invites,
squad_join_uri,
# the squad's matchmaking context (current/last):
game_mode, status, is_joinable, session_id, battleserver_id,
min_pilot_rank, max_pilot_rank
```

## Leaderboard entry — recovered (E3)

Anchor `instance_name` region (leaderboard parse):
```
pilots[ { pilot_id, callsign, platform,
          rank, position, points, kills, kd_ratio,
          league_position, league_score,
          battles, battles_required } ]
```

## Challenge object — recovered (E3)

Anchor `challenge_url`:
```
active_challenges[ { challenge_id, challenge_name, difficulty_name,
                     challenge_url, progress, rewards:{type,amount},
                     ship_name, cosmetic_type_name, cosmetic_name,
                     # objective thresholds:
                     max_kills/max_assists/max_captures/max_pvp_kills/
                     max_points/max_drone_kills/max_emps/max_repairs/
                     max_node_kills/max_kd } ],
challenges_ended_recently
```

## Auth token response — confirmed (E3)

Anchor `expires_in` → `{ access_token, refresh_token, expires_in }` (standard
OAuth2 token response; matches `03-*`). Confirms what a re-impl SSO returns.

## Client-event telemetry payload — recovered (E3)

Anchor `event_name` → the `client-event` payload carries `event_name`, `count`,
`type_name`, plus event-specific stats: `ship_name`, `kills`/`deaths`/`assists`/
`wins`/`losses`/`battles`, `implant_type_name`/`implant_count`,
`loot_score`/`loot_capsule_uri`/`loot_capsule_type_name`/`capsules_earned`/
`unlocked`, `cosmetics`/`cosmetic_name`. (Different events fill different
subsets — see throttling in `14-*`.)

## Battle-server registration — recovered (E3)

Anchor `public_ip` → the dedicated server's self-registration payload (POSTed to
`battleservers`, cf. local reg `localhost:10080` in `14-*`):
```
{ href, battle_id, public_ip, port,
  map_unique_name, game_mode_unique_name,
  # host/machine fingerprint:
  client_id, build_version, os_platform, computer_name, hmd_type, is_2d }
```
This is the concrete Plane1→Plane2 seam: the server advertises its `public_ip`
+ `port` (the WebSocket endpoint) keyed by `battle_id`.

## Static-data manifest — confirmed (E3)

Anchor `filename` → `GetFileList` response (confirms `10-*`):
```
{ files: [ { filename, checksum, uri } ],
  branch_name, build_number }
```
(So the inferred `{name,url,hash,version}` in `10-*` is really
`{filename, uri, checksum}` + manifest-level `branch_name`/`build_number`.)

## Store offer / purchase — recovered (E3)

```
offers:  { products: [ { items: [ { quantity } ], currency, price } ], next }
purchase/sale request: { currency, amount, parameters }
```
(`next` = pagination cursor; media type `application/vnd.ccp.eve.VgsSale-v1+json`,
`14-*`.)

## Remaining thin/shared objects (E3)

The last few resources are thin or reuse documented fields:
- **session-request** (`sessionrequests`): a thin POST — carries the matchmaking
  selectors already documented (game_mode/session_type/region as query+body) and
  returns a `session` (log: "Session Request returned session: %s and pilot: %s").
  No distinct large object.
- **notification**: a thin list (`notificationlist_success`/`_fail`); no rich
  object recovered — likely `[ { message/type/uri } ]`.
- **league entry**: `{ score, rank, completed }` (+ display/settings toggles
  `show_leagues`, `roll_on_stick` which belong to the pilot `settings` object).

## Match-result report — recovered (E3, request body)

The dedicated server's match-end POST (drives rewards, `05-*`/`11-*`):
```
{ battle_id, pilot_id, team_id,
  battle_stats: { ... }, player_stats: { ... } }
# stats content:
{ score, loot_scores, kills, deaths, assists, hero_ship_stats,
  # objective breakdown:
  objective_firstblood, objective_multikill, objective_dronekill,
  objective_emp, objective_repair, objective_nodekill,
  objective_carrierkill, objective_capture }
```
Backend **responds** with the rewards object (`reputation`, `old/new_rank`,
`base`+`bonus`+`boost`, `xp`, `loot`, capsules — see the rewards object above).
So the match-end flow is: server POSTs this report → backend computes payout →
returns rewards. (`objective_*` are the scored objective events; new fields.)

## Completeness audit (E3)

A sweep with `recover_object.py` across remaining anchors (`collectible_name`,
`upgrade_name`, `friends_uri`, `item_id`, …) found **no significant new
structures** — they land in already-documented objects:
- **upgrades**: `{ upgrade_name, xp, active, seconds_remaining, seconds_to_start }`
  — i.e. timed/active upgrades & boosters (consistent with `global_booster`/
  `booster_name`/`multiplier`, `14-*`).
- collectibles: a thin list (`collectible_name` + ids).
- friends/cosmetics: resolve into the pilot link graph (already documented).

So the recovered object set is **complete** for the resources the client uses;
remaining refinement is value-types/nesting via capture (E4).

## Object-model coverage status — COMPLETE (E3)

Recovered statically: **pilot, session, post-battle rewards, squad, leaderboard
entry, challenge, auth-token response, client-event, battle-server registration,
static-data manifest, store offer/purchase** + the **common envelope**. This is
the full set of resources a minimal backend serves. Remaining work is confirming
exact value types / deep nesting per object — best closed by one captured
response each (E4), but the field sets + grouping above are sufficient to
scaffold a working re-implementation.

## Value

The disassembly method is now proven and can be pointed at any `Vk*Resource`
builder to recover its exact field set — the most productive remaining static
technique for fleshing out per-resource JSON schemas (tier E3), short of live
capture (E4).
