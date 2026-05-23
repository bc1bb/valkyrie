---
doc: engine-render-audio-vr
title: Rendering, Audio & VR Pipeline
summary: Integration-level map of the VR (Oculus-primary + SteamVR/OpenVR), rendering (D3D11/12, forward shading, InstancedStereo, NVIDIA Multi-Res, NvVolumetricLighting) and audio (Wwise + Oculus HRTF spatializer) middleware. Interface/wiring facts, no asset RE.
keywords: [vr, oculus, steamvr, openvr, hmd, stereo, forward shading, instancedstereo, multires, volumetric lighting, d3d11, d3d12, wwise, akaudio, spatializer, hrtf, audio, rendering]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E5]
---

# Rendering, Audio & VR Pipeline

How the client renders and sounds — at the **middleware-integration** level
(which SDKs, how wired). Client-local; no backend relevance. Documented for
completeness of "how the game works technically." We do not RE assets/shaders.

## VR / HMD

EVE Valkyrie is **VR-first**. HMD support (E2):
- **Oculus Rift** — the primary/dominant path (by far the most references;
  `LibOVR`/Oculus PC SDK; ships an Oculus client DLL and the Oculus audio
  spatializer). The game launched on Oculus Home first.
- **SteamVR / OpenVR** — secondary path (`openvr_api.dll`, `SteamVR`/`OpenVR`),
  enabling Vive and other OpenVR headsets via Steam.
- Stereo specifics: `Stereo`, `HMD`, `IPD`, `reprojection`/ASW. The `-vr` launch
  flag (`networking/05-*`) selects VR; `-nullrhi`/non-VR runs flat (for tools/
  dedicated server).

## Rendering

UE 4.14 rendering tuned for VR (E2):
- **RHI**: Direct3D **11** (default, static import) and **12** (opt-in, delay-
  loaded; `-d3d11`/`-d3d12` flags). OpenGL imported but D3D is the Windows path.
  A **Vulkan** RHI is also present (delay-loaded `vulkan-1.dll`, 106 imports;
  `binary/01-*`) — UE 4.14's experimental Vulkan, shipped but non-default.
- **Forward shading** (`ForwardShading`) — UE4's forward renderer, preferred for
  VR (MSAA + lower latency) over the default deferred path.
- **InstancedStereo** — single-pass stereo rendering (both eyes in one pass).
- **NVIDIA Multi-Res Shading** (`MultiRes`) — VR foveated-style perf optimization
  (renders periphery at lower res). Tobii foveation also feeds DoF (`03-*`).
- **NvVolumetricLighting** (GameWorks, ships `NvVolumetricLighting.win64.dll`) —
  volumetric light shafts.
- **MSAA** anti-aliasing (forward-renderer friendly).

## Audio

- **Wwise** (Audiokinetic) is the audio engine (`AkAudio`, `AkSoundEngine`) —
  the dominant audio middleware here, not UE4's native audio.
- **Oculus Spatializer for Wwise** (`OculusSpatializerWwise.dll`,
  `OculusSpatializer`) — **HRTF** 3D spatialization for VR positional audio.
- `VkAudioTrackedMeshRotation` and `UVkDynamicMusicMapSettings` (`05-*`) indicate
  spatialized, position-tracked sources and a dynamic/adaptive music system.

### Gameplay → audio integration (E2)

How gameplay drives audio (the code layer; sound assets/banks are out of scope):
- **Wwise API** via `UAkGameplayStatics` / `UAkComponent`: `PostEvent`
  (one-shot `AkAudioEvent`s — fire, explosion, hit), `SetRTPCValue` (continuous
  params — speed/boost/heat/health drive RTPCs), `SetState` + `SwitchGroup`
  (global/per-object state audio). `AkRTPCData`/`AkEventData` carry the bindings.
- **Game-state hook:** `UVkGameplayStatics::UpdateGameStateForAudio()` pushes
  match state (warmup/active/end, intensity) into Wwise states/RTPCs.
- **POV-aware:** `AkEventPOVData` selects 1P (cockpit) vs 3P event variants —
  mirroring the `…1P/3P` temporary effects (`gameplay/11`).
- **Voice-over:** `AkVoiceClipData` drives VO clips (the quick-chat speakers,
  `gameplay/12`), routed through Wwise.
- **Dynamic music:** `DynamicMusicComponent` + `DynamicMusicData`/`Settings`
  driven by a `DynamicMusicValue` **RTPC** (`DynamicMusicRTPCData`) — music
  intensity tracks gameplay (combat/objective tension). Configured per map via
  `UVkDynamicMusicMapSettings` (`05-*`).

All client-local; a preservation client runs the Wwise integration as shipped
(needs the shipped sound banks). No backend/server relevance.

## Relevance to preservation

None of this touches the backend — a server re-implementation needs nothing
here. It is documented so the technical picture is complete and to explain
binary artifacts (the shipped VR/audio/GameWorks DLLs, `Foveated*`/`MultiRes`/
`ForwardShading` cvars). For a preservation *client*, the VR/audio stack runs
exactly as shipped; only the network layer needs redirection.
