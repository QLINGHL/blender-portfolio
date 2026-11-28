# -*- coding: utf-8 -*-
"""070 3D 训练数据：蒸馏器场景（068 蒸馏器 + 066 漏斗与量杯 + 049 炼金术士
+ 工作台）多视角标注
Load the 068 alembic still, 066 funnel & measuring beaker and 049
alchemist from their blends into a clean studio scene, render 4 views,
and compute per-object bounding boxes and keypoints from real camera
projection (no invented numbers).
Layout: the funnel & beaker stands on a small wooden worktable (right,
table top z 0.725); the alembic still stands on the floor (left); the
alchemist stands behind the table facing the front camera (-y) so the
flask he holds stays visible (049 lesson). No walls, so all four views
are usable.
Run: blender --background --python 070-render-views.py
(with the lavapipe env: VK_ICD_FILENAMES=~/workspace/blender/
vulkan-libs/lvp_icd.json, LD_LIBRARY_PATH=.../vulkan-libs/usr/lib/
x86_64-linux-gnu)
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
from common import (clear_scene, make_world_gradient, add_ground,
                    studio_lights, make_camera, solid_material,
                    flat_shade, poly_count, total_poly_count)

ALEMBIC_BLEND = os.path.join(ROOT, "scenes",
                             "068-lowpoly-alembic-still.blend")
FUNNEL_BLEND = os.path.join(ROOT, "scenes",
                            "066-lowpoly-funnel-beaker.blend")
ALC_BLEND = os.path.join(ROOT, "scenes", "049-lowpoly-alchemist.blend")
ANN = os.path.join(ROOT, "scenes", "070-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "070-still-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

# Placement (metres). Funnel & beaker base sits on the table top
# (z 0.725); the funnel rig is 0.44 wide, centred at x 0.50 it spans
# 0.28-0.72, inside the 0.90-wide table top (0.10-1.00). The alembic
# is 0.62 wide, centred at x -0.55 it spans -0.86 to -0.24.
TABLE_CENTER = Vector((0.55, -0.10, 0.0))
TABLE_TOP_Z = 0.725
FUNNEL_OFFSET = Vector((0.50, -0.10, TABLE_TOP_Z))
ALEMBIC_OFFSET = Vector((-0.55, -0.10, 0.0))
ALC_OFFSET = Vector((0.0, 0.55, 0.0))

TARGET = (0.0, 0.15, 0.95)
VIEWS = [
    ("front", (0.0, -6.0, 2.0), TARGET),
    ("diag", (4.5, -4.5, 3.2), TARGET),
    ("side", (6.3, 0.15, 2.0), TARGET),
    ("high", (-5.0, -2.5, 6.0), TARGET),
]

# Exact mesh names, verified by dumping the source blends.
ALEMBIC_NAMES = {
    "VapourArm", "StandRod", "StandRing", "RingArm",
    "RetortRimLip", "RetortLiquid", "RetortFlask",
    "Flame", "DripTube", "CondenserTube", "CondenserCoil",
    "CollectionLiquid", "CollectionFlask",
    "Collar_Neck", "Collar_Condenser",
    "BurnerWick", "Burner", "BaseBoard",
}
FUNNEL_NAMES = {
    "StandPost_R", "StandPost_L", "StandCrossbar", "StandBase",
    "RingArm_R", "RingArm_L",
    "MeasuringCup",
    "GradRing_1", "GradRing_2", "GradRing_3", "GradRing_4",
    "FunnelRing", "FunnelRimLip", "FunnelLiquid", "Funnel",
    "CupLiquid",
}
# Same 39 names as 052/057/065 (049 alchemist, after the 054 apron fix).
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

LABELS = {
    "alchemist": "lowpoly_alchemist",
    "alembic": "lowpoly_alembic_still",
    "funnel": "lowpoly_funnel_beaker",
    "worktable": "lowpoly_worktable",
}
GROUP_ORDER = ("alchemist", "alembic", "funnel", "worktable")


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


def build_worktable():
    """Small wooden worktable (same as 057/065): top + 4 legs, flat
    shaded. Top 0.90 x 0.60 x 0.05 centred at z 0.70, so its top face
    is 0.725. Legs 0.06 x 0.06 from z 0 to 0.70."""
    wood = solid_material("Table_Wood", (0.42, 0.30, 0.18),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Table_WoodDark", (0.30, 0.21, 0.12),
                               metallic=0.0, roughness=0.85)
    objs = []

    def box(name, center, size, mat):
        bpy.ops.mesh.primitive_cube_add(location=center)
        obj = bpy.context.active_object
        obj.name = name
        obj.dimensions = Vector(size)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        obj.data.materials.append(mat)
        flat_shade(obj)
        objs.append(obj)
        return obj

    box("Table_Top", (TABLE_CENTER.x, TABLE_CENTER.y, 0.70),
        (0.90, 0.60, 0.05), wood)
    for i, (dx, dy) in enumerate(((-0.38, -0.23), (0.38, -0.23),
                                  (-0.38, 0.23), (0.38, 0.23))):
        box("TableLeg_%d" % i,
            (TABLE_CENTER.x + dx, TABLE_CENTER.y + dy, 0.35),
            (0.06, 0.06, 0.70), wood_dark)
    return objs


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0.0, 0.15, 0.9))

    exclude = {"Camera", "KeyLight", "FillLight", "RimLight", "Ground"}
    alembic_objs = append_blend(ALEMBIC_BLEND, exclude)
    funnel_objs = append_blend(FUNNEL_BLEND, exclude)
    alc_objs = append_blend(ALC_BLEND, exclude)
    for obj in alembic_objs:
        obj.location += ALEMBIC_OFFSET
    for obj in funnel_objs:
        obj.location += FUNNEL_OFFSET
    for obj in alc_objs:
        obj.location += ALC_OFFSET
    table_objs = build_worktable()

    groups = {g: [] for g in GROUP_ORDER}
    for obj in alc_objs:
        assert obj.name in ALCHEMIST_NAMES, "unexpected 049 obj: %s" % obj.name
        groups["alchemist"].append(obj)
    for obj in alembic_objs:
        assert obj.name in ALEMBIC_NAMES, "unexpected 068 obj: %s" % obj.name
        groups["alembic"].append(obj)
    for obj in funnel_objs:
        assert obj.name in FUNNEL_NAMES, "unexpected 066 obj: %s" % obj.name
        groups["funnel"].append(obj)
    groups["worktable"] = table_objs
    for g, objs in groups.items():
        print("GROUP %s: %d objects" % (g, len(objs)))
        assert objs, "empty group: %s" % g
    assert len(groups["alchemist"]) == len(ALCHEMIST_NAMES)
    assert len(groups["alembic"]) == len(ALEMBIC_NAMES)
    assert len(groups["funnel"]) == len(FUNNEL_NAMES)

    bpy.context.view_layer.update()

    by_name = {o.name: o for g in groups.values() for o in g}
    verts = {g: [v for o in objs if o.type == 'MESH'
                 for v in mesh_world_verts(o)]
             for g, objs in groups.items()}

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
        "alembic": {
            "retort_flask_center": mean_point(
                mesh_world_verts(by_name["RetortFlask"])),
            "retort_liquid_center": mean_point(
                mesh_world_verts(by_name["RetortLiquid"])),
            "flame_center": mean_point(mesh_world_verts(by_name["Flame"])),
            "condenser_coil_center": mean_point(
                mesh_world_verts(by_name["CondenserCoil"])),
            "collection_flask_center": mean_point(
                mesh_world_verts(by_name["CollectionFlask"])),
            "collection_liquid_center": mean_point(
                mesh_world_verts(by_name["CollectionLiquid"])),
            "drip_tube_tip": min(mesh_world_verts(by_name["DripTube"]),
                                 key=lambda v: v.z),
            "stand_ring_center": mean_point(
                mesh_world_verts(by_name["StandRing"])),
        },
        "funnel": {
            "funnel_center": mean_point(mesh_world_verts(by_name["Funnel"])),
            "funnel_liquid_center": mean_point(
                mesh_world_verts(by_name["FunnelLiquid"])),
            "funnel_rim_center": mean_point(
                mesh_world_verts(by_name["FunnelRimLip"])),
            "measuring_cup_center": mean_point(
                mesh_world_verts(by_name["MeasuringCup"])),
            "cup_liquid_center": mean_point(
                mesh_world_verts(by_name["CupLiquid"])),
        },
        "worktable": {
            "table_top_center": mean_point(
                mesh_world_verts(by_name["Table_Top"])),
            "table_center": mean_point(
                mesh_world_verts(by_name["Table_Top"])
                + mesh_world_verts(by_name["TableLeg_0"])
                + mesh_world_verts(by_name["TableLeg_1"])
                + mesh_world_verts(by_name["TableLeg_2"])
                + mesh_world_verts(by_name["TableLeg_3"])),
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
        path = os.path.join(VIEW_DIR, "view070_%s.png" % name)
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
        "asset": "still_training_data",
        "labels": [LABELS[g] for g in GROUP_ORDER],
        "source_blends": ["scenes/068-lowpoly-alembic-still.blend",
                          "scenes/066-lowpoly-funnel-beaker.blend",
                          "scenes/049-lowpoly-alchemist.blend"],
        "layout": ("Studio scene, no walls: the 066 funnel & measuring "
                   "beaker stands on a small wooden worktable at (0.50, "
                   "-0.10), table top surface z 0.725; the 068 alembic "
                   "still stands on the floor at (-0.55, -0.10) with its "
                   "glass retort flask, copper condenser coil, spirit "
                   "lamp and collection flask; the 049 alchemist stands "
                   "behind the table at (0, 0.55) facing the front camera "
                   "so the flask he holds in front of him stays visible. "
                   "Ground plane + three-point studio lights. Views are "
                   "front / front-right diagonal / right side / high "
                   "from the left."),
        "image": "renders/070-training-data-sample.png",
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
