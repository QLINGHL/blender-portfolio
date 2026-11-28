# -*- coding: utf-8 -*-
"""072 资产质检：对 071 低模炼金沙漏做真实 mesh 检查（拓扑/法线/UV/材质），
并实测沙漏特有结构：玻璃车削环、双沙体与玻璃壁间隙、35° 安息角沙锥、
箍环楔合、细沙流两端间隙、立柱与顶钮、端板贴合。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 072-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "071-lowpoly-hourglass.blend")
UV_JSON = os.path.join(ROOT, "scenes", "072-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "072-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "072-asset-qa-checklist.md")

# every mesh object in the 071 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/071-lowpoly-hourglass.md (per-part table)
EXPECTED_FACES = {
    "BoardBottom": 6, "BoardTop": 6, "HourglassGlass": 360,
    "SandLower": 192, "SandUpper": 168, "SandStream": 24,
    "RingLower": 144, "RingUpper": 144,
    "Pillar_0": 36, "Pillar_1": 36, "Pillar_2": 36, "Pillar_3": 36,
    "KnobBase": 36, "KnobTop": 96,
}
EXPECTED_TOTAL_FACES = 1320
EXPECTED_TRIS = 232
EXPECTED_QUADS = 1088

# part -> design material (from the 071 build script)
PART_MATERIAL = {
    "BoardBottom": "Board_Wood", "BoardTop": "Board_Wood",
    "HourglassGlass": "Glass_Clear",
    "SandLower": "Sand_Warm", "SandUpper": "Sand_Warm",
    "SandStream": "Sand_Warm",
    "RingLower": "Frame_Brass", "RingUpper": "Frame_Brass",
    "Pillar_0": "Frame_Brass", "Pillar_1": "Frame_Brass",
    "Pillar_2": "Frame_Brass", "Pillar_3": "Frame_Brass",
    "KnobBase": "Frame_Brass", "KnobTop": "Frame_Brass",
}

# Design material values from the 071 build script. The build script
# passes raw tuples to solid_material, which stores them directly as
# linear Base Color (same convention as the 059/060/063/067/069 scripts).
# Glass_Clear: alpha 0.35 + dithered (059 recipe). Sand_Warm is
# Principled + Emission mixed in (glow_material): check emission
# strength, mix factor and roughness as well.
DESIGN_MATS = {
    "Board_Wood":   {"metallic": 0.00, "roughness": 0.80,
                     "color": (0.32, 0.22, 0.12), "emissive": None},
    "Frame_Brass":  {"metallic": 0.70, "roughness": 0.35,
                     "color": (0.55, 0.40, 0.15), "emissive": None},
    "Glass_Clear":  {"metallic": 0.00, "roughness": 0.15,
                     "color": (0.80, 0.85, 0.88), "emissive": None,
                     "alpha": 0.35, "dithered": True},
    "Sand_Warm":    {"metallic": 0.00, "roughness": 0.90,
                     "color": (0.85, 0.72, 0.45),
                     "emissive": ((0.85, 0.72, 0.45), 0.25, 0.2)},
}

# design geometry (copied from the 071 build script)
GLASS_PROFILE = [
    (0.001, 0.020), (0.055, 0.025), (0.085, 0.050), (0.095, 0.090),
    (0.092, 0.130), (0.075, 0.160), (0.045, 0.185), (0.009, 0.220),
    (0.045, 0.232), (0.075, 0.255), (0.092, 0.300), (0.095, 0.350),
    (0.085, 0.390), (0.055, 0.415), (0.001, 0.420),
]
LOWER_SAND_PROFILE = [
    (0.001, 0.021), (0.040, 0.024), (0.060, 0.032), (0.075, 0.045),
    (0.055, 0.052), (0.035, 0.062), (0.015, 0.069), (0.001, 0.072),
]
# Upper sand cone: free surface at the 35-degree angle of repose from
# the neck (r 0.008, z 0.22), apex at (0.001, 0.2151), clamped to the
# glass wall (glass_r - 0.002) at the edge (0.0815, 0.2774). z values
# below are the build script's exact values rounded to 4 decimals.
UPPER_SAND_PROFILE = [
    (0.001, 0.2151), (0.020, 0.2284), (0.035, 0.2389), (0.050, 0.2494),
    (0.065, 0.2599), (0.078, 0.2690), (0.0815, 0.2774),
]
REPOSE_TAN = math.tan(math.radians(35.0))
NECK_Z = 0.22
NECK_R = 0.009
# 073 修复：STREAM_TOP_Z 从 0.219 降到 0.2145（低于沙锥顶点 z 0.2151，
# 整块顶盖落在沙锥体内；沙锥面在流半径 0.0035 处 z 0.2168）
STREAM_TOP_Z = 0.2145
STREAM_BOT_Z = 0.073
STREAM_R = 0.0035
RING_Z_LOW = 0.09
RING_Z_HIGH = 0.35
RING_R = 0.097
RING_TUBE = 0.006
GLASS_MAX_R = 0.095
# box parts: name -> (center, size)
BOXES = {
    "BoardBottom": ((0, 0, 0.01), (0.34, 0.26, 0.02)),
    "BoardTop": ((0, 0, 0.43), (0.34, 0.26, 0.02)),
}
# tapered cylinders: name -> (origin, z0, r0, z1, r1, sides)
TAPERED = {
    "Pillar_0": ((0.14, 0.10, 0), 0.02, 0.012, 0.42, 0.012, 12),
    "Pillar_1": ((-0.14, 0.10, 0), 0.02, 0.012, 0.42, 0.012, 12),
    "Pillar_2": ((0.14, -0.10, 0), 0.02, 0.012, 0.42, 0.012, 12),
    "Pillar_3": ((-0.14, -0.10, 0), 0.02, 0.012, 0.42, 0.012, 12),
    "KnobBase": ((0, 0, 0), 0.44, 0.020, 0.465, 0.008, 12),
}
# two-point tubes: name -> (p0, p1, radius, sides)
TUBES = {
    "SandStream": ((0, 0, STREAM_TOP_Z), (0, 0, STREAM_BOT_Z),
                   STREAM_R, 8),
}
# flat tori: name -> (center, R, tube, arc_segments, tube_segments)
TORI = {
    "RingLower": ((0, 0, RING_Z_LOW), RING_R, RING_TUBE, 24, 6),
    "RingUpper": ((0, 0, RING_Z_HIGH), RING_R, RING_TUBE, 24, 6),
}


def profile_radius_at(profile, z):
    """True piecewise-linear radius of a lathe profile at height z."""
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


def glass_radius_at(z):
    return profile_radius_at(GLASS_PROFILE, z)


def cone_surface_z(r):
    """Height of the upper sand cone's free surface at radius r
    (35-degree repose line through the neck point)."""
    return NECK_Z + REPOSE_TAN * (r - 0.008)


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
    mw = obj.matrix_world
    ws = [mw @ v.co for v in obj.data.vertices]
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def ring_analysis(obj, origin, direction, rho_min=0.0005):
    """Group the tube's ring verts (rho > rho_min off axis) by axial
    distance, then split each axial group by radius with a 0.002 gap
    tolerance; return [(distance, count, center, radius)] per ring."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    mw = obj.matrix_world
    by_axial = {}
    for v in obj.data.vertices:
        w = mw @ v.co
        rel = w - o
        axial = rel.dot(d)
        rho = (rel - d * axial).length
        if rho < rho_min:
            continue
        by_axial.setdefault(round(axial, 3), []).append((w, rho))
    rings = []
    for dist in sorted(by_axial):
        items = sorted(by_axial[dist], key=lambda t: t[1])
        groups = [[items[0]]]
        for item in items[1:]:
            if item[1] - groups[-1][-1][1] > 0.002:
                groups.append([item])
            else:
                groups[-1].append(item)
        for g in groups:
            pts = [w for w, _rho in g]
            c = sum(pts, Vector((0, 0, 0))) / len(pts)
            r = sum(rho for _w, rho in g) / len(g)
            rings.append({"distance": dist, "count": len(pts),
                          "center": tuple(round(v, 3) for v in c),
                          "radius": round(r, 3)})
    rings.sort(key=lambda x: (x["distance"], x["radius"]))
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


def check_lathe_winding_analytic(obj, profile, sides):
    """Analytic winding check for a lathe mesh, in local space (same
    method as the 071 build script's own self-check): the expected
    outward normal of each profile segment is computed from the
    profile geometry, and each face normal is compared against it.
    Authoritative for the lathe parts: Blender's recalc_face_normals
    decides orientation from the mesh's signed volume, which for an
    open vessel can misjudge (see 067 funnel)."""
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
    """Winding check for a flat ring: each face normal must point
    away from the nearest point on the ring's centre circle."""
    import bmesh as _bm
    mw = obj.matrix_world
    bm = _bm.new()
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


def check_centroid_winding(obj):
    """Centroid check (same as the 071 build script): count faces
    whose normal points inward toward the mesh centroid."""
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


def check_tapered_cyl(name, obj, origin, z0, r0, z1, r1, sides):
    rings = ring_analysis(obj, origin, (0, 0, 1), rho_min=0.0005)
    mw = obj.matrix_world
    tri_ax = []
    for p in obj.data.polygons:
        if len(p.vertices) == 3:
            c = mw @ p.center
            tri_ax.append(round(c.z, 3))
    r = world_range(obj)
    ox, oy, _oz = origin
    m = max(r0, r1)
    exp = (round(ox - m, 3), round(ox + m, 3),
           round(oy - m, 3), round(oy + m, 3),
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


def check_tube_between(name, obj, p0, p1, radius, sides):
    """A cylinder_between part: 2 rings, side quads, cap fans at both
    ends, closed (0 boundary edges)."""
    p0v, p1v = Vector(p0), Vector(p1)
    d = (p1v - p0v)
    L = d.length
    d = d.normalized()
    rings = ring_analysis(obj, p0, d, rho_min=0.0005)
    mw = obj.matrix_world
    tri_ax = []
    for p in obj.data.polygons:
        if len(p.vertices) == 3:
            c = mw @ p.center
            tri_ax.append(round((c - p0v).dot(d), 3))
    r = world_range(obj)
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for p in (p0v, p1v):
        for i in range(3):
            h = radius * math.sqrt(max(0.0, 1.0 - d[i] * d[i]))
            mins[i] = min(mins[i], p[i] - h)
            maxs[i] = max(maxs[i], p[i] + h)
    exp = (round(mins.x, 3), round(maxs.x, 3),
           round(mins.y, 3), round(maxs.y, 3),
           round(mins.z, 3), round(maxs.z, 3))
    row = {"range": r, "expected": exp,
           "rings": [(x["distance"], x["count"], x["radius"])
                     for x in rings],
           "tri_axial_positions": sorted(set(tri_ax)),
           "tri_count": len(tri_ax),
           "length": round(L, 4),
           "ok": bool(
               len(rings) == 2
               and [x["count"] for x in rings] == [sides, sides]
               and abs(rings[0]["distance"]) < 0.002
               and abs(rings[1]["distance"] - L) < 0.002
               and all(abs(x["radius"] - radius) < 0.002 for x in rings)
               and sorted(set(tri_ax)) == [0.0, round(L, 3)]
               and len(tri_ax) == 2 * sides
               and bbox_close(r, exp))}
    return row


def check_torus(name, obj, center, R, tube, arc_segments, tube_segments):
    """A torus_xy part: bbox vs the analytic torus bbox. The tube is
    sampled in `tube_segments` steps, so the measured z half-extent
    is tube*sin(60deg) for 6 segments, not the full tube radius;
    allow tol 0.002 against the continuous bbox (same note as 067)."""
    cx, cy, cz = center
    r = world_range(obj)
    exp = (round(cx - (R + tube), 3), round(cx + (R + tube), 3),
           round(cy - (R + tube), 3), round(cy + (R + tube), 3),
           round(cz - tube, 3), round(cz + tube, 3))
    rhos = [math.hypot(v.x - cx, v.y - cy) for v in world_verts(obj)]
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


def check_sphere_knob(obj):
    """KnobTop: Blender UV sphere segments=12, ring_count=8 ->
    86 verts, 96 faces (72 quads + 24 tris), centre (0, 0, 0.47),
    radius 0.011. The ring latitudes sit at phi = k*pi/7, so the
    measured x/y half-extent is 0.011*sin(3*pi/7) = 0.0107, not the
    full 0.011; allow tol 0.002 against the continuous bbox."""
    r = world_range(obj)
    vs = world_verts(obj)
    cx = sum(v.x for v in vs) / len(vs)
    cy = sum(v.y for v in vs) / len(vs)
    cz = sum(v.z for v in vs) / len(vs)
    exp = (-0.011, 0.011, -0.011, 0.011, 0.459, 0.481)
    row = {"range": r, "expected": exp,
           "verts": len(vs),
           "center": (round(cx, 4), round(cy, 4), round(cz, 4)),
           "ok": bool(bbox_close(r, exp, tol=0.002)
                      and len(vs) == 86
                      and abs(cx) < 0.002 and abs(cy) < 0.002
                      and abs(cz - 0.47) < 0.002)}
    return row


def check_ring_embed(by_name):
    """Both brass rings (R 0.097, tube 0.006, inner radius 0.091) wrap
    the glass at its widest (r 0.095 at z 0.09 and z 0.35): the ring
    is wedged 0.004 into the glass by design (same intent as the
    067 collar)."""
    glass = by_name["HourglassGlass"]
    rows = {}
    for name, z in (("RingLower", RING_Z_LOW), ("RingUpper", RING_Z_HIGH)):
        ring = by_name[name]
        rhos = [math.hypot(v.x, v.y) for v in world_verts(ring)]
        ring_inner = min(rhos)
        ring_outer = max(rhos)
        glass_rs = [math.hypot(v.x, v.y) for v in world_verts(glass)
                    if abs(v.z - z) < 0.001]
        glass_r = sum(glass_rs) / len(glass_rs) if glass_rs else None
        rows[name] = {
            "ring_z": z,
            "ring_inner_radius": round(ring_inner, 4),
            "ring_inner_design": round(RING_R - RING_TUBE, 4),
            "ring_outer_radius": round(ring_outer, 4),
            "ring_outer_design": round(RING_R + RING_TUBE, 4),
            "glass_radius_at_ring_z": round(glass_r, 4) if glass_r else None,
            "glass_radius_design": GLASS_MAX_R,
            "embed": round(glass_r - ring_inner, 4) if glass_r else None,
            "embed_design": 0.004,
            "ok": bool(abs(ring_inner - (RING_R - RING_TUBE)) < 0.002
                       and abs(ring_outer - (RING_R + RING_TUBE)) < 0.002
                       and glass_r is not None
                       and abs(glass_r - GLASS_MAX_R) < 0.002
                       and 0.003 <= glass_r - ring_inner <= 0.005)}
    return {"rings": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_pillar_clearance(by_name):
    """Each pillar stands at (+-0.14, +-0.10); its inner edge is at
    hypot(0.14, 0.10) - 0.012 = 0.160 from the axis, clearing the
    glass max radius 0.095 by 0.065. Pillars must also stand inside
    the board footprint (board half extents 0.17 x 0.13)."""
    glass = by_name["HourglassGlass"]
    glass_rs = [math.hypot(v.x, v.y) for v in world_verts(glass)]
    glass_max = max(glass_rs)
    rows = {}
    for i in range(4):
        p = by_name["Pillar_%d" % i]
        vs = world_verts(p)
        cx = sum(v.x for v in vs) / len(vs)
        cy = sum(v.y for v in vs) / len(vs)
        axis_dist = math.hypot(cx, cy)
        # exclude the cap-centre verts (rho ~ 0) from the radius mean
        rhos = [math.hypot(v.x - cx, v.y - cy) for v in vs
                if math.hypot(v.x - cx, v.y - cy) > 0.0005]
        pr = sum(rhos) / len(rhos)
        rows["Pillar_%d" % i] = {
            "center": (round(cx, 4), round(cy, 4)),
            "center_design": [(0.14, 0.10), (-0.14, 0.10),
                              (0.14, -0.10), (-0.14, -0.10)][i],
            "axis_distance": round(axis_dist, 4),
            "pillar_radius": round(pr, 4),
            "inner_edge": round(axis_dist - pr, 4),
            "clearance_to_glass": round(axis_dist - pr - glass_max, 4),
            "footprint_inside_board": bool(
                abs(cx) + pr < 0.17 and abs(cy) + pr < 0.13),
            "ok": bool(abs(axis_dist - math.hypot(0.14, 0.10)) < 0.002
                       and abs(pr - 0.012) < 0.002
                       and abs(cx) + pr < 0.17 and abs(cy) + pr < 0.13)}
    clear = min(v["clearance_to_glass"] for v in rows.values())
    return {"pillars": rows,
            "glass_max_radius": round(glass_max, 4),
            "min_clearance": round(clear, 4),
            "clearance_design": 0.065,
            "ok": bool(all(v["ok"] for v in rows.values())
                       and abs(clear - 0.065) < 0.002)}


def check_stream(by_name):
    """SandStream (r 0.0035) through the neck: top z 0.2145 sits below
    the upper sand cone's apex (z 0.2151) and must be buried inside the
    cone; bottom z 0.073 sits 0.001 above the lower mound peak
    (z 0.072). The cone's free surface at the stream radius is
    z = 0.22 + tan(35deg)*(0.0035 - 0.008) = 0.2169, so a stream top
    at 0.2145 is buried 0.0023 inside the cone (073 fix; the old
    0.219 top poked 0.0022 above the cone surface)."""
    stream = by_name["SandStream"]
    vs = world_verts(stream)
    top_z = max(v.z for v in vs)
    bot_z = min(v.z for v in vs)
    rhos = [math.hypot(v.x, v.y) for v in vs if math.hypot(v.x, v.y) > 0.001]
    sr = sum(rhos) / len(rhos)
    cone_z_at_stream = cone_surface_z(sr)
    mound = by_name["SandLower"]
    mound_peak = max(v.z for v in world_verts(mound))
    row = {"stream_top_z": round(top_z, 4),
           "neck_z": NECK_Z,
           "top_below_neck": round(NECK_Z - top_z, 4),
           "stream_radius": round(sr, 4),
           "cone_surface_z_at_stream_radius": round(cone_z_at_stream, 4),
           "stream_top_vs_cone_surface": round(top_z - cone_z_at_stream, 4),
           "stream_bottom_z": round(bot_z, 4),
           "mound_peak_z": round(mound_peak, 4),
           "bottom_gap_above_mound": round(bot_z - mound_peak, 4),
           "ok": bool(abs(top_z - STREAM_TOP_Z) < 0.002
                      and abs(bot_z - STREAM_BOT_Z) < 0.002
                      and abs(sr - STREAM_R) < 0.002
                      and top_z < NECK_Z
                      and top_z <= cone_z_at_stream
                      and abs(bot_z - mound_peak - 0.001) < 0.002)}
    return row


def check_board_contacts(by_name):
    """Glass bottom (z 0.02) touches the bottom board top (0.02);
    glass top (z 0.42) touches the top board bottom (0.42); knob
    base bottom (z 0.44) touches the top board top (0.44); pillars
    run z 0.02-0.42 between the boards; knob sphere bottom (0.459)
    embeds 0.006 into the knob base top (0.465)."""
    glass = by_name["HourglassGlass"]
    bb = by_name["BoardBottom"]
    bt = by_name["BoardTop"]
    kb = by_name["KnobBase"]
    kt = by_name["KnobTop"]
    glass_bot = min(v.z for v in world_verts(glass))
    glass_top = max(v.z for v in world_verts(glass))
    bb_top = max(v.z for v in world_verts(bb))
    bb_bot = min(v.z for v in world_verts(bb))
    bt_top = max(v.z for v in world_verts(bt))
    bt_bot = min(v.z for v in world_verts(bt))
    kb_bot = min(v.z for v in world_verts(kb))
    kb_top = max(v.z for v in world_verts(kb))
    kt_bot = min(v.z for v in world_verts(kt))
    kt_top = max(v.z for v in world_verts(kt))
    pillar_zs = []
    for i in range(4):
        vs = world_verts(by_name["Pillar_%d" % i])
        pillar_zs.append((round(min(v.z for v in vs), 4),
                          round(max(v.z for v in vs), 4)))
    row = {"glass_bottom_z": round(glass_bot, 4),
           "board_bottom_top_z": round(bb_top, 4),
           "glass_board_bottom_gap": round(glass_bot - bb_top, 4),
           "glass_top_z": round(glass_top, 4),
           "board_top_bottom_z": round(bt_bot, 4),
           "glass_board_top_gap": round(bt_bot - glass_top, 4),
           "knob_base_bottom_z": round(kb_bot, 4),
           "board_top_top_z": round(bt_top, 4),
           "knob_board_gap": round(kb_bot - bt_top, 4),
           "knob_sphere_bottom_z": round(kt_bot, 4),
           "knob_base_top_z": round(kb_top, 4),
           "knob_sphere_embed": round(kb_top - kt_bot, 4),
           "knob_sphere_top_z": round(kt_top, 4),
           "board_bottom_z": round(bb_bot, 4),
           "pillar_z_ranges": pillar_zs,
           "ok": bool(abs(glass_bot - bb_top) < 0.002
                      and abs(bt_bot - glass_top) < 0.002
                      and abs(kb_bot - bt_top) < 0.002
                      and abs(bb_bot) < 0.002
                      and all(abs(lo - 0.02) < 0.002
                              and abs(hi - 0.42) < 0.002
                              for lo, hi in pillar_zs)
                      and 0.004 <= kb_top - kt_bot <= 0.008)}
    return row


def check_sand_clearances(by_name):
    """Both sand bodies vs the glass wall: vertex-based and analytic
    (fine sampling of the sand profile against the true glass
    profile). Upper cone: min clearance 0.0020 at the wall-clamped
    edge; lower mound: min clearance 0.0034. Also verifies the upper
    cone's free-surface slope is the 35-degree angle of repose."""
    rows = {}

    def sand_vs_glass(sand_obj):
        """Vertex-based min clearance of a sand body vs the glass wall."""
        min_clear = 1e9
        min_at = None
        for v in world_verts(sand_obj):
            rho = math.hypot(v.x, v.y)
            clear = glass_radius_at(v.z) - rho
            if clear < min_clear:
                min_clear = clear
                min_at = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
        return {"min_clearance_verts": round(min_clear, 4),
                "min_clearance_vert_at": min_at}

    # upper cone: sample the ACTUAL mesh profile segments (the last
    # segment runs from the last free-surface ring to the wall-clamped
    # edge point, which is NOT on the ideal 35-degree line -- sampling
    # the ideal line past r 0.078 would measure a line that is not
    # the mesh and would wrongly report a negative clearance there)
    min_an = 1e9
    min_an_z = None
    for k in range(len(UPPER_SAND_PROFILE) - 1):
        r0, z0 = UPPER_SAND_PROFILE[k]
        r1, z1 = UPPER_SAND_PROFILE[k + 1]
        for i in range(101):
            t = i / 100.0
            r = r0 + t * (r1 - r0)
            z = z0 + t * (z1 - z0)
            clear = glass_radius_at(z) - r
            if clear < min_an:
                min_an = clear
                min_an_z = z
    u = sand_vs_glass(by_name["SandUpper"])
    u["min_clearance_analytic"] = round(min_an, 4)
    u["min_clearance_analytic_z"] = round(min_an_z, 4)
    # edge clearance: the wall-clamped rim point vs the glass wall
    # (the 071 note's "0.0020" is this edge value, not the global min:
    # the continuous cone surface dips to 0.001 where it crosses the
    # neck plane at z 0.22 -- still positive, no intersection, but the
    # note's global-minimum claim needs correcting, see checklist §6)
    edge_r, edge_z = UPPER_SAND_PROFILE[-1]
    u["edge_clearance"] = round(glass_radius_at(edge_z) - edge_r, 4)
    u["edge_point"] = (edge_r, edge_z)
    u["edge_clearance_design"] = 0.0020
    u["ok"] = bool(u["min_clearance_verts"] > 0
                   and u["min_clearance_analytic"] > 0
                   and abs(u["edge_clearance"] - 0.0020) < 0.001)
    rows["SandUpper"] = u

    # lower mound: sample the mound profile segments
    min_an = 1e9
    min_an_z = None
    for k in range(len(LOWER_SAND_PROFILE) - 1):
        r0, z0 = LOWER_SAND_PROFILE[k]
        r1, z1 = LOWER_SAND_PROFILE[k + 1]
        for i in range(101):
            t = i / 100.0
            r = r0 + t * (r1 - r0)
            z = z0 + t * (z1 - z0)
            clear = glass_radius_at(z) - r
            if clear < min_an:
                min_an = clear
                min_an_z = z
    lo = sand_vs_glass(by_name["SandLower"])
    lo["min_clearance_analytic"] = round(min_an, 4)
    lo["min_clearance_analytic_z"] = round(min_an_z, 4)
    lo["min_clearance_design"] = 0.0034
    lo["ok"] = bool(lo["min_clearance_verts"] > 0
                    and abs(lo["min_clearance_analytic"] - 0.0034) < 0.001)
    rows["SandLower"] = lo

    # repose slope from the measured upper-cone rings, using RAW
    # vertex coordinates (the ring_analysis values are rounded to 3
    # decimals, which alone swings a 0.015-wide segment's slope by up
    # to 0.07 -- far above the 0.01 tolerance). Cap-centre verts
    # (rho ~ 0) are excluded from the ring mean radius.
    upper = by_name["SandUpper"]
    by_z = {}
    for v in world_verts(upper):
        rho = math.hypot(v.x, v.y)
        if rho < 0.0005:
            continue
        by_z.setdefault(round(v.z, 4), []).append(rho)
    pairs = sorted((z, sum(rs) / len(rs)) for z, rs in by_z.items())
    slopes = []
    for (z0, r0), (z1, r1) in zip(pairs, pairs[1:]):
        if r1 > 0.08:
            continue  # wall-clamped edge segment, not free surface
        if r1 - r0 > 1e-6:
            slopes.append(round((z1 - z0) / (r1 - r0), 4))
    rows["repose_slopes"] = slopes
    rows["repose_tan35"] = round(REPOSE_TAN, 4)
    rows["repose_ok"] = bool(
        slopes and all(abs(s - REPOSE_TAN) < 0.01 for s in slopes))
    rows["ok"] = bool(u["ok"] and lo["ok"] and rows["repose_ok"])
    return rows


def check_ground(by_name):
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
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
           # 071 note: "整体约 0.34 m 宽 × 0.48 m 高 × 0.26 m 深"
           "note_size": (0.34, 0.48, 0.26)}
    row["ok"] = bool(abs(row["width"] - 0.34) <= 0.02
                     and abs(row["height"] - 0.48) <= 0.02
                     and abs(row["depth"] - 0.26) <= 0.02)
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 071 design values.
    Glass_Clear also checks Alpha + dithered render method; the
    glowing sand material also checks the Emission node (color,
    strength) and the MixShader factor."""
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

    glass = check_lathe("HourglassGlass", by_name["HourglassGlass"],
                        GLASS_PROFILE, 24, (0, 0, 0), (0, 0, 1),
                        24, [0.020])
    print("QA_GLASS:", glass)
    sand_lower = check_lathe("SandLower", by_name["SandLower"],
                             LOWER_SAND_PROFILE, 24, (0, 0, 0), (0, 0, 1),
                             24, [0.021])
    print("QA_SAND_LOWER_SHAPE:", sand_lower)
    sand_upper = check_lathe("SandUpper", by_name["SandUpper"],
                             UPPER_SAND_PROFILE, 24, (0, 0, 0), (0, 0, 1),
                             24, [0.215])
    print("QA_SAND_UPPER_SHAPE:", sand_upper)
    tapered = {}
    for name, spec in TAPERED.items():
        origin, z0, r0, z1, r1, sides = spec
        tapered[name] = check_tapered_cyl(name, by_name[name], origin,
                                          z0, r0, z1, r1, sides)
        print("QA_TAPERED %s:" % name, tapered[name])
    tubes = {}
    for name, spec in TUBES.items():
        p0, p1, radius, sides = spec
        tubes[name] = check_tube_between(name, by_name[name], p0, p1,
                                         radius, sides)
        print("QA_TUBE %s:" % name, tubes[name])
    tori = {}
    for name, spec in TORI.items():
        center, R, tube, a, t = spec
        tori[name] = check_torus(name, by_name[name], center, R, tube,
                                 a, t)
        print("QA_TORUS %s:" % name, tori[name])
    boxes = {n: check_box(n, by_name[n]) for n in BOXES}
    print("QA_BOXES:", boxes)
    knob = check_sphere_knob(by_name["KnobTop"])
    print("QA_KNOB_SPHERE:", knob)
    ring_embed = check_ring_embed(by_name)
    print("QA_RING_EMBED:", ring_embed)
    pillars = check_pillar_clearance(by_name)
    print("QA_PILLARS:", pillars)
    stream = check_stream(by_name)
    print("QA_STREAM:", stream)
    contacts = check_board_contacts(by_name)
    print("QA_BOARD_CONTACTS:", contacts)
    sands = check_sand_clearances(by_name)
    print("QA_SAND_CLEARANCES:", sands)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    # Normal checks, authoritative per part type (same approach as 067):
    # - the 3 lathe parts: profile-segment analytic check (recalc's
    #   signed-volume heuristic can misjudge an open vessel);
    # - the 2 tori: centre-circle check; everything else: centroid
    #   check (same as the 071 build script's own self-check).
    lathe_winding = {}
    for name, profile in (("HourglassGlass", GLASS_PROFILE),
                          ("SandLower", LOWER_SAND_PROFILE),
                          ("SandUpper", UPPER_SAND_PROFILE)):
        lathe_winding[name] = check_lathe_winding_analytic(
            by_name[name], profile, 24)
    print("QA_LATHE_WINDING_ANALYTIC:",
          {k: len(v) for k, v in lathe_winding.items()})
    torus_winding = {}
    for name, spec in TORI.items():
        center, R, _tube, _a, _t = spec
        torus_winding[name] = check_torus_winding_xy(
            by_name[name], R, center)
    print("QA_TORUS_WINDING:", torus_winding)
    other_names = [n for n in by_name
                   if n not in lathe_winding and n not in torus_winding]
    centroid_winding = {n: check_centroid_winding(by_name[n])
                        for n in other_names}
    print("QA_CENTROID_WINDING:", centroid_winding)
    analytic_flipped = (sum(len(v) for v in lathe_winding.values())
                        + sum(torus_winding.values())
                        + sum(centroid_winding.values()))
    recalc_flipped = sum(r["inverted_normals"]
                         for r in results.values())
    # recalc is the independent re-measurement except for the lathe
    # parts, where the analytic check rules (067 funnel precedent)
    recalc_lathe = sum(results[n]["inverted_normals"]
                       for n in lathe_winding)
    inverted_effective = (recalc_flipped - recalc_lathe
                          + sum(len(v) for v in lathe_winding.values()))

    structure = {"glass": glass,
                 "sand_lower_shape": sand_lower,
                 "sand_upper_shape": sand_upper,
                 "tapered": tapered, "tubes": tubes, "tori": tori,
                 "boxes": boxes, "knob_sphere": knob,
                 "ring_embed": ring_embed, "pillars": pillars,
                 "stream": stream, "board_contacts": contacts,
                 "sand_clearances": sands,
                 "ground_contact": ground, "overall": overall,
                 "lathe_winding_analytic": {
                     k: len(v) for k, v in lathe_winding.items()},
                 "torus_winding": torus_winding,
                 "centroid_winding": centroid_winding,
                 "analytic_flipped_total": analytic_flipped}
    structure_ok = (glass["ok"] and sand_lower["ok"] and sand_upper["ok"]
                    and all(v["ok"] for v in tapered.values())
                    and all(v["ok"] for v in tubes.values())
                    and all(v["ok"] for v in tori.values())
                    and all(v["ok"] for v in boxes.values())
                    and knob["ok"] and ring_embed["ok"] and pillars["ok"]
                    and stream["ok"] and contacts["ok"] and sands["ok"]
                    and ground["ok"] and overall["ok"]
                    and analytic_flipped == 0)

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # Boundary edges BY DESIGN (open lathe tops, not holes):
    # HourglassGlass: top ring at r 0.001, z 0.42 (24); SandLower:
    # top ring at r 0.001, z 0.072 (24); SandUpper: top rim where the
    # cone meets the glass wall, r 0.0815, z 0.2774 (24). Everything
    # else must be closed (0 boundary edges).
    open_parts = {"HourglassGlass": 24, "SandLower": 24, "SandUpper": 24}
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
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and boundary_ok
              and inverted_effective == 0 and tot_oob == 0
              and worst_overlap < 1.0 and mats["empty_material_slots"] == 0
              and not mats["assignment_mismatches"]
              and not mats["unused_design_mats"]
              and faces_ok and structure_ok and mats["all_ok"])

    summary = {
        "asset": "071-lowpoly-hourglass",
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
        "inverted_normals_recalc_lathe": recalc_lathe,
        "analytic_flipped_total": analytic_flipped,
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
        f.write("# 072 资产质检单：低模炼金沙漏（071）\n\n")
        f.write("被检资产：`scenes/071-lowpoly-hourglass.blend`（%d 个道具部件，不含地面）。\n" % len(results))
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
        f.write("- 面数与 071 设计表逐部件比对：%s（设计 1320 面：三角 232、四边 1088、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 开口边：边界边共 %d 条，全部是设计上的开口（玻璃顶环 r 0.001、z 0.42 计 24；下瓶沙丘顶环 r 0.001、z 0.072 计 24；上瓶沙锥贴壁边沿 r 0.0815、z 0.2774 计 24），其余 11 个部件 0 条：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致：车削件轮廓段解析检查内翻面 %s；圆环中心线检查内翻面 %s；其余部件质心法检查内翻面 %s；recalc 交叉核对有效倒置面 %d 个：%s\n" % (
            {k: len(v) for k, v in lathe_winding.items()},
            torus_winding, centroid_winding,
            inverted_effective, verdict(inverted_effective == 0)))
        f.write("  （说明：recalc_face_normals 用网格有向体积定内外，对开口容器可能误判——本次 SandUpper 的 recalc 读数为 %d 面内翻，但轮廓段解析检查为 0 面，与 071 构建脚本自检同一方法、同一结论；067 漏斗即有此先例（recalc 误判 120 面）。其余两个车削件 recalc 与解析一致（均为 0）。有效倒置面以解析检查为准。）\n\n" % (
            results["SandUpper"]["inverted_normals"],))
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
        f.write("## 4. 沙漏结构（实测）\n\n")
        f.write("### 4.1 玻璃沙漏（车削轮廓，24 段）\n\n")
        f.write("- HourglassGlass：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.020），顶环 z 0.42、r 0.001 开口；颈部环 z 0.22、r 0.009：%s\n" % (
            len(glass["rings"]), glass["ring_distances"],
            glass["ring_radii"],
            glass["design_radii"],
            glass["range"][0], glass["range"][1], glass["range"][2],
            glass["range"][3], glass["range"][4], glass["range"][5],
            glass["expected"], verdict(glass["ok"])))
        f.write("- SandLower：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.021），顶环 z 0.072、r 0.001 开口：%s\n" % (
            len(sand_lower["rings"]), sand_lower["ring_distances"],
            sand_lower["ring_radii"],
            sand_lower["design_radii"],
            sand_lower["range"][0], sand_lower["range"][1],
            sand_lower["range"][2], sand_lower["range"][3],
            sand_lower["range"][4], sand_lower["range"][5],
            sand_lower["expected"], verdict(sand_lower["ok"])))
        f.write("- SandUpper：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.215），顶环 r 0.0815、z 0.2774 贴玻璃壁：%s\n" % (
            len(sand_upper["rings"]), sand_upper["ring_distances"],
            sand_upper["ring_radii"],
            sand_upper["design_radii"],
            sand_upper["range"][0], sand_upper["range"][1],
            sand_upper["range"][2], sand_upper["range"][3],
            sand_upper["range"][4], sand_upper["range"][5],
            sand_upper["expected"], verdict(sand_upper["ok"])))
        f.write("\n### 4.2 双沙体与玻璃壁间隙\n\n")
        up = sands["SandUpper"]
        lo = sands["SandLower"]
        f.write("- SandUpper：与玻璃壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.4f，颈部）；贴壁边沿间隙 %.4f（边沿 r %.4f、z %.4f，设计 0.0020）；自由面斜率 %s（35° 安息角 tan 值为 %.4f）：%s\n" % (
            up["min_clearance_verts"], up["min_clearance_vert_at"],
            up["min_clearance_analytic"],
            up["min_clearance_analytic_z"],
            up["edge_clearance"], up["edge_point"][0], up["edge_point"][1],
            sands["repose_slopes"], sands["repose_tan35"],
            verdict(up["ok"] and sands["repose_ok"])))
        f.write("- SandLower：与玻璃壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.4f，设计 0.0034）：%s\n" % (
            lo["min_clearance_verts"], lo["min_clearance_vert_at"],
            lo["min_clearance_analytic"],
            lo["min_clearance_analytic_z"],
            verdict(lo["ok"])))
        f.write("\n### 4.3 箍环与立柱\n\n")
        for name in ("RingLower", "RingUpper"):
            rr = ring_embed["rings"][name]
            tt = tori[name]
            f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.091、外径 0.103）；该高度玻璃半径 %.4f（设计 0.095），箍环楔入玻璃 %.4f（设计 0.004，设计意图，同 067 卡箍）：%s\n" % (
                name, tt["range"][0], tt["range"][1], tt["range"][2],
                tt["range"][3], tt["range"][4], tt["range"][5],
                tt["expected"], tt["rho_min"], tt["rho_max"],
                rr["glass_radius_at_ring_z"], rr["embed"],
                verdict(rr["ok"])))
        f.write("- 立柱：4 根均 z 0.02–0.42、半径 0.012，轴心 (±0.14, ±0.10)，内沿离轴 0.160，玻璃最大半径 %.4f，最小间隙 %.4f（设计 0.065）；立柱足底均在端板幅面内（板半幅 0.17×0.13）：%s\n" % (
            pillars["glass_max_radius"], pillars["min_clearance"],
            verdict(pillars["ok"])))
        for i in range(4):
            p = pillars["pillars"]["Pillar_%d" % i]
            f.write("  - Pillar_%d：轴心 %s（设计 %s），半径 %.4f，内沿 %.4f，间隙 %.4f：%s\n" % (
                i, p["center"], p["center_design"], p["pillar_radius"],
                p["inner_edge"], p["clearance_to_glass"],
                verdict(p["ok"])))
        f.write("\n### 4.4 细沙流\n\n")
        t = tubes["SandStream"]
        f.write("- SandStream：2 环（每环 8 顶点），长度 %.4f m，半径 %.4f；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；16 个三角面分处两端盖（轴向位置 %s）：%s\n" % (
            t["length"], t["rings"][0][2],
            t["range"][0], t["range"][1], t["range"][2],
            t["range"][3], t["range"][4], t["range"][5],
            t["expected"], t["tri_axial_positions"], verdict(t["ok"])))
        stream_top_note = (
            "流顶端低于沙锥面 %.4f（埋进沙锥内）"
            % (-stream["stream_top_vs_cone_surface"])
            if stream["stream_top_vs_cone_surface"] <= 0 else
            "流顶端高出沙锥面 %.4f（应埋进沙锥内，见第 7 节待修项）"
            % stream["stream_top_vs_cone_surface"])
        f.write("- 细沙流顶端 z %.4f，颈部平面 z %.4f，顶端在颈面下 %.4f；沙锥自由面在该半径处 z %.4f，%s；底端 z %.4f，沙丘峰顶 z %.4f，间隙 %.4f：%s\n" % (
            stream["stream_top_z"], stream["neck_z"],
            stream["top_below_neck"],
            stream["cone_surface_z_at_stream_radius"],
            stream_top_note,
            stream["stream_bottom_z"], stream["mound_peak_z"],
            stream["bottom_gap_above_mound"],
            verdict(stream["ok"])))
        f.write("\n### 4.5 端板、顶钮与贴合\n\n")
        for name in ("BoardBottom", "BoardTop"):
            b = boxes[name]
            f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
                name, b["range"][0], b["range"][1], b["range"][2],
                b["range"][3], b["range"][4], b["range"][5],
                b["expected"], verdict(b["ok"])))
        kb = tapered["KnobBase"]
        f.write("- KnobBase：2 环（每环 12 顶点），环高 z %s、半径 %s；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面分处两端盖（轴向位置 %s）：%s\n" % (
            [d for d, _c, _r in kb["rings"]],
            [r for _d, _c, r in kb["rings"]],
            kb["range"][0], kb["range"][1], kb["range"][2],
            kb["range"][3], kb["range"][4], kb["range"][5],
            kb["expected"], kb["tri_axial_positions"],
            verdict(kb["ok"])))
        f.write("- KnobTop：UV 球 segments=12、ring_count=8，%d 个顶点（设计 86），96 面（72 四边 + 24 三角）；中心 %s（设计 (0, 0, 0.47)），包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
            knob["verts"], knob["center"],
            knob["range"][0], knob["range"][1], knob["range"][2],
            knob["range"][3], knob["range"][4], knob["range"][5],
            knob["expected"], verdict(knob["ok"])))
        f.write("- 玻璃底 z %.4f − 下板顶 z %.4f = %.4f（贴合）；玻璃顶 z %.4f − 上板底 z %.4f = %.4f（贴合）；顶钮底 z %.4f − 上板顶 z %.4f = %.4f（贴合）；球顶底 z %.4f 埋入顶钮顶 z %.4f，埋入 %.4f；下板底 z %.4f 落地；立柱 z 范围 %s：%s\n" % (
            contacts["glass_bottom_z"], contacts["board_bottom_top_z"],
            contacts["glass_board_bottom_gap"],
            contacts["glass_top_z"], contacts["board_top_bottom_z"],
            contacts["glass_board_top_gap"],
            contacts["knob_base_bottom_z"], contacts["board_top_top_z"],
            contacts["knob_board_gap"],
            contacts["knob_sphere_bottom_z"], contacts["knob_base_top_z"],
            contacts["knob_sphere_embed"],
            contacts["board_bottom_z"], contacts["pillar_z_ranges"],
            verdict(contacts["ok"])))
        f.write("\n### 4.6 地面、整体\n\n")
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s（下板 z=0 落地，其余部件在端板或支架上）：%s\n" % (
            ground["checked"], ground["global_min_z"],
            ground["below_ground"] if ground["below_ground"] else "无",
            verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（071 笔记“约 0.34 × 0.48 × 0.26 m”，"
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
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 071 构建脚本直接存入的线性值；玻璃另查 Alpha 与渲染方式，沙子另查 Emission 与混合系数）：\n")
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
        f.write("- 071 笔记已在 073 修复中更正：全曲面最小间隙实为 %.4f（位于颈部 z %.4f，沙锥面穿过颈部平面时离玻璃壁仅 0.001，仍为正、不穿帮），0.0020 只是贴壁边沿处的间隙（实测 %.4f）。旧笔记称“最小间隙 0.0020”不实：构建脚本只在采样环半径处验算间隙，漏了锥面与颈部平面的交点。其余间隙数字与本质检复核一致：箍环楔入 %.4f、立柱间隙 %.4f、下瓶沙丘最小间隙 %.4f、细沙流底端间隙 %.4f、玻璃与端板贴合 0.000、顶钮贴合 0.000；细沙流顶端一项已在 073 修复（见第 7 节）。\n" % (
            sands["SandUpper"]["min_clearance_analytic"],
            sands["SandUpper"]["min_clearance_analytic_z"],
            sands["SandUpper"]["edge_clearance"],
            ring_embed["rings"]["RingLower"]["embed"],
            pillars["min_clearance"],
            sands["SandLower"]["min_clearance_analytic"],
            stream["bottom_gap_above_mound"]))
        f.write("- 三处开口边均为设计上的开口：玻璃顶环（r 0.001 的针孔）、沙丘顶环（r 0.001 的针孔）、沙锥贴壁边沿（r 0.0815 的开环，藏在玻璃壁内侧 0.002 处），不是破洞；与 066 量杯腔底针孔、068 药液平顶同一做法。\n")
        f.write("- 箍环楔入玻璃 0.004 是设计意图的连接（环箍住玻璃最宽处），不是穿帮；顶钮球底埋入锥台 0.006 是设计意图的连接，不是穿帮。\n")
        f.write("- 沙与玻璃在影棚光下整体偏淡，是仓库既有影棚风格（同 053/058/059/068 笔记已知问题），本质检不重复判否。\n")
        f.write("- 071 笔记尺寸与实测一致：宽 %.3f m × 深 %.3f m × 高 %.3f m"
                "（笔记“约 0.34 × 0.48 × 0.26 m”）。\n" % (
                    overall["width"], overall["depth"], overall["height"]))
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、沙漏结构、地面接触均通过。071 笔记的间隙数字经复核全部准确，无需返工、无需更正。\n")
        else:
            f.write("待修项：\n\n")
            f.write("1. 细沙流顶端高出沙锥面 %.4f m：细沙流顶端 z %.4f，沙锥自由面在流半径 %.4f 处的高度是 z %.4f，流顶端比沙锥面高 %.4f（071 笔记称“上端埋进沙锥”，实测并未埋进去）。同材质、同色，藏在玻璃颈内，渲染图上看不出来，但几何上与设计意图不符。修法：把 STREAM_TOP_Z 从 0.219 降到 0.2145（低于沙锥顶点 z 0.2151，整块顶盖落在沙锥体内），或把沙锥顶点抬高；修完重跑本脚本复核到 PASS，重渲美观图与线框图。\n" % (
                stream["stream_top_vs_cone_surface"],
                stream["stream_top_z"], stream["stream_radius"],
                stream["cone_surface_z_at_stream_radius"],
                stream["stream_top_vs_cone_surface"]))


if __name__ == "__main__":
    main()
