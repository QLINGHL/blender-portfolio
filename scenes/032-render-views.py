# -*- coding: utf-8 -*-
"""032 3D 训练数据：铁匠铺角落场景（铁砧 + 木桶 + 火盆）多视角标注
Load the anvil group, barrel and brazier from the 028 blacksmith-corner
blend into one clean training scene, render 4 views, and compute
per-object bounding boxes and keypoints from real camera projection
(no invented numbers).
Run: blender --background --python 032-render-views.py
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

CORNER_BLEND = os.path.join(ROOT, "scenes", "028-blacksmith-corner.blend")
ANN = os.path.join(ROOT, "scenes", "032-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "032-blacksmith-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

# Layout (metres): anvil left, barrel centre, brazier right.
# Anvil ~1.5 long, z 0-1.07; barrel 0.9 tall, radius ~0.53;
# brazier pedestal 0.45 + bowl, coals up to z~0.87.
# Source positions in 028: anvil group (-0.45, 0.35), barrel (2.0, -0.2),
# brazier (-1.75, 0.10).
LAYOUT = {
    "anvil": {"group": "AnvilGroup", "loc": (-2.2, 0.0, 0.0)},
    "barrel": {"offset": (-1.8, 0.2, 0.0)},
    "brazier": {"offset": (4.05, -0.10, 0.0)},
}
TARGET = (0.0, 0.0, 0.55)
VIEWS = [
    ("front", (0.0, -9.0, 2.2), (0.0, 0.0, 0.55)),
    ("side", (9.0, 0.0, 2.2), (0.0, 0.0, 0.55)),
    ("back", (0.0, 9.0, 2.2), (0.0, 0.0, 0.55)),
    ("top45", (6.0, -6.5, 7.5), (0.0, 0.0, 0.5)),
]

PREFIXES = {
    "anvil": ("Anvil_", "AnvilGroup"),
    "barrel": ("Barrel_",),
    "brazier": ("Brazier_", "Ember_"),
}


def append_corner_objects():
    """Append the labelled objects of the 028 blend (meshes + the
    anvil group empty), skipping Ground / Camera / lights."""
    with bpy.data.libraries.load(CORNER_BLEND, link=False) as (data_from,
                                                               data_to):
        wanted = []
        for n in data_from.objects:
            if n in ("Ground", "Camera", "ForgeGlow"):
                continue
            if n.startswith(("Anvil_", "Barrel_", "Brazier_", "Ember_")) \
                    or n == "AnvilGroup":
                wanted.append(n)
        data_to.objects = wanted
    groups = {"anvil": [], "barrel": [], "brazier": []}
    for obj in data_to.objects:
        if obj is None:
            continue
        bpy.context.scene.collection.objects.link(obj)
        for g, prefs in PREFIXES.items():
            if obj.name.startswith(prefs):
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
    add_ground(size=30.0, color=(0.55, 0.53, 0.49))
    studio_lights(target=(0.0, 0.0, 0.55))

    groups = append_corner_objects()
    for g, objs in groups.items():
        print("GROUP %s: %d objects" % (g, len(objs)))
        assert objs, "empty group: %s" % g

    # --- reposition: anvil group moves as a whole (children follow the
    # empty); barrel / brazier parts are top-level, shift each by the
    # same offset (the 019 LidBand_7 lesson: never move children too).
    anvil_group = bpy.data.objects["AnvilGroup"]
    anvil_group.location = Vector(LAYOUT["anvil"]["loc"])
    for g in ("barrel", "brazier"):
        off = Vector(LAYOUT[g]["offset"])
        for obj in groups[g]:
            if obj.parent is None:
                obj.location = Vector(obj.location) + off

    # Warm point light above the brazier coals (replaces 028 ForgeGlow).
    forge_light = bpy.data.lights.new("ForgeGlow", 'POINT')
    forge_light.energy = 250.0
    forge_light.color = (1.0, 0.55, 0.20)
    forge_light.shadow_soft_size = 0.3
    forge_obj = bpy.data.objects.new("ForgeGlow", forge_light)
    bpy.context.scene.collection.objects.link(forge_obj)
    forge_obj.location = (2.3, 0.0, 1.15)

    # matrix_world is stale until the depsgraph is evaluated; refresh it
    # before reading world-space vertices for the annotations.
    bpy.context.view_layer.update()

    by_name = {o.name: o for g in groups.values() for o in g}
    verts = {g: [v for o in objs if o.type == 'MESH'
                 for v in mesh_world_verts(o)]
             for g, objs in groups.items()}

    ember_verts = (mesh_world_verts(by_name["Ember_0"])
                   + mesh_world_verts(by_name["Ember_1"])
                   + mesh_world_verts(by_name["Ember_2"]))
    anvil_kp_world = {
        "horn_tip": max(mesh_world_verts(by_name["Anvil_Horn"]),
                        key=lambda v: v.x),
        "top_plate_center": mean_point(mesh_world_verts(
            by_name["Anvil_TopPlate"])),
        "heel_top": max(mesh_world_verts(by_name["Anvil_Heel"]),
                        key=lambda v: v.z),
        "hardy_hole": mean_point(mesh_world_verts(
            by_name["Anvil_HardyHole"])),
        "base_center": mean_point(mesh_world_verts(
            by_name["Anvil_Base"])),
    }
    barrel_kp_world = {
        "lid_center": mean_point(mesh_world_verts(
            by_name["Barrel_Lid"])),
        "top_rim": max(mesh_world_verts(by_name["Barrel_Top"]),
                       key=lambda v: v.z),
        "hoop_mid": mean_point(mesh_world_verts(
            by_name["Barrel_Hoop_45"])),
        "barrel_center": mean_point(mesh_world_verts(
            by_name["Barrel_Middle"])),
        "bottom_center": mean_point(mesh_world_verts(
            by_name["Barrel_Bottom"])),
    }
    brazier_kp_world = {
        "bowl_rim_top": max(mesh_world_verts(by_name["Brazier_Bowl"]),
                            key=lambda v: v.z),
        "ember_center": mean_point(ember_verts),
        "ember_front": max(mesh_world_verts(by_name["Ember_0"]),
                           key=lambda v: v.y),
        "pedestal_center": mean_point(mesh_world_verts(
            by_name["Brazier_Pedestal"])),
        "bowl_center": mean_point(mesh_world_verts(
            by_name["Brazier_Bowl"])),
    }
    keypoints = {"anvil": anvil_kp_world, "barrel": barrel_kp_world,
                 "brazier": brazier_kp_world}
    labels = {"anvil": "lowpoly_anvil", "barrel": "lowpoly_barrel",
              "brazier": "lowpoly_brazier"}

    cam = make_camera("Camera", (0, -13.5, 3.0), TARGET, lens=40.0)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.eevee.taa_render_samples = 16

    all_verts = verts["anvil"] + verts["barrel"] + verts["brazier"]
    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(VIEW_DIR, "view032_%s.png" % name)
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
                for g in ("anvil", "barrel", "brazier")
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
    print("GROUP_POLY", group_counts, "total=%d" % total)
    print("PER_OBJECT", per_object)

    ann = {
        "asset": "blacksmith_corner_training_data",
        "labels": ["lowpoly_anvil", "lowpoly_barrel", "lowpoly_brazier"],
        "source_blends": ["scenes/028-blacksmith-corner.blend"],
        "layout": ("anvil group at (-2.2, 0), rotated -20 deg, ~1.5 long "
                   "along x, z 0-1.07; barrel at (0.2, 0), 0.9 tall, "
                   "radius ~0.53; brazier at (2.3, 0), pedestal + bowl + "
                   "3 glowing coals, top z~0.87; objects renamed with "
                   "anvil_/barrel_/brazier_ prefixes because names "
                   "collide across source blends; only top-level objects "
                   "moved, children follow their parent"),
        "image": "renders/032-training-data-sample.png",
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
