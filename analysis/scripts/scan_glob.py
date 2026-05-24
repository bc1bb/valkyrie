#!/usr/bin/env python3
"""Find rip-relative refs to an absolute VA by brute-forcing the disp32 bytes.
For each .text byte position we treat the 4 bytes as a candidate disp32 and, for
plausible instruction-end positions (disp end + 0/1/4 imm bytes), check whether
rip+disp == target. Prints VA of the disp field with context so each can be
confirmed in the disassembler."""
import struct, sys
EXE = r"E:\valkyrie\WindowsNoEditor\VkGame\Binaries\Win64\EVE Valkyrie - Warzone.exe"
target = int(sys.argv[1], 0)
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
tn, tva, tvsz, traw, trawsz = [s for s in secs if s[0] == ".text"][0]
tb = f[traw:traw+trawsz]
for idx in range(len(tb)-4):
    disp = struct.unpack_from("<i", tb, idx)[0]
    # instruction ends at disp_field_end (idx+4) plus tail immediate bytes
    for tail in (0,1,2,4):
        ripbase = tva + idx + 4 + tail
        if ripbase + disp == target:
            dva = tva + idx
            ctx = tb[max(0,idx-3):idx+4+tail]
            print(f"  disp@{hex(dva)} (instr_end+{tail}) ctx={ctx.hex()}")
            break
