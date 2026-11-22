# -*- coding: utf-8 -*-
"""037 3D 训练数据：药水店柜台场景（033）多视角标注
Load the potion shop counter scene from the 033 blend into a clean
training scene, render 4 views, and compute per-object bounding boxes
and keypoints from real camera projection (no invented numbers).
The shop has walls on the back (y=+2.2) and left (x=-2.2), so there is
no usable back view: views are front / front-right diagonal / right
side / high-left (looking over the left wall).
Run: blender --background --python 037-render-views.py
(with the lavapipe env from 015-setup-render.sh)
"""
import os
import sys
import json
import math
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, make_world_gradient, make_camera,
                    poly_count, total_poly_count)

SHOP_BLEND = os.path.join(ROOT, "scenes", "033-potion-shop-counter.blend")
ANN = os.path.join(ROOT, "scenes", "037-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "037-potion-shop-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

TARGET = (0.3, 0.3, 1.1)
VIEWS = [
    ("front", (0.3, -6.0, 2.0), TARGET),
    ("diag", (4.5, -4.5, 3.2), TARGET),
    ("side", (6.3, 0.3, 2.0), TARGET),
    ("high", (-5.0, -2.5, 6.0), TARGET),
]

# Object-name prefixes per labelled group. Everything else in the 033
# blend (walls, planks, rug, ground, lights) is scene background.
PREFIXES = {
    "counter": ("Counter_Body", "Counter_Top", "Counter_Kick",
                "Counter_Trim", "CounterPanel_", "CounterPanelTrim_"),
    "shelf": ("Shelf_150", "Shelf_195", "ShelfBracket_"),
    "shelf_bottles": ("ShelfBtl_",),
    "counter_props": ("CounterBtl_", "Candle", "Candle_Flame",
                      "Candle_Holder", "Coin_", "Pouch", "Pouch_Tie"),
    "ledger": ("Ledger_",),
    "cauldron": ("Cauldron", "BrewBubble_"),  # note: legs are named
    # CauldronLeg_0 (no underscore after Cauldron), so the prefix must
    # not include the trailing underscore
    "lantern": ("LampChain_", "Lamp_Cap", "Lamp_Glass", "LampPost_",
                "Lamp_Base", "Lamp_Candle", "Lamp_Flame"),
    "stool": ("Stool_Seat", "StoolLeg_"),
}
LABELS = {
    "counter": "lowpoly_counter",
    "shelf": "lowpoly_shelf",
    "shelf_bottles": "lowpoly_shelf_bottles",
    "counter_props": "lowpoly_counter_props",
    "ledger": "lowpoly_ledger",
    "cauldron": "lowpoly_cauldron",
    "lantern": "lowpoly_lantern",
    "stool": "lowpoly_stool",
}
GROUP_ORDER = ("counter", "shelf", "shelf_bottles", "counter_props",
               "ledger", "cauldron", "lantern", "stool")


def append_shop_objects():
    """Append everything from the 033 blend except its Camera."""
    with bpy.data.libraries.load(SHOP_BLEND, link=False) as (data_from,
                                                             data_to):
        wanted = [n for n in data_from.objects if n != "Camera"]
        data_to.objects = wanted
    groups = {g: [] for g in GROUP_ORDER}
    for obj in data_to.objects:
        if obj is None:
            continue
        bpy.context.scene.collection.objects.link(obj)
        for g in GROUP_ORDER:
            if obj.name.startswith(PREFIXES[g]):
                groups[g].append(obj)
                break
    return groups


def mesh_world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def project(scene, cam, co):
    x, y, depth = world_to_camera_view(scene, cam, Vector(co))
    return [round(x, 4), round(1.0 - y, 4)]


def bbox_of(scene, cam, verts):
    xs, ys = [], []
    for v in verts:
        px, py = project(scene, cam, v)
        xs.append(px)
        ys.append(py)
    return [round(min(xs), 4), round(min(ys), 4),
            round(max(xs), 4), round(max(ys), 4)]


def mean_point(verts):
    s = Vector((0.0, 0.0, 0.0))
    for v in verts:
        s += v
    return s / len(verts)


def main():
    clear_scene()
    make_world_gradient()

    groups = append_shop_objects()
    for g, objs in groups.items():
        print("GROUP %s: %d objects" % (g, len(objs)))
        assert objs, "empty group: %s" % g

    # matrix_world is stale until the depsgraph is evaluated; refresh it
    # before reading world-space vertices for the annotations.
    bpy.context.view_layer.update()

    by_name = {o.name: o for g in groups.values() for o in g}
    verts = {g: [v for o in objs if o.type == 'MESH'
                 for v in mesh_world_verts(o)]
             for g, objs in groups.items()}

    shelf_bottle_bodies = [v for n, o in by_name.items()
                           if n.startswith("ShelfBtl_")
                           and n.endswith("_Body")
                           for v in mesh_world_verts(o)]
    stool_verts = (mesh_world_verts(by_name["Stool_Seat"])
                   + mesh_world_verts(by_name["StoolLeg_0"])
                   + mesh_world_verts(by_name["StoolLeg_1"])
                   + mesh_world_verts(by_name["StoolLeg_2"]))
    shelf_verts = (mesh_world_verts(by_name["Shelf_150"])
                   + mesh_world_verts(by_name["Shelf_195"]))

    keypoints = {
        "counter": {
            "top_center": mean_point(mesh_world_verts(
                by_name["Counter_Top"])),
            "trim_mid": mean_point(mesh_world_verts(
                by_name["Counter_Trim"])),
            "panel0_center": mean_point(mesh_world_verts(
                by_name["CounterPanel_0"])),
            "kick_center": mean_point(mesh_world_verts(
                by_name["Counter_Kick"])),
            "body_center": mean_point(mesh_world_verts(
                by_name["Counter_Body"])),
        },
        "shelf": {
            "shelf_low_center": mean_point(mesh_world_verts(
                by_name["Shelf_150"])),
            "shelf_high_center": mean_point(mesh_world_verts(
                by_name["Shelf_195"])),
            "bracket_low_left": mean_point(mesh_world_verts(
                by_name["ShelfBracket_150_-8"])),
            "bracket_high_right": mean_point(mesh_world_verts(
                by_name["ShelfBracket_195_14"])),
            "shelf_mid": mean_point(shelf_verts),
        },
        "shelf_bottles": {
            "bottle_A_body": mean_point(mesh_world_verts(
                by_name["ShelfBtl_A_Body"])),
            "bottle_H_cork_top": max(mesh_world_verts(
                by_name["ShelfBtl_H_Cork"]), key=lambda v: v.z),
            "bottle_K_body": mean_point(mesh_world_verts(
                by_name["ShelfBtl_K_Body"])),
            "bottle_D_cork_top": max(mesh_world_verts(
                by_name["ShelfBtl_D_Cork"]), key=lambda v: v.z),
            "bottles_center": mean_point(shelf_bottle_bodies),
        },
        "counter_props": {
            "bottle_A_cork_top": max(mesh_world_verts(
                by_name["CounterBtl_A_Cork"]), key=lambda v: v.z),
            "bottle_B_body": mean_point(mesh_world_verts(
                by_name["CounterBtl_B_Body"])),
            "coin_top": max(mesh_world_verts(by_name["Coin_2"]),
                            key=lambda v: v.z),
            "pouch_center": mean_point(mesh_world_verts(
                by_name["Pouch"])),
            "candle_flame": mean_point(mesh_world_verts(
                by_name["Candle_Flame"])),
        },
        "ledger": {
            "cover_center": mean_point(mesh_world_verts(
                by_name["Ledger_Cover"])),
            "left_page": mean_point(mesh_world_verts(
                by_name["Ledger_Left"])),
            "right_page": mean_point(mesh_world_verts(
                by_name["Ledger_Right"])),
            "cover_front_edge": max(mesh_world_verts(
                by_name["Ledger_Cover"]), key=lambda v: v.y),
            "cover_top": max(mesh_world_verts(by_name["Ledger_Cover"]),
                             key=lambda v: v.z),
        },
        "cauldron": {
            "brew_center": mean_point(mesh_world_verts(
                by_name["Cauldron_Brew"])),
            "pot_top": max(mesh_world_verts(by_name["Cauldron_Pot"]),
                           key=lambda v: v.z),
            "spoon_tip": max(mesh_world_verts(by_name["Cauldron_Spoon"]),
                             key=lambda v: v.z),
            "leg0_bottom": min(mesh_world_verts(by_name["CauldronLeg_0"]),
                               key=lambda v: v.z),
            "bubble0_center": mean_point(mesh_world_verts(
                by_name["BrewBubble_0"])),
        },
        "lantern": {
            "flame_center": mean_point(mesh_world_verts(
                by_name["Lamp_Flame"])),
            "glass_center": mean_point(mesh_world_verts(
                by_name["Lamp_Glass"])),
            "cap_top": max(mesh_world_verts(by_name["Lamp_Cap"]),
                           key=lambda v: v.z),
            "base_center": mean_point(mesh_world_verts(
                by_name["Lamp_Base"])),
            "chain_top": max(mesh_world_verts(by_name["LampChain_0"]),
                             key=lambda v: v.z),
        },
        "stool": {
            "seat_center": mean_point(mesh_world_verts(
                by_name["Stool_Seat"])),
            "seat_top": max(mesh_world_verts(by_name["Stool_Seat"]),
                            key=lambda v: v.z),
            "leg0_bottom": min(mesh_world_verts(by_name["StoolLeg_0"]),
                               key=lambda v: v.z),
            "leg1_bottom": min(mesh_world_verts(by_name["StoolLeg_1"]),
                               key=lambda v: v.z),
            "stool_center": mean_point(stool_verts),
        },
    }

    cam = make_camera("Camera", (0, -13.5, 3.0), TARGET, lens=40.0)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.eevee.taa_render_samples = 16

    all_verts = []
    for g in GROUP_ORDER:
        all_verts += verts[g]
    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(VIEW_DIR, "view037_%s.png" % name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("VIEW_RENDERED:", name, path)

        dx, dy, dz = (Vector(loc) - Vector(target))
        azimuth = round(math.degrees(math.atan2(dx, -dy)) % 360.0, 1)
        horiz = math.hypot(dx, dy)
        elevation = round(math.degrees(math.atan2(dz, horiz)), 1)
        views_out.append({
            "view": name,
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "panel": None,  # filled by the compose script
            "scene_bbox": bbox_of(scene, cam, all_verts),
            "objects": [
                {
                    "label": LABELS[g],
                    "bbox": bbox_of(scene, cam, verts[g]),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in keypoints[g].items()},
                }
                for g in GROUP_ORDER
            ],
        })
        print("VIEW_ANN %s azimuth=%.1f elev=%.1f scene_bbox=%s" % (
            name, azimuth, elevation, views_out[-1]["scene_bbox"]))

    # Poly counts: per-group totals + per-object counts (all measured).
    group_counts = {g: total_poly_count(objs)
                    for g, objs in groups.items()}
    per_object = {o.name: poly_count(o)
                  for g in groups.values() for o in g if o.type == 'MESH'}
    total = sum(group_counts.values())
    scene_total = total_poly_count(
        [o for o in bpy.context.scene.objects if o.type == 'MESH'])
    print("GROUP_POLY", group_counts, "total=%d" % total)
    print("SCENE_POLY total=%d" % scene_total)
    print("PER_OBJECT", per_object)

    ann = {
        "asset": "potion_shop_counter_training_data",
        "labels": [LABELS[g] for g in GROUP_ORDER],
        "source_blends": ["scenes/033-potion-shop-counter.blend"],
        "layout": ("033 scene used as-is, no repositioning: counter "
                   "along x at y 0.1, top z 1.00; two wall shelves on "
                   "the back wall (z 1.50 / 1.95) with 14 bottles; "
                   "hanging lantern above the counter (chain from the "
                   "beam, flame z 1.88); cauldron right of the counter "
                   "at (2.05, 0.10); rug + stool in front of the "
                   "counter; ledger, 3 counter bottles, candle, 3 gold "
                   "coins and pouch on the counter top; back wall "
                   "y=+2.2 and left wall x=-2.2 are background, so no "
                   "back view - views are front / front-right diagonal "
                   "/ right side / high-left over the wall"),
        "image": "renders/037-training-data-sample.png",
        "image_size": [1024, 1024],
        "coordinate_system": "normalized 0-1 within each view's own 512x512 panel, origin top-left, y down; 'panel' gives the view's [x, y, w, h] in the 1024x1024 sheet, so a full-sheet coordinate is (panel_x + bbox_x*512)/1024",
        "poly_counts": {
            "groups": group_counts,
            "per_object": per_object,
        },
        "total_polys": total,
        "scene_total_polys": scene_total,
        "views": views_out,
    }
    with open(ANN, "w", encoding="utf-8") as f:
        json.dump(ann, f, indent=2)
    print("ANNOTATIONS_WRITTEN:", ANN)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print("BLEND_SAVED:", BLEND_OUT)


if __name__ == "__main__":
    main()
