# -*- coding: utf-8 -*-
"""018 低模游戏道具：圆盾（Round Shield）
Low-poly game round shield: domed wooden face (12 sides), iron rim ring,
domed steel boss, 12 brass rivets, wooden grip + brackets on the back.
Built with the dome axis along +Z at the origin, then rotated +90 deg
about X so the face points at the camera (-Y) and lifted to z=1.0.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 018-lowpoly-shield.py
"""
import os
import sys
import math
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, make_camera, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    export_wireframe_segments)


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


def box(name, center, size, mat):
    """Axis-aligned box from center + (sx, sy, sz). Outward winding."""
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return mesh_from_data(name, verts, faces, mat)


def tapered_cylinder(name, center, r_bottom, r_top, height, sides, mat):
    """Vertical (Z-axis) cylinder with different bottom/top radius.
    Caps are triangle fans from a center vertex (no N-gons)."""
    cx, cy, cz = center
    verts = []
    for z, r in ((cz - height / 2.0, r_bottom),
                 (cz + height / 2.0, r_top)):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((cx + r * math.cos(a),
                          cy + r * math.sin(a), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    verts.append((cx, cy, cz - height / 2.0))
    verts.append((cx, cy, cz + height / 2.0))
    c_bot, c_top = 2 * sides, 2 * sides + 1
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_bot, j, i))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_top, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def octahedron(name, center, radius, z_scale, mat):
    """Faceted 8-face crystal/rivet: 6 vertices, stretched along Z."""
    cx, cy, cz = center
    top = (cx, cy, cz + radius * z_scale)
    bottom = (cx, cy, cz - radius * z_scale)
    ring = []
    for i in range(4):
        a = math.pi / 4.0 + i * math.pi / 2.0
        ring.append((cx + radius * math.cos(a),
                     cy + radius * math.sin(a), cz))
    verts = [top, bottom] + ring
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((0, 2 + j, 2 + i))   # upper pyramid
        faces.append((1, 2 + i, 2 + j))   # lower pyramid
    return mesh_from_data(name, verts, faces, mat)


def domed_disc(name, sides, mat):
    """Shield face: 12-sided disc, gently domed toward +Z.
    Rings: (r=0.85, z=0.00), (r=0.84, z=0.05), (r=0.76, z=0.11),
    apex (0, 0, 0.26); flat back cap fan to (0, 0, -0.03)."""
    rings = [(0.85, 0.00), (0.84, 0.05), (0.76, 0.11)]
    verts = []
    for r, z in rings:
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(a), r * math.sin(a), z))
    apex = len(verts)
    verts.append((0.0, 0.0, 0.26))
    back = len(verts)
    verts.append((0.0, 0.0, -0.03))
    faces = []
    for k in range(len(rings) - 1):
        base0, base1 = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((base0 + i, base0 + j, base1 + j, base1 + i))
    top_ring = (len(rings) - 1) * sides
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((apex, top_ring + i, top_ring + j))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((back, j, i))
    return mesh_from_data(name, verts, faces, mat)


def torus(name, ring_radius, tube_radius, around, tube_sides, mat):
    """Low-poly torus, axis Z. Quad grid, outward winding."""
    verts = []
    for i in range(around):
        th = 2.0 * math.pi * i / around
        for j in range(tube_sides):
            ph = 2.0 * math.pi * j / tube_sides
            rr = ring_radius + tube_radius * math.cos(ph)
            verts.append((rr * math.cos(th), rr * math.sin(th),
                          tube_radius * math.sin(ph)))
    faces = []
    for i in range(around):
        i2 = (i + 1) % around
        for j in range(tube_sides):
            j2 = (j + 1) % tube_sides
            faces.append((i * tube_sides + j, i2 * tube_sides + j,
                          i2 * tube_sides + j2, i * tube_sides + j2))
    return mesh_from_data(name, verts, faces, mat)


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def stand_upright(obj):
    """Rotate +90 deg about X (dome axis +Z -> -Y, facing the camera)
    and lift the shield center to z=1.0."""
    obj.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    obj.location = (0.0, 0.0, 1.0)


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

    wood = solid_material("Shield_Wood", (0.55, 0.36, 0.18),
                          metallic=0.0, roughness=0.75)
    wood_dark = solid_material("Shield_WoodDark", (0.30, 0.19, 0.10),
                               metallic=0.0, roughness=0.85)
    iron = solid_material("Shield_Iron", (0.28, 0.28, 0.32),
                          metallic=0.85, roughness=0.35)
    steel = solid_material("Shield_Steel", (0.55, 0.57, 0.62),
                           metallic=0.9, roughness=0.25)
    brass = solid_material("Shield_Brass", (0.80, 0.62, 0.22),
                           metallic=0.9, roughness=0.3)

    parts = []
    # --- domed wooden face, 12 sides, radius 0.85 ---
    parts.append(domed_disc("Face", 12, wood))
    # --- iron rim ring around the edge ---
    parts.append(torus("Rim", 0.86, 0.05, 12, 6, iron))
    # --- steel boss: domed cap over the face apex ---
    parts.append(tapered_cylinder("Boss", (0, 0, 0.24),
                                  0.23, 0.07, 0.20, 8, steel))
    # --- 12 brass rivets on the dome, radius 0.68 ---
    # dome surface z at r=0.68: lerp between ring (0.76, 0.11) and
    # apex (0, 0.26): z = 0.26 - (0.68/0.76) * 0.15 = 0.126
    for k in range(12):
        a = 2.0 * math.pi * k / 12.0
        parts.append(octahedron(
            "Rivet_%02d" % k,
            (0.68 * math.cos(a), 0.68 * math.sin(a), 0.13),
            0.04, 1.0, brass))
    # --- back grip: horizontal bar + two brackets (behind the face) ---
    parts.append(box("Grip", (0, 0, -0.10), (0.55, 0.08, 0.07), wood_dark))
    parts.append(box("Bracket_L", (-0.20, 0, -0.06),
                     (0.06, 0.06, 0.08), wood_dark))
    parts.append(box("Bracket_R", (0.20, 0, -0.06),
                     (0.06, 0.06, 0.08), wood_dark))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    for obj in parts:
        stand_upright(obj)

    cam = make_camera("Camera", (3.0, -4.6, 2.1), (0, 0, 1.0), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "018-lowpoly-shield.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "018-lowpoly-shield.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "shield_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("SHIELD_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("SHIELD_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "018-lowpoly-shield.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 018 低模游戏道具：圆盾\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 盾面：12 边微凸圆盘，半径 0.85，顶点隆起至 z=0.26，木色\n")
        f.write("- 铁箍：低模圆环（12×6 段，管半径 0.05），沿盾沿一圈\n")
        f.write("- 盾心：8 边渐细钢质圆顶（底半径 0.23 → 顶 0.07，高 0.20），扣在盾面顶点\n")
        f.write("- 铆钉：12 颗黄铜八面体铆钉，沿半径 0.68 一圈均布，z 由盾面轮廓插值算出（0.13）\n")
        f.write("- 背面握把：横向木条（0.55 长）+ 两块连接支架，位于盾背\n")
        f.write("- 摆放：整盾绕 X 轴 +90° 立起，盾面朝向相机（-Y），中心高 1.0\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Shield_Wood：盾面木色（roughness 0.75）\n")
        f.write("- Shield_Iron：铁箍（metallic 0.85）\n")
        f.write("- Shield_Steel：钢质盾心（metallic 0.9，roughness 0.25）\n")
        f.write("- Shield_Brass：黄铜铆钉（metallic 0.9）\n")
        f.write("- Shield_WoodDark：背面握把深木色\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
