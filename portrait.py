#!/usr/bin/env python3
"""
Converts a photo into ASCII-portrait art for the profile card.

Run this ONCE locally with your photo; it writes `portrait.txt`, which update.py
reads and embeds on the left of the card. The GitHub Action never needs the
original photo — only the committed portrait.txt.

    python portrait.py me.jpg

Tuning knobs are at the top. Re-run after tweaking to preview in the terminal.
"""

import sys
from PIL import Image, ImageOps, ImageFilter

# --- tuning -----------------------------------------------------------------
COLS       = 62      # width of the portrait in characters
CHAR_RATIO = 0.52    # monospace cell height/width correction (~0.5)
CUTOFF     = 0.12    # clean up the background to make it pop
GAMMA      = 0.90    # near-linear gamma for faithful shading (no artificial heavy beard)
AUTOCONTRAST = 1     # gently normalize lighting
# Use the full image! Previous crops were likely cutting off the chin/neck, 
# making shadows look like a floating beard and destroying the likeness.
CROP       = (0.0, 0.0, 1.0, 1.0)
# ramp from least ink (blank) to most ink (solid); darkness picks the glyph
RAMP = " .`'\",:;-~=+ilcaoxPO#8%@$&"


def to_ascii(path):
    img = Image.open(path).convert("L")

    w, h = img.size
    l, t, r, b = CROP
    img = img.crop((int(w*l), int(h*t), int(w*r), int(h*b)))

    if AUTOCONTRAST > 0:
        img = ImageOps.autocontrast(img, cutoff=AUTOCONTRAST)
    
    # Mild sharpening to keep glasses and eyebrows defined without blowing out shadows
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3))

    w, h = img.size
    rows = max(1, int(COLS * (h / w) * CHAR_RATIO))
    img = img.resize((COLS, rows), Image.LANCZOS)
    px = img.load()

    n = len(RAMP) - 1
    lines = []
    for y in range(rows):
        row = []
        for x in range(COLS):
            darkness = (255 - px[x, y]) / 255.0          # dark pixel -> more ink
            t = max(0.0, (darkness - CUTOFF) / (1 - CUTOFF))
            t = t ** GAMMA
            row.append(RAMP[round(t * n)])
        lines.append("".join(row).rstrip())
    # trim fully-blank leading/trailing rows
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "me.jpg"
    lines = to_ascii(src)
    with open("portrait.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote portrait.txt  ({len(lines)} rows x {COLS} cols) from {src}\n")
    # console preview
    print("\n".join(lines))


if __name__ == "__main__":
    main()
