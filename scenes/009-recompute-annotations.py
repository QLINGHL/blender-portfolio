# -*- coding: utf-8 -*-
"""009 标注重算（不重渲染）：打开已保存的 009 .blend，按 4 个视角重设
相机并刷新 depsgraph 后，用真实相机投影重算每个物体的包围盒与关键点，
修正首版脚本中 matrix_world 未刷新导致的标注偏移。
Run: blender --background --python 009-recompute-annotations.py
"""
import os
import json
import math
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLEND = os.path.join(ROOT, "scenes", "009-multi-object-training-data.blend")
ANN = os.path.join(ROOT, "scenes", "009-training-data-annotations.json")

SWORD_PARTS = ("Blade", "Guard", "Grip", "Pommel")
POTION_PARTS = ("Bottle", "Liquid", "Cork", "Label", "WaxSeal")

VIEWS = [
    ("front", (0.0, -7.5, 1.7), (0.0, 0.0, 1.3)),
    ("side", (7.5, 0.0, 1.7), (0.0, 0.0, 1.3)),
    ("back", (0.0, 7.5, 1.7), (0.0, 0.0, 1.3)),
    ("top45", (4.6, -4.6, 6.0), (0.0, 0.0, 1.2)),
]


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
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scene = bpy.context.scene
    sword = [scene.objects[n] for n in SWORD_PARTS]
    potion = [scene.objects[n] for n in POTION_PARTS]
    blade = scene.objects["Blade"]
    guard = scene.objects["Guard"]
    pommel = scene.objects["Pommel"]
    bottle = scene.objects["Bottle"]
    cork = scene.objects["Cork"]
    wax = scene.objects["WaxSeal"]

    sword_verts = []
    for o in sword:
        sword_verts += mesh_world_verts(o)
    potion_verts = []
    for o in potion:
        potion_verts += mesh_world_verts(o)

    sword_kp_world = {
        "tip": max(mesh_world_verts(blade), key=lambda v: v.z),
        "guard_left": min(mesh_world_verts(guard), key=lambda v: v.x),
        "guard_right": max(mesh_world_verts(guard), key=lambda v: v.x),
        "pommel": min(mesh_world_verts(pommel), key=lambda v: v.z),
    }
    potion_kp_world = {
        "cork_top": max(mesh_world_verts(cork), key=lambda v: v.z),
        "bottle_base_left": min(mesh_world_verts(bottle), key=lambda v: v.x),
        "bottle_base_right": max(mesh_world_verts(bottle), key=lambda v: v.x),
        "wax_seal_center": mean_point(mesh_world_verts(wax)),
    }

    cam = scene.camera
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512

    with open(ANN, encoding="utf-8") as f:
        ann = json.load(f)

    views_out = []
    for name, loc, target in VIEWS:
        cam.location = Vector(loc)
        direction = Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        dx, dy, dz = (Vector(loc) - Vector(target))
        azimuth = round(math.degrees(math.atan2(dx, -dy)) % 360.0, 1)
        horiz = math.hypot(dx, dy)
        elevation = round(math.degrees(math.atan2(dz, horiz)), 1)
        # keep the panel already filled by the compose step if present
        old = next((v for v in ann["views"] if v["view"] == name), {})
        views_out.append({
            "view": name,
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "panel": old.get("panel"),
            "scene_bbox": bbox_of(scene, cam, sword_verts + potion_verts),
            "objects": [
                {"label": "lowpoly_sword",
                 "bbox": bbox_of(scene, cam, sword_verts),
                 "keypoints": {k: project(scene, cam, v)
                               for k, v in sword_kp_world.items()}},
                {"label": "lowpoly_potion",
                 "bbox": bbox_of(scene, cam, potion_verts),
                 "keypoints": {k: project(scene, cam, v)
                               for k, v in potion_kp_world.items()}},
            ],
        })
        print("RECOMPUTED %s scene_bbox=%s sword=%s potion=%s" % (
            name, views_out[-1]["scene_bbox"],
            views_out[-1]["objects"][0]["bbox"],
            views_out[-1]["objects"][1]["bbox"]))

    ann["views"] = views_out
    with open(ANN, "w", encoding="utf-8") as f:
        json.dump(ann, f, indent=2)
    print("ANNOTATIONS_REWRITTEN:", ANN)


if __name__ == "__main__":
    main()
