#!/usr/bin/env python3
"""Scan .text for ANY instruction encoding the disp32 0x000019d0 and classify
read vs write by the opcode byte that precedes the ModRM. Prints VA + 12 bytes
of context so each hit can be confirmed with the disassembler.
"""
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
pat = struct.pack("<I", 0x19d0)
start = 0
WRITE = {0x88: "mov r/m8,r8", 0x89: "mov r/m,r", 0xc6: "mov r/m8,imm8", 0xc7: "mov r/m,imm32"}
READ = {0x8a: "mov r8,r/m8", 0x8b: "mov r,r/m", 0x0fb6: "movzx", 0x0fb7: "movzx16", 0x38: "cmp r/m8,r8", 0x3a: "cmp r8,r/m8", 0x80: "grp1 r/m8,imm8", 0x84: "test r/m8,r8"}
while True:
    idx = tb.find(pat, start)
    if idx < 0: break
    start = idx + 1
    modrm = tb[idx-1]
    if (modrm >> 6) != 2:  # need mod=10 (disp32)
        continue
    va = tva + idx - 1
    ctx = tb[idx-8:idx+4]
    # find opcode: walk back skipping rex/legacy prefixes
    # opcode is byte before modrm, or 0f-prefixed
    op = tb[idx-2]
    op0f = None
    if tb[idx-3] == 0x0f:
        op0f = (0x0f00 | op)
    rex = tb[idx-3]
    kind = "?"
    label = ""
    if op0f in READ:
        kind, label = "READ", READ[op0f]
    elif op in WRITE:
        kind, label = "WRITE", WRITE[op]
    elif op in READ:
        kind, label = "READ", READ[op]
    print(f"  VA~{hex(va)}  op={op:#04x} op0f={op0f}  modrm={modrm:#04x}  {kind:5} {label:14} ctx={ctx.hex()}")
