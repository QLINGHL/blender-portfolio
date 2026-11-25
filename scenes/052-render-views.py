# -*- coding: utf-8 -*-
"""052 3D 训练数据：炼金实验室角落场景（047 + 049 炼金术士）多视角标注
Load the 047 alchemy lab corner scene and the 049 alchemist from their
blends into a clean training scene, render 4 views, and compute
per-object bounding boxes and keypoints from real camera projection
(no invented numbers).
The alchemist stands on the rug in front of the workbench, next to the
stool, facing the front camera (-y) so the flask he holds is visible
(049 lesson: the flask must be seen, not hidden behind the robe).
The lab has walls on the back (y=+2.2) and left (x=-2.2), so there is
no usable back view: views are front / front-right diagonal /
right side / high-left (looking over the left wall).
Run: blender --background --python 052-render-views.py
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

LAB_BLEND = os.path.join(ROOT, "scenes", "047-alchemy-lab-corner.blend")
ALC_BLEND = os.path.join(ROOT, "scenes", "049-lowpoly-alchemist.blend")
ANN = os.path.join(ROOT, "scenes", "052-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "052-alchemy-lab-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

# Alchemist placement: on the rug in front of the workbench, left of
# the stool (stool seat at (0.30, 0.55) r=0.22; rug spans
# x -0.55..1.15, y -0.05..1.15). Faces -y (front camera) by default.
ALC_OFFSET = Vector((-0.35, 0.60, 0.0))

TARGET = (0.0, 0.3, 1.1)
VIEWS = [
    ("front", (0.0, -6.0, 2.0), TARGET),
    ("diag", (4.5, -4.5, 3.2), TARGET),
    ("side", (6.3, 0.3, 2.0), TARGET),
    ("high", (-5.0, -2.5, 6.0), TARGET),
]

# Exact mesh names of the 049 alchemist (from 049-lowpoly-alchemist.md).
ALCHEMIST_NAMES = {
    "Head", "Eye", "Eye.001", "HairCap", "Beard",
    "GoggleRim", "GoggleLens", "GoggleRim.001", "GoggleLens.001",
    "GoggleStrap", "Neck", "Collar", "Shawl", "Robe",
    "Apron", "ApronPocket", "ApronStrap", "ApronStrap.001",
    "Belt", "Buckle",
    "PotionRedBody", "PotionRedCork",
    "PotionBlueBody", "PotionBlueCork",
    "PotionPurpleBody", "PotionPurpleCork",
    "Arm", "Cuff", "Hand", "Arm.001", "Cuff.001", "Hand.001",
    "Flask", "FlaskLiquid", "FlaskCork",
    "Leg", "Shoe", "Leg.001", "Shoe.001",
}

# Object-name prefixes per labelled group. Everything else in the 047
# blend (walls, stone base/rail, beams, floor tiles, ground, lights)
# is scene background.
PREFIXES = {
    "workbench": ("Bench", "Mortar", "Pestle", "Rack_", "Tube",
                  "Alembic", "Receiver_Liq", "Spellbook_", "FloorBook_",
                  "FloorScroll"),
    "potion_shelf": ("PotionShelf_", "Potion_T", "ShelfBook_"),
    "cauldron": ("Hearth_Slab", "Cauldron", "Bubble_", "CauldronLeg_",
                 "Fire_", "Ladle"),
    "jar_shelf": ("JarShelf_", "Jar_T"),
    "storage": ("Barrel", "Crate", "CrateBottle"),
    "wall_decor": ("Chart_", "HerbString_", "HerbLeaf_", "Sconce"),
    "stool": ("Stool", "Rug"),
}
LABELS = {
    "alchemist": "lowpoly_alchemist",
    "workbench": "lowpoly_workbench",
    "potion_shelf": "lowpoly_potion_shelf",
    "cauldron": "lowpoly_cauldron",
    "jar_shelf": "lowpoly_jar_shelf",
    "storage": "lowpoly_storage",
    "wall_decor": "lowpoly_wall_decor",
    "stool": "lowpoly_stool_rug",
}
GROUP_ORDER = ("alchemist", "workbench", "potion_shelf", "cauldron",
               "jar_shelf", "storage", "wall_decor", "stool")


def append_blend(path, exclude):
    """Append objects from a blend, link them, return the objects."""
    with bpy.data.libraries.load(path, link=False) as (data_from,
                                                       data_to):
        wanted = [n for n in data_from.objects if n not in exclude]
        data_to.objects = wanted
    objs = []
    for obj in data_to.objects:
        if obj is None:
            continue
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


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

    # 047 lab: everything except its Camera (keep its lights: studio
    # Key/Fill/Rim + CauldronGlow + SconceGlow point lights).
    lab_objs = append_blend(LAB_BLEND, {"Camera"})
    # 049 alchemist: meshes only (skip its Camera, its own studio
    # lights and its Ground plane - the lab already has those).
    alc_objs = append_blend(ALC_BLEND, {"Camera", "KeyLight", "FillLight",
                                        "RimLight", "Ground"})
    for obj in alc_objs:
        obj.location += ALC_OFFSET

    groups = {g: [] for g in GROUP_ORDER}
    for obj in alc_objs:
        assert obj.name in ALCHEMIST_NAMES, "unexpected 049 obj: %s" % obj.name
        groups["alchemist"].append(obj)
    assert len(groups["alchemist"]) == len(ALCHEMIST_NAMES), (
        "alchemist count %d != %d" % (len(groups["alchemist"]),
                                      len(ALCHEMIST_NAMES)))
    for obj in lab_objs:
        if obj.type != 'MESH':
            continue
        for g in GROUP_ORDER[1:]:
            if obj.name.startswith(PREFIXES[g]):
                groups[g].append(obj)
                break
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

    potion_bodies = [v for n, o in by_name.items()
                     if n.startswith("Potion_T") and n.endswith("_Body")
                     for v in mesh_world_verts(o)]
    jar_bodies = [v for n, o in by_name.items()
                  if n.startswith("Jar_T") and n.endswith("_Body")
                  for v in mesh_world_verts(o)]
    storage_verts = verts["storage"]
    decor_verts = verts["wall_decor"]
    stool_verts = (mesh_world_verts(by_name["Stool_Seat"])
                   + mesh_world_verts(by_name["StoolLeg_0"])
                   + mesh_world_verts(by_name["StoolLeg_1"])
                   + mesh_world_verts(by_name["StoolLeg_2"]))

    keypoints = {
        "alchemist": {
            "head_center": mean_point(mesh_world_verts(by_name["Head"])),
            "goggles_center": mean_point(
                mesh_world_verts(by_name["GoggleRim"])
                + mesh_world_verts(by_name["GoggleRim.001"])),
            "flask_center": mean_point(mesh_world_verts(by_name["Flask"])),
            "flask_liquid_center": mean_point(
                mesh_world_verts(by_name["FlaskLiquid"])),
            "belt_bottle_red_center": mean_point(
                mesh_world_verts(by_name["PotionRedBody"])),
        },
        "workbench": {
            "bench_top_center": mean_point(
                mesh_world_verts(by_name["Bench_Top"])),
            "mortar_center": mean_point(
                mesh_world_verts(by_name["Mortar"])),
            "alembic_flask_center": mean_point(
                mesh_world_verts(by_name["Alembic_Flask"])),
            "spellbook_left_center": mean_point(
                mesh_world_verts(by_name["Spellbook_Left"])),
            "bench_candle_flame": mean_point(
                mesh_world_verts(by_name["BenchCandle_Flame"])),
        },
        "potion_shelf": {
            "shelf_top_center": mean_point(
                mesh_world_verts(by_name["PotionShelf_Top"])),
            "potion_T0_0_center": mean_point(
                mesh_world_verts(by_name["Potion_T0_0_Body"])),
            "potion_T1_12_center": mean_point(
                mesh_world_verts(by_name["Potion_T1_12_Body"])),
            "shelfbook_0_center": mean_point(
                mesh_world_verts(by_name["ShelfBook_0"])),
            "potions_center": mean_point(potion_bodies),
        },
        "cauldron": {
            "hearth_center": mean_point(
                mesh_world_verts(by_name["Hearth_Slab"])),
            "cauldron_body_center": mean_point(
                mesh_world_verts(by_name["Cauldron_Body"])),
            "liquid_top": max(mesh_world_verts(by_name["Cauldron_Liquid"]),
                              key=lambda v: v.z),
            "bubble_0_center": mean_point(
                mesh_world_verts(by_name["Bubble_0"])),
            "ladle_center": mean_point(mesh_world_verts(by_name["Ladle"])),
        },
        "jar_shelf": {
            "jar_shelf_top_center": mean_point(
                mesh_world_verts(by_name["JarShelf_Top"])),
            "jar_T0_0_center": mean_point(
                mesh_world_verts(by_name["Jar_T0_0_Body"])),
            "jar_T1_8_center": mean_point(
                mesh_world_verts(by_name["Jar_T1_8_Body"])),
            "jars_center": mean_point(jar_bodies),
        },
        "storage": {
            "barrel_center": mean_point(mesh_world_verts(by_name["Barrel"])),
            "crate_0_center": mean_point(
                mesh_world_verts(by_name["Crate_0"])),
            "cratebottle_center": mean_point(
                mesh_world_verts(by_name["CrateBottle_Body"])),
            "storage_center": mean_point(storage_verts),
        },
        "wall_decor": {
            "chart_canvas_center": mean_point(
                mesh_world_verts(by_name["Chart_Canvas"])),
            "chart_circle_center": mean_point(
                mesh_world_verts(by_name["Chart_Circle"])),
            "herb_0_center": mean_point(
                mesh_world_verts(by_name["HerbLeaf_0_0"])),
            "sconce_flame": mean_point(
                mesh_world_verts(by_name["SconceCandle_Flame"])),
            "decor_center": mean_point(decor_verts),
        },
        "stool": {
            "stool_seat_center": mean_point(
                mesh_world_verts(by_name["Stool_Seat"])),
            "stool_ring_center": mean_point(
                mesh_world_verts(by_name["Stool_Ring"])),
            "rug_center": mean_point(mesh_world_verts(by_name["Rug"])),
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
        path = os.path.join(VIEW_DIR, "view052_%s.png" % name)
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
        "asset": "alchemy_lab_corner_training_data",
        "labels": [LABELS[g] for g in GROUP_ORDER],
        "source_blends": ["scenes/047-alchemy-lab-corner.blend",
                          "scenes/049-lowpoly-alchemist.blend"],
        "layout": ("047 lab scene used as-is, no repositioning: heavy "
                   "workbench against the back wall (center 0.3, 1.6) "
                   "with mortar & pestle, test tube rack, alembic, open "
                   "spellbook and candle; potion shelf above the bench "
                   "(2 tiers, 26 bottles + 4 small books); cauldron on "
                   "the hearth at (1.70, 0.55) with green liquid, "
                   "bubbles and ladle; jar shelf on the left wall "
                   "(2 tiers, 18 jars); barrel + 2 crates + crate "
                   "bottle in the left corner; alchemy star chart, 3 "
                   "hanging herb bundles and a wall sconce on the "
                   "walls; stool + rug in front of the bench. The 049 "
                   "alchemist stands on the rug at (-0.35, 0.60), left "
                   "of the stool, facing the front camera so the flask "
                   "he holds in front of him stays visible; back wall "
                   "y=+2.2 and left wall x=-2.2 are background, so no "
                   "back view - views are front / front-right diagonal "
                   "/ right side / high-left over the wall"),
        "image": "renders/052-training-data-sample.png",
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
