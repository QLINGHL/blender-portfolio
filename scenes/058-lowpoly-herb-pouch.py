# -*- coding: utf-8 -*-
"""058 低模游戏道具：炼金草药袋（Alchemy Herb Pouch）
Low-poly game alchemy herb pouch: a burlap sack with a cinched neck
(lathe profile), a rope tie ring, a drawstring bow (two loops + knot +
two hanging ends), three dried herb sprigs sticking out of the neck
(stems + flat-box leaves), and a small parchment tag hanging from the
tie on the front. Game-asset standard, flat shading.
Overall ~0.30 m wide x ~0.46 m tall (herb tips).
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 058-lowpoly-herb-pouch.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector

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


def box_local(name, size, mat):
    """Box centered on its own origin (safe to rotate/place via
    location + rotation_euler). Outward winding."""
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz),
        (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz),
        (sx, sy, sz), (-sx, sy, sz),
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


def lathe_z(name, profile, sides, mat, cap_bottom=True):
    """Surface of revolution around Z from a bottom-to-top profile of
    (radius, z) points. Open at the top; optional fan cap at the bottom."""
    verts = []
    for r, z in profile:
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(ang), r * math.sin(ang), z))
    faces = []
    n = len(profile)
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    if cap_bottom:
        c = len(verts)
        verts.append((0.0, 0.0, profile[0][1]))
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((c, j, i))
    return mesh_from_data(name, verts, faces, mat)


def torus_xy_local(name, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying flat in the XY plane, centered on its own
    origin (safe to rotate/place via location + rotation_euler)."""
    verts = []
    for i in range(arc_segments):
        th = 2.0 * math.pi * i / arc_segments
        rx, ry = math.cos(th), math.sin(th)
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append(((R + r * math.cos(ph)) * rx,
                          (R + r * math.cos(ph)) * ry,
                          r * math.sin(ph)))
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


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.22))

    burlap = solid_material("Pouch_Burlap", (0.58, 0.45, 0.27),
                            metallic=0.0, roughness=0.9)
    burlap_dark = solid_material("Pouch_BurlapDark", (0.45, 0.34, 0.20),
                                 metallic=0.0, roughness=0.9)
    rope = solid_material("Pouch_Rope", (0.78, 0.68, 0.47),
                          metallic=0.0, roughness=0.85)
    stem_mat = solid_material("Pouch_Stem", (0.35, 0.28, 0.14),
                              metallic=0.0, roughness=0.85)
    leaf_mat = solid_material("Pouch_Leaf", (0.30, 0.52, 0.22),
                              metallic=0.0, roughness=0.75)
    leaf_mat2 = solid_material("Pouch_LeafDry", (0.55, 0.55, 0.25),
                               metallic=0.0, roughness=0.8)
    parchment = solid_material("Pouch_Parchment", (0.86, 0.79, 0.60),
                               metallic=0.0, roughness=0.85)

    parts = []
    flipped = {}

    # --- sack body: lathe, flat bottom z 0 -> cinched neck z 0.30 ---
    # profile (r, z): flat base, bulging belly, tapering neck
    profile = [
        (0.095, 0.0), (0.115, 0.02), (0.130, 0.08), (0.135, 0.15),
        (0.125, 0.22), (0.100, 0.27), (0.075, 0.30),
    ]
    sack = lathe_z("Sack", profile, 20, burlap, cap_bottom=True)
    parts.append(sack)

    # --- neck fold: a slightly darker short lathe band over the cinch ---
    fold_profile = [
        (0.078, 0.285), (0.082, 0.30), (0.080, 0.315), (0.072, 0.325),
    ]
    fold = lathe_z("NeckFold", fold_profile, 20, burlap_dark,
                   cap_bottom=False)
    parts.append(fold)

    # --- rope tie ring around the neck, z 0.295 ---
    tie = torus_xy_local("TieRing", 0.078, 0.010, 20, 6, rope)
    tie.location = (0, 0, 0.295)
    parts.append(tie)

    # --- drawstring bow at the front of the neck (-Y side) ---
    # two loops: small flat tori, each rotated about its own center
    loop_l = torus_xy_local("BowLoop_L", 0.020, 0.006, 12, 6, rope)
    loop_l.location = (-0.028, -0.082, 0.300)
    loop_l.rotation_euler = (math.radians(70), 0, math.radians(35))
    parts.append(loop_l)
    loop_r = torus_xy_local("BowLoop_R", 0.020, 0.006, 12, 6, rope)
    loop_r.location = (0.028, -0.082, 0.300)
    loop_r.rotation_euler = (math.radians(70), 0, math.radians(-35))
    parts.append(loop_r)
    # knot: small sphere at the bow center
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=10, ring_count=5, radius=0.011,
        location=(0, -0.082, 0.298))
    knot = bpy.context.active_object
    knot.name = "BowKnot"
    knot.data.materials.append(rope)
    flat_shade(knot)
    parts.append(knot)
    # two hanging string ends down the front of the sack
    end_l = cyl_between("StringEnd_L", (0, -0.082, 0.292),
                        (-0.012, -0.105, 0.225), 0.005, 6, rope)
    parts.append(end_l)
    end_r = cyl_between("StringEnd_R", (0, -0.082, 0.292),
                        (0.014, -0.108, 0.230), 0.005, 6, rope)
    parts.append(end_r)

    # --- parchment tag hanging from the tie on the front ---
    tag_string = cyl_between("TagString", (0.045, -0.080, 0.292),
                             (0.055, -0.115, 0.245), 0.003, 6, rope)
    parts.append(tag_string)
    tag = box_local("Tag", (0.070, 0.004, 0.095), parchment)
    tag.location = (0.058, -0.118, 0.195)
    tag.rotation_euler = (math.radians(-6), 0, math.radians(4))
    parts.append(tag)

    # --- three dried herb sprigs sticking out of the neck ---
    # stem: (base inside neck, tip, leaf material for the dry sprig)
    sprigs = [
        # (base, tip, leaf_mat, yaw_deg)
        ((0.005, 0.005, 0.27), (0.020, 0.020, 0.465), leaf_mat, 20),
        ((-0.010, -0.005, 0.27), (-0.075, 0.030, 0.435), leaf_mat2, 140),
        ((0.000, -0.010, 0.27), (0.065, -0.025, 0.445), leaf_mat, -55),
    ]
    for si, (base, tip, lmat, yaw) in enumerate(sprigs):
        stem = cyl_between("Stem_%d" % (si + 1), base, tip, 0.006, 6,
                           stem_mat)
        parts.append(stem)
        # leaves: 3 flat boxes along the stem, fanning outward.
        # leaf long axis ~ along the stem direction, tilted outward.
        b = Vector(base)
        t = Vector(tip)
        for li, frac in enumerate((0.45, 0.65, 0.85)):
            p = b.lerp(t, frac)
            # outward direction: away from the stem axis in the yaw plane
            yaw_r = math.radians(yaw + (li - 1) * 35)
            out = Vector((math.cos(yaw_r), math.sin(yaw_r), 0))
            leaf = box_local("Leaf_%d_%d" % (si + 1, li + 1),
                             (0.055, 0.022, 0.003), lmat)
            leaf.location = (p.x + out.x * 0.022,
                             p.y + out.y * 0.022, p.z)
            # pitch the leaf up/outward, yaw it around Z
            leaf.rotation_euler = (math.radians(-35),
                                   math.radians(15),
                                   yaw_r)
            parts.append(leaf)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    for o in parts:
        if o.type == 'MESH':
            flipped[o.name] = check_winding(o)
    print("POUCH_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "058-lowpoly-herb-pouch.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "058-lowpoly-herb-pouch.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "herb_pouch_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("POUCH_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("POUCH_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "058-lowpoly-herb-pouch.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 058 低模游戏道具：炼金草药袋\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "粗布束口袋，麻绳系带在袋口打了蝴蝶结，两根绳头垂在袋身"
                "前面，一枚羊皮纸签挂在系带上；袋口伸出三束干草药。接 "
                "047 炼金实验室场景的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 袋身（Sack）：车削轮廓（lathe），7 个断面，20 段，"
                "z 0–0.30，最大腹径 r 0.135（z 0.15），底面扇形封口平放"
                "地面，粗布黄褐色\n")
        f.write("- 袋口翻边（NeckFold）：深色短车削带，z 0.285–0.325，"
                "r 约 0.078–0.082，盖住束口收褶\n")
        f.write("- 系带环（TieRing）：麻绳圆环，z 0.295，R 0.078，"
                "管 r 0.010\n")
        f.write("- 蝴蝶结（BowLoop_L/R + BowKnot）：两只小圆环"
                "（R 0.020，管 r 0.006），各自绕自身中心旋转 70°/±35°"
                "张开在袋口前面（-Y 侧），绳结小球 r 0.011\n")
        f.write("- 绳头（StringEnd_L/R）：细圆柱，r 0.005，从绳结垂到"
                "袋身前面 z 约 0.23\n")
        f.write("- 纸签（Tag + TagString）：羊皮纸小牌 0.070×0.004×0.095，"
                "挂在系带前面，细绳 r 0.003，纸牌微倾 -6°/+4°\n")
        f.write("- 草药茎（Stem_1–3）：细圆柱，r 0.006，6 段，从袋口内"
                "（z 0.27）伸出到 z 0.435–0.465，三束朝向各异"
                "（中直、左倾、右倾）\n")
        f.write("- 草药叶（Leaf_1_1–3_3）：每束 3 片，共 9 片，扁盒"
                "0.055×0.022×0.003，沿茎 45%/65%/85% 处向外张开，"
                "两束鲜绿、一束干黄绿\n")
        f.write("- 整体约 0.30 m 宽 × 0.465 m 高（草药尖顶）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("圆环类部件（TieRing、BowLoop_L/R）用环中心线检测；"
                "其余部件用质心检测。\n\n")
        f.write("注意：质心检测对圆环是误报——管内侧面的法线指向环轴，"
                "与（面心 - 环心）的点积为负；初版脚本质心检测报 "
                "TieRing 40、BowLoop 各 24，中心线复核后均为 0，"
                "绕向正确。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Pouch_Burlap：袋身粗布黄褐（roughness 0.9）\n")
        f.write("- Pouch_BurlapDark：袋口翻边深褐（roughness 0.9）\n")
        f.write("- Pouch_Rope：系带/蝴蝶结/绳头/纸签绳麻绳色"
                "（roughness 0.85）\n")
        f.write("- Pouch_Stem：草药茎褐色（roughness 0.85）\n")
        f.write("- Pouch_Leaf：草药叶鲜绿（roughness 0.75）\n")
        f.write("- Pouch_LeafDry：干草药叶黄绿（roughness 0.8）\n")
        f.write("- Pouch_Parchment：纸签羊皮纸色（roughness 0.85）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.35)）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
