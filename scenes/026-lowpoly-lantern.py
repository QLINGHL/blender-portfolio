# -*- coding: utf-8 -*-
"""026 低模游戏道具：提灯（Lantern）
Low-poly game lantern: square iron frame, tapered glass shade, candle
with flame + warm point light inside, pyramid cap, finial and arched
carrying handle. Game-asset standard, flat shading, clean topology.
Height ~0.79 m (handle top), body ~0.63 m.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 026-lowpoly-lantern.py
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


def square_frustum(name, s_bottom, s_top, z0, z1, mat):
    """Open tapered square tube: 4 side quads, no caps.
    Corners CCW seen from +Z: (s,-s) -> (s,s) -> (-s,s) -> (-s,-s)."""
    corners = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
    verts = []
    for s, z in ((s_bottom, z0), (s_top, z1)):
        for sx, sy in corners:
            verts.append((sx * s, sy * s, z))
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((i, j, 4 + j, 4 + i))
    return mesh_from_data(name, verts, faces, mat)


def pyramid_cap(name, s_base, z_base, z_apex, mat):
    """Square pyramid: 4 side triangles + bottom fan (no N-gons)."""
    corners = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
    verts = [(sx * s_base, sy * s_base, z_base) for sx, sy in corners]
    verts.append((0, 0, z_apex))          # apex, index 4
    verts.append((0, 0, z_base))          # bottom center, index 5
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((i, j, 4))
        faces.append((5, j, i))
    return mesh_from_data(name, verts, faces, mat)


def half_torus(name, R, r, arc_segments, tube_segments, mat):
    """Half torus arch in the XZ plane: semicircle of radius R (angle
    0..pi, endpoints at (+/-R, 0, 0)), tube radius r. End caps are
    triangle fans from the end-circle centers (no N-gons)."""
    verts = []
    for i in range(arc_segments + 1):
        th = math.pi * i / arc_segments
        cx, cz = R * math.cos(th), R * math.sin(th)
        rx, rz = math.cos(th), math.sin(th)   # radial direction
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + r * math.cos(ph) * rx,
                          r * math.sin(ph),
                          cz + r * math.cos(ph) * rz))
    faces = []
    ring = tube_segments
    for i in range(arc_segments):
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            faces.append((i * ring + j, i * ring + k,
                          (i + 1) * ring + k, (i + 1) * ring + j))
    # end caps
    for end, base in ((0, 0), (arc_segments, arc_segments * ring)):
        c_idx = len(verts)
        th = 0.0 if end == 0 else math.pi
        verts.append((R * math.cos(th), 0, R * math.sin(th)))
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            if end == 0:
                faces.append((c_idx, base + k, base + j))
            else:
                faces.append((c_idx, base + j, base + k))
    return mesh_from_data(name, verts, faces, mat)


def cone(name, center, r_bottom, height, sides, mat):
    """Vertical (Z-axis) cone: apex on top, bottom cap as a triangle fan
    from a center vertex (no N-gons)."""
    cx, cy, cz = center
    z_bot = cz - height / 2.0
    z_apex = cz + height / 2.0
    verts = []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        verts.append((cx + r_bottom * math.cos(a),
                      cy + r_bottom * math.sin(a), z_bot))
    verts.append((cx, cy, z_apex))   # apex, index sides
    verts.append((cx, cy, z_bot))    # bottom center, index sides+1
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides))
        faces.append((sides + 1, j, i))
    return mesh_from_data(name, verts, faces, mat)


def check_torus_winding(obj, R, center_z):
    """Winding check for the half-torus handle: compare each face normal
    with the direction from the nearest point on the semicircle centerline
    (radius R in the XZ plane at height center_z) to the face center.
    (The centroid test does not apply to torus geometry.)"""
    import bmesh
    from mathutils import Vector
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = 0
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        # nearest point on the semicircle centerline (x^2 + (z-cz)^2 = R^2)
        dx, dz = c.x, c.z - center_z
        L = math.hypot(dx, dz)
        if L < 1e-9:
            continue
        nearest = Vector((R * dx / L, 0, center_z + R * dz / L))
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def glass_material(name, color, alpha=0.30):
    """Semi-transparent glass: Principled BSDF with alpha, blended render."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.08
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        mat.blend_method = 'BLEND'
    try:
        mat.shadow_method = 'NONE'
    except AttributeError:
        pass
    return mat


def emission_material(name, color, strength=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
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
    studio_lights(target=(0, 0, 0.35))

    iron = solid_material("Lantern_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    brass = solid_material("Lantern_Brass", (0.55, 0.42, 0.18),
                           metallic=0.85, roughness=0.35)
    wax = solid_material("Lantern_Wax", (0.92, 0.86, 0.70),
                         metallic=0.0, roughness=0.6)
    wick_mat = solid_material("Lantern_Wick", (0.10, 0.08, 0.06),
                              metallic=0.0, roughness=0.9)
    glass = glass_material("Lantern_Glass", (0.85, 0.75, 0.55), alpha=0.30)
    flame_mat = emission_material("Lantern_Flame", (1.0, 0.45, 0.08),
                                  strength=8.0)

    parts = []
    # --- base: iron foot, 0.34 x 0.34 x 0.07, z 0.00-0.07 ---
    parts.append(box("Base", (0, 0, 0.035), (0.34, 0.34, 0.07), iron))
    # --- bottom frame ring: brass, 0.30 x 0.30 x 0.05, z 0.07-0.12 ---
    parts.append(box("BottomFrame", (0, 0, 0.095),
                     (0.30, 0.30, 0.05), brass))
    # --- 4 corner posts: brass, 0.03 x 0.03 x 0.34, z 0.12-0.46 ---
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box("Post_%+d%+d" % (sx, sy),
                             (sx * 0.125, sy * 0.125, 0.29),
                             (0.03, 0.03, 0.34), brass))
    # --- glass shade: tapered square frustum, half 0.13 -> 0.10,
    #     z 0.12-0.46, open tube (no caps) ---
    parts.append(square_frustum("GlassShade", 0.13, 0.10, 0.12, 0.46, glass))
    # --- candle: wax cylinder r 0.035, z 0.12-0.24 ---
    parts.append(tapered_cylinder("Candle", (0, 0, 0.18),
                                  0.035, 0.035, 0.12, 8, wax))
    # --- wick: tiny dark cylinder, z 0.24-0.265 ---
    parts.append(tapered_cylinder("Wick", (0, 0, 0.2525),
                                  0.006, 0.006, 0.025, 6, wick_mat))
    # --- flame: 8-sided cone, r 0.028, z 0.255-0.345, emissive orange ---
    flame = cone("Flame", (0, 0, 0.30), 0.028, 0.09, 8, flame_mat)
    parts.append(flame)
    # --- top frame ring: brass, 0.26 x 0.26 x 0.05, z 0.46-0.51 ---
    parts.append(box("TopFrame", (0, 0, 0.485), (0.26, 0.26, 0.05), brass))
    # --- pyramid cap: iron, base half 0.13 at z 0.51, apex z 0.63 ---
    parts.append(pyramid_cap("Cap", 0.13, 0.51, 0.63, iron))
    # --- finial: small brass knob, cylinder r 0.02, z 0.63-0.68.
    #     Kept short on purpose: the handle arch passes just above it,
    #     so no tip cone (it would poke through the arch). ---
    parts.append(tapered_cylinder("Finial", (0, 0, 0.655),
                                  0.020, 0.016, 0.05, 8, brass))
    # --- handle posts: iron, r 0.015, z 0.51-0.56 at x = +/-0.14 ---
    for sx in (-1, 1):
        parts.append(tapered_cylinder("HandlePost_%+d" % sx,
                                      (sx * 0.14, 0, 0.535),
                                      0.015, 0.015, 0.05, 6, iron))
    # --- arched handle: half torus, major r 0.14, minor r 0.012,
    #     in the XZ plane, center z 0.56 ---
    handle = half_torus("Handle", 0.14, 0.012, 24, 6, iron)
    handle.location = (0, 0, 0.56)
    bpy.context.view_layer.update()
    parts.append(handle)

    # --- warm candle light inside the shade ---
    light_data = bpy.data.lights.new("CandleLight", 'POINT')
    light_data.energy = 10.0
    light_data.color = (1.0, 0.55, 0.2)
    light_data.use_shadow = False
    light_obj = bpy.data.objects.new("CandleLight", light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (0, 0, 0.30)

    for obj in parts:
        if obj.type == 'MESH' and obj.name != "GlassShade":
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    # centroid test is invalid for torus geometry: re-check the handle
    # against its semicircle centerline instead
    flipped["Handle"] = check_torus_winding(handle, 0.14, 0.56)
    print("LANTERN_WINDING:", flipped)
    print("HANDLE_BBOX_Z:", [round(v, 3) for v in
                             (handle.bound_box[0][2], handle.bound_box[6][2])])
    print("HANDLE_WORLD_Z:", round(handle.matrix_world.translation.z, 3),
          "dim:", [round(d, 3) for d in handle.dimensions])

    cam = make_camera("Camera", (1.35, -1.75, 0.9), (0, 0, 0.35), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "026-lowpoly-lantern.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "026-lowpoly-lantern.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "lantern_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("LANTERN_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("LANTERN_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "026-lowpoly-lantern.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 026 低模游戏道具：提灯\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 底座：铁质 0.34×0.34×0.07，z 0.00–0.07\n")
        f.write("- 下灯框：黄铜 0.30×0.30×0.05，z 0.07–0.12\n")
        f.write("- 四角立柱：黄铜 0.03×0.03×0.34，位于 (±0.125, ±0.125)，z 0.12–0.46\n")
        f.write("- 玻璃罩：方形渐缩空筒（半宽 0.13→0.10），z 0.12–0.46，4 个四边面，"
                "半透明暖色玻璃（alpha 0.30，roughness 0.08，不投阴影）\n")
        f.write("- 蜡烛：米白蜡柱 r 0.035，高 0.12，z 0.12–0.24；烛芯 r 0.006，z 0.24–0.265\n")
        f.write("- 火焰：8 边圆锥 r 0.028，高 0.09，z 0.255–0.345，自发光橙色（强度 8.0）\n")
        f.write("- 烛光：暖色点光源 (1.0, 0.55, 0.2)，能量 10.0，位于 (0, 0, 0.30)，不投阴影\n")
        f.write("- 上灯框：黄铜 0.26×0.26×0.05，z 0.46–0.51\n")
        f.write("- 顶盖：铁质四棱锥，底半宽 0.13（z 0.51），顶点 z 0.63，侧面三角 + 底面扇形剖分，无 N-gon\n")
        f.write("- 顶饰：黄铜小柱 r 0.02，z 0.63–0.68；特意不加锥尖——提环拱顶正好从其上方穿过，锥尖会穿出提环\n")
        f.write("- 提环：半圆环（major r 0.14，minor r 0.012），竖立于 XZ 平面，中心 z 0.56，"
                "两端由铁质小柱（r 0.015，z 0.51–0.56，x=±0.14）承接\n")
        f.write("- 全高约 0.71（提环顶），灯体约 0.68\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("提环为半圆环几何，绕向用环中心线检测（质心检测不适用于环形）；其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Lantern_Iron：底座/顶盖/提环（metallic 0.7，roughness 0.5）\n")
        f.write("- Lantern_Brass：上下灯框/立柱/顶饰（metallic 0.85，roughness 0.35）\n")
        f.write("- Lantern_Glass：玻璃罩（alpha 0.30，roughness 0.08，不投阴影）\n")
        f.write("- Lantern_Wax：蜡烛（roughness 0.6）\n")
        f.write("- Lantern_Flame：火焰自发光（橙色，强度 6.0）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
