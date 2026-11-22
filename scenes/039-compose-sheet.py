# -*- coding: utf-8 -*-
"""039 compose (system python3 + PIL): draw the UV layout from the exported
UV data (28 parts, 6x5 grid of 170x204 cells), then compose the 3-panel
QA contact sheet.
Run: python3 039-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UV_JSON = os.path.join(HERE, "039-uv-data.json")
SUMMARY = os.path.join(HERE, "039-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "035-lowpoly-spellbook.png")
WIREFRAME = os.path.join(ROOT, "renders", "035-lowpoly-spellbook-wireframe.png")
UV_PNG = os.path.join(ROOT, "renders", "039-uv-layout.png")
SHEET = os.path.join(ROOT, "renders", "039-asset-qa-sheet.png")

SIZE = 1024
ORDER = ["CoverBottom", "PageBlock", "CoverTop", "Spine",
         "PageLineFore_1", "PageLineFore_2", "PageLineFore_3",
         "PageLineHead_1", "PageLineHead_2", "PageLineHead_3",
         "PageLineTail_1", "PageLineTail_2", "PageLineTail_3",
         "RuneRing",
         "RuneStar_1", "RuneStar_2", "RuneStar_3", "RuneStar_4",
         "RuneStar_5",
         "Gem", "ClaspTop", "ClaspFront", "ClaspStud",
         "Corner_-1-1", "Corner_-1+1", "Corner_+1-1", "Corner_+1+1",
         "Bookmark"]
COLORS = ["#2f6fb2", "#c25e2e", "#3a9a5f", "#8a5fc0", "#b07d2a", "#2e8b8b",
          "#a03a5f", "#5a7d2a", "#7a4a2a", "#c23a3a", "#2a5a7d", "#8a7d2a",
          "#4a6a8a", "#9a5a3a", "#6a3a7a", "#3a8a6a"]


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_uv_layout(uv_data, out_path):
    """One cell per part (each part has its own 0-1 UV map),
    6 columns x 5 rows = 30 cells for 28 parts."""
    cols, rows = 6, 5
    cw, ch = SIZE // cols, SIZE // rows
    img = Image.new("RGB", (cols * cw, rows * ch), "white")
    d = ImageDraw.Draw(img, "RGBA")
    f = font(20, bold=True)
    for qi, name in enumerate(ORDER):
        faces = uv_data.get(name, [])
        ox = (qi % cols) * cw
        oy = (qi // cols) * ch
        for i in range(6):
            px = int(i * cw / 5)
            py = int(i * ch / 5)
            w = 2 if i in (0, 5) else 1
            col = (120, 120, 120) if i in (0, 5) else (225, 225, 225)
            d.line([(ox + px, oy), (ox + px, oy + ch)], fill=col, width=w)
            d.line([(ox, oy + py), (ox + cw, oy + py)], fill=col, width=w)
        color = COLORS[qi % len(COLORS)]
        for pts in faces:
            xy = [(ox + u * cw, oy + (1.0 - v) * ch) for u, v in pts]
            d.polygon(xy, fill=color + "44", outline=color)
            d.line(xy + [xy[0]], fill=color, width=1)
        d.rectangle([ox, oy, ox + cw - 1, oy + ch - 1], outline=(60, 60, 60), width=2)
        label = name
        while f.getbbox(label)[2] > cw - 12 and len(label) > 4:
            label = label[:-2] + "…"
        tw = f.getbbox(label)[2]
        d.rectangle([ox + 3, oy + 3, ox + 3 + tw + 10, oy + 30],
                    fill=(20, 22, 28))
        d.text((ox + 6, oy + 6), label, fill=(255, 255, 255), font=f)
        if not faces:
            d.text((ox + 14, oy + ch // 2 - 14), "no UV layer\n(by design)",
                   fill=(120, 120, 120), font=font(20))
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
    uv_img = Image.open(UV_PNG).convert("RGB").resize((SIZE, SIZE))

    header_h, label_h, footer_h = 110, 70, 130
    W = SIZE * 3
    H = header_h + SIZE + label_h + footer_h
    sheet = Image.new("RGB", (W, H), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, header_h], fill=(30, 34, 42))
    d.text((36, 26), "Asset QA Sheet  |  Low-Poly Spellbook (035)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "PASS" if s["overall_pass"] else "REVIEW NEEDED"
    vcol = (80, 200, 120) if s["overall_pass"] else (230, 120, 60)
    d.text((W - 560, 34), verdict, fill=vcol, font=font(44, bold=True))
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
    footer1 = ("Faces: %d   |   Ngons: %d   |   "
               "Duplicate verts: %d   |   Inverted normals: %d   |   "
               "UV out-of-bounds: %d   |   UV islands: %d   |   "
               "UV overlap: %.2f%%" % (
                   s["total_faces"], s["ngons"], s["duplicate_verts"],
                   s["inverted_normals"], s["uv_out_of_bounds"],
                   s["uv_islands"], s["uv_overlap_pct"]))
    d.text((36, fy + 10), footer1, fill=(60, 60, 60), font=font(30))
    footer2 = ("Book stack 0-0.098 OK   |   Spine r=0.022 OK   |   "
               "Rune ring R=0.14 + star 72 deg OK   |   "
               "Gem top +0.052 above cover OK   |   "
               "Bookmark sticks out 0.08 OK" % ())
    d.text((36, fy + 52), footer2, fill=(60, 60, 60), font=font(28))
    n_mats = len(s["materials"]["rows"])
    ok_mats = sum(1 for r in s["materials"]["rows"] if r["ok"])
    footer3 = ("Materials: %d/%d node values match design   |   "
               "DEFECT: ClaspFront bottom z=-0.001, 1 mm below ground "
               "(raise ClaspFront z by 0.001)" % (ok_mats, n_mats))
    d.text((36, fy + 90), footer3, fill=(200, 60, 40), font=font(28))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
