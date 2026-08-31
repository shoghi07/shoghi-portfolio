#!/usr/bin/env python3
"""Extract a single glyph from a TrueType font as an SVG path.

    python3 tools/glyph-to-path.py                    # print the favicon's "S" path
    python3 tools/glyph-to-path.py --write-favicon    # rewrite assets/favicon.svg
    python3 tools/glyph-to-path.py --char A --cap-height 18

This is what makes assets/favicon.svg font-independent: the mark is a baked outline,
so it renders identically everywhere and rasterises exactly into favicon.ico — no
webfont, no system-font fallback. Run tools/generate-favicon.py afterwards to rebuild
the .ico from the updated SVG.

Defaults reproduce the committed favicon. Two of them are deliberate and worth
keeping if you change the letter:

  * CAP_HEIGHT is 17 in a 32-unit box (53%), well above the type's own cap height.
  * STROKE adds a 0.3-unit hairline.

EB Garamond is a high-contrast text face. At a literal cap-height match its thin
strokes broke up into scattered pixels at 16x16 — which is exactly the size a browser
tab renders. Both values are optical compensation for small sizes; drop them and the
tab icon becomes mush.

Only simple (non-composite) glyphs are supported, which covers letterforms. The font
is pulled from the same cache tools/generate-og.py uses, or pass --font PATH.
"""

import argparse
import hashlib
import os
import re
import struct
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_CACHE = os.path.join(tempfile.gettempdir(), "og-font-cache")
FONT_CSS = "https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400"

BOX = 32.0            # favicon.svg viewBox
CAP_HEIGHT = 17.0     # height of the glyph inside the box
STROKE = 0.3          # hairline thickening for 16px legibility
BRAND = "#C23A17"
CREAM = "#E9E2D4"


class TrueType:
    """Just enough TrueType to read one glyph's outline."""

    def __init__(self, path):
        self.d = open(path, "rb").read()
        count = struct.unpack(">H", self.d[4:6])[0]
        self.tables = {}
        for i in range(count):
            o = 12 + i * 16
            tag = self.d[o:o + 4].decode("latin-1")
            off, ln = struct.unpack(">II", self.d[o + 8:o + 16])
            self.tables[tag] = (off, ln)
        for required in ("head", "cmap", "loca", "glyf"):
            if required not in self.tables:
                sys.exit(f"error: font is missing the {required} table "
                         f"(is it a CFF/OpenType font rather than TrueType?)")
        ho = self.tables["head"][0]
        self.units_per_em = struct.unpack(">H", self.d[ho + 18:ho + 20])[0]
        self.loc_format = struct.unpack(">h", self.d[ho + 50:ho + 52])[0]

    def name(self, name_id=4):
        off, _ = self.tables["name"]
        count, str_off = struct.unpack(">HH", self.d[off + 2:off + 6])
        for i in range(count):
            o = off + 6 + i * 12
            pid, _eid, _lid, nid, ln, so = struct.unpack(">HHHHHH", self.d[o:o + 12])
            if nid == name_id:
                raw = self.d[off + str_off + so: off + str_off + so + ln]
                try:
                    return raw.decode("utf-16-be") if pid == 3 else raw.decode("latin-1")
                except UnicodeDecodeError:
                    continue
        return "?"

    def glyph_id(self, ch):
        off, _ = self.tables["cmap"]
        n = struct.unpack(">H", self.d[off + 2:off + 4])[0]
        best = None
        for i in range(n):
            pid, eid, so = struct.unpack(">HHI", self.d[off + 4 + i * 8: off + 12 + i * 8])
            if (pid, eid) in ((3, 1), (0, 3), (0, 4), (3, 10)):
                best = off + so
        if best is None:
            sys.exit("error: no usable cmap subtable")
        fmt = struct.unpack(">H", self.d[best:best + 2])[0]
        c = ord(ch)
        if fmt == 12:                                   # EB Garamond ships format 12
            groups = struct.unpack(">I", self.d[best + 12:best + 16])[0]
            for i in range(groups):
                o = best + 16 + i * 12
                sc, ec, sg = struct.unpack(">III", self.d[o:o + 12])
                if sc <= c <= ec:
                    return sg + (c - sc)
            return 0
        if fmt != 4:
            sys.exit(f"error: cmap format {fmt} unsupported (need 4 or 12)")
        seg_x2 = struct.unpack(">H", self.d[best + 6:best + 8])[0]
        ends_o = best + 14
        starts_o = ends_o + seg_x2 + 2
        deltas_o = starts_o + seg_x2
        ranges_o = deltas_o + seg_x2
        for i in range(seg_x2 // 2):
            end = struct.unpack(">H", self.d[ends_o + i * 2: ends_o + i * 2 + 2])[0]
            if c > end:
                continue
            start = struct.unpack(">H", self.d[starts_o + i * 2: starts_o + i * 2 + 2])[0]
            if c < start:
                return 0
            delta = struct.unpack(">h", self.d[deltas_o + i * 2: deltas_o + i * 2 + 2])[0]
            ro = struct.unpack(">H", self.d[ranges_o + i * 2: ranges_o + i * 2 + 2])[0]
            if ro == 0:
                return (c + delta) & 0xFFFF
            addr = ranges_o + i * 2 + ro + (c - start) * 2
            g = struct.unpack(">H", self.d[addr:addr + 2])[0]
            return (g + delta) & 0xFFFF if g else 0
        return 0

    def _loca(self, gid):
        off, _ = self.tables["loca"]
        if self.loc_format == 0:
            a, b = struct.unpack(">HH", self.d[off + gid * 2: off + gid * 2 + 4])
            return a * 2, b * 2
        return struct.unpack(">II", self.d[off + gid * 4: off + gid * 4 + 8])

    def contours(self, gid):
        """[[(x, y, on_curve), ...], ...] in font units."""
        go, _ = self.tables["glyf"]
        s, e = self._loca(gid)
        if s == e:
            return []
        o = go + s
        nc = struct.unpack(">h", self.d[o:o + 2])[0]
        if nc < 0:
            sys.exit("error: composite glyphs are not supported — pick a simple letterform")
        o += 10
        ends = list(struct.unpack(f">{nc}H", self.d[o:o + nc * 2])); o += nc * 2
        npts = ends[-1] + 1
        instr = struct.unpack(">H", self.d[o:o + 2])[0]; o += 2 + instr

        flags = []
        while len(flags) < npts:
            f = self.d[o]; o += 1
            flags.append(f)
            if f & 8:                                    # repeat
                rep = self.d[o]; o += 1
                flags += [f] * rep

        # x then y, each delta-encoded: short_bit picks 1-byte deltas (same_bit is
        # then the sign), otherwise same_bit means "repeat previous" and costs nothing.
        cursor = o

        def coords(short_bit, same_bit):
            nonlocal cursor
            vals, v = [], 0
            for f in flags:
                if f & short_bit:
                    delta = self.d[cursor]; cursor += 1
                    v += delta if f & same_bit else -delta
                elif not (f & same_bit):
                    v += struct.unpack(">h", self.d[cursor:cursor + 2])[0]; cursor += 2
                vals.append(v)
            return vals

        xs = coords(2, 16)
        ys = coords(4, 32)

        out, start = [], 0
        for end in ends:
            out.append([(xs[i], ys[i], bool(flags[i] & 1)) for i in range(start, end + 1)])
            start = end + 1
        return out


def cached_font():
    """Reuse tools/generate-og.py's font cache; download EB Garamond if absent."""
    os.makedirs(FONT_CACHE, exist_ok=True)
    try:
        css = urllib.request.urlopen(FONT_CSS, timeout=30).read().decode()
    except Exception as exc:
        sys.exit(f"error: could not reach Google Fonts ({exc}). Pass --font PATH instead.")
    m = re.search(r"src: url\(([^)]+)\) format\('truetype'\)", css)
    if not m:
        sys.exit("error: no TTF face in the Google Fonts response")
    url = m.group(1)
    path = os.path.join(FONT_CACHE, hashlib.sha256(url.encode()).hexdigest()[:16] + ".ttf")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(urllib.request.urlopen(url, timeout=60).read())
    return path


def to_path(contours, cap_height, box):
    """Quadratic TrueType contours -> an SVG path, scaled and centred in the box."""
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    scale = cap_height / (max_y - min_y)
    width = (max_x - min_x) * scale
    tx = (box - width) / 2 - min_x * scale
    ty = (box - cap_height) / 2 + max_y * scale          # SVG y grows downward

    def P(x, y):
        return round(x * scale + tx, 2), round(ty - y * scale, 2)

    def mid(a, b):
        return (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0

    parts = []
    for c in contours:
        if c[0][2]:
            start, rest = c[0][:2], c[1:]
        elif c[-1][2]:
            start, rest = c[-1][:2], c[:-1]
        else:                                            # no on-curve point to start from
            start, rest = mid(c[0][:2], c[-1][:2]), c[:]
        sx, sy = P(*start)
        d = [f"M{sx} {sy}"]
        ctrl = None
        for (x, y, on) in rest:
            if on:
                if ctrl is None:
                    d.append("L%g %g" % P(x, y))
                else:
                    cx, cy = P(*ctrl); px, py = P(x, y)
                    d.append(f"Q{cx} {cy} {px} {py}")
                    ctrl = None
            else:
                if ctrl is not None:                     # implied on-curve midpoint
                    mx, my = P(*mid(ctrl, (x, y)))
                    cx, cy = P(*ctrl)
                    d.append(f"Q{cx} {cy} {mx} {my}")
                ctrl = (x, y)
        if ctrl is not None:
            cx, cy = P(*ctrl)
            d.append(f"Q{cx} {cy} {sx} {sy}")
        d.append("Z")
        parts.append("".join(d))
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", help="path to a .ttf (default: cached EB Garamond Regular)")
    ap.add_argument("--char", default="S", help="character to extract (default: S)")
    ap.add_argument("--cap-height", type=float, default=CAP_HEIGHT)
    ap.add_argument("--box", type=float, default=BOX)
    ap.add_argument("--stroke", type=float, default=STROKE)
    ap.add_argument("--write-favicon", action="store_true",
                    help="rewrite assets/favicon.svg with the result")
    args = ap.parse_args()

    font = args.font or cached_font()
    ttf = TrueType(font)
    gid = ttf.glyph_id(args.char)
    if not gid:
        sys.exit(f"error: {args.char!r} is not in {ttf.name()}")
    contours = ttf.contours(gid)
    if not contours:
        sys.exit(f"error: {args.char!r} has an empty outline")
    path = to_path(contours, args.cap_height, args.box)
    print(f"{ttf.name()} — {args.char!r} glyph {gid}, {len(contours)} contour(s), "
          f"{len(path)} chars", file=sys.stderr)

    if not args.write_favicon:
        print(path)
        return

    stroke = (f' stroke="{CREAM}" stroke-width="{args.stroke}" stroke-linejoin="round"'
              if args.stroke else "")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {args.box:g} {args.box:g}">
  <rect width="{args.box:g}" height="{args.box:g}" rx="2" fill="{BRAND}"/>
  <!-- "{args.char}" from {ttf.name()} as an outline, so the mark needs no webfont and
       rasterises exactly into favicon.ico via tools/generate-favicon.py.
       Generated by tools/glyph-to-path.py (write-favicon mode). Set larger than the
       type's cap height and given a hairline stroke because Garamond's thin strokes
       break up at 16px otherwise. -->
  <path d="{path}" fill="{CREAM}"{stroke}/>
</svg>
'''
    if "--" in svg[svg.index("<!--") + 4: svg.index("-->")]:
        sys.exit('error: the SVG comment contains "--", which is illegal in XML '
                 'and would stop the file from rendering')
    dst = os.path.join(ROOT, "assets", "favicon.svg")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote assets/favicon.svg ({len(svg)} bytes)", file=sys.stderr)
    print("next: python3 tools/generate-favicon.py", file=sys.stderr)


if __name__ == "__main__":
    main()
