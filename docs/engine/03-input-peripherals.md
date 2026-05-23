---
doc: engine-input
title: Input & Peripheral Subsystems
summary: Beyond gamepad/VR controllers, the client integrates DirectInput HOTAS flight sticks (Thrustmaster, axes/FFB/deadzones), TrackIR head tracking (NaturalPoint NPClient), and Tobii eye tracking (GTOM gaze-to-object + foveated rendering).
keywords: [input, peripherals, directinput, hotas, joystick, thrustmaster, trackir, naturalpoint, tobii, eyetracking, gaze, foveated, gamepad]
status: draft
updated: 2026-05-23
evidence: [E1, E2]
---

# Input & Peripheral Subsystems

A space-combat VR title, EVE Valkyrie supports a wide input surface. These are
client-local subsystems (not networked); only the resulting player intent is
replicated via the gameplay RPCs (`networking/08-gameplay-replication.md`). All
ship as UE4 plugins (`engine/01-engine-identification.md`).

## Standard input

`Gamepad` and `Axis` mappings dominate (XInput pad, plus the VR controllers /
HMD). UE4's stock input pipeline handles these. Supported device classes:
`EVkSupportedInputTypes` = **Gamepad, Joystick, MotionController,
MouseAndKeyboard**.

## Input action map (`EVR_*`, E2)

The control scheme — the abstract input actions (mapped to devices via UE4 input
bindings; actions drive the gameplay RPCs in `networking/08-*`):

| Group | Actions |
|-------|---------|
| **Flight axes** | `EVR_Pitch`, `EVR_Yaw`, `EVR_Roll` (+ mouse `EVR_MousePitch/Yaw/Roll`) |
| **Speed** | `EVR_Boost`, `EVR_Brake` |
| **Combat** | `EVR_Fire1`, `EVR_Fire2`, `EVR_Target` (lock/cycle) |
| **Abilities** | `EVR_Ability`, `EVR_Ability2`, `EVR_Ultimate`, `EVR_CallIn` |
| **VR look / camera** | `EVR_HeadPitch`/`EVR_HeadYaw` (HMD aim), `EVR_MouseHeadPitch/Yaw` (non-VR head-look), `EVR_FreeLook`, `EVR_ResetHMD` (recenter), `EVR_ToggleCameraMode` |
| **Comms (wheel)** | `EVR_QuickChatMenu`, `EVR_QuickChatSelectX`/`Y` (+ mouse variants) |
| **System** | `EVR_Pause` (+ `EVR_PausePS4`), `EVR_Escalator` (menu/hangar nav) |

Note the **mouse variants** of head-look/rotation/quick-chat: the game is
playable flat (non-VR) with mouse+keyboard, mapping mouse to HMD-look. Platform
pause variant (`PausePS4`) reflects the original console/PS4 build.

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
  player is looking at — e.g. target selection by gaze). GTOM **scores** each
  candidate object by its distance from the **center gaze ray**, decaying with
  distance down to a floor (E2: "*each extra score … decayed … depending on its
  distance from the center ray; the score cannot drop below this amount*"); the
  highest-scoring object is the gaze target. A debug cvar visualizes GTOM scores.
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
