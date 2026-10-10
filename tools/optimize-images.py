#!/usr/bin/env python3
"""Turn full-size originals into small WebP files for the site.

    python3 tools/optimize-images.py            # every folder in assets-src/
    python3 tools/optimize-images.py delicut    # just assets-src/delicut/

Drop originals (PNG, JPG or WebP, any size) into assets-src/<project>/, named
the way the page should refer to them. assets-src/ is git-ignored, so heavy
originals never reach the repo. For each one this writes two WebP files to
assets/work/<project>/, <name>-<width>.webp, and prints an <img> tag with
srcset, width and height ready to paste into the page.

The filename prefix picks the widths, since each kind of image is shown at a
different size:

    full-*   full-page screenshots (browser frame, compare)   1200 / 2400
    app-*    phone screens                                    400 / 800
    anything else (photos, crops)                             640 / 1280

A source narrower than a width is never enlarged; the file is then named by
the width it was asked for, but the srcset uses its real width. Files whose
outputs are newer than the source are skipped, so it's safe to re-run.

Uses sharp through npx (the first run downloads it; nothing is added to the
project) and macOS sips to read the output sizes.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets-src")
OUT = os.path.join(ROOT, "assets", "work")
SHARP = ["npx", "--yes", "sharp-cli@5.1.0"]
QUALITY = "78"
EXTS = (".png", ".jpg", ".jpeg", ".webp")

WIDTHS = [
    ("full-", (1200, 2400)),
    ("app-", (400, 800)),
    ("", (640, 1280)),
]


def widths_for(name):
    return next(w for prefix, w in WIDTHS if name.startswith(prefix))


def size_of(path):
    out = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
        capture_output=True, text=True, check=True,
    ).stdout
    vals = [int(line.split()[-1]) for line in out.splitlines() if "pixel" in line]
    return vals[0], vals[1]


def run(project):
    src_dir = os.path.join(SRC, project)
    out_dir = os.path.join(OUT, project)
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(EXTS))
    if not files:
        print(f"  nothing in assets-src/{project}/")
        return

    # batch by width, so sharp starts once per width rather than once per file
    todo = {}
    for f in files:
        name = os.path.splitext(f)[0]
        src = os.path.join(src_dir, f)
        for w in widths_for(name):
            dest = os.path.join(out_dir, f"{name}-{w}.webp")
            if os.path.exists(dest) and os.path.getmtime(dest) >= os.path.getmtime(src):
                continue
            todo.setdefault(w, []).append(src)
    for w, srcs in sorted(todo.items()):
        # inputs first: -i takes an array and would swallow a following "resize"
        cmd = list(SHARP)
        for s in srcs:
            cmd += ["-i", s]
        cmd += ["-o", os.path.join(out_dir, "{name}-" + str(w) + ".webp"),
                "-f", "webp", "-q", QUALITY, "resize", str(w), "--withoutEnlargement"]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  {len(srcs)} file(s) at {w}px")

    rel = f"../assets/work/{project}/"
    total = 0
    for f in files:
        name = os.path.splitext(f)[0]
        small, large = widths_for(name)
        a, b = (os.path.join(out_dir, f"{name}-{w}.webp") for w in (small, large))
        (aw, ah), (bw, _) = size_of(a), size_of(b)
        total += os.path.getsize(a) + os.path.getsize(b)
        srcset = f"{rel}{name}-{small}.webp {aw}w"
        if bw > aw:
            srcset += f", {rel}{name}-{large}.webp {bw}w"
        kb = os.path.getsize(a) // 1024, os.path.getsize(b) // 1024
        print(f"\n  {name}  ({kb[0]} KB / {kb[1]} KB)")
        print(f'  <img src="{rel}{name}-{small}.webp" srcset="{srcset}" sizes="…" '
              f'width="{aw}" height="{ah}" alt="…" loading="lazy" decoding="async" />')
    print(f"\n  assets/work/{project}/: {len(files)} images, {total // 1024} KB of WebP")


def main():
    if not os.path.isdir(SRC):
        sys.exit("No assets-src/ folder: put originals in assets-src/<project>/ first.")
    projects = sys.argv[1:] or sorted(
        d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d))
    )
    for p in projects:
        print(f"assets-src/{p}/")
        run(p)


if __name__ == "__main__":
    main()
