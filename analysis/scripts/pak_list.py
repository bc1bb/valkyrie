#!/usr/bin/env python3
"""
pak_list.py — list the file index of an unencrypted UE4 v3 .pak WITHOUT extracting
the whole archive. Reads the footer (IndexOffset/IndexSize), parses the index
(mount point + per-entry filename + FPakEntry), and prints filenames, optionally
filtered by substring. Lets us discover the static-data DataTable asset paths the
client ships with (a reliable source for real unique-names/structure).

Clean-room: lists asset PATHS/NAMES from the locally-held pak; extracts nothing
copyrighted. Usage: python analysis/scripts/pak_list.py [filter1 filter2 ...]
"""
import struct, sys, os

PAK = r"WindowsNoEditor/VkGame/Content/Paks/VkGame-WindowsNoEditor.pak"
MAGIC = 0x5A6F12E1

def fstring(buf, o):
    (n,) = struct.unpack_from("<i", buf, o); o += 4
    if n == 0:
        return "", o
    if n > 0:                              # ASCII (n includes null term)
        s = buf[o:o + n - 1].decode("latin1", "replace"); o += n
    else:                                  # UTF-16LE
        n = -n
        s = buf[o:o + n * 2 - 2].decode("utf-16-le", "replace"); o += n * 2
    return s, o

def main():
    filters = [a.lower() for a in sys.argv[1:]]
    sz = os.path.getsize(PAK)
    with open(PAK, "rb") as f:
        f.seek(sz - 256); tail = f.read(256)
        m = tail.rfind(struct.pack("<I", MAGIC))
        if m < 0:
            print("pak magic not found"); return
        foot = tail[m:m + 44]              # footer starts AT the magic
        version, = struct.unpack_from("<i", foot, 4)
        index_off, index_size = struct.unpack_from("<qq", foot, 8)
        if not (0 < index_size < 300_000_000):
            print(f"implausible index_size={index_size}; footer layout differs"); return
        print(f"pak version={version} index_off={index_off} index_size={index_size} (size={sz})")
        f.seek(index_off)
        idx = f.read(index_size)

    mount, o = fstring(idx, 0)
    (num,) = struct.unpack_from("<i", idx, o); o += 4
    print(f"mount={mount!r} entries={num}")
    names = []
    bad = 0
    for i in range(num):
        try:
            name, o = fstring(idx, o)
            # FPakEntry: Offset(8) Size(8) Uncompressed(8) Method(4) Hash(20)
            offset, size, usize = struct.unpack_from("<qqq", idx, o); o += 24
            (method,) = struct.unpack_from("<I", idx, o); o += 4
            o += 20  # hash
            if version >= 3:
                if method != 0:
                    (nblocks,) = struct.unpack_from("<I", idx, o); o += 4
                    o += nblocks * 16
                o += 1  # bEncrypted
                o += 4  # CompressionBlockSize
            if not name or any(c not in "\t" and ord(c) < 32 for c in name):
                bad += 1
                if bad > 5:
                    print(f"!! index desync at entry {i}; stopping"); break
                continue
            names.append((name, offset, size, usize, method))
        except struct.error:
            print(f"!! struct error at entry {i}, offset {o}"); break

    print(f"parsed {len(names)} filenames\n")
    if filters:
        hits = [n for n in names if any(fl in n[0].lower() for fl in filters)]
        print(f"--- {len(hits)} matching {filters} ---")
        for name, off, size, usize, method in hits[:200]:
            print(f"  {name}  (size={size} usize={usize} method={method})")
    else:
        # summary: top-level dirs
        from collections import Counter
        tops = Counter(n[0].split("/")[1] if n[0].count("/") > 1 else n[0] for n in names)
        for k, v in tops.most_common(40):
            print(f"  {v:6d}  {k}")

if __name__ == "__main__":
    main()
