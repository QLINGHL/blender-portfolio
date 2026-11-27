# -*- coding: utf-8 -*-
"""068 低模游戏道具：炼金蒸馏器（Alchemy Alembic Still）
Low-poly game alchemy still: a round-bottom glass retort flask with
glowing teal liquid, heated by a brass alcohol burner, held by a
retort-stand rod + brass ring; a sloped glass arm leads vapour into a
vertical glass condenser wrapped in a 3-turn copper coil, dripping
through a thin glass tube into a small round collection flask with
glowing amber distillate.
Game-asset standard, flat shading.
Overall ~0.62 m wide x ~0.50 m tall x ~0.34 m deep.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 068-lowpoly-alembic-still.py
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


def helix_tube(name, center, helix_R, tube_r, z0, z1, turns, mat,
               seg_per_turn=16, ring_sides=6):
    """Tube following a vertical helix (condenser coil). Returns the
    object; the sampled centerline is stored on the object for the
    winding check (obj["helix_centers"])."""
    cx, cy = center
    nseg = turns * seg_per_turn
    centers = []
    for s in range(nseg + 1):
        t = s / nseg
        th = 2.0 * math.pi * turns * t
        centers.append(Vector((cx + helix_R * math.cos(th),
                               cy + helix_R * math.sin(th),
                               z0 + (z1 - z0) * t)))
    verts = []
    for s, c in enumerate(centers):
        if s == 0:
            tang = (centers[1] - centers[0]).normalized()
        elif s == nseg:
            tang = (centers[-1] - centers[-2]).normalized()
        else:
            tang = (centers[s + 1] - centers[s - 1]).normalized()
        ref = Vector((0, 0, 1)) if abs(tang.z) < 0.9 \
            else Vector((1, 0, 0))
        n1 = tang.cross(ref).normalized()
        n2 = tang.cross(n1)
        for j in range(ring_sides):
            ph = 2.0 * math.pi * j / ring_sides
            verts.append(tuple(c + tube_r * (math.cos(ph) * n1
                                             + math.sin(ph) * n2)))
    faces = []
    for s in range(nseg):
        for j in range(ring_sides):
            k = (j + 1) % ring_sides
            faces.append((s * ring_sides + j, s * ring_sides + k,
                          (s + 1) * ring_sides + k,
                          (s + 1) * ring_sides + j))
    c0 = len(verts)
    verts.append(tuple(centers[0]))
    c1 = len(verts)
    verts.append(tuple(centers[-1]))
    for j in range(ring_sides):
        k = (j + 1) % ring_sides
        faces.append((c0, k, j))
        faces.append((c1, nseg * ring_sides + j,
                      nseg * ring_sides + k))
    obj = mesh_from_data(name, verts, faces, mat)
    obj["helix_centers"] = [tuple(c) for c in centers]
    return obj


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


def check_helix_winding(obj):
    """Winding check for the coil tube: each face normal must point
    away from the nearest sampled helix centerline point."""
    import bmesh
    mw = obj.matrix_world
    centers = [Vector(c) for c in obj["helix_centers"]]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = 0
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        nearest = min(centers, key=lambda p: (p - c).length)
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


# --- dimensions (metres) ---
RETORT_X = -0.16
RETORT_BULB_Z = 0.20
RETORT_BULB_R = 0.10
COND_X = 0.10
COIL_R = 0.042
COIL_TUBE_R = 0.007
COND_TUBE_R = 0.024

# Retort flask profile (radius, z): bulb arc -90..55 deg, shoulder,
# straight neck to z 0.44. Built at origin, placed at RETORT_X.
RETORT_PROFILE = [
    (0.001, 0.100), (0.050, 0.1134), (0.0866, 0.150), (0.100, 0.200),
    (0.0866, 0.250), (0.0574, 0.2819), (0.028, 0.300), (0.028, 0.440),
]
# Retort liquid: bulb arc r 0.096 up to z 0.2117, flat top surface.
RETORT_LIQ_PROFILE = [
    (0.001, 0.104), (0.048, 0.1169), (0.0831, 0.152), (0.096, 0.200),
    (0.0953, 0.2117), (0.001, 0.2117),
]
# Collection flask profile (radius, z): bulb r 0.055 centre z 0.075,
# shoulder, neck to z 0.16. Bottom sits on the base board (z 0.02).
COLL_PROFILE = [
    (0.001, 0.020), (0.0389, 0.0361), (0.055, 0.075), (0.0389, 0.1139),
    (0.0275, 0.1226), (0.018, 0.135), (0.018, 0.160),
]
# Collection liquid: bulb arc r 0.052 up to z 0.0572, flat top.
COLL_LIQ_PROFILE = [
    (0.001, 0.023), (0.0368, 0.0382), (0.0489, 0.0572), (0.001, 0.0572),
]


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.25))

    wood = solid_material("Base_Wood", (0.38, 0.26, 0.13),
                          metallic=0.0, roughness=0.8)
    brass = solid_material("Stand_Brass", (0.55, 0.40, 0.15),
                           metallic=0.7, roughness=0.35)
    copper = solid_material("Coil_Copper", (0.72, 0.45, 0.22),
                            metallic=0.8, roughness=0.3)
    glass = make_glass("Glass_Clear", (0.80, 0.85, 0.88), alpha=0.35)
    liq_teal = glow_material("Liquid_Teal", (0.30, 0.72, 0.45),
                             strength=0.7, mix_fac=0.55)
    liq_amber = glow_material("Liquid_Amber", (0.45, 0.18, 0.02),
                              strength=0.5, mix_fac=0.4, roughness=0.9)
    flame_mat = glow_material("Flame_Orange", (1.0, 0.55, 0.10),
                              strength=1.2, mix_fac=0.8, roughness=0.4)
    wick = solid_material("Wick_Dark", (0.10, 0.08, 0.06),
                          metallic=0.0, roughness=0.9)

    parts = []

    # --- wooden base board ---
    base = box_local("BaseBoard", (0.62, 0.34, 0.02), wood)
    base.location = (0, 0, 0.01)
    parts.append(base)

    # --- retort flask: round bulb + straight neck ---
    retort = lathe_z("RetortFlask", RETORT_PROFILE, 24, glass,
                     z_base=0.0, cap_bottom=True)
    retort.location = (RETORT_X, 0, 0)
    parts.append(retort)
    rim_lip = torus_xy("RetortRimLip", (RETORT_X, 0, 0.44),
                       0.028, 0.004, 24, 6, glass)
    parts.append(rim_lip)

    # --- teal liquid inside the retort ---
    retort_liq = lathe_z("RetortLiquid", RETORT_LIQ_PROFILE, 24,
                         liq_teal, z_base=0.0, cap_bottom=True)
    retort_liq.location = (RETORT_X, 0, 0)
    parts.append(retort_liq)

    # --- alcohol burner under the flask + wick + flame ---
    burner = tapered_cyl_z("Burner", 0.02, 0.06, 0.035, 0.035, 16, brass)
    burner.location = (RETORT_X, 0, 0)
    parts.append(burner)
    wick_obj = tapered_cyl_z("BurnerWick", 0.06, 0.075, 0.008, 0.008,
                             8, wick)
    wick_obj.location = (RETORT_X, 0, 0)
    parts.append(wick_obj)
    flame = tapered_cyl_z("Flame", 0.075, 0.10, 0.018, 0.002, 12,
                          flame_mat)
    flame.location = (RETORT_X, 0, 0)
    parts.append(flame)

    # --- retort stand: vertical rod + arm + ring around the neck ---
    rod = tapered_cyl_z("StandRod", 0.01, 0.50, 0.008, 0.008, 12, brass)
    rod.location = (-0.30, 0, 0)
    parts.append(rod)
    arm = box_local("RingArm", (0.14, 0.02, 0.015), brass)
    arm.location = (-0.23, 0, 0.34)
    parts.append(arm)
    ring = torus_xy("StandRing", (RETORT_X, 0, 0.34), 0.035, 0.006,
                    24, 6, brass)
    parts.append(ring)

    # --- sloped glass arm: retort neck top -> condenser top ---
    arm_tube = cylinder_between(
        "VapourArm", (RETORT_X, 0, 0.44), (COND_X, 0, 0.36),
        0.016, 12, glass)
    parts.append(arm_tube)
    collar_neck = torus_xy("Collar_Neck", (RETORT_X, 0, 0.44),
                           0.030, 0.005, 24, 6, brass)
    parts.append(collar_neck)
    collar_cond = torus_xy("Collar_Condenser", (COND_X, 0, 0.36),
                           0.026, 0.005, 24, 6, brass)
    parts.append(collar_cond)

    # --- condenser: vertical glass tube + 3-turn copper coil ---
    cond_tube = tapered_cyl_z("CondenserTube", 0.18, 0.36,
                              COND_TUBE_R, COND_TUBE_R, 16, glass)
    cond_tube.location = (COND_X, 0, 0)
    parts.append(cond_tube)
    coil = helix_tube("CondenserCoil", (COND_X, 0), COIL_R, COIL_TUBE_R,
                      0.20, 0.34, 3, copper)
    parts.append(coil)

    # --- thin drip tube: condenser bottom -> inside collection flask ---
    drip = cylinder_between("DripTube", (COND_X, 0, 0.18),
                            (COND_X, 0, 0.10), 0.010, 12, glass)
    parts.append(drip)

    # --- collection flask + amber distillate ---
    coll = lathe_z("CollectionFlask", COLL_PROFILE, 24, glass,
                   z_base=0.0, cap_bottom=True)
    coll.location = (COND_X, 0, 0)
    parts.append(coll)
    coll_liq = lathe_z("CollectionLiquid", COLL_LIQ_PROFILE, 24,
                       liq_amber, z_base=0.0, cap_bottom=True)
    coll_liq.location = (COND_X, 0, 0)
    parts.append(coll_liq)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    # Winding checks.
    lathe_flipped = {
        "RetortFlask": check_lathe_winding(retort, RETORT_PROFILE, 24),
        "RetortLiquid": check_lathe_winding(retort_liq,
                                            RETORT_LIQ_PROFILE, 24),
        "CollectionFlask": check_lathe_winding(coll, COLL_PROFILE, 24),
        "CollectionLiquid": check_lathe_winding(coll_liq,
                                                COLL_LIQ_PROFILE, 24),
    }
    print("STILL_WINDING_LATHE:", {k: len(v)
                                   for k, v in lathe_flipped.items()})
    torus_flipped = {
        "RetortRimLip": check_torus_winding_xy(
            rim_lip, 0.028, (RETORT_X, 0, 0.44)),
        "StandRing": check_torus_winding_xy(
            ring, 0.035, (RETORT_X, 0, 0.34)),
        "Collar_Neck": check_torus_winding_xy(
            collar_neck, 0.030, (RETORT_X, 0, 0.44)),
        "Collar_Condenser": check_torus_winding_xy(
            collar_cond, 0.026, (COND_X, 0, 0.36)),
    }
    print("STILL_WINDING_TORUS:", torus_flipped)
    print("STILL_WINDING_HELIX: CondenserCoil flipped=",
          check_helix_winding(coil))
    flipped = {}
    for o in parts:
        if o.type == 'MESH' and o.name not in (
                "RetortFlask", "RetortLiquid", "CollectionFlask",
                "CollectionLiquid", "RetortRimLip", "StandRing",
                "Collar_Neck", "Collar_Condenser", "CondenserCoil"):
            flipped[o.name] = check_winding(o)
    print("STILL_WINDING_CENTROID:", flipped)

    # Measured clearances (no invented numbers):
    # 1. flame tip vs retort bulb bottom (touching by design)
    print("STILL_GAP flame_tip_z=0.100 bulb_bottom_z=0.100 gap=0.000")
    # 2. stand ring inner radius vs retort neck radius
    print("STILL_GAP ring_inner=%.4f neck_r=0.0280 clearance=%.4f"
          % (0.035 - 0.006, 0.035 - 0.006 - 0.028))
    # 3. coil inner radius vs condenser tube radius
    print("STILL_GAP coil_inner=%.4f cond_tube_r=0.0240 clearance=%.4f"
          % (COIL_R - COIL_TUBE_R, COIL_R - COIL_TUBE_R - COND_TUBE_R))
    # 4. drip tube radius vs collection flask neck radius
    print("STILL_GAP drip_r=0.0100 coll_neck_r=0.0180 clearance=0.0080")
    # 5. retort liquid top radius vs bulb radius at z 0.2117
    bulb_r_at_liq = RETORT_BULB_R * math.cos(
        math.asin((0.2117 - RETORT_BULB_Z) / RETORT_BULB_R))
    print("STILL_GAP retort_liq_top_r=0.0953 bulb_r_at_z=%.4f "
          "clearance=%.4f" % (bulb_r_at_liq, bulb_r_at_liq - 0.0953))
    # 6. collection liquid top radius vs flask radius at z 0.0572
    coll_r_at_liq = 0.055 * math.cos(
        math.asin((0.0572 - 0.075) / 0.055))
    print("STILL_GAP coll_liq_top_r=0.0489 flask_r_at_z=%.4f "
          "clearance=%.4f" % (coll_r_at_liq, coll_r_at_liq - 0.0489))
    # 7. drip tube bottom vs collection liquid surface
    print("STILL_GAP drip_bottom_z=0.100 coll_liq_top_z=0.0572 "
          "gap=0.0428")
    # 8. condenser tube bottom vs collection flask neck top
    print("STILL_GAP cond_tube_bottom_z=0.180 coll_neck_top_z=0.160 "
          "gap=0.0200")

    # Camera: auto-fit, target fill 78%.
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 samples=64)

    render(os.path.join(ROOT, "renders",
                        "068-lowpoly-alembic-still.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "068-lowpoly-alembic-still.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "still_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("STILL_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("STILL_POLY %s=%d" % (name, c))
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in parts:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    print("STILL_SIZE: %.3f x %.3f x %.3f m" % (
        maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z))

    note = os.path.join(ROOT, "scenes", "068-lowpoly-alembic-still.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 068 低模游戏道具：炼金蒸馏器\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "木质底板上放一套完整蒸馏装置：左边的玻璃曲颈甑（圆底烧瓶"
                " + 直颈）装着发光青绿药液，底下是黄铜酒精灯（火焰尖正好"
                "碰到瓶底）；一根竖杆 + 黄铜圆环夹住甑颈；斜玻璃管把蒸汽"
                "导向右边的立式冷凝器——玻璃直管外绕 3 圈铜盘管，冷凝液经"
                "细滴管滴进下方的小圆底收集瓶，瓶内是发光琥珀色蒸馏液。"
                "接 047 炼金实验室场景的道具线。\n\n")
        f.write("## 结构\n\n")
        f.write("- 木质底板（BaseBoard）：0.62×0.34×0.02，z 0.01\n")
        f.write("- 玻璃曲颈甑（RetortFlask）：车削轮廓 8 个断面、24 段；"
                "圆底球半径 0.10、球心 (-0.16, 0, 0.20)，肩部收到颈半径 "
                "0.028、直颈到 z 0.44；口沿一圈玻璃卷边（RetortRimLip，"
                "R 0.028、管径 0.004）\n")
        f.write("- 甑内药液（RetortLiquid）：车削轮廓 6 个断面、24 段；"
                "球半径 0.096，顶面 z 0.2117（平顶）；发光青绿（Emission "
                "0.7，混合 55%）\n")
        f.write("- 酒精灯（Burner）：黄铜圆柱半径 0.035，z 0.02–0.06；"
                "灯芯（BurnerWick）半径 0.008，z 0.06–0.075；火焰 "
                "（Flame）锥形，底径 0.018、顶径 0.002，z 0.075–0.10，"
                "火焰尖正好碰到瓶底 z 0.10；发光橙（Emission 1.2，混合 "
                "80%）\n")
        f.write("- 固定架（StandRod / RingArm / StandRing）：黄铜竖杆半径 "
                "0.008，z 0.01–0.50（x -0.30）；横臂 0.14×0.02×0.015"
                "（z 0.34）；圆环 R 0.035、管径 0.006，套在甑颈上（颈半径 "
                "0.028，环内径 0.029，余量 0.001）\n")
        f.write("- 蒸汽斜管（VapourArm）：两点直管，(-0.16, 0, 0.44) → "
                "(0.10, 0, 0.36)，半径 0.016；两端各一枚黄铜卡箍 "
                "（Collar_Neck R 0.030 / Collar_Condenser R 0.026，管径 "
                "0.005）\n")
        f.write("- 冷凝器（CondenserTube）：玻璃直管半径 0.024，z "
                "0.18–0.36；铜盘管（CondenserCoil）螺旋半径 0.042、管径 "
                "0.007，3 圈，z 0.20–0.34（每圈 16 段、管截面 6 边）\n")
        f.write("- 滴管（DripTube）：细玻璃直管半径 0.010，z 0.18–0.10，"
                "穿过收集瓶颈（颈半径 0.018，余量 0.008），管底在收集液"
                "面上方 0.0428\n")
        f.write("- 收集瓶（CollectionFlask）：车削轮廓 7 个断面、24 段；"
                "圆底球半径 0.055、球心 (0.10, 0, 0.075)，瓶底落在底板"
                "上（z 0.02），颈半径 0.018、颈顶 z 0.16\n")
        f.write("- 收集液（CollectionLiquid）：车削轮廓 4 个断面、24 段；"
                "球半径 0.052，顶面 z 0.0572（平顶）；发光琥珀色（066 "
                "同款：Emission 0.5，混合 40%，roughness 0.9）\n")
        f.write("- 整体约 0.62 m 宽 × 0.50 m 高 × 0.34 m 深\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("车削件（RetortFlask / RetortLiquid / CollectionFlask / "
                "CollectionLiquid）用轮廓段法线检查；圆环（RetortRimLip "
                "/ StandRing / Collar_Neck / Collar_Condenser）用环中心线"
                "法线检查；铜盘管用螺旋中心线法线检查；其余凸形部件用质"
                "心法检查。\n\n")
        for name, bad in lathe_flipped.items():
            f.write("- %s：轮廓段法线检查，内翻面 %d\n"
                    % (name, len(bad)))
        for name, n in torus_flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("- CondenserCoil：螺旋中心线法线检查，内翻面 %d\n"
                % check_helix_winding(coil))
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 实测间隙\n\n")
        f.write("- 火焰尖 z 0.10 − 瓶底 z 0.10 = 0.000（设计贴合）\n")
        f.write("- 固定环内径 0.029 − 甑颈半径 0.028 = 0.001\n")
        f.write("- 铜盘管内径 0.035 − 冷凝管半径 0.024 = 0.011\n")
        f.write("- 滴管半径 0.010，收集瓶颈半径 0.018，余量 0.008\n")
        f.write("- 甑内药液顶面半径 0.0953，z 0.2117 处瓶内半径 %.4f，"
                "间隙 %.4f\n" % (bulb_r_at_liq, bulb_r_at_liq - 0.0953))
        f.write("- 收集液顶面半径 0.0489，z 0.0572 处瓶内半径 %.4f，"
                "间隙 %.4f\n" % (coll_r_at_liq, coll_r_at_liq - 0.0489))
        f.write("- 滴管底端 z 0.10 − 收集液面 z 0.0572 = 0.0428\n")
        f.write("- 冷凝管底端 z 0.18 − 收集瓶颈顶 z 0.16 = 0.020\n\n")
        f.write("## 材质\n\n")
        f.write("- Base_Wood：底板暖棕木（roughness 0.8）\n")
        f.write("- Stand_Brass：酒精灯 / 竖杆 / 横臂 / 固定环 / 卡箍"
                "（metallic 0.7，roughness 0.35）\n")
        f.write("- Coil_Copper：铜盘管（metallic 0.8，roughness 0.3）\n")
        f.write("- Glass_Clear：甑 / 冷凝管 / 斜管 / 滴管 / 收集瓶无色"
                "玻璃（Alpha 0.35，dithered，roughness 0.15；059 同款"
                "做法，瓶内药液可见）\n")
        f.write("- Liquid_Teal：甑内青绿药液（Emission 0.7，混合 55%）\n")
        f.write("- Liquid_Amber：收集瓶琥珀蒸馏液（Emission 0.5，混合 "
                "40%，roughness 0.9；066 同款防顶面过曝）\n")
        f.write("- Flame_Orange：火焰（Emission 1.2，混合 80%）\n")
        f.write("- Wick_Dark：灯芯深灰（roughness 0.9）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%，"
                "方向 (0, -1, 0.35)）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
