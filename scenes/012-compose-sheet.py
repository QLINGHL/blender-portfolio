# -*- coding: utf-8 -*-
"""012 compose (system python3 + PIL): draw the UV layout from the exported
UV data (41 parts, 8x6 grid of 128px quadrants), then compose the 3-panel
QA contact sheet.
Run: python3 012-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UV_JSON = os.path.join(HERE, "012-uv-data.json")
SUMMARY = os.path.join(HERE, "012-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "010-lowpoly-chest.png")
WIREFRAME = os.path.join(ROOT, "renders", "010-lowpoly-chest-wireframe.png")
UV_PNG = os.path.join(ROOT, "renders", "012-uv-layout.png")
SHEET = os.path.join(ROOT, "renders", "012-asset-qa-sheet.png")

SIZE = 1024
ORDER = ["Body_Bottom", "Body_Front", "Body_Back", "Body_Left", "Body_Right",
         "Inner_Floor", "Rim_Front", "Rim_Back", "Rim_Left", "Rim_Right",
         "Band_Front_7", "Band_Back_7", "Band_Bottom_7",
         "Band_Front_7.001", "Band_Back_7.001", "Band_Bottom_7.001",
         "Hasp_Body", "Padlock", "Padlock_Shankle",
         "Coin_L0_0", "Coin_L0_1", "Coin_L0_2", "Coin_L0_3", "Coin_L0_4",
         "Coin_L0_5", "Coin_L0_6",
         "Coin_L1_0", "Coin_L1_1", "Coin_L1_2", "Coin_L1_3", "Coin_L1_4",
         "Coin_L2_0", "Coin_L2_1", "Coin_L2_2", "Coin_Top",
         "Gem_Red", "Gem_Blue", "Lid", "LidBand_7", "LidBand_7.001",
         "LidHasp"]
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
    8 columns x 6 rows = 48 cells for 41 parts."""
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
    d.text((ex + 10, ey + 10), "41 parts,\neach own 0-1\nUV space",
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
    d.text((36, 26), "Asset QA Sheet  |  Low-Poly Treasure Chest (010)",
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
    hinge = s["hinge"]
    footer2 = ("Hinge: lid at (%.1f, %.1f, %.1f), open %.0f deg, %d parts parented to lid   |   "
               "Treasure: %d parts inside cavity   |   Cavity raycast: %s / %s" % (
                   hinge["lid_location"][0], hinge["lid_location"][1],
                   hinge["lid_location"][2], abs(hinge["open_angle_deg"]),
                   len(hinge["parented_to_lid"]),
                   s["treasure_containment"]["treasure_parts"],
                   s["cavity"]["over_treasure"]["hit"],
                   s["cavity"]["over_clear_corner"]["hit"]))
    d.text((36, fy + 52), footer2, fill=(60, 60, 60), font=font(28))
    footer3 = ("Boundary edges: %d (open parts only: 2 lid bands + lid hasp)" % (
        s["boundary_edges"],))
    d.text((36, fy + 90), footer3, fill=(60, 60, 60), font=font(28))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
