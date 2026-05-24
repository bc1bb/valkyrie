// vk_boot_patch — EVE: Valkyrie preservation boot patch (clean-room, our own code).
//
// The shipped client is VR-only. Run in 2D / no-VR against the clean-room private
// backend, its login state machine reaches "DOWNLOADING STATIC DATA" (state 2) and
// then waits on a secondary gate, the byte GameInstance+0x19d0, which is only set
// once the OnlineSubsystem completes a VR-platform login that never happens without
// a headset/runtime. So login times out ("A NETWORK ERROR HAS OCCURRED").
//
// This tool neutralises ONLY that one gate, in the LIVE PROCESS MEMORY (it never
// touches the game file on disk): at module RVA 0x6ec701 the state-2 handler has
//     je 0x1406ec75c        ; if [GameInstance+0x19d0]==0 -> timeout branch
// encoded as the two bytes  74 59 . Overwriting them with two NOPs (90 90) makes the
// handler fall through to "advance" once static data is done (the earlier static-data
// and minimum-dwell checks are left intact). Result: the client boots to its menu.
//
// It is fully reversible: `--revert` restores the original bytes in the running
// process, and since nothing on disk is modified, simply not running the tool (or
// restarting the game) reverts everything.
//
// Distribution note: ship THIS tool (our own code). Never redistribute the patched
// game or any game bytes. The tool verifies the original bytes before writing and
// no-ops on any build that does not match, so it cannot corrupt a different binary.
//
// Build (from a VS Developer environment so the MSVC linker is found):
//     rustc -O main.rs -o vk_boot_patch.exe
// Usage:
//     vk_boot_patch.exe            # wait for the game, apply the patch
//     vk_boot_patch.exe --revert   # restore the original bytes in the running game
//     vk_boot_patch.exe --timeout 300   # how long to wait for the process (s)

#![allow(non_snake_case, non_camel_case_types)]

use std::ffi::c_void;

type HANDLE = isize;
type BOOL = i32;

const TH32CS_SNAPPROCESS: u32 = 0x0000_0002;
const TH32CS_SNAPMODULE: u32 = 0x0000_0008;
const TH32CS_SNAPMODULE32: u32 = 0x0000_0010;
const INVALID_HANDLE_VALUE: HANDLE = -1;

const PROCESS_QUERY_INFORMATION: u32 = 0x0400;
const PROCESS_VM_OPERATION: u32 = 0x0008;
const PROCESS_VM_READ: u32 = 0x0010;
const PROCESS_VM_WRITE: u32 = 0x0020;
const PAGE_EXECUTE_READWRITE: u32 = 0x40;

// The single gate to neutralise. RVA is relative to the module's load base, so it is
// ASLR-safe (we add it to the runtime base of the main module).
const PATCH_RVA: usize = 0x6ec701;
const ORIG: [u8; 2] = [0x74, 0x59]; // je <timeout branch>
const NOPS: [u8; 2] = [0x90, 0x90]; // nop; nop

#[repr(C)]
struct PROCESSENTRY32W {
    dwSize: u32,
    cntUsage: u32,
    th32ProcessID: u32,
    th32DefaultHeapID: usize,
    th32ModuleID: u32,
    cntThreads: u32,
    th32ParentProcessID: u32,
    pcPriClassBase: i32,
    dwFlags: u32,
    szExeFile: [u16; 260],
}

#[repr(C)]
struct MODULEENTRY32W {
    dwSize: u32,
    th32ModuleID: u32,
    th32ProcessID: u32,
    GlblcntUsage: u32,
    ProccntUsage: u32,
    modBaseAddr: *mut u8,
    modBaseSize: u32,
    hModule: *mut c_void,
    szModule: [u16; 256],
    szExePath: [u16; 260],
}

#[link(name = "kernel32")]
extern "system" {
    fn CreateToolhelp32Snapshot(dwFlags: u32, th32ProcessID: u32) -> HANDLE;
    fn Process32FirstW(hSnapshot: HANDLE, lppe: *mut PROCESSENTRY32W) -> BOOL;
    fn Process32NextW(hSnapshot: HANDLE, lppe: *mut PROCESSENTRY32W) -> BOOL;
    fn Module32FirstW(hSnapshot: HANDLE, lpme: *mut MODULEENTRY32W) -> BOOL;
    fn OpenProcess(dwDesiredAccess: u32, bInheritHandle: BOOL, dwProcessId: u32) -> HANDLE;
    fn ReadProcessMemory(h: HANDLE, addr: *const c_void, buf: *mut c_void, n: usize, read: *mut usize) -> BOOL;
    fn WriteProcessMemory(h: HANDLE, addr: *mut c_void, buf: *const c_void, n: usize, wrote: *mut usize) -> BOOL;
    fn VirtualProtectEx(h: HANDLE, addr: *mut c_void, n: usize, newp: u32, oldp: *mut u32) -> BOOL;
    fn FlushInstructionCache(h: HANDLE, addr: *const c_void, n: usize) -> BOOL;
    fn CloseHandle(h: HANDLE) -> BOOL;
    fn GetLastError() -> u32;
    fn Sleep(ms: u32);
}

fn wlower_contains(name: &[u16], needle: &str) -> bool {
    let mut s = String::new();
    for &c in name {
        if c == 0 { break; }
        if let Some(ch) = char::from_u32(c as u32) { s.push(ch); }
    }
    s.to_lowercase().contains(needle)
}

// Find the first process whose image name contains "valkyrie" (case-insensitive).
fn find_pid() -> Option<u32> {
    unsafe {
        let snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snap == INVALID_HANDLE_VALUE { return None; }
        let mut pe: PROCESSENTRY32W = std::mem::zeroed();
        pe.dwSize = std::mem::size_of::<PROCESSENTRY32W>() as u32;
        let mut ok = Process32FirstW(snap, &mut pe);
        let mut found = None;
        while ok != 0 {
            if wlower_contains(&pe.szExeFile, "valkyrie") || wlower_contains(&pe.szExeFile, "warzone") {
                found = Some(pe.th32ProcessID);
                break;
            }
            ok = Process32NextW(snap, &mut pe);
        }
        CloseHandle(snap);
        found
    }
}

// Runtime base of the process's main module (the first entry of a module snapshot).
fn main_module_base(pid: u32) -> Option<usize> {
    unsafe {
        // module snapshots can fail transiently while a process is initialising
        for _ in 0..40 {
            let snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
            if snap != INVALID_HANDLE_VALUE {
                let mut me: MODULEENTRY32W = std::mem::zeroed();
                me.dwSize = std::mem::size_of::<MODULEENTRY32W>() as u32;
                if Module32FirstW(snap, &mut me) != 0 {
                    let base = me.modBaseAddr as usize;
                    CloseHandle(snap);
                    if base != 0 { return Some(base); }
                }
                CloseHandle(snap);
            }
            Sleep(100);
        }
        None
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let revert = args.iter().any(|a| a == "--revert");
    let mut timeout_s: u64 = 180;
    if let Some(i) = args.iter().position(|a| a == "--timeout") {
        if let Some(v) = args.get(i + 1) { if let Ok(n) = v.parse() { timeout_s = n; } }
    }

    println!("vk_boot_patch — {} the GameInstance+0x19d0 login gate (live memory, reversible)",
             if revert { "REVERT" } else { "apply" });
    println!("waiting up to {}s for the game process (launch it via Steam now if not running)...", timeout_s);

    // poll for the process
    let mut pid = None;
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(timeout_s);
    while std::time::Instant::now() < deadline {
        pid = find_pid();
        if pid.is_some() { break; }
        unsafe { Sleep(500); }
    }
    let pid = match pid {
        Some(p) => { println!("found game pid {}", p); p }
        None => { eprintln!("ERROR: game process not found within timeout."); std::process::exit(2); }
    };

    let base = match main_module_base(pid) {
        Some(b) => { println!("main module base = {:#x}", b); b }
        None => { eprintln!("ERROR: could not read main module base."); std::process::exit(3); }
    };
    let addr = base + PATCH_RVA;
    println!("patch site = {:#x} (base + {:#x})", addr, PATCH_RVA);

    unsafe {
        let h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, 0, pid);
        if h == 0 {
            eprintln!("ERROR: OpenProcess failed (GetLastError={}). Try running as the same user as the game.", GetLastError());
            std::process::exit(4);
        }

        let mut cur = [0u8; 2];
        let mut nread = 0usize;
        if ReadProcessMemory(h, addr as *const c_void, cur.as_mut_ptr() as *mut c_void, 2, &mut nread) == 0 || nread != 2 {
            eprintln!("ERROR: ReadProcessMemory failed (GetLastError={}).", GetLastError());
            CloseHandle(h); std::process::exit(5);
        }
        println!("current bytes at patch site: {:02x} {:02x}", cur[0], cur[1]);

        let (want, write): (&[u8; 2], &[u8; 2]) = if revert { (&NOPS, &ORIG) } else { (&ORIG, &NOPS) };

        if cur == *write {
            println!("already in the desired state ({} present). Nothing to do.",
                     if revert { "original bytes" } else { "NOPs" });
            CloseHandle(h); return;
        }
        if cur != *want {
            eprintln!("ABORT: bytes are neither the expected original ({:02x} {:02x}) nor the patched ({:02x} {:02x}).",
                      ORIG[0], ORIG[1], NOPS[0], NOPS[1]);
            eprintln!("       This is likely a different game build. Refusing to write so nothing is corrupted.");
            CloseHandle(h); std::process::exit(6);
        }

        let mut oldp = 0u32;
        if VirtualProtectEx(h, addr as *mut c_void, 2, PAGE_EXECUTE_READWRITE, &mut oldp) == 0 {
            eprintln!("ERROR: VirtualProtectEx failed (GetLastError={}).", GetLastError());
            CloseHandle(h); std::process::exit(7);
        }
        let mut nwrote = 0usize;
        let ok = WriteProcessMemory(h, addr as *mut c_void, write.as_ptr() as *const c_void, 2, &mut nwrote);
        let mut tmp = 0u32;
        VirtualProtectEx(h, addr as *mut c_void, 2, oldp, &mut tmp); // restore page protection
        FlushInstructionCache(h, addr as *const c_void, 2);
        if ok == 0 || nwrote != 2 {
            eprintln!("ERROR: WriteProcessMemory failed (GetLastError={}).", GetLastError());
            CloseHandle(h); std::process::exit(8);
        }
        CloseHandle(h);
        println!("OK: wrote {:02x} {:02x}. {}", write[0], write[1],
                 if revert { "Gate restored." } else { "Gate neutralised — login should advance to the menu." });
    }
}
