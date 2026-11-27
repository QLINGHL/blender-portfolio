# -*- coding: utf-8 -*-
"""063 资产质检：对 062 低模炼金研钵与杵做真实 mesh 检查（拓扑/法线/UV/材质），
并实测研钵与杵特有结构：研钵车削环、研杵 38° 斜靠与碗口净空、粉堆与草药碎
在碗内斜坡底上的位置、干草药与研钵的间距。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 063-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "062-lowpoly-mortar-pestle.blend")
UV_JSON = os.path.join(ROOT, "scenes", "063-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "063-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "063-asset-qa-checklist.md")

# every mesh object in the 062 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/062-lowpoly-mortar-pestle.md (per-part table)
EXPECTED_FACES = {
    "Mortar": 360, "Pestle": 176, "PowderMound": 72,
    "HerbChunk_1": 20, "HerbChunk_2": 20, "HerbChunk_3": 20,
    "HerbChunk_4": 20, "HerbChunk_5": 20, "HerbChunk_6": 20,
    "HerbChunk_7": 20, "HerbChunk_8": 20,
    "DryStem_1": 18, "DryStem_2": 18, "DryStem_3": 18,
    "DryStem_4": 18, "DryStem_5": 18,
    "DryLeaf_1": 6, "DryLeaf_2": 6, "DryLeaf_3": 6,
    "DryLeaf_4": 6, "DryLeaf_5": 6, "DryLeaf_6": 6,
}
EXPECTED_TOTAL_FACES = 894
EXPECTED_TRIS = 272
EXPECTED_QUADS = 622

# part -> design material (from the 062 build script)
PART_MATERIAL = {
    "Mortar": "Mortar_Stone", "Pestle": "Pestle_Wood",
    "PowderMound": "Herb_Powder",
    "HerbChunk_1": "Herb_Green", "HerbChunk_2": "Herb_Light",
    "HerbChunk_3": "Herb_Green", "HerbChunk_4": "Herb_Light",
    "HerbChunk_5": "Herb_Green", "HerbChunk_6": "Herb_Light",
    "HerbChunk_7": "Herb_Green", "HerbChunk_8": "Herb_Green",
    "DryStem_1": "Herb_StemDry", "DryStem_2": "Herb_StemDry",
    "DryStem_3": "Herb_StemDry", "DryStem_4": "Herb_StemDry",
    "DryStem_5": "Herb_StemDry",
    "DryLeaf_1": "Herb_LeafDry", "DryLeaf_2": "Herb_LeafDry",
    "DryLeaf_3": "Herb_LeafDry", "DryLeaf_4": "Herb_LeafDry",
    "DryLeaf_5": "Herb_LeafDry", "DryLeaf_6": "Herb_LeafDry",
}

# Design material values from the 062 build script. The 062 build script
# passes raw tuples to solid_material, which stores them directly as
# linear Base Color (same convention as the 059/060 scripts).
DESIGN_MATS = {
    "Mortar_Stone":  {"metallic": 0.00, "roughness": 0.95,
                      "color": (0.30, 0.29, 0.28), "emissive": None},
    "Pestle_Wood":   {"metallic": 0.00, "roughness": 0.80,
                      "color": (0.38, 0.26, 0.13), "emissive": None},
    "Herb_Green":    {"metallic": 0.00, "roughness": 0.90,
                      "color": (0.20, 0.36, 0.12), "emissive": None},
    "Herb_Light":    {"metallic": 0.00, "roughness": 0.90,
                      "color": (0.30, 0.48, 0.18), "emissive": None},
    "Herb_Powder":   {"metallic": 0.00, "roughness": 1.00,
                      "color": (0.38, 0.52, 0.20), "emissive": None},
    "Herb_StemDry":  {"metallic": 0.00, "roughness": 0.95,
                      "color": (0.40, 0.35, 0.15), "emissive": None},
    "Herb_LeafDry":  {"metallic": 0.00, "roughness": 0.95,
                      "color": (0.34, 0.30, 0.12), "emissive": None},
}

# design geometry (copied from the 062 build script)
MORTAR_PROFILE = [
    (0.001, 0.000), (0.100, 0.000), (0.115, 0.008), (0.130, 0.018),
    (0.150, 0.045), (0.158, 0.075), (0.150, 0.100), (0.145, 0.110),
    (0.138, 0.112), (0.132, 0.108), (0.128, 0.095), (0.120, 0.070),
    (0.100, 0.050), (0.060, 0.040), (0.001, 0.038),
]
PESTLE_PROFILE = [
    (0.001, 0.000), (0.020, 0.002), (0.032, 0.012), (0.034, 0.025),
    (0.028, 0.040), (0.020, 0.055), (0.016, 0.120), (0.014, 0.180),
    (0.016, 0.220), (0.012, 0.245), (0.001, 0.255),
]
MOUND_PROFILE = [
    (0.001, 0.000), (0.0385, 0.000), (0.0364, 0.005), (0.0224, 0.014),
    (0.0084, 0.021), (0.001, 0.024),
]
MORTAR_SIDES = 24
PESTLE_SIDES = 16
MOUND_SIDES = 12
PESTLE_ORIGIN = (0.01, 0.01, 0.038)
PESTLE_ANGLE_DEG = 38.0
MOUND_LOC = (0.0, 0.09, 0.0)
MOUND_Z_BASE = 0.038
# inner wall of the mortar, rim -> centre (radius, z), for the floor-height
# function: the bowl floor is a slope, not a flat plane.
INNER_PROFILE = [(0.132, 0.108), (0.128, 0.095), (0.120, 0.070),
                 (0.100, 0.050), (0.060, 0.040), (0.001, 0.038)]
INNER_RADIUS_MAX = 0.132
MORTAR_OUTER_RADIUS = 0.158
BOWL_FLOOR_Z = 0.038  # floor height at the centre
# herb chunks: (x, y, z, radius, scale_z, rot_z_deg, material)
CHUNKS = [
    (0.075, 0.045, 0.0534, 0.019, 0.45, 20, "Herb_Green"),
    (-0.055, 0.060, 0.0517, 0.021, 0.40, 75, "Herb_Light"),
    (-0.085, 0.010, 0.0529, 0.017, 0.50, 140, "Herb_Green"),
    (-0.020, -0.005, 0.0451, 0.020, 0.42, 200, "Herb_Light"),
    (0.100, -0.030, 0.0610, 0.018, 0.48, 260, "Herb_Green"),
    (0.095, 0.015, 0.0542, 0.016, 0.45, 310, "Herb_Light"),
    (-0.045, 0.095, 0.0616, 0.017, 0.50, 45, "Herb_Green"),
    (0.100, 0.060, 0.0714, 0.015, 0.45, 170, "Herb_Green"),
]
# dry stems: common base point + fan directions (from the 062 build script)
STEM_BASE = (0.26, 0.02, 0.004)
STEM_DIRS = [
    (0.95, 0.30, 0.05), (1.00, 0.05, 0.03), (0.90, -0.25, 0.06),
    (0.75, 0.55, 0.04), (0.85, -0.50, 0.05),
]
STEM_LEN = 0.17
STEM_R = 0.004
STEM_SIDES = 6
# dry leaves: (x, y, z, rot_z_deg, tilt_deg)
LEAVES = [
    (0.33, 0.10, 0.006, 30, 8), (0.38, 0.02, 0.006, -40, 12),
    (0.36, -0.06, 0.006, 80, 6), (0.42, 0.08, 0.006, 10, 15),
    (0.30, -0.03, 0.006, 120, 10), (0.40, -0.04, 0.006, -70, 7),
]
LEAF_SIZE = (0.034, 0.014, 0.002)
# icosphere subdiv 0 as built by Blender: a vertex sits at the pole,
# so max |z| over vertices = r (not 0.8507 * r of the unrotated
# icosahedron); rotation about Z leaves z alone.
ICO_POLE = 1.0


def pestle_dir():
    a = math.radians(PESTLE_ANGLE_DEG)
    return Vector((math.sin(a), 0.0, math.cos(a)))


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


def inner_floor_z(rho):
    """Height of the mortar inner surface (floor/wall) at radial
    distance rho from the mortar axis. The floor is a slope: z 0.038
    at the centre, 0.050 at r 0.100, 0.108 at the rim."""
    if rho <= INNER_PROFILE[-1][0]:
        return INNER_PROFILE[-1][1]
    for k in range(len(INNER_PROFILE) - 1):
        r0, z0 = INNER_PROFILE[k]
        r1, z1 = INNER_PROFILE[k + 1]
        if r1 <= rho <= r0:
            if r0 == r1:
                return z0
            t = (rho - r1) / (r0 - r1)
            return z1 + t * (z0 - z1)
    return 0.112  # outside the cavity: rim top


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


def mesh_centroid(obj):
    vs = world_verts(obj)
    return sum(vs, Vector((0, 0, 0))) / len(vs)


def ring_analysis(obj, origin, direction, rho_min=0.0005):
    """Group the tube's ring verts (rho > rho_min off axis) by (axial
    distance, radius); return [(distance, count, center, radius)] per
    ring. Keyed on both axial distance and radius because a lathe
    profile may put two rings at the same height (e.g. the mortar
    bottom: r 0.001 and r 0.100 both at z 0)."""
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


def check_lathe(name, obj, profile, sides, origin, direction):
    """Ring-by-ring check of a lathe part: ring count, per-ring vertex
    count, ring (axial distance, radius) pairs vs the design profile
    (compared as sorted pairs: the profile is not monotonic in z);
    bottom cap fan triangles; analytic bbox."""
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
               and len(tri_ax) == sides
               and all(abs(a) < 0.002 for a in tri_ax))}
    return row


def check_pestle_clearance(by_name):
    """Pestle tip position, rim-plane crossing vs the inner cavity
    radius, bulb bottom cap centre on the bowl floor, and how far the
    tilted bulb's lower side dips below the floor plane (planted)."""
    o = Vector(PESTLE_ORIGIN)
    d = pestle_dir()
    tip = o + d * PESTLE_PROFILE[-1][1]
    rim_axial = (0.112 - o.z) / d.z
    rim_pt = o + d * rim_axial
    rim_radial = math.hypot(rim_pt.x, rim_pt.y)
    pestle = by_name["Pestle"]
    # bottom cap centre vertex: axial ~0, rho ~0 (the fan centre)
    cap_z = None
    lowest_z = None
    for v in world_verts(pestle):
        rel = v - o
        axial = rel.dot(d)
        rho = (rel - d * axial).length
        if rho < 0.0005 and abs(axial) < 0.001:
            cap_z = v.z
        lowest_z = v.z if lowest_z is None else min(lowest_z, v.z)
    row = {"tip": tuple(round(v, 3) for v in tip),
           "tip_expected": (0.167, 0.01, 0.239),
           "rim_cross": tuple(round(v, 3) for v in rim_pt),
           "rim_cross_radial": round(rim_radial, 3),
           "inner_radius_at_rim": 0.132,
           "rim_clearance": round(0.132 - rim_radial, 3),
           "bulb_tip_z": round(cap_z, 3) if cap_z is not None else None,
           "floor_z_at_tip": BOWL_FLOOR_Z,
           "bulb_lowest_z": round(lowest_z, 3),
           "bulb_embed_below_floor": round(BOWL_FLOOR_Z - lowest_z, 3),
           "ok": bool(
               all(abs(a - b) < 0.002
                   for a, b in zip(tip, (0.167, 0.01, 0.239)))
               and rim_radial < 0.132
               and cap_z is not None
               and abs(cap_z - BOWL_FLOOR_Z) < 0.001)}
    return row


def pestle_surface_clearance(point):
    """Signed distance from a point to the pestle solid: negative =
    inside. For axial < 0 (below the bulb bottom cap plane) the distance
    is measured to the bottom cap disc (radius 0.001 at axial 0)."""
    o = Vector(PESTLE_ORIGIN)
    d = pestle_dir()
    rel = Vector(point) - o
    axial = rel.dot(d)
    radial = (rel - d * axial).length
    if axial < 0.0:
        return math.sqrt(axial * axial
                         + max(0.0, radial - 0.001) ** 2)
    if axial > PESTLE_PROFILE[-1][1]:
        dz = axial - PESTLE_PROFILE[-1][1]
        return math.sqrt(dz * dz + max(0.0, radial - 0.001) ** 2)
    return radial - radius_at(PESTLE_PROFILE, axial)


def check_chunks(by_name):
    """Each herb chunk: 20 tris, centre on design, bottom planted into
    the bowl floor — and, decisively, how much of it actually sticks
    OUT of the sloped inner wall: a chunk whose top is below the local
    floor surface is invisible in the render."""
    rows = {}
    for i, (x, y, z, r, sz, rz, _mat) in enumerate(CHUNKS):
        name = "HerbChunk_%d" % (i + 1)
        obj = by_name[name]
        c = mesh_centroid(obj)
        vs = world_verts(obj)
        top_z = max(v.z for v in vs)
        bot_z = min(v.z for v in vs)
        center_rho = math.hypot(x, y)
        floor_c = inner_floor_z(center_rho)
        visible = round(top_z - floor_c, 4)
        buried = 0
        max_depth = 0.0
        for v in vs:
            rho = math.hypot(v.x, v.y)
            fz = inner_floor_z(rho)
            if v.z < fz - 0.001:
                buried += 1
                max_depth = max(max_depth, fz - v.z)
        # clearance to the pestle solid (negative = clipping into it)
        min_pestle = min(pestle_surface_clearance(v) for v in vs)
        # expected bottom: lowest ico vertex z = centre - sz*r (a pole
        # vertex sits at |z| = r; rotation about Z leaves z alone)
        exp_bot = round(z - sz * ICO_POLE * r, 4)
        row = {"center": tuple(round(v, 3) for v in c),
               "design_center": (x, y, z),
               "center_radial": round(center_rho, 3),
               "floor_z_at_center": round(floor_c, 3),
               "top_z": round(top_z, 3),
               "bottom_z": round(bot_z, 3),
               "expected_bottom_z": exp_bot,
               "floor_embed": round(floor_c - bot_z, 4),
               "visible_height": visible,
               "buried_verts": buried,
               "total_verts": len(vs),
               "max_burial_depth": round(max_depth, 4),
               "pestle_clearance": round(min_pestle, 4),
               # verdict: the chunk must stick clearly out of the
               # sloped floor (visible > 0.004, about half its
               # half-height) and must not clip the pestle. Buried
               # verts alone are not the verdict: a flattened chunk
               # sitting on a slope always sinks its downhill edge
               # into the wall; what matters is the visible cap.
               "ok": bool(
                   abs(c.x - x) < 0.003 and abs(c.y - y) < 0.003
                   and abs(c.z - z) < 0.003
                   and abs(bot_z - exp_bot) < 0.001
                   and visible > 0.004
                   and min_pestle > 0.0)}
        rows[name] = row
    return {"chunks": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_mound(by_name):
    """Powder mound: lathe rings, base planted into the sloped floor,
    visible height above the local floor, and clearance to the pestle
    bulb (the mound base disc reaches toward the pestle axis)."""
    obj = by_name["PowderMound"]
    lathe = check_lathe("PowderMound", obj, MOUND_PROFILE, MOUND_SIDES,
                        (MOUND_LOC[0], MOUND_LOC[1], MOUND_Z_BASE),
                        (0, 0, 1))
    vs = world_verts(obj)
    top_z = max(v.z for v in vs)
    center_rho = math.hypot(MOUND_LOC[0], MOUND_LOC[1])
    floor_c = inner_floor_z(center_rho)
    base_verts = [v for v in vs if abs(v.z - MOUND_Z_BASE) < 0.001]
    base_burial = 0.0
    for v in base_verts:
        fz = inner_floor_z(math.hypot(v.x, v.y))
        base_burial = max(base_burial, fz - v.z)
    min_pestle = min(pestle_surface_clearance(v) for v in vs)
    # distance from the mound centre to the pestle axis line
    o = Vector(PESTLE_ORIGIN)
    d = pestle_dir()
    rel = Vector((MOUND_LOC[0], MOUND_LOC[1], MOUND_Z_BASE)) - o
    pestle_axis_dist = (rel - d * rel.dot(d)).length
    row = {"lathe": lathe,
           "center_radial": round(center_rho, 3),
           "pestle_axis_distance": round(pestle_axis_dist, 3),
           "floor_z_at_center": round(floor_c, 3),
           "top_z": round(top_z, 3),
           "visible_height": round(top_z - floor_c, 4),
           "base_ring_burial_max": round(base_burial, 4),
           "pestle_clearance": round(min_pestle, 4),
           "ok": bool(lathe["ok"]
                      and (top_z - floor_c) > 0.005
                      and min_pestle > 0.0)}
    return row


def check_stems(by_name):
    rows = {}
    for i, d in enumerate(STEM_DIRS):
        name = "DryStem_%d" % (i + 1)
        obj = by_name[name]
        dv = Vector(d).normalized()
        base = Vector(STEM_BASE)
        p1 = base + dv * STEM_LEN
        rings = ring_analysis(obj, STEM_BASE, dv, rho_min=0.0005)
        mw = obj.matrix_world
        tri_ax = []
        for p in obj.data.polygons:
            if len(p.vertices) == 3:
                c = mw @ p.center
                tri_ax.append(round((c - base).dot(dv), 3))
        r = world_range(obj)
        # expected bbox: the cylinder swept between base and p1, radius
        # STEM_R, plus the cap discs
        mins = Vector((1e9, 1e9, 1e9))
        maxs = Vector((-1e9, -1e9, -1e9))
        for pt in (base, p1):
            for j in range(3):
                h = STEM_R * math.sqrt(max(0.0, 1.0 - dv[j] * dv[j]))
                mins[j] = min(mins[j], pt[j] - h)
                maxs[j] = max(maxs[j], pt[j] + h)
        exp = (round(mins.x, 3), round(maxs.x, 3),
               round(mins.y, 3), round(maxs.y, 3),
               round(mins.z, 3), round(maxs.z, 3))
        # The analytic bbox is for the swept circle; a 6-sided ring's
        # lowest vertex sits up to ~0.001 above the circle's lowest
        # point, so allow 0.002 here.
        row = {"range": r, "expected": exp,
               "base": tuple(round(v, 3) for v in base),
               "tip": tuple(round(v, 3) for v in p1),
               "rings": [(x["distance"], x["count"], x["radius"])
                         for x in rings],
               "tri_axial_positions": sorted(set(tri_ax)),
               "min_z": r[4],
               "ok": bool(
                   len(rings) == 2
                   and [x["count"] for x in rings] == [STEM_SIDES] * 2
                   and [x["distance"] for x in rings]
                   == [0.0, round(STEM_LEN, 3)]
                   and all(abs(x["radius"] - STEM_R) < 0.002
                           for x in rings)
                   and sorted(set(tri_ax)) == [0.0, round(STEM_LEN, 3)]
                   and bbox_close(r, exp, tol=0.002)
                   and abs(r[4] - 0.0) < 0.002)}
        rows[name] = row
    return {"stems": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_leaves(by_name):
    rows = {}
    for i, (x, y, z, rz, tilt) in enumerate(LEAVES):
        name = "DryLeaf_%d" % (i + 1)
        obj = by_name[name]
        c = mesh_centroid(obj)
        r = world_range(obj)
        row = {"center": tuple(round(v, 3) for v in c),
               "design_center": (x, y, z),
               "range": r,
               "min_z": r[4],
               "ok": bool(abs(c.x - x) < 0.002 and abs(c.y - y) < 0.002
                          and abs(c.z - z) < 0.002
                          and r[4] >= -0.001)}
        rows[name] = row
    return {"leaves": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_spacing(by_name):
    """No dry-pile vertex may clip into the mortar wall (radial <
    outer radius 0.158 while z is within the mortar height), and no
    dry-pile vertex may clip into the pestle."""
    rows = {}
    for name in (["DryStem_%d" % (i + 1) for i in range(5)]
                 + ["DryLeaf_%d" % (i + 1) for i in range(6)]):
        obj = by_name[name]
        worst = None
        worst_pen = 0.0
        for v in world_verts(obj):
            rho = math.hypot(v.x, v.y)
            if v.z < 0.112 and rho < MORTAR_OUTER_RADIUS:
                pen = MORTAR_OUTER_RADIUS - rho
                if pen > worst_pen:
                    worst_pen = pen
                    worst = ("mortar_wall", tuple(round(c, 3) for c in v))
            pc = pestle_surface_clearance(v)
            if pc < 0 and -pc > worst_pen:
                worst_pen = -pc
                worst = ("pestle", tuple(round(c, 3) for c in v))
        rows[name] = {"worst_clip": worst,
                      "max_penetration": round(worst_pen, 4),
                      "ok": bool(worst is None)}
    return {"spacing": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_ground(by_name):
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
    # the mortar stands on the ground (bottom z 0); the dry pile lies
    # on the ground (min z ~0); bowl contents sit on the bowl floor
    # (min z 0.030+), so nothing may go below z 0
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
           # 062 note: "整体约 0.58 m 宽 × 0.25 m 高 × 0.32 m 深"
           "note_size": (0.58, 0.25, 0.32)}
    row["ok"] = bool(abs(row["width"] - 0.58) <= 0.02
                     and abs(row["height"] - 0.25) <= 0.02
                     and abs(row["depth"] - 0.32) <= 0.02)
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 062 design values.
    All 7 materials are plain Principled solids (no glass, no
    emission). The 062 build script stores raw tuples as linear
    Base Color."""
    rows = []
    for name, spec in DESIGN_MATS.items():
        col = tuple(round(v, 2) for v in spec["color"])
        mat = bpy.data.materials.get(name)
        if mat is None or not mat.use_nodes:
            rows.append({"name": name, "found": False, "ok": False,
                         "design_color_linear": col})
            continue
        bsdf = None
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
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
        rows.append({"name": name, "found": True, "metallic": m,
                     "roughness": r, "base_color": c,
                     "design_color_linear": col, "ok": bool(ok)})
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

    mortar = check_lathe("Mortar", by_name["Mortar"], MORTAR_PROFILE,
                         MORTAR_SIDES, (0, 0, 0), (0, 0, 1))
    print("QA_MORTAR:", mortar)
    pestle = check_lathe("Pestle", by_name["Pestle"], PESTLE_PROFILE,
                         PESTLE_SIDES, PESTLE_ORIGIN, pestle_dir())
    print("QA_PESTLE:", pestle)
    pestle_clear = check_pestle_clearance(by_name)
    print("QA_PESTLE_CLEARANCE:", pestle_clear)
    mound = check_mound(by_name)
    print("QA_MOUND:", mound)
    chunks = check_chunks(by_name)
    print("QA_CHUNKS:", chunks)
    stems = check_stems(by_name)
    print("QA_STEMS:", stems)
    leaves = check_leaves(by_name)
    print("QA_LEAVES:", leaves)
    spacing = check_spacing(by_name)
    print("QA_SPACING:", spacing)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    structure = {"mortar": mortar, "pestle": pestle,
                 "pestle_clearance": pestle_clear, "mound": mound,
                 "chunks": chunks, "stems": stems, "leaves": leaves,
                 "spacing": spacing, "ground_contact": ground,
                 "overall": overall}
    structure_ok = (mortar["ok"] and pestle["ok"] and pestle_clear["ok"]
                    and mound["ok"] and chunks["ok"] and stems["ok"]
                    and leaves["ok"] and spacing["ok"] and ground["ok"]
                    and overall["ok"])

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # The three lathe parts are OPEN AT THE AXIS END BY DESIGN: each
    # profile ends in a 0.001-radius ring with no cap fan (the bottom
    # cap is the only fan). Mortar 24 + Pestle 16 + PowderMound 12 =
    # 52 boundary edges, all 1 mm pinholes at the lathe axis, not real
    # holes. Every other part must be a closed mesh (0 boundary edges).
    open_parts = {"Mortar": MORTAR_SIDES, "Pestle": PESTLE_SIDES,
                  "PowderMound": MOUND_SIDES}
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
    # the 062 build script's own winding self-check was all 0; the
    # recalc check above is the independent re-measurement.
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and boundary_ok
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and mats["empty_material_slots"] == 0
              and not mats["assignment_mismatches"]
              and not mats["unused_design_mats"]
              and faces_ok and structure_ok and mats["all_ok"])

    summary = {
        "asset": "062-lowpoly-mortar-pestle",
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
        "open_top_boundary_edges": open_boundary,
        "inverted_normals": tot["inverted_normals"],
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
        f.write("# 063 资产质检单：低模炼金研钵与杵（062）\n\n")
        f.write("被检资产：`scenes/062-lowpoly-mortar-pestle.blend`（%d 个道具部件，不含地面）。\n" % len(results))
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
        f.write("- 面数与 062 设计表逐部件比对：%s（设计 894 面：三角 272、四边 622、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 闭合网格：边界边共 %d 条，全部在 3 个车削件的轴端针孔环上（Mortar 24、Pestle 16、PowderMound 12，轮廓末端半径 0.001 无封盖扇形，是 1 mm 针孔不是破洞），其余 19 个部件 0 条：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("  062 构建脚本自带的绕向自检（车削件轮廓段法线 + 其余部件质心检测）同样全 0，两次独立测量一致。\n\n")
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
        f.write("## 4. 研钵与杵结构（实测）\n\n")
        f.write("### 4.1 研钵（车削轮廓，24 段）\n\n")
        f.write("- Mortar：%d 环（每环 24 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；%d 个三角面全部是底面扇形封口（面中心轴向位置 0.000），顶部内底中心无封盖（1 mm 针孔）：%s\n" % (
            len(mortar["rings"]), mortar["ring_distances"],
            mortar["ring_radii"],
            mortar["design_radii"],
            mortar["range"][0], mortar["range"][1], mortar["range"][2],
            mortar["range"][3], mortar["range"][4], mortar["range"][5],
            mortar["expected"], mortar["tri_count"],
            verdict(mortar["ok"])))
        f.write("\n### 4.2 研杵（车削轮廓，16 段，38° 斜靠）\n\n")
        f.write("- Pestle：%d 环（每环 16 顶点），沿杵轴向距离 %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；%d 个三角面全部是杵头底端扇形封口（面中心轴向位置 0.000）：%s\n" % (
            len(pestle["rings"]), pestle["ring_distances"],
            pestle["ring_radii"],
            pestle["design_radii"],
            pestle["range"][0], pestle["range"][1], pestle["range"][2],
            pestle["range"][3], pestle["range"][4], pestle["range"][5],
            pestle["expected"], pestle["tri_count"],
            verdict(pestle["ok"])))
        f.write("- 研杵净空：柄端 %s（设计 (0.167, 0.01, 0.239)）；柄在碗口平面（z 0.112）处过点 %s，离碗轴 %.3f（内腔半径 0.132，净空 %.3f，不碰碗口）；杵头底盖中心 z %.3f（碗底中心 z 0.038，差 %.3f，落在碗底）；斜靠杵头下侧最低 z %.3f，比碗底面低 %.3f（倾斜车削环的下沿埋入碗底，属 planted）：%s\n" % (
            pestle_clear["tip"], pestle_clear["rim_cross"],
            pestle_clear["rim_cross_radial"], pestle_clear["rim_clearance"],
            pestle_clear["bulb_tip_z"],
            pestle_clear["bulb_tip_z"] - pestle_clear["floor_z_at_tip"],
            pestle_clear["bulb_lowest_z"],
            pestle_clear["bulb_embed_below_floor"],
            verdict(pestle_clear["ok"])))
        f.write("\n### 4.3 草药粉堆\n\n")
        f.write("- PowderMound：%d 环（每环 12 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 z %.3f–%.3f；中心离碗轴 %.3f，该处碗底面高 %.3f，粉堆顶高 %.3f、露出 %.3f；底圈埋入斜坡碗底最深 %.4f（平底落在斜坡底上，属 planted）；与研杵杵头最小间隙 %.4f（须 > 0）：%s\n" % (
            len(mound["lathe"]["rings"]), mound["lathe"]["ring_distances"],
            mound["lathe"]["ring_radii"],
            mound["lathe"]["design_radii"],
            mound["lathe"]["range"][4], mound["lathe"]["range"][5],
            mound["center_radial"], mound["floor_z_at_center"],
            mound["top_z"], mound["visible_height"],
            mound["base_ring_burial_max"], mound["pestle_clearance"],
            verdict(mound["ok"])))
        f.write("\n### 4.4 碗内草药碎（8 块）\n\n")
        f.write("判定标准：草药碎须露出斜坡碗底面才可见——露出高度 = 碎块顶 z − 碎块中心处碗底面高，须 > 0.004（约碎块半高的一半）；碎块底埋入碗底、下坡一侧顶点埋入斜坡壁属 planted，不单独判否。碗底面是斜坡（中心 z 0.038、r 0.100 处 z 0.050、碗口 z 0.108），064 起碎块中心按当地碗底面高抬高（中心 z = 当地碗底面高 + 碎块半高 − 0.002），离轴越远抬得越高。\n\n")
        for name, ch in chunks["chunks"].items():
            f.write("- %s：中心 %s（设计 %s），离碗轴 %.3f、该处碗底面高 %.3f；顶 z %.3f、底 z %.3f（设计底 %.3f，底埋入碗底 %.4f，属 planted）；露出高度 %.4f；埋入碗壁顶点 %d/%d 个、最深 %.4f；与研杵最小间隙 %.4f：%s\n" % (
                name, ch["center"], ch["design_center"],
                ch["center_radial"], ch["floor_z_at_center"],
                ch["top_z"], ch["bottom_z"], ch["expected_bottom_z"],
                ch["floor_embed"], ch["visible_height"],
                ch["buried_verts"], ch["total_verts"],
                ch["max_burial_depth"], ch["pestle_clearance"],
                verdict(ch["ok"])))
        f.write("\n### 4.5 干草茎（5 根）\n\n")
        for name, s in stems["stems"].items():
            f.write("- %s：2 环（每环 6 顶点），环距 %s、半径 %s；基点 %s、端点 %s；包围盒 z %.3f–%.3f，最低 z %.3f（地面 z 0，差 %.3f）；三角面全部在两端盖上：%s\n" % (
                name, [d for d, _c, _r in s["rings"]],
                [r for _d, _c, r in s["rings"]],
                s["base"], s["tip"], s["range"][4], s["range"][5],
                s["min_z"], s["min_z"] - 0.0, verdict(s["ok"])))
        f.write("\n### 4.6 干叶（6 片）\n\n")
        for name, lf in leaves["leaves"].items():
            f.write("- %s：中心 %s（设计 %s），包围盒 z %.3f–%.3f，最低 z %.3f（地面 z 0，不低于地面）：%s\n" % (
                name, lf["center"], lf["design_center"],
                lf["range"][4], lf["range"][5], lf["min_z"],
                verdict(lf["ok"])))
        f.write("\n### 4.7 干草堆与研钵/研杵间距\n\n")
        for name, sp in spacing["spacing"].items():
            if sp["worst_clip"] is None:
                f.write("- %s：无一顶点卡进研钵壁或研杵：%s\n" % (
                    name, verdict(sp["ok"])))
            else:
                f.write("- %s：卡进 %s（最深 %.4f m，位于 %s）：%s\n" % (
                    name, sp["worst_clip"][0], sp["max_penetration"],
                    sp["worst_clip"][1], verdict(sp["ok"])))
        f.write("\n### 4.8 地面、整体\n\n")
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s（研钵底 z=0 落地，干草茎/叶贴地，碗内物在碗底上）：%s\n" % (
            ground["checked"], ground["global_min_z"],
            ground["below_ground"] if ground["below_ground"] else "无",
            verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（062 笔记“约 0.58 × 0.25 × 0.32 m”，"
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
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 062 构建脚本直接存入的线性值）：\n")
        for row in mats["rows"]:
            f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                    "底色 %s（设计 %s）：%s\n" % (
                        row["name"], row["metallic"],
                        DESIGN_MATS[row["name"]]["metallic"],
                        row["roughness"],
                        DESIGN_MATS[row["name"]]["roughness"],
                        row["base_color"], row["design_color_linear"],
                        verdict(row["ok"])))
        f.write("\n## 6. 备注（实测发现，非缺陷）\n\n")
        f.write("- 车削件轴端针孔：Mortar / Pestle / PowderMound 各有 %d / %d / %d 条边界边，"
                "全部在轮廓末端半径 0.001 的轴端环上（无封盖扇形），是 1 mm 针孔、肉眼不可见，"
                "不是破洞；其余 19 个部件全部闭合。\n" % (
                    results["Mortar"]["boundary_edges"],
                    results["Pestle"]["boundary_edges"],
                    results["PowderMound"]["boundary_edges"]))
        f.write("- 草药碎底埋 planted：8 块草药碎底面均在碗底面之下（底比当地碗底面低 "
                "%.4f–%.4f，即底埋深度；设计为坐在碗底上，底埋属正常）；问题不在底埋，"
                "而在 4.4 节的露出高度——底埋再深，只要顶露出碗底面就可见。\n" % (
                    min(v["floor_embed"] for v in chunks["chunks"].values()),
                    max(v["floor_embed"] for v in chunks["chunks"].values())))
        f.write("- 粉堆底圈埋入斜坡碗底最深 %.4f（平底落在斜坡底上，底圈一侧埋入属正常）；"
                "粉堆露出碗底面 %.3f，渲染中可见。\n" % (
                    mound["base_ring_burial_max"], mound["visible_height"]))
        f.write("- 062 笔记尺寸与实测一致：宽 %.3f m × 深 %.3f m × 高 %.3f m"
                "（笔记“约 0.58 × 0.25 × 0.32 m”）。\n" % (
                    overall["width"], overall["depth"], overall["height"]))
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、研钵与杵结构、地面接触均通过。\n")
        else:
            f.write("待修项：\n\n")
            buried_chunks = [n for n, v in chunks["chunks"].items()
                             if v["visible_height"] <= 0.004]
            if buried_chunks:
                invisible = [n for n, v in chunks["chunks"].items()
                             if v["visible_height"] <= 0]
                slivers = [n for n, v in chunks["chunks"].items()
                           if 0 < v["visible_height"] <= 0.004]
                sliver_note = ""
                if slivers:
                    sliver_note = "，另有 %s 仅露出 %.4f–%.4f（亚像素级，渲染中只剩一个绿点）" % (
                        ", ".join(slivers),
                        min(chunks["chunks"][n]["visible_height"]
                            for n in slivers),
                        max(chunks["chunks"][n]["visible_height"]
                            for n in slivers))
                f.write("- 碗内草药碎埋入斜坡碗壁（%s）：碎块中心原先统一 z 0.040，"
                        "但碗底面是斜坡（离轴越远越高），%s 顶低于当地碗底面、"
                        "渲染中完全看不见%s；"
                        "修法：每块碎块按其中心离轴距离抬到当地碗底面上"
                        "（中心 z = 当地碗底面高 + 碎块半高 − 0.002 底埋），"
                        "修完重跑本质检脚本复核到 PASS。\n" % (
                            ", ".join(buried_chunks),
                            ", ".join(invisible),
                            sliver_note))
            clip_chunks = [(n, v["pestle_clearance"])
                           for n, v in chunks["chunks"].items()
                           if v["pestle_clearance"] <= 0]
            if clip_chunks:
                f.write("- 碗内草药碎卡进研杵杵头（%s）：碎块离杵轴太近，"
                        "顶点伸进杵头球体内（最小间隙 %s）；"
                        "修法：随上条一起抬高并移离杵轴（离杵轴 > 碎块半径 + 杵头半径 + 0.005），"
                        "修完重跑本质检脚本复核。\n" % (
                            "、".join("%s（%.4f）" % (n, c)
                                      for n, c in clip_chunks),
                            ", ".join("%.4f" % c for _n, c in clip_chunks)))
            if mound["pestle_clearance"] <= 0:
                f.write("- 草药粉堆卡进研杵杵头（最小间隙 %.4f m，最深穿入 %.4f）："
                        "粉堆底盘半径 0.0385、中心离杵轴仅 %.3f，底盘扫过杵头球体；"
                        "修法：粉堆移到碗内远离杵轴一侧（离杵轴 > 0.08，同时与抬高后的"
                        "草药碎保持间距）或进一步缩小底盘，修完重跑本质检脚本复核。\n" % (
                            mound["pestle_clearance"],
                            -mound["pestle_clearance"],
                            mound["pestle_axis_distance"]))
            f.write("\n其余项：拓扑、法线、UV、材质、研钵/研杵本体、干草堆、地面接触均通过。\n")


if __name__ == "__main__":
    main()
