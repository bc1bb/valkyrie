---
doc: net-staticdata
title: Static Data Distribution & Voice
summary: VkStaticDataResource fetches a JSON file manifest (GetFileList → 'files' array of file objects), then downloads each file's contents — a CDN/manifest pattern the client must receive before play. Plus a note on VOIP.
keywords: [static data, manifest, getfilelist, files, cdn, download, VkStaticData, voice, voip, voicechannel, json]
status: draft
updated: 2026-05-23
evidence: [E2]
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
