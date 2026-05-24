#!/usr/bin/env python3
"""
pak_extract.py — extract UNCOMPRESSED (method=0) files from the v3 .pak by path
substring, into an output dir (mirroring the in-pak path). Each file's data is
preceded by an inline FPakEntry header; for method=0 v3 that header is a fixed
size, after which `size` raw bytes are the file. Clean-room: pulls the locally
shipped data files (e.g. the StaticData JSON catalog) for serving via our backend.

Usage: python analysis/scripts/pak_extract.py <out_dir> <path_substr> [substr2 ...]
"""
import struct, sys, os

PAK = r"WindowsNoEditor/VkGame/Content/Paks/VkGame-WindowsNoEditor.pak"
MAGIC = 0x5A6F12E1

def fstring(buf, o):
    (n,) = struct.unpack_from("<i", buf, o); o += 4
    if n == 0: return "", o
    if n > 0:
        s = buf[o:o + n - 1].decode("latin1", "replace"); o += n
    else:
        n = -n; s = buf[o:o + n * 2 - 2].decode("utf-16-le", "replace"); o += n * 2
    return s, o

def main():
    out_dir = sys.argv[1]
    filters = [a.lower() for a in sys.argv[2:]]
    sz = os.path.getsize(PAK)
    with open(PAK, "rb") as f:
        f.seek(sz - 256); tail = f.read(256)
        m = tail.rfind(struct.pack("<I", MAGIC))
        foot = tail[m:m + 44]
        version, = struct.unpack_from("<i", foot, 4)
        index_off, index_size = struct.unpack_from("<qq", foot, 8)
        f.seek(index_off); idx = f.read(index_size)

        mount, o = fstring(idx, 0)
        (num,) = struct.unpack_from("<i", idx, o); o += 4
        targets = []
        for i in range(num):
            name, o = fstring(idx, o)
            offset, size, usize = struct.unpack_from("<qqq", idx, o); o += 24
            (method,) = struct.unpack_from("<I", idx, o); o += 4
            o += 20
            if version >= 3:
                if method != 0:
                    (nb,) = struct.unpack_from("<I", idx, o); o += 4 + nb * 16
                o += 5  # bEncrypted(1) + CompressionBlockSize(4)
            if any(fl in name.lower() for fl in filters):
                targets.append((name, offset, size, usize, method))

        print(f"{len(targets)} files match {filters}")
        n_ok = 0
        for name, offset, size, usize, method in targets:
            if method != 0:
                print(f"  SKIP (compressed) {name}"); continue
            # inline header for method=0 v3: 8+8+8+4 +20 +1+4 = 53 bytes
            f.seek(offset); hdr = f.read(64)
            (hmethod,) = struct.unpack_from("<I", hdr, 24)
            hsize = 8 + 8 + 8 + 4 + 20 + (1 + 4 if version >= 3 else 0)
            f.seek(offset + hsize); data = f.read(size)
            rel = name.split("Content/StaticData/", 1)[-1] if "Content/StaticData/" in name else name.replace("/", "_")
            dst = os.path.join(out_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as w: w.write(data)
            head = data[:1]
            ok = head in (b"{", b"[")
            n_ok += ok
            print(f"  {'OK ' if ok else '?? '} {rel}  ({size}B, starts {data[:12]!r})")
        print(f"wrote {len(targets)} files; {n_ok} look like JSON")

if __name__ == "__main__":
    main()
