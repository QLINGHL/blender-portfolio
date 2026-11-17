# -*- coding: utf-8 -*-
"""004 3D 训练数据样本：加载 001 宝剑，渲染 4 个视角，用相机投影算出
真实包围盒与关键点（归一化坐标），写出标注 JSON。
Run: blender --background --python 004-render-views.py
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
BLEND = os.path.join(ROOT, "scenes", "001-lowpoly-sword.blend")
ANN = os.path.join(ROOT, "scenes", "004-training-data-annotations.json")

VIEWS = [
    ("front", (0.0, -6.0, 1.7), (0.0, 0.0, 1.3)),
    ("side", (6.0, 0.0, 1.7), (0.0, 0.0, 1.3)),
    ("back", (0.0, 6.0, 1.7), (0.0, 0.0, 1.3)),
    ("top45", (3.0, -3.0, 5.44), (0.0, 0.0, 1.2)),
]


def mesh_world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def project(scene, cam, co):
    """World -> normalized camera coords, y flipped to top-left origin."""
    x, y, depth = world_to_camera_view(scene, cam, Vector(co))
    return [round(x, 4), round(1.0 - y, 4)]


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scene = bpy.context.scene
    parts = [o for o in scene.objects
             if o.type == 'MESH' and o.name in ("Blade", "Guard", "Grip", "Pommel")]
    blade = next(o for o in parts if o.name == "Blade")
    guard = next(o for o in parts if o.name == "Guard")
    pommel = next(o for o in parts if o.name == "Pommel")

    # keypoints from the real meshes (world space)
    blade_verts = mesh_world_verts(blade)
    guard_verts = mesh_world_verts(guard)
    pommel_verts = mesh_world_verts(pommel)
    tip = max(blade_verts, key=lambda v: v.z)
    guard_left = min(guard_verts, key=lambda v: v.x)
    guard_right = max(guard_verts, key=lambda v: v.x)
    pommel_pt = min(pommel_verts, key=lambda v: v.z)
    all_verts = []
    for o in parts:
        all_verts += mesh_world_verts(o)

    cam = scene.camera
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
        path = os.path.join("/tmp", "view_%s.png" % name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("VIEW_RENDERED:", name, path)

        # bbox from all projected vertices
        xs, ys = [], []
        for v in all_verts:
            px, py = project(scene, cam, v)
            xs.append(px)
            ys.append(py)
        bbox = [round(min(xs), 4), round(min(ys), 4),
                round(max(xs), 4), round(max(ys), 4)]
        # azimuth / elevation of the camera relative to the target
        dx, dy, dz = (Vector(loc) - Vector(target))
        azimuth = round(math.degrees(math.atan2(dx, -dy)) % 360.0, 1)
        horiz = math.hypot(dx, dy)
        elevation = round(math.degrees(math.atan2(dz, horiz)), 1)
        views_out.append({
            "view": name,
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "panel": None,  # filled by the compose script
            "bbox": bbox,
            "keypoints": {
                "tip": project(scene, cam, tip),
                "guard_left": project(scene, cam, guard_left),
                "guard_right": project(scene, cam, guard_right),
                "pommel": project(scene, cam, pommel_pt),
            },
        })
        print("VIEW_ANN %s azimuth=%.1f elev=%.1f bbox=%s" % (
            name, azimuth, elevation, bbox))

    ann = {
        "asset": "lowpoly_sword",
        "label": "lowpoly_sword",
        "source_blend": "scenes/001-lowpoly-sword.blend",
        "image": "renders/004-training-data-sample.png",
        "image_size": [1024, 1024],
        "coordinate_system": "normalized 0-1, origin top-left, y down",
        "views": views_out,
    }
    with open(ANN, "w", encoding="utf-8") as f:
        json.dump(ann, f, indent=2)
    print("ANNOTATIONS_WRITTEN:", ANN)


if __name__ == "__main__":
    main()
