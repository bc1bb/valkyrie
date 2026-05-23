---
doc: binary-overview
title: Client Binary Overview
summary: PE32+ x64 shipping client — section layout, build metadata, embedded toolchain/libs, where networking code lives.
keywords: [pe, binary, exe, sections, objdump, sha256, shipping, x64]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Client Binary Overview

## Identity

- Path: `WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe`
- Format: PE32+ (GUI) x86-64, 9 sections.
- Size: 62,423,552 bytes.
- SHA-256: `d79707fd01d9b17f0aba8cbc5722b4e9a9b244158e8d95db683beec461e5d781`
- Entry point VA: `0x1425f20dc`. Image base `0x140000000`.
- Manifest also references `VkGame-Win64-Shipping.exe` + a `.pdb`; on this
  Steam install the binary is renamed to the display name and **no PDB ships**.
  (A PDB, if ever located, would massively accelerate documentation — symbols.)

## Section table (objdump, E1)

| Idx | Name | Virtual size | VMA | Notes |
|----:|------|-------------:|-----|-------|
| 0 | `.text`   | 0x02781e8c (~41 MB) | 0x140001000 | Code. Monolithic UE4 shipping build. |
| 1 | `.rdata`  | 0x00ea307a (~15 MB) | 0x142783000 | Read-only data: strings, vtables, RTTI. |
| 2 | `.data`   | 0x00225a00 | 0x143627000 | Mutable globals. |
| 3 | `.pdata`  | 0x00238ecc | 0x143af2000 | x64 exception unwind info (fn boundaries!). |
| 4 | `.tls`    | 0x0000001d | 0x143d2b000 | Thread-local storage. |
| 5 | `.gfids`  | 0x00000038 | 0x143d2c000 | Control-Flow-Guard function ids. |
| 6 | `_RDATA`  | 0x00008b50 | 0x143d2d000 | Extra read-only data. |
| 7 | `.rsrc`   | 0x00029040 | 0x143d36000 | Win32 resources (icons, version info). |
| 8 | `.reloc`  | 0x000d1c3c | 0x143d60000 | Base relocations. |

`.pdata` is useful: it enumerates function start addresses, giving a clean
function inventory without a disassembler heuristic pass.

## Embedded toolchain / library fingerprints (E2)

- Statically linked: **libcurl**, **OpenSSL**, **libwebsockets** (all confirmed
  via version/format strings). These three are the entire userland network
  stack for backend comms; UE4's own socket layer handles game replication.
- Built with MSVC (VS2015 toolset, matching shipped PhysX `VS2015` dirs).

## Import table — OS-level dependency surface (E1)

The PE import directory (parsed via `pefile`) is the authoritative list of OS/
middleware APIs the client calls. Highlights for the technical picture:

**Network (static imports):**
- **`WS2_32.dll` (42 fns)** — Winsock: full BSD socket set (`socket`/`bind`/
  `connect`/`send`/`recv`, UDP `sendto`/`recvfrom`, TCP `listen`/`accept`) plus
  **event-based async I/O** (`WSAEventSelect`, `WSAEnumNetworkEvents`,
  `WSAWaitForMultipleEvents`) and both `gethostbyname` **and** `getaddrinfo`/
  `inet_pton`/`inet_ntop` (IPv4+IPv6). This is the real transport floor under
  both libwebsockets (game replication, `networking/02-*`) and libcurl.
- **`WININET.dll` (13 fns)** — a complete WinINet HTTP client (`InternetOpenW`/
  `HttpOpenRequestW`/`HttpSendRequestW`, all wide-char). **Refines** the HTTP
  picture: alongside the statically-linked **libcurl** used by `VkRestUtils`
  (`networking/01-*`), UE 4.14's stock HTTP module on Windows is WinINet-backed —
  so engine-level HTTP (e.g. the Epic telemetry DataRouter, `networking/07-*`)
  can ride WinINet while the VGS REST client rides libcurl. Two HTTP paths
  coexist.
- **`WINHTTP.dll` (2 fns)** — only `WinHttpGetIEProxyConfigForCurrentUser` /
  `…DefaultProxyConfiguration`: **proxy auto-detection** (read IE/system proxy),
  not a third HTTP client.
- **`IPHLPAPI.DLL`** — `GetAdaptersInfo`/`GetAdaptersAddresses`: network-adapter/
  MAC enumeration (machine fingerprint / telemetry device id).
- **`Secur32.dll`** — `GetUserNameExW` (OS account name).

**Crash/diagnostics:** `dbghelp.dll` (11 fns) — UE4 crash handler / minidump.

**Delay-loaded (loaded on demand) — reveals optional subsystems:**
- **`vulkan-1.dll` (106 fns)** — a **Vulkan RHI** is present (delay-loaded),
  beyond the D3D11/12 + OpenGL noted in `engine/06-*`. UE 4.14's Vulkan was
  experimental; it ships but is not the default Windows path.
- **`d3d12.dll`** delay-loaded — D3D12 is the opt-in path (`-d3d12`); D3D11 is
  default-linked statically.
- **`MF.dll` / `MFPlat.DLL`** — **Media Foundation**: this is how the cooked
  intro `.mp4`s (`Generic_Launch_SEQ`, `Introduction_Cinematic`) play back
  (UE4 `MediaFoundation` player).
- **`LibOVRPlatform64_1.dll` (40 fns)** — **Oculus Platform SDK** (entitlement /
  identity / IAP / rooms), distinct from the Oculus *rendering* SDK — feeds the
  `VkOculusPlatform` OSS path (`networking/07-*`).
- **`steam_api64.dll` (22)**, **`hmd_client.dll` (8)**, **`openvr_api.dll` (4)**,
  **PhysX/APEX**, **`NvVolumetricLighting`**, **`libvorbisfile_64`**,
  **Tobii** — match the shipped middleware (`binary/02-*`).

**Local audio/input fallbacks (static):** `DSOUND.dll`, `X3DAudio1_7.dll`,
`XAPOFX1_5.dll` (XAudio2/DirectSound), `XINPUT1_3.dll` (gamepad), `DINPUT8.dll`
(HOTAS, `engine/03-*`), `WINMM.dll`.

libcurl's classic Windows dependency fingerprint is also visible in the static
imports (`WLDAP32.dll`, `Normaliz.dll` for IDN) — corroborating the libcurl link
from `binary/01` string evidence.

## Where the interesting code is (E1 source-path mapping)

The build embeds 13k+ source-file path strings. Networking-relevant clusters:
- `VkGame/Source/VkRestUtils/Private/Vk*Resource.cpp` → REST client classes.
- `VkGame/Source/OnlineSubsystemVk/Private/Online*Vk.cpp` → online subsystem.
- `Engine/Plugins/Experimental/HTML5Networking/...` → WebSocket NetDriver.

See `networking/01-rest-backend.md` and `networking/02-websocket-netdriver.md`.

## Next analysis steps

- Parse `.pdata` → function table; correlate with `.rdata` string xrefs.
- ~~Dump import table~~ — **done** (see *Import table* above).
- Extract UTF-16 strings (Windows often stores config keys/URLs as wide) —
  largely done via `analysis/scripts/recover_object.py` (`networking/13-*`).
