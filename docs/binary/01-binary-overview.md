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

## Where the interesting code is (E1 source-path mapping)

The build embeds 13k+ source-file path strings. Networking-relevant clusters:
- `VkGame/Source/VkRestUtils/Private/Vk*Resource.cpp` → REST client classes.
- `VkGame/Source/OnlineSubsystemVk/Private/Online*Vk.cpp` → online subsystem.
- `Engine/Plugins/Experimental/HTML5Networking/...` → WebSocket NetDriver.

See `networking/01-rest-backend.md` and `networking/02-websocket-netdriver.md`.

## Next analysis steps

- Parse `.pdata` → function table; correlate with `.rdata` string xrefs.
- Dump import table (which Win32 / Ws2_32 / crypt APIs are used).
- Extract UTF-16 strings (Windows often stores config keys/URLs as wide).
