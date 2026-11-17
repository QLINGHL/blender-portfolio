# -*- coding: utf-8 -*-
"""008 compose (system python3 + PIL): draw the UV layout from the exported
UV data (14 parts, 4x4 grid of 256px quadrants), then compose the 3-panel
QA contact sheet.
Run: python3 008-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UV_JSON = os.path.join(HERE, "008-uv-data.json")
SUMMARY = os.path.join(HERE, "008-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "002-lowpoly-character.png")
WIREFRAME = os.path.join(ROOT, "renders", "002-lowpoly-character-wireframe.png")
UV_PNG = os.path.join(ROOT, "renders", "008-uv-layout.png")
SHEET = os.path.join(ROOT, "renders", "008-asset-qa-sheet.png")

SIZE = 1024
ORDER = ["Head", "Hair", "Eye", "Eye.001", "Neck", "Torso",
         "Arm", "Hand", "Arm.001", "Hand.001",
         "Leg", "Foot", "Leg.001", "Foot.001"]
COLORS = ["#2f6fb2", "#c25e2e", "#3a9a5f", "#8a5fc0", "#b07d2a", "#2e8b8b",
          "#a03a5f", "#5a7a2e", "#6a5acd", "#c05a2e", "#2e7a5f", "#7a5a9a",
          "#9a6a2e", "#4a6a9a"]


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_uv_layout(uv_data, out_path):
    """One 256x256 quadrant per part (each part has its own 0-1 UV map)."""
    img = Image.new("RGB", (SIZE, SIZE), "white")
    d = ImageDraw.Draw(img, "RGBA")
    quad = SIZE // 4
    f = font(20, bold=True)
    for qi, name in enumerate(ORDER):
        faces = uv_data.get(name, [])
        ox = (qi % 4) * quad
        oy = (qi // 4) * quad
        for i in range(11):
            p = int(i * quad / 10)
            w = 2 if i in (0, 10) else 1
            col = (120, 120, 120) if i in (0, 10) else (225, 225, 225)
            d.line([(ox + p, oy), (ox + p, oy + quad)], fill=col, width=w)
            d.line([(ox, oy + p), (ox + quad, oy + p)], fill=col, width=w)
        color = COLORS[qi % len(COLORS)]
        for pts in faces:
            xy = [(ox + u * quad, oy + (1.0 - v) * quad) for u, v in pts]
            d.polygon(xy, fill=color + "44", outline=color)
            d.line(xy + [xy[0]], fill=color, width=2)
        d.rectangle([ox, oy, ox + quad - 1, oy + quad - 1], outline=(60, 60, 60), width=2)
        d.rectangle([ox + 6, oy + 6, ox + 138, oy + 32], fill=(20, 22, 28))
        d.text((ox + 12, oy + 10), name, fill=(255, 255, 255), font=f)
    # last two empty cells: label the grid
    d.rectangle([3 * quad + 6, 3 * quad + 6, 4 * quad - 8, 3 * quad + 120],
                fill=(240, 240, 242))
    d.text((3 * quad + 14, 3 * quad + 14), "14 parts,\neach own 0-1\nUV space",
           fill=(60, 60, 60), font=font(22))
    img.save(out_path)
    print("UV_LAYOUT_WRITTEN:", out_path)


def main():
    with open(UV_JSON, encoding="utf-8") as fh:
        uv_data = json.load(fh)
    with open(SUMMARY, encoding="utf-8") as fh:
        s = json.load(fh)
    draw_uv_layout(uv_data, UV_PNG)

    beauty = Image.open(BEAUTY).convert("RGB").resize((SIZE, SIZE))
    wire = Image.open(WIREFRAME).convert("RGB").resize((SIZE, SIZE))
    uv_img = Image.open(UV_PNG).convert("RGB")

    header_h, label_h, footer_h = 110, 70, 96
    W = SIZE * 3
    H = header_h + SIZE + label_h + footer_h
    sheet = Image.new("RGB", (W, H), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, header_h], fill=(30, 34, 42))
    d.text((36, 26), "Asset QA Sheet  |  Low-Poly Character (002)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "PASS" if s["overall_pass"] else "REVIEW NEEDED"
    vcol = (80, 200, 120) if s["overall_pass"] else (230, 120, 60)
    d.text((W - 420, 34), verdict, fill=vcol, font=font(44, bold=True))
    panels = [(beauty, "1  Beauty Render"),
              (wire, "2  Wireframe / Topology"),
              (uv_img, "3  UV Layout (per part)")]
    for i, (img, label) in enumerate(panels):
        x = i * SIZE
        sheet.paste(img, (x, header_h))
        d.rectangle([x, header_h + SIZE, x + SIZE, header_h + SIZE + label_h],
                    fill=(235, 235, 238))
        d.text((x + 24, header_h + SIZE + 14), label, fill=(30, 30, 30),
               font=font(36, bold=True))
    fy = header_h + SIZE + label_h
    footer1 = ("Faces: %d   |   Ngons: %d   |   Duplicate verts: %d   |   "
               "Inverted normals: %d   |   UV out-of-bounds: %d   |   "
               "UV islands: %d   |   UV overlap: %.2f%%" % (
                   s["total_faces"], s["ngons"], s["duplicate_verts"],
                   s["inverted_normals"], s["uv_out_of_bounds"],
                   s["uv_islands"], s["uv_overlap_pct"]))
    d.text((36, fy + 10), footer1, fill=(60, 60, 60), font=font(30))
    rings = s["joint_rings"]
    footer2 = ("Joint rings: " + "  ".join(
        "%s %d rings, mid %.0f%%" % (n, r["rings"], r["mid_ring_fraction"] * 100)
        for n, r in rings.items()))
    d.text((36, fy + 50), footer2, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
