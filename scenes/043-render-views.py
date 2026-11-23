# -*- coding: utf-8 -*-
"""043 3D 训练数据：魔法图书馆角落场景（040）多视角标注
Load the magic library corner scene from the 040 blend into a clean
training scene, render 4 views, and compute per-object bounding boxes
and keypoints from real camera projection (no invented numbers).
The library has walls on the back (y=+2.2) and left (x=-2.2), so there
is no usable back view: views are front / front-right diagonal /
right side / high-left (looking over the left wall).
Run: blender --background --python 043-render-views.py
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

LIB_BLEND = os.path.join(ROOT, "scenes", "040-magic-library-corner.blend")
ANN = os.path.join(ROOT, "scenes", "043-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "043-library-corner-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

TARGET = (0.0, 0.3, 1.1)
VIEWS = [
    ("front", (0.0, -6.0, 2.0), TARGET),
    ("diag", (4.5, -4.5, 3.2), TARGET),
    ("side", (6.3, 0.3, 2.0), TARGET),
    ("high", (-5.0, -2.5, 6.0), TARGET),
]

# Object-name prefixes per labelled group. Everything else in the 040
# blend (walls, planks, rug, ground, lights) is scene background.
PREFIXES = {
    "bookshelf": ("Shelf_", "ShelfBoard_", "Book_T", "BookStack_",
                  "FloorBook_"),
    "low_shelf": ("LowShelf_", "LBook_", "Globe"),
    "ladder": ("LadderRail_", "LadderRung_"),
    "desk": ("Desk_", "DeskLeg_", "DeskKnob_", "Spellbook_", "InkPot",
             "Ink_Surface", "Quill", "DeskBook_", "Scroll", "ScrollKnob_"),
    "candelabra": ("Candelabra_", "DeskCandle_"),
    "floor_candle": ("FloorCand_", "FloorCandle_"),
    "chair": ("Chair",),
    "chart": ("Chart_",),
}
LABELS = {
    "bookshelf": "lowpoly_bookshelf",
    "low_shelf": "lowpoly_low_shelf",
    "ladder": "lowpoly_ladder",
    "desk": "lowpoly_desk",
    "candelabra": "lowpoly_candelabra",
    "floor_candle": "lowpoly_floor_candle",
    "chair": "lowpoly_chair",
    "chart": "lowpoly_star_chart",
}
GROUP_ORDER = ("bookshelf", "low_shelf", "ladder", "desk", "candelabra",
               "floor_candle", "chair", "chart")


def append_lib_objects():
    """Append everything from the 040 blend except its Camera."""
    with bpy.data.libraries.load(LIB_BLEND, link=False) as (data_from,
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

    groups = append_lib_objects()
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

    shelf_books = [v for n, o in by_name.items()
                   if n.startswith("Book_T")
                   for v in mesh_world_verts(o)]
    low_books = [v for n, o in by_name.items()
                 if n.startswith("LBook_")
                 for v in mesh_world_verts(o)]
    chair_verts = (mesh_world_verts(by_name["Chair_Seat"])
                   + mesh_world_verts(by_name["ChairLeg_-20_-17"])
                   + mesh_world_verts(by_name["ChairLeg_20_-17"])
                   + mesh_world_verts(by_name["ChairLeg_-20_17"])
                   + mesh_world_verts(by_name["ChairLeg_20_17"]))

    keypoints = {
        "bookshelf": {
            "shelf_top_center": mean_point(mesh_world_verts(
                by_name["Shelf_Top"])),
            "shelf_board2_center": mean_point(mesh_world_verts(
                by_name["ShelfBoard_2"])),
            "book_T2_5_center": mean_point(mesh_world_verts(
                by_name["Book_T2_5"])),
            "bookstack_top": max(mesh_world_verts(
                by_name["BookStack_2"]), key=lambda v: v.z),
            "books_center": mean_point(shelf_books),
        },
        "low_shelf": {
            "low_shelf_top_center": mean_point(mesh_world_verts(
                by_name["LowShelf_Top"])),
            "globe_center": mean_point(mesh_world_verts(
                by_name["Globe"])),
            "globe_ring_top": max(mesh_world_verts(
                by_name["Globe_Ring"]), key=lambda v: v.z),
            "lbook_T0_3_center": mean_point(mesh_world_verts(
                by_name["LBook_T0_3"])),
            "low_books_center": mean_point(low_books),
        },
        "ladder": {
            "rail0_top": max(mesh_world_verts(by_name["LadderRail_0"]),
                             key=lambda v: v.z),
            "rung3_center": mean_point(mesh_world_verts(
                by_name["LadderRung_3"])),
            "rail1_bottom": min(mesh_world_verts(
                by_name["LadderRail_1"]), key=lambda v: v.z),
            "ladder_center": mean_point(verts["ladder"]),
        },
        "desk": {
            "desk_top_center": mean_point(mesh_world_verts(
                by_name["Desk_Top"])),
            "spellbook_left_center": mean_point(mesh_world_verts(
                by_name["Spellbook_Left"])),
            "inkpot_center": mean_point(mesh_world_verts(
                by_name["InkPot"])),
            "scroll_center": mean_point(mesh_world_verts(
                by_name["Scroll"])),
            "deskbook_1_center": mean_point(mesh_world_verts(
                by_name["DeskBook_1"])),
        },
        "candelabra": {
            "base_center": mean_point(mesh_world_verts(
                by_name["Candelabra_Base"])),
            "stem_top": max(mesh_world_verts(by_name["Candelabra_Stem"]),
                            key=lambda v: v.z),
            "candle_L_flame": mean_point(mesh_world_verts(
                by_name["DeskCandle_L_Flame"])),
            "candle_C_flame": mean_point(mesh_world_verts(
                by_name["DeskCandle_C_Flame"])),
            "cupR_center": mean_point(mesh_world_verts(
                by_name["Candelabra_CupR"])),
        },
        "floor_candle": {
            "base_center": mean_point(mesh_world_verts(
                by_name["FloorCand_Base"])),
            "pole_top": max(mesh_world_verts(by_name["FloorCand_Pole"]),
                            key=lambda v: v.z),
            "tray_center": mean_point(mesh_world_verts(
                by_name["FloorCand_Tray"])),
            "candle0_flame": mean_point(mesh_world_verts(
                by_name["FloorCandle_0_Flame"])),
            "candle1_flame": mean_point(mesh_world_verts(
                by_name["FloorCandle_1_Flame"])),
        },
        "chair": {
            "seat_center": mean_point(mesh_world_verts(
                by_name["Chair_Seat"])),
            "seat_top": max(mesh_world_verts(by_name["Chair_Seat"]),
                            key=lambda v: v.z),
            "back_top_center": mean_point(mesh_world_verts(
                by_name["ChairBack_Top"])),
            "leg0_bottom": min(mesh_world_verts(
                by_name["ChairLeg_-20_-17"]), key=lambda v: v.z),
            "chair_center": mean_point(chair_verts),
        },
        "chart": {
            "canvas_center": mean_point(mesh_world_verts(
                by_name["Chart_Canvas"])),
            "moon_center": mean_point(mesh_world_verts(
                by_name["Chart_Moon"])),
            "star0_center": mean_point(mesh_world_verts(
                by_name["Chart_Star_0"])),
            "star4_center": mean_point(mesh_world_verts(
                by_name["Chart_Star_4"])),
            "frame_center": mean_point(mesh_world_verts(
                by_name["Chart_Frame"])),
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
        path = os.path.join(VIEW_DIR, "view043_%s.png" % name)
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
        "asset": "magic_library_corner_training_data",
        "labels": [LABELS[g] for g in GROUP_ORDER],
        "source_blends": ["scenes/040-magic-library-corner.blend"],
        "layout": ("040 scene used as-is, no repositioning: tall "
                   "bookshelf on the back wall (x -1.6..0.9, 5 tiers, "
                   "111 books + 3 stacked flat books); low bookshelf "
                   "on the left wall (y -0.6..1.4, 2 tiers, 38 books) "
                   "with globe on top; ladder leaning on the tall "
                   "shelf at 17.7 deg; desk at (1.05, 0.55) with open "
                   "spellbook, 3-arm candelabra, inkpot + quill, 3 "
                   "stacked books and a scroll; floor candelabra at "
                   "(-1.55, 0.75) with warm point light; star chart "
                   "above the desk on the back wall; rug + chair in "
                   "front of the desk; 2 floor books by the ladder; "
                   "back wall y=+2.2 and left wall x=-2.2 are "
                   "background, so no back view - views are front / "
                   "front-right diagonal / right side / high-left "
                   "over the wall"),
        "image": "renders/043-training-data-sample.png",
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
