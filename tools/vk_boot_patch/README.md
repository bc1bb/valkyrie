# vk_boot_patch — EVE: Valkyrie 2D boot patch (clean-room, reversible)

A tiny, dependency-free Windows tool that lets the **shipped EVE: Valkyrie – Warzone
client boot to its main menu in 2D / no-VR** against the clean-room private backend
(`docs/reimpl/mvp-server`). It is our own code; it ships no game bytes.

## Why this is needed

The client is VR-only. Run without a headset (2D mode), its login state machine reaches
**"DOWNLOADING STATIC DATA"** and then blocks on a secondary gate — the byte
`GameInstance+0x19d0`. That byte is only set after the store/catalog subsystem ticks,
which is driven by the **OnlineSubsystem completing a VR-platform login that never
happens without a headset/runtime**. So login times out: *"A NETWORK ERROR HAS OCCURRED."*
Full analysis: `docs/reimpl/04-live-bringup-log.md` (Sessions 4–5) and
`docs/reimpl/07-gameinstance-storedata-gate.md`. There is **no server-side fix** — the
missing trigger is client/platform-side — so a minimal client-side nudge is the
realistic preservation path.

## What it does (and does NOT do)

- Neutralises **only** that one gate, in **live process memory** (it never modifies the
  game file on disk). At main-module RVA `0x6ec701` the state-2 handler has
  `je <timeout>` (bytes `74 59`); the tool overwrites it with two NOPs (`90 90`) so the
  handler falls through to "advance" once static data is done. The earlier static-data
  and minimum-dwell checks are left intact.
- Verifies the original bytes before writing and **refuses to write** on any build that
  doesn't match — it cannot corrupt a different binary.
- Fully reversible: `--revert` restores the original bytes in the running process; and
  because nothing on disk is changed, simply not running the tool (or restarting the
  game) reverts everything.

## Usage

```
vk_boot_patch.exe                 # wait for the game, then apply the patch
vk_boot_patch.exe --revert        # restore the original bytes in the running game
vk_boot_patch.exe --timeout 300   # seconds to wait for the process (default 180)
```

Run it as the **same Windows user** as the game (no admin needed). It polls for the
game process and patches it within ~1 s of launch — well before login reaches the gate,
so start it before or right after launching the game.

## Full boot recipe (2D, no VR)

1. `OPENSSL_ia32cap=:~0x20000000` in the environment (user env var; fixes the 2017
   OpenSSL SHA-NI crash on modern CPUs — restart Steam after setting).
2. Redirect the backend hosts to `127.0.0.1` and trust a local CA covering
   `login.eveonline.com`, `vkpilot.live-valkyrieapi.com`, `vgs-tq.eveonline.com`
   (see `docs/reimpl/mvp-server`).
3. Run the backend: `VK_PORT=443 VK_BASE=https://vkpilot.live-valkyrieapi.com VK_TLS_MAX=1.2 python server.py`.
4. Run `vk_boot_patch.exe`.
5. Launch the game via Steam (`steam://rungameid/688480`).

The client logs in and reaches the main menu (verified: store-offers + hero_survival
fetched, menu rendered, stable). Screenshot evidence: `mvp-server/logs/menu_via_patcher.png`.

## Build

Requires the Rust toolchain and the MSVC linker (Visual Studio / Build Tools). From a
VS Developer environment:

```
rustc -O main.rs -o vk_boot_patch.exe
```

No external crates — raw Win32 FFI (toolhelp snapshot + `OpenProcess`/`ReadProcessMemory`/
`VirtualProtectEx`/`WriteProcessMemory`). Single static `.exe`, ~164 KB.

## Distribution & legal

Distribute **only this tool** (source + the `.exe` we build). **Never** redistribute the
game or any patched game binary/bytes — the patch lives in memory at runtime and is keyed
to a verified byte pattern. This is a documented, reversible preservation aid for a
title you own, to play it in 2D on hardware without VR.

## Known follow-up (not a login issue)

After reaching the menu the client has been observed to auto-close after a few minutes
with no crash dump — likely the new-player/avatar flow expecting VR input. Separate from
the login gate; to be investigated when exercising the menu.
