---
doc: schema-vgs-rest
title: VGS REST Schema Reference (consolidated)
summary: Single structured reference for the VGS backend REST surface — base/versioning, HATEOAS model, common conventions, per-resource endpoints + object fields recovered to date. Our own clean-room description, not captured bytes.
keywords: [schema, rest, vgs, reference, endpoints, json, hateoas, fields, valkyrie, consolidated, spec]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# VGS REST Schema Reference (consolidated)

A re-implementer's single-page model of the backend REST surface. This is **our
own description** synthesized from interface evidence (docs 01/03/04/05/10); it
is not a copy of any captured payload. Fields marked `?` are inferred (E5) and
need a real capture to confirm (see `methodology/traffic-capture-plan.md`).

## Base & versioning

```
base_url       = https://vgs-tq.eveonline.com/        # TQ (prod); see 04
multi-tenant   = {scheme}://{tenant}.{domain}/{path}/ # %s://%s.%s/%s/ ; see 14
domains        = valkyrieapi.com, evevalkyrie.com, eveonline.com  # NEW (14)
path_prefix    = {version}/valkyrie/                  # version is PER-RESOURCE
versions_seen  = v1.0, v2.0                            # both must be routed
auth           = Authorization: Bearer <JWT>          # REST; see 03
token-endpoint = Authorization: Basic b64(client_id:client_secret) # OAuth; 03/12
content_type   = application/json (+ vnd.ccp.eve.VgsSale-v1+json for sales)
encoding       = snake_case field names ; HATEOAS *_uri links
full-surface   = see networking/14-vgs-api-surface.md (resources/fields/taxonomies)
```

## Conventions

```
envelope   : responses wrap the resource in a common envelope (E3, 13-*):
             { uri, verb, message, content:{...resource...} } ; read `content`.
hypermedia : responses embed *_uri fields; client follows them (HATEOAS).
             => server controls paths; don't assume hardcoded routes.
paging     : offset + limit (and/or page + page_size); count returned.
filtering  : filter, period, scope, recent, group (query string).
ids        : numeric ids (pilot_id:int, store id in path e.g. stores/7).
errors     : standard HTTP status. 401/expired-token => client runs the
             refresh_token grant and retries (return 401, not generic 5xx).
             Some endpoints have "allowed" non-fatal codes (e.g. 404 optional).
retry      : UE4 HttpRetrySystem (backoff); slow-request watchdog. Be forgiving.
```

## Endpoints (confirmed paths in **bold**, inferred in plain)

```
AUTH  (login host, see 03)
  POST  https://login.eveonline.com/oauth/token
        grant_type=steam_ticket | password(oculus) | refresh_token

ACCOUNTS / IDENTITY
  *  v2.0/valkyrie/accounts/                 # account root
     fields: account/pilot refs, npe_completed, *_uri links

PILOTS
     {ver}/valkyrie/pilots/?pilot_id={int}
     {ver}/valkyrie/pilots/?pilot_ids={csv}
     follow pilot_uri / pilots_uri from parent objects
     fields: pilot_id, my_pilot_id, reputation_rank, league_score,
             hero_ship_stats, applied_pilot_cosmetics, implant_seconds,
             stats_updated, *_uri

SESSIONS / MATCHMAKING (see 05, 06)
     {ver}/valkyrie/sessions/?session_type={str}
     follow session_uri ; queue by playlist; ServerTime = authoritative clock
     session_type/mode values: EVkGameModeType (see engine/04-game-modes)
       PvP (needs backend): Control, Base_PVP, TDM, Bomb, Bounty, Convoy, Armada
       PvE/narrative (standalone): Survival, Scout, Virus, Training, Recall_*, ...
     custom-match visibility: PUBLIC | FRIENDS | PRIVATE (EVkCustomMatchType)
     fields: session_id, session_type, max_players, max_pilots,
             min_pilot_rank, max_pilot_rank, num_ai_per_team,
             clones_per_team, battles_required, time_to_battle_join,
             battle_id, battleserver_id, *_uri

PLAYER STATE / PROGRESSION / ECONOMY (see 11)
     wallet: Currencies { silver (soft), gold (hard), balance }
     ranks:  reputation_rank, league_score, min/max_pilot_rank
     rewards (post-battle): win_bonus + match_score + first_win + completion,
             rewardTier, reward capsules; triggered by battle_completed
     loadout/customization: hero_ships[ {hero_ship_name, hero_ship_stats} ],
             loadouts, applied_pilot_cosmetics (decal/skin/paintjob/variant),
             implants (implant_seconds = time-limited), pilot_cosmetic_variant_uri
     account flags: npe_completed, build_version, os_platform, client_id

SQUADS / PARTY (see 06)
     follow squad_uri / squad_join_uri / squad_invites_uri / squad_pilot_uri
     fields: squad_id, squad_version, squad_leader_id,
             squad_leader_callsign, team_id

STORE / VIRTUAL GOODS (see 01)
  *  v2.0/valkyrie/stores/{store_id}/offers/    # e.g. stores/7/offers/
     purchase result -> EInAppPurchaseState
     follow loot_capsule_uri, hero_rewards_uri

LEADERBOARDS
  *  {base}hero_leaderboard/{id}?{query}
  *  {base}hero_survival_leaderboard/{a}/{b}
  *  {base}wormhole_leaderboard/{id}?{query}
     query: offset/limit/count/filter/period/scope

NOTIFICATIONS
  *  v1.0/valkyrie/notifications/oculus        # platform-channel notifications
     callbacks: notificationlist_success / notificationlist_fail

STATIC DATA (see 10)
     GetFileList -> { "files": [ { name, url?, hash?, version? }, ... ] }
     then fetch each file's bytes (manifest is the allow-list)

BATTLE RESULTS
     battle_completed report at match end -> progression/stats update
```

## Minimal viable backend (maps to roadmap 09 P0/P1)

```
1. POST /oauth/token         -> mint JWT (scopes: valkyrie.userLogin.v1,
                                vgs.valkyrieVirtualStore.v1, vgs.marketAccess.v1)
2. GET  accounts/            -> account obj w/ pilot_uri, npe_completed=false
3. GET  pilots/?pilot_id=    -> pilot profile obj
4. StaticData GetFileList    -> files[] the client can load
5. sessions/ + battleserver  -> allocate server, return its ws uri + join token
6. (PartyBeacon host accepts reservation; client connects; match runs)
```

## Confidence

Paths/fields here are **interface-level (E2)**; the link graph and full per-object
schemas are partly inferred (E5). Confirm with one captured response per resource
via the gdb method before treating any `?` field as final.
