# -*- coding: utf-8 -*-
"""015 3D 训练数据：小木屋场景（房屋 + 松树 + 岩石）的多视角标注
Load all objects from the 011 cabin .blend into one scene, render 4 views,
and compute per-object bounding boxes and keypoints from real camera
projection (no invented numbers).
Run: blender --background --python 015-render-views.py
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

CABIN_BLEND = os.path.join(ROOT, "scenes", "011-lowpoly-cabin.blend")
ANN = os.path.join(ROOT, "scenes", "015-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "015-cabin-training-data.blend")

VIEW_DIR = os.path.join(HERE, "tmp_views")
os.makedirs(VIEW_DIR, exist_ok=True)

# Group prefixes: cabin = house structure + door/windows/steps/path stones;
# pine = trunk + 3 cones; rocks = 3 icosphere rocks.
CABIN_PREFIXES = ("Log", "Gable", "Roof", "RidgeBeam", "Chimney",
                  "Door", "Step", "Window", "PathStone")
PINE_PREFIXES = ("Pine",)
ROCK_PREFIXES = ("Rock",)

# Scene centre (pine at x=-3.9, path stones to y=-5.0, chimney top z~4.1).
TARGET = (-0.5, -1.0, 1.8)
VIEWS = [
    ("front", (-0.5, -13.5, 3.0), (-0.5, -1.0, 1.8)),
    ("side", (12.5, -1.0, 3.0), (-0.5, -1.0, 1.8)),
    ("back", (-0.5, 11.5, 3.0), (-0.5, -1.0, 1.8)),
    ("top45", (8.0, -9.5, 10.5), (-0.5, -1.0, 1.5)),
]


def group_of(name):
    if name.startswith(CABIN_PREFIXES):
        return "cabin"
    if name.startswith(PINE_PREFIXES):
        return "pine"
    if name.startswith(ROCK_PREFIXES):
        return "rocks"
    return None


def append_cabin_objects(blend_path):
    """Append only the labelled mesh objects from the cabin blend."""
    with bpy.data.libraries.load(blend_path, link=False) as (data_from,
                                                             data_to):
        data_to.objects = [n for n in data_from.objects
                           if group_of(n) is not None]
    groups = {"cabin": [], "pine": [], "rocks": []}
    for obj in data_to.objects:
        if obj is None or obj.type != 'MESH':
            continue
        bpy.context.scene.collection.objects.link(obj)
        groups[group_of(obj.name)].append(obj)
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


def family_of(name):
    """Coarse part family for the cabin poly-count breakdown."""
    for fam in ("Log", "Gable", "Roof", "RidgeBeam", "Chimney",
                "Door", "Step", "Window", "PathStone"):
        if name.startswith(fam):
            return fam
    return "other"


def main():
    clear_scene()
    make_world_gradient()
    add_ground(size=30.0, color=(0.42, 0.60, 0.30))
    studio_lights(target=(0, -0.5, 1.8))

    groups = append_cabin_objects(CABIN_BLEND)
    for g, objs in groups.items():
        print("GROUP %s: %d objects" % (g, len(objs)))
        assert objs, "empty group: %s" % g
    # matrix_world is stale until the depsgraph is evaluated; refresh it
    # before reading world-space vertices for the annotations.
    bpy.context.view_layer.update()

    cabin = groups["cabin"]
    pine = groups["pine"]
    rocks = groups["rocks"]
    by_name = {o.name: o for g in groups.values() for o in g}

    cabin_verts = []
    for o in cabin:
        cabin_verts += mesh_world_verts(o)
    pine_verts = []
    for o in pine:
        pine_verts += mesh_world_verts(o)
    rocks_verts = []
    for o in rocks:
        rocks_verts += mesh_world_verts(o)

    ridge = by_name["RidgeBeam"]
    chimney_top = by_name["Chimney_Top"]
    door_panel = by_name["Door_Panel"]
    door_handle = by_name["Door_Handle"]
    cone_top = by_name["Pine_Cone_2"]
    cone_mid = by_name["Pine_Cone_1"]
    trunk = by_name["Pine_Trunk"]

    cabin_kp_world = {
        "roof_peak": max(mesh_world_verts(ridge), key=lambda v: v.z),
        "chimney_top": max(mesh_world_verts(chimney_top),
                           key=lambda v: v.z),
        "door_top": max(mesh_world_verts(door_panel), key=lambda v: v.z),
        "door_handle": mean_point(mesh_world_verts(door_handle)),
    }
    pine_kp_world = {
        "tree_top": max(mesh_world_verts(cone_top), key=lambda v: v.z),
        "trunk_base": min(mesh_world_verts(trunk), key=lambda v: v.z),
        "canopy_left": min(mesh_world_verts(cone_mid), key=lambda v: v.x),
        "canopy_right": max(mesh_world_verts(cone_mid), key=lambda v: v.x),
    }
    rocks_kp_world = {
        "rock0_top": max(mesh_world_verts(by_name["Rock_0"]),
                         key=lambda v: v.z),
        "rock1_top": max(mesh_world_verts(by_name["Rock_1"]),
                         key=lambda v: v.z),
        "rock2_top": max(mesh_world_verts(by_name["Rock_2"]),
                         key=lambda v: v.z),
        "rocks_center": mean_point(rocks_verts),
    }

    cam = make_camera("Camera", (0, -13.5, 3.0), TARGET, lens=40.0)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.eevee.taa_render_samples = 16

    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(VIEW_DIR, "view015_%s.png" % name)
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
            "scene_bbox": bbox_of(scene, cam,
                                  cabin_verts + pine_verts + rocks_verts),
            "objects": [
                {
                    "label": "lowpoly_cabin",
                    "bbox": bbox_of(scene, cam, cabin_verts),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in cabin_kp_world.items()},
                },
                {
                    "label": "lowpoly_pine",
                    "bbox": bbox_of(scene, cam, pine_verts),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in pine_kp_world.items()},
                },
                {
                    "label": "lowpoly_rocks",
                    "bbox": bbox_of(scene, cam, rocks_verts),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in rocks_kp_world.items()},
                },
            ],
        })
        print("VIEW_ANN %s azimuth=%.1f elev=%.1f scene_bbox=%s" % (
            name, azimuth, elevation, views_out[-1]["scene_bbox"]))

    # Poly counts: per-group totals + cabin family breakdown + pine/rocks
    # per-object counts (all measured, not invented).
    group_counts = {g: total_poly_count(objs)
                    for g, objs in groups.items()}
    cabin_families = {}
    for o in cabin:
        fam = family_of(o.name)
        cabin_families[fam] = cabin_families.get(fam, 0) + poly_count(o)
    small_counts = {o.name: poly_count(o) for o in pine + rocks}
    total = sum(group_counts.values())
    print("GROUP_POLY", group_counts, "total=%d" % total)
    print("CABIN_FAMILIES", cabin_families)
    print("SMALL_POLY", small_counts)

    ann = {
        "asset": "cabin_scene_training_data",
        "labels": ["lowpoly_cabin", "lowpoly_pine", "lowpoly_rocks"],
        "source_blends": ["scenes/011-lowpoly-cabin.blend"],
        "layout": ("cabin at origin (footprint 4.0 x 3.0 m, chimney top "
                   "z~4.1); pine at (-3.9, -0.8); rocks at (-2.6, -2.4), "
                   "(2.9, 1.6), (3.3, -1.4); stone path from door toward "
                   "-y; lowpoly_cabin group includes the house structure, "
                   "door/windows/steps and the path stones"),
        "image": "renders/015-training-data-sample.png",
        "image_size": [1024, 1024],
        "coordinate_system": "normalized 0-1 within each view's own 512x512 panel, origin top-left, y down; 'panel' gives the view's [x, y, w, h] in the 1024x1024 sheet, so a full-sheet coordinate is (panel_x + bbox_x*512)/1024",
        "poly_counts": {
            "groups": group_counts,
            "cabin_families": cabin_families,
            "pine_and_rocks": small_counts,
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
