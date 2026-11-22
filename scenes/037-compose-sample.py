# -*- coding: utf-8 -*-
"""037 compose (system python3 + PIL): 2x2 multi-view sample sheet.
Also fills the 'panel' field of the annotations JSON.
Run: python3 037-compose-sample.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ANN = os.path.join(HERE, "037-training-data-annotations.json")
OUT = os.path.join(ROOT, "renders", "037-training-data-sample.png")

ORDER = [("front", "front"), ("diag", "diag 45 deg"),
         ("side", "side"), ("high", "high left")]
CELL = 512


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    with open(ANN, encoding="utf-8") as fh:
        ann = json.load(fh)
    sheet = Image.new("RGB", (CELL * 2, CELL * 2), "white")
    d = ImageDraw.Draw(sheet)
    f = font(30, bold=True)
    for idx, (view, label) in enumerate(ORDER):
        img = Image.open(os.path.join(HERE, "tmp_views",
                                      "view037_%s.png" % view)).convert("RGB")
        x = (idx % 2) * CELL
        y = (idx // 2) * CELL
        sheet.paste(img, (x, y))
        # label chip
        d.rectangle([x + 10, y + 10, x + 210, y + 52], fill=(20, 22, 28))
        d.text((x + 22, y + 16), label, fill=(255, 255, 255), font=f)
        for v in ann["views"]:
            if v["view"] == view:
                v["panel"] = [x, y, CELL, CELL]
    sheet.save(OUT)
    with open(ANN, "w", encoding="utf-8") as fh:
        json.dump(ann, fh, indent=2)
    print("SAMPLE_WRITTEN:", OUT, sheet.size)


if __name__ == "__main__":
    main()
