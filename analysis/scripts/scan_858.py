#!/usr/bin/env python3
"""Scan .text for disp32 0x00000858 used as ModRM disp32; classify read/write."""
import struct
EXE = r"E:\valkyrie\WindowsNoEditor\VkGame\Binaries\Win64\EVE Valkyrie - Warzone.exe"
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
import sys
target = int(sys.argv[1],0) if len(sys.argv)>1 else 0x858
pat = struct.pack("<I", target)
start = 0
WRITE = {0x88: "mov r/m8,r8", 0x89: "mov r/m,r", 0xc6: "mov r/m8,imm8", 0xc7: "mov r/m,imm32"}
READ = {0x8a: "mov r8,r/m8", 0x8b: "mov r,r/m", 0x38: "cmp r/m8,r8", 0x3a: "cmp r8,r/m8", 0x80: "grp1 r/m8,imm8", 0x84: "test r/m8,r8", 0x39:"cmp r/m,r", 0x3b:"cmp r,r/m", 0x83:"grp1 r/m,imm8", 0x81:"grp1 r/m,imm32"}
while True:
    idx = tb.find(pat, start)
    if idx < 0: break
    start = idx + 1
    modrm = tb[idx-1]
    if (modrm >> 6) != 2:
        continue
    va = tva + idx - 1
    ctx = tb[idx-8:idx+4]
    op = tb[idx-2]
    op0f = (0x0f00 | op) if tb[idx-3] == 0x0f else None
    kind = "?"; label = ""
    if op0f in READ: kind, label = "READ", READ[op0f]
    elif op in WRITE: kind, label = "WRITE", WRITE[op]
    elif op in READ: kind, label = "READ", READ[op]
    print(f"  VA~{hex(va)}  op={op:#04x} modrm={modrm:#04x}  {kind:5} {label:14} ctx={ctx.hex()}")
