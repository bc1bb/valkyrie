#!/usr/bin/env python3
"""
recover_object.py — clean-room structure recovery for the Vk client (PE x64).

Given an anchor UTF-16 string (a field/path the game uses), find the request/
parse routine that references it and dump the ordered set of *other* string
constants that routine loads (via RIP-relative `lea`). The order/grouping
reveals a resource's JSON field set — the technique behind docs/networking/13-*.

This tool reads ONLY the local shipped binary and prints field-NAME identifiers
(interface facts) to stdout. It writes nothing into the repo; pipe output to
analysis/raw/ (git-ignored) if you want to keep it. No copyrighted bytes leave
the binary.

Usage:
    analysis/scripts/recover_object.py "<anchor string>" [window_back] [window_fwd]
Examples:
    analysis/scripts/recover_object.py has_set_gender          # pilot object
    analysis/scripts/recover_object.py owner_callsign          # session object
    analysis/scripts/recover_object.py grant_type=steam_ticket # SSO body builder

Notes:
  * Anchor must be reasonably unique; very common short strings (e.g. "verb")
    have many copies and many xrefs -> slow. Prefer a distinctive field.
  * Verbs (GET/PUT/POST) are uppercase; pass --verbs to include them.
"""
import sys, struct, re

EXE = "WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"

def load_pe(path):
    f = open(path, "rb").read()
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
        secs.append((name, va, vsz, raw, rawsz))
    return f, imagebase, secs

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    anchor = sys.argv[1]
    # int(x, 0) accepts decimal or 0x-hex window sizes
    back = int(sys.argv[2], 0) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 0xC00
    fwd  = int(sys.argv[3], 0) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else 0x400
    want_verbs = "--verbs" in sys.argv

    f, imagebase, secs = load_pe(EXE)
    text = next(s for s in secs if s[0] == ".text")
    tname, tva, tvsz, traw, trawsz = text
    textVA = imagebase + tva
    tb = f[traw:traw + trawsz]

    def va2off(v):
        for n, va, vsz, raw, rawsz in secs:
            s = imagebase + va
            if s <= v < s + rawsz: return raw + (v - s)
        return None
    def off2va(o):
        for n, va, vsz, raw, rawsz in secs:
            if raw <= o < raw + rawsz: return imagebase + va + (o - raw)
        return None
    def read_w(v, maxlen=80):
        o = va2off(v)
        if o is None: return None
        out = []
        for i in range(0, maxlen*2, 2):
            ch = f[o+i] | (f[o+i+1] << 8)
            if ch == 0: break
            if 32 <= ch < 127: out.append(chr(ch))
            else: return None
        return "".join(out)

    # locate anchor (UTF-16LE) VAs
    w = anchor.encode("utf-16-le"); locs = []; i = f.find(w)
    while i != -1:
        locs.append(off2va(i)); i = f.find(w, i + 1)
    locs = [v for v in locs if v]
    if not locs:
        print(f"anchor not found (utf-16): {anchor!r}"); sys.exit(2)

    # single pass: for each anchor VA, find xref instruction(s)
    field_re = re.compile(r"[a-z][a-z0-9_]{1,40}")
    verb_re  = re.compile(r"(GET|PUT|POST|DELETE|PATCH)")
    for av in locs:
        refs = []
        for p in range(len(tb) - 4):
            d = av - (textVA + p + 4)
            if -0x80000000 <= d <= 0x7fffffff and \
               tb[p] == (d & 0xff) and tb[p+1] == ((d>>8)&0xff) and \
               tb[p+2] == ((d>>16)&0xff) and tb[p+3] == ((d>>24)&0xff):
                refs.append(textVA + p)
        for x in refs:
            o = va2off(x - back); seq = []
            for i in range(back + fwd):
                p = o + i
                if f[p] in (0x48, 0x4c) and f[p+1] == 0x8d and (f[p+2] & 0xc7) == 0x05:
                    disp = struct.unpack_from("<i", f, p+3)[0]
                    s = read_w(off2va(p) + 7 + disp)
                    if not s: continue
                    if field_re.fullmatch(s) or (want_verbs and verb_re.fullmatch(s)):
                        seq.append(s)
            seen = set(); ordered = [s for s in seq if not (s in seen or seen.add(s))]
            print(f"# anchor {anchor!r} @ xref {hex(x)} ({len(ordered)} fields)")
            print("  " + ", ".join(ordered))

if __name__ == "__main__":
    main()
