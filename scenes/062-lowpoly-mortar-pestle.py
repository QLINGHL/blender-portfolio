# -*- coding: utf-8 -*-
"""062 低模游戏道具：炼金研钵与杵（Alchemy Mortar and Pestle）
Low-poly game alchemy mortar and pestle: a stone mortar bowl (one
continuous lathe profile: outside wall up, over the rim, inside wall
down), a wooden pestle leaning at 38 degrees with its bulb resting in
the bowl, ground herb fragments + a powder mound inside the bowl, and
a small pile of dried herbs (stems + leaves) lying beside it on the
ground. Game-asset standard, flat shading.
Overall ~0.58 m wide x ~0.25 m tall x ~0.32 m deep.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 062-lowpoly-mortar-pestle.py
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


def lathe_z(name, profile, sides, mat, z_base=0.0, cap_bottom=True):
    """Surface of revolution around Z from a bottom-to-top profile of
    (radius, z) points (z relative to z_base). The profile is one
    continuous path, so it may run up the outside, over a rim and
    down the inside (bowl): the quad winding (k*i, k*j, (k+1)*j,
    (k+1)*i) keeps the normal on the solid's outside all along the
    path (verified: bottom -> -Z, outer wall -> +r, inner wall -> -r,
    rim top -> +Z). Optional fan cap at the bottom."""
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
    """Centroid check: count faces whose normal points inward (dot with
    the vector from the mesh centroid to the face center is negative).
    Valid for convex parts only; concave parts (bowl interior) are
    checked with check_lathe_winding instead."""
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
    """Winding check for a lathe mesh, in local space. For profile
    segment k from (r0, z0) to (r1, z1) the correct outward normal in
    the r-z plane is (dz, -dr) / |(dz, -dr)|, i.e. at face angle theta
    the expected normal is (n_r*cos t, n_r*sin t, n_z). Faces are
    stored segment-major (face index // sides == segment k); the
    bottom cap fan (if any) is skipped. Faces near the axis (r < 0.005)
    are skipped (degenerate slivers)."""
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


def herb_chunk(name, center, radius, scale_z, rot_z, mat):
    """One ground-herb fragment: a flat icosphere (subdiv 0, 20 tris),
    squashed in Z and rotated, sitting on the bowl floor."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=0, radius=radius,
                                          location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    obj.scale = (1.0, 1.0, scale_z)
    obj.rotation_euler = (0.0, 0.0, rot_z)
    flat_shade(obj)
    return obj


# Mortar profile (radius, z): bottom center -> foot -> outer belly ->
# rim -> inner wall -> inner bottom center. Outer radius 0.158,
# height 0.112, inner cavity radius 0.132, inner floor z 0.038.
MORTAR_PROFILE = [
    (0.001, 0.000), (0.100, 0.000), (0.115, 0.008), (0.130, 0.018),
    (0.150, 0.045), (0.158, 0.075), (0.150, 0.100), (0.145, 0.110),
    (0.138, 0.112), (0.132, 0.108), (0.128, 0.095), (0.120, 0.070),
    (0.100, 0.050), (0.060, 0.040), (0.001, 0.038),
]

# Pestle profile (radius, local z): bulb bottom -> bulb -> neck ->
# shaft -> handle swell -> rounded top. Length 0.255.
PESTLE_PROFILE = [
    (0.001, 0.000), (0.020, 0.002), (0.032, 0.012), (0.034, 0.025),
    (0.028, 0.040), (0.020, 0.055), (0.016, 0.120), (0.014, 0.180),
    (0.016, 0.220), (0.012, 0.245), (0.001, 0.255),
]

# Powder mound profile (radius, z), base at the bowl floor. 064: base
# radii shrunk x0.7 (0.055 -> 0.0385) so the mound fits the far side
# clear of the pestle (063: min pestle clearance -0.0242 at full size);
# height unchanged (0.024).
MOUND_PROFILE = [
    (0.001, 0.000), (0.0385, 0.000), (0.0364, 0.005), (0.0224, 0.014),
    (0.0084, 0.021), (0.001, 0.024),
]


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0.1, 0, 0.13))

    stone = solid_material("Mortar_Stone", (0.30, 0.29, 0.28),
                           metallic=0.0, roughness=0.95)
    wood = solid_material("Pestle_Wood", (0.38, 0.26, 0.13),
                          metallic=0.0, roughness=0.8)
    herb_green = solid_material("Herb_Green", (0.20, 0.36, 0.12),
                                metallic=0.0, roughness=0.9)
    herb_light = solid_material("Herb_Light", (0.30, 0.48, 0.18),
                                metallic=0.0, roughness=0.9)
    powder = solid_material("Herb_Powder", (0.38, 0.52, 0.20),
                            metallic=0.0, roughness=1.0)
    stem_mat = solid_material("Herb_StemDry", (0.40, 0.35, 0.15),
                              metallic=0.0, roughness=0.95)
    leaf_mat = solid_material("Herb_LeafDry", (0.34, 0.30, 0.12),
                              metallic=0.0, roughness=0.95)

    parts = []

    # --- stone mortar: one continuous lathe, outside + rim + inside ---
    mortar = lathe_z("Mortar", MORTAR_PROFILE, 24, stone,
                     z_base=0.0, cap_bottom=True)
    parts.append(mortar)

    # --- wooden pestle: bulb bottom at the bowl floor, leaning 38 deg
    # toward +X (rotation about the object origin = bulb tip, so the
    # bulb stays put and the handle swings out over the rim). ---
    pestle = lathe_z("Pestle", PESTLE_PROFILE, 16, wood,
                     z_base=0.0, cap_bottom=True)
    pestle.location = (0.01, 0.01, 0.038)
    pestle.rotation_euler = (0.0, math.radians(38.0), 0.0)
    parts.append(pestle)

    # --- ground powder mound, off-center on the bowl floor, on the
    # far (+Y) side so it stays visible over the near rim. 064: moved
    # from (0.06, 0.03) to (0.0, 0.09) — centre 0.0804 from the pestle
    # axis (063: -0.0242 clearance at the old spot); the -X side the
    # 063 sheet suggested is already occupied by HerbChunk_2/3, so the
    # +Y far side is the free spot that still clears the pestle. ---
    mound = lathe_z("PowderMound", MOUND_PROFILE, 12, powder,
                    z_base=0.038, cap_bottom=True)
    mound.location = (0.0, 0.09, 0.0)
    parts.append(mound)

    # --- ground herb fragments scattered on the bowl floor, clear of
    # the pestle bulb (bulb occupies r < ~0.04 around (0.01, 0.01)).
    # 064 (063: chunks 1/2/3/6/7/8 buried in the sloped bowl wall,
    # visible height -0.020..0.003): each chunk is raised onto the
    # local floor — centre z = floor height at its radial distance +
    # half-height (scale_z * radius) - 0.002 bottom embed — so every
    # chunk sticks ~0.012-0.015 out of the slope. Chunk 5 (063:
    # -0.0059 into the pestle) also moves away from the pestle axis to
    # (0.100, -0.030); its raised top (z 0.070) still clears the near
    # rim on the (0,-1,0.60) sightline, so the y >= -0.01 rule no
    # longer binds it. ---
    chunks = [
        # (x, y, z, radius, scale_z, rot_z_deg, material)
        (0.075, 0.045, 0.0534, 0.019, 0.45, 20, herb_green),
        (-0.055, 0.060, 0.0517, 0.021, 0.40, 75, herb_light),
        (-0.085, 0.010, 0.0529, 0.017, 0.50, 140, herb_green),
        (-0.020, -0.005, 0.0451, 0.020, 0.42, 200, herb_light),
        (0.100, -0.030, 0.0610, 0.018, 0.48, 260, herb_green),
        (0.095, 0.015, 0.0542, 0.016, 0.45, 310, herb_light),
        (-0.045, 0.095, 0.0616, 0.017, 0.50, 45, herb_green),
        (0.100, 0.060, 0.0714, 0.015, 0.45, 170, herb_green),
    ]
    for i, (x, y, z, r, sz, rz, mat) in enumerate(chunks):
        parts.append(herb_chunk("HerbChunk_%d" % (i + 1), (x, y, z),
                                r, sz, math.radians(rz), mat))

    # --- dried herb pile beside the mortar: 5 stems fanned out from a
    # common base point + 6 dried leaves ---
    stem_base = (0.26, 0.02, 0.004)
    stem_dirs = [
        (0.95, 0.30, 0.05), (1.00, 0.05, 0.03), (0.90, -0.25, 0.06),
        (0.75, 0.55, 0.04), (0.85, -0.50, 0.05),
    ]
    for i, d in enumerate(stem_dirs):
        dv = Vector(d).normalized()
        p1 = (stem_base[0] + dv.x * 0.17, stem_base[1] + dv.y * 0.17,
              0.004 + dv.z * 0.17)
        parts.append(cyl_between("DryStem_%d" % (i + 1), stem_base, p1,
                                 0.004, 6, stem_mat))
    leaves = [
        # (x, y, z, rot_z_deg, tilt_deg)
        (0.33, 0.10, 0.006, 30, 8), (0.38, 0.02, 0.006, -40, 12),
        (0.36, -0.06, 0.006, 80, 6), (0.42, 0.08, 0.006, 10, 15),
        (0.30, -0.03, 0.006, 120, 10), (0.40, -0.04, 0.006, -70, 7),
    ]
    for i, (x, y, z, rz, tilt) in enumerate(leaves):
        leaf = box_local("DryLeaf_%d" % (i + 1),
                         (0.034, 0.014, 0.002), leaf_mat)
        leaf.location = (x, y, z)
        leaf.rotation_euler = (math.radians(tilt), 0.0,
                               math.radians(rz))
        parts.append(leaf)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    # Winding: lathe parts get the profile-segment check (authoritative
    # for concave bowls); convex parts get the centroid check.
    lathe_flipped = {
        "Mortar": check_lathe_winding(mortar, MORTAR_PROFILE, 24),
        "Pestle": check_lathe_winding(pestle, PESTLE_PROFILE, 16),
    }
    print("MORTAR_WINDING_LATHE:", lathe_flipped)
    flipped = {}
    for o in parts:
        if o.type == 'MESH' and o.name not in ("Mortar", "Pestle"):
            flipped[o.name] = check_winding(o)
    print("MORTAR_WINDING_CENTROID:", flipped)

    # Pestle clearance: bulb vs bowl floor / rim, handle tip vs rim.
    # Bulb tip sits on the inner floor (z 0.038); shaft crosses the rim
    # plane (z 0.112) well inside the inner radius (0.132).
    import bmesh
    pestle_dir = Vector((math.sin(math.radians(38.0)), 0.0,
                         math.cos(math.radians(38.0))))
    tip = Vector((0.01, 0.01, 0.038)) + pestle_dir * 0.255
    shaft_at_rim = Vector((0.01, 0.01, 0.038)) + pestle_dir * (
        (0.112 - 0.038) / pestle_dir.z)
    print("PESTLE_TIP: (%.3f, %.3f, %.3f) rim_cross=(%.3f, %.3f, %.3f) "
          "rim_cross_r=%.3f" % (tip.x, tip.y, tip.z, shaft_at_rim.x,
                                shaft_at_rim.y, shaft_at_rim.z,
                                math.hypot(shaft_at_rim.x,
                                           shaft_at_rim.y)))

    # Camera: higher elevation than the usual (0,-1,0.30) so the bowl
    # interior (powder + herb fragments) stays visible over the near
    # rim (v1 at 0.45 hid the powder mound and 4 of 8 fragments).
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.60),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 samples=64)

    render(os.path.join(ROOT, "renders",
                        "062-lowpoly-mortar-pestle.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "062-lowpoly-mortar-pestle.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "mortar_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("MORTAR_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("MORTAR_POLY %s=%d" % (name, c))
    # Overall size (excluding ground).
    import mathutils
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in parts:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    print("MORTAR_SIZE: %.3f x %.3f x %.3f m" % (
        maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z))

    note = os.path.join(ROOT, "scenes", "062-lowpoly-mortar-pestle.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 062 低模游戏道具：炼金研钵与杵\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "石质研钵（一条连续车削轮廓：外壁上行、过碗口、内壁下行，"
                "一次成型带壁厚），木质研杵 38° 斜靠在碗内、杵头落在碗底，"
                "碗内一撮研磨的草药碎 + 一小堆草药粉，旁边地上散着一小撮"
                "干草药（5 根草茎 + 6 片干叶）。接 047 炼金实验室场景的"
                "道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 研钵（Mortar）：车削轮廓 15 个断面、24 段；外径 0.158、"
                "高 0.112，内腔半径 0.132、内底 z 0.038；底面扇形封口\n")
        f.write("- 研杵（Pestle）：车削轮廓 11 个断面、16 段，长 0.255；"
                "杵头球径 0.034、柄径 0.014–0.016；绕自身原点（杵头底端）"
                "转 38°（绕 Y 轴），杵头落在碗底中心 (0.01, 0.01, 0.038)，"
                "柄端伸出碗口上方；柄在碗口平面（z 0.112）处 x 约 0.064，"
                "在内腔半径内，不碰碗口\n")
        f.write("- 草药粉堆（PowderMound）：车削小丘，6 个断面、12 段，"
                "底径 0.0385（064 缩小底盘 ×0.7）、高 0.024，落在碗底"
                " +Y 远侧 (0.0, 0.09, 0.038)，中心离杵轴 0.0804，"
                "避免被近侧碗口遮挡\n")
        f.write("- 草药碎（HerbChunk_1–8）：20 面扁平二十面体，压扁 0.4–"
                "0.5，半径 0.015–0.021，散在碗底、避开杵头；064 起每块按"
                "当地碗底面高抬高（中心 z = 当地碗底面高 + 碎块半高"
                " − 0.002），5 号移离杵轴到 (0.100, -0.030, 0.0610)\n")
        f.write("- 干草茎（DryStem_1–5）：两点圆柱，6 段，半径 0.004、"
                "长 0.17，从公共基点 (0.26, 0.02, 0.004) 扇形散开\n")
        f.write("- 干叶（DryLeaf_1–6）：扁平小盒 0.034×0.014×0.002，"
                "平放在干草茎周围，带 6–15° 倾角\n")
        f.write("- 整体约 0.58 m 宽 × 0.25 m 高 × 0.32 m 深\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("车削件（Mortar / Pestle）用轮廓段法线检查：每段轮廓的正确"
                "外法线为 (dz, -dr) 方向，逐面核对；其余凸形部件用质心法"
                "检查。质心法对凹形碗内壁会误报，故研钵不采用质心法。\n\n")
        for name, bad in lathe_flipped.items():
            f.write("- %s：轮廓段法线检查，内翻面 %d\n"
                    % (name, len(bad)))
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Mortar_Stone：研钵灰石（roughness 0.95）\n")
        f.write("- Pestle_Wood：研杵暖棕木（roughness 0.8）\n")
        f.write("- Herb_Green / Herb_Light：碗内草药碎深绿 / 浅绿"
                "（roughness 0.9）\n")
        f.write("- Herb_Powder：草药粉浅黄绿（roughness 1.0）\n")
        f.write("- Herb_StemDry / Herb_LeafDry：干草茎 / 干叶橄榄色"
                "（roughness 0.95）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.60)；俯角比常规 0.30 高，为看清碗内草药；"
                "v1 俯角 0.45 时粉堆与 4 块草药碎被近侧碗口挡住，已修："
                "俯角抬到 0.60，粉堆与草药碎移到碗底远侧）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
