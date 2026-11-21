# -*- coding: utf-8 -*-
"""030 低模游戏道具：弩（Crossbow）
Low-poly game crossbow: wooden stock laid flat, steel prod swept
slightly forward, V-shaped bowstring, loaded bolt in the groove,
trigger, foot stirrup and a side-mounted bolt quiver with 3 spare
bolts. Game-asset standard, flat shading, clean topology.
Overall ~1.10 m wide (prod tip to tip) x ~1.05 m long.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 030-lowpoly-crossbow.py
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


def rot_box(name, center, size, angle_z, mat):
    """Box rotated about the Z axis by angle_z (radians)."""
    obj = box(name, center, size, mat)
    obj.rotation_euler = (0, 0, angle_z)
    return obj


def tapered_cylinder_z(name, center, r_bottom, r_top, height, sides, mat):
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


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points, open fan caps."""
    from mathutils import Vector
    a = Vector(p0)
    b = Vector(p1)
    axis = b - a
    length = axis.length
    axis.normalize()
    # build an orthonormal basis around the axis
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


def cone_y(name, center, r_base, length, sides, mat, tip_forward=True):
    """Cone along the Y axis: base at rear, apex toward -Y (front)
    when tip_forward is True. Base cap is a triangle fan."""
    cx, cy, cz = center
    y_base = cy + length / 2.0 if tip_forward else cy - length / 2.0
    y_apex = cy - length / 2.0 if tip_forward else cy + length / 2.0
    verts = []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        verts.append((cx + r_base * math.cos(a), y_base,
                      cz + r_base * math.sin(a)))
    verts.append((cx, y_apex, cz))   # apex, index sides
    verts.append((cx, y_base, cz))   # base center, index sides+1
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        if tip_forward:
            faces.append((i, j, sides))
            faces.append((sides + 1, j, i))
        else:
            faces.append((j, i, sides))
            faces.append((sides + 1, i, j))
    return mesh_from_data(name, verts, faces, mat)


def half_torus_flat(name, R, r, arc_segments, tube_segments, mat):
    """Half torus arch lying flat in the XY plane: semicircle of radius R
    (angle 0..pi, endpoints at (+/-R, 0, 0)), tube radius r. End caps are
    triangle fans from the end-circle centers (no N-gons)."""
    verts = []
    for i in range(arc_segments + 1):
        th = math.pi * i / arc_segments
        cx, cy = R * math.cos(th), R * math.sin(th)
        rx, ry = math.cos(th), math.sin(th)   # radial direction
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + r * math.cos(ph) * rx,
                          cy + r * math.cos(ph) * ry,
                          r * math.sin(ph)))
    faces = []
    ring = tube_segments
    for i in range(arc_segments):
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            faces.append((i * ring + j, (i + 1) * ring + j,
                          (i + 1) * ring + k, i * ring + k))
    # End caps: both face -Y (start cap faces -T(0), end cap faces +T(pi)).
    for end, base in ((0, 0), (arc_segments, arc_segments * ring)):
        c_idx = len(verts)
        th = 0.0 if end == 0 else math.pi
        verts.append((R * math.cos(th), R * math.sin(th), 0))
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            if end == 0:
                faces.append((c_idx, base + j, base + k))
            else:
                faces.append((c_idx, base + k, base + j))
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


def check_torus_winding_flat(obj, R, center):
    """Winding check for the flat half-torus stirrup: compare each face
    normal with the direction from the nearest point on the semicircle
    centerline (radius R in the XY plane at center) to the face center."""
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


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.1))

    wood = solid_material("Crossbow_Wood", (0.38, 0.24, 0.12),
                          metallic=0.0, roughness=0.7)
    wood_dark = solid_material("Crossbow_WoodDark", (0.22, 0.13, 0.06),
                               metallic=0.0, roughness=0.75)
    steel = solid_material("Crossbow_Steel", (0.45, 0.47, 0.50),
                           metallic=0.85, roughness=0.35)
    iron = solid_material("Crossbow_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    string_mat = solid_material("Crossbow_String", (0.85, 0.82, 0.72),
                                metallic=0.0, roughness=0.9)
    leather = solid_material("Crossbow_Leather", (0.35, 0.20, 0.10),
                             metallic=0.0, roughness=0.85)
    feather = solid_material("Crossbow_Fletching", (0.75, 0.72, 0.60),
                             metallic=0.0, roughness=0.8)

    parts = []
    # --- stock: main tiller, wood, 0.10 x 0.95 x 0.07, z 0.00-0.07 ---
    parts.append(box("Stock", (0, 0, 0.035), (0.10, 0.95, 0.07), wood))
    # --- butt: wider rear stock, wood, 0.13 x 0.18 x 0.08, y 0.40-0.58 ---
    parts.append(box("Butt", (0, 0.47, 0.04), (0.13, 0.18, 0.08), wood))
    # --- cheek rest: small raised pad on the butt, leather ---
    parts.append(box("CheekRest", (0, 0.47, 0.085), (0.09, 0.12, 0.02),
                     leather))
    # --- bolt groove: dark channel on top of the stock, y -0.36..0.34 ---
    parts.append(box("BoltGroove", (0, -0.01, 0.072), (0.03, 0.70, 0.012),
                     wood_dark))
    # --- rear sight: small iron notch block at the back of the groove ---
    parts.append(box("RearSight", (0, 0.36, 0.082), (0.05, 0.03, 0.02),
                     iron))
    # --- prod (limbs): steel arms swept slightly forward.
    #     Each arm runs from x=+-0.05 to x=+-0.55, y -0.38 -> -0.47.
    #     Arm length 0.52, tilt atan2(0.09, 0.50) ~ 10.2 deg. ---
    arm_len = math.hypot(0.50, 0.09)
    arm_ang = math.atan2(0.09, 0.50)
    for s in (-1, 1):
        cx = s * (0.05 + 0.25)
        cy = -0.38 - 0.045
        parts.append(rot_box("Limb_%+d" % s, (cx, cy, 0.045),
                             (arm_len, 0.045, 0.028),
                             -s * arm_ang, steel))
        # limb tip caps: small iron blocks at the outer ends
        tip_x = s * 0.55
        tip_y = -0.47
        parts.append(rot_box("LimbTip_%+d" % s, (tip_x, tip_y, 0.045),
                             (0.05, 0.06, 0.034), -s * arm_ang, iron))
    # --- prod binding: iron block clamping the limbs to the stock front ---
    parts.append(box("ProdBinding", (0, -0.38, 0.05), (0.14, 0.08, 0.05),
                     iron))
    # --- bowstring: two thin cylinders, tips -> nock point (0, -0.02) ---
    nock = (0, -0.02, 0.055)
    for s in (-1, 1):
        parts.append(cyl_between("String_%+d" % s,
                                 (s * 0.55, -0.47, 0.045), nock,
                                 0.004, 6, string_mat))
    # --- loaded bolt: shaft in the groove, y -0.34..0.30, r 0.008 ---
    parts.append(cyl_between("BoltShaft", (0, 0.30, 0.085),
                             (0, -0.34, 0.085), 0.008, 8, wood))
    # --- bolt tip: steel cone, apex toward -Y (front) ---
    parts.append(cone_y("BoltTip", (0, -0.365, 0.085), 0.011, 0.05, 8,
                        steel, tip_forward=True))
    # --- fletching: two thin vertical vanes at the rear of the bolt ---
    for s in (-1, 1):
        vane = box("Fletch_%+d" % s, (s * 0.012, 0.27, 0.095),
                   (0.004, 0.10, 0.02), feather)
        vane.rotation_euler = (0, s * 0.35, 0)
        parts.append(vane)
    # --- trigger: iron lever below the stock, tilted in the YZ plane ---
    trigger = box("Trigger", (0, 0.06, 0.005), (0.02, 0.07, 0.05), iron)
    trigger.rotation_euler = (0.5, 0, 0)
    parts.append(trigger)
    # --- trigger guard: thin iron bar under the stock ---
    parts.append(box("TriggerGuard", (0, 0.06, -0.005), (0.09, 0.02, 0.01),
                     iron))
    # --- stirrup: flat half-torus loop at the front, center (0, -0.55) ---
    stirrup = half_torus_flat("Stirrup", 0.07, 0.008, 24, 6, iron)
    stirrup.location = (0, -0.55, 0.035)
    bpy.context.view_layer.update()
    parts.append(stirrup)
    # --- quiver (side-mounted bolt case): wood box on the right side ---
    parts.append(box("Quiver", (0.11, 0.15, 0.05), (0.06, 0.30, 0.10),
                     wood_dark))
    parts.append(box("QuiverLid", (0.11, 0.15, 0.105), (0.07, 0.31, 0.015),
                     leather))
    # --- 3 spare bolts standing in the quiver, vertical, tips up ---
    for i, dy in enumerate((-0.09, 0.0, 0.09)):
        parts.append(tapered_cylinder_z("SpareBolt_%d" % (i + 1),
                                        (0.11, 0.15 + dy, 0.21),
                                        0.008, 0.008, 0.22, 8, wood))
        parts.append(tapered_cylinder_z("SpareTip_%d" % (i + 1),
                                        (0.11, 0.15 + dy, 0.335),
                                        0.011, 0.004, 0.03, 8, steel))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    flipped["Stirrup"] = check_torus_winding_flat(stirrup, 0.07,
                                                  (0, -0.55, 0.035))
    print("CROSSBOW_WINDING:", flipped)

    cam = make_camera("Camera", (1.15, -1.45, 0.95), (0, 0, 0.05), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "030-lowpoly-crossbow.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "030-lowpoly-crossbow.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "crossbow_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("CROSSBOW_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CROSSBOW_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "030-lowpoly-crossbow.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 030 低模游戏道具：弩\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "弩身平放于地面，3/4 俯视角度展示。\n\n")
        f.write("## 结构\n\n")
        f.write("- 弩身（Stock）：木质 0.10×0.95×0.07，z 0.00–0.07\n")
        f.write("- 枪托（Butt）：木质 0.13×0.18×0.08，y 0.38–0.56；"
                "贴腮垫皮革 0.09×0.12×0.02\n")
        f.write("- 箭槽（BoltGroove）：深色木质 0.03×0.70×0.012，弩身顶部\n")
        f.write("- 照门（RearSight）：铁质小块 0.05×0.03×0.02，箭槽后端\n")
        f.write("- 弩臂（Limb）：钢质，每侧长 0.52、截面 0.045×0.028，"
                "从 x=±0.05 伸至 x=±0.55，前倾约 10.2°（y -0.38→-0.47）\n")
        f.write("- 弩臂尖（LimbTip）：铁质小块，位于两端 x=±0.55\n")
        f.write("- 弩臂座（ProdBinding）：铁质 0.14×0.08×0.05，"
                "将弩臂固定于弩身前端\n")
        f.write("- 弓弦（String）：两段 r 0.004 细圆柱，从弩臂尖"
                " (±0.55, -0.47) 收至待发点 (0, -0.02, 0.055)，呈 V 形\n")
        f.write("- 待发弩箭：木质箭杆 r 0.008，y -0.34–0.30；钢质箭头圆锥"
                " r 0.011、长 0.05，箭尾两片羽片（薄板，倾斜 20°）\n")
        f.write("- 扳机（Trigger）：铁质，弩身下方倾斜；扳机护圈铁条\n")
        f.write("- 蹬环（Stirrup）：扁平半圆环（major r 0.07，minor r 0.008），"
                "平放于前端 (0, -0.55)，供脚蹬上弦\n")
        f.write("- 箭匣（Quiver）：右侧挂深色木盒 0.06×0.30×0.10，皮革盖；"
                "内插 3 支备用弩箭（竖立，箭杆高 0.22，钢质箭头朝上）\n")
        f.write("- 整体约 1.10 m 宽（弩臂尖到尖）× 1.13 m 长（含蹬环）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("蹬环为半圆环几何，绕向用环中心线检测（质心检测不适用于环形）；"
                "其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Crossbow_Wood：弩身/枪托（roughness 0.7）\n")
        f.write("- Crossbow_WoodDark：箭槽/箭匣（roughness 0.75）\n")
        f.write("- Crossbow_Steel：弩臂/箭头（metallic 0.85，roughness 0.35）\n")
        f.write("- Crossbow_Iron：弩臂尖/弩臂座/扳机/蹬环（metallic 0.7，"
                "roughness 0.5）\n")
        f.write("- Crossbow_String：弓弦（浅色，roughness 0.9）\n")
        f.write("- Crossbow_Leather：贴腮垫/箭匣盖（roughness 0.85）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
