#!/usr/bin/env python3
"""
disasm_func.py — Capstone x64 disassembly of a function in the Vk client, with
RIP-relative reference annotation (UTF-16/ASCII string targets decoded inline).

Deeper than recover_object.py: shows the actual instructions, so you can read
logic (string/constant loads, calls, control flow) — for recovering algorithms
and the data a routine assembles. Clean-room: prints disassembly of the local
binary for analysis; distil findings into docs as prose, never commit raw output.

Requires capstone (installed in /home/agent/re-venv). Run with that python:
    /home/agent/re-venv/bin/python analysis/scripts/disasm_func.py 0x1420c6779 [nbytes]
The VA may be inside the function; we back up `back` bytes and disassemble
`back+nbytes`. Use a known xref VA (from recover_object.py) as the anchor.
"""
import sys, struct
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError:
    sys.exit("capstone not found — run with /home/agent/re-venv/bin/python")

EXE = "WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"

def load():
    f = open(EXE, "rb").read()
    pe = f.find(b"PE\0\0"); coff = pe + 4
    nsec, = struct.unpack_from("<H", f, coff + 2)
    optsz, = struct.unpack_from("<H", f, coff + 16)
    imagebase, = struct.unpack_from("<Q", f, coff + 20 + 24)
    sh = coff + 20 + optsz
    secs = []
    for i in range(nsec):
        o = sh + i*40
        name = f[o:o+8].rstrip(b"\0").decode("latin1")
        vsz, va, rawsz, raw = struct.unpack_from("<IIII", f, o+8)
        secs.append((name, imagebase+va, max(vsz, rawsz), raw, rawsz))
    return f, imagebase, secs

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    center = int(sys.argv[1], 0)
    nbytes = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x200
    back = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x40
    f, imagebase, secs = load()
    def va2off(v):
        for n, va, sz, raw, rawsz in secs:
            if va <= v < va+rawsz: return raw + (v-va)
        return None
    def read_str(v):
        o = va2off(v)
        if o is None: return None
        # try UTF-16LE then ASCII
        for enc, step in (("utf-16-le", 2), ("ascii", 1)):
            out = []
            for i in range(0, 160, step):
                if step == 2: ch = f[o+i] | (f[o+i+1] << 8)
                else: ch = f[o+i]
                if ch == 0: break
                if 32 <= ch < 127: out.append(chr(ch))
                else: out = []; break
            if len(out) >= 3: return ("w" if step==2 else "a", "".join(out))
        return None
    start = center - back
    o = va2off(start)
    if o is None: sys.exit("VA not in an initialized section")
    code = f[o:o+back+nbytes]
    md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
    for ins in md.disasm(code, start):
        ann = ""
        # annotate rip-relative memory operand targets
        if "rip" in ins.op_str:
            # target = address of next instruction + disp; capstone gives disp via operands
            for op in ins.operands:
                if op.type == 3 and op.mem.base != 0:  # X86_OP_MEM, base reg present
                    try:
                        if md.reg_name(op.mem.base) == "rip":
                            tgt = ins.address + ins.size + op.mem.disp
                            s = read_str(tgt)
                            ann = f"   ; ->{hex(tgt)}" + (f' "{s[1]}"({s[0]})' if s else "")
                    except Exception:
                        pass
        print(f"{ins.address:#x}: {ins.mnemonic:<7} {ins.op_str}{ann}")

if __name__ == "__main__":
    main()
