---
doc: engine-id
title: Engine Identification
summary: Client is stock-ish Unreal Engine 4.14.3 (CL 3195953), project codename "Vk", branch LIVE; module + third-party-lib inventory.
keywords: [unreal, ue4, 4.14, engine, version, modules, plugins, libraries, codename]
status: verified
updated: 2026-05-22
evidence: [E1, E2]
---

# Engine Identification

## Verdict

**Unreal Engine 4.14.3.** Source-compatible baseline; networking and asset
behaviour can be cross-referenced against the public UE 4.14 source tree.

`Engine/Build/Build.version` (E1):
- MajorVersion 4 · MinorVersion 14 · PatchVersion 3
- CompatibleChangelist 3195953 · IsLicenseeVersion 0 · BranchName ""

`IsLicenseeVersion 0` ⇒ built from Epic's released engine, not a custom CCP
engine fork at the version-stamp level.

## Distribution identity (Steam, E1)

- **Steam App ID: `688480`** ("EVE: Valkyrie - Warzone"); Steam buildid
  `2347437`; installdir `EVE Valkyrie - Warzone`.
- Precisely identifies this title/build, and is the handle for a Steam-context
  launch (`steam://rungameid/688480`) — see the capture plan's path #1
  (`methodology/traffic-capture-plan.md`).

## Project identity (from build-agent paths, E1)

Embedded debug paths look like:
`D:\BuildAgent\work\13008ed72f062fc8\Vk\LIVE\<module>\...`

- Project codename: **`Vk`**
- Branch: **`LIVE`** (a release/live branch; expect singularity/test branches existed)
- CI: a TeamCity-style **BuildAgent** working directory.
- Game project dir: **`VkGame`** (UE "uproject" name).

## Game module inventory (E1, file-count = rough size proxy)

Custom C++ modules under `VkGame/Source/`:

| Module | Files | Role (inferred) |
|--------|------:|-----------------|
| `VkGame` | ~1548 | Main gameplay module (the bulk of the game). |
| `VkRestUtils` | ~148 | REST/HTTP backend client layer. **Networking.** |
| `OnlineSubsystemVk` | ~38 | Custom UE4 OnlineSubsystem → Valkyrie backend. **Networking.** |
| `VkCore` | ~22 | Core/shared utilities. |
| `VkStaticData` | ~44 | Static game data tables/loading. |
| `VkFramerateStats` | ~6 | Perf/telemetry. |
| `OnlineSubsystemVkSteam` | ~2 | Steam platform bridge for the Vk subsystem. |

Plugins under `VkGame/Plugins/`:
- `DirectInputPlugin` — HOTAS / joystick input.
- `TrackIR` — head tracking (non-VR head look).
- `TobiiEyetracking` — eye tracking (ships its own DLLs).

## Third-party libraries embedded / shipped (E2)

Networking & crypto (statically embedded in the exe, per format strings):
- **libcurl** (HTTP/HTTPS client) — "curl.haxx.se" docs string present.
- **OpenSSL** (TLS) — "openssl.org" string present.
- **libwebsockets** — "Libwebsockets version: %s", "User-agent: libwebsockets".

Shipped DLLs (E1, `Manifest_*` + on-disk):
- Oculus PC SDK path (`Engine/Binaries/ThirdParty/PS4/Win64/hmd_client.dll` is
  mislabeled-dir Oculus client; confirm), `OculusSpatializerWwise.dll` (audio).
- `openvr_api.dll` (OpenVR/SteamVR HMD support).
- `steam_api64.dll` (Steamworks SDK v132).
- PhysX 3 + APEX (VS2015) — physics.
- Ogg/Vorbis — audio codecs; **Wwise** audio middleware (Oculus spatializer).
- NvVolumetricLighting (GameWorks) — rendering.
- Tobii GameIntegration + stream engine — eye tracking.

## Why this matters for preservation

Because the engine is stock UE 4.14.3, the *transport-level* networking
(NetDriver, channels, replication, RPC bunching) follows documented UE4
behaviour. The **proprietary surface to reverse is narrow**: the `Vk*` REST
resources, the `OnlineSubsystemVk` glue, the backend hostnames/protocol, and
which UE NetDriver is selected. That is where effort should concentrate.
