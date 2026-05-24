#!/usr/bin/env python3
"""find_wstr.py — locate UTF-16LE (and ASCII) string literals in the Vk client
and print their VA. Usage: find_wstr.py <substring> [<substring> ...]
Searches all initialized sections; prints section name, VA, and the decoded text.
Clean-room: prints offsets for analysis only.
"""
import sys, struct

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
        secs.append((name, imagebase+va, vsz, raw, rawsz))
    return f, secs

def main():
    f, secs = load()
    needles = sys.argv[1:]
    for needle in needles:
        wpat = needle.encode("utf-16-le")
        apat = needle.encode("ascii")
        print(f"=== '{needle}' ===")
        for enc, pat in (("w", wpat), ("a", apat)):
            start = 0
            while True:
                idx = f.find(pat, start)
                if idx < 0: break
                start = idx + 1
                # map raw offset to VA
                for name, va, vsz, raw, rawsz in secs:
                    if raw <= idx < raw + rawsz:
                        rva = va + (idx - raw)
                        # decode full string at this VA
                        step = 2 if enc == "w" else 1
                        out = []
                        j = idx
                        for _ in range(200):
                            if step == 2:
                                ch = f[j] | (f[j+1] << 8)
                            else:
                                ch = f[j]
                            if ch == 0: break
                            out.append(chr(ch) if 32 <= ch < 127 else ".")
                            j += step
                        print(f"  {enc} {name:<10} VA={hex(rva)}  \"{''.join(out)}\"")
                        break

if __name__ == "__main__":
    main()
