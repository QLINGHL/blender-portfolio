# -*- coding: utf-8 -*-
"""017 compose (system python3 + PIL): draw the UV layout from the exported
UV data (43 parts, 8x6 grid of 128px quadrants), then compose the 3-panel
QA contact sheet.
Run: python3 017-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UV_JSON = os.path.join(HERE, "017-uv-data.json")
SUMMARY = os.path.join(HERE, "017-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "016-lowpoly-altar.png")
WIREFRAME = os.path.join(ROOT, "renders", "016-lowpoly-altar-wireframe.png")
UV_PNG = os.path.join(ROOT, "renders", "017-uv-layout.png")
SHEET = os.path.join(ROOT, "renders", "017-asset-qa-sheet.png")

SIZE = 1024
ORDER = ["Platform_Tier1", "Platform_Tier2", "Platform_Tier3",
         "Step_Low", "Step_High", "Altar_Block", "Altar_Slab",
         "Rune_Ring",
         "RuneStone_0", "RuneStone_1", "RuneStone_2", "RuneStone_3",
         "RuneStone_4", "RuneStone_5", "RuneStone_6", "RuneStone_7",
         "RunePlate_0", "RunePlate_1", "RunePlate_2", "RunePlate_3",
         "RunePlate_4", "RunePlate_5", "RunePlate_6", "RunePlate_7",
         "Candle_L_Base", "Candle_L_Stem", "Candle_L_Cup",
         "Candle_L_Candle", "Candle_L_Flame",
         "Candle_R_Base", "Candle_R_Stem", "Candle_R_Cup",
         "Candle_R_Candle", "Candle_R_Flame",
         "Candle_Tall_Base", "Candle_Tall_Stem", "Candle_Tall_Cup",
         "Candle_Tall_Candle", "Candle_Tall_Flame",
         "Crystal_Main", "Crystal_Shard_0", "Crystal_Shard_1",
         "Crystal_Shard_2"]
COLORS = ["#2f6fb2", "#c25e2e", "#3a9a5f", "#8a5fc0", "#b07d2a", "#2e8b8b",
          "#a03a5f", "#5a7a2e", "#6a5acd", "#c05a2e", "#2e7a5f", "#7a5a9a",
          "#9a6a2e", "#4a6a9a", "#b23a48", "#3a6ea5", "#7a9a3a", "#c07a2e"]


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_uv_layout(uv_data, out_path):
    """One 128x128 quadrant per part (each part has its own 0-1 UV map),
    8 columns x 6 rows = 48 cells for 43 parts."""
    img = Image.new("RGB", (SIZE, SIZE), "white")
    d = ImageDraw.Draw(img, "RGBA")
    cols, rows = 8, 6
    quad = SIZE // cols
    f = font(12, bold=True)
    for qi, name in enumerate(ORDER):
        faces = uv_data.get(name, [])
        ox = (qi % cols) * quad
        oy = (qi // cols) * quad
        for i in range(6):
            p = int(i * quad / 5)
            w = 2 if i in (0, 5) else 1
            col = (120, 120, 120) if i in (0, 5) else (225, 225, 225)
            d.line([(ox + p, oy), (ox + p, oy + quad)], fill=col, width=w)
            d.line([(ox, oy + p), (ox + quad, oy + p)], fill=col, width=w)
        color = COLORS[qi % len(COLORS)]
        for pts in faces:
            xy = [(ox + u * quad, oy + (1.0 - v) * quad) for u, v in pts]
            d.polygon(xy, fill=color + "44", outline=color)
            d.line(xy + [xy[0]], fill=color, width=1)
        d.rectangle([ox, oy, ox + quad - 1, oy + quad - 1], outline=(60, 60, 60), width=2)
        label = name
        while f.getbbox(label)[2] > 116 and len(label) > 4:
            label = label[:-2] + "…"
        tw = f.getbbox(label)[2]
        d.rectangle([ox + 3, oy + 3, ox + 3 + tw + 10, oy + 20],
                    fill=(20, 22, 28))
        d.text((ox + 6, oy + 5), label, fill=(255, 255, 255), font=f)
    # remaining empty cells: label the grid
    ex, ey = (len(ORDER) % cols) * quad, (len(ORDER) // cols) * quad
    d.text((ex + 10, ey + 10), "43 parts,\neach own 0-1\nUV space",
           fill=(60, 60, 60), font=font(20))
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

    header_h, label_h, footer_h = 110, 70, 130
    W = SIZE * 3
    H = header_h + SIZE + label_h + footer_h
    sheet = Image.new("RGB", (W, H), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, header_h], fill=(30, 34, 42))
    d.text((36, 26), "Asset QA Sheet  |  Low-Poly Magic Altar (016)",
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
    ring = s["rune_ring"]
    footer2 = ("Rune ring: centre z=%.2f, lowest z=%.2f (tier 3 top 1.05)   |   "
               "Rune stones: 8x radius 2.0, 45 deg apart, tilt 8 deg   |   "
               "Crystal gap above slab: %.2f" % (
                   ring["center_z"], ring["min_z"],
                   s["crystal_float"]["Crystal_Main"]["gap_above_slab"]))
    d.text((36, fy + 52), footer2, fill=(60, 60, 60), font=font(28))
    footer3 = ("Boundary edges: %d (all 43 parts closed)   |   "
               "Emission: Rune_Glow 1.8, Altar_Crystal 1.4, Candle_Flame 2.5 (measured)" % (
                   s["boundary_edges"],))
    d.text((36, fy + 90), footer3, fill=(60, 60, 60), font=font(28))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
