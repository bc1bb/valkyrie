---
doc: net-progression
title: Progression & Economy Backend Model
summary: Backend-served player-state model — dual currency (Silver/Gold), match reward breakdown, ranks, and the loadout/cosmetic/implant/hero-ship customization data the server must persist and return.
keywords: [progression, economy, currency, silver, gold, rewards, rank, loadout, cosmetic, implant, hero ship, skin, decal, paintjob, variant, backend]
status: draft
updated: 2026-05-22
evidence: [E2, E5]
---

# Progression & Economy Backend Model

What the backend persists per pilot and returns to the client. These are the
data objects a re-implemented server must serve (via the `Vk*Resource` REST
layer, `01-*`) for progression/customization to work. Field names are E2;
groupings/relationships are partly inferred (E5).

## Currencies (dual-currency economy)

- **Silver** — soft currency (earned in-match). (`silver`, `Credits`.)
- **Gold** — hard/premium currency (real-money / store). (`gold`.)
- Held in a per-pilot wallet: `Currencies` / `balance`. Store purchases
  (`VkVirtualGoods`, `stores/{id}/offers/`) and loot (`VkLootCapsuleResource`)
  debit/credit these. `refund_for_hero_ship_name` indicates a refund path.
- **Real-money top-up** of Gold went through the **platform store**, not the VGS
  backend: the Oculus build links Oculus-Store IAP (`ovr_IAP_LaunchCheckoutFlow`/
  `GetProductsBySKU`/`GetViewerPurchases`, E1, `07-*`); the Steam build the Steam
  equivalent. A preservation backend cannot honor these (they were store
  transactions); it can only grant/seed the resulting currency balances.

## Match rewards (post-battle grant)

Reward components observed (combined into the end-of-match payout):
`Rewards_WinBonus`, `Rewards_MatchScore`, `Rewards_FirstWinScore`,
`Rewards_CompletionBonus`, plus a `rewardTier` and reward "capsule" (loot)
grants. Driven by the `battle_completed` report (`01-*`) → backend computes and
credits rewards, returns the breakdown for the rewards-flow UI.

## Ranks / standing

`reputation_rank` (pilot standing), `league_score` (competitive), and matchmaking
bands `min_pilot_rank` / `max_pilot_rank` (also session fields, `01-*`/`05-*`).
A backend must track rank/score and expose them on the pilot object.

## Loadout & customization (backend-served catalog + ownership)

The backend serves both a **catalog** (what exists) and **ownership/applied**
state (what this pilot has/equips):

- **Hero ships** (the playable ships): `hero_ships` (collection),
  `hero_ship_name`, `hero_ship_stats` (per-ship tuning/stats).
- **Loadout**: `loadout` / `loadouts` — the equipped configuration per ship.
- **Cosmetics**: `cosmetic_name`, `cosmetic_type_name`, `variant_name`,
  `applied_pilot_cosmetics`, and link `pilot_cosmetic_variant_uri`. Cosmetic
  *types* include **decals**, **skins**/**paintjobs**/**modelskins** (ship
  appearance) and pilot cosmetics. (`VkPilotCosmeticResource`,
  `VkHeroCosmeticResource`.)
- **Implants**: `implant`, `implant_seconds` — **time-limited** gameplay
  modifiers (note `_seconds`: implants are consumable/duration-based, not
  permanent). (`VkImplantResource`.)

## Re-implementation value

For playability (roadmap `09-*`), a private backend can serve **static/permissive
defaults**: a wallet with some Silver/Gold, all hero ships unlocked, empty
applied-cosmetics, no active implants. Rewards can be stubbed to a fixed payout.
None of this blocks reaching a match — it's P2/P3 — but the **field shapes above
must exist** in the pilot/account responses or the client's progression UI may
error. Confirm exact JSON via the gdb/capture path
(`methodology/traffic-capture-plan.md`).

## Open questions

- Whether `hero_ship_stats` are server-authoritative (balance) or cosmetic-only.
- Implant duration semantics (`implant_seconds`: countdown vs. expiry timestamp).
- Currency caps, sources, and store price fields on `offers`.
