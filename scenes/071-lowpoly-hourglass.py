# -*- coding: utf-8 -*-
"""071 低模游戏道具：炼金沙漏（Alchemy Hourglass）
Low-poly game alchemy hourglass: a double-bulb glass timer between two
wooden end boards, held by 4 brass corner pillars and 2 brass equator
rings; the lower bulb holds a sand mound hugging the glass bottom, the
upper bulb holds a sand cone at the 35-degree angle of repose draining
through the neck, with a thin falling sand stream and a brass knob on
the top board.
Game-asset standard, flat shading.
Overall ~0.34 m wide x ~0.48 m tall x ~0.26 m deep.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 071-lowpoly-hourglass.py
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


def cylinder_between(name, p0, p1, r, sides, mat):
    """Straight tube (with end caps) between two points."""
    p0 = Vector(p0)
    p1 = Vector(p1)
    d = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u)
    verts = []
    for p in (p0, p1):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append(tuple(p + r * (math.cos(ang) * u
                                        + math.sin(ang) * v)))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append(tuple(p0))
    c1 = len(verts)
    verts.append(tuple(p1))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def make_glass(name, color, alpha=0.35):
    """Stylized glass: Principled BSDF with alpha + dithered
    transparency, so the sand inside stays visible (059)."""
    mat = solid_material(name, color, metallic=0.0, roughness=0.15)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = alpha
    mat.surface_render_method = 'DITHERED'
    return mat


def glow_material(name, color, strength=0.7, mix_fac=0.55, roughness=0.35):
    """Principled base color + an Emission node mixed in, for glowing
    potion liquid / warm sand."""
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


# --- dimensions (metres) ---
# Glass hourglass profile (radius, z), bottom to top, 15 points, 24 sides.
# Neck r 0.009 at z 0.22; the upper bulb flares sharply above the neck
# (dr/dz 3.0 at the waist) so a 35-degree repose cone from the neck can
# open up inside the glass instead of exiting the wall at once.
GLASS_PROFILE = [
    (0.001, 0.020), (0.055, 0.025), (0.085, 0.050), (0.095, 0.090),
    (0.092, 0.130), (0.075, 0.160), (0.045, 0.185), (0.009, 0.220),
    (0.045, 0.232), (0.075, 0.255), (0.092, 0.300), (0.095, 0.350),
    (0.085, 0.390), (0.055, 0.415), (0.001, 0.420),
]
# Lower sand mound: underside hugs the glass bottom curve, then a cone
# up to a peak at z 0.072 (35-degree repose from the base edge).
LOWER_SAND_PROFILE = [
    (0.001, 0.021), (0.040, 0.024), (0.060, 0.032), (0.075, 0.045),
    (0.055, 0.052), (0.035, 0.062), (0.015, 0.069), (0.001, 0.072),
]
NECK_Z = 0.22
NECK_R = 0.009
REPOSE_TAN = math.tan(math.radians(35.0))  # dz/dr of the sand surface
STREAM_R = 0.0035
# 073 修复：原 0.219 高出沙锥面 0.0022（沙锥面在流半径 0.0035 处
# z 0.2168，沙锥顶点 z 0.2151）。降到 0.2145 后整块顶盖落在沙锥体内。
STREAM_TOP_Z = 0.2145
STREAM_BOT_Z = 0.073
RING_Z_LOW = 0.09
RING_Z_HIGH = 0.35
RING_R = 0.097
RING_TUBE = 0.006
GLASS_MAX_R = 0.095


def glass_radius_at(z):
    """Linear interpolation of the glass radius at height z."""
    prof = GLASS_PROFILE
    if z <= prof[0][1]:
        return prof[0][0]
    for i in range(len(prof) - 1):
        r0, z0 = prof[i]
        r1, z1 = prof[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0) if z1 > z0 else 0.0
            return r0 + (r1 - r0) * t
    return prof[-1][0]


def upper_sand_profile():
    """Sand cone in the upper bulb: free surface at the 35-degree angle
    of repose, apex at the neck (r 0.008, z 0.22), rising outward until
    it meets the glass wall. Each sampled point is verified against the
    glass radius; the cone stops (clamped to glass_r - 0.002) where it
    would exit the glass. Returns (profile, edge_r, edge_z, min_clear).
    """
    profile = [(0.001, NECK_Z - 0.0049)]  # apex, just inside the neck
    min_clear = 1e9
    edge_r, edge_z = None, None
    for r in (0.02, 0.035, 0.05, 0.065, 0.078, 0.09):
        z = NECK_Z + REPOSE_TAN * (r - 0.008)
        clear = glass_radius_at(z) - r
        if clear < 0.002:
            # Cone would exit the glass here: clamp to the wall and stop.
            r_clamped = glass_radius_at(z) - 0.002
            profile.append((r_clamped, z))
            edge_r, edge_z = r_clamped, z
            min_clear = min(min_clear, 0.002)
            break
        profile.append((r, z))
        min_clear = min(min_clear, clear)
        edge_r, edge_z = r, z
    return profile, edge_r, edge_z, min_clear


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.24))

    wood = solid_material("Board_Wood", (0.32, 0.22, 0.12),
                          metallic=0.0, roughness=0.8)
    brass = solid_material("Frame_Brass", (0.55, 0.40, 0.15),
                           metallic=0.7, roughness=0.35)
    glass = make_glass("Glass_Clear", (0.80, 0.85, 0.88), alpha=0.35)
    sand = glow_material("Sand_Warm", (0.85, 0.72, 0.45),
                         strength=0.25, mix_fac=0.2, roughness=0.9)

    upper_prof, edge_r, edge_z, upper_min_clear = upper_sand_profile()
    print("HOURGLASS_UPPER_SAND: edge_r=%.4f edge_z=%.4f "
          "min_clearance=%.4f profile=%s"
          % (edge_r, edge_z, upper_min_clear, upper_prof))
    # 073 更正：上面 min_clearance 只在采样环半径处验算（贴壁边沿
    # 0.0020），不是全曲面最小值。沿实际轮廓段逐点采样：沙锥面穿过
    # 颈部平面 z 0.22 时离玻璃壁仅 0.001（072 质检单 §6 实测）。
    upper_min_true = 1e9
    upper_min_true_z = None
    for k in range(len(upper_prof) - 1):
        r0, z0 = upper_prof[k]
        r1, z1 = upper_prof[k + 1]
        for i in range(101):
            t = i / 100.0
            r = r0 + t * (r1 - r0)
            z = z0 + t * (z1 - z0)
            c = glass_radius_at(z) - r
            if c < upper_min_true:
                upper_min_true, upper_min_true_z = c, z
    print("HOURGLASS_UPPER_SAND_TRUE_MIN: min_clearance=%.4f at z=%.4f"
          % (upper_min_true, upper_min_true_z))
    lower_clears = [glass_radius_at(z) - r
                    for r, z in LOWER_SAND_PROFILE]
    print("HOURGLASS_LOWER_SAND: min_clearance=%.4f clears=%s"
          % (min(lower_clears),
             ["%.4f" % c for c in lower_clears]))

    parts = []

    # --- wooden end boards ---
    board_b = box_local("BoardBottom", (0.34, 0.26, 0.02), wood)
    board_b.location = (0, 0, 0.01)
    parts.append(board_b)
    board_t = box_local("BoardTop", (0.34, 0.26, 0.02), wood)
    board_t.location = (0, 0, 0.43)
    parts.append(board_t)

    # --- glass hourglass ---
    hourglass = lathe_z("HourglassGlass", GLASS_PROFILE, 24, glass,
                        z_base=0.0, cap_bottom=True)
    parts.append(hourglass)

    # --- lower sand mound ---
    lower_sand = lathe_z("SandLower", LOWER_SAND_PROFILE, 24, sand,
                         z_base=0.0, cap_bottom=True)
    parts.append(lower_sand)

    # --- upper sand cone (35-degree repose) ---
    upper_sand = lathe_z("SandUpper", upper_prof, 24, sand,
                         z_base=0.0, cap_bottom=True)
    parts.append(upper_sand)

    # --- falling sand stream through the neck ---
    stream = cylinder_between("SandStream", (0, 0, STREAM_TOP_Z),
                              (0, 0, STREAM_BOT_Z), STREAM_R, 8, sand)
    parts.append(stream)

    # --- brass equator rings around the glass ---
    ring_low = torus_xy("RingLower", (0, 0, RING_Z_LOW), RING_R,
                        RING_TUBE, 24, 6, brass)
    parts.append(ring_low)
    ring_high = torus_xy("RingUpper", (0, 0, RING_Z_HIGH), RING_R,
                         RING_TUBE, 24, 6, brass)
    parts.append(ring_high)

    # --- 4 brass corner pillars ---
    for i, (px, py) in enumerate(((0.14, 0.10), (-0.14, 0.10),
                                  (0.14, -0.10), (-0.14, -0.10))):
        pillar = tapered_cyl_z("Pillar_%d" % i, 0.02, 0.42,
                               0.012, 0.012, 12, brass)
        pillar.location = (px, py, 0)
        parts.append(pillar)

    # --- brass knob on the top board ---
    knob_base = tapered_cyl_z("KnobBase", 0.44, 0.465, 0.020, 0.008,
                              12, brass)
    parts.append(knob_base)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                                         radius=0.011,
                                         location=(0, 0, 0.47))
    knob_top = bpy.context.active_object
    knob_top.name = "KnobTop"
    knob_top.data.materials.append(brass)
    flat_shade(knob_top)
    parts.append(knob_top)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    # Winding checks.
    lathe_flipped = {
        "HourglassGlass": check_lathe_winding(hourglass, GLASS_PROFILE,
                                              24),
        "SandLower": check_lathe_winding(lower_sand,
                                         LOWER_SAND_PROFILE, 24),
        "SandUpper": check_lathe_winding(upper_sand, upper_prof, 24),
    }
    print("HOURGLASS_WINDING_LATHE:", {k: len(v)
                                       for k, v in lathe_flipped.items()})
    torus_flipped = {
        "RingLower": check_torus_winding_xy(ring_low, RING_R,
                                            (0, 0, RING_Z_LOW)),
        "RingUpper": check_torus_winding_xy(ring_high, RING_R,
                                            (0, 0, RING_Z_HIGH)),
    }
    print("HOURGLASS_WINDING_TORUS:", torus_flipped)
    flipped = {}
    for o in parts:
        if o.type == 'MESH' and o.name not in (
                "HourglassGlass", "SandLower", "SandUpper",
                "RingLower", "RingUpper"):
            flipped[o.name] = check_winding(o)
    print("HOURGLASS_WINDING_CENTROID:", flipped)

    # Measured clearances (no invented numbers):
    # 1. ring inner radius vs glass radius at the equator (design wedge)
    print("HOURGLASS_GAP ring_inner=%.4f glass_r=%.4f embed=%.4f"
          % (RING_R - RING_TUBE, GLASS_MAX_R,
             GLASS_MAX_R - (RING_R - RING_TUBE)))
    # 2. pillar inner edge vs glass max radius
    pillar_inner = math.hypot(0.14, 0.10) - 0.012
    print("HOURGLASS_GAP pillar_inner=%.4f glass_max_r=%.4f "
          "clearance=%.4f" % (pillar_inner, GLASS_MAX_R,
                              pillar_inner - GLASS_MAX_R))
    # 3. stream top vs neck plane / stream bottom vs mound peak
    print("HOURGLASS_GAP stream_top_z=%.3f neck_z=%.3f overlap=%.3f"
          % (STREAM_TOP_Z, NECK_Z, NECK_Z - STREAM_TOP_Z))
    cone_z_at_stream = NECK_Z + REPOSE_TAN * (STREAM_R - 0.008)
    print("HOURGLASS_GAP stream_top_z=%.4f cone_surface_at_stream_r="
          "%.4f buried=%.4f"
          % (STREAM_TOP_Z, cone_z_at_stream,
             cone_z_at_stream - STREAM_TOP_Z))
    print("HOURGLASS_GAP stream_bot_z=%.3f mound_peak_z=0.072 "
          "gap=%.3f" % (STREAM_BOT_Z, STREAM_BOT_Z - 0.072))
    # 4. glass bottom/top vs boards (touching by design)
    print("HOURGLASS_GAP glass_bottom_z=0.020 board_top_z=0.020 "
          "gap=0.000")
    print("HOURGLASS_GAP glass_top_z=0.420 board_bot_z=0.420 gap=0.000")
    # 5. knob base vs top board top
    print("HOURGLASS_GAP knob_base_z=0.440 board_top_z=0.440 gap=0.000")
    # 6. upper sand cone edge vs glass wall (script-verified above)
    print("HOURGLASS_GAP upper_sand_edge r=%.4f z=%.4f min_clear=%.4f"
          % (edge_r, edge_z, upper_min_clear))
    # 7. lower sand mound vs glass wall (script-verified above)
    print("HOURGLASS_GAP lower_sand min_clear=%.4f"
          % min(lower_clears))

    # Camera: auto-fit, target fill 78%.
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 samples=64)

    render(os.path.join(ROOT, "renders",
                        "071-lowpoly-hourglass.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "071-lowpoly-hourglass.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "hourglass_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("HOURGLASS_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("HOURGLASS_POLY %s=%d" % (name, c))
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in parts:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    print("HOURGLASS_SIZE: %.3f x %.3f x %.3f m" % (
        maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z))

    note = os.path.join(ROOT, "scenes", "071-lowpoly-hourglass.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 071 低模游戏道具：炼金沙漏\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "两块木质端板之间夹着双锥玻璃沙漏：4 根黄铜立柱撑住上下板，"
                "两枚黄铜箍环箍在玻璃最宽处；下瓶里是贴合玻璃底部的沙丘，"
                "上瓶里是 35° 安息角的沙锥正从颈部漏下，一道细沙流穿过颈"
                "部落在沙丘顶上；顶板中央一枚黄铜顶钮。接 047 炼金实验室"
                "场景的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 木质端板（BoardBottom / BoardTop）：0.34×0.26×0.02，"
                "下板 z 0–0.02、上板 z 0.42–0.44\n")
        f.write("- 玻璃沙漏（HourglassGlass）：车削轮廓 15 个断面、24 段；"
                "下瓶球半径 0.095（z 0.09）、颈半径 0.009（z 0.22）、上瓶"
                "球半径 0.095（z 0.35）；颈部上方喇叭口放宽（dr/dz 3.0），"
                "让 35° 沙锥能在玻璃内展开而不是一出颈就撞壁\n")
        f.write("- 下瓶沙丘（SandLower）：车削轮廓 8 个断面、24 段；底面"
                "贴合玻璃底部曲线（z 0.021–0.045），锥面以 35° 安息角收"
                "到峰顶 z 0.072\n")
        f.write("- 上瓶沙锥（SandUpper）：车削轮廓 %d 个断面、24 段；自由"
                "面按 35° 安息角从颈部（r 0.008，z 0.22）向外上升，逐点"
                "验算玻璃壁间隙，在 r %.4f、z %.4f 处贴到玻璃壁收住（间隙"
                " 0.002）\n" % (len(upper_prof), edge_r, edge_z))
        f.write("- 细沙流（SandStream）：两点直管半径 0.0035，z 0.2145–"
                "0.073，穿过颈部、上端埋进沙锥内（顶端低于沙锥面 0.0023）、"
                "下端落在沙丘顶上\n")
        f.write("- 黄铜箍环（RingLower / RingUpper）：R 0.097、管径 0.006，"
                "箍在玻璃最宽处 z 0.09 / z 0.35（内径 0.091，楔入玻璃 "
                "0.004，设计意图，同 067 卡箍）\n")
        f.write("- 黄铜立柱（Pillar_0–3）：半径 0.012，z 0.02–0.42，位于"
                " (±0.14, ±0.10) 四角，内沿离玻璃最宽处 0.065\n")
        f.write("- 黄铜顶钮（KnobBase / KnobTop）：锥台 r 0.020→0.008，"
                "z 0.44–0.465；球顶 r 0.011，球心 z 0.47\n")
        f.write("- 整体约 0.34 m 宽 × 0.48 m 高 × 0.26 m 深\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("车削件（HourglassGlass / SandLower / SandUpper）用轮廓段"
                "法线检查；圆环（RingLower / RingUpper）用环中心线法线检查；"
                "其余凸形部件用质心法检查。\n\n")
        for name, bad in lathe_flipped.items():
            f.write("- %s：轮廓段法线检查，内翻面 %d\n"
                    % (name, len(bad)))
        for name, n in torus_flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 实测间隙\n\n")
        f.write("- 箍环内径 0.091 − 玻璃半径 0.095 = 楔入 0.004（设计意图）\n")
        f.write("- 立柱内沿 0.160 − 玻璃最大半径 0.095 = 0.065\n")
        f.write("- 细沙流顶端 z 0.2145，沙锥自由面在流半径 0.0035 处 "
                "z 0.2168，顶端埋入沙锥内 0.0023（顶盖落在沙锥体内；073 "
                "修复，原 0.219 高出沙锥面 0.0022）\n")
        f.write("- 细沙流底端 z 0.073 − 沙丘峰顶 z 0.072 = 0.001\n")
        f.write("- 玻璃底 z 0.02 − 下板顶 z 0.02 = 0.000（贴合）\n")
        f.write("- 玻璃顶 z 0.42 − 上板底 z 0.42 = 0.000（贴合）\n")
        f.write("- 顶钮底 z 0.44 − 上板顶 z 0.44 = 0.000（贴合）\n")
        f.write("- 上瓶沙锥全曲面最小间隙 %.4f（颈部 z %.4f 处，沙锥面"
                "穿过颈部平面时离玻璃壁最近；073 更正，原笔记称最小间隙 "
                "0.0020 不实）；贴壁边沿间隙 %.4f（r %.4f、z %.4f）\n"
                % (upper_min_true, upper_min_true_z, upper_min_clear,
                   edge_r, edge_z))
        f.write("- 下瓶沙丘与玻璃壁最小间隙 %.4f\n"
                % min(lower_clears))
        f.write("\n## 材质\n\n")
        f.write("- Board_Wood：端板暖棕木（roughness 0.8）\n")
        f.write("- Frame_Brass：立柱 / 箍环 / 顶钮黄铜（metallic 0.7，"
                "roughness 0.35）\n")
        f.write("- Glass_Clear：沙漏无色玻璃（Alpha 0.35，dithered，"
                "roughness 0.15；059 同款做法，瓶内沙子可见）\n")
        f.write("- Sand_Warm：沙丘 / 沙锥 / 沙流暖沙色（Emission 0.25，"
                "混合 20%，roughness 0.9）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.35)）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
