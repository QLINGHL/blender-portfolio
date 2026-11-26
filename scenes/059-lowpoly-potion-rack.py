# -*- coding: utf-8 -*-
"""059 低模游戏道具：炼金药水架（Alchemy Potion Rack）
Low-poly game alchemy potion rack: a wooden two-shelf rack holding eight
potion bottles of different shapes (round flask / tall bottle / conical
flask / vial), each with glowing coloured liquid, a cork stopper and a
parchment label; three spare corks on the top board, brass nameplate on
the middle shelf. Game-asset standard, flat shading.
Overall ~0.59 m wide x ~0.55 m tall x ~0.17 m deep.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 059-lowpoly-potion-rack.py
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


def lathe_z(name, profile, sides, mat, z_base=0.0, cap_bottom=True):
    """Surface of revolution around Z from a bottom-to-top profile of
    (radius, z) points (z relative to z_base). Open at the top;
    optional fan cap at the bottom."""
    verts = []
    for r, z in profile:
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(ang), r * math.sin(ang),
                          z_base + z))
    faces = []
    n = len(profile)
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    if cap_bottom:
        c = len(verts)
        verts.append((0.0, 0.0, z_base + profile[0][1]))
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((c, j, i))
    return mesh_from_data(name, verts, faces, mat)


def radius_at(profile, z):
    """Linear interpolation of the profile radius at height z."""
    if z <= profile[0][1]:
        return profile[0][0]
    for k in range(len(profile) - 1):
        z0, z1 = profile[k][1], profile[k + 1][1]
        if z0 <= z <= z1:
            if z1 == z0:
                return profile[k][0]
            t = (z - z0) / (z1 - z0)
            return profile[k][0] + t * (profile[k + 1][0]
                                        - profile[k][0])
    return profile[-1][0]


def liquid_profile(profile, liq_h, scale=0.8):
    """Bottle profile clipped to the liquid height, radii scaled in."""
    pts = []
    for r, z in profile:
        if z <= liq_h:
            pts.append((r * scale, z))
    pts.append((radius_at(profile, liq_h) * scale, liq_h))
    return pts


def make_glass(name, color, alpha=0.45):
    """Stylized glass: Principled BSDF with alpha + dithered
    transparency, so the glowing liquid inside stays visible."""
    mat = solid_material(name, color, metallic=0.0, roughness=0.15)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = alpha
    mat.surface_render_method = 'DITHERED'
    return mat


def glow_material(name, color, strength=0.6, mix_fac=0.55):
    """Principled base color + an Emission node mixed in, for glowing
    potion liquid."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = mix_fac
    out = nt.nodes["Material Output"]
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
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


# Bottle body profiles (radius, z), base at z 0.
PROFILES = {
    # round flask: bulging belly, narrow neck
    "round": [(0.001, 0.0), (0.040, 0.004), (0.052, 0.04),
              (0.050, 0.08), (0.030, 0.105), (0.016, 0.120),
              (0.014, 0.135), (0.014, 0.145)],
    # tall bottle: straight body, shoulder, neck
    "tall": [(0.001, 0.0), (0.030, 0.004), (0.033, 0.10),
             (0.030, 0.13), (0.016, 0.145), (0.014, 0.155),
             (0.014, 0.17)],
    # conical (Erlenmeyer) flask: wide cone base, short neck
    "conical": [(0.001, 0.0), (0.048, 0.004), (0.046, 0.02),
                (0.030, 0.07), (0.016, 0.10), (0.014, 0.115),
                (0.014, 0.125)],
    # small vial: slim cylinder, short neck
    "vial": [(0.001, 0.0), (0.022, 0.003), (0.024, 0.06),
             (0.020, 0.075), (0.012, 0.085), (0.011, 0.09),
             (0.011, 0.10)],
}


def make_bottle(tag, kind, x, z_base, glass_mat, liquid_mat, cork_mat,
                label_mat, parts):
    """One bottle: glass lathe + glowing liquid + top disc + cork +
    parchment label on the front (-Y). Returns (top_z, max_r)."""
    prof = PROFILES[kind]
    height = prof[-1][1]
    max_r = max(r for r, _ in prof)
    glass = lathe_z("Bottle_%s" % tag, prof, 16, glass_mat,
                    z_base=z_base, cap_bottom=True)
    glass.location.x = x
    parts.append(glass)
    # liquid: clipped profile, filled to ~65% of body height
    liq_h = height * 0.65
    liq = lathe_z("Liquid_%s" % tag,
                  liquid_profile(prof, liq_h, 0.8), 16, liquid_mat,
                  z_base=z_base, cap_bottom=True)
    liq.location.x = x
    parts.append(liq)
    # liquid top disc
    r_top = radius_at(prof, liq_h) * 0.8
    disc = tapered_cyl_z("LiquidTop_%s" % tag, z_base + liq_h,
                         z_base + liq_h + 0.003, r_top, r_top, 16,
                         liquid_mat)
    disc.location.x = x
    parts.append(disc)
    # cork stopper in the neck
    neck_r = prof[-1][0]
    cork = tapered_cyl_z("Cork_%s" % tag, z_base + height - 0.006,
                         z_base + height + 0.022,
                         neck_r * 0.85, neck_r * 1.05, 8, cork_mat)
    cork.location.x = x
    parts.append(cork)
    # parchment label on the front, tilted to hug the wall slope
    # (radius at label bottom vs top); without the tilt the label's
    # lower edge sinks into a conical bottle's widening wall.
    label_h = height * 0.30
    label_z = z_base + height * 0.38
    r_bot = radius_at(prof, height * 0.38 - label_h / 2)
    r_top = radius_at(prof, height * 0.38 + label_h / 2)
    r_lab = radius_at(prof, height * 0.38)
    tilt = math.atan2(r_bot - r_top, label_h)
    label_w = min(0.05, max_r * 1.1)
    label = box_local("Label_%s" % tag,
                      (label_w, 0.002, label_h), label_mat)
    label.location = (x, -(r_lab + 0.0005), label_z)
    label.rotation_euler = (-tilt, 0, 0)
    parts.append(label)
    return z_base + height + 0.022, max_r


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.27))

    wood = solid_material("Rack_Wood", (0.42, 0.28, 0.15),
                          metallic=0.0, roughness=0.85)
    wood_dark = solid_material("Rack_WoodDark", (0.30, 0.19, 0.10),
                               metallic=0.0, roughness=0.9)
    brass = solid_material("Rack_Brass", (0.55, 0.38, 0.12),
                           metallic=0.7, roughness=0.35)
    cork_mat = solid_material("Rack_Cork", (0.62, 0.45, 0.26),
                              metallic=0.0, roughness=0.9)
    parchment = solid_material("Rack_Parchment", (0.86, 0.79, 0.60),
                               metallic=0.0, roughness=0.85)
    glass_amber = make_glass("Glass_Amber", (0.75, 0.45, 0.15))
    glass_green = make_glass("Glass_Green", (0.35, 0.55, 0.25))
    glass_blue = make_glass("Glass_Blue", (0.25, 0.45, 0.65))
    glass_red = make_glass("Glass_Red", (0.65, 0.25, 0.20))
    glass_teal = make_glass("Glass_Teal", (0.25, 0.55, 0.55))
    glass_purple = make_glass("Glass_Purple", (0.45, 0.30, 0.60))
    liq_amber = glow_material("Liquid_Amber", (0.85, 0.50, 0.12),
                              strength=0.7, mix_fac=0.55)
    liq_green = glow_material("Liquid_Green", (0.35, 0.75, 0.25),
                              strength=0.7, mix_fac=0.55)
    liq_blue = glow_material("Liquid_Blue", (0.25, 0.55, 0.95),
                             strength=0.7, mix_fac=0.55)
    liq_red = glow_material("Liquid_Red", (0.90, 0.25, 0.20),
                            strength=0.7, mix_fac=0.55)
    liq_teal = glow_material("Liquid_Teal", (0.25, 0.75, 0.70),
                             strength=0.7, mix_fac=0.55)
    liq_purple = glow_material("Liquid_Purple", (0.60, 0.35, 0.85),
                               strength=0.7, mix_fac=0.55)

    parts = []

    # --- wooden rack: 2 posts, 2 shelves, top board, back rail ---
    for sx in (-1, 1):
        post = box_local("Post_%s" % ("L" if sx < 0 else "R"),
                         (0.045, 0.06, 0.54), wood)
        post.location = (sx * 0.27, 0, 0.27)
        parts.append(post)
    for zi, zc in enumerate((0.03, 0.27, 0.51)):
        shelf = box_local("Shelf_%d" % (zi + 1),
                          (0.585, 0.17, 0.03),
                          wood if zi < 2 else wood_dark)
        shelf.location = (0, 0, zc)
        parts.append(shelf)
    rail = box_local("BackRail", (0.50, 0.02, 0.04), wood_dark)
    rail.location = (0, 0.075, 0.44)
    parts.append(rail)
    # brass nameplate on the middle shelf front
    plate = box_local("Nameplate", (0.12, 0.002, 0.03), brass)
    plate.location = (0, -0.086, 0.27)
    parts.append(plate)

    # --- bottles ---
    # lower shelf, base z 0.045
    tops = {}
    tops["L1"] = make_bottle("L1", "round", -0.19, 0.045, glass_amber,
                             liq_amber, cork_mat, parchment, parts)
    tops["L2"] = make_bottle("L2", "tall", -0.075, 0.045, glass_green,
                             liq_green, cork_mat, parchment, parts)
    tops["L3"] = make_bottle("L3", "vial", 0.035, 0.045, glass_blue,
                             liq_blue, cork_mat, parchment, parts)
    tops["L4"] = make_bottle("L4", "conical", 0.16, 0.045, glass_purple,
                             liq_purple, cork_mat, parchment, parts)
    # upper shelf, base z 0.285
    tops["U1"] = make_bottle("U1", "round", -0.19, 0.285, glass_red,
                             liq_red, cork_mat, parchment, parts)
    tops["U2"] = make_bottle("U2", "tall", -0.05, 0.285, glass_teal,
                             liq_teal, cork_mat, parchment, parts)
    tops["U3"] = make_bottle("U3", "vial", 0.08, 0.285, glass_amber,
                             liq_amber, cork_mat, parchment, parts)
    tops["U4"] = make_bottle("U4", "conical", 0.19, 0.285, glass_green,
                             liq_green, cork_mat, parchment, parts)

    # --- three spare corks standing on the top board ---
    for i, cx in enumerate((-0.10, 0.0, 0.10)):
        spare = tapered_cyl_z("SpareCork_%d" % (i + 1), 0.525, 0.552,
                              0.011, 0.014, 8, cork_mat)
        spare.location.x = cx
        parts.append(spare)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {}
    for o in parts:
        if o.type == 'MESH':
            flipped[o.name] = check_winding(o)
    print("RACK_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.30),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 samples=64)

    render(os.path.join(ROOT, "renders", "059-lowpoly-potion-rack.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "059-lowpoly-potion-rack.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "potion_rack_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("RACK_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("RACK_POLY %s=%d" % (name, c))
    print("RACK_TOPS:", tops)

    note = os.path.join(ROOT, "scenes", "059-lowpoly-potion-rack.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 059 低模游戏道具：炼金药水架\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "双层木架，上下两层共 8 瓶不同形状的药水（圆腹瓶 / 高身瓶 / "
                "锥形瓶 / 小药瓶），瓶内彩色药水自发光，软木塞封口，羊皮纸"
                "标签贴在瓶身前面；顶板上立着 3 个备用软木塞，中层前面嵌"
                "一块黄铜铭牌。接 047 炼金实验室场景的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 木架（Post_L/R + Shelf_1/2/3 + BackRail）：两根立柱 "
                "0.045×0.06×0.54（x ±0.27），下层板 / 中层板 / 顶板 "
                "0.585×0.17×0.03（z 0.03/0.27/0.51），后横档 0.50×0.02×"
                "0.04（y 0.075，z 0.44），深色木\n")
        f.write("- 铭牌（Nameplate）：黄铜薄板 0.12×0.002×0.03，嵌在中层板"
                "前面（y -0.086，z 0.27），金属度 0.7\n")
        f.write("- 瓶身（Bottle_*）：车削轮廓（lathe），16 段，底面扇形封口；"
                "圆腹瓶高 0.145（最大腹径 r 0.052）、高身瓶高 0.17（r 0.033）、"
                "锥形瓶高 0.125（底 r 0.048）、小药瓶高 0.10（r 0.024）；"
                "瓶身为半透明玻璃（Alpha 0.45，dithered），透出瓶内发光药水\n")
        f.write("- 药水（Liquid_* + LiquidTop_*）：瓶身轮廓按 0.8 缩径、"
                "截到瓶高 65% 处，顶部加薄圆盘封口；自发光材质"
                "（Emission 0.7，混合 55%），六色：琥珀 / 绿 / 蓝 / 红 / "
                "青 / 紫\n")
        f.write("- 瓶塞（Cork_*）：锥形圆柱，8 段，颈口 r 约 0.014，塞入瓶颈、"
                "露出约 0.022\n")
        f.write("- 标签（Label_*）：羊皮纸薄板，宽取 min(0.05, 最大腹径×1.1)，"
                "高为瓶高 30%，贴在瓶身前面（-Y），按标签高度处轮廓半径定位；"
                "标签按瓶壁斜率倾斜（atan2(下沿半径-上沿半径, 标签高)），"
                "锥形瓶下沿不再埋进瓶壁\n")
        f.write("- 下层（z 0.045）：L1 圆腹琥珀、L2 高身绿、L3 小药瓶蓝、"
                "L4 锥形紫\n")
        f.write("- 修复记录（061，2026-11-26）：060 质检单发现 Bottle_L1 "
                "卡进 Post_L（4 个顶点在立柱体内，最深 0.0045 m）；L1 向内"
                "移 0.01 m（x -0.20 → -0.19，与 U1 对齐），修完重跑 060 "
                "质检脚本复核到 PASS\n")
        f.write("- 上层（z 0.285）：U1 圆腹红、U2 高身青、U3 小药瓶琥珀、"
                "U4 锥形绿；上层最高瓶顶（瓶塞）约 z 0.477，顶板底 0.495，"
                "不穿帮\n")
        f.write("- 备用软木塞（SpareCork_1–3）：3 个锥形圆柱立在顶板上"
                "（z 0.525–0.552，x -0.10/0/0.10）\n")
        f.write("- 整体约 0.59 m 宽 × 0.55 m 高 × 0.17 m 深\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("质心检测，全部部件逐一核查。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Rack_Wood / Rack_WoodDark：木架棕色 / 深棕"
                "（roughness 0.85/0.9）\n")
        f.write("- Rack_Brass：铭牌黄铜（metallic 0.7，roughness 0.35）\n")
        f.write("- Rack_Cork：瓶塞软木色（roughness 0.9）\n")
        f.write("- Rack_Parchment：标签羊皮纸色（roughness 0.85）\n")
        f.write("- Glass_*：六色瓶身，浅色玻璃色（roughness 0.15）\n")
        f.write("- Liquid_*：六色药水自发光（Emission 0.7，混合 55%）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.30)）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
