#!/usr/bin/env python3
"""Regenerate the root favicon.ico from assets/favicon.svg.

    python3 tools/generate-favicon.py

Browsers that support SVG icons use assets/favicon.svg via the <link rel="icon">
tags. This .ico is the fallback for everything that does not — older Safari,
some crawlers and link previewers, Windows taskbar pins — and it also answers
the automatic GET /favicon.ico that browsers make regardless of any link tag.

Requires macOS: rasterising uses qlmanage (Quick Look), same as
tools/generate-og.py.

The one subtlety: Quick Look flattens transparency onto WHITE, so the rounded
corners come back as opaque pink rather than clear. Rather than trusting the
render's alpha, coverage is recomputed analytically from the rounded-rect
geometry in the SVG (see COVERAGE below) and reapplied. Any partially covered
pixel can only be on the rect's own edge — the "S" sits well inside — so those
pixels are simply the brand red at fractional alpha.

If you restyle assets/favicon.svg, update RECT/RADIUS/BRAND to match, then re-run.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "favicon.svg")
DST = os.path.join(ROOT, "favicon.ico")

SIZES = [16, 32, 48]
VIEWBOX = 32.0            # the SVG's viewBox is "0 0 32 32"
RADIUS = 2.0              # <rect rx="2">
BRAND = (0xC2, 0x3A, 0x17)
SUBSAMPLES = 4            # per axis, for antialiasing the corner coverage


def read_png(path):
    """Minimal 8-bit PNG decoder -> (w, h, rows of RGBA tuples)."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"error: {path} is not a PNG")
    i, idat = 8, b""
    w = h = bd = ct = None
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        typ = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + ln]
        i += 12 + ln
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", body[:10])
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
    if bd != 8:
        sys.exit(f"error: expected an 8-bit PNG, got {bd}-bit")
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    out = bytearray()
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out += line
        prev = line

    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            o = y * stride + x * ch
            if ch == 4:
                row.append(tuple(out[o:o + 4]))
            elif ch == 3:
                row.append((out[o], out[o + 1], out[o + 2], 255))
            elif ch == 2:
                row.append((out[o], out[o], out[o], out[o + 1]))
            else:
                row.append((out[o], out[o], out[o], 255))
        rows.append(row)
    return w, h, rows


def coverage(px, py, size):
    """Fraction of pixel (px, py) covered by the rounded rect, 0..1."""
    r = RADIUS * size / VIEWBOX
    hits = 0
    for sy in range(SUBSAMPLES):
        for sx in range(SUBSAMPLES):
            x = px + (sx + 0.5) / SUBSAMPLES
            y = py + (sy + 0.5) / SUBSAMPLES
            # distance outside the corner arcs; straight edges are always inside
            cx = min(max(x, r), size - r)
            cy = min(max(y, r), size - r)
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= r * r:
                hits += 1
    return hits / (SUBSAMPLES * SUBSAMPLES)


def restore_alpha(size, rows):
    """Replace Quick Look's white-flattened alpha with true rounded-rect coverage."""
    out = []
    for y in range(size):
        row = []
        for x in range(size):
            cov = coverage(x, y, size)
            if cov >= 0.999:
                r, g, b, _ = rows[y][x]
                row.append((r, g, b, 255))
            else:
                # only the rect's own edge is partial here, so it is brand red
                row.append((*BRAND, int(round(cov * 255))))
        out.append(row)
    return out


def dib(size, rows):
    """A 32-bit BGRA DIB entry: header, bottom-up XOR bitmap, then the AND mask."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                         size * size * 4, 0, 0, 0, 0)
    xor = bytearray()
    for y in range(size - 1, -1, -1):
        for (r, g, b, a) in rows[y]:
            xor += bytes((b, g, r, a))
    mask_stride = ((size + 31) // 32) * 4        # 1bpp rows padded to 4 bytes
    return header + bytes(xor) + bytes(mask_stride * size)


def main():
    if shutil.which("qlmanage") is None:
        sys.exit("error: qlmanage not found — this script needs macOS.")
    if not os.path.exists(SRC):
        sys.exit(f"error: {SRC} not found")

    tmp = tempfile.mkdtemp(prefix="favicon-")
    entries = []
    try:
        for size in SIZES:
            subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", tmp, SRC],
                           check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            raw = os.path.join(tmp, "favicon.svg.png")
            if not os.path.exists(raw):
                sys.exit(f"error: Quick Look did not rasterise favicon.svg at {size}px")
            w, h, rows = read_png(raw)
            os.remove(raw)
            if (w, h) != (size, size):
                sys.exit(f"error: {size}px render came back {w}x{h}")
            rows = restore_alpha(size, rows)
            entries.append((size, dib(size, rows)))
            print(f"  {size:>2}x{size:<2}  corner alpha={rows[0][0][3]:<3} "
                  f"centre=#{''.join(f'{c:02x}' for c in rows[size // 2][size // 2][:3])}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    blob = bytearray(struct.pack("<HHH", 0, 1, len(entries)))   # ICONDIR
    offset = 6 + 16 * len(entries)
    for size, data in entries:                                   # ICONDIRENTRY
        blob += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in entries:
        blob += data

    with open(DST, "wb") as fh:
        fh.write(bytes(blob))
    print(f"wrote favicon.ico  {len(blob)} bytes  sizes={SIZES}")


if __name__ == "__main__":
    main()
