#!/usr/bin/env python3
"""
parse_minidump.py — extract the crash essentials from a Windows minidump (.dmp).

Clean-room tool: prints the exception context (code, faulting access + address,
registers), maps the fault RIP and candidate stack return-addresses to module+RVA,
and lists loaded modules. No copyrighted bytes are emitted — only addresses and
module names derived from a crash of the locally-held binary. Distil findings into
docs as prose; do not commit raw output.

Usage: python analysis/scripts/parse_minidump.py <dump.dmp> [main_module_substr]
"""
import sys, struct

CTX = {  # x64 CONTEXT register offsets
    "Rax":0x78,"Rcx":0x80,"Rdx":0x88,"Rbx":0x90,"Rsp":0x98,"Rbp":0xA0,
    "Rsi":0xA8,"Rdi":0xB0,"R8":0xB8,"R9":0xC0,"R10":0xC8,"R11":0xD0,
    "R12":0xD8,"R13":0xE0,"R14":0xE8,"R15":0xF0,"Rip":0xF8,
}

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    data = open(sys.argv[1], "rb").read()
    want = (sys.argv[2] if len(sys.argv) > 2 else "Valkyrie").lower()
    assert data[:4] == b"MDMP", "not a minidump"
    nstreams, dir_rva = struct.unpack_from("<II", data, 8)
    streams = {}
    for i in range(nstreams):
        t, sz, rva = struct.unpack_from("<III", data, dir_rva + i*12)
        streams.setdefault(t, (sz, rva))

    # --- modules (type 4) ---
    modules = []  # (base, size, name)
    if 4 in streams:
        _, rva = streams[4]
        n, = struct.unpack_from("<I", data, rva); o = rva + 4
        for _ in range(n):
            base, size = struct.unpack_from("<QI", data, o)
            name_rva, = struct.unpack_from("<I", data, o+20)
            slen, = struct.unpack_from("<I", data, name_rva)
            name = data[name_rva+4:name_rva+4+slen].decode("utf-16-le", "replace")
            modules.append((base, size, name.split("\\")[-1]))
            o += 108
    modules.sort()
    def whichmod(addr):
        for base, size, name in modules:
            if base <= addr < base+size: return f"{name}+0x{addr-base:x}"
        return None
    main_mod = next((m for m in modules if want in m[2].lower()), None)

    # --- exception (type 6) ---
    if 6 not in streams:
        print("no exception stream");
    else:
        _, rva = streams[6]
        tid, = struct.unpack_from("<I", data, rva)
        er = rva + 8
        code, flags, _rec, addr, nparam = struct.unpack_from("<IIQQI", data, er)
        # ExceptionInformation[] starts at er+32 (after NumberParameters + __unusedAlignment)
        info = [struct.unpack_from("<Q", data, er+32+8*k)[0] for k in range(min(nparam,15))]
        ctx_sz, ctx_rva = struct.unpack_from("<II", data, er + 32 + 15*8)
        print(f"=== EXCEPTION ===")
        print(f"thread {tid}  code=0x{code:08x}  address=0x{addr:x}  ({whichmod(addr)})")
        if nparam >= 2:
            acc = {0:'READ',1:'WRITE',8:'EXECUTE'}.get(info[0], info[0])
            print(f"access={acc}  faulting_data_address=0x{info[1]:x}")
        regs = {r: struct.unpack_from("<Q", data, ctx_rva+off)[0] for r,off in CTX.items()}
        for r in ("Rip","Rsp","Rbp","Rax","Rcx","Rdx","Rbx","Rsi","Rdi","R8","R9"):
            print(f"  {r}=0x{regs[r]:x}")
        rsp = regs["Rsp"]

        # --- stack scan via Memory64List (type 9) ---
        ranges = []
        if 9 in streams:
            _, mrva = streams[9]
            nr, base_rva = struct.unpack_from("<QQ", data, mrva)
            o = mrva + 16; cur = base_rva
            for _ in range(nr):
                start, dsz = struct.unpack_from("<QQ", data, o); o += 16
                ranges.append((start, dsz, cur)); cur += dsz
        def read_mem(va, n):
            for start, dsz, frva in ranges:
                if start <= va < start+dsz:
                    off = frva + (va-start); return data[off:off+min(n, start+dsz-va)]
            return b""
        print(f"=== STACK return-address candidates (scan from Rsp) ===")
        stack = read_mem(rsp, 0x800)
        seen = set()
        if main_mod:
            lo, hi = main_mod[0], main_mod[0]+main_mod[1]
            for k in range(0, len(stack)-8, 8):
                v, = struct.unpack_from("<Q", stack, k)
                if lo <= v < hi and v not in seen:
                    seen.add(v); print(f"  [rsp+0x{k:03x}] 0x{v:x}  {main_mod[2]}+0x{v-lo:x}")

    print(f"=== MODULES ({len(modules)}) — net/tls/steam of interest ===")
    for base, size, name in modules:
        if any(s in name.lower() for s in ("steam","ssl","crypt","curl","wininet","winhttp","ws2","openvr","oculus","ovr","vrclient")):
            print(f"  0x{base:x}  {name}")

if __name__ == "__main__":
    main()
