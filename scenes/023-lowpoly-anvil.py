# -*- coding: utf-8 -*-
"""023 低模游戏道具：铁砧（Anvil）
Low-poly game anvil: stepped iron base, tapered waist, steel body,
polished top plate, tapered horn (+X), square heel (-X), hardy (square)
and pritchel (round) holes on the top face.
Length along X, ~2.3 m overall, height ~1.07 m.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 023-lowpoly-anvil.py
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


def tapered_box(name, center, bottom_size, top_size, height, mat):
    """Box whose top rectangle is smaller than the bottom one.
    Bottom at cz-height/2, top at cz+height/2. Outward winding."""
    cx, cy, cz = center
    bx, by = bottom_size[0] / 2.0, bottom_size[1] / 2.0
    tx, ty = top_size[0] / 2.0, top_size[1] / 2.0
    zb, zt = cz - height / 2.0, cz + height / 2.0
    verts = [
        (cx - bx, cy - by, zb), (cx + bx, cy - by, zb),
        (cx + bx, cy + by, zb), (cx - bx, cy + by, zb),
        (cx - tx, cy - ty, zt), (cx + tx, cy - ty, zt),
        (cx + tx, cy + ty, zt), (cx - tx, cy + ty, zt),
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
    studio_lights(target=(0, 0, 0.55))

    steel = solid_material("Anvil_Steel", (0.32, 0.33, 0.37),
                           metallic=0.85, roughness=0.35)
    top_steel = solid_material("Anvil_TopSteel", (0.62, 0.64, 0.68),
                               metallic=0.9, roughness=0.18)
    iron = solid_material("Anvil_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    dark = solid_material("Anvil_Dark", (0.05, 0.05, 0.06),
                          metallic=0.3, roughness=0.8)

    parts = []
    # --- base: wide flat foot, z 0.00-0.18 ---
    parts.append(box("Base", (0, 0, 0.09), (1.50, 0.80, 0.18), iron))
    # --- pedestal step, z 0.18-0.32 ---
    parts.append(box("Pedestal", (0, 0, 0.25), (1.00, 0.55, 0.14), iron))
    # --- waist: tapered box, z 0.32-0.62, 0.60x0.42 -> 0.45x0.34 ---
    parts.append(tapered_box("Waist", (0, 0, 0.47),
                             (0.60, 0.42), (0.45, 0.34), 0.30, steel))
    # --- body: main block, z 0.62-0.98 ---
    parts.append(box("Body", (0, 0, 0.80), (1.05, 0.42, 0.36), steel))
    # --- top plate: polished face, z 0.98-1.06, overhangs body ---
    parts.append(box("TopPlate", (0, 0, 1.02), (1.30, 0.50, 0.08),
                     top_steel))
    # --- horn: 8-sided cone along +X, base r 0.21 at x=0.55,
    #     tip r 0.02 at x=1.15; built centered on the origin (so the
    #     +90 deg Y rotation spins it in place), then moved into place.
    #     NOTE: rotating an object spins it about the world origin, so
    #     building it at its final center first would bury it below
    #     the floor (z -> -x). ---
    horn = tapered_cylinder("Horn", (0, 0, 0),
                            0.21, 0.02, 0.60, 8, steel)
    horn.rotation_euler = (0.0, math.pi / 2.0, 0.0)
    horn.location = (0.85, 0, 0.86)
    parts.append(horn)
    # --- heel: square tail at -X, z 0.71-1.01 ---
    parts.append(box("Heel", (-0.62, 0, 0.86), (0.22, 0.46, 0.30), steel))
    # --- hardy hole: dark square inset on the top plate near the heel ---
    parts.append(box("HardyHole", (-0.45, 0, 1.065),
                     (0.09, 0.09, 0.02), dark))
    # --- pritchel hole: dark round inset on the top plate ---
    parts.append(tapered_cylinder("PritchelHole", (0.35, 0, 1.065),
                                  0.035, 0.035, 0.02, 8, dark))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    cam = make_camera("Camera", (3.4, -4.2, 2.2), (0, 0, 0.55), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "023-lowpoly-anvil.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "023-lowpoly-anvil.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "anvil_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("ANVIL_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("ANVIL_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "023-lowpoly-anvil.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 023 低模游戏道具：铁砧\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 底座：1.50×0.80×0.18 扁平铁足，z 0.00–0.18\n")
        f.write("- 底座台阶：1.00×0.55×0.14，z 0.18–0.32\n")
        f.write("- 腰身：渐细方台，底 0.60×0.42 → 顶 0.45×0.34，高 0.30，z 0.32–0.62\n")
        f.write("- 砧身：1.05×0.42×0.36 主块，z 0.62–0.98，钢色\n")
        f.write("- 砧面：1.30×0.50×0.08 抛光钢板，z 0.98–1.06，四边外伸于砧身\n")
        f.write("- 砧角：8 边锥体，底半径 0.21 → 尖 0.02，长 0.60，沿 +X，根部接砧身端面（x 0.55–1.15）\n")
        f.write("- 砧尾：0.22×0.46×0.30 方块，z 0.71–1.01，位于 -X 端\n")
        f.write("- 方孔（hardy hole）：0.09×0.09 深色方块，砧面近砧尾处\n")
        f.write("- 圆孔（pritchel hole）：半径 0.035 深色圆柱，砧面 x=0.35 处\n")
        f.write("- 全长约 2.30（砧角尖 x=1.15 至砧尾 x=-0.73），高 1.07\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Anvil_Steel：砧身/腰身/砧角/砧尾（metallic 0.85，roughness 0.35）\n")
        f.write("- Anvil_TopSteel：抛光砧面（metallic 0.9，roughness 0.18）\n")
        f.write("- Anvil_Iron：底座/台阶深铁色（metallic 0.7，roughness 0.5）\n")
        f.write("- Anvil_Dark：方孔/圆孔（近黑）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
