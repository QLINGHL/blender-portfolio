# -*- coding: utf-8 -*-
"""001 低模游戏道具：宝剑
Build a low-poly game sword (blade / guard / grip / pommel), render a beauty
shot and a wireframe shot with Eevee, save .blend + a description note.
Run: blender --background --python 001-lowpoly-sword.py
"""
import os
import sys
import math
import bpy
import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, wireframe_material,
                    make_world_gradient, add_ground, studio_lights,
                    make_camera, flat_shade, poly_count, total_poly_count,
                    setup_render, render, export_wireframe_segments)


def mesh_from_data(name, verts, faces, material=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    flat_shade(obj)
    return obj


def build_blade(mat):
    """Diamond cross-section blade, 4 rings + apex. Rings are CCW (top view)."""
    rings = [
        (0.52, 0.115, 0.040),
        (1.50, 0.105, 0.038),
        (2.15, 0.070, 0.030),
        (2.45, 0.012, 0.008),
    ]
    apex_z = 2.58
    verts, faces = [], []
    for z, w, t in rings:
        base = len(verts)
        verts += [(w, 0, z), (0, t, z), (-w, 0, z), (0, -t, z)]
        if base > 0:
            prev = base - 4
            for i in range(4):
                j = (i + 1) % 4
                faces.append((prev + i, prev + j, base + j, base + i))
    apex = len(verts)
    verts.append((0, 0, apex_z))
    last = apex - 4
    for i in range(4):
        j = (i + 1) % 4
        faces.append((apex, last + i, last + j))
    # bottom cap (base ring, normal -Z, hidden inside the guard)
    faces.append((3, 2, 1, 0))
    return mesh_from_data("Blade", verts, faces, mat)


def build_guard(mat):
    """Tapered crossguard box, 8 verts, 6 quad faces."""
    b = [(0.31, -0.06, 0.44), (0.31, 0.06, 0.44),
         (-0.31, 0.06, 0.44), (-0.31, -0.06, 0.44)]
    t = [(0.27, -0.05, 0.52), (0.27, 0.05, 0.52),
         (-0.27, 0.05, 0.52), (-0.27, -0.05, 0.52)]
    verts = b + t
    faces = [
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),  # sides
        (4, 5, 6, 7),  # top
        (3, 2, 1, 0),  # bottom
    ]
    return mesh_from_data("Guard", verts, faces, mat)


def build_grip(mat, sides=6, r=0.055, z0=0.13, z1=0.44):
    """Hexagonal grip tube, quad sides + triangle-fan caps (no ngons)."""
    verts, faces = [], []
    for z in (z0, z1):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    top_c = len(verts)
    verts.append((0, 0, z1))
    bot_c = len(verts)
    verts.append((0, 0, z0))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((top_c, sides + i, sides + j))   # top fan (+Z)
        faces.append((bot_c, j, i))                   # bottom fan (-Z)
    return mesh_from_data("Grip", verts, faces, mat)


def build_pommel(mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=5,
                                         radius=0.075, location=(0, 0, 0.075))
    obj = bpy.context.active_object
    obj.name = "Pommel"
    obj.data.materials.append(mat)
    flat_shade(obj)
    return obj


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.3))

    steel = solid_material("Blade_Steel", (0.72, 0.75, 0.80),
                           metallic=1.0, roughness=0.25)
    gold = solid_material("Guard_Gold", (0.80, 0.60, 0.20),
                          metallic=1.0, roughness=0.35)
    leather = solid_material("Grip_Leather", (0.14, 0.08, 0.04),
                             metallic=0.0, roughness=0.9)
    bronze = solid_material("Pommel_Bronze", (0.62, 0.42, 0.14),
                            metallic=1.0, roughness=0.4)

    blade = build_blade(steel)
    guard = build_guard(gold)
    grip = build_grip(leather)
    pommel = build_pommel(bronze)
    parts = [blade, guard, grip, pommel]

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = make_camera("Camera", (0, -5.0, 1.6), (0, 0, 1.3), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    # --- beauty render, then save .blend with beauty materials ---
    render(os.path.join(ROOT, "renders", "001-lowpoly-sword.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "001-lowpoly-sword.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "sword_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("SWORD_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("SWORD_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "001-lowpoly-sword.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 001 低模游戏道具：宝剑\n\n")
        f.write("低多边形游戏武器资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 剑身：菱形截面，4 段环 + 尖顶收束\n")
        f.write("- 剑格：横向护手，锥形收窄\n")
        f.write("- 剑柄：六边形握把，皮革材质\n")
        f.write("- 剑首：低多边形球形配重\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Blade_Steel：亮银金属（metallic 1.0，roughness 0.25）\n")
        f.write("- Guard_Gold：金色金属（metallic 1.0，roughness 0.35）\n")
        f.write("- Grip_Leather：深棕皮革（roughness 0.9）\n")
        f.write("- Pommel_Bronze：青铜金属（metallic 1.0，roughness 0.4）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
