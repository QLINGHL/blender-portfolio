# -*- coding: utf-8 -*-
"""013 低模游戏道具：魔法杖（Magic Staff）
Low-poly game magic staff: tapered wooden shaft, faceted octahedron
crystal head held by three metal prongs, brass bands, metal pommel cap.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 013-lowpoly-staff.py
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
    """Faceted 8-face crystal: 6 vertices, stretched along Z."""
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


def crystal_material(name, color):
    """Bright faceted crystal: Principled + a touch of emission so the
    head glows against the dark wood."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.12
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.35
    return mat


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
    studio_lights(target=(0, 0, 1.7))

    wood = solid_material("Staff_Wood", (0.32, 0.20, 0.10),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Staff_WoodDark", (0.22, 0.13, 0.06),
                               metallic=0.0, roughness=0.85)
    brass = solid_material("Brass_Band", (0.80, 0.62, 0.22),
                           metallic=0.9, roughness=0.3)
    iron = solid_material("Iron_Prong", (0.25, 0.25, 0.28),
                          metallic=0.85, roughness=0.35)
    crystal = crystal_material("Crystal_Head", (0.15, 0.65, 0.90))
    crystal_small = crystal_material("Crystal_Small", (0.45, 0.80, 0.95))

    parts = []
    # --- shaft: tapered, 2.9 tall, standing on the ground ---
    # bottom z=0.0, top z=2.9; radius 0.11 -> 0.08
    parts.append(tapered_cylinder("Shaft", (0, 0, 1.45),
                                  0.11, 0.08, 2.9, 8, wood))
    # --- grip wrap: slightly thicker dark band in the middle ---
    parts.append(tapered_cylinder("Grip", (0, 0, 1.35),
                                  0.13, 0.12, 0.55, 8, wood_dark))
    # --- brass bands: top collar + bottom collar + grip rings ---
    parts.append(tapered_cylinder("Band_Top", (0, 0, 2.86),
                                  0.115, 0.115, 0.10, 8, brass))
    parts.append(tapered_cylinder("Band_Bottom", (0, 0, 0.12),
                                  0.13, 0.13, 0.10, 8, brass))
    parts.append(tapered_cylinder("Band_GripTop", (0, 0, 1.66),
                                  0.135, 0.135, 0.05, 8, brass))
    parts.append(tapered_cylinder("Band_GripBottom", (0, 0, 1.04),
                                  0.135, 0.135, 0.05, 8, brass))
    # --- pommel: small metal cap + tiny crystal at the butt end ---
    parts.append(tapered_cylinder("Pommel_Cap", (0, 0, 0.03),
                                  0.12, 0.10, 0.06, 8, brass))
    parts.append(octahedron("Pommel_Gem", (0, 0, -0.06), 0.07, 1.3,
                            crystal_small))
    # --- crystal head: octahedron, center z=3.35, radius 0.34 ---
    parts.append(octahedron("Crystal", (0, 0, 3.35), 0.34, 1.45, crystal))
    # --- seat: small brass cup under the crystal ---
    parts.append(tapered_cylinder("Crystal_Seat", (0, 0, 2.98),
                                  0.10, 0.16, 0.12, 8, brass))
    # --- three prongs: thin tapered iron bars leaning inward, holding
    # the crystal. Each prong runs from the seat rim (r=0.15, z=3.02)
    # up to the crystal equator (r=0.30, z=3.35), tilted ~35 deg.
    for k in range(3):
        a = math.pi / 2.0 + k * 2.0 * math.pi / 3.0
        x0, y0 = 0.15 * math.cos(a), 0.15 * math.sin(a)
        x1, y1 = 0.30 * math.cos(a), 0.30 * math.sin(a)
        mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        mz = (3.02 + 3.35) / 2.0
        # Build the prong mesh around the LOCAL origin and place it with
        # obj.location: mesh_from_data bakes the center into the vertices,
        # so rotating an object built at (mx, my, mz) would swing it around
        # the world origin instead of its own center.
        prong = tapered_cylinder("Prong_%d" % k, (0, 0, 0),
                                 0.035, 0.025, 0.42, 4, iron)
        prong.location = (mx, my, mz)
        # tilt around the axis perpendicular to the radial direction
        dx, dy = x1 - x0, y1 - y0
        tilt = math.atan2(math.hypot(dx, dy), 3.35 - 3.02)
        prong.rotation_euler[0] = -dy / math.hypot(dx, dy) * tilt
        prong.rotation_euler[1] = dx / math.hypot(dx, dy) * tilt
        parts.append(prong)
    # --- small floating shard orbiting the crystal head ---
    parts.append(octahedron("Shard", (0.55, 0.25, 3.55), 0.09, 1.5,
                            crystal_small))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    cam = make_camera("Camera", (4.0, -4.2, 2.9), (0, 0, 1.8), lens=35.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "013-lowpoly-staff.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "013-lowpoly-staff.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "staff_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("STAFF_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("STAFF_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "013-lowpoly-staff.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 013 低模游戏道具：魔法杖\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 杖身：8 边渐细圆柱，高 2.9，底半径 0.11 → 顶 0.08，深木色\n")
        f.write("- 握把：中段深色缠绕段（高 0.55），上下各一道黄铜箍\n")
        f.write("- 水晶头：八面体水晶（8 面），中心 z=3.35，纵向拉长 1.45 倍，带轻微自发光\n")
        f.write("- 爪托：3 根铁质细爪，从底座斜向上扣住水晶赤道，120° 均布\n")
        f.write("- 底座：黄铜杯托（水晶下方）+ 杖首 / 杖尾黄铜箍\n")
        f.write("- 杖尾：黄铜底帽 + 一颗小八面体水晶\n")
        f.write("- 漂浮碎片：水晶头旁一颗小八面体碎片（0.55, 0.25, 3.55）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Staff_Wood：杖身木色（roughness 0.8）\n")
        f.write("- Staff_WoodDark：握把深木色\n")
        f.write("- Brass_Band：黄铜箍 / 底座（metallic 0.9）\n")
        f.write("- Iron_Prong：铁爪（metallic 0.85）\n")
        f.write("- Crystal_Head：蓝色水晶（roughness 0.12，自发光 0.35）\n")
        f.write("- Crystal_Small：浅色小水晶（杖尾 + 漂浮碎片）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，35mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
