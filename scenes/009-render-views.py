# -*- coding: utf-8 -*-
"""009 3D 训练数据：多物体场景（宝剑 + 药水瓶）的多视角标注
Load the 001 sword and 005 potion from their .blend files into one scene,
render 4 views, and compute per-object bounding boxes and keypoints from
real camera projection (no invented numbers).
Run: blender --background --python 009-render-views.py
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

SWORD_BLEND = os.path.join(ROOT, "scenes", "001-lowpoly-sword.blend")
POTION_BLEND = os.path.join(ROOT, "scenes", "005-lowpoly-potion.blend")
ANN = os.path.join(ROOT, "scenes", "009-training-data-annotations.json")
BLEND_OUT = os.path.join(ROOT, "scenes",
                         "009-multi-object-training-data.blend")

SWORD_PARTS = ("Blade", "Guard", "Grip", "Pommel")
POTION_PARTS = ("Bottle", "Liquid", "Cork", "Label", "WaxSeal")

VIEWS = [
    ("front", (0.0, -7.5, 1.7), (0.0, 0.0, 1.3)),
    ("side", (7.5, 0.0, 1.7), (0.0, 0.0, 1.3)),
    ("back", (0.0, 7.5, 1.7), (0.0, 0.0, 1.3)),
    ("top45", (4.6, -4.6, 6.0), (0.0, 0.0, 1.2)),
]


def append_objects(blend_path, names):
    out = []
    for name in names:
        directory = blend_path + "/Object/"
        bpy.ops.wm.append(filepath=directory + name, directory=directory,
                          files=[{"name": name}])
        obj = bpy.context.scene.objects.get(name)
        assert obj is not None, "append failed: %s from %s" % (name, blend_path)
        out.append(obj)
    return out


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
    add_ground(size=30.0)  # wide ground: top45 view must not catch the edge
    studio_lights(target=(0, 0, 1.3))

    sword = append_objects(SWORD_BLEND, SWORD_PARTS)
    potion = append_objects(POTION_BLEND, POTION_PARTS)

    # Place the two props side by side on the ground, sword left, potion right.
    for o in sword:
        o.location.x -= 0.95
    for o in potion:
        o.location.x += 0.95
    # matrix_world is stale until the depsgraph is evaluated; refresh it
    # before reading world-space vertices for the annotations.
    bpy.context.view_layer.update()

    # Real keypoint anchors in world space (after placement).
    blade = next(o for o in sword if o.name == "Blade")
    guard = next(o for o in sword if o.name == "Guard")
    pommel = next(o for o in sword if o.name == "Pommel")
    bottle = next(o for o in potion if o.name == "Bottle")
    cork = next(o for o in potion if o.name == "Cork")
    wax = next(o for o in potion if o.name == "WaxSeal")

    sword_verts = []
    for o in sword:
        sword_verts += mesh_world_verts(o)
    potion_verts = []
    for o in potion:
        potion_verts += mesh_world_verts(o)

    blade_verts = mesh_world_verts(blade)
    guard_verts = mesh_world_verts(guard)
    pommel_verts = mesh_world_verts(pommel)
    bottle_verts = mesh_world_verts(bottle)
    cork_verts = mesh_world_verts(cork)
    wax_verts = mesh_world_verts(wax)

    sword_kp_world = {
        "tip": max(blade_verts, key=lambda v: v.z),
        "guard_left": min(guard_verts, key=lambda v: v.x),
        "guard_right": max(guard_verts, key=lambda v: v.x),
        "pommel": min(pommel_verts, key=lambda v: v.z),
    }
    potion_kp_world = {
        "cork_top": max(cork_verts, key=lambda v: v.z),
        "bottle_base_left": min(bottle_verts, key=lambda v: v.x),
        "bottle_base_right": max(bottle_verts, key=lambda v: v.x),
        "wax_seal_center": mean_point(wax_verts),
    }

    cam = make_camera("Camera", (0, -7.5, 1.7), (0, 0, 1.3), lens=50.0)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.eevee.taa_render_samples = 32

    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join("/tmp", "view009_%s.png" % name)
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
            "scene_bbox": bbox_of(scene, cam, sword_verts + potion_verts),
            "objects": [
                {
                    "label": "lowpoly_sword",
                    "bbox": bbox_of(scene, cam, sword_verts),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in sword_kp_world.items()},
                },
                {
                    "label": "lowpoly_potion",
                    "bbox": bbox_of(scene, cam, potion_verts),
                    "keypoints": {k: project(scene, cam, v)
                                  for k, v in potion_kp_world.items()},
                },
            ],
        })
        print("VIEW_ANN %s azimuth=%.1f elev=%.1f scene_bbox=%s" % (
            name, azimuth, elevation, views_out[-1]["scene_bbox"]))

    counts = {o.name: poly_count(o) for o in sword + potion}
    total = total_poly_count(sword + potion)
    print("MULTI_POLY total=%d" % total)
    for n, c in counts.items():
        print("MULTI_POLY %s=%d" % (n, c))

    ann = {
        "asset": "multi_object_sword_potion",
        "labels": ["lowpoly_sword", "lowpoly_potion"],
        "source_blends": ["scenes/001-lowpoly-sword.blend",
                          "scenes/005-lowpoly-potion.blend"],
        "layout": "sword at x=-0.95, potion at x=+0.95, both standing on z=0",
        "image": "renders/009-training-data-sample.png",
        "image_size": [1024, 1024],
        "coordinate_system": "normalized 0-1 within each view's own 512x512 panel, origin top-left, y down; 'panel' gives the view's [x, y, w, h] in the 1024x1024 sheet, so a full-sheet coordinate is (panel_x + bbox_x*512)/1024",
        "poly_counts": counts,
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
