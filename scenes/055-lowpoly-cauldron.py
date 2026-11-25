# -*- coding: utf-8 -*-
"""055 低模游戏道具：炼金坩埚（Alchemy Cauldron）
Low-poly game alchemy cauldron: cast-iron pot (lathe profile) on three
splayed legs, an iron belly band, two loop handles, a glowing green
potion surface with bubbles, a wooden stir stick resting across the
rim, and a small campfire (crossed logs + three stylized flames)
burning underneath. Game-asset standard, flat shading.
Overall ~0.55 m wide (handles) x ~0.42 m tall (stick top).
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 055-lowpoly-cauldron.py
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


def lathe_z(name, profile, sides, mat, cap_bottom=True):
    """Surface of revolution around Z from a bottom-to-top profile of
    (radius, z) points. Open at the top; optional fan cap at the bottom
    (only valid if the first profile point has radius ~0... no: the fan
    closes the bottom ring to the axis point at the first ring's z).
    Same quad winding as tapered_cyl_z (outward)."""
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


def torus_yz(name, center, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying in the YZ plane (vertical loop), centered at
    `center`. Built directly in the YZ plane -- do NOT build a flat
    torus_xy and rotate the object: rotation_euler rotates about the
    world origin and displaces the ring (055 v1: both handles ended up
    at x 0.33, one underground)."""
    cx, cy, cz = center
    verts = []
    for i in range(arc_segments):
        th = 2.0 * math.pi * i / arc_segments
        # centerline point in the YZ plane
        py, pz = cy + R * math.cos(th), cz + R * math.sin(th)
        # tube circle: X axis + radial direction in the YZ plane
        ry, rz = math.cos(th), math.sin(th)
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + r * math.cos(ph),
                          py + r * math.sin(ph) * ry,
                          pz + r * math.sin(ph) * rz))
    faces = []
    for i in range(arc_segments):
        ni = (i + 1) % arc_segments
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            # NB: the (th, ph) grid maps to the YZ plane with opposite
            # orientation vs torus_xy, so the quad winds the other way
            # round for outward normals (v2 fix: all 96 faces flipped).
            faces.append((i * tube_segments + j, i * tube_segments + k,
                          ni * tube_segments + k, ni * tube_segments + j))
    return mesh_from_data(name, verts, faces, mat)


def emissive_material(name, color, strength=1.0, mix_fac=0.45):
    """Principled base color + an Emission node mixed in, for glowing
    potion liquid / flames."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
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


def check_torus_winding_yz(obj, R, center):
    """Same as check_torus_winding_xy but for a torus rotated 90 deg about
    Y (ring plane YZ, centerline circle in the YZ plane)."""
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
        dy, dz = c.y - cy, c.z - cz
        L = math.hypot(dy, dz)
        if L < 1e-9:
            continue
        nearest = Vector((cx, cy + R * dy / L, cz + R * dz / L))
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.22))

    iron = solid_material("Cauldron_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.55)
    iron_dark = solid_material("Cauldron_IronDark", (0.10, 0.10, 0.11),
                               metallic=0.65, roughness=0.6)
    wood = solid_material("Cauldron_Wood", (0.36, 0.22, 0.12),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Cauldron_WoodDark", (0.24, 0.15, 0.08),
                               metallic=0.0, roughness=0.85)
    potion = emissive_material("Cauldron_Potion", (0.22, 0.72, 0.22),
                               strength=0.8, mix_fac=0.7)
    bubble_mat = emissive_material("Cauldron_Bubble", (0.45, 0.90, 0.40),
                                   strength=0.6, mix_fac=0.6)
    flame = emissive_material("Cauldron_Flame", (0.95, 0.45, 0.10),
                              strength=1.2, mix_fac=0.7)
    flame_core = emissive_material("Cauldron_FlameCore", (0.98, 0.80, 0.25),
                                   strength=1.4, mix_fac=0.7)

    parts = []
    flipped = {}

    # --- pot body: lathe, bottom z 0.14 -> rim z 0.40 ---
    # profile (r, z): foot, belly, shoulder, rim
    profile = [
        (0.085, 0.14), (0.115, 0.16), (0.145, 0.21), (0.160, 0.27),
        (0.158, 0.32), (0.145, 0.36), (0.138, 0.40),
    ]
    pot = lathe_z("Pot", profile, 24, iron, cap_bottom=True)
    parts.append(pot)

    # --- rim torus at the pot mouth, z 0.40 ---
    rim = torus_xy("Rim", (0, 0, 0.40), 0.138, 0.009, 24, 6, iron_dark)
    flipped[rim.name] = check_torus_winding_xy(rim, 0.138, (0, 0, 0.40))
    parts.append(rim)

    # --- belly band, z 0.27 (belly radius 0.160) ---
    band = torus_xy("BellyBand", (0, 0, 0.27), 0.160, 0.008, 24, 6,
                    iron_dark)
    flipped[band.name] = check_torus_winding_xy(band, 0.160, (0, 0, 0.27))
    parts.append(band)

    # --- potion surface: disc just below the rim, z 0.385 ---
    # v1 put it at z 0.375: with the auto-fit camera below rim height
    # the sightline never dropped to the disc, so it was invisible.
    liquid = tapered_cyl_z("Potion", 0.382, 0.385, 0.132, 0.132, 24,
                           potion)
    parts.append(liquid)

    # --- bubbles: small spheres half-submerged in the potion ---
    bubble_specs = [
        ((0.045, 0.030), 0.018), ((-0.055, 0.045), 0.014),
        ((-0.020, -0.060), 0.016), ((0.070, -0.045), 0.012),
        ((0.005, 0.075), 0.011),
    ]
    for i, ((bx, by), br) in enumerate(bubble_specs):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10, ring_count=5, radius=br,
            location=(bx, by, 0.385))
        bub = bpy.context.active_object
        bub.name = "Bubble_%d" % (i + 1)
        bub.data.materials.append(bubble_mat)
        flat_shade(bub)
        parts.append(bub)

    # --- loop handles: vertical rings on +/-X sides, z 0.33 ---
    # Built directly in the YZ plane (torus_yz); v1 rotated a flat
    # torus about the world origin and displaced both handles.
    for i, sx in enumerate((-1, 1)):
        h = torus_yz("Handle_%d" % (i + 1), (sx * 0.155, 0, 0.33),
                     0.035, 0.008, 16, 6, iron_dark)
        flipped[h.name] = check_torus_winding_yz(
            h, 0.035, (sx * 0.155, 0, 0.33))
        parts.append(h)

    # --- three splayed legs: from the pot foot out to the ground ---
    # leg tops attach at r 0.10, z 0.15; feet at r 0.20, z 0.0
    # angles 90 (back), 210, 330 deg -> front view shows two legs
    for i, adeg in enumerate((90, 210, 330)):
        a = math.radians(adeg)
        top = (0.10 * math.cos(a), 0.10 * math.sin(a), 0.16)
        foot = (0.20 * math.cos(a), 0.20 * math.sin(a), 0.0)
        leg = cyl_between("Leg_%d" % (i + 1), top, foot, 0.018, 8, iron)
        parts.append(leg)
        # small foot pad
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10, ring_count=5, radius=0.022,
            location=(foot[0], foot[1], 0.012))
        pad = bpy.context.active_object
        pad.name = "FootPad_%d" % (i + 1)
        pad.data.materials.append(iron_dark)
        flat_shade(pad)
        parts.append(pad)

    # --- campfire: two crossed logs under the pot ---
    log1 = cyl_between("Log_1", (-0.13, -0.05, 0.025),
                       (0.13, 0.05, 0.025), 0.026, 8, wood_dark)
    parts.append(log1)
    log2 = cyl_between("Log_2", (-0.13, 0.05, 0.025),
                       (0.13, -0.05, 0.025), 0.026, 8, wood_dark)
    parts.append(log2)

    # --- flames: three tapered cones + one bright core ---
    flame_specs = [
        ((0.0, 0.0), 0.045, 0.17, flame),
        ((-0.05, 0.03), 0.035, 0.13, flame),
        ((0.05, -0.03), 0.035, 0.12, flame),
    ]
    for i, ((fx, fy), fr, fh, fmat) in enumerate(flame_specs):
        fl = tapered_cyl_z("Flame_%d" % (i + 1), 0.03, 0.03 + fh,
                           fr, 0.001, 8, fmat)
        fl.location = (fx, fy, 0)
        parts.append(fl)
    core = tapered_cyl_z("FlameCore", 0.03, 0.12, 0.028, 0.001, 8,
                         flame_core)
    parts.append(core)

    # --- stir stick resting across the rim ---
    stick = cyl_between("StirStick", (-0.17, 0.04, 0.415),
                        (0.17, -0.03, 0.405), 0.011, 8, wood)
    parts.append(stick)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    for o in parts:
        if o.type == 'MESH' and o.name not in flipped:
            flipped[o.name] = check_winding(o)
    print("CAULDRON_WINDING:", flipped)

    # Steeper elevation than the usual 0.32: the camera must look down
    # into the pot mouth so the potion surface is visible.
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.45),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "055-lowpoly-cauldron.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "055-lowpoly-cauldron.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "cauldron_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("CAULDRON_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CAULDRON_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "055-lowpoly-cauldron.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 055 低模游戏道具：炼金坩埚\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "铸铁坩埚置于三脚支架上，锅底燃着小篝火，锅内是发光的绿色"
                "药水与气泡，木质搅拌棒横搁在锅沿上。接 047 炼金实验室场景"
                "的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 锅身（Pot）：车削轮廓（lathe），7 个断面，24 段，"
                "z 0.14–0.40，最大腹径 r 0.160（z 0.27），底面扇形封口，"
                "铸铁\n")
        f.write("- 锅沿（Rim）：暗铁圆环，z 0.40，R 0.138，管 r 0.009\n")
        f.write("- 腹箍（BellyBand）：暗铁圆环，z 0.27，R 0.160，"
                "管 r 0.008\n")
        f.write("- 药水面（Potion）：圆盘，z 0.382–0.385，r 0.132，"
                "绿色自发光（Emission 0.8，混合 70%）\n")
        f.write("- 气泡（Bubble_1–5）：小球，r 0.011–0.018，半浸在药水面"
                "上，亮绿自发光（混合 60%）\n")
        f.write("- 提环（Handle_1–2）：竖直圆环（torus_yz 直接在 YZ 平面"
                "生成），R 0.035，管 r 0.008，"
                "中心 (±0.155, 0, 0.33)，暗铁，半嵌锅壁\n")
        f.write("- 支腿（Leg_1–3）：斜撑铁柱，r 0.018，8 段，从锅底"
                "（r 0.10，z 0.16）外张至地面（r 0.20，z 0），"
                "方位 90°/210°/330°，正面可见两腿\n")
        f.write("- 足垫（FootPad_1–3）：暗铁扁球，r 0.022，"
                "z 0.012，位于三腿落地点\n")
        f.write("- 篝火木柴（Log_1–2）：深木圆柱，r 0.026，长 0.30，"
                "交叉平放于锅底地面，z 0.025\n")
        f.write("- 火焰（Flame_1–3）：锥形，底 r 0.035–0.045，"
                "高 0.12–0.17，橙色自发光；焰心（FlameCore）亮黄，"
                "底 r 0.028，高 0.09\n")
        f.write("- 搅拌棒（StirStick）：木质圆柱，r 0.011，长约 0.34，"
                "横搁锅沿，z 约 0.41\n")
        f.write("- 整体约 0.55 m 宽（提环外缘）× 0.42 m 高\n\n")
        f.write("## v1 修正（目视检查发现两处问题后重渲）\n\n")
        f.write("- 提环错位：v1 用 torus_xy 建平环再 rotation_euler 绕世界"
                "原点旋转，两只提环被甩到 x 0.33 处，一只沉到地面以下；"
                "改 torus_yz 直接在 YZ 平面生成，绕向自检随之归零\n")
        f.write("- 药水面不可见：v1 药水面 z 0.375 且相机俯角小，视线越过"
                "近侧锅沿后始终高于药水面；药水面抬至 z 0.385，相机方向"
                "改为 (0, -1, 0.45)，自发光混合比提至 70%（火焰同）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("圆环类部件用环中心线检测（平环用 XY 版，竖环用 YZ 版）；"
                "其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Cauldron_Iron：锅身铸铁（metallic 0.7，roughness 0.55）\n")
        f.write("- Cauldron_IronDark：锅沿/腹箍/提环/足垫暗铁"
                "（metallic 0.65，roughness 0.6）\n")
        f.write("- Cauldron_Wood：搅拌棒木色（roughness 0.8）\n")
        f.write("- Cauldron_WoodDark：篝火木柴深木色（roughness 0.85）\n")
        f.write("- Cauldron_Potion：药水面亮绿自发光（Emission 0.8，"
                "混合 70%）\n")
        f.write("- Cauldron_Bubble：气泡亮绿自发光（Emission 0.6，"
                "混合 60%）\n")
        f.write("- Cauldron_Flame：火焰橙色自发光（Emission 1.2，"
                "混合 70%）\n")
        f.write("- Cauldron_FlameCore：焰心亮黄自发光（Emission 1.4，"
                "混合 70%）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.45)：俯角更大以便看到锅内药水面）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
