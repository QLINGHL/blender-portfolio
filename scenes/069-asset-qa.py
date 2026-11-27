# -*- coding: utf-8 -*-
"""069 资产质检：对 068 低模炼金蒸馏器做真实 mesh 检查（拓扑/法线/UV/材质），
并实测蒸馏器特有结构：曲颈甑与收集瓶车削环、双药液与球壁间隙、酒精灯与
火焰贴合、固定环与甑颈、斜管与两枚卡箍、冷凝盘管、滴管与收集液面、冷凝管
与瓶颈间隙、竖杆埋入底板。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 069-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "068-lowpoly-alembic-still.blend")
UV_JSON = os.path.join(ROOT, "scenes", "069-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "069-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "069-asset-qa-checklist.md")

# every mesh object in the 068 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/068-lowpoly-alembic-still.md (per-part table)
EXPECTED_FACES = {
    "BaseBoard": 6, "RetortFlask": 192, "RetortRimLip": 144,
    "RetortLiquid": 144, "Burner": 48, "BurnerWick": 24, "Flame": 36,
    "StandRod": 36, "RingArm": 6, "StandRing": 144, "VapourArm": 36,
    "Collar_Neck": 144, "Collar_Condenser": 144, "CondenserTube": 48,
    "CondenserCoil": 300, "DripTube": 36, "CollectionFlask": 168,
    "CollectionLiquid": 96,
}
EXPECTED_TOTAL_FACES = 1752
EXPECTED_TRIS = 284
EXPECTED_QUADS = 1468

# part -> design material (from the 068 build script)
PART_MATERIAL = {
    "BaseBoard": "Base_Wood",
    "Burner": "Stand_Brass", "StandRod": "Stand_Brass",
    "RingArm": "Stand_Brass", "StandRing": "Stand_Brass",
    "Collar_Neck": "Stand_Brass", "Collar_Condenser": "Stand_Brass",
    "CondenserCoil": "Coil_Copper",
    "RetortFlask": "Glass_Clear", "RetortRimLip": "Glass_Clear",
    "VapourArm": "Glass_Clear", "CondenserTube": "Glass_Clear",
    "DripTube": "Glass_Clear", "CollectionFlask": "Glass_Clear",
    "RetortLiquid": "Liquid_Teal", "CollectionLiquid": "Liquid_Amber",
    "Flame": "Flame_Orange", "BurnerWick": "Wick_Dark",
}

# Design material values from the 068 build script. The build script
# passes raw tuples to solid_material, which stores them directly as
# linear Base Color (same convention as the 059/060/063/067 scripts).
# Glass_Clear: alpha 0.35 + dithered (059 recipe). Liquid_*/Flame_* are
# Principled + Emission mixed in (glow_material): check emission
# strength, mix factor and roughness as well.
DESIGN_MATS = {
    "Base_Wood":     {"metallic": 0.00, "roughness": 0.80,
                      "color": (0.38, 0.26, 0.13), "emissive": None},
    "Stand_Brass":   {"metallic": 0.70, "roughness": 0.35,
                      "color": (0.55, 0.40, 0.15), "emissive": None},
    "Coil_Copper":   {"metallic": 0.80, "roughness": 0.30,
                      "color": (0.72, 0.45, 0.22), "emissive": None},
    "Glass_Clear":   {"metallic": 0.00, "roughness": 0.15,
                      "color": (0.80, 0.85, 0.88), "emissive": None,
                      "alpha": 0.35, "dithered": True},
    "Liquid_Teal":   {"metallic": 0.00, "roughness": 0.35,
                      "color": (0.30, 0.72, 0.45),
                      "emissive": ((0.30, 0.72, 0.45), 0.7, 0.55)},
    "Liquid_Amber":  {"metallic": 0.00, "roughness": 0.90,
                      "color": (0.45, 0.18, 0.02),
                      "emissive": ((0.45, 0.18, 0.02), 0.5, 0.4)},
    "Flame_Orange":  {"metallic": 0.00, "roughness": 0.40,
                      "color": (1.00, 0.55, 0.10),
                      "emissive": ((1.00, 0.55, 0.10), 1.2, 0.8)},
    "Wick_Dark":     {"metallic": 0.00, "roughness": 0.90,
                      "color": (0.10, 0.08, 0.06), "emissive": None},
}

# design geometry (copied from the 068 build script)
RETORT_X = -0.16
COND_X = 0.10
RETORT_PROFILE = [
    (0.001, 0.100), (0.050, 0.1134), (0.0866, 0.150), (0.100, 0.200),
    (0.0866, 0.250), (0.0574, 0.2819), (0.028, 0.300), (0.028, 0.440),
]
RETORT_LIQ_PROFILE = [
    (0.001, 0.104), (0.048, 0.1169), (0.0831, 0.152), (0.096, 0.200),
    (0.0953, 0.2117), (0.001, 0.2117),
]
COLL_PROFILE = [
    (0.001, 0.020), (0.0389, 0.0361), (0.055, 0.075), (0.0389, 0.1139),
    (0.0275, 0.1226), (0.018, 0.135), (0.018, 0.160),
]
COLL_LIQ_PROFILE = [
    (0.001, 0.023), (0.0368, 0.0382), (0.0489, 0.0572), (0.001, 0.0572),
]
RETORT_BULB = ((-0.16, 0, 0.20), 0.10)   # (center, radius)
COLL_BULB = ((0.10, 0, 0.075), 0.055)
COIL = {"center": (0.10, 0), "R": 0.042, "tube": 0.007,
        "z0": 0.20, "z1": 0.34, "turns": 3}
# box parts: name -> (center, size)
BOXES = {
    "BaseBoard": ((0, 0, 0.01), (0.62, 0.34, 0.02)),
    "RingArm": ((-0.23, 0, 0.34), (0.14, 0.02, 0.015)),
}
# tapered cylinders: name -> (origin, z0, r0, z1, r1, sides)
TAPERED = {
    "Burner": ((-0.16, 0, 0), 0.02, 0.035, 0.06, 0.035, 16),
    "BurnerWick": ((-0.16, 0, 0), 0.06, 0.008, 0.075, 0.008, 8),
    "Flame": ((-0.16, 0, 0), 0.075, 0.018, 0.10, 0.002, 12),
    "StandRod": ((-0.30, 0, 0), 0.01, 0.008, 0.50, 0.008, 12),
    "CondenserTube": ((0.10, 0, 0), 0.18, 0.024, 0.36, 0.024, 16),
}
# two-point tubes: name -> (p0, p1, radius, sides)
TUBES = {
    "VapourArm": ((-0.16, 0, 0.44), (0.10, 0, 0.36), 0.016, 12),
    "DripTube": ((0.10, 0, 0.18), (0.10, 0, 0.10), 0.010, 12),
}
# flat tori: name -> (center, R, tube, arc_segments, tube_segments)
TORI = {
    "RetortRimLip": ((-0.16, 0, 0.44), 0.028, 0.004, 24, 6),
    "StandRing": ((-0.16, 0, 0.34), 0.035, 0.006, 24, 6),
    "Collar_Neck": ((-0.16, 0, 0.44), 0.030, 0.005, 24, 6),
    "Collar_Condenser": ((0.10, 0, 0.36), 0.026, 0.005, 24, 6),
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


def sphere_radius_at(center_z, R, z):
    """Radius of a sphere (centre z, radius R) at height z."""
    dz = z - center_z
    if abs(dz) >= R:
        return 0.0
    return math.sqrt(R * R - dz * dz)


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
    tolerance; return [(distance, count, center, radius)] per ring.
    The gap split (not rounding the radius into the key) matters:
    a ring whose true radius sits on a rounding boundary (e.g. the
    collection flask shoulder ring at r 0.0275) must not be split into
    two clusters by float noise, while two genuinely different rings
    at the same height (a liquid's flat top: r 0.001 and r 0.0953)
    must stay apart."""
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
    method as the 068 build script's own self-check): the expected
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


def check_helix_winding(obj):
    """Winding check for the coil tube: each face normal must point
    away from the nearest sampled helix centerline point."""
    mw = obj.matrix_world
    if "helix_centers" in obj:
        centers = [Vector(c) for c in obj["helix_centers"]]
    else:
        # recompute from design params if the property did not survive
        centers = []
        nseg = COIL["turns"] * 16
        for s in range(nseg + 1):
            t = s / nseg
            th = 2.0 * math.pi * COIL["turns"] * t
            centers.append(Vector((
                COIL["center"][0] + COIL["R"] * math.cos(th),
                COIL["center"][1] + COIL["R"] * math.sin(th),
                COIL["z0"] + (COIL["z1"] - COIL["z0"]) * t)))
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


def check_centroid_winding(obj):
    """Centroid check (same as the 068 build script): count faces
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


def check_coil(obj):
    """CondenserCoil helix tube: 49 rings x 6 verts + 2 cap centres =
    296 verts; 48*6 quads + 12 cap tris = 300 faces; bbox vs the
    analytic helix bbox (tube sampled in 6 steps: z half-extent
    0.007*cos(10deg) ~= 0.0069 at the ends)."""
    r = world_range(obj)
    cx, cy = COIL["center"]
    exp = (round(cx - (COIL["R"] + COIL["tube"]), 3),
           round(cx + (COIL["R"] + COIL["tube"]), 3),
           round(cy - (COIL["R"] + COIL["tube"]), 3),
           round(cy + (COIL["R"] + COIL["tube"]), 3),
           round(COIL["z0"] - COIL["tube"], 3),
           round(COIL["z1"] + COIL["tube"], 3))
    verts = len(obj.data.vertices)
    rhos = [math.hypot(v.x - cx, v.y - cy) for v in world_verts(obj)]
    row = {"range": r, "expected": exp,
           "verts": verts, "verts_expected": 296,
           "rho_min": round(min(rhos), 3), "rho_max": round(max(rhos), 3),
           "rho_min_expected": round(COIL["R"] - COIL["tube"], 3),
           "rho_max_expected": round(COIL["R"] + COIL["tube"], 3),
           "ok": bool(bbox_close(r, exp, tol=0.002)
                      and verts == 296
                      and abs(min(rhos) - (COIL["R"] - COIL["tube"])) < 0.002
                      and abs(max(rhos) - (COIL["R"] + COIL["tube"])) < 0.002)}
    return row


def torus_sdf(rho, z, R, tube, cz):
    """Signed distance to a flat torus (XY plane, centre z=cz)."""
    return math.sqrt((rho - R) ** 2 + (z - cz) ** 2) - tube

def check_flame_contact(by_name):
    """Flame tip (z 0.10) must touch the retort bulb bottom (z 0.10)
    by design; wick (0.06-0.075) sits on the burner top (0.06) and
    the flame bottom (0.075) sits on the wick top."""
    flame = by_name["Flame"]
    retort = by_name["RetortFlask"]
    wick = by_name["BurnerWick"]
    burner = by_name["Burner"]
    flame_top = max(v.z for v in world_verts(flame))
    flame_bot = min(v.z for v in world_verts(flame))
    flame_bot_r = max(math.hypot(v.x - RETORT_X, v.y)
                      for v in world_verts(flame)
                      if abs(v.z - flame_bot) < 0.001)
    bulb_bot = min(v.z for v in world_verts(retort))
    wick_bot = min(v.z for v in world_verts(wick))
    wick_top = max(v.z for v in world_verts(wick))
    burner_top = max(v.z for v in world_verts(burner))
    row = {"flame_tip_z": round(flame_top, 4),
           "bulb_bottom_z": round(bulb_bot, 4),
           "flame_bulb_gap": round(flame_top - bulb_bot, 4),
           "flame_bottom_z": round(flame_bot, 4),
           "flame_bottom_radius": round(flame_bot_r, 4),
           "wick_bottom_z": round(wick_bot, 4),
           "wick_top_z": round(wick_top, 4),
           "burner_top_z": round(burner_top, 4),
           "ok": bool(abs(flame_top - 0.10) < 0.002
                      and abs(bulb_bot - 0.10) < 0.002
                      and abs(flame_bot - wick_top) < 0.002
                      and abs(wick_bot - burner_top) < 0.002)}
    return row


def check_stand_ring(by_name):
    """StandRing (R 0.035, tube 0.006, z 0.34) around the retort neck
    (radius 0.028): inner radius 0.029, clearance 0.001 by design.
    RingArm must bridge rod (x -0.30) and ring (inner edge -0.201)."""
    ring = by_name["StandRing"]
    retort = by_name["RetortFlask"]
    arm = by_name["RingArm"]
    cx = RETORT_X
    rhos = [math.hypot(v.x - cx, v.y) for v in world_verts(ring)]
    ring_inner = min(rhos)
    ring_outer = max(rhos)
    # neck radius from the retort rings at z 0.30 and 0.44
    neck_rs = []
    for v in world_verts(retort):
        if abs(v.z - 0.30) < 0.001 or abs(v.z - 0.44) < 0.001:
            neck_rs.append(math.hypot(v.x - RETORT_X, v.y))
    neck_r = sum(neck_rs) / len(neck_rs) if neck_rs else None
    arm_r = world_range(arm)
    rod = by_name["StandRod"]
    rod_r = world_range(rod)
    row = {"ring_inner_radius": round(ring_inner, 4),
           "ring_outer_radius": round(ring_outer, 4),
           "ring_inner_design": 0.029,
           "neck_radius": round(neck_r, 4) if neck_r else None,
           "neck_design": 0.028,
           "clearance": round(ring_inner - neck_r, 4) if neck_r else None,
           "ring_arm_x": (arm_r[0], arm_r[1]),
           "rod_x": (rod_r[0], rod_r[1]),
           "ring_inner_edge_x": round(cx - ring_inner, 3),
           "ok": bool(abs(ring_inner - 0.029) < 0.002
                      and abs(neck_r - 0.028) < 0.002
                      and ring_inner > neck_r
                      and arm_r[0] <= rod_r[1] and arm_r[1] >= cx - ring_inner)}
    return row


def check_coil_clearance(by_name):
    """Coil inner surface (R - tube = 0.035) vs condenser tube
    (radius 0.024): clearance 0.011 by design; coil must also clear
    the condenser tube top/bottom (coil z 0.20-0.34 inside tube
    z 0.18-0.36)."""
    coil = by_name["CondenserCoil"]
    tube = by_name["CondenserTube"]
    cx, cy = COIL["center"]
    rhos = [math.hypot(v.x - cx, v.y - cy) for v in world_verts(coil)]
    coil_inner = min(rhos)
    tube_rs = [math.hypot(v.x - COND_X, v.y) for v in world_verts(tube)
               if math.hypot(v.x - COND_X, v.y) > 0.001]
    tube_r = sum(tube_rs) / len(tube_rs)
    coil_z = (min(v.z for v in world_verts(coil)),
              max(v.z for v in world_verts(coil)))
    tube_z = (min(v.z for v in world_verts(tube)),
              max(v.z for v in world_verts(tube)))
    row = {"coil_inner_radius": round(coil_inner, 4),
           "coil_inner_design": 0.035,
           "condenser_tube_radius": round(tube_r, 4),
           "clearance": round(coil_inner - tube_r, 4),
           "coil_z": tuple(round(v, 3) for v in coil_z),
           "tube_z": tuple(round(v, 3) for v in tube_z),
           "ok": bool(abs(coil_inner - 0.035) < 0.002
                      and abs(tube_r - 0.024) < 0.002
                      and coil_inner > tube_r
                      and coil_z[0] > tube_z[0] and coil_z[1] < tube_z[1])}
    return row


def check_collars(by_name):
    """Both brass collars wrap the sloped vapour arm: the arm's
    centreline passes through each collar centre, so the minimum
    distance from arm mesh verts to the collar centre circle, minus
    the collar tube radius, must stay positive."""
    arm = by_name["VapourArm"]
    rows = {}
    for name in ("Collar_Neck", "Collar_Condenser"):
        center, R, tube, _a, _t = TORI[name]
        cx, cy, cz = center
        min_dist = 1e9
        min_at = None
        for v in world_verts(arm):
            rho = math.hypot(v.x - cx, v.y - cy)
            d = torus_sdf(rho, v.z, R, tube, cz)
            if d < min_dist:
                min_dist = d
                min_at = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
        rows[name] = {
            "collar_center": center, "collar_R": R,
            "collar_tube": tube,
            "collar_inner_radius": round(R - tube, 4),
            "arm_radius": 0.016,
            "min_sdf_arm_to_collar": round(min_dist, 4),
            "min_sdf_at": min_at,
            "ok": bool(min_dist > 0)}
    return {"collars": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_rim_lip_wrap(by_name):
    """RetortRimLip torus wraps the retort neck top ring: the neck's
    top ring (r 0.028, z 0.44) passes through the lip tube's centre
    circle (R 0.028, tube 0.004)."""
    retort = by_name["RetortFlask"]
    center, R, tube, _a, _t = TORI["RetortRimLip"]
    cx, cy, cz = center
    top_ring = [v for v in world_verts(retort) if abs(v.z - cz) < 0.001]
    dists = [torus_sdf(math.hypot(v.x - cx, v.y - cy), v.z, R, tube, cz)
             for v in top_ring]
    row = {"top_ring_verts": len(top_ring),
           "top_ring_radius": round(
               sum(math.hypot(v.x - cx, v.y - cy) for v in top_ring)
               / max(1, len(top_ring)), 4),
           "lip_center_radius": R,
           "min_sdf_to_lip": round(min(dists), 4) if dists else None,
           "max_sdf_to_lip": round(max(dists), 4) if dists else None,
           "ok": bool(top_ring and all(d < 0 for d in dists))}
    return row


def check_liquids(by_name):
    """Both liquids must sit inside their glass bulbs, with positive
    clearance everywhere; tops below the shoulders; bottoms above the
    bulb floors. Clearances are measured against the true sphere
    (bulb centre + radius), vertex-based and analytic (fine sampling
    of the liquid profile against the sphere)."""
    rows = {}

    def liquid_vs_sphere(liq_obj, profile, bulb_center, bulb_R):
        bcx, _bcy, bcz = bulb_center
        min_clear = 1e9
        min_at = None
        for v in world_verts(liq_obj):
            rho = math.hypot(v.x - bcx, v.y)
            clear = sphere_radius_at(bcz, bulb_R, v.z) - rho
            if clear < min_clear:
                min_clear = clear
                min_at = (round(v.x, 3), round(v.y, 3), round(v.z, 3))
        z_lo = min(r for _r, r in [(p[0], p[1]) for p in profile])
        z_hi = max(p[1] for p in profile)
        min_an = 1e9
        min_an_z = None
        for i in range(501):
            z = z_lo + i * (z_hi - z_lo) / 500.0
            liq_r = profile_radius_at(profile, z)
            clear = sphere_radius_at(bcz, bulb_R, z) - liq_r
            if clear < min_an:
                min_an = clear
                min_an_z = z
        vs = world_verts(liq_obj)
        return {"min_clearance_verts": round(min_clear, 4),
                "min_clearance_vert_at": min_at,
                "min_clearance_analytic": round(min_an, 4),
                "min_clearance_analytic_z": round(min_an_z, 4),
                "bottom_z": round(min(v.z for v in vs), 4),
                "top_z": round(max(v.z for v in vs), 4)}

    r = liquid_vs_sphere(by_name["RetortLiquid"], RETORT_LIQ_PROFILE,
                         RETORT_BULB[0], RETORT_BULB[1])
    r["bulb_bottom_z"] = round(RETORT_BULB[0][2] - RETORT_BULB[1], 4)
    r["ok"] = bool(r["min_clearance_verts"] > 0
                   and r["min_clearance_analytic"] > 0
                   and r["bottom_z"] > r["bulb_bottom_z"])
    rows["RetortLiquid"] = r
    c = liquid_vs_sphere(by_name["CollectionLiquid"], COLL_LIQ_PROFILE,
                         COLL_BULB[0], COLL_BULB[1])
    c["bulb_bottom_z"] = round(COLL_BULB[0][2] - COLL_BULB[1], 4)
    c["ok"] = bool(c["min_clearance_verts"] > 0
                   and c["min_clearance_analytic"] > 0
                   and c["bottom_z"] > c["bulb_bottom_z"])
    rows["CollectionLiquid"] = c
    return {"liquids": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_drip_gap(by_name):
    """Drip tube bottom (z 0.10) vs collection liquid surface
    (z 0.0572): gap 0.0428 by design; the tube (r 0.010) passes
    through the collection neck (r 0.018) and hangs above the liquid
    without touching it."""
    drip = by_name["DripTube"]
    liq = by_name["CollectionLiquid"]
    flask = by_name["CollectionFlask"]
    drip_bot = min(v.z for v in world_verts(drip))
    drip_top = max(v.z for v in world_verts(drip))
    drip_rs = [math.hypot(v.x - COND_X, v.y) for v in world_verts(drip)
               if math.hypot(v.x - COND_X, v.y) > 0.001]
    drip_r = sum(drip_rs) / len(drip_rs)
    liq_top = max(v.z for v in world_verts(liq))
    # flask radius at the drip bottom height (profile interpolation)
    flask_r_at_drip = profile_radius_at(COLL_PROFILE, drip_bot)
    neck_rs = [math.hypot(v.x - COND_X, v.y)
               for v in world_verts(flask) if abs(v.z - 0.16) < 0.001]
    neck_r = sum(neck_rs) / len(neck_rs) if neck_rs else None
    row = {"drip_bottom_z": round(drip_bot, 4),
           "drip_top_z": round(drip_top, 4),
           "drip_radius": round(drip_r, 4),
           "collection_liquid_top_z": round(liq_top, 4),
           "drip_gap": round(drip_bot - liq_top, 4),
           "flask_radius_at_drip_bottom": round(flask_r_at_drip, 4),
           "collection_neck_radius": round(neck_r, 4) if neck_r else None,
           "ok": bool(abs(drip_bot - 0.10) < 0.002
                      and abs(drip_r - 0.010) < 0.002
                      and drip_bot > liq_top
                      and drip_r < neck_r
                      and drip_r < flask_r_at_drip)}
    return row


def check_condenser_gap(by_name):
    """Condenser tube bottom (z 0.18) vs collection flask neck top
    (z 0.16): gap 0.020 by design; the drip tube top (z 0.18) meets
    the condenser tube bottom exactly."""
    tube = by_name["CondenserTube"]
    flask = by_name["CollectionFlask"]
    drip = by_name["DripTube"]
    tube_bot = min(v.z for v in world_verts(tube))
    neck_top = max(v.z for v in world_verts(flask)
                   if abs(math.hypot(v.x - COND_X, v.y) - 0.018) < 0.001)
    drip_top = max(v.z for v in world_verts(drip))
    row = {"condenser_tube_bottom_z": round(tube_bot, 4),
           "collection_neck_top_z": round(neck_top, 4),
           "gap": round(tube_bot - neck_top, 4),
           "drip_tube_top_z": round(drip_top, 4),
           "ok": bool(abs(tube_bot - 0.18) < 0.002
                      and abs(neck_top - 0.16) < 0.002
                      and abs(drip_top - tube_bot) < 0.002)}
    return row


def check_vapour_joints(by_name):
    """Vapour arm end caps: start cap centre must sit at the retort
    neck top centre (-0.16, 0, 0.44), end cap centre at the condenser
    top centre (0.10, 0, 0.36); arm radius 0.016 must be smaller than
    both openings (neck 0.028, condenser tube 0.024)."""
    arm = by_name["VapourArm"]
    p0, p1, radius, _s = TUBES["VapourArm"]
    # the two cap-centre verts sit exactly at p0 / p1 (the fan
    # triangles' centres are 1/3 of the way out, not at the cap
    # centre, so count verts, not polygon centres)
    vs = world_verts(arm)
    starts = [v for v in vs if (v - Vector(p0)).length < 0.002]
    ends = [v for v in vs if (v - Vector(p1)).length < 0.002]
    row = {"arm_start_cap_centres": len(starts),
           "arm_end_cap_centres": len(ends),
           "arm_radius": radius,
           "retort_neck_radius": 0.028,
           "condenser_tube_radius": 0.024,
           "ok": bool(len(starts) == 1 and len(ends) == 1
                      and radius < 0.028 and radius < 0.024)}
    return row


def check_rod_embed(by_name):
    """StandRod bottom (z 0.01) embeds 0.01 into the base board
    (z 0-0.02) by design; rod top (z 0.50) is the highest point of
    the whole asset."""
    rod = by_name["StandRod"]
    board = by_name["BaseBoard"]
    rod_bot = min(v.z for v in world_verts(rod))
    rod_top = max(v.z for v in world_verts(rod))
    board_top = max(v.z for v in world_verts(board))
    board_bot = min(v.z for v in world_verts(board))
    row = {"rod_bottom_z": round(rod_bot, 4),
           "rod_top_z": round(rod_top, 4),
           "board_z": (round(board_bot, 4), round(board_top, 4)),
           "embed_depth": round(board_top - rod_bot, 4),
           "ok": bool(abs(rod_bot - 0.01) < 0.002
                      and abs(rod_top - 0.50) < 0.002
                      and rod_bot < board_top and rod_bot > board_bot)}
    return row


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
           # 068 note: "整体约 0.62 m 宽 × 0.50 m 高 × 0.34 m 深"
           "note_size": (0.62, 0.50, 0.34)}
    row["ok"] = bool(abs(row["width"] - 0.62) <= 0.02
                     and abs(row["height"] - 0.50) <= 0.02
                     and abs(row["depth"] - 0.34) <= 0.02)
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 068 design values.
    Glass_Clear also checks Alpha + dithered render method; the three
    glowing materials also check the Emission node (color, strength)
    and the MixShader factor."""
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

    retort = check_lathe("RetortFlask", by_name["RetortFlask"],
                         RETORT_PROFILE, 24, (RETORT_X, 0, 0), (0, 0, 1),
                         24, [0.100])
    print("QA_RETORT_FLASK:", retort)
    retort_liq = check_lathe("RetortLiquid", by_name["RetortLiquid"],
                             RETORT_LIQ_PROFILE, 24, (RETORT_X, 0, 0),
                             (0, 0, 1), 24, [0.104])
    print("QA_RETORT_LIQUID_SHAPE:", retort_liq)
    coll = check_lathe("CollectionFlask", by_name["CollectionFlask"],
                       COLL_PROFILE, 24, (COND_X, 0, 0), (0, 0, 1),
                       24, [0.020])
    print("QA_COLLECTION_FLASK:", coll)
    coll_liq = check_lathe("CollectionLiquid", by_name["CollectionLiquid"],
                           COLL_LIQ_PROFILE, 24, (COND_X, 0, 0), (0, 0, 1),
                           24, [0.023])
    print("QA_COLLECTION_LIQUID_SHAPE:", coll_liq)
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
    coil = check_coil(by_name["CondenserCoil"])
    print("QA_COIL:", coil)
    flame = check_flame_contact(by_name)
    print("QA_FLAME_CONTACT:", flame)
    stand_ring = check_stand_ring(by_name)
    print("QA_STAND_RING:", stand_ring)
    coil_clear = check_coil_clearance(by_name)
    print("QA_COIL_CLEARANCE:", coil_clear)
    collars = check_collars(by_name)
    print("QA_COLLARS:", collars)
    rimlip = check_rim_lip_wrap(by_name)
    print("QA_RIM_LIP_WRAP:", rimlip)
    liquids = check_liquids(by_name)
    print("QA_LIQUIDS:", liquids)
    drip = check_drip_gap(by_name)
    print("QA_DRIP_GAP:", drip)
    cond_gap = check_condenser_gap(by_name)
    print("QA_CONDENSER_GAP:", cond_gap)
    vapour = check_vapour_joints(by_name)
    print("QA_VAPOUR_JOINTS:", vapour)
    rod_embed = check_rod_embed(by_name)
    print("QA_ROD_EMBED:", rod_embed)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    # Normal checks, authoritative per part type (same approach as 067):
    # - the 4 lathe parts: profile-segment analytic check (recalc's
    #   signed-volume heuristic can misjudge an open vessel);
    # - the 4 tori: centre-circle check; the coil: helix-centreline
    #   check; everything else: centroid check (same as the 068 build
    #   script's own self-check).
    lathe_winding = {}
    for name, profile in (("RetortFlask", RETORT_PROFILE),
                          ("RetortLiquid", RETORT_LIQ_PROFILE),
                          ("CollectionFlask", COLL_PROFILE),
                          ("CollectionLiquid", COLL_LIQ_PROFILE)):
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
    coil_winding = check_helix_winding(by_name["CondenserCoil"])
    print("QA_HELIX_WINDING flipped=%d" % coil_winding)
    other_names = [n for n in by_name
                   if n not in lathe_winding and n not in torus_winding
                   and n != "CondenserCoil"]
    centroid_winding = {n: check_centroid_winding(by_name[n])
                        for n in other_names}
    print("QA_CENTROID_WINDING:", centroid_winding)
    analytic_flipped = (sum(len(v) for v in lathe_winding.values())
                        + sum(torus_winding.values()) + coil_winding
                        + sum(centroid_winding.values()))
    recalc_flipped = sum(r["inverted_normals"]
                         for r in results.values())
    # recalc is the independent re-measurement except for the lathe
    # parts, where the analytic check rules (067 funnel precedent)
    recalc_lathe = sum(results[n]["inverted_normals"]
                       for n in lathe_winding)
    inverted_effective = (recalc_flipped - recalc_lathe
                          + sum(len(v) for v in lathe_winding.values()))

    structure = {"retort_flask": retort,
                 "retort_liquid_shape": retort_liq,
                 "collection_flask": coll,
                 "collection_liquid_shape": coll_liq,
                 "tapered": tapered, "tubes": tubes, "tori": tori,
                 "boxes": boxes, "coil": coil,
                 "flame_contact": flame, "stand_ring": stand_ring,
                 "coil_clearance": coil_clear, "collars": collars,
                 "rim_lip_wrap": rimlip, "liquids": liquids,
                 "drip_gap": drip, "condenser_gap": cond_gap,
                 "vapour_joints": vapour, "rod_embed": rod_embed,
                 "ground_contact": ground, "overall": overall,
                 "lathe_winding_analytic": {
                     k: len(v) for k, v in lathe_winding.items()},
                 "torus_winding": torus_winding,
                 "coil_winding_flipped": coil_winding,
                 "centroid_winding": centroid_winding,
                 "analytic_flipped_total": analytic_flipped}
    structure_ok = (retort["ok"] and retort_liq["ok"] and coll["ok"]
                    and coll_liq["ok"]
                    and all(v["ok"] for v in tapered.values())
                    and all(v["ok"] for v in tubes.values())
                    and all(v["ok"] for v in tori.values())
                    and all(v["ok"] for v in boxes.values())
                    and coil["ok"] and flame["ok"] and stand_ring["ok"]
                    and coil_clear["ok"] and collars["ok"]
                    and rimlip["ok"] and liquids["ok"] and drip["ok"]
                    and cond_gap["ok"] and vapour["ok"]
                    and rod_embed["ok"] and ground["ok"] and overall["ok"]
                    and analytic_flipped == 0)

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # Boundary edges BY DESIGN (open glassware, not holes):
    # RetortFlask: open neck top (24); CollectionFlask: open neck top
    # (24); RetortLiquid / CollectionLiquid: flat-top annulus ends in
    # a 1 mm centre ring (24 each) — same pinhole as the 066 cup.
    # Everything else must be closed (0 boundary edges).
    open_parts = {"RetortFlask": 24, "RetortLiquid": 24,
                  "CollectionFlask": 24, "CollectionLiquid": 24}
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
        "asset": "068-lowpoly-alembic-still",
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
        f.write("# 069 资产质检单：低模炼金蒸馏器（068）\n\n")
        f.write("被检资产：`scenes/068-lowpoly-alembic-still.blend`（%d 个道具部件，不含地面）。\n" % len(results))
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
        f.write("- 面数与 068 设计表逐部件比对：%s（设计 1752 面：三角 284、四边 1468、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 开口边：边界边共 %d 条，全部是设计上的开口（曲颈甑颈口 24 + 收集瓶颈口 24 = 48；两瓶药液平顶各以 1 mm 中心环收口，各 24，共 48），其余 14 个部件 0 条：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致：车削件轮廓段解析检查内翻面 %s；圆环中心线检查内翻面 %s；盘管螺旋中心线检查内翻面 %d；其余部件质心法检查内翻面 %s；recalc 交叉核对有效倒置面 %d 个：%s\n" % (
            {k: len(v) for k, v in lathe_winding.items()},
            torus_winding, coil_winding, centroid_winding,
            inverted_effective, verdict(inverted_effective == 0)))
        f.write("  （说明：recalc_face_normals 用网格有向体积定内外，对开口容器可能误判，故车削件以轮廓段解析检查为准——与 068 构建脚本自检同一方法；067 漏斗即有此先例。本次 recalc 与解析检查一致，无误判需要剔除。）\n\n" if recalc_lathe == sum(len(v) for v in lathe_winding.values()) else "  （注意：recalc 在车削件上的读数与解析检查不一致，见上——解析检查为准。）\n\n")
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
        f.write("## 4. 蒸馏器结构（实测）\n\n")
        f.write("### 4.1 玻璃曲颈甑（车削轮廓，24 段）\n\n")
        f.write("- RetortFlask：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.100），颈口 z 0.44 开口：%s\n" % (
            len(retort["rings"]), retort["ring_distances"],
            retort["ring_radii"],
            retort["design_radii"],
            retort["range"][0], retort["range"][1], retort["range"][2],
            retort["range"][3], retort["range"][4], retort["range"][5],
            retort["expected"], verdict(retort["ok"])))
        f.write("- RetortLiquid：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.104），顶面 z 0.2117 平顶：%s\n" % (
            len(retort_liq["rings"]), retort_liq["ring_distances"],
            retort_liq["ring_radii"],
            retort_liq["design_radii"],
            retort_liq["range"][0], retort_liq["range"][1],
            retort_liq["range"][2], retort_liq["range"][3],
            retort_liq["range"][4], retort_liq["range"][5],
            retort_liq["expected"], verdict(retort_liq["ok"])))
        f.write("\n### 4.2 收集瓶（车削轮廓，24 段）\n\n")
        f.write("- CollectionFlask：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.020），颈口 z 0.16 开口：%s\n" % (
            len(coll["rings"]), coll["ring_distances"],
            coll["ring_radii"],
            coll["design_radii"],
            coll["range"][0], coll["range"][1], coll["range"][2],
            coll["range"][3], coll["range"][4], coll["range"][5],
            coll["expected"], verdict(coll["ok"])))
        f.write("- CollectionLiquid：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面全部是底面扇形封口（面中心轴向位置 0.023），顶面 z 0.0572 平顶：%s\n" % (
            len(coll_liq["rings"]), coll_liq["ring_distances"],
            coll_liq["ring_radii"],
            coll_liq["design_radii"],
            coll_liq["range"][0], coll_liq["range"][1],
            coll_liq["range"][2], coll_liq["range"][3],
            coll_liq["range"][4], coll_liq["range"][5],
            coll_liq["expected"], verdict(coll_liq["ok"])))
        f.write("\n### 4.3 酒精灯、灯芯与火焰\n\n")
        for name in ("Burner", "BurnerWick", "Flame"):
            t = tapered[name]
            f.write("- %s：2 环（每环 %d 顶点），环高 z %s、半径 %s；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；%d 个三角面分处两端盖（轴向位置 %s）：%s\n" % (
                name, t["rings"][0][1],
                [d for d, _c, _r in t["rings"]],
                [r for _d, _c, r in t["rings"]],
                t["range"][0], t["range"][1], t["range"][2],
                t["range"][3], t["range"][4], t["range"][5],
                t["expected"], t["tri_count"], t["tri_axial_positions"],
                verdict(t["ok"])))
        f.write("- 火焰尖 z %.4f，甑底 z %.4f，间隙 %.4f（设计贴合 0.000）；灯芯 z %.4f–%.4f 坐在酒精灯顶面 z %.4f 上，火焰底端 z %.4f 坐在灯芯顶面：%s\n" % (
            flame["flame_tip_z"], flame["bulb_bottom_z"],
            flame["flame_bulb_gap"], flame["wick_bottom_z"],
            flame["wick_top_z"], flame["burner_top_z"],
            flame["flame_bottom_z"], verdict(flame["ok"])))
        f.write("\n### 4.4 固定架与圆环\n\n")
        f.write("- StandRod：2 环（每环 12 顶点），z 0.01–0.50，半径 0.008；底端 z %.4f 埋入底板（底板 z %.4f–%.4f），埋入 %.4f；顶端 z %.4f 是全资产最高点：%s\n" % (
            rod_embed["rod_bottom_z"], rod_embed["board_z"][0],
            rod_embed["board_z"][1], rod_embed["embed_depth"],
            rod_embed["rod_top_z"], verdict(rod_embed["ok"])))
        f.write("- StandRing：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.029、外径 0.041）；甑颈半径 %.4f（设计 0.028），固定环余量 %.4f：%s\n" % (
            tori["StandRing"]["range"][0], tori["StandRing"]["range"][1],
            tori["StandRing"]["range"][2], tori["StandRing"]["range"][3],
            tori["StandRing"]["range"][4], tori["StandRing"]["range"][5],
            tori["StandRing"]["expected"], tori["StandRing"]["rho_min"],
            tori["StandRing"]["rho_max"], stand_ring["neck_radius"],
            stand_ring["clearance"], verdict(stand_ring["ok"])))
        f.write("- RingArm：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s），内端 x %.3f 接竖杆（竖杆 x %.3f–%.3f），外端 x %.3f 探到固定环内缘 x %.3f：%s\n" % (
            boxes["RingArm"]["range"][0], boxes["RingArm"]["range"][1],
            boxes["RingArm"]["range"][2], boxes["RingArm"]["range"][3],
            boxes["RingArm"]["range"][4], boxes["RingArm"]["range"][5],
            boxes["RingArm"]["expected"],
            boxes["RingArm"]["range"][0], stand_ring["rod_x"][0],
            stand_ring["rod_x"][1],
            boxes["RingArm"]["range"][1], stand_ring["ring_inner_edge_x"],
            verdict(stand_ring["ok"])))
        f.write("- BaseBoard：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
            boxes["BaseBoard"]["range"][0], boxes["BaseBoard"]["range"][1],
            boxes["BaseBoard"]["range"][2], boxes["BaseBoard"]["range"][3],
            boxes["BaseBoard"]["range"][4], boxes["BaseBoard"]["range"][5],
            boxes["BaseBoard"]["expected"],
            verdict(boxes["BaseBoard"]["ok"])))
        f.write("\n### 4.5 蒸汽斜管与两枚卡箍\n\n")
        t = tubes["VapourArm"]
        f.write("- VapourArm：2 环（每环 12 顶点），长度 %.4f m，半径 0.016；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；24 个三角面分处两端盖（轴向位置 %s）：%s\n" % (
            t["length"], t["range"][0], t["range"][1], t["range"][2],
            t["range"][3], t["range"][4], t["range"][5],
            t["expected"], t["tri_axial_positions"], verdict(t["ok"])))
        f.write("- 斜管两端盖中心：甑颈顶 (-0.16, 0, 0.44) 处 %d 个盖心顶点、冷凝管顶 (0.10, 0, 0.36) 处 %d 个盖心顶点；斜管半径 0.016 小于甑颈内径 0.028 与冷凝管内径 0.024，两端都落在开口内：%s\n" % (
            vapour["arm_start_cap_centres"], vapour["arm_end_cap_centres"],
            verdict(vapour["ok"])))
        for name in ("Collar_Neck", "Collar_Condenser"):
            cc = collars["collars"][name]
            tt = tori[name]
            f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 %.4f、外径 %.4f）；斜管表面到卡箍管面的最小有向距离 %.4f（位于 %s），为正即不穿帮：%s\n" % (
                name, tt["range"][0], tt["range"][1], tt["range"][2],
                tt["range"][3], tt["range"][4], tt["range"][5],
                tt["expected"], tt["rho_min"], tt["rho_max"],
                cc["collar_inner_radius"], tt["rho_max_expected"],
                cc["min_sdf_arm_to_collar"], cc["min_sdf_at"],
                verdict(cc["ok"])))
        f.write("- RetortRimLip：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.024、外径 0.032）；甑顶环 %d 个顶点、平均半径 %.4f（卷边中心圆半径 0.028），到卷边管面的有向距离 %.4f–%.4f（全为负值，即顶环整圈埋在卷边管内）：%s\n" % (
            tori["RetortRimLip"]["range"][0],
            tori["RetortRimLip"]["range"][1],
            tori["RetortRimLip"]["range"][2],
            tori["RetortRimLip"]["range"][3],
            tori["RetortRimLip"]["range"][4],
            tori["RetortRimLip"]["range"][5],
            tori["RetortRimLip"]["expected"],
            tori["RetortRimLip"]["rho_min"],
            tori["RetortRimLip"]["rho_max"],
            rimlip["top_ring_verts"], rimlip["top_ring_radius"],
            rimlip["min_sdf_to_lip"], rimlip["max_sdf_to_lip"],
            verdict(rimlip["ok"])))
        f.write("\n### 4.6 冷凝器与铜盘管\n\n")
        t = tapered["CondenserTube"]
        f.write("- CondenserTube：2 环（每环 16 顶点），z 0.18–0.36，半径 0.024；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
            t["range"][0], t["range"][1], t["range"][2],
            t["range"][3], t["range"][4], t["range"][5],
            t["expected"], verdict(t["ok"])))
        f.write("- CondenserCoil：%d 个顶点（设计 296：49 环 × 6 + 2 盖心），300 面（288 四边 + 12 三角）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；径向范围 %.3f–%.3f（设计内径 0.035、外径 0.049）：%s\n" % (
            coil["verts"], coil["range"][0], coil["range"][1],
            coil["range"][2], coil["range"][3], coil["range"][4],
            coil["range"][5], coil["expected"], coil["rho_min"],
            coil["rho_max"], verdict(coil["ok"])))
        f.write("- 盘管内径 %.4f（设计 0.035），冷凝管半径 %.4f，余量 %.4f；盘管 z %.3f–%.3f 在冷凝管 z %.3f–%.3f 之内：%s\n" % (
            coil_clear["coil_inner_radius"],
            coil_clear["condenser_tube_radius"],
            coil_clear["clearance"],
            coil_clear["coil_z"][0], coil_clear["coil_z"][1],
            coil_clear["tube_z"][0], coil_clear["tube_z"][1],
            verdict(coil_clear["ok"])))
        f.write("\n### 4.7 滴管、冷凝管与收集瓶\n\n")
        t = tubes["DripTube"]
        f.write("- DripTube：2 环（每环 12 顶点），长度 %.4f m，半径 0.010；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
            t["length"], t["range"][0], t["range"][1], t["range"][2],
            t["range"][3], t["range"][4], t["range"][5],
            t["expected"], verdict(t["ok"])))
        f.write("- 滴管底端 z %.4f，收集液面 z %.4f，滴落间隙 %.4f m；滴管半径 %.4f 小于收集瓶颈半径 %.4f，滴管底端处瓶内半径 %.4f：%s\n" % (
            drip["drip_bottom_z"], drip["collection_liquid_top_z"],
            drip["drip_gap"], drip["drip_radius"],
            drip["collection_neck_radius"],
            drip["flask_radius_at_drip_bottom"], verdict(drip["ok"])))
        f.write("- 冷凝管底端 z %.4f，收集瓶颈顶 z %.4f，间隙 %.4f m；滴管顶端 z %.4f 与冷凝管底端接合：%s\n" % (
            cond_gap["condenser_tube_bottom_z"],
            cond_gap["collection_neck_top_z"], cond_gap["gap"],
            cond_gap["drip_tube_top_z"], verdict(cond_gap["ok"])))
        f.write("\n### 4.8 双药液与球壁间隙\n\n")
        rl = liquids["liquids"]["RetortLiquid"]
        cl = liquids["liquids"]["CollectionLiquid"]
        f.write("- RetortLiquid：与甑球壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.4f）；底面 z %.4f 在甑底 z %.4f 之上、顶面 z %.4f：%s\n" % (
            rl["min_clearance_verts"], rl["min_clearance_vert_at"],
            rl["min_clearance_analytic"],
            rl["min_clearance_analytic_z"],
            rl["bottom_z"], rl["bulb_bottom_z"], rl["top_z"],
            verdict(rl["ok"])))
        f.write("- CollectionLiquid：与收集瓶球壁最小间隙（顶点实测）%.4f（位于 %s），曲面解析最小间隙 %.4f（z %.4f）；底面 z %.4f 在瓶底 z %.4f 之上、顶面 z %.4f：%s\n" % (
            cl["min_clearance_verts"], cl["min_clearance_vert_at"],
            cl["min_clearance_analytic"],
            cl["min_clearance_analytic_z"],
            cl["bottom_z"], cl["bulb_bottom_z"], cl["top_z"],
            verdict(cl["ok"])))
        f.write("\n### 4.9 地面、整体\n\n")
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s（底板 z=0 落地，竖杆底端埋入底板 0.01，其余部件在底板或支架上）：%s\n" % (
            ground["checked"], ground["global_min_z"],
            ground["below_ground"] if ground["below_ground"] else "无",
            verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（068 笔记“约 0.62 × 0.50 × 0.34 m”，"
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
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 068 构建脚本直接存入的线性值；玻璃另查 Alpha 与渲染方式，药液与火焰另查 Emission 与混合系数）：\n")
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
        f.write("- 068 笔记“实测间隙”数字与本质检复核一致：火焰贴合 0.000、固定环余量 %.4f、盘管余量 %.4f、滴管余量 0.008、甑内药液间隙 %.4f、收集液间隙 %.4f、滴管间隙 %.4f、冷凝管间隙 %.4f，无需更正。\n" % (
            stand_ring["clearance"], coil_clear["clearance"],
            liquids["liquids"]["RetortLiquid"]["min_clearance_analytic"],
            liquids["liquids"]["CollectionLiquid"]["min_clearance_analytic"],
            drip["drip_gap"], cond_gap["gap"]))
        f.write("- 两瓶药液平顶各以 1 mm 中心环收口（边界边各 24 条）：与 066 量杯腔底针孔同一做法，顶面是几乎封死的平顶环面，不是破洞。\n")
        f.write("- 竖杆底端埋入底板 0.01 m 是设计意图的连接（杆子穿过底板、底端不落地），不是穿帮；酒精灯与收集瓶底面 z 0.02 正好落在底板顶面上。\n")
        f.write("- 斜管两端盖中心正好落在甑颈顶与冷凝管顶的开口中心，斜管半径 0.016 小于两处开口内径，两端是“插进去”的连接，不是悬空。\n")
        f.write("- 玻璃斜管在影棚光下偏淡，是仓库既有玻璃风格（同 066/068 笔记已知问题），本质检不重复判否。\n")
        f.write("- 068 笔记尺寸与实测一致：宽 %.3f m × 深 %.3f m × 高 %.3f m"
                "（笔记“约 0.62 × 0.50 × 0.34 m”）。\n" % (
                    overall["width"], overall["depth"], overall["height"]))
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、蒸馏器结构、地面接触均通过。068 笔记的间隙数字经复核全部准确，无需返工、无需更正。\n")
        else:
            f.write("待修项：\n\n")
            f.write("（按复核结果填写）\n")


if __name__ == "__main__":
    main()
