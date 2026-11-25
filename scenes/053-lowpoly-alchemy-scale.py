# -*- coding: utf-8 -*-
"""053 低模游戏道具：炼金天平（Alchemy Balance Scale）
Low-poly game alchemy balance scale: stepped round wooden plinth with
brass trim, a brass pillar with collar rings and a finial, a horizontal
beam on a center pivot, a pointer needle hanging in front of a dial
plate on the pillar, two shallow brass pans hung by three chains each,
a stacked weight set on the right pan and one spare weight on the
ground beside the plinth. Game-asset standard, flat shading.
Overall ~0.62 m wide x ~0.46 m tall (beam 0.52 + end finials, finial
top z 0.465).
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 053-lowpoly-alchemy-scale.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector, Matrix

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


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points."""
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


def tapered_cyl_z(name, z0, z1, r0, r1, sides, mat):
    """Vertical tapered cylinder (with end caps) along Z."""
    verts = []
    for z, r in ((z0, r0), (z1, r1)):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(ang), r * math.sin(ang), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append((0, 0, z0))
    c1 = len(verts)
    verts.append((0, 0, z1))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def torus_xy(name, center, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying flat in the XY plane, centered at `center`."""
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
    center. Must run while the torus is still unrotated in the XY plane."""
    import bmesh
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


BEAM_Z = 0.42
BEAM_HALF = 0.26
PAN_R = 0.09
PAN_Z_TOP = 0.30


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.25))

    wood = solid_material("Scale_Wood", (0.34, 0.21, 0.11),
                          metallic=0.0, roughness=0.75)
    wood_dark = solid_material("Scale_WoodDark", (0.22, 0.13, 0.07),
                               metallic=0.0, roughness=0.8)
    brass = solid_material("Scale_Brass", (0.68, 0.50, 0.18),
                           metallic=0.9, roughness=0.35)
    brass_dark = solid_material("Scale_BrassDark", (0.50, 0.36, 0.13),
                                metallic=0.85, roughness=0.45)
    iron = solid_material("Scale_Iron", (0.28, 0.28, 0.30),
                          metallic=0.85, roughness=0.5)

    parts = []
    flipped = {}

    # --- plinth: stepped round base, z 0-0.03, r 0.20 -> 0.18 ---
    parts.append(tapered_cyl_z("Plinth", 0.0, 0.03, 0.20, 0.18, 24,
                               wood_dark))
    # --- plinth trim ring, z 0.03 ---
    trim = torus_xy("PlinthTrim", (0, 0, 0.03), 0.185, 0.007, 24, 6, brass)
    flipped[trim.name] = check_torus_winding_xy(trim, 0.185, (0, 0, 0.03))
    parts.append(trim)
    # --- base body: tapered, z 0.03-0.06, r 0.16 -> 0.13 ---
    parts.append(tapered_cyl_z("BaseBody", 0.03, 0.06, 0.16, 0.13, 24,
                               wood))
    # --- base band, z 0.06 ---
    band = torus_xy("BaseBand", (0, 0, 0.06), 0.135, 0.006, 24, 6, brass)
    flipped[band.name] = check_torus_winding_xy(band, 0.135, (0, 0, 0.06))
    parts.append(band)

    # --- pillar: tapered brass column, z 0.06-0.40, r 0.028 -> 0.022 ---
    parts.append(tapered_cyl_z("Pillar", 0.06, 0.40, 0.028, 0.022, 12,
                               brass))
    # --- pillar collar rings at z 0.14 and z 0.32 ---
    for i, z in enumerate((0.14, 0.32)):
        r = 0.028 - (z - 0.06) / 0.34 * 0.006
        collar = torus_xy("Collar_%d" % (i + 1), (0, 0, z), r, 0.006,
                          16, 6, brass_dark)
        flipped[collar.name] = check_torus_winding_xy(collar, r, (0, 0, z))
        parts.append(collar)

    # --- dial plate on the pillar front, z 0.315-0.345 ---
    parts.append(box("DialPlate", (0, -0.027, 0.33),
                     (0.06, 0.008, 0.03), brass_dark))
    # --- pointer arm: from beam center forward, at beam height ---
    parts.append(cyl_between("PointerArm", (0, 0, BEAM_Z),
                             (0, -0.04, BEAM_Z), 0.006, 6, brass_dark))
    # --- pointer needle: hangs from the arm tip down to the dial top ---
    parts.append(tapered_cyl_z("Pointer", 0.345, BEAM_Z, 0.001, 0.005, 6,
                               brass_dark))
    # NB: tapered_cyl_z is centered on the Z axis; move the needle to
    # the arm tip (0, -0.04).
    parts[-1].location = (0, -0.04, 0)

    # --- center pivot: small sphere at the beam center ---
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6,
                                         radius=0.02,
                                         location=(0, 0, BEAM_Z))
    pivot = bpy.context.active_object
    pivot.name = "Pivot"
    pivot.data.materials.append(brass_dark)
    flat_shade(pivot)
    parts.append(pivot)

    # --- beam: horizontal brass rod along X at z 0.42 ---
    parts.append(cyl_between("Beam", (-BEAM_HALF, 0, BEAM_Z),
                             (BEAM_HALF, 0, BEAM_Z), 0.012, 8, brass))
    # --- beam end finials ---
    for i, sx in enumerate((-1, 1)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=12, ring_count=6, radius=0.016,
            location=(sx * BEAM_HALF, 0, BEAM_Z))
        fin = bpy.context.active_object
        fin.name = "BeamFinial_%d" % (i + 1)
        fin.data.materials.append(brass_dark)
        flat_shade(fin)
        parts.append(fin)

    # --- finial on top of the pillar, above the beam ---
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6,
                                         radius=0.02,
                                         location=(0, 0, 0.445))
    finial = bpy.context.active_object
    finial.name = "TopFinial"
    finial.data.materials.append(brass)
    flat_shade(finial)
    parts.append(finial)

    # --- pans + chains: one set per beam end ---
    for side, sx in enumerate((-1, 1)):
        cx = sx * BEAM_HALF
        # shallow dish: cone frustum, bottom r 0.03 at z 0.285,
        # top r 0.09 at z 0.30 (top cap is the pan surface)
        pan = tapered_cyl_z("Pan_%d" % (side + 1), 0.285, PAN_Z_TOP,
                            0.03, PAN_R, 24, brass)
        pan.location = (cx, 0, 0)
        parts.append(pan)
        # pan rim torus
        rim = torus_xy("PanRim_%d" % (side + 1), (cx, 0, PAN_Z_TOP),
                       PAN_R, 0.005, 24, 6, brass_dark)
        flipped[rim.name] = check_torus_winding_xy(
            rim, PAN_R, (cx, 0, PAN_Z_TOP))
        parts.append(rim)
        # three chains from the beam end down to the pan rim
        for k in range(3):
            a = 2.0 * math.pi * k / 3.0
            rx = cx + PAN_R * math.cos(a)
            ry = PAN_R * math.sin(a)
            chain = cyl_between("Chain_%d_%d" % (side + 1, k + 1),
                                (cx, 0, BEAM_Z),
                                (rx, ry, PAN_Z_TOP), 0.0025, 4, iron)
            parts.append(chain)

    # --- weight set: three stacked cylinders on the right pan ---
    # pan top surface is z 0.30; weights sit on it, centered at x +0.26
    wx = BEAM_HALF
    parts.append(tapered_cyl_z("Weight_Large", 0.30, 0.32, 0.030, 0.030,
                               16, brass_dark))
    parts[-1].location = (wx, 0, 0)
    parts.append(tapered_cyl_z("Weight_Mid", 0.32, 0.338, 0.022, 0.022,
                               16, brass_dark))
    parts[-1].location = (wx, 0, 0)
    parts.append(tapered_cyl_z("Weight_Small", 0.338, 0.353, 0.015, 0.015,
                               12, brass_dark))
    parts[-1].location = (wx, 0, 0)
    # knob on the large weight
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=5,
                                         radius=0.008,
                                         location=(wx, 0, 0.324))
    knob = bpy.context.active_object
    knob.name = "WeightKnob"
    knob.data.materials.append(brass)
    flat_shade(knob)
    parts.append(knob)

    # --- spare weight on the ground beside the plinth ---
    parts.append(tapered_cyl_z("SpareWeight", 0.0, 0.025, 0.028, 0.028,
                               16, brass_dark))
    parts[-1].location = (0.32, 0.14, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=5,
                                         radius=0.009,
                                         location=(0.32, 0.14, 0.029))
    sknob = bpy.context.active_object
    sknob.name = "SpareWeightKnob"
    sknob.data.materials.append(brass)
    flat_shade(sknob)
    parts.append(sknob)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    for o in parts:
        if o.type == 'MESH' and o.name not in flipped:
            flipped[o.name] = check_winding(o)
    print("SCALE_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.30),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "053-lowpoly-alchemy-scale.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "053-lowpoly-alchemy-scale.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "scale_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("SCALE_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("SCALE_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "053-lowpoly-alchemy-scale.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 053 低模游戏道具：炼金天平\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "圆台木底座 + 黄铜立柱，横梁两端各挂一只浅托盘，右盘叠放"
                "三枚砝码，底座旁另有一枚备用砝码；指针自横梁垂至立柱前"
                "的刻度板，3/4 俯视角度。\n\n")
        f.write("## 结构\n\n")
        f.write("- 底座底盘（Plinth）：锥形圆柱，z 0–0.03，r 0.20→0.18，"
                "24 段，深木色\n")
        f.write("- 底盘饰环（PlinthTrim）：黄铜圆环，z 0.03，R 0.185，"
                "管 r 0.007\n")
        f.write("- 底座身（BaseBody）：锥形圆柱，z 0.03–0.06，"
                "r 0.16→0.13，24 段，木色\n")
        f.write("- 底座箍带（BaseBand）：黄铜圆环，z 0.06，R 0.135，"
                "管 r 0.006\n")
        f.write("- 立柱（Pillar）：锥形圆柱，z 0.06–0.40，r 0.028→0.022，"
                "12 段，黄铜\n")
        f.write("- 柱箍（Collar_1–2）：暗黄铜圆环，z 0.14 / 0.32，"
                "管 r 0.006\n")
        f.write("- 刻度板（DialPlate）：暗黄铜扁盒 0.06×0.008×0.03，"
                "立柱正面 z 0.315–0.345\n")
        f.write("- 指针臂（PointerArm）：暗黄铜柱，r 0.006，从横梁中心"
                "向前伸至 (0, -0.04, 0.42)\n")
        f.write("- 指针（Pointer）：锥形针，z 0.345–0.42，"
                "r 0.001→0.005，针尖正对刻度板顶缘\n")
        f.write("- 支点（Pivot）：暗黄铜球，r 0.02，横梁中心 z 0.42\n")
        f.write("- 横梁（Beam）：黄铜杆，沿 X 轴，z 0.42，长 0.52，"
                "r 0.012，8 段\n")
        f.write("- 梁端饰球（BeamFinial_1–2）：暗黄铜球，r 0.016，"
                "x ±0.26，z 0.42\n")
        f.write("- 柱顶饰球（TopFinial）：黄铜球，r 0.02，z 0.445\n")
        f.write("- 托盘（Pan_1–2）：浅锥台，底 r 0.03（z 0.285）→"
                "口 r 0.09（z 0.30），24 段，黄铜；顶面圆盘即盘面\n")
        f.write("- 盘沿（PanRim_1–2）：暗黄铜圆环，R 0.09，管 r 0.005，"
                "z 0.30\n")
        f.write("- 吊链（Chain_1_1–3 / Chain_2_1–3）：铁灰细柱，"
                "r 0.0025，4 段，每盘 3 根，从梁端汇聚至盘沿三点\n")
        f.write("- 砝码组（Weight_Large/Mid/Small）：右盘叠放三枚暗黄铜"
                "圆柱，r 0.030 / 0.022 / 0.015，高 0.02 / 0.018 / 0.015，"
                "16/16/12 段；大砝码带黄铜提钮（WeightKnob，r 0.008）\n")
        f.write("- 备用砝码（SpareWeight）：暗黄铜圆柱，r 0.028，"
                "高 0.025，置于地面 (0.32, 0.14)，带提钮 r 0.009\n")
        f.write("- 整体约 0.62 m 宽（梁端饰球外缘）× 0.465 m 高\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("圆环类部件用环中心线检测；其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Scale_Wood：底座身木色（roughness 0.75）\n")
        f.write("- Scale_WoodDark：底盘深木色（roughness 0.8）\n")
        f.write("- Scale_Brass：立柱/横梁/托盘/饰环黄铜"
                "（metallic 0.9，roughness 0.35）\n")
        f.write("- Scale_BrassDark：柱箍/刻度板/指针/支点/盘沿/砝码暗黄铜"
                "（metallic 0.85，roughness 0.45）\n")
        f.write("- Scale_Iron：吊链铁灰（metallic 0.85，roughness 0.5）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
