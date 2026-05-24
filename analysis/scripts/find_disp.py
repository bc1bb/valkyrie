#!/usr/bin/env python3
"""find_disp.py — scan .text for instructions whose ModRM uses a disp32 equal to
a given value (e.g. struct field offset like 0x899). Prints VA + raw bytes so we
can spot reads/writes of obj+0xNNN. Usage: find_disp.py 0x899 [0x898 ...]
Heuristic: finds the 4-byte little-endian disp anywhere in code preceded by a
plausible ModRM with mod=10 (disp32). Reports context bytes; verify with disasm.
"""
import sys, struct
EXE = "WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
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
    secs.append((name, imagebase+va, vsz, raw, rawsz))
text = [s for s in secs if s[0] == ".text"][0]
tn, tva, tvsz, traw, trawsz = text
tb = f[traw:traw+trawsz]
for arg in sys.argv[1:]:
    disp = int(arg, 0)
    pat = struct.pack("<i", disp)
    print(f"=== disp {hex(disp)} ===")
    start = 0
    hits = 0
    while True:
        idx = tb.find(pat, start)
        if idx < 0: break
        start = idx + 1
        # ModRM byte is typically 1-2 bytes before disp (mod=10 => high bits 10xxxsss)
        # check the byte right before; mod field == 2 (0b10)
        modrm = tb[idx-1]
        if (modrm >> 6) == 2:
            va = tva + idx - 1
            # back up to show a few bytes of opcode context
            ctx = tb[idx-6:idx+4].hex()
            print(f"  VA~{hex(va)}  modrm={modrm:#04x}  ctx={ctx}")
            hits += 1
    if hits == 0:
        print("  (no mod=10 disp32 hits)")
