---
doc: net-staticdata
title: Static Data Distribution & Voice
summary: VkStaticDataResource fetches a JSON file manifest (GetFileList → 'files' array of file objects), then downloads each file's contents — a CDN/manifest pattern the client must receive before play. Plus a note on VOIP.
keywords: [static data, manifest, getfilelist, files, cdn, download, VkStaticData, voice, voip, voicechannel, json]
status: draft
updated: 2026-05-22
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

### Inferred GetFileList response shape (E2-derived hypothesis)

```jsonc
{
  "files": [
    {
      // required fields (names TBD by capture):
      "name": "<logical file id/path>",
      // probable additional fields:
      "url":  "<download location>",
      "hash": "<integrity checksum>",
      "version": "<revision>"
    }
    // ...
  ]
}
```

Exact field names need a live capture (E4) or deeper static analysis; the
**structure** (`files: [ {...} ]`) and the allow-list rule are confirmed (E2).

### Re-implementation value

This is one of the most concrete REST contracts found so far and a **P0**
dependency (the client likely won't progress past load without valid static
data). A private backend must serve a `GetFileList` returning a `files` array
and then serve each file's bytes. Because it gates loading, getting this right
early unblocks everything downstream. (See roadmap `09-*`.)

## Voice (VOIP)

Voice chat is present (`VoiceChat`, `VoIP`, `VoiceChannel`). UE4 supports
networked voice through its `IOnlineVoice` interface; the audio path here also
involves the Oculus spatializer (Wwise). Whether voice packets ride the game
NetDriver (replicated voice) or a platform-relayed channel is undetermined.

### Re-implementation value

Voice is **non-blocking** for playability (P3). A private server can omit voice
relay initially; players simply won't hear in-game VOIP.

## Open questions

- Exact `files[]` object schema (field names, whether URLs are absolute or
  relative to the VGS host).
- Whether static data is cached on disk and re-validated by hash/version.
- The `GetFileList` request path/verb on the VGS host.
- Voice transport: replicated over NetDriver vs platform relay.
