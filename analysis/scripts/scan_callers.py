#!/usr/bin/env python3
import struct, sys
EXE = "WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
f = open(EXE, "rb").read()
pe = f.find(b"PE\0\0"); coff = pe + 4
nsec, = struct.unpack_from("<H", f, coff + 2)
optsz, = struct.unpack_from("<H", f, coff + 16)
imagebase, = struct.unpack_from("<Q", f, coff + 20 + 24)
sh = coff + 20 + optsz
secs = []
for i in range(nsec):
    o = sh + i * 40
    name = f[o:o+8].rstrip(b"\0").decode("latin1")
    vsz, va, rawsz, raw = struct.unpack_from("<IIII", f, o + 8)
    secs.append((name, imagebase + va, vsz, raw, rawsz))
text = [s for s in secs if s[0] == ".text"][0]
tn, tva, tvsz, traw, trawsz = text
tb = f[traw:traw + trawsz]
def off2va(o): return tva + o  # o is index into tb (already sliced from traw)

# targets passed as hex args; find E8 call rel32 and also lea reg,[rip+x] loads of those VAs
targets = [int(a, 0) for a in sys.argv[1:]]
for tgt in targets:
    callers = []
    leas = []
    for p in range(len(tb) - 7):
        if tb[p] == 0xE8:
            d = struct.unpack_from("<i", tb, p + 1)[0]
            if off2va(p) + 5 + d == tgt:
                callers.append(off2va(p))
        # lea r64,[rip+disp32]: REX.W (48/4c) 8D /r mod=00 rm=101
        if tb[p] in (0x48, 0x4c) and tb[p+1] == 0x8d and (tb[p+2] & 0xc7) == 0x05:
            disp = struct.unpack_from("<i", tb, p + 3)[0]
            if off2va(p) + 7 + disp == tgt:
                leas.append(off2va(p))
    print("target", hex(tgt))
    print("  E8 callers:", [hex(h) for h in callers])
    print("  lea-loads :", [hex(h) for h in leas])
