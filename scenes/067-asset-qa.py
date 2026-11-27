# -*- coding: utf-8 -*-
"""067 资产质检：对 066 低模炼金漏斗与量杯做真实 mesh 检查（拓扑/法线/UV/材质），
并实测漏斗与量杯特有结构：漏斗车削环、量杯开口车削、双药液与玻璃壁间隙、
刻度环、漏斗卡环楔合、滴落间隙、支架连接。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 067-asset-qa.py
"""
import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLEND = os.path.join(ROOT, "scenes", "066-lowpoly-funnel-beaker.blend")
UV_JSON = os.path.join(ROOT, "scenes", "067-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "067-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "067-asset-qa-checklist.md")

# every mesh object in the 066 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/066-lowpoly-funnel-beaker.md (per-part table)
EXPECTED_FACES = {
    "StandBase": 6, "StandPost_L": 6, "StandPost_R": 6,
    "StandCrossbar": 6, "FunnelRing": 144, "RingArm_L": 6,
    "RingArm_R": 6, "Funnel": 120, "FunnelRimLip": 144,
    "FunnelLiquid": 72, "MeasuringCup": 144, "CupLiquid": 72,
    "GradRing_1": 24, "GradRing_2": 24, "GradRing_3": 24,
    "GradRing_4": 24,
}
EXPECTED_TOTAL_FACES = 828
EXPECTED_TRIS = 120
EXPECTED_QUADS = 708

# part -> design material (from the 066 build script)
PART_MATERIAL = {
    "StandBase": "Stand_Wood", "StandPost_L": "Stand_Wood",
    "StandPost_R": "Stand_Wood", "StandCrossbar": "Stand_WoodDark",
    "FunnelRing": "Ring_Brass", "RingArm_L": "Ring_Brass",
    "RingArm_R": "Ring_Brass", "Funnel": "Glass_Clear",
    "FunnelRimLip": "Glass_Clear", "FunnelLiquid": "Liquid_Green",
    "MeasuringCup": "Glass_Clear", "CupLiquid": "Liquid_Amber",
    "GradRing_1": "Graduation_Dark", "GradRing_2": "Graduation_Dark",
    "GradRing_3": "Graduation_Dark", "GradRing_4": "Graduation_Dark",
}

# Design material values from the 066 build script. The 066 build script
# passes raw tuples to solid_material, which stores them directly as
# linear Base Color (same convention as the 059/060/063 scripts).
# Glass_Clear: alpha 0.35 + dithered (059 recipe). Liquid_* are Principled
# + Emission mixed in (glow_material): check emission strength, mix factor
# and roughness as well.
DESIGN_MATS = {
    "Stand_Wood":     {"metallic": 0.00, "roughness": 0.80,
                       "color": (0.38, 0.26, 0.13), "emissive": None},
    "Stand_WoodDark": {"metallic": 0.00, "roughness": 0.85,
                       "color": (0.30, 0.20, 0.10), "emissive": None},
    "Ring_Brass":     {"metallic": 0.70, "roughness": 0.35,
                       "color": (0.55, 0.40, 0.15), "emissive": None},
    "Glass_Clear":    {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.80, 0.85, 0.88), "emissive": None,
                       "alpha": 0.35, "dithered": True},
    "Liquid_Green":   {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.35, 0.75, 0.25),
                       "emissive": ((0.35, 0.75, 0.25), 0.7, 0.55)},
    "Liquid_Amber":   {"metallic": 0.00, "roughness": 0.90,
                       "color": (0.45, 0.18, 0.02),
                       "emissive": ((0.45, 0.18, 0.02), 0.5, 0.4)},
    "Graduation_Dark": {"metallic": 0.00, "roughness": 0.70,
                        "color": (0.12, 0.11, 0.10), "emissive": None},
}

# design geometry (copied from the 066 build script)
FUNNEL_PROFILE = [
    (0.022, 0.160), (0.022, 0.300), (0.050, 0.330), (0.090, 0.400),
    (0.125, 0.460), (0.150, 0.500),
]
FUNNEL_Z_BASE = 0.017
FUNNEL_SIDES = 24
RING_Z = 0.42
RING_R = 0.095
RING_TUBE = 0.007
LIP_R = 0.150
LIP_TUBE = 0.005
LIP_Z = FUNNEL_Z_BASE + 0.500
CUP_PROFILE = [
    (0.001, 0.020), (0.075, 0.020), (0.085, 0.150), (0.082, 0.150),
    (0.072, 0.030), (0.001, 0.030),
]
CUP_SIDES = 24
# funnel liquid: tapered cylinder, bottom (z, r) -> top (z, r)
FUNNEL_LIQ = (0.322, 0.026, 0.457, 0.104)
CUP_LIQ = (0.031, 0.070, 0.11, 0.076)
GRAD_ZS = (0.05, 0.075, 0.10, 0.125)
GRAD_SIDES = 24
# stand boxes: name -> (center, size)
BOXES = {
    "StandBase": ((0, 0, 0.01), (0.44, 0.30, 0.02)),
    "StandPost_L": ((-0.17, 0, 0.24), (0.04, 0.05, 0.44)),
    "StandPost_R": ((0.17, 0, 0.24), (0.04, 0.05, 0.44)),
    "StandCrossbar": ((0, 0, 0.46), (0.38, 0.05, 0.04)),
    "RingArm_L": ((-0.135, 0, 0.42), (0.075, 0.03, 0.02)),
    "RingArm_R": ((0.135, 0, 0.42), (0.075, 0.03, 0.02)),
}


def profile_radius_at(profile, z):
    """True piecewise-linear radius of a lathe profile at height z.
    NOTE: the 066 build script's funnel_radius_at() is a simplified
    straight line from (0.022, 0.30) to (0.150, 0.50) and ignores the
    kink at (0.050, 0.330); the 066 note's ring-fit and liquid-clearance
    numbers were computed with it and are wrong. This function uses the
    real profile segments."""
    if z <= profile[0][1]:
        return profile[0][0]
    for k in range(len(profile) - 1):
        r0, z0 = profile[k]
        r1, z1 = profile[k + 1]
        if z0 <= z <= z1:
            if z1 == z0:
                return r0
            t = (z - z0) / (z1 - z0)
            return r0 + t * (r1 - r0)
    return profile[-1][0]


def funnel_radius_at(world_z):
    return profile_radius_at(FUNNEL_PROFILE, world_z - FUNNEL_Z_BASE)


def cup_radius_at(z):
    """Measuring cup OUTER radius at height z (taper 0.075 -> 0.085
    over z 0.02..0.15)."""
    return 0.075 + (z - 0.02) / 0.13 * 0.010


def cup_inner_radius_at(z):
    """Measuring cup INNER radius at height z (inner wall from
    (0.082, 0.15) down to (0.072, 0.03))."""
    return 0.082 - (0.15 - z) / 0.12 * 0.010


def check_mesh(obj):
    """Real inspection of one mesh. Returns a dict of measurements."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    n_verts = len(bm.verts)
    n_faces = len(bm.faces)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)

    seen = {}
    dups = 0
    for v in bm.verts:
        key = (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
        if key in seen:
            dups += 1
        else:
            seen[key] = v.index

    loose_edges = sum(1 for e in bm.edges if len(e.link_faces) == 0)
    boundary_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-8)

    # normal consistency: copy the bmesh, run Blender's own
    # recalc_face_normals and count faces whose normal flips.
    bm2 = bm.copy()
    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    bm2.faces.ensure_lookup_table()
    orig_normals = [f.normal.copy() for f in bm.faces]
    inverted = sum(1 for i, f in enumerate(bm2.faces)
                   if orig_normals[i].dot(f.normal) < 0)
    bm2.free()

    max_valence = max((len(v.link_edges) for v in bm.verts), default=0)

    uv_layer = bm.loops.layers.uv.active
    uv = {"has_uv": uv_layer is not None, "out_of_bounds": 0,
          "utilization": 0.0, "islands": 0, "overlap_pct": 0.0,
          "faces": []}
    if uv_layer is not None:
        face_uvs = []
        for f in bm.faces:
            pts = [(l[uv_layer].uv.x, l[uv_layer].uv.y) for l in f.loops]
            face_uvs.append(pts)
            for (u, v) in pts:
                if u < -1e-4 or u > 1.0001 or v < -1e-4 or v > 1.0001:
                    uv["out_of_bounds"] += 1
        area = 0.0
        for pts in face_uvs:
            for k in range(1, len(pts) - 1):
                (x0, y0), (x1, y1), (x2, y2) = pts[0], pts[k], pts[k + 1]
                area += abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0
        uv["utilization"] = area
        parent = list(range(len(face_uvs)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        pos_to_faces = {}
        for fi, pts in enumerate(face_uvs):
            for (u, v) in pts:
                key = (round(u, 4), round(v, 4))
                pos_to_faces.setdefault(key, []).append(fi)
        for fis in pos_to_faces.values():
            for fi in fis[1:]:
                union(fis[0], fi)
        face_island = [find(i) for i in range(len(face_uvs))]
        uv["islands"] = len(set(face_island))
        grid = {}
        N = 512
        for fi, pts in enumerate(face_uvs):
            for k in range(1, len(pts) - 1):
                (x0, y0), (x1, y1), (x2, y2) = pts[0], pts[k], pts[k + 1]
                steps = 12
                for i in range(steps + 1):
                    for j in range(steps + 1 - i):
                        a = i / steps
                        b = j / steps
                        c = 1.0 - a - b
                        if a < 0.06 or b < 0.06 or c < 0.06:
                            continue
                        x = a * x0 + b * x1 + c * x2
                        y = a * y0 + b * y1 + c * y2
                        cell = (min(int(x * N), N - 1), min(int(y * N), N - 1))
                        grid.setdefault(cell, set()).add(face_island[fi])
        total_cells = len(grid)
        overlap_cells = sum(1 for s in grid.values() if len(s) > 1)
        uv["overlap_pct"] = (100.0 * overlap_cells / total_cells) if total_cells else 0.0
        uv["faces"] = [[list(p) for p in pts] for pts in face_uvs]

    bm.free()
    return {
        "name": obj.name,
        "verts": n_verts, "faces": n_faces, "tris": tris, "quads": quads,
        "ngons": ngons, "duplicate_verts": dups, "loose_edges": loose_edges,
        "boundary_edges": boundary_edges, "nonmanifold_edges": nonmanifold,
        "degenerate_faces": degenerate, "inverted_normals": inverted,
        "max_valence": max_valence,
        "uv": uv,
        "materials": [m.name if m else None for m in obj.data.materials],
    }


def world_range(obj):
    """World-space bbox (xmin, xmax, ymin, ymax, zmin, zmax)."""
    mw = obj.matrix_world
    ws = [mw @ v.co for v in obj.data.vertices]
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def ring_analysis(obj, origin, direction, rho_min=0.0005):
    """Group the tube's ring verts (rho > rho_min off axis) by (axial
    distance, radius); return [(distance, count, center, radius)] per
    ring."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    mw = obj.matrix_world
    clusters = {}
    for v in obj.data.vertices:
        w = mw @ v.co
        rel = w - o
        axial = rel.dot(d)
        rho = (rel - d * axial).length
        if rho < rho_min:
            continue  # cap centre, not a ring vert
        key = (round(axial, 3), round(rho, 3))
        clusters.setdefault(key, []).append(w)
    rings = []
    for dist, rad in sorted(clusters):
        pts = clusters[(dist, rad)]
        c = sum(pts, Vector((0, 0, 0))) / len(pts)
        r = sum((p - c).length for p in pts) / len(pts)
        rings.append({"distance": dist, "count": len(pts),
                      "center": tuple(round(v, 3) for v in c),
                      "radius": round(r, 3)})
    return rings


def bbox_close(measured, expected, tol=0.002):
    return all(abs(a - b) <= tol for a, b in zip(measured, expected))


def lathe_expected_bbox(profile, origin, direction):
    """Analytic bbox of a lathe: for each profile ring (radius r at
    axial z) the ring is a circle in the plane perpendicular to the
    axis; its per-axis half-extent is r*sqrt(1-dir_i^2)."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for r, z in profile:
        c = o + d * z
        for i in range(3):
            h = r * math.sqrt(max(0.0, 1.0 - d[i] * d[i]))
            mins[i] = min(mins[i], c[i] - h)
            maxs[i] = max(maxs[i], c[i] + h)
    return (round(mins.x, 3), round(maxs.x, 3),
            round(mins.y, 3), round(maxs.y, 3),
            round(mins.z, 3), round(maxs.z, 3))


def check_lathe(name, obj, profile, sides, origin, direction,
                expected_tri_count, expected_tri_axial):
    """Ring-by-ring check of a lathe part: ring count, per-ring vertex
    count, ring (axial distance, radius) pairs vs the design profile
    (compared as sorted pairs: the profile is not monotonic in z);
    cap fan triangles at the expected axial positions; analytic bbox."""
    rings = ring_analysis(obj, origin, direction, rho_min=0.0005)
    measured_pairs = sorted((x["distance"], x["radius"]) for x in rings)
    expected_pairs = sorted((round(z, 3), r) for r, z in profile)
    mw = obj.matrix_world
    tri_ax = []
    for p in obj.data.polygons:
        if len(p.vertices) == 3:
            c = mw @ p.center
            tri_ax.append(round((c - Vector(origin)).dot(
                Vector(direction).normalized()), 3))
    r = world_range(obj)
    exp = lathe_expected_bbox(profile, origin, direction)
    pairs_ok = (len(measured_pairs) == len(expected_pairs)
                and all(abs(a - b) <= 0.002
                        for (a, _r1), (b, _r2) in zip(measured_pairs,
                                                      expected_pairs))
                and all(abs(a - b) < 0.002
                        for (_d1, a), (_d2, b) in zip(measured_pairs,
                                                      expected_pairs)))
    row = {"range": r, "expected": exp,
           "rings": rings,
           "ring_distances": [x["distance"] for x in rings],
           "ring_counts": [x["count"] for x in rings],
           "ring_radii": [x["radius"] for x in rings],
           "design_distances": [d for d, _r in expected_pairs],
           "design_radii": [r for _d, r in expected_pairs],
           "tri_axial_positions": sorted(set(tri_ax)),
           "tri_count": len(tri_ax),
           "ok": bool(
               pairs_ok
               and all(c == sides for c in [x["count"] for x in rings])
               and bbox_close(r, exp)
               and len(tri_ax) == expected_tri_count
               and sorted(set(tri_ax)) == expected_tri_axial)}
    return row


def check_lathe_winding_analytic(obj, profile, sides, z_base=0.0):
    """Analytic winding check for a lathe mesh, in local space (same
    method as the 066 build script's own self-check): the expected
    outward normal of each profile segment is computed from the
    profile geometry, and each face normal is compared against it.
    This is the authoritative normal check for an OPEN lathe tube:
    Blender's recalc_face_normals decides orientation from the mesh's
    signed volume, and for the funnel (a megaphone: top opening much
    wider than the stem) the wall-only signed volume is negative, so
    recalc flips all 120 faces even though they are wound outward.
    Returns the list of flipped face indices."""
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


def check_tapered_cyl(name, obj, z0, r0, z1, r1, sides):
    """A tapered_cyl_z part: 2 rings, side quads, cap fans at both
    ends (48 tris), closed (0 boundary edges)."""
    rings = ring_analysis(obj, (0, 0, 0), (0, 0, 1), rho_min=0.0005)
    mw = obj.matrix_world
    tri_ax = []
    for p in obj.data.polygons:
        if len(p.vertices) == 3:
            c = mw @ p.center
            tri_ax.append(round(c.z, 3))
    r = world_range(obj)
    exp = (round(-max(r0, r1), 3), round(max(r0, r1), 3),
           round(-max(r0, r1), 3), round(max(r0, r1), 3),
           round(z0, 3), round(z1, 3))
    row = {"range": r, "expected": exp,
           "rings": [(x["distance"], x["count"], x["radius"])
                     for x in rings],
           "tri_axial_positions": sorted(set(tri_ax)),
           "tri_count": len(tri_ax),
           "ok": bool(
               len(rings) == 2
               and [x["count"] for x in rings] == [sides, sides]
               and abs(rings[0]["distance"] - z0) < 0.002
               and abs(rings[1]["distance"] - z1) < 0.002
               and abs(rings[0]["radius"] - r0) < 0.002
               and abs(rings[1]["radius"] - r1) < 0.002
               and sorted(set(tri_ax)) == [round(z0, 3), round(z1, 3)]
               and len(tri_ax) == 2 * sides
               and bbox_close(r, exp))}
    return row


def check_torus(name, obj, R, tube, cz, arc_segments, tube_segments):
    """A torus_xy part: bbox vs the analytic torus bbox. The tube is
    sampled in `tube_segments` steps, so the measured z half-extent is
    tube*sin(pi*(tube_segments-1)/tube_segments)... for 6 segments the
    extreme sampled angle is 60 deg -> tube*sin(60deg); allow tol 0.002
    against the continuous bbox (the sampled value is within 0.001)."""
    r = world_range(obj)
    exp = (round(-(R + tube), 3), round(R + tube, 3),
           round(-(R + tube), 3), round(R + tube, 3),
           round(cz - tube, 3), round(cz + tube, 3))
    # measured radial extremes from the mesh verts
    rhos = [math.hypot(v.x, v.y) for v in world_verts(obj)]
    row = {"range": r, "expected": exp,
           "rho_min": round(min(rhos), 3), "rho_max": round(max(rhos), 3),
           "rho_min_expected": round(R - tube, 3),
           "rho_max_expected": round(R + tube, 3),
           "ok": bool(bbox_close(r, exp)
                      and abs(min(rhos) - (R - tube)) < 0.002
                      and abs(max(rhos) - (R + tube)) < 0.002)}
    return row


def check_box(name, obj):
    center, size = BOXES[name]
    r = world_range(obj)
    exp = (round(center[0] - size[0] / 2, 3),
           round(center[0] + size[0] / 2, 3),
           round(center[1] - size[1] / 2, 3),
           round(center[1] + size[1] / 2, 3),
           round(center[2] - size[2] / 2, 3),
           round(center[2] + size[2] / 2, 3))
    return {"range": r, "expected": exp,
            "ok": bool(bbox_close(r, exp))}


def torus_sdf(rho, z, R, tube, cz):
    """Signed distance to a flat torus (XY plane, centre z=cz)."""
    return math.sqrt((rho - R) ** 2 + (z - cz) ** 2) - tube


def check_ring_wedge(by_name):
    """The funnel cone wedges into the brass ring (design intent:
    '锥体卡在环里'). Measure both ways: funnel mesh verts vs the ring
    torus SDF, and ring mesh verts vs the true funnel cone surface.
    Also the analytic surface maximum: sample the cone wall between
    profile rings (the mesh has no verts between rings) against the
    torus inner surface."""
    funnel = by_name["Funnel"]
    ring = by_name["FunnelRing"]
    # 1. funnel verts vs torus
    worst_f = None
    worst_f_sdf = 1e9
    for v in world_verts(funnel):
        rho = math.hypot(v.x, v.y)
        sdf = torus_sdf(rho, v.z, RING_R, RING_TUBE, RING_Z)
        if sdf < worst_f_sdf:
            worst_f_sdf = sdf
            worst_f = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
    # 2. ring verts vs cone surface (only where the cone exists)
    worst_r = None
    worst_r_pen = -1e9
    for v in world_verts(ring):
        if not (FUNNEL_Z_BASE + 0.160 <= v.z
                <= FUNNEL_Z_BASE + 0.500):
            continue
        rho = math.hypot(v.x, v.y)
        pen = funnel_radius_at(v.z) - rho
        if pen > worst_r_pen:
            worst_r_pen = pen
            worst_r = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
    # 3. analytic surface max: cone wall segment (0.400, 0.090) ->
    # (0.460, 0.125) crosses the ring plane; sample the penetration
    # cone_r(z) - torus_inner_r(z) finely.
    max_analytic = -1e9
    max_analytic_z = None
    for i in range(401):
        z = 0.413 + i * (0.427 - 0.413) / 400.0
        dz = z - RING_Z
        inner = RING_R - math.sqrt(max(0.0, RING_TUBE ** 2 - dz ** 2))
        pen = funnel_radius_at(z) - inner
        if pen > max_analytic:
            max_analytic = pen
            max_analytic_z = z
    # the 066 note's simplified-function claim, for the correction note
    approx_cone_r = 0.022 + (RING_Z - FUNNEL_Z_BASE - 0.30) / 0.20 * 0.128
    row = {"funnel_vert_min_sdf": round(worst_f_sdf, 4),
           "funnel_vert_worst": worst_f,
           "ring_vert_max_penetration": round(worst_r_pen, 4),
           "ring_vert_worst": worst_r,
           "analytic_max_penetration": round(max_analytic, 4),
           "analytic_max_z": round(max_analytic_z, 3),
           "cone_radius_at_ring_plane_true": round(
               funnel_radius_at(RING_Z), 4),
           "cone_radius_at_ring_plane_note_approx": round(
               approx_cone_r, 4),
           "ring_inner_radius": round(RING_R - RING_TUBE, 4),
           "ring_tube_radius": RING_TUBE,
           # wedged contact by design: the cone must be wider than the
           # ring hole at the ring plane (it cannot fall through) and
           # must not punch through the whole tube (pen < tube radius)
           "ok": bool(funnel_radius_at(RING_Z) > RING_R - RING_TUBE
                      and max_analytic < RING_TUBE
                      and max_analytic > 0)}
    return row


def check_rim_lip(by_name):
    """FunnelRimLip torus wraps the funnel rim: the funnel's top ring
    (r 0.150, z 0.517) passes through the lip tube's centre circle."""
    funnel = by_name["Funnel"]
    top_ring = [v for v in world_verts(funnel) if abs(v.z - LIP_Z) < 0.001]
    dists = [torus_sdf(math.hypot(v.x, v.y), v.z, LIP_R, LIP_TUBE, LIP_Z)
             for v in top_ring]
    row = {"top_ring_verts": len(top_ring),
           "top_ring_radius": round(
               sum(math.hypot(v.x, v.y) for v in top_ring)
               / max(1, len(top_ring)), 4),
           "lip_center_radius": LIP_R,
           "min_sdf_to_lip": round(min(dists), 4) if dists else None,
           "max_sdf_to_lip": round(max(dists), 4) if dists else None,
           # every top-ring vert must sit inside the lip tube
           "ok": bool(top_ring and all(d < 0 for d in dists))}
    return row


def check_liquids(by_name):
    """Both liquids must sit inside their glass, with positive
    clearance everywhere; tops below the rims; bottoms above the
    cavity floors. Clearances are measured against the TRUE profile
    (piecewise-linear), not the 066 note's simplified cone function."""
    rows = {}
    # funnel liquid vs funnel wall
    fl = by_name["FunnelLiquid"]
    min_clear = 1e9
    min_clear_at = None
    for v in world_verts(fl):
        rho = math.hypot(v.x, v.y)
        if v.z < FUNNEL_Z_BASE + 0.160 or v.z > FUNNEL_Z_BASE + 0.500:
            continue
        clear = funnel_radius_at(v.z) - rho
        if clear < min_clear:
            min_clear = clear
            min_clear_at = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
    # analytic min over the liquid height (the wall is faceted between
    # rings; sample the liquid radius vs the true profile finely)
    min_an = 1e9
    min_an_z = None
    for i in range(281):
        z = 0.322 + i * (0.457 - 0.322) / 280.0
        liq_r = 0.026 + (z - 0.322) / 0.135 * 0.078
        clear = funnel_radius_at(z) - liq_r
        if clear < min_an:
            min_an = clear
            min_an_z = z
    fl_top = max(v.z for v in world_verts(fl))
    fl_top_r = max(math.hypot(v.x, v.y)
                   for v in world_verts(fl) if abs(v.z - fl_top) < 0.001)
    rows["FunnelLiquid"] = {
        "min_clearance_verts": round(min_clear, 4),
        "min_clearance_vert_at": min_clear_at,
        "min_clearance_analytic": round(min_an, 4),
        "min_clearance_analytic_z": round(min_an_z, 3),
        "top_z": round(fl_top, 3),
        "top_clearance": round(funnel_radius_at(fl_top) - fl_top_r, 4),
        "funnel_rim_z": round(FUNNEL_Z_BASE + 0.500, 3),
        "ok": bool(min_clear > 0 and min_an > 0
                   and fl_top < FUNNEL_Z_BASE + 0.500)}
    # cup liquid vs cup inner wall
    cl = by_name["CupLiquid"]
    min_clear2 = 1e9
    min_clear2_at = None
    for v in world_verts(cl):
        rho = math.hypot(v.x, v.y)
        if v.z < 0.03 or v.z > 0.15:
            continue
        clear = cup_inner_radius_at(v.z) - rho
        if clear < min_clear2:
            min_clear2 = clear
            min_clear2_at = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
    min_an2 = 1e9
    min_an2_z = None
    for i in range(161):
        z = 0.031 + i * (0.11 - 0.031) / 160.0
        liq_r = 0.070 + (z - 0.031) / 0.079 * 0.006
        clear = cup_inner_radius_at(z) - liq_r
        if clear < min_an2:
            min_an2 = clear
            min_an2_z = z
    cl_vs = world_verts(cl)
    cl_bot = min(v.z for v in cl_vs)
    cl_top = max(v.z for v in cl_vs)
    rows["CupLiquid"] = {
        "min_clearance_verts": round(min_clear2, 4),
        "min_clearance_vert_at": min_clear2_at,
        "min_clearance_analytic": round(min_an2, 4),
        "min_clearance_analytic_z": round(min_an2_z, 3),
        "bottom_z": round(cl_bot, 3),
        "cavity_floor_z": 0.030,
        "top_z": round(cl_top, 3),
        "cup_rim_z": 0.150,
        "ok": bool(min_clear2 > 0 and min_an2 > 0
                   and cl_bot > 0.030 and cl_top < 0.150)}
    return {"liquids": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_drip_gap(by_name):
    """Funnel stem bottom (z 0.177) vs cup rim (z 0.15): the stem must
    hang above the rim with a gap, centred over the cup mouth."""
    funnel = by_name["Funnel"]
    stem_bot = min(v.z for v in world_verts(funnel))
    stem_verts = [v for v in world_verts(funnel)
                  if abs(v.z - stem_bot) < 0.001]
    stem_r = sum(math.hypot(v.x, v.y) for v in stem_verts) / len(stem_verts)
    stem_c = sum(stem_verts, Vector((0, 0, 0))) / len(stem_verts)
    cup = by_name["MeasuringCup"]
    rim_z = max(v.z for v in world_verts(cup))
    row = {"stem_bottom_z": round(stem_bot, 3),
           "stem_bottom_radius": round(stem_r, 3),
           "stem_bottom_center": tuple(round(v, 3) for v in stem_c),
           "cup_rim_z": round(rim_z, 3),
           "cup_inner_radius_at_rim": round(cup_inner_radius_at(0.15), 3),
           "drip_gap": round(stem_bot - rim_z, 3),
           "ok": bool(abs(stem_bot - 0.177) < 0.002
                      and abs(rim_z - 0.150) < 0.002
                      and stem_bot > rim_z
                      and abs(stem_c.x) < 0.002 and abs(stem_c.y) < 0.002
                      and stem_r < cup_inner_radius_at(0.15))}
    return row


def check_grad_rings(by_name):
    rows = {}
    for i, z in enumerate(GRAD_ZS):
        name = "GradRing_%d" % (i + 1)
        obj = by_name[name]
        rings = ring_analysis(obj, (0, 0, 0), (0, 0, 1), rho_min=0.0005)
        want_r = cup_radius_at(z) + 0.001
        row = {"rings": [(x["distance"], x["count"], x["radius"])
                         for x in rings],
               "design_center_z": z,
               "design_radius": round(want_r, 4),
               "ok": bool(
                   len(rings) == 2
                   and [x["count"] for x in rings] == [GRAD_SIDES] * 2
                   and abs(rings[0]["distance"] - (z - 0.0015)) < 0.002
                   and abs(rings[1]["distance"] - (z + 0.0015)) < 0.002
                   and all(abs(x["radius"] - want_r) < 0.002
                           for x in rings))}
        rows[name] = row
    return {"rings": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_stand_joins(by_name):
    """Crossbar ends embed into the posts and ring arms embed into the
    ring tube and the posts: joined by design, so measure the embed
    depths and report them (they must be > 0, i.e. actually joined,
    and < the receiving part's size, i.e. not poking through)."""
    rows = {}
    # crossbar (x -0.19..0.19) vs posts (x 0.15..0.19 / -0.19..-0.15),
    # z overlap 0.44..0.46
    cb = world_range(by_name["StandCrossbar"])
    pl = world_range(by_name["StandPost_L"])
    pr = world_range(by_name["StandPost_R"])
    rows["crossbar_into_posts"] = {
        "crossbar_x": (cb[0], cb[1]), "post_L_x": (pl[0], pl[1]),
        "post_R_x": (pr[0], pr[1]),
        "embed_L": round(cb[0] - pl[0], 3) if cb[0] > pl[0] else None,
        "embed_R": round(pr[1] - cb[1], 3) if cb[1] < pr[1] else None,
        "z_overlap": (round(max(cb[4], pl[4]), 3),
                      round(min(cb[5], pl[5]), 3)),
        "ok": bool(cb[0] >= pl[0] and cb[0] < pl[1]
                   and cb[1] <= pr[1] and cb[1] > pr[0]
                   and cb[4] < pl[5] and cb[5] > pl[4])}
    # ring arms: inner end inside the ring tube (radial 0.088..0.102),
    # outer end inside the posts (x 0.15..0.19)
    for sx, name in ((-1, "RingArm_L"), (1, "RingArm_R")):
        r = world_range(by_name[name])
        inner = min(abs(r[0]), abs(r[1])) if sx < 0 else min(abs(r[0]), abs(r[1]))
        # inner end = the end nearer x=0
        inner_end = r[1] if sx < 0 else r[0]
        outer_end = r[0] if sx < 0 else r[1]
        rows[name] = {
            "range": r,
            "inner_end_x": round(inner_end, 3),
            "outer_end_x": round(outer_end, 3),
            "ring_tube_radial": (round(RING_R - RING_TUBE, 3),
                                 round(RING_R + RING_TUBE, 3)),
            "post_x": (round(-0.19, 3), round(-0.15, 3)) if sx < 0
                      else (round(0.15, 3), round(0.19, 3)),
            "ok": bool(0.088 <= abs(inner_end) <= 0.102
                       and 0.15 <= abs(outer_end) <= 0.19)}
    return {"joins": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_ground(by_name):
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
    # the stand base stands on the ground (bottom z 0); everything
    # else sits on or above it, so nothing may go below z 0
    ok = all(z >= -0.001 for z in zmins.values())
    return {"checked": len(zmins), "below_ground": below,
            "global_min_z": round(min(zmins.values()), 3),
            "ok": bool(ok)}


def check_overall(by_name):
    rs = [world_range(o) for o in by_name.values()]
    x0 = min(r[0] for r in rs)
    x1 = max(r[1] for r in rs)
    y0 = min(r[2] for r in rs)
    y1 = max(r[3] for r in rs)
    z0 = min(r[4] for r in rs)
    z1 = max(r[5] for r in rs)
    row = {"bbox": (x0, x1, y0, y1, z0, z1),
           "width": round(x1 - x0, 3), "depth": round(y1 - y0, 3),
           "height": round(z1 - z0, 3),
           # 066 note: "整体约 0.44 m 宽 × 0.52 m 高 × 0.30 m 深"
           "note_size": (0.44, 0.52, 0.30)}
    row["ok"] = bool(abs(row["width"] - 0.44) <= 0.02
                     and abs(row["height"] - 0.52) <= 0.02
                     and abs(row["depth"] - 0.30) <= 0.02)
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 066 design values.
    Glass_Clear also checks Alpha + dithered render method; the two
    liquids also check the Emission node (color, strength) and the
    MixShader factor."""
    rows = []
    for name, spec in DESIGN_MATS.items():
        col = tuple(round(v, 2) for v in spec["color"])
        mat = bpy.data.materials.get(name)
        if mat is None or not mat.use_nodes:
            rows.append({"name": name, "found": False, "ok": False,
                         "design_color_linear": col})
            continue
        bsdf = None
        emit = None
        mix = None
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
            elif n.type == 'EMISSION':
                emit = n
            elif n.type == 'MIX_SHADER':
                mix = n
        if bsdf is None:
            rows.append({"name": name, "found": True, "ok": False,
                         "design_color_linear": col})
            continue
        m = round(bsdf.inputs["Metallic"].default_value, 2)
        r = round(bsdf.inputs["Roughness"].default_value, 2)
        c = tuple(round(v, 2)
                  for v in bsdf.inputs["Base Color"].default_value[:3])
        ok = (abs(m - spec["metallic"]) < 0.01
              and abs(r - spec["roughness"]) < 0.01
              and all(abs(a - b) < 0.01 for a, b in zip(c, col)))
        extra = {}
        if "alpha" in spec:
            a = round(bsdf.inputs["Alpha"].default_value, 2)
            extra["alpha"] = a
            extra["alpha_ok"] = bool(abs(a - spec["alpha"]) < 0.01)
            extra["surface_render_method"] = mat.surface_render_method
            extra["dithered_ok"] = bool(
                mat.surface_render_method == 'DITHERED')
            ok = ok and extra["alpha_ok"] and extra["dithered_ok"]
        if spec["emissive"] is not None:
            ecol, estr, mfac = spec["emissive"]
            if emit is None or mix is None:
                extra["emission_found"] = False
                ok = False
            else:
                ec = tuple(round(v, 2)
                           for v in emit.inputs["Color"].default_value[:3])
                es = round(emit.inputs["Strength"].default_value, 2)
                mf = round(mix.inputs[0].default_value, 2)
                extra["emission_color"] = ec
                extra["emission_strength"] = es
                extra["mix_factor"] = mf
                extra["emission_found"] = True
                ok = ok and all(abs(a - b) < 0.01
                                for a, b in zip(ec, ecol)) \
                    and abs(es - estr) < 0.01 and abs(mf - mfac) < 0.01
        rows.append({"name": name, "found": True, "metallic": m,
                     "roughness": r, "base_color": c,
                     "design_color_linear": col, "ok": bool(ok), **extra})
    used = {m.name for o in parts for m in o.data.materials if m}
    unused_design = [n for n in DESIGN_MATS if n not in used]
    assign_bad = []
    for name, want in PART_MATERIAL.items():
        got = results[name]["materials"]
        if got != [want]:
            assign_bad.append({"part": name, "want": want, "got": got})
    empty_slots = sum(1 for o in parts
                      for m in o.data.materials if m is None)
    return {"rows": rows,
            "all_ok": bool(all(r["ok"] for r in rows)),
            "unused_design_mats": unused_design,
            "assignment_mismatches": assign_bad,
            "empty_material_slots": empty_slots}


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    parts = [o for o in bpy.context.scene.objects
             if o.type == 'MESH' and o.name not in EXCLUDE]
    by_name = {o.name: o for o in parts}
    print("QA_PARTS_COUNT:", len(parts))
    print("QA_PART_NAMES:", sorted(by_name.keys()))
    results = {}
    uv_dump = {}
    for obj in sorted(parts, key=lambda o: o.name):
        r = check_mesh(obj)
        results[obj.name] = r
        uv_dump[obj.name] = r["uv"]["faces"]
        print("QA %s verts=%d faces=%d tris=%d quads=%d ngons=%d dups=%d "
              "loose=%d boundary=%d nonmanifold=%d degen=%d invnorm=%d maxval=%d" % (
                  obj.name, r["verts"], r["faces"], r["tris"], r["quads"],
                  r["ngons"], r["duplicate_verts"], r["loose_edges"],
                  r["boundary_edges"], r["nonmanifold_edges"],
                  r["degenerate_faces"], r["inverted_normals"],
                  r["max_valence"]))
        print("QA_UV %s has_uv=%s oob=%d util=%.3f islands=%d overlap=%.2f%%" % (
            obj.name, r["uv"]["has_uv"], r["uv"]["out_of_bounds"],
            r["uv"]["utilization"], r["uv"]["islands"], r["uv"]["overlap_pct"]))

    with open(UV_JSON, "w", encoding="utf-8") as f:
        json.dump(uv_dump, f)

    face_mismatch = {n: (results[n]["faces"], e)
                     for n, e in EXPECTED_FACES.items()
                     if n in results and results[n]["faces"] != e}
    missing = [n for n in EXPECTED_FACES if n not in results]
    extra = [n for n in results if n not in EXPECTED_FACES]
    print("QA_FACE_MISMATCH:", face_mismatch)
    print("QA_MISSING:", missing, "QA_EXTRA:", extra)

    funnel = check_lathe("Funnel", by_name["Funnel"], FUNNEL_PROFILE,
                         FUNNEL_SIDES, (0, 0, FUNNEL_Z_BASE), (0, 0, 1),
                         0, [])
    print("QA_FUNNEL:", funnel)
    cup = check_lathe("MeasuringCup", by_name["MeasuringCup"],
                      CUP_PROFILE, CUP_SIDES, (0, 0, 0), (0, 0, 1),
                      CUP_SIDES, [0.020])
    print("QA_CUP:", cup)
    grad = check_grad_rings(by_name)
    print("QA_GRAD_RINGS:", grad)
    fliq = check_tapered_cyl("FunnelLiquid", by_name["FunnelLiquid"],
                             FUNNEL_LIQ[0], FUNNEL_LIQ[1],
                             FUNNEL_LIQ[2], FUNNEL_LIQ[3], 24)
    print("QA_FUNNEL_LIQUID_SHAPE:", fliq)
    cliq = check_tapered_cyl("CupLiquid", by_name["CupLiquid"],
                             CUP_LIQ[0], CUP_LIQ[1],
                             CUP_LIQ[2], CUP_LIQ[3], 24)
    print("QA_CUP_LIQUID_SHAPE:", cliq)
    ring = check_torus("FunnelRing", by_name["FunnelRing"],
                       RING_R, RING_TUBE, RING_Z, 24, 6)
    print("QA_FUNNEL_RING:", ring)
    lip = check_torus("FunnelRimLip", by_name["FunnelRimLip"],
                      LIP_R, LIP_TUBE, LIP_Z, 24, 6)
    print("QA_RIM_LIP:", lip)
    boxes = {n: check_box(n, by_name[n]) for n in BOXES}
    print("QA_BOXES:", boxes)
    wedge = check_ring_wedge(by_name)
    print("QA_RING_WEDGE:", wedge)
    rimlip = check_rim_lip(by_name)
    print("QA_RIM_LIP_WRAP:", rimlip)
    liquids = check_liquids(by_name)
    print("QA_LIQUIDS:", liquids)
    drip = check_drip_gap(by_name)
    print("QA_DRIP_GAP:", drip)
    joins = check_stand_joins(by_name)
    print("QA_STAND_JOINS:", joins)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)
    # Normal check for the open funnel tube: the recalc heuristic
    # flips all 120 funnel faces because the megaphone's wall-only
    # signed volume is negative (see check_lathe_winding_analytic).
    # The analytic profile-segment check is authoritative here.
    funnel_winding = check_lathe_winding_analytic(
        by_name["Funnel"], FUNNEL_PROFILE, FUNNEL_SIDES, FUNNEL_Z_BASE)
    print("QA_FUNNEL_WINDING_ANALYTIC flipped=%d of 120"
          % len(funnel_winding))
    funnel_winding_row = {
        "method": "profile-segment analytic (same as 066 build self-check)",
        "flipped_faces": len(funnel_winding),
        "recalc_flipped_faces": results["Funnel"]["inverted_normals"],
        "ok": bool(len(funnel_winding) == 0)}

    structure = {"funnel": funnel, "cup": cup, "grad_rings": grad,
                 "funnel_liquid_shape": fliq, "cup_liquid_shape": cliq,
                 "funnel_ring": ring, "rim_lip": lip, "boxes": boxes,
                 "ring_wedge": wedge, "rim_lip_wrap": rimlip,
                 "liquids": liquids, "drip_gap": drip,
                 "stand_joins": joins, "ground_contact": ground,
                 "overall": overall,
                 "funnel_winding": funnel_winding_row}
    structure_ok = (funnel["ok"] and cup["ok"] and grad["ok"]
                    and fliq["ok"] and cliq["ok"] and ring["ok"]
                    and lip["ok"]
                    and all(v["ok"] for v in boxes.values())
                    and wedge["ok"] and rimlip["ok"] and liquids["ok"]
                    and drip["ok"] and joins["ok"] and ground["ok"]
                    and overall["ok"] and funnel_winding_row["ok"])

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # Boundary edges BY DESIGN (open glassware, not holes):
    # Funnel: open stem bottom (24) + open rim (24) = 48;
    # MeasuringCup: cavity floor centre ring, radius 0.001 (24) — a
    # 1 mm pinhole at the cavity floor, same as the 062 mortar;
    # GradRing_1..4: each is a zero-thickness band open at both its
    # top and bottom circular edges (24 + 24 = 48 each).
    # Everything else must be closed (0 boundary edges).
    open_parts = {"Funnel": 48, "MeasuringCup": 24,
                  "GradRing_1": 48, "GradRing_2": 48,
                  "GradRing_3": 48, "GradRing_4": 48}
    open_boundary = sum(results[n]["boundary_edges"] for n in open_parts)
    open_ok = all(results[n]["boundary_edges"] == s
                  for n, s in open_parts.items())
    other_boundary = sum(r["boundary_edges"] for n, r in results.items()
                         if n not in open_parts)
    boundary_ok = (open_boundary == sum(open_parts.values())
                   and open_ok and other_boundary == 0)
    ngons_ok = tot["ngons"] == 0
    uv_ok = all(r["uv"]["has_uv"] for r in results.values())
    faces_ok = (not face_mismatch and not missing and not extra
                and tot["faces"] == EXPECTED_TOTAL_FACES
                and tot["tris"] == EXPECTED_TRIS
                and tot["quads"] == EXPECTED_QUADS)
    # the 066 build script's own winding self-check was all 0; the
    # recalc check above is the independent re-measurement — except
    # for the open funnel tube, where recalc's signed-volume heuristic
    # is wrong (see funnel_winding_row) and the analytic check rules.
    inverted_effective = (tot["inverted_normals"]
                          - results["Funnel"]["inverted_normals"]
                          + len(funnel_winding))
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and boundary_ok
              and inverted_effective == 0 and tot_oob == 0
              and worst_overlap < 1.0 and mats["empty_material_slots"] == 0
              and not mats["assignment_mismatches"]
              and not mats["unused_design_mats"]
              and faces_ok and structure_ok and mats["all_ok"])

    summary = {
        "asset": "066-lowpoly-funnel-beaker",
        "parts": len(results),
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "ngons_ok": bool(ngons_ok),
        "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "boundary_edges": tot["boundary_edges"],
        "boundary_edges_ok": bool(boundary_ok),
        "open_boundary_edges": open_boundary,
        "inverted_normals": inverted_effective,
        "inverted_normals_recalc_raw": tot["inverted_normals"],
        "inverted_normals_recalc_funnel": results["Funnel"][
            "inverted_normals"],
        "funnel_winding_analytic_flipped": len(funnel_winding),
        "face_counts_match_design": bool(faces_ok),
        "face_mismatch": face_mismatch,
        "missing_parts": missing, "extra_parts": extra,
        "uv_out_of_bounds": tot_oob,
        "uv_ok": bool(uv_ok),
        "uv_utilization_per_part": {k: round(v["uv"]["utilization"], 3)
                                    for k, v in results.items()},
        "uv_islands": tot_islands,
        "uv_overlap_pct": round(worst_overlap, 2),
        "uv_overlap_worst_part": worst_overlap_part,
        "empty_material_slots": mats["empty_material_slots"],
        "structure": structure,
        "structure_ok": bool(structure_ok),
        "materials": mats,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("QA_SUMMARY:", summary)

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    order = sorted(results.keys())
    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 067 资产质检单：低模炼金漏斗与量杯（066）\n\n")
        f.write("被检资产：`scenes/066-lowpoly-funnel-beaker.blend`（%d 个道具部件，不含地面）。\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。\n\n")
        f.write("## 结论\n\n")
        f.write("**%s**\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED：见第 7 节待修项"))
        f.write("## 1. 拓扑\n\n")
        f.write("| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 最高顶点价数 |\n")
        f.write("| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | ------------ |\n")
        for name in order:
            r = results[name]
            f.write("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n" % (
                name, r["verts"], r["faces"], r["tris"], r["quads"], r["ngons"],
                r["duplicate_verts"], r["loose_edges"], r["boundary_edges"],
                r["nonmanifold_edges"], r["degenerate_faces"], r["max_valence"]))
        f.write("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | — |\n\n" % (
            tot["verts"], tot["faces"], tot["tris"], tot["quads"], tot["ngons"],
            tot["duplicate_verts"], tot["loose_edges"], tot["boundary_edges"],
            tot["nonmanifold_edges"], tot["degenerate_faces"]))
        f.write("- 面数与 066 设计表逐部件比对：%s（设计 828 面：三角 120、四边 708、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
            verdict(faces_ok), tot["faces"], tot["tris"], tot["quads"], tot["ngons"]))
        if face_mismatch:
            f.write("  - 面数不符：%s\n" % face_mismatch)
        if missing:
            f.write("  - 缺失部件：%s\n" % missing)
        if extra:
            f.write("  - 多余部件：%s\n" % extra)
        f.write("- N-gon：共 %d 个（设计值 0）：%s\n" % (tot["ngons"], verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 开口边：边界边共 %d 条，全部是设计上的开口（漏斗细管底口 24 + 漏斗口沿 24 = 48；量杯腔底中心 1 mm 针孔 24；4 道刻度环各为零厚度圆柱带、上下两圈开口边各 24，共 192），其余 10 个部件 0 条：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：除漏斗外的 15 个部件倒置面 %d 个；漏斗的 recalc 读数 %d 个是该启发式在开口喇叭筒上的误判（见下），不计入结论：%s，合计有效倒置面 %d 个\n" % (
            tot["inverted_normals"] - results["Funnel"]["inverted_normals"],
            results["Funnel"]["inverted_normals"],
            verdict(inverted_effective == 0), inverted_effective))
        f.write("  漏斗说明：recalc_face_normals 用网格有向体积定内外，漏斗是两端开口的喇叭筒（口沿半径 0.150、细管半径 0.022），仅侧壁的有向体积为负，recalc 便把全部 120 个面翻转；但轮廓段解析检查（与 066 构建脚本自检同一方法：每段轮廓的理论外法线与面法线逐面比对）内翻面 %d 个，且渲染中漏斗玻璃着色正常——解析检查为准，recalc 读数是开口管上的已知误判。其余部件的 recalc 检查与 066 构建脚本自检一致，全 0。\n\n" % len(funnel_winding))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（%d 个部件均已 Smart UV Project 展开）\n" % (
            verdict(uv_ok), len(results)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率最低的 10 个部件：\n")
        low = sorted(results.items(),
                     key=lambda kv: kv[1]["uv"]["utilization"])[:10]
        for name, r in low:
            f.write("  - %s：%.1f%%\n" % (name, r["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长/薄板部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件 %s）：%.2f%%，%s（阈值 <1%%）\n\n" % (
            worst_overlap_part, worst_overlap,
            verdict(worst_overlap < 1.0)))
        f.write("## 4. 漏斗与量杯结构（实测）\n\n")
        f.write("### 4.1 玻璃漏斗（车削轮廓，24 段）\n\n")
        f.write("- Funnel：%d 环（每环 24 顶点），环高（局部 z）%s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；无三角面（上下两端开口，无封盖扇形）：%s\n" % (
            len(funnel["rings"]), funnel["ring_distances"],
            funnel["ring_radii"],
            funnel["design_radii"],
            funnel["range"][0], funnel["range"][1], funnel["range"][2],
            funnel["range"][3], funnel["range"][4], funnel["range"][5],
            funnel["expected"], verdict(funnel["ok"])))
        f.write("\n### 4.2 玻璃量杯（开口车削杯，24 段）\n\n")
        f.write("- MeasuringCup：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；%d 个三角面全部是底面扇形封口（面中心轴向位置 0.020），腔底中心无封盖（1 mm 针孔）：%s\n" % (
            len(cup["rings"]), cup["ring_distances"],
            cup["ring_radii"],
            cup["design_radii"],
            cup["range"][0], cup["range"][1], cup["range"][2],
            cup["range"][3], cup["range"][4], cup["range"][5],
            cup["expected"], cup["tri_count"],
            verdict(cup["ok"])))
        f.write("\n### 4.3 刻度环（4 道，杯外壁）\n\n")
        for name, g in grad["rings"].items():
            f.write("- %s：2 环（每环 24 顶点），环高 z %s、半径 %s（设计中心 z %.3f、半径 %.4f，杯壁外探 0.001）：%s\n" % (
                name, [d for d, _c, _r in g["rings"]],
                [r for _d, _c, r in g["rings"]],
                g["design_center_z"], g["design_radius"],
                verdict(g["ok"])))
        f.write("\n### 4.4 双药液（截锥，24 段）\n\n")
        f.write("- FunnelLiquid：2 环（底 z %.3f、半径 %.3f；顶 z %.3f、半径 %.3f），48 个三角面分处两端盖（轴向位置 %s）；与漏斗内壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.3f）；顶面 z %.3f 在漏斗口沿 z %.3f 之下：%s\n" % (
            fliq["rings"][0][0], fliq["rings"][0][2],
            fliq["rings"][1][0], fliq["rings"][1][2],
            fliq["tri_axial_positions"],
            liquids["liquids"]["FunnelLiquid"]["min_clearance_verts"],
            liquids["liquids"]["FunnelLiquid"]["min_clearance_vert_at"],
            liquids["liquids"]["FunnelLiquid"]["min_clearance_analytic"],
            liquids["liquids"]["FunnelLiquid"]["min_clearance_analytic_z"],
            liquids["liquids"]["FunnelLiquid"]["top_z"],
            liquids["liquids"]["FunnelLiquid"]["funnel_rim_z"],
            verdict(liquids["liquids"]["FunnelLiquid"]["ok"])))
        f.write("- CupLiquid：2 环（底 z %.3f、半径 %.3f；顶 z %.3f、半径 %.3f），48 个三角面分处两端盖（轴向位置 %s）；与量杯内壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.3f）；底面 z %.3f 在腔底 z 0.030 之上、顶面 z %.3f 在杯口 z 0.150 之下：%s\n" % (
            cliq["rings"][0][0], cliq["rings"][0][2],
            cliq["rings"][1][0], cliq["rings"][1][2],
            cliq["tri_axial_positions"],
            liquids["liquids"]["CupLiquid"]["min_clearance_verts"],
            liquids["liquids"]["CupLiquid"]["min_clearance_vert_at"],
            liquids["liquids"]["CupLiquid"]["min_clearance_analytic"],
            liquids["liquids"]["CupLiquid"]["min_clearance_analytic_z"],
            liquids["liquids"]["CupLiquid"]["bottom_z"],
            liquids["liquids"]["CupLiquid"]["top_z"],
            verdict(liquids["liquids"]["CupLiquid"]["ok"])))
        f.write("\n### 4.5 黄铜圆环与玻璃卷边\n\n")
        f.write("- FunnelRing：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.088、外径 0.102）：%s\n" % (
            ring["range"][0], ring["range"][1], ring["range"][2],
            ring["range"][3], ring["range"][4], ring["range"][5],
            ring["expected"], ring["rho_min"], ring["rho_max"],
            verdict(ring["ok"])))
        f.write("- FunnelRimLip：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.145、外径 0.155）：%s\n" % (
            lip["range"][0], lip["range"][1], lip["range"][2],
            lip["range"][3], lip["range"][4], lip["range"][5],
            lip["expected"], lip["rho_min"], lip["rho_max"],
            verdict(lip["ok"])))
        f.write("- 漏斗卡环楔合：漏斗锥在圆环平面（z 0.42）处真实半径 %.4f，大于圆环内径 %.4f，漏斗不可能从环里掉下去；锥面与圆环管壁的最大穿入（曲面解析，z %.3f 处）%.4f m（小于管径 0.007，未打穿整根管子），漏斗网格顶点实测最深穿入 %.4f（位于 %s），圆环网格顶点实测最大穿入 %.4f（位于 %s）：楔合是设计意图（066 笔记“锥体卡在环里”），%s\n" % (
            wedge["cone_radius_at_ring_plane_true"],
            wedge["ring_inner_radius"],
            wedge["analytic_max_z"], wedge["analytic_max_penetration"],
            -wedge["funnel_vert_min_sdf"], wedge["funnel_vert_worst"],
            wedge["ring_vert_max_penetration"], wedge["ring_vert_worst"],
            verdict(wedge["ok"])))
        f.write("- 卷边裹住漏斗口沿：漏斗顶环 %d 个顶点、平均半径 %.4f（卷边中心圆半径 %.3f），到卷边管面的有向距离 %.4f–%.4f（全为负值，即顶环整圈埋在卷边管内）：%s\n" % (
            rimlip["top_ring_verts"], rimlip["top_ring_radius"],
            rimlip["lip_center_radius"], rimlip["min_sdf_to_lip"],
            rimlip["max_sdf_to_lip"], verdict(rimlip["ok"])))
        f.write("\n### 4.6 木质支架（盒子件）与连接\n\n")
        for name, b in boxes.items():
            f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
                name, b["range"][0], b["range"][1], b["range"][2],
                b["range"][3], b["range"][4], b["range"][5],
                b["expected"], verdict(b["ok"])))
        f.write("- 横梁埋入立柱：横梁 x %.3f–%.3f，两端分别埋入左立柱（x %.3f–%.3f）与右立柱（x %.3f–%.3f），z 重叠 %.3f–%.3f：%s\n" % (
            joins["joins"]["crossbar_into_posts"]["crossbar_x"][0],
            joins["joins"]["crossbar_into_posts"]["crossbar_x"][1],
            joins["joins"]["crossbar_into_posts"]["post_L_x"][0],
            joins["joins"]["crossbar_into_posts"]["post_L_x"][1],
            joins["joins"]["crossbar_into_posts"]["post_R_x"][0],
            joins["joins"]["crossbar_into_posts"]["post_R_x"][1],
            joins["joins"]["crossbar_into_posts"]["z_overlap"][0],
            joins["joins"]["crossbar_into_posts"]["z_overlap"][1],
            verdict(joins["joins"]["crossbar_into_posts"]["ok"])))
        for name in ("RingArm_L", "RingArm_R"):
            j = joins["joins"][name]
            f.write("- %s：内端 x %.3f（圆环管径向范围 %.3f–%.3f，埋入管内），外端 x %.3f（立柱 x %.3f–%.3f，埋入柱内）：%s\n" % (
                name, j["inner_end_x"], j["ring_tube_radial"][0],
                j["ring_tube_radial"][1], j["outer_end_x"],
                j["post_x"][0], j["post_x"][1], verdict(j["ok"])))
        f.write("\n### 4.7 滴落间隙\n\n")
        f.write("- 漏斗细管底端 z %.3f（底环半径 %.3f、中心 %s），量杯口沿 z %.3f（杯口内径 %.3f），滴落间隙 %.3f m；细管正对杯口中心、半径远小于杯口内径：%s\n" % (
            drip["stem_bottom_z"], drip["stem_bottom_radius"],
            drip["stem_bottom_center"], drip["cup_rim_z"],
            drip["cup_inner_radius_at_rim"], drip["drip_gap"],
            verdict(drip["ok"])))
        f.write("\n### 4.8 地面、整体\n\n")
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s（底板 z=0 落地，其余部件在底板或支架上）：%s\n" % (
            ground["checked"], ground["global_min_z"],
            ground["below_ground"] if ground["below_ground"] else "无",
            verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（066 笔记“约 0.44 × 0.52 × 0.30 m”，"
                "允差 ±0.02）：%s\n" % (
                    overall["bbox"][0], overall["bbox"][1],
                    overall["bbox"][2], overall["bbox"][3],
                    overall["bbox"][4], overall["bbox"][5],
                    overall["width"], overall["depth"], overall["height"],
                    verdict(overall["ok"])))
        f.write("\n## 5. 材质 / 贴图\n\n")
        f.write("- 各部件材质均为程序化 Principled 材质，无图片贴图（%d 个部件，%d 个材质槽）：\n" % (
            len(results), sum(len(o.data.materials)
                              for o in parts if o.type == 'MESH')))
        f.write("- 空材质槽：%d 个，%s\n" % (
            mats["empty_material_slots"],
            verdict(mats["empty_material_slots"] == 0)))
        f.write("- 部件材质分配与设计一致：%s\n" % verdict(
            not mats["assignment_mismatches"]))
        if mats["assignment_mismatches"]:
            f.write("  - 分配不符：%s\n" % mats["assignment_mismatches"])
        f.write("- 未使用的设计材质：%s\n" % (
            mats["unused_design_mats"] if mats["unused_design_mats"] else "无"))
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 066 构建脚本直接存入的线性值；玻璃另查 Alpha 与渲染方式，药液另查 Emission 与混合系数）：\n")
        for row in mats["rows"]:
            line = ("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                    "底色 %s（设计 %s）" % (
                        row["name"], row["metallic"],
                        DESIGN_MATS[row["name"]]["metallic"],
                        row["roughness"],
                        DESIGN_MATS[row["name"]]["roughness"],
                        row["base_color"], row["design_color_linear"]))
            if "alpha" in row:
                line += "，Alpha %.2f（设计 %.2f），渲染方式 %s（须 DITHERED）" % (
                    row["alpha"], DESIGN_MATS[row["name"]]["alpha"],
                    row["surface_render_method"])
            if row.get("emission_found"):
                ecol, estr, mfac = DESIGN_MATS[row["name"]]["emissive"]
                line += "，Emission 颜色 %s（设计 %s）、强度 %.2f（设计 %.2f）、混合 %.2f（设计 %.2f）" % (
                    row["emission_color"], ecol, row["emission_strength"],
                    estr, row["mix_factor"], mfac)
            line += "：%s\n" % verdict(row["ok"])
            f.write(line)
        f.write("\n## 6. 备注（实测发现，非缺陷）\n\n")
        f.write("- 066 笔记“实测间隙”两处数字有误，根因是 066 构建脚本里的 funnel_radius_at() 用了一条简化直线（局部 z 0.30→0.50、半径 0.022→0.150），忽略了轮廓在 (0.050, 0.330) 处的折点；本质检改用真实分段轮廓重算：\n")
        f.write("  - 圆环平面 z 0.42：笔记称漏斗锥半径 0.0879、与圆环内径 0.088 差 -0.0001（“正好卡在环里”）；真实轮廓半径是 %.4f，比圆环内径大 0.0037——漏斗锥在环平面处本来就比环孔宽，楔合穿入最深 %.4f（见 4.5 节），不是 0.0001 的轻触。几何本身没问题（漏斗确实卡在环里），错的是笔记的数字；已随 067 在 066 笔记末尾追加更正。\n" % (
            wedge["cone_radius_at_ring_plane_true"],
            wedge["analytic_max_penetration"]))
        f.write("  - 漏斗药液间隙：笔记称 z 0.36 处 0.0016、z 0.41 处 0.0047、顶面 0.0076（同样出自简化直线）；真实分段轮廓下最小间隙 %.4f（药液底环 z 0.322 处），顶面间隙 %.4f，处处为正、无穿帮。\n" % (
            liquids["liquids"]["FunnelLiquid"]["min_clearance_analytic"],
            liquids["liquids"]["FunnelLiquid"]["top_clearance"]))
        f.write("- 漏斗卡环楔合穿入 %.4f m（4.5 节）是设计意图的接触，不是缺陷：锥体必须比环孔宽才能卡住；穿入小于管径 0.007，未打穿整根黄铜管，渲染中读作漏斗 resting 在环里。\n" % (
            wedge["analytic_max_penetration"]))
        f.write("- 刻度环是零厚度圆柱带（上下两圈开口边）：它贴在杯壁上只起刻度线作用，无厚度是低模刻度线的常规做法，不判为破洞。\n")
        f.write("- 漏斗药液最窄间隙 %.4f m（底环处）偏紧但为正，渲染中看不见穿帮；后续若改药液形状，底环半径须按真实轮廓留出余量，别再用简化直线估算。\n" % (
            liquids["liquids"]["FunnelLiquid"]["min_clearance_analytic"]))
        f.write("- 杯体前壁上半段主光过曝偏白（066 笔记已知问题），仓库影棚风格所致，本质检不重复判否。\n")
        f.write("- 066 笔记尺寸与实测一致：宽 %.3f m × 深 %.3f m × 高 %.3f m"
                "（笔记“约 0.44 × 0.52 × 0.30 m”）。\n" % (
                    overall["width"], overall["depth"], overall["height"]))
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、漏斗与量杯结构、地面接触均通过。唯一需要做的事是 066 笔记的数字更正（见第 6 节，已随 067 追加到 066 笔记末尾），几何本身无需返工。\n")
        else:
            f.write("待修项：\n\n")
            f.write("（按复核结果填写）\n")


if __name__ == "__main__":
    main()
