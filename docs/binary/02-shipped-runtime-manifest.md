---
doc: binary-manifest
title: Shipped Runtime Manifest & Middleware Versions
summary: The exact non-packaged (NonUFS) files shipped with the build — third-party middleware DLLs with precise versions (OpenVR v1.0.2, Steamworks v1.32, PhysX/APEX VS2015, Ogg/Vorbis, GameWorks, Oculus/Tobii) — plus build dates and the engine Build.version. Definitive dependency inventory for a preservation runtime.
keywords: [manifest, nonufs, dependencies, dll, middleware, openvr, steamworks, physx, apex, vorbis, gameworks, oculus, tobii, build version, changelist]
status: draft
updated: 2026-05-23
evidence: [E1]
---

# Shipped Runtime Manifest & Middleware Versions

The UE4 packaging process emits two manifests next to the build root listing the
**non-packaged** files (everything not inside the `.pak`): `Manifest_NonUFSFiles_
Win64.txt` (runtime deps) and `Manifest_DebugFiles_Win64.txt` (symbols). Each line
is `relative\path<TAB>ISO-8601 timestamp`. These are pure build metadata (E1) —
no creative content — and give a **definitive dependency list** for standing up a
preservation runtime, plus exact middleware versions that pin the integration
points documented elsewhere.

## Build dates (E1)

- **Game EXE/PDB:** `2017-12-06T15:27:32Z` — the Warzone client build timestamp.
- **Engine third-party DLLs + `Build.version`:** `2017-11-28T13:xx` — the
  prebuilt UE 4.14.3 redist layer (older than the game code, as expected).
- **Cooked movies:** `2017-11-28T15:39Z`.

## `Build.version` (E1)

```
MajorVersion 4 · MinorVersion 14 · PatchVersion 3
Changelist 0 · CompatibleChangelist 3195953
IsLicenseeVersion 0 · BranchName ""
```

Precision note: the **3195953** figure is the *CompatibleChangelist* — i.e. the
stock Epic UE 4.14.3 release changelist the build is binary-compatible with — not
a game-specific CL (the game `Changelist` is `0`, and `BranchName` is empty in
this file; the `Vk`/`LIVE` branch codename seen in binary strings is the internal
Perforce stream, a separate fact). Confirms a vanilla 4.14.3 engine base.

## Third-party middleware (NonUFS, exact versions, E1)

The shipped DLLs and their versioned paths — this is the authoritative middleware
inventory (supersedes inferences in `engine/06-*` / `02-*` with exact versions):

| Middleware | Shipped artifact / version | Role | Cross-ref |
|------------|----------------------------|------|-----------|
| **OpenVR** | `OpenVRv1_0_2/.../openvr_api.dll` — **v1.0.2** | SteamVR/Vive HMD path | `engine/06` |
| **Steamworks** | `Steamv132/.../steam_api64.dll` — **SDK v1.32** | Steam platform/tickets/overlay | `networking/07` |
| **Oculus** | `OculusSpatializerWwise.dll` | Wwise HRTF spatializer (Oculus audio) | `engine/06` |
| **PhysX** | `PhysX3_x64`, `PhysX3Cooking_x64`, `PhysX3Common_x64`, `PxFoundation_x64`, `PxPvdSDK_x64` (VS2015) | Rigid-body physics / collision | below |
| **APEX** | `APEX_Clothing_x64`, `APEX_Destructible_x64`, `APEX_Legacy_x64`, `ApexFramework_x64` (VS2015) | Cloth + destructible meshes | below |
| **GameWorks** | `NvVolumetricLighting.win64.dll` | Volumetric light shafts | `engine/06` |
| **Ogg/Vorbis** | `libogg_64`, `libvorbis_64`, `libvorbisfile_64` (VS2015) | Vorbis codec (Wwise/UE4 compressed audio) | `engine/06` |
| **Tobii** | `Tobii.GameIntegration.dll`, `tobii_stream_engine.dll` | Eye tracking / foveation | `engine/03` |
| **PS4 HMD** | `ThirdParty/PS4/Win64/hmd_client.dll` | HMD client lib (PS4-lineage path; ships on PC build) | note below |
| **Steam Input** | `Engine/Config/controller.vdf` | Steam controller binding profile | `engine/03` |
| **Prereqs** | `UE4PrereqSetup_x64.exe` | VC++ runtime installer (launch-time) | — |

All toolchain-tagged libs are **VS2015** builds — consistent with the MSVC VS2015
toolset fingerprint in `binary/01-*` and confirms the whole native stack was
compiled with one toolchain (matters for ABI when reproducing a runtime).

### PhysX / APEX — physics stack (newly surfaced, E1)

The build ships the full **PhysX 3 + APEX** stack — not previously documented as a
distinct subsystem. UE 4.14 uses PhysX as its default physics backend, so this is
engine-stock, but its presence pins concrete capabilities for a preservation
client: rigid-body collision (ship/projectile/asteroid), `APEX_Destructible`
(breakable geometry — destructible objects/debris) and `APEX_Clothing` (simulated
cloth). `PxPvdSDK` is the PhysX Visual Debugger transport (dev tooling, inert at
retail). This is **client/engine-local** and has **no backend relevance**: server
authority is over the gameplay RPCs (`networking/08-*`), not PhysX simulation.

### `hmd_client.dll` (PS4 path) — caution (E1)

The file lives under `Engine/Binaries/ThirdParty/PS4/Win64/` yet is a Win64 DLL.
This is a UE 4.14 redist-layout artifact; the PS4 directory name reflects the
engine's cross-platform HMD-client lib origin and does **not** imply PS4 code runs
on PC. Recorded as-is (E1) without over-claiming a PSVR runtime on this build.

## Debug manifest (E1)

`Manifest_DebugFiles_Win64.txt` lists `VkGame-Win64-Shipping.pdb` plus the PhysX/
APEX `.pdb`s. **None are present** on this Steam install (retail build strips
them) — see `binary/01-*`. The manifest only proves they *existed* in the
packaging tree; a located game PDB would massively accelerate symbol recovery.

## Preservation relevance

This is the shopping list for a **runtime environment**: a preservation client
needs these exact DLLs (or version-compatible substitutes) alongside the EXE and
`.pak`. The middleware is all client-local; **none** of it is needed to
re-implement the **server/backend** (`networking/*`). The version pins (OpenVR
1.0.2, Steamworks 1.32) also bound compatibility testing for any modern-runtime
shimming.
