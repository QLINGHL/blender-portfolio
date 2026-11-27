# -*- coding: utf-8 -*-
"""069 compose (system python3 + PIL): draw the UV layout from the exported
UV data (18 parts, 6x3 grid of 170px cells), then compose the 3-panel
QA contact sheet (beauty + wireframe reused from the 068 renders).
Run: python3 069-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UV_JSON = os.path.join(HERE, "069-uv-data.json")
SUMMARY = os.path.join(HERE, "069-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "068-lowpoly-alembic-still.png")
WIREFRAME = os.path.join(ROOT, "renders",
                         "068-lowpoly-alembic-still-wireframe.png")
UV_PNG = os.path.join(ROOT, "renders", "069-uv-layout.png")
SHEET = os.path.join(ROOT, "renders", "069-asset-qa-sheet.png")

SIZE = 1020
ORDER = sorted(json.load(open(UV_JSON, encoding="utf-8")).keys())
COLORS = ["#2f6fb2", "#c25e2e", "#3a9a5f", "#8a5fc0", "#b07d2a", "#2e8b8b",
          "#a03a5f", "#4a6b8a"]


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_uv_layout(uv_data, out_path):
    """One 170x170 cell per part (each part has its own 0-1 UV map),
    6 columns x 3 rows = 18 cells for 18 parts."""
    cols, rows = 6, 3
    cell = SIZE // cols
    img = Image.new("RGB", (cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(img, "RGBA")
    f = font(13, bold=True)
    for qi, name in enumerate(ORDER):
        faces = uv_data.get(name, [])
        ox = (qi % cols) * cell
        oy = (qi // cols) * cell
        for i in range(5):
            p = int(i * cell / 4)
            w = 2 if i in (0, 4) else 1
            col = (120, 120, 120) if i in (0, 4) else (225, 225, 225)
            d.line([(ox + p, oy), (ox + p, oy + cell)], fill=col, width=w)
            d.line([(ox, oy + p), (ox + cell, oy + p)], fill=col, width=w)
        color = COLORS[qi % len(COLORS)]
        for pts in faces:
            xy = [(ox + u * cell, oy + (1.0 - v) * cell) for u, v in pts]
            d.polygon(xy, fill=color + "44", outline=color)
            d.line(xy + [xy[0]], fill=color, width=1)
        d.rectangle([ox, oy, ox + cell - 1, oy + cell - 1],
                    outline=(60, 60, 60), width=1)
        label = name
        while f.getbbox(label)[2] > cell - 6 and len(label) > 4:
            label = label[:-2] + "…"
        tw = f.getbbox(label)[2]
        d.rectangle([ox + 2, oy + 2, ox + 2 + tw + 4, oy + 18],
                    fill=(20, 22, 28))
        d.text((ox + 3, oy + 3), label, fill=(255, 255, 255), font=f)
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
    uv_img = Image.open(UV_PNG).convert("RGB").resize((SIZE, SIZE // 2))
    uv_panel = Image.new("RGB", (SIZE, SIZE), (245, 245, 247))
    uv_panel.paste(uv_img, (0, (SIZE - SIZE // 2) // 2))

    header_h, label_h, footer_h = 110, 70, 130
    W = SIZE * 3
    H = header_h + SIZE + label_h + footer_h
    sheet = Image.new("RGB", (W, H), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, header_h], fill=(30, 34, 42))
    d.text((36, 26), "Asset QA Sheet  |  Low-Poly Alchemy Alembic Still (068)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "PASS" if s["overall_pass"] else "REVIEW NEEDED"
    vcol = (80, 200, 120) if s["overall_pass"] else (230, 120, 60)
    d.text((W - 620, 34), verdict, fill=vcol, font=font(44, bold=True))
    panels = [(beauty, "1  Beauty Render"),
              (wire, "2  Wireframe / Topology"),
              (uv_panel, "3  UV Layout (per part)")]
    for i, (img, label) in enumerate(panels):
        x = i * SIZE
        sheet.paste(img, (x, header_h))
        d.rectangle([x, header_h + SIZE, x + SIZE, header_h + SIZE + label_h],
                    fill=(235, 235, 238))
        d.text((x + 24, header_h + SIZE + 14), label, fill=(30, 30, 30),
               font=font(36, bold=True))
    fy = header_h + SIZE + label_h
    footer1 = ("Faces: %d   |   Ngons: %d   |   "
               "Duplicate verts: %d   |   Inverted normals: %d   |   "
               "UV out-of-bounds: %d   |   UV islands: %d   |   "
               "UV overlap: %.2f%%" % (
                   s["total_faces"], s["ngons"], s["duplicate_verts"],
                   s["inverted_normals"], s["uv_out_of_bounds"],
                   s["uv_islands"], s["uv_overlap_pct"]))
    d.text((36, fy + 10), footer1, fill=(60, 60, 60), font=font(30))
    st = s["structure"]
    footer2 = ("Flame-bulb gap %.3f m   |   Stand ring clearance %.4f   |   "
               "Coil clearance %.4f   |   Drip gap %.4f   |   "
               "Retort liquid min clearance %.4f   |   "
               "Collection liquid min clearance %.4f" % (
                   st["flame_contact"]["flame_bulb_gap"],
                   st["stand_ring"]["clearance"],
                   st["coil_clearance"]["clearance"],
                   st["drip_gap"]["drip_gap"],
                   st["liquids"]["liquids"]["RetortLiquid"][
                       "min_clearance_analytic"],
                   st["liquids"]["liquids"]["CollectionLiquid"][
                       "min_clearance_analytic"]))
    d.text((36, fy + 52), footer2, fill=(60, 60, 60), font=font(28))
    n_mats = len(s["materials"]["rows"])
    ok_mats = sum(1 for r in s["materials"]["rows"] if r["ok"])
    footer3 = ("Materials: %d/%d node values match design (8 incl. glass "
               "alpha + 3 glowing materials)   |   Overall 0.62 x 0.34 x "
               "0.50 m   |   068 note gap numbers verified, no correction "
               "needed (see checklist §6)" % (ok_mats, n_mats))
    d.text((36, fy + 90), footer3, fill=(60, 60, 60), font=font(28))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
