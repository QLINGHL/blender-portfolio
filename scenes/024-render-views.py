# -*- coding: utf-8 -*-
"""024 3D 训练数据：多物体场景（铁砧 + 圆盾 + 药水瓶）的多视角标注
Load the objects from the 023 anvil, 018 shield and 005 potion blends into
one scene, render 4 views, and compute per-object bounding boxes and
keypoints from real camera projection (no invented numbers).
Run: blender --background --python 024-render-views.py
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
from common import (clear_scene, make_world_gradient, add_ground,
                    studio_lights, make_camera, poly_count,
                    total_poly_count)

ANVIL_BLEND = os.path.join(ROOT, "scenes", "023-lowpoly-anvil.blend")
SHIELD_BLEND = os.path.join(ROOT, "scenes", "018-lowpoly-shield.blend")
POTION_BLEND = os.path.join(ROOT, "scenes", "005-lowpoly-potion.blend")
ANN = os.path.join(ROOT, "scenes", "024-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "024-anvil-scene-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

# Layout (metres): anvil left, shield centre, potion right.
# Anvil 2.30 long along x, z 0-1.07; shield disc faces +/-y, centre z~1.0,
# radius ~0.91; potion 1.62 tall, radius ~0.36.
SOURCES = [
    ("anvil", ANVIL_BLEND, (-2.3, 0.0, 0.0)),
    ("shield", SHIELD_BLEND, (0.4, 0.3, 0.0)),
    ("potion", POTION_BLEND, (2.4, 0.0, 0.0)),
]
TARGET = (0.0, 0.0, 1.0)
VIEWS = [
    ("front", (0.0, -9.0, 2.6), (0.0, 0.0, 1.0)),
    ("side", (9.0, 0.0, 2.6), (0.0, 0.0, 1.0)),
    ("back", (0.0, 9.0, 2.6), (0.0, 0.0, 1.0)),
    ("top45", (6.0, -6.5, 7.5), (0.0, 0.0, 0.8)),
]


def append_group(blend_path, prefix, offset):
    """Append the labelled mesh objects of one blend, prefix their names
    (names collide across blends, e.g. 'Grip' in shield and others),
    move the whole group by offset, and link them into the scene."""
    with bpy.data.libraries.load(blend_path, link=False) as (data_from,
                                                             data_to):
        data_to.objects = [n for n in data_from.objects
                           if n != "Ground"]
    objs = []
    for obj in data_to.objects:
        if obj is None or obj.type != 'MESH':
            continue
        obj.name = prefix + "_" + obj.name
        # Only move top-level objects: children inherit the offset through
        # the parent. Moving them too would double the offset and detach
        # them (the 019 LidBand_7 lesson).
        if obj.parent is None:
            obj.location = Vector(obj.location) + Vector(offset)
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
    add_ground(size=30.0, color=(0.55, 0.53, 0.49))
    studio_lights(target=(0.0, 0.0, 1.0))

    groups = {}
    for prefix, blend, offset in SOURCES:
        groups[prefix] = append_group(blend, prefix, offset)
        print("GROUP %s: %d objects" % (prefix, len(groups[prefix])))
        assert groups[prefix], "empty group: %s" % prefix
    # matrix_world is stale until the depsgraph is evaluated; refresh it
    # before reading world-space vertices for the annotations.
    bpy.context.view_layer.update()

    by_name = {o.name: o for g in groups.values() for o in g}
    verts = {g: [v for o in objs for v in mesh_world_verts(o)]
             for g, objs in groups.items()}

    anvil_kp_world = {
        "horn_tip": max(mesh_world_verts(by_name["anvil_Horn"]),
                        key=lambda v: v.x),
        "top_plate_center": mean_point(mesh_world_verts(
            by_name["anvil_TopPlate"])),
        "heel_top": max(mesh_world_verts(by_name["anvil_Heel"]),
                        key=lambda v: v.z),
        "hardy_hole": mean_point(mesh_world_verts(
            by_name["anvil_HardyHole"])),
        "base_center": mean_point(mesh_world_verts(
            by_name["anvil_Base"])),
    }
    shield_kp_world = {
        "boss_center": mean_point(mesh_world_verts(by_name["shield_Boss"])),
        "rim_top": max(mesh_world_verts(by_name["shield_Rim"]),
                       key=lambda v: v.z),
        "rim_left": min(mesh_world_verts(by_name["shield_Rim"]),
                        key=lambda v: v.x),
        "rim_right": max(mesh_world_verts(by_name["shield_Rim"]),
                         key=lambda v: v.x),
        "face_center": mean_point(mesh_world_verts(by_name["shield_Face"])),
    }
    potion_kp_world = {
        "cork_top": max(mesh_world_verts(by_name["potion_Cork"]),
                        key=lambda v: v.z),
        "liquid_center": mean_point(mesh_world_verts(
            by_name["potion_Liquid"])),
        "label_center": mean_point(mesh_world_verts(
            by_name["potion_Label"])),
        "wax_seal": mean_point(mesh_world_verts(
            by_name["potion_WaxSeal"])),
        "bottle_base": min(mesh_world_verts(by_name["potion_Bottle"]),
                           key=lambda v: v.z),
    }
    keypoints = {"anvil": anvil_kp_world, "shield": shield_kp_world,
                 "potion": potion_kp_world}
    labels = {"anvil": "lowpoly_anvil", "shield": "lowpoly_shield",
              "potion": "lowpoly_potion"}

    cam = make_camera("Camera", (0, -13.5, 3.0), TARGET, lens=40.0)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.eevee.taa_render_samples = 16

    all_verts = verts["anvil"] + verts["shield"] + verts["potion"]
    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(VIEW_DIR, "view024_%s.png" % name)
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
                    "label": labels[g],
                    "bbox": bbox_of(scene, cam, verts[g]),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in keypoints[g].items()},
                }
                for g in ("anvil", "shield", "potion")
            ],
        })
        print("VIEW_ANN %s azimuth=%.1f elev=%.1f scene_bbox=%s" % (
            name, azimuth, elevation, views_out[-1]["scene_bbox"]))

    # Poly counts: per-group totals + per-object counts (all measured).
    group_counts = {g: total_poly_count(objs)
                    for g, objs in groups.items()}
    per_object = {o.name: poly_count(o)
                  for g in groups.values() for o in g}
    total = sum(group_counts.values())
    print("GROUP_POLY", group_counts, "total=%d" % total)
    print("PER_OBJECT", per_object)

    ann = {
        "asset": "anvil_scene_training_data",
        "labels": ["lowpoly_anvil", "lowpoly_shield", "lowpoly_potion"],
        "source_blends": ["scenes/023-lowpoly-anvil.blend",
                          "scenes/018-lowpoly-shield.blend",
                          "scenes/005-lowpoly-potion.blend"],
        "layout": ("anvil at (-2.3, 0), 2.30 long along x, z 0-1.07; shield "
                   "at (0.4, 0.3), disc facing +/-y, centre z~1.0, radius "
                   "~0.91; potion at (2.4, 0), 1.62 tall, radius ~0.36; "
                   "objects renamed with anvil_/shield_/potion_ prefixes "
                   "because names collide across source blends"),
        "image": "renders/024-training-data-sample.png",
        "image_size": [1024, 1024],
        "coordinate_system": "normalized 0-1 within each view's own 512x512 panel, origin top-left, y down; 'panel' gives the view's [x, y, w, h] in the 1024x1024 sheet, so a full-sheet coordinate is (panel_x + bbox_x*512)/1024",
        "poly_counts": {
            "groups": group_counts,
            "per_object": per_object,
        },
        "total_polys": total,
        "views": views_out,
    }
    with open(ANN, "w", encoding="utf-8") as f:
        json.dump(ann, f, indent=2)
    print("ANNOTATIONS_WRITTEN:", ANN)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print("BLEND_SAVED:", BLEND_OUT)


if __name__ == "__main__":
    main()
