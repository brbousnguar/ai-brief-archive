#!/usr/bin/env python3
"""Draw the AI Brief mark and write every icon the site serves (#11).

The mark is punched teletype tape, the wire service's own medium: a strip of
newsprint across wire blue, three ink holes, the last one stamped red. It is
plain rectangles and circles in a 100-unit box, so the SVG and every PNG come
from the same geometry and stay identical at any size.

    python3 tools/make_icons.py        # needs Pillow; run from anywhere

Writes icons/mark.svg (also inlined in the masthead by publish.py), the PNGs
the manifest and iOS use, and favicon.ico at the root, where browsers look.
"""
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent

# Tokens from css/main.css.
PAPER, INK, WIRE, STAMP = "#FBF7EF", "#14120E", "#1B5E7A", "#C81E1E"

BACKGROUND = WIRE
SHAPES = [
    ("rect", 0, 34, 100, 66, PAPER),      # the tape
    ("circle", 20, 50, 6, INK),           # punched holes
    ("circle", 40, 50, 6, INK),
    ("circle", 60, 50, 6, INK),
    ("circle", 81, 50, 10, STAMP),        # the one that made the brief
]


def svg() -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           f'<rect width="100" height="100" fill="{BACKGROUND}"/>']
    for kind, *a in SHAPES:
        if kind == "rect":
            x0, y0, x1, y1, c = a
            out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="{c}"/>')
        else:
            cx, cy, r, c = a
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}"/>')
    return "".join(out) + "</svg>\n"


def render(size: int, safe: float = 1.0) -> Image.Image:
    """Draw at 1024 and downsample. `safe` < 1 shrinks the mark toward the
    centre for maskable icons; the tape still runs edge to edge."""
    S = 1024
    k = S / 100
    img = Image.new("RGB", (S, S), BACKGROUND)
    d = ImageDraw.Draw(img)
    t = lambda v: (50 + (v - 50) * safe) * k
    for kind, *a in SHAPES:
        if kind == "rect":
            x0, y0, x1, y1, c = a
            d.rectangle([0 if x0 == 0 else t(x0), t(y0), S if x1 == 100 else t(x1) - 1, t(y1) - 1], fill=c)
        else:
            cx, cy, r, c = a
            d.ellipse([t(cx - r), t(cy - r), t(cx + r), t(cy + r)], fill=c)
    return img.resize((size, size), Image.LANCZOS)


def save_ico(path: Path, sizes=(16, 32, 48)) -> None:
    raw = []
    for s in sizes:
        buf = io.BytesIO()
        render(s).save(buf, format="PNG")
        raw.append(buf.getvalue())
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, data in zip(sizes, raw):
        entries += struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(raw))


def main() -> None:
    icons = ROOT / "icons"
    icons.mkdir(exist_ok=True)
    (icons / "mark.svg").write_text(svg(), encoding="utf-8")
    for name, size in (("icon-32.png", 32), ("icon-192.png", 192), ("icon-512.png", 512)):
        render(size).save(icons / name, optimize=True)
    # Android crops maskable icons to a circle of 80% diameter: keep the holes inside it.
    render(512, safe=0.72).save(icons / "icon-maskable.png", optimize=True)
    # iOS asks for /apple-touch-icon.png at the root even without a link.
    render(180).save(ROOT / "apple-touch-icon.png", optimize=True)
    # Podcast apps want square artwork of 1400 to 3000px; podcast.xml points here (#15).
    render(3000).save(icons / "podcast.png", optimize=True)
    save_ico(ROOT / "favicon.ico")
    print("wrote icons/mark.svg, icons/icon-{32,192,512,maskable}.png, icons/podcast.png, "
          "apple-touch-icon.png, favicon.ico")


if __name__ == "__main__":
    main()
