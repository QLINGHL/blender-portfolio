# -*- coding: utf-8 -*-
"""025 低模游戏道具：战斧（Battle Axe）
Low-poly game battle axe: tapered wooden haft, leather grip, iron
pommel, steel socket block, fan-shaped extruded blade (hexagon profile,
front/back faces triangulated from centroid - no N-gons), bright
sharpened edge strip, wooden wedge cap on top of the haft.
Height ~1.62 m, blade reach x 0.00-0.56.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 025-lowpoly-battleaxe.py
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


def extruded_profile(name, profile, thickness, mat):
    """Extrude a 2D (x, z) profile along Y by `thickness`, centered on y=0.
    Profile must be CCW in the (x, z) plane (x right, z up).
    Front (+Y) and back (-Y) faces are triangulated from the profile
    centroid, so the result has no N-gons. Winding verified by the
    right-hand rule: back face in profile order, front face reversed,
    side quads (A_i, B_i, B_j, A_j)."""
    t = thickness / 2.0
    n = len(profile)
    cx = sum(p[0] for p in profile) / n
    cz = sum(p[1] for p in profile) / n
    verts = []
    for (x, z) in profile:
        verts.append((x, -t, z))          # A_i: back ring
    for (x, z) in profile:
        verts.append((x, t, z))           # B_i: front ring
    c_back = 2 * n
    c_front = 2 * n + 1
    verts.append((cx, -t, cz))
    verts.append((cx, t, cz))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((c_back, i, j))          # back face fan, normal -Y
        faces.append((c_front, n + j, n + i))  # front face fan, normal +Y
        faces.append((i, n + i, n + j, j))     # side quad, outward
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


def check_winding(obj):
    """Count faces whose normal points inward (dot with the vector from
    the mesh centroid to the face center is negative)."""
    import bmesh
    from mathutils import Vector
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    center = Vector((0, 0, 0))
    for v in bm.verts:
        center += mw @ v.co
    center /= len(bm.verts)
    flipped = 0
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        if n.dot((c - center).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0.1, 0, 0.85))

    steel = solid_material("Axe_Steel", (0.30, 0.31, 0.34),
                           metallic=0.85, roughness=0.35)
    edge_steel = solid_material("Axe_EdgeSteel", (0.62, 0.64, 0.68),
                                metallic=0.9, roughness=0.15)
    wood = solid_material("Axe_Wood", (0.45, 0.28, 0.14),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Axe_WoodDark", (0.30, 0.18, 0.09),
                               metallic=0.0, roughness=0.85)
    leather = solid_material("Axe_Leather", (0.20, 0.12, 0.08),
                             metallic=0.0, roughness=0.9)
    iron = solid_material("Axe_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)

    parts = []
    # --- haft: tapered 8-sided wooden shaft, z 0.00-1.55 ---
    parts.append(tapered_cylinder("Haft", (0, 0, 0.775),
                                  0.045, 0.035, 1.55, 8, wood))
    # --- grip: darker leather wrap near the bottom, z 0.02-0.30 ---
    parts.append(tapered_cylinder("Grip", (0, 0, 0.16),
                                  0.052, 0.050, 0.28, 8, leather))
    # --- pommel: iron cap at the very bottom, z 0.00-0.06 ---
    parts.append(tapered_cylinder("Pommel", (0, 0, 0.03),
                                  0.050, 0.045, 0.06, 8, iron))
    # --- socket: steel block where the blade meets the haft,
    #     x -0.09..0.13, z 1.09-1.39 ---
    parts.append(box("Socket", (0.02, 0, 1.24), (0.22, 0.13, 0.30), steel))
    # --- blade: fan-shaped extruded hexagon profile, thickness 0.08,
    #     x 0.00-0.52, z 0.88-1.56 (CCW in XZ) ---
    blade_profile = [
        (0.00, 1.02), (0.40, 0.88), (0.52, 1.02),
        (0.52, 1.42), (0.40, 1.56), (0.00, 1.44),
    ]
    parts.append(extruded_profile("Blade", blade_profile, 0.08, steel))
    # --- cutting edge: bright sharpened strip at the blade edge,
    #     x 0.50-0.56, z 1.01-1.43, slightly thicker than the blade ---
    parts.append(box("CuttingEdge", (0.53, 0, 1.22),
                     (0.06, 0.10, 0.42), edge_steel))
    # --- wedge cap: wooden wedge on top of the haft, z 1.55-1.62 ---
    parts.append(box("TopWedge", (0, 0, 1.585), (0.09, 0.09, 0.07),
                     wood_dark))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    print("AXE_WINDING:", flipped)

    cam = make_camera("Camera", (2.2, -2.8, 1.4), (0.15, 0, 0.85), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "025-lowpoly-battleaxe.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "025-lowpoly-battleaxe.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "battleaxe_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("AXE_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("AXE_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "025-lowpoly-battleaxe.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 025 低模游戏道具：战斧\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 斧柄：8 边渐细木杆，底半径 0.045 → 顶 0.035，高 1.55，z 0.00–1.55\n")
        f.write("- 握把：深色皮革缠绕，半径约 0.05，高 0.28，z 0.02–0.30\n")
        f.write("- 斧底帽：铁质圆盖，半径约 0.05，高 0.06，z 0.00–0.06\n")
        f.write("- 斧头座：钢块 0.22×0.13×0.30，x -0.09–0.13，z 1.09–1.39，连接斧刃与斧柄\n")
        f.write("- 斧刃：六边形轮廓沿 Y 挤出（厚 0.08），x 0.00–0.52，z 0.88–1.56；"
                "刃口外张、近柄收窄的扇形；正反面用形心三角扇剖分，无 N-gon\n")
        f.write("- 刃口：亮钢薄条 0.06×0.10×0.42，x 0.50–0.56，z 1.01–1.43，"
                "比斧刃略厚一圈，读作开刃\n")
        f.write("- 顶楔：深色木楔 0.09×0.09×0.07，z 1.55–1.62，斧柄顶端外露\n")
        f.write("- 全高约 1.62，斧刃最远 x=0.56\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Axe_Steel：斧头座/斧刃（metallic 0.85，roughness 0.35）\n")
        f.write("- Axe_EdgeSteel：刃口亮钢（metallic 0.9，roughness 0.15）\n")
        f.write("- Axe_Wood：斧柄（roughness 0.8）\n")
        f.write("- Axe_WoodDark：顶楔（roughness 0.85）\n")
        f.write("- Axe_Leather：握把皮革（roughness 0.9）\n")
        f.write("- Axe_Iron：斧底帽（metallic 0.7，roughness 0.5）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
