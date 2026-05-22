---
doc: engine-input
title: Input & Peripheral Subsystems
summary: Beyond gamepad/VR controllers, the client integrates DirectInput HOTAS flight sticks (Thrustmaster, axes/FFB/deadzones), TrackIR head tracking (NaturalPoint NPClient), and Tobii eye tracking (GTOM gaze-to-object + foveated rendering).
keywords: [input, peripherals, directinput, hotas, joystick, thrustmaster, trackir, naturalpoint, tobii, eyetracking, gaze, foveated, gamepad]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Input & Peripheral Subsystems

A space-combat VR title, EVE Valkyrie supports a wide input surface. These are
client-local subsystems (not networked); only the resulting player intent is
replicated via the gameplay RPCs (`networking/08-gameplay-replication.md`). All
ship as UE4 plugins (`engine/01-engine-identification.md`).

## Standard input

`Gamepad` and `Axis` mappings dominate (XInput pad, plus the VR controllers /
HMD). UE4's stock input pipeline handles these.

## DirectInput — HOTAS / flight sticks (`DirectInputPlugin`, E1/E2)

A dedicated plugin adds **DirectInput8** device support for joysticks/flight
sticks beyond XInput. Evidence (E2): `DirectInput`, `Joystick`,
`ForceFeedback`, `DeadZone`, and explicit **`Thrustmaster`** references (a HOTAS
brand) — so specific flight-stick hardware was recognized/profiled.

Capabilities indicated:
- Multi-**axis** input (pitch/roll/yaw/throttle) with per-axis **deadzone**.
- **Force feedback** (rumble/FFB effects on supported sticks).
- Device enumeration via the `IDirectInputDevice8` interface family.

Re-impl/preservation note: purely local; no backend dependency. Relevant only to
input fidelity, not server emulation.

## TrackIR — head tracking (`TrackIR` plugin, E1/E2)

Integrates **NaturalPoint TrackIR** via the **`NPClient`** SDK (`NaturalPoint`,
`HeadTracking`). Lets non-VR players use an IR head tracker to look around the
cockpit (head pose → camera/aim look). Local-only.

## Tobii — eye tracking (`TobiiEyetracking` plugin, E1/E2)

Ships its own DLLs (`Tobii.GameIntegration.dll`, `tobii_stream_engine.dll`) and
integrates the Tobii **GameIntegration** SDK. Features (E2):
- **Gaze** input and **GTOM** = *Gaze-To-Object-Mapping* (resolve what the
  player is looking at — e.g. target selection by gaze).
- **Foveated depth-of-field** (`FoveatedDepthOfFieldMode` + near-field
  tuning params) — render/post effects driven by gaze position.

Local-only; affects targeting UX and rendering, not networking.

## Why documented here

The project brief is "how the game works technically." These subsystems explain
input breadth and some console variables (`Foveated*`, deadzone, axis configs)
seen in the binary, and they bound what a preservation effort must *not* worry
about server-side: all peripheral handling is client-local. The single networked
consequence is that resolved intent (move/fire/target) flows through the
standard replication RPCs.
