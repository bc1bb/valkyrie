#!/usr/bin/env python3
"""read_f32.py — read float32 constants at given VAs. Usage: read_f32.py 0x1427ce048 ..."""
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
def va2off(v):
    for n, va, vsz, raw, rawsz in secs:
        if va <= v < va+rawsz: return raw + (v-va)
    return None
for a in sys.argv[1:]:
    v = int(a, 0); o = va2off(v)
    if o is None: print(v, "n/a"); continue
    f32, = struct.unpack_from("<f", f, o)
    f32b, = struct.unpack_from("<f", f, o+4)
    print(f"{hex(v)}: f32={f32}  next={f32b}")
