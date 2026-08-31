#!/usr/bin/env python3
"""Regenerate the Open Graph share cards in assets/og/.

    python3 tools/generate-og.py

Each card is 1200x630 and is drawn as SVG, then rasterised. The project cards
reuse the .cover--* gradients from css/styles.css, so a share card and its work
row read as the same artwork — if you change a cover in the CSS, mirror it in
COVERS below.

Requires macOS: rasterising uses qlmanage (Quick Look / WebKit) and sips, both
of which ship with the OS. There is no cross-platform fallback.

Two things that are easy to break:

  * Quick Look renders into a SQUARE canvas and does not centre a 1200x630
    document inside it the way you would expect, which silently clips the top
    of the card. wrap() therefore pads every card into an explicit 1200x1200
    canvas with the artwork at y=285, so the centre-crop back to 630 is exact.

  * Quick Look only sees locally installed fonts, so the site's webfonts
    (EB Garamond / Figtree / IBM Plex Mono) are downloaded and inlined into each
    SVG as base64 @font-face rules — see font_style_block(). This is what keeps
    the cards glyph-exact against the live pages. The first run needs network;
    the TTFs are then cached in the system temp dir.

  * Display sizes here are ~1.10x their pre-Garamond values. EB Garamond measures
    a 65.3 cap height against Instrument Serif's 72.0 at the same font-size, so a
    literal size carry-over would have rendered the cards visibly smaller.

After editing copy here, re-run and re-check the og:image dimensions still
match the og:image:width/height meta tags in the HTML (1200x630).
"""

import base64
import hashlib
import html
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "og")

SERIF = "EB Garamond, Iowan Old Style, Palatino, Georgia, serif"
SANS = "Figtree, Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "IBM Plex Mono, ui-monospace, Menlo, monospace"

# Quick Look only sees locally installed fonts, so the real webfonts are downloaded
# and inlined into each SVG as base64 @font-face rules. Without this the cards fall
# back to Palatino/Helvetica and drift from the live site. Needs network on first run;
# files are cached in the system temp dir afterwards.
FONT_CSS = ("https://fonts.googleapis.com/css2"
            "?family=EB+Garamond:ital,wght@0,400;1,400"
            "&family=Figtree:wght@400"
            "&family=IBM+Plex+Mono:wght@400")
FONT_CACHE = os.path.join(tempfile.gettempdir(), "og-font-cache")
_FONT_STYLE = None

# mirrors the custom properties in css/styles.css
PAPER, PAPER2 = "#f2f1ee", "#faf9f6"
INK, INK2, ACCENT, GREEN = "#171512", "#413d38", "#c23a17", "#2f7a45"

W, H = 1200, 630
JPEG_QUALITY = 86


def font_style_block():
    """Download the webfonts once and return an SVG <style> of base64 @font-face rules."""
    global _FONT_STYLE
    if _FONT_STYLE is not None:
        return _FONT_STYLE
    os.makedirs(FONT_CACHE, exist_ok=True)
    try:
        # a plain urllib UA makes Google Fonts serve TTF, which WebKit handles
        # reliably inside a data: URI (woff2 support in Quick Look is patchier)
        css = urllib.request.urlopen(FONT_CSS, timeout=30).read().decode()
    except Exception as exc:
        sys.exit(f"error: could not reach Google Fonts ({exc}).\n"
                 f"       The cards need the real fonts embedded; retry with a network "
                 f"connection.")
    faces = re.findall(
        r"font-family: '([^']+)';\s*font-style: (\w+);\s*font-weight: (\d+);"
        r"\s*src: url\(([^)]+)\) format\('truetype'\)", css)
    if not faces:
        sys.exit("error: no TTF faces found in the Google Fonts response")

    rules = []
    for family, style, weight, url in faces:
        key = hashlib.sha256(url.encode()).hexdigest()[:16] + ".ttf"
        path = os.path.join(FONT_CACHE, key)
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(urllib.request.urlopen(url, timeout=60).read())
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        rules.append(f"@font-face{{font-family:'{family}';font-style:{style};"
                     f"font-weight:{weight};"
                     f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")
        print(f"  font: {family} {style} {weight}  "
              f"{os.path.getsize(path) // 1024}KB")
    _FONT_STYLE = "<style>" + "".join(rules) + "</style>"
    return _FONT_STYLE


def lin(id_, deg, stops):
    """CSS linear-gradient(Ndeg) -> SVG linearGradient across the unit box."""
    r = math.radians(deg)
    dx, dy = math.sin(r), -math.cos(r)
    x1, y1 = 0.5 - dx / 2, 0.5 - dy / 2
    x2, y2 = 0.5 + dx / 2, 0.5 + dy / 2
    body = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return (f'<linearGradient id="{id_}" x1="{x1:.3f}" y1="{y1:.3f}" '
            f'x2="{x2:.3f}" y2="{y2:.3f}">{body}</linearGradient>')


def rad(id_, cx, cy, r, colour, opacity):
    """CSS radial-gradient(circle at x y, colour, transparent) -> SVG."""
    return (f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}">'
            f'<stop offset="0" stop-color="{colour}" stop-opacity="{opacity}"/>'
            f'<stop offset="1" stop-color="{colour}" stop-opacity="0"/>'
            f'</radialGradient>')


def esc(text):
    return html.escape(text, quote=False)


def wrap(inner):
    """Pad a 1200x630 card into a 1200x1200 canvas so the centre-crop is exact."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" '
            'viewBox="0 0 1200 1200">'
            f'{font_style_block()}'
            f'<g transform="translate(0,285)">{inner}</g></svg>')


# Project cover art, transcribed from the .cover--* rules in css/styles.css.
COVERS = {
    "quixera": dict(
        defs=lin("g", 160, [(0, "#173528"), (.55, "#0d2118"), (1, "#2a4a1d")])
        + rad("h", .18, .20, .34, "#ffdc8c", .28),
        art='<rect width="1200" height="630" fill="url(#g)"/>'
            '<rect width="1200" height="630" fill="url(#h)"/>'
            '<g opacity=".08">'
            + "".join(f'<rect x="{x}" y="113" width="10" height="265" fill="#e8e0d2"/>'
                      for x in range(-60, 1260, 22))
            + '</g>'),
    "connectx": dict(
        defs=lin("g", 135, [(0, "#14110f"), (1, "#2a211c")]),
        art='<rect width="1200" height="630" fill="url(#g)"/>'
            '<g opacity=".08" stroke="#c23a17" stroke-width="1">'
            + "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="630"/>'
                      for x in range(0, 1201, 28))
            + "".join(f'<line x1="0" y1="{y}" x2="1200" y2="{y}"/>'
                      for y in range(0, 631, 28))
            + '</g>'
            '<circle cx="396" cy="245" r="130" fill="none" stroke="#e8e0d2" '
            'stroke-opacity=".35" stroke-width="1"/>'
            '<circle cx="396" cy="245" r="139" fill="none" stroke="#c23a17" '
            'stroke-opacity=".12" stroke-width="18"/>'),
    "delicut": dict(
        defs=lin("g", 200, [(0, "#c75a24"), (.70, "#8d2d16"), (1, "#24110c")])
        + rad("h", .80, .20, .38, "#ffc45c", .45),
        art='<rect width="1200" height="630" fill="url(#g)"/>'
            '<rect width="1200" height="630" fill="url(#h)"/>'
            '<circle cx="420" cy="277" r="138" fill="#f3ece0" fill-opacity=".14" '
            'stroke="#f3ece0" stroke-opacity=".28"/>'),
    "pubadmin": dict(
        defs=lin("g", 180, [(0, "#1a2744"), (1, "#0e1526")]),
        art='<rect width="1200" height="630" fill="url(#g)"/>'
            '<line x1="144" y1="101" x2="1056" y2="101" stroke="#e8e0d2" '
            'stroke-opacity=".22"/>'
            '<g opacity=".08">'
            + "".join(f'<rect x="144" y="{y}" width="912" height="1" fill="#e8e0d2"/>'
                      for y in range(123, 530, 22))
            + '</g>'),
    "novus": dict(
        defs=lin("g", 135, [(0, "#3a2140"), (1, "#1a121c")])
        + rad("h", .70, .80, .44, "#c23a17", .35),
        art='<rect width="1200" height="630" fill="url(#g)"/>'
            '<rect width="1200" height="630" fill="url(#h)"/>'
            '<polygon points="120,489 236,414 336,451 449,359 562,439 675,340 '
            '750,410 750,489" fill="#e8e0d2" fill-opacity=".16"/>'),
    "curam": dict(
        defs=lin("g", 160, [(0, "#d7c4a8"), (.46, "#7f9b8a"), (1, "#2d4a40")]),
        art='<rect width="1200" height="630" fill="url(#g)"/>'),
}


def case_card(slug, num, name, word):
    """A project card: cover art, then one scrimmed text band along the bottom.

    The scrim is what makes this work on every cover. Curam's gradient runs
    light-to-dark, so without it the title sat dark-on-dark and disappeared.
    """
    c = COVERS[slug]
    return wrap(f'''<defs>{c["defs"]}
<linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#171512" stop-opacity="0"/>
<stop offset="0.55" stop-color="#171512" stop-opacity="0.62"/>
<stop offset="1" stop-color="#171512" stop-opacity="0.86"/></linearGradient></defs>
{c["art"]}
<rect x="0" y="315" width="1200" height="315" fill="url(#scrim)"/>
<text x="80" y="470" font-family="{MONO}" font-size="20" letter-spacing="2" \
fill="{PAPER2}" fill-opacity=".82">{num} · SELECTED WORK · SHOGHI BAGUL</text>
<text x="80" y="556" font-family="{SERIF}" font-size="101" \
fill="{PAPER2}">{esc(name)}</text>
<text x="1120" y="556" text-anchor="end" font-family="{SERIF}" font-style="italic" \
font-size="101" fill="{PAPER2}" fill-opacity=".92">{esc(word)}</text>''')


def paper_card(title_lines, kicker, meta):
    """A paper card for the site-level pages: kicker, serif title, meta rule."""
    parts = []
    for i, (text, size, italic) in enumerate(title_lines):
        style = ' font-style="italic"' if italic else ""
        if isinstance(text, str):
            fill, inner = (ACCENT if italic else INK), esc(text)
        else:
            # segments: [(text, colour), ...] so part of a word can be accented,
            # matching the .mark spans in the About headline
            fill = INK
            inner = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in text)
        parts.append(f'<text x="80" y="{300 + i * 104}" font-family="{SERIF}" '
                     f'font-size="{size}"{style} fill="{fill}">{inner}</text>')
    return wrap(f'''<rect width="1200" height="630" fill="{PAPER}"/>
<circle cx="86" cy="82" r="7" fill="{GREEN}"/>
<text x="108" y="90" font-family="{MONO}" font-size="20" letter-spacing="2" \
fill="{INK2}">{esc(kicker)}</text>
{"".join(parts)}
<line x1="80" y1="502" x2="1120" y2="502" stroke="{INK}" stroke-opacity=".22"/>
<text x="80" y="548" font-family="{SANS}" font-size="24" \
fill="{INK2}">{esc(meta)}</text>''')


# Flat paper cards stay PNG (crisp text, already small). The gradient-heavy
# project cards go to JPEG — as PNG they were ~700KB each, 4.5MB in total.
# Keep these formats in step with the og:image:type meta tags in the HTML.
CARDS = [
    ("home", "png", paper_card(
        [("Shoghi", 130, False), ("Bagul", 130, True)],
        "AVAILABLE FOR NEW ROLES",
        "Product designer · Design Lead, Tcules · Ahmedabad")),
    ("about", "png", paper_card(
        [([("Design", ACCENT), ("er by craft.", INK)], 84, False),
         ([("Engineer", ACCENT), (" by training.", INK)], 84, False)],
        "ABOUT · SHOGHI BAGUL",
        "M.Des, NID Ahmedabad · Design Lead, Tcules")),
    ("quixera", "jpg", case_card("quixera", "01", "Quixera", "Play")),
    ("connectx", "jpg", case_card("connectx", "02", "ConnectX", "Signal")),
    ("delicut", "jpg", case_card("delicut", "03", "Delicut", "Nourish")),
    ("pubadmin", "jpg", case_card("pubadmin", "04", "PubAdmin", "Rights")),
    ("novus", "jpg", case_card("novus", "05", "Novus Insights", "Insight")),
    ("curam", "jpg", case_card("curam", "06", "Curam Care", "Care")),
]


def main():
    for tool in ("qlmanage", "sips"):
        if shutil.which(tool) is None:
            sys.exit(f"error: {tool} not found — this script needs macOS.")

    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="og-cards-")
    try:
        for name, fmt, svg in CARDS:
            svg_path = os.path.join(tmp, f"{name}.svg")
            with open(svg_path, "w", encoding="utf-8") as fh:
                fh.write(svg)

            # Quick Look writes <input name>.png alongside the source.
            subprocess.run(["qlmanage", "-t", "-s", str(W), "-o", tmp, svg_path],
                           check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            raw = os.path.join(tmp, f"{name}.svg.png")
            if not os.path.exists(raw):
                sys.exit(f"error: Quick Look did not rasterise {name}.svg")

            dst = os.path.join(OUT, f"{name}.{fmt}")
            args = ["sips", "-c", str(H), str(W)]
            if fmt == "jpg":
                args += ["-s", "format", "jpeg",
                         "-s", "formatOptions", str(JPEG_QUALITY)]
            subprocess.run(args + [raw, "--out", dst], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # drop a stale sibling if a card's format was switched
            stale = os.path.join(OUT, f"{name}.{'png' if fmt == 'jpg' else 'jpg'}")
            if os.path.exists(stale):
                os.remove(stale)
                print(f"  removed stale {os.path.basename(stale)}")

            size = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", dst],
                check=True, capture_output=True, text=True).stdout
            w = int(size.split("pixelWidth:")[1].split()[0])
            h = int(size.split("pixelHeight:")[1].split()[0])
            if (w, h) != (W, H):
                sys.exit(f"error: {name}.{fmt} is {w}x{h}, expected {W}x{H}")

            print(f"  {name}.{fmt}  {w}x{h}  {os.path.getsize(dst) // 1024} KB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"{len(CARDS)} cards written to assets/og/ ({total // 1024} KB total)")


if __name__ == "__main__":
    main()
