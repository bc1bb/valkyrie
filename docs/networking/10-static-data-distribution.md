---
doc: net-staticdata
title: Static Data Distribution & Voice
summary: VkStaticDataResource fetches a JSON file manifest (GetFileList → 'files' array of file objects), then downloads each file's contents — a CDN/manifest pattern the client must receive before play. Plus a note on VOIP.
keywords: [static data, manifest, getfilelist, files, cdn, download, VkStaticData, voice, voip, voicechannel, json, completion, listener, wall, login, e4]
status: draft
updated: 2026-05-24
evidence: [E2, E3, E4]
---

# Static Data Distribution & Voice

## Static data = a versioned file manifest (`FVKStaticDataResource`, E2)

Before/at boot the client pulls **static game data** (balance tables, catalogs,
config) from the backend using a two-step manifest pattern. The error strings
reveal the JSON contract:

1. **`GetFileList`** — the client requests a manifest. The response is JSON that
   **must contain a `files` array** ("No 'files' array in response to
   GetFileList"). Each entry is a **file object with required fields** ("File
   object didn't contain required fields") — minimally a file name/id, and very
   likely a content URL/hash/version (to support caching & integrity).
2. **Fetch contents** — the client then requests the contents of files **from
   that list**; requesting a file not in the manifest is rejected ("File
   contents requested for file not in file list"). This means the manifest is
   the authoritative allow-list; downloads are keyed off it.

`UVkStaticDataStatics` exposes this data to gameplay; `Static_Data` is the
in-engine category.

### What static data *contains* — entry taxonomy (E2)

Static data is a **versioned catalog of named entries** the client resolves by
key. Each entry has a **`StaticDataUniqueName`** + a human **ShortName** (must be
unique — *"The ShortName %s is being used more than once"*) + `StaticDataLink(s)`
+ a `StaticDataMapName`; the set is versioned (`About_StaticDataVersion` /
`STATIC DATA VERSION`). Recovered entry **categories**:
- **`ShipClassStaticData`** — the playable ship classes.
- **`UpgradeStaticData`** — ship upgrades.
- **Game modes** — resolved here: *"No game mode unique name found (-gamemode=
  xxx). Trying to determine static data entry from short name"* — so `-gamemode=`
  (`05-*`) maps to a static-data entry by unique-name/short-name.
- **Maps** — via `StaticDataMapName`.
- **Challenge links** — *"Backend delivered challenge is missing matching static
  data (ID %d, Name %s)"*: backend challenge objects (`11-*`/`13-*`) reference
  static-data entries by **ID + Name**, which must exist in the catalog.

So static data is the **name↔entry dictionary** binding backend identifiers
(game-mode/ship/upgrade/challenge unique-names) to client content. A re-impl
backend's static data must define every unique-name the pilot/session/challenge
objects refer to, or the client errors on lookup.

### It is login-gating (E2)

`LoginMessage_StaticDataDownloadFailed` is a **login-blocking** message — a static
-data download failure stops login. This confirms the **P0** classification: the
client will not proceed without a successful static-data fetch.

### GetFileList response shape — CONFIRMED (E3, via disassembly `13-*`)

```jsonc
{
  "files": [
    { "filename": "<logical file id/path>",
      "uri":      "<download location>",
      "checksum": "<integrity hash>" }
    // ...
  ],
  "branch_name":  "<build branch>",
  "build_number": "<build id>"
}
```

Field names recovered from the parse routine (`13-*`): each file entry is
`{filename, uri, checksum}`, and the manifest carries `branch_name` +
`build_number` (so static data is versioned per build/branch — the client can
detect stale data). The allow-list rule (only listed files are fetchable) holds.

### Re-implementation value

This is one of the most concrete REST contracts found so far and a **P0**
dependency (the client likely won't progress past load without valid static
data). A private backend must serve a `GetFileList` returning a `files` array
and then serve each file's bytes. Because it gates loading, getting this right
early unblocks everything downstream. (See roadmap `09-*`.)

### CONFIRMED LIVE (E4, 2026-05-23) — the real catalog ships in the client's pak

The genuine static-data files were recovered from the shipped pak (no guessing):

- **Source:** `WindowsNoEditor/VkGame/Content/Paks/VkGame-WindowsNoEditor.pak`
  (UE4 pak **v3, unencrypted**) ships `VkGame/Content/StaticData/**/*.json` as
  **plain uncompressed JSON** — 43 files across categories: `Currency`, `GameMode`
  (`GameModes.json`, `Wormholes.json`), `HeroShips` (`Covert/Fighter/Heavy/Support/
  NPC/NonTechTreeShips`), `Maps`, `Implants`, `Leagues`, `Reputation`, `Scoring`,
  `Popups`, `PilotCosmetics`, `HeroCosmetics`, `IAP`, `GlobalBoosters`,
  `LootCapsules`, `Platforms`, `DailyChallenges`, `RewardTiers` — each with a
  `Schema.json`. Tools: `analysis/scripts/pak_list.py`, `pak_extract.py`.
- **File format (confirmed):** each data file is
  `{ "schema": "./Schema.json", "uniqueName": "<catalog>", "dbID": <int>,
  "displayName": "<str>", "<category>": [ {entry}, … ] }`. Entries are keyed by
  **`uniqueName`** (dotted, e.g. `currency.visk`, `shipclass.Fighter`,
  `gamemode.*`) + a numeric **`dbID`**; this resolves the `StaticDataUniqueName`
  taxonomy in `01-*`. The manifest `files[]` entries are `{filename, uri,
  checksum}`; **`checksum` is md5 (hex)** of the file bytes (confirmed accepted by
  the client).
- **Live behaviour:** when the GetFileList manifest's md5 checksums match the
  client's local pak copies, the client **does not download** — it uses its local
  static data. So a re-impl can serve the pak-extracted files with correct md5s
  and the client treats them as current. (Serving an empty/stub manifest instead
  makes the checksum mismatch and the client downloads the stub.)
- **Important:** static-data CONTENT is NOT the current login blocker — see
  `reimpl/04-live-bringup-log.md` (Session 2). With both an empty stub and the
  full real catalog the client reaches the same post-registration "connection-
  ready" timeout, so the final wall is elsewhere.

The `files[]` schema and absolute-vs-relative URL question (Open questions, below)
are answered: filenames are repo-relative paths under `StaticData/`, uris are
absolute on the VGS host, checksum is md5.

## GetFileList completion handler & the completion-notification wall (E3/E4, 2026-05-24)

The `FVKStaticDataResource` GetFileList response handler is **`0x14209b550`** (found
by direct xref to the manifest fields `branch_name` `0x143105f30` / `build_number`
`0x143105f60`; the resource's log-format strings are linker-pooled and have no direct
xref). Instruction-level behaviour:

- Null-`Response` guard → transport-failure path.
- Parse the body via `0x142038010` into an `FVkJsonObject`.
- Read `branch_name` + `build_number` (logged as `"CL %d : %s"` — **not** a gate).
- `TryGetObjectArrayField("files")`; per entry read **`filename` / `checksum` / `uri`**
  (all three required, else the entry is dropped — the "File object didn't contain
  required fields" path). Each valid entry is registered into a manager at
  `resource+0x90` and appended to a local list.
- **Success gate (`0x14209bc50`):** `success = (Response != null) && (validFileCount > 0)`.
  With a well-formed manifest this is **true** — GetFileList SUCCEEDS (verified live).

**The login wall is NOT GetFileList and NOT static-data content (E4, 2026-05-24).**
Confirmed live: GetFileList succeeds; the served files are **byte-identical to the
client's pak** (re-extracted all 43 `StaticData/*.json` and md5-compared — 43/43 exact),
so cache-hit (zero downloads) is correct. With both forced downloads (cache-busted md5)
and pure cache-hit the client stalls **identically** on "DOWNLOADING STATIC DATA",
heartbeats `PUT /clients/1` for `heartbeat_seconds`, then `DELETE`s and shows "A NETWORK
ERROR HAS OCCURRED" (`LoginMessage_StaticDataDownloadFailed` / `_GenericTimeout`).

**Root cause located:** after GetFileList succeeds, the handler's **completion-notify
block is skipped** — at `0x14209bc6c` it gates on `resource+0x30 != 0`, and a live probe
found `resource+0x20` (the completion listener) **NULL** and `resource+0x30 == 0` at
completion. So the static-data resource finishes but **notifies nothing**, and the login
state machine is never told static data is ready → it times out. The open question for a
re-impl is therefore **how the frontend/login flow subscribes to the static-data "done"
signal** (what sets `resource+0x20` / `resource+0x30`) and why it is unset — likely a
listener that depends on a field not yet supplied in the pilot/accounts/clients
responses, or a polled "ready" state never set. See `reimpl/04-live-bringup-log.md`
(Session 3) for the full trace and the ruled-out list.

> Manifest serving (re-impl): advertise only the real catalog data files in `files[]`
> (the live evidence: the client fetches exactly the 26 data files and never requests a
> `Schema.json`, so the 17 `Schema.json` files must NOT be listed). `checksum` = md5 hex
> of the served bytes. A `Location` header on the manifest/file responses is **not**
> required (tested, no effect).

## Voice (VOIP)

Voice chat is present (`VoiceChat`, `VoIP`, `VoiceChannel`). **Resolved (E2,
`08-*`):** it is **UE4's built-in VOIP over the Opus codec** (`opus_packet_get_
nb_*`, `AddVoicePacket to=/from=`), riding the game NetDriver — not a platform
relay. Push-to-talk is configurable (`bRequiresPushToTalk`).

### Re-implementation value

Voice is **non-blocking** for playability (P3). A private server on the same
engine inherits VOIP packet relay for free; it can also be ignored initially.

## Open questions

- Exact `files[]` object schema (field names, whether URLs are absolute or
  relative to the VGS host). *(Partly closed: `{filename, uri, checksum}` + manifest
  `branch_name`/`build_number`, `13-*`.)*
- Whether static data is cached on disk and re-validated by hash/version.
- The `GetFileList` request path/verb on the VGS host.
