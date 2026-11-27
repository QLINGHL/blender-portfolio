# -*- coding: utf-8 -*-
"""066 低模游戏道具：炼金漏斗与量杯（Alchemy Funnel & Measuring Cup）
Low-poly game alchemy funnel and measuring cup: a clear glass funnel
(cone + stem) with glowing green liquid inside, held by a brass ring
on a wooden stand, dripping into a graduated glass measuring cup
(tapered walls, 4 graduation rings, glowing amber liquid) below.
Game-asset standard, flat shading.
Overall ~0.44 m wide x ~0.52 m tall x ~0.30 m deep.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 066-lowpoly-funnel-beaker.py
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
    (radius, z) points (z relative to z_base). Optional fan cap at the
    bottom."""
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


def make_glass(name, color, alpha=0.35):
    """Stylized glass: Principled BSDF with alpha + dithered
    transparency, so the glowing liquid inside stays visible (059)."""
    mat = solid_material(name, color, metallic=0.0, roughness=0.15)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = alpha
    mat.surface_render_method = 'DITHERED'
    return mat


def glow_material(name, color, strength=0.7, mix_fac=0.55, roughness=0.35):
    """Principled base color + an Emission node mixed in, for glowing
    potion liquid."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
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
    """Centroid check: count faces whose normal points inward."""
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


def check_lathe_winding(obj, profile, sides):
    """Winding check for a lathe mesh, in local space (062)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = []
    nseg = len(profile) - 1
    for idx, f in enumerate(bm.faces):
        k = idx // sides
        if k >= nseg:
            continue  # cap fan
        c = f.calc_center_median()
        if math.hypot(c.x, c.y) < 0.005:
            continue
        r0, z0 = profile[k]
        r1, z1 = profile[k + 1]
        dr, dz = r1 - r0, z1 - z0
        ln = math.hypot(dr, dz)
        if ln < 1e-9:
            continue
        n_r, n_z = dz / ln, -dr / ln
        theta = math.atan2(c.y, c.x)
        exp = Vector((n_r * math.cos(theta), n_r * math.sin(theta), n_z))
        if f.normal.normalized().dot(exp) < -0.001:
            flipped.append(idx)
    bm.free()
    return flipped


def check_torus_winding_xy(obj, R, center):
    """Winding check for a flat ring (055)."""
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


# Funnel profile (radius, local z): stem bottom -> stem top -> cone
# flare -> rim. Local z_base 0.017 lifts the funnel so the cone rests
# in the brass ring at world z 0.42: cone radius at local z 0.403 is
# 0.0879, ring inner radius is 0.088 (R 0.095 - tube 0.007).
FUNNEL_PROFILE = [
    (0.022, 0.160), (0.022, 0.300), (0.050, 0.330), (0.090, 0.400),
    (0.125, 0.460), (0.150, 0.500),
]
FUNNEL_Z_BASE = 0.017
RING_Z = 0.42
RING_R = 0.095
RING_TUBE = 0.007


def funnel_radius_at(world_z):
    """Cone radius of the funnel at a world height (linear interp on
    the cone section, local z 0.30..0.50)."""
    lz = world_z - FUNNEL_Z_BASE
    if lz <= 0.30:
        return 0.022
    return 0.022 + (lz - 0.30) / 0.20 * (0.150 - 0.022)


def cup_radius_at(z):
    """Measuring cup outer radius at height z (taper 0.075 -> 0.085
    over z 0.02..0.15)."""
    return 0.075 + (z - 0.02) / 0.13 * 0.010


def cup_inner_radius_at(z):
    """Measuring cup inner radius at height z (inner wall from
    (0.082, 0.15) down to (0.072, 0.03))."""
    return 0.082 - (0.15 - z) / 0.12 * 0.010


# Measuring cup profile (radius, z): bottom center -> outer bottom
# edge -> outer wall up -> over the rim -> inner wall down -> cavity
# floor center. One continuous lathe like the 062 mortar: the cup is
# OPEN at the top, no lid (a real measuring cup has no lid).
CUP_PROFILE = [
    (0.001, 0.020), (0.075, 0.020), (0.085, 0.150), (0.082, 0.150),
    (0.072, 0.030), (0.001, 0.030),
]


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.26))

    wood = solid_material("Stand_Wood", (0.38, 0.26, 0.13),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Stand_WoodDark", (0.30, 0.20, 0.10),
                               metallic=0.0, roughness=0.85)
    brass = solid_material("Ring_Brass", (0.55, 0.40, 0.15),
                           metallic=0.7, roughness=0.35)
    glass = make_glass("Glass_Clear", (0.80, 0.85, 0.88), alpha=0.35)
    liq_green = glow_material("Liquid_Green", (0.35, 0.75, 0.25),
                              strength=0.7, mix_fac=0.55)
    liq_amber = glow_material("Liquid_Amber", (0.45, 0.18, 0.02),
                              strength=0.5, mix_fac=0.4, roughness=0.9)
    mark = solid_material("Graduation_Dark", (0.12, 0.11, 0.10),
                          metallic=0.0, roughness=0.7)

    parts = []

    # --- wooden stand: base plate + 2 posts + top crossbar ---
    base = box_local("StandBase", (0.44, 0.30, 0.02), wood)
    base.location = (0, 0, 0.01)
    parts.append(base)
    for sx in (-1, 1):
        post = box_local("StandPost_%s" % ("L" if sx < 0 else "R"),
                         (0.04, 0.05, 0.44), wood)
        post.location = (sx * 0.17, 0, 0.24)
        parts.append(post)
    crossbar = box_local("StandCrossbar", (0.38, 0.05, 0.04), wood_dark)
    crossbar.location = (0, 0, 0.46)
    parts.append(crossbar)

    # --- brass ring holding the funnel + 2 connector arms to posts ---
    ring = torus_xy("FunnelRing", (0, 0, RING_Z), RING_R, RING_TUBE,
                    24, 6, brass)
    parts.append(ring)
    for sx in (-1, 1):
        arm = box_local("RingArm_%s" % ("L" if sx < 0 else "R"),
                        (0.075, 0.03, 0.02), brass)
        arm.location = (sx * 0.135, 0, RING_Z)
        parts.append(arm)

    # --- glass funnel: lathe cone + stem, rolled rim lip ---
    funnel = lathe_z("Funnel", FUNNEL_PROFILE, 24, glass,
                     z_base=FUNNEL_Z_BASE, cap_bottom=False)
    parts.append(funnel)
    rim_lip = torus_xy("FunnelRimLip", (0, 0, FUNNEL_Z_BASE + 0.500),
                       0.150, 0.005, 24, 6, glass)
    parts.append(rim_lip)

    # --- green liquid inside the funnel: truncated cone, top surface
    # at world z 0.457 (local 0.44, inside the cone: funnel radius
    # there 0.1116, liquid top radius 0.104); stem section inset so
    # the liquid stays inside the funnel wall all the way down. ---
    funnel_liq = tapered_cyl_z("FunnelLiquid", 0.322, 0.457,
                               0.026, 0.104, 24, liq_green)
    parts.append(funnel_liq)

    # --- graduated measuring cup: open-topped lathe (outer wall up,
    # over the rim, inner wall down to the cavity floor). v5: the
    # tapered_cyl_z version had a glass top cap closing the cup mouth;
    # at the 24-degree camera angle that flat cap reflected the white
    # studio (grazing Fresnel) and hid the amber liquid completely —
    # three material changes (colour x2, roughness) moved the sampled
    # top-disc pixels by <4/255, proving the cap, not the colour, was
    # the problem. A measuring cup is open; the lathe leaves it open
    # like the 062 mortar bowl. ---
    cup = lathe_z("MeasuringCup", CUP_PROFILE, 24, glass,
                  z_base=0.0, cap_bottom=True)
    parts.append(cup)

    # --- amber liquid in the cup, top surface at z 0.11 (inner wall
    # radius there 0.0787, liquid top radius 0.076). ---
    cup_liq = tapered_cyl_z("CupLiquid", 0.031, 0.11, 0.070, 0.076,
                            24, liq_amber)
    parts.append(cup_liq)

    # --- 4 graduation rings around the cup exterior ---
    grad_profiles = []
    for i, z in enumerate((0.05, 0.075, 0.10, 0.125)):
        r = cup_radius_at(z) + 0.001
        prof = [(r, z - 0.0015), (r, z + 0.0015)]
        grad_profiles.append(prof)
        ring_mark = lathe_z("GradRing_%d" % (i + 1), prof, 24, mark,
                            z_base=0.0, cap_bottom=False)
        parts.append(ring_mark)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    # Winding checks.
    lathe_flipped = {
        "Funnel": check_lathe_winding(funnel, FUNNEL_PROFILE, 24),
        "MeasuringCup": check_lathe_winding(cup, CUP_PROFILE, 24),
    }
    for i, prof in enumerate(grad_profiles):
        lathe_flipped["GradRing_%d" % (i + 1)] = check_lathe_winding(
            bpy.data.objects["GradRing_%d" % (i + 1)], prof, 24)
    print("FUNNEL_WINDING_LATHE:", {k: len(v)
                                    for k, v in lathe_flipped.items()})
    torus_flipped = {
        "FunnelRing": check_torus_winding_xy(ring, RING_R, (0, 0, RING_Z)),
        "FunnelRimLip": check_torus_winding_xy(
            rim_lip, 0.150, (0, 0, FUNNEL_Z_BASE + 0.500)),
    }
    print("FUNNEL_WINDING_TORUS:", torus_flipped)
    flipped = {}
    for o in parts:
        if o.type == 'MESH' and o.name not in (
                "Funnel", "MeasuringCup", "FunnelRing", "FunnelRimLip") \
                and not o.name.startswith("GradRing_"):
            flipped[o.name] = check_winding(o)
    print("FUNNEL_WINDING_CENTROID:", flipped)

    # Measured clearances (no invented numbers):
    # 1. funnel stem bottom vs cup rim (drip gap)
    stem_bottom_z = FUNNEL_Z_BASE + 0.160
    cup_rim_z = 0.15
    print("FUNNEL_GAP stem_bottom_z=%.3f cup_rim_z=%.3f gap=%.3f"
          % (stem_bottom_z, cup_rim_z, stem_bottom_z - cup_rim_z))
    # 2. cone radius at the ring plane vs ring inner radius
    cone_r = funnel_radius_at(RING_Z)
    print("FUNNEL_RING cone_r_at_ring=%.4f ring_inner=%.4f diff=%.4f"
          % (cone_r, RING_R - RING_TUBE, cone_r - (RING_R - RING_TUBE)))
    # 3. funnel liquid radius vs funnel inner radius at several heights
    liq_clear = {}
    for wz in (0.36, 0.41, 0.457):
        lz = (wz - 0.322) / (0.457 - 0.322)
        liq_r = 0.026 + lz * (0.104 - 0.026)
        liq_clear[wz] = funnel_radius_at(wz) - liq_r
        print("FUNNEL_LIQ z=%.3f liquid_r=%.4f funnel_r=%.4f "
              "clearance=%.4f" % (wz, liq_r, funnel_radius_at(wz),
                                  liq_clear[wz]))
    # 4. cup liquid radius vs cup inner radius at its top surface
    print("CUP_LIQ top_z=0.110 liquid_r=0.0760 cup_inner_r=%.4f "
          "clearance=%.4f"
          % (cup_inner_radius_at(0.11),
             cup_inner_radius_at(0.11) - 0.076))
    # 5. graduation ring radius vs cup radius (should sit 0.001 proud)
    for z in (0.05, 0.075, 0.10, 0.125):
        print("GRAD_RING z=%.3f cup_r=%.4f ring_r=%.4f"
              % (z, cup_radius_at(z), cup_radius_at(z) + 0.001))

    # Camera: higher elevation (0,-1,0.45) so the green liquid surface
    # inside the funnel stays visible over the rim (062 lesson).
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.45),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 samples=64)

    render(os.path.join(ROOT, "renders",
                        "066-lowpoly-funnel-beaker.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "066-lowpoly-funnel-beaker.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "funnel_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("FUNNEL_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("FUNNEL_POLY %s=%d" % (name, c))
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in parts:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    print("FUNNEL_SIZE: %.3f x %.3f x %.3f m" % (
        maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z))

    note = os.path.join(ROOT, "scenes", "066-lowpoly-funnel-beaker.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 066 低模游戏道具：炼金漏斗与量杯\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "木质支架（底板 + 双立柱 + 顶横梁）上装一枚黄铜圆环，玻璃"
                "漏斗的锥体正好卡在圆环里，漏斗内是发光绿药液；漏斗细管"
                "正下方放一只带 4 道刻度环的玻璃量杯，杯内是发光琥珀色药"
                "液。接 047 炼金实验室场景的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 木质支架（StandBase / StandPost_L/R / StandCrossbar）："
                "底板 0.44×0.30×0.02，双立柱 0.04×0.05×0.44（x ±0.17），"
                "顶横梁 0.38×0.05×0.04（z 0.46）\n")
        f.write("- 黄铜圆环（FunnelRing）：平放圆环 R 0.095、管径 0.007，"
                "位于 z 0.42；两根黄铜连接臂（RingArm_L/R，0.075×0.03×"
                "0.02）把圆环连到立柱上\n")
        f.write("- 玻璃漏斗（Funnel）：车削轮廓 6 个断面、24 段；细管半径 "
                "0.022（z 0.16–0.30，局部坐标）、锥体由 0.05 张到 0.15"
                "（z 0.33–0.50）；整体抬高 z_base 0.017，使锥体在圆环平面"
                "（z 0.42）处的半径 0.0879 正好等于圆环内径 0.088，锥体卡"
                "在环里；口沿一圈玻璃卷边（FunnelRimLip，R 0.150、管径 "
                "0.005）\n")
        f.write("- 漏斗药液（FunnelLiquid）：截锥，底径 0.026、顶径 0.104，"
                "顶面 z 0.457（漏斗内锥半径 0.1116，余量 0.0076）；发光绿"
                "（Emission 0.7，混合 55%）\n")
        f.write("- 玻璃量杯（MeasuringCup）：开口车削杯，6 个断面、24 段；"
                "一条连续轮廓：底面中心 → 外底沿（半径 0.075，z 0.02）"
                "→ 外壁上行到口沿（半径 0.085，z 0.15）→ 越过杯口 → "
                "内壁下行到杯腔底面（半径 0.072，z 0.03）→ 腔底中心；"
                "杯壁厚 0.003，杯口敞开无盖（062 研钵同款做法）。v5 "
                "改法原因：v1–v4 用锥形筒做杯，顶部有一层玻璃盖封住杯"
                "口，24° 俯角下那层平盖以掠射角反射白色影棚，把杯内药"
                "液完全盖住——三次改材质（颜色 ×2、roughness）顶面像素"
                "变化不到 4/255，证明问题在盖不在颜色\n")
        f.write("- 杯内药液（CupLiquid）：截锥，底径 0.070、顶径 0.076，"
                "底面 z 0.031（腔底 z 0.03 之上）、顶面 z 0.11（杯内壁"
                "半径 0.0787，余量 0.0027）；发光琥珀色\n")
        f.write("- 刻度环（GradRing_1–4）：杯外壁 4 道细环，z 0.05 / 0.075"
                " / 0.10 / 0.125，半径比当地杯壁大 0.001、高 0.003\n")
        f.write("- 漏斗细管底端 z 0.177，量杯口沿 z 0.15，滴落间隙 0.027\n")
        f.write("- 整体约 0.44 m 宽 × 0.52 m 高 × 0.30 m 深\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("车削件（Funnel / MeasuringCup / GradRing_1–4）用轮廓段"
                "法线检查；圆环"
                "（FunnelRing / FunnelRimLip）用环中心线法线检查；其余凸"
                "形部件用质心法检查。\n\n")
        for name, bad in lathe_flipped.items():
            f.write("- %s：轮廓段法线检查，内翻面 %d\n"
                    % (name, len(bad)))
        for name, n in torus_flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 实测间隙\n\n")
        f.write("- 漏斗细管底端 z 0.177 − 量杯口沿 z 0.15 = 滴落间隙 "
                "0.027\n")
        f.write("- 圆环平面 z 0.42：漏斗锥半径 0.0879，圆环内径 0.088，"
                "差值 -0.0001（锥体正好卡在环里）\n")
        f.write("- 漏斗药液与漏斗内壁间隙：z 0.36 处 %.4f，z 0.41 处 "
                "%.4f，顶面 %.4f\n"
                % (liq_clear[0.36], liq_clear[0.41], liq_clear[0.457]))
        f.write("- 杯内药液顶面与杯内壁间隙 0.0027（顶径 0.076，杯内壁"
                "半径 0.0787）；药液底面 z 0.031，腔底 z 0.03\n")
        f.write("- 刻度环比杯壁外探 0.001\n\n")
        f.write("## 材质\n\n")
        f.write("- Stand_Wood / Stand_WoodDark：支架暖棕木 / 深棕横梁"
                "（roughness 0.8 / 0.85）\n")
        f.write("- Ring_Brass：黄铜圆环与连接臂（metallic 0.7，"
                "roughness 0.35）\n")
        f.write("- Glass_Clear：漏斗与量杯无色玻璃（Alpha 0.35，"
                "dithered，roughness 0.15；059 同款做法，瓶内药液可见）\n")
        f.write("- Liquid_Green / Liquid_Amber：漏斗绿药液 / 杯内琥珀"
                "药液（Emission 0.7 / 0.5，混合 55% / 40%；杯内药液两"
                "次加深：v1 用 059 同款琥珀 (0.85, 0.50, 0.12) 渲出来发"
                "白发奶油，v2 (0.78, 0.38, 0.05) 仍近白——像素实测顶面 "
                "(225, 221, 219) 与背景 (225, 226, 228) 几乎无差，根因"
                "是顶面正对主光过曝而非底色不够深；v3 降到 (0.45, 0.18, "
                "0.02) 并把 Emission 降到 0.5 / 混合 40%，顶面仍近白"
                "——放大看杯体侧面已有米黄药液色，顶面是朝上的平面对"
                "白色天光的镜面反射（roughness 0.35）盖住了底色；v4 "
                "把琥珀药液 roughness 提到 0.9 压掉顶面反光）\n")
        f.write("- Graduation_Dark：刻度环深灰（roughness 0.7）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.45)；俯角比常规 0.30 高，为看清漏斗内药"
                "液面；062 同款教训）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
