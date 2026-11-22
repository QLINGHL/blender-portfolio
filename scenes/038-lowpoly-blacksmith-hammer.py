# -*- coding: utf-8 -*-
"""038 低模游戏道具：铁匠锤（Blacksmith Hammer）
Low-poly game blacksmith hammer: upright display, steel head with a
flat striking face and a cross-peen wedge, tapered wooden handle,
steel wedge in the eye, steel collar, leather grip wrap and two
leather binding straps. Game-asset standard, flat shading.
Overall ~0.43 m wide x 0.86 m tall (head along X, handle along Z).
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 038-lowpoly-blacksmith-hammer.py
"""
import os
import sys
import math
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    fit_camera_to_objects, export_wireframe_segments)


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


def rot_box_z(name, center, size, angle_z, mat):
    """Box rotated about the Z axis by angle_z (radians)."""
    obj = box(name, center, size, mat)
    obj.rotation_euler = (0, 0, angle_z)
    return obj


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points, open fan caps."""
    from mathutils import Vector
    a = Vector(p0)
    b = Vector(p1)
    axis = b - a
    length = axis.length
    axis.normalize()
    up = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(up).normalized()
    v = axis.cross(u).normalized()
    verts = []
    for p in (a, b):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append(tuple(p + radius * (math.cos(ang) * u
                                             + math.sin(ang) * v)))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append(tuple(a))
    c1 = len(verts)
    verts.append(tuple(b))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def tapered_cyl_between(name, p0, p1, r0, r1, sides, mat):
    """Tapered cylinder (with end caps) between two points:
    radius r0 at p0, r1 at p1."""
    from mathutils import Vector
    a = Vector(p0)
    b = Vector(p1)
    axis = b - a
    axis.normalize()
    up = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(up).normalized()
    v = axis.cross(u).normalized()
    verts = []
    for p, r in ((a, r0), (b, r1)):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append(tuple(p + r * (math.cos(ang) * u
                                        + math.sin(ang) * v)))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append(tuple(a))
    c1 = len(verts)
    verts.append(tuple(b))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def torus_xy(name, center, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying flat in the XY plane, centered at `center`.
    Closed tube, no caps needed."""
    cx, cy, cz = center
    verts = []
    for i in range(arc_segments):
        th = 2.0 * math.pi * i / arc_segments
        rx, ry = math.cos(th), math.sin(th)
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + (R + r * math.cos(ph)) * rx,
                          cy + (R + r * math.cos(ph)) * ry,
                          cz + r * math.sin(ph)))
    faces = []
    for i in range(arc_segments):
        ni = (i + 1) % arc_segments
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            faces.append((i * tube_segments + j, ni * tube_segments + j,
                          ni * tube_segments + k, i * tube_segments + k))
    return mesh_from_data(name, verts, faces, mat)


def peen_wedge(name, x0, x1, half_y0, half_y1, z0, z1, mat):
    """Cross-peen wedge: full-height block at x0 tapering to a thin
    vertical edge at x1 (half-thickness half_y0 -> half_y1)."""
    verts = [
        (x0, -half_y0, z0), (x0, half_y0, z0),
        (x0, half_y0, z1), (x0, -half_y0, z1),
        (x1, -half_y1, z0), (x1, half_y1, z0),
        (x1, half_y1, z1), (x1, -half_y1, z1),
    ]
    faces = [
        (0, 4, 5, 1),   # bottom, -Z
        (3, 2, 6, 7),   # top, +Z
        (0, 3, 7, 4),   # side, -Y
        (1, 5, 6, 2),   # side, +Y
        (4, 7, 6, 5),   # tip, -X
        (0, 1, 2, 3),   # back, +X (hidden inside the head body)
    ]
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


def check_torus_winding_xy(obj, R, center):
    """Winding check for a flat ring: compare each face normal with the
    direction from the nearest point on the ring centerline to the face
    center."""
    import bmesh
    from mathutils import Vector
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = 0
    cx, cy, cz = center
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        dx, dy = c.x - cx, c.y - cy
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nearest = Vector((cx + R * dx / L, cy + R * dy / L, cz))
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def handle_radius(z):
    """Handle taper: r 0.026 at z=0.02 -> r 0.020 at z=0.845."""
    return 0.026 - (z - 0.02) / (0.845 - 0.02) * 0.006


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.45))

    head_steel = solid_material("Hammer_HeadSteel", (0.28, 0.29, 0.31),
                                metallic=0.85, roughness=0.45)
    face_steel = solid_material("Hammer_FaceSteel", (0.52, 0.54, 0.56),
                                metallic=0.9, roughness=0.28)
    wedge_steel = solid_material("Hammer_WedgeSteel", (0.38, 0.38, 0.40),
                                 metallic=0.8, roughness=0.4)
    wood = solid_material("Hammer_Wood", (0.42, 0.28, 0.14),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Hammer_WoodDark", (0.28, 0.17, 0.08),
                               metallic=0.0, roughness=0.85)
    leather = solid_material("Hammer_Leather", (0.16, 0.09, 0.04),
                             metallic=0.0, roughness=0.9)

    parts = []
    # --- head body: steel block 0.24 x 0.10 x 0.10, z 0.73-0.83 ---
    parts.append(box("HeadBody", (0, 0, 0.78), (0.24, 0.10, 0.10),
                     head_steel))
    # --- striking face: light-steel cylinder along X, x 0.12-0.16 ---
    parts.append(cyl_between("Face", (0.12, 0, 0.78), (0.16, 0, 0.78),
                             0.055, 16, face_steel))
    # --- face rim: thin forged lip, x 0.155-0.167, r 0.057 ---
    parts.append(cyl_between("FaceRim", (0.155, 0, 0.78),
                             (0.167, 0, 0.78), 0.057, 16, head_steel))
    # --- cross-peen: wedge from the head body to a thin edge at x=-0.26 ---
    parts.append(peen_wedge("Peen", -0.12, -0.26, 0.05, 0.0075,
                            0.73, 0.83, head_steel))
    # --- handle: tapered wood cylinder, z 0.02-0.845, r 0.026 -> 0.020 ---
    parts.append(tapered_cyl_between("Handle", (0, 0, 0.02),
                                     (0, 0, 0.845), 0.026, 0.020, 12,
                                     wood))
    # --- pommel cap: darker wood, z 0.02-0.08, r 0.030 -> 0.033 ---
    parts.append(tapered_cyl_between("Pommel", (0, 0, 0.02),
                                     (0, 0, 0.08), 0.030, 0.033, 12,
                                     wood_dark))
    # --- grip wrap: leather over the lower handle, z 0.14-0.38 ---
    parts.append(tapered_cyl_between("GripWrap", (0, 0, 0.14),
                                     (0, 0, 0.38), 0.027, 0.0255, 12,
                                     leather))
    # --- collar: steel ring where the handle enters the head, z 0.70-0.73 ---
    parts.append(cyl_between("Collar", (0, 0, 0.70), (0, 0, 0.73),
                             0.030, 16, head_steel))
    # --- eye wedge: steel wedge on top of the handle, half sunk ---
    parts.append(rot_box_z("EyeWedge", (0, 0, 0.848),
                           (0.036, 0.028, 0.018), 0.25, wedge_steel))
    # --- binding straps: two leather rings around the handle below head ---
    straps = []
    for i, z in enumerate((0.64, 0.685)):
        ring = torus_xy("Strap_%d" % (i + 1), (0, 0, z),
                        handle_radius(z) + 0.001, 0.0055, 24, 6, leather)
        straps.append((ring, z))
        parts.append(ring)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    # NB: torus meshes bake absolute coords (object location is 0,0,0),
    # so the ring centerline must use the build-time z, not location.z.
    for ring, z in straps:
        flipped[ring.name] = check_torus_winding_xy(
            ring, handle_radius(z) + 0.001, (0, 0, z))
    print("HAMMER_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "038-lowpoly-blacksmith-hammer.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "038-lowpoly-blacksmith-hammer.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "hammer_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("HAMMER_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("HAMMER_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "038-lowpoly-blacksmith-hammer.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 038 低模游戏道具：铁匠锤\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "铁匠锤直立展示，3/4 俯视角度。\n\n")
        f.write("## 结构\n\n")
        f.write("- 锤头（HeadBody）：钢块 0.24×0.10×0.10，z 0.73–0.83\n")
        f.write("- 击面（Face）：浅色钢圆柱沿 X 轴，x 0.12–0.16，r 0.055，"
                "16 段\n")
        f.write("- 击面唇缘（FaceRim）：锻造唇，x 0.155–0.167，r 0.057\n")
        f.write("- 锤砧/横楔（Peen）：楔形，从锤头 x=-0.12 处半厚 0.05 "
                "收至 x=-0.26 处半厚 0.0075，z 0.73–0.83\n")
        f.write("- 锤柄（Handle）：木质锥形圆柱，z 0.02–0.845，"
                "r 0.026→0.020，12 段\n")
        f.write("- 柄尾帽（Pommel）：深色木，z 0.02–0.08，r 0.030→0.033\n")
        f.write("- 握把缠皮（GripWrap）：皮革，z 0.14–0.38，"
                "r 0.027→0.0255\n")
        f.write("- 套箍（Collar）：钢环，锤柄入头处，z 0.70–0.73，r 0.030\n")
        f.write("- 眼楔（EyeWedge）：钢楔 0.036×0.028×0.018，位于柄顶 "
                "z 0.848，绕 Z 轴转 0.25 弧度，半沉入柄顶\n")
        f.write("- 绑带（Strap_1/2）：皮革圆环，z 0.64 / 0.685，"
                "环 R 为当地柄半径 +0.001，管 r 0.0055\n")
        f.write("- 整体约 0.43 m 宽（x -0.26–0.167）× 0.86 m 高\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("绑带为闭合圆环几何，绕向用环中心线检测；其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Hammer_HeadSteel：锤头/唇缘/套箍深钢"
                "（metallic 0.85，roughness 0.45）\n")
        f.write("- Hammer_FaceSteel：击面浅钢"
                "（metallic 0.9，roughness 0.28）\n")
        f.write("- Hammer_WedgeSteel：眼楔钢"
                "（metallic 0.8，roughness 0.4）\n")
        f.write("- Hammer_Wood：锤柄木色（roughness 0.8）\n")
        f.write("- Hammer_WoodDark：柄尾帽深木色（roughness 0.85）\n")
        f.write("- Hammer_Leather：握把缠皮/绑带皮革（roughness 0.9）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
