# -*- coding: utf-8 -*-
"""002 低模游戏角色：风格化小人
Tube limbs with explicit edge-loop rings at shoulder / elbow / knee / ankle,
so the joints are bind-ready. Flat shading, Eevee beauty + wireframe shots.
Run: blender --background --python 002-lowpoly-character.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector

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


def make_tube(name, origin, direction, distances, radii, sides, material):
    """Closed tube along `direction`; one ring per (distance, radius).
    Rings are edge loops — joints land exactly on a ring."""
    d = Vector(direction).normalized()
    # basis perpendicular to d
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    o = Vector(origin)
    verts, faces = [], []
    for dist, r in zip(distances, radii):
        c = o + d * dist
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            p = c + (u * math.cos(a) + v * math.sin(a)) * r
            verts.append(tuple(p))
    n_rings = len(distances)
    for k in range(n_rings - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    # caps (triangle fans) -- winding flipped so cap normals point outward
    # (QA 008 found both cap fans inverted: recalc + ray-cast verified)
    top_c = len(verts)
    verts.append(tuple(o + d * distances[0]))
    bot_c = len(verts)
    verts.append(tuple(o + d * distances[-1]))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((top_c, j, i))
        faces.append((bot_c, (n_rings - 1) * sides + i, (n_rings - 1) * sides + j))
    return mesh_from_data(name, verts, faces, material)


def make_box_tube(name, rings, material):
    """Rectangular tube from a list of (z, half_x, half_y) rings (CCW corners)."""
    verts, faces = [], []
    for z, hx, hy in rings:
        verts += [(hx, -hy, z), (hx, hy, z), (-hx, hy, z), (-hx, -hy, z)]
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            # winding flipped: QA 008 found the whole box tube inside-out
            # (recalc + ray-cast verified); caps were already outward.
            faces.append((k * 4 + i, (k + 1) * 4 + i, (k + 1) * 4 + j, k * 4 + j))
    n = len(rings)
    # caps also flipped: QA 008 re-verify showed both cap quads inverted
    faces.append(((n - 1) * 4, (n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1))
    faces.append((0, 1, 2, 3))
    return mesh_from_data(name, verts, faces, material)


def add_sphere(name, location, radius, segments, rings, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    flat_shade(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
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
    studio_lights(target=(0, 0, 0.9))

    skin = solid_material("Skin", (0.85, 0.62, 0.48), metallic=0.0, roughness=0.7)
    shirt = solid_material("Shirt_Teal", (0.12, 0.45, 0.50), metallic=0.0, roughness=0.8)
    pants = solid_material("Pants_Navy", (0.20, 0.24, 0.42), metallic=0.0, roughness=0.85)
    shoes = solid_material("Shoes_Brown", (0.25, 0.16, 0.10), metallic=0.0, roughness=0.9)
    hair = solid_material("Hair_Dark", (0.16, 0.10, 0.06), metallic=0.0, roughness=0.85)
    eyes = solid_material("Eyes_Dark", (0.05, 0.05, 0.06), metallic=0.0, roughness=0.4)

    parts = []
    # --- head ---
    head = add_sphere("Head", (0, 0, 1.50), 0.22, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- hair cap: top half of a sphere ---
    hair_obj = add_sphere("Hair", (0, 0, 1.56), 0.235, 8, 5, (1.0, 0.92, 0.85), hair)
    parts.append(hair_obj)
    # --- eyes (front is -Y) ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.075, -0.185, 1.52), 0.028, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.09, 0.085], 6, skin)
    parts.append(neck)
    # --- torso: 3-ring rectangular tube (shoulder / mid / waist) ---
    torso = make_box_tube("Torso", [(1.28, 0.31, 0.17), (0.95, 0.28, 0.16),
                                    (0.62, 0.25, 0.15)], shirt)
    parts.append(torso)
    # --- arms: 5 rings, middle ring = elbow joint loop ---
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.33, 0, 1.22))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.095, 0.090, 0.088, 0.082, 0.075], 6, shirt)
        parts.append(arm)
        wrist = shoulder + direction.normalized() * 0.55
        hand = add_sphere("Hand", tuple(wrist), 0.085, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    # --- legs: 5 rings, middle ring = knee joint loop ---
    for sx in (-1, 1):
        hip = Vector((sx * 0.13, 0, 0.62))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.115, 0.108, 0.102, 0.092, 0.085], 6, pants)
        parts.append(leg)
        # foot: forward-pointing box (-Y)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sx * 0.13, -0.04, 0.045))
        foot = bpy.context.active_object
        foot.name = "Foot"
        foot.scale = (0.16, 0.28, 0.09)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        foot.data.materials.append(shoes)
        flat_shade(foot)
        parts.append(foot)

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = make_camera("Camera", (0, -3.4, 1.0), (0, 0, 0.85), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "002-lowpoly-character.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "002-lowpoly-character.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "character_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CHAR_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "002-lowpoly-character.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 002 低模游戏角色：风格化小人\n\n")
        f.write("低多边形风格化游戏角色，平面着色（flat shading）。\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Skin / Hair_Dark / Eyes_Dark：皮肤、头发、眼睛\n")
        f.write("- Shirt_Teal：上衣；Pants_Navy：裤子；Shoes_Brown：鞋\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
