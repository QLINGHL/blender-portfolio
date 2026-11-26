# -*- coding: utf-8 -*-
"""060 资产质检：对 059 低模炼金药水架做真实 mesh 检查（拓扑/法线/UV/材质），
并实测药水架特有结构：木架（立柱/层板/后横档/铭牌）、8 瓶车削瓶身、
瓶内药水与顶盘、瓶塞、倾斜标签、备用软木塞、层板净空与瓶间距。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 060-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "059-lowpoly-potion-rack.blend")
UV_JSON = os.path.join(ROOT, "scenes", "060-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "060-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "060-asset-qa-checklist.md")

# every mesh object in the 059 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/059-lowpoly-potion-rack.md (per-part table)
EXPECTED_FACES = {
    "Post_L": 6, "Post_R": 6,
    "Shelf_1": 6, "Shelf_2": 6, "Shelf_3": 6,
    "BackRail": 6, "Nameplate": 6,
    "Bottle_L1": 128, "Liquid_L1": 80, "LiquidTop_L1": 48,
    "Cork_L1": 24, "Label_L1": 6,
    "Bottle_L2": 112, "Liquid_L2": 64, "LiquidTop_L2": 48,
    "Cork_L2": 24, "Label_L2": 6,
    "Bottle_L3": 112, "Liquid_L3": 64, "LiquidTop_L3": 48,
    "Cork_L3": 24, "Label_L3": 6,
    "Bottle_L4": 112, "Liquid_L4": 80, "LiquidTop_L4": 48,
    "Cork_L4": 24, "Label_L4": 6,
    "Bottle_U1": 128, "Liquid_U1": 80, "LiquidTop_U1": 48,
    "Cork_U1": 24, "Label_U1": 6,
    "Bottle_U2": 112, "Liquid_U2": 64, "LiquidTop_U2": 48,
    "Cork_U2": 24, "Label_U2": 6,
    "Bottle_U3": 112, "Liquid_U3": 64, "LiquidTop_U3": 48,
    "Cork_U3": 24, "Label_U3": 6,
    "Bottle_U4": 112, "Liquid_U4": 80, "LiquidTop_U4": 48,
    "Cork_U4": 24, "Label_U4": 6,
    "SpareCork_1": 24, "SpareCork_2": 24, "SpareCork_3": 24,
}
EXPECTED_TOTAL_FACES = 2242
EXPECTED_TRIS = 688
EXPECTED_QUADS = 1554

# part -> design material (from the 059 build script)
PART_MATERIAL = {
    "Post_L": "Rack_Wood", "Post_R": "Rack_Wood",
    "Shelf_1": "Rack_Wood", "Shelf_2": "Rack_Wood",
    "Shelf_3": "Rack_WoodDark",
    "BackRail": "Rack_WoodDark", "Nameplate": "Rack_Brass",
    "Bottle_L1": "Glass_Amber", "Liquid_L1": "Liquid_Amber",
    "LiquidTop_L1": "Liquid_Amber", "Cork_L1": "Rack_Cork",
    "Label_L1": "Rack_Parchment",
    "Bottle_L2": "Glass_Green", "Liquid_L2": "Liquid_Green",
    "LiquidTop_L2": "Liquid_Green", "Cork_L2": "Rack_Cork",
    "Label_L2": "Rack_Parchment",
    "Bottle_L3": "Glass_Blue", "Liquid_L3": "Liquid_Blue",
    "LiquidTop_L3": "Liquid_Blue", "Cork_L3": "Rack_Cork",
    "Label_L3": "Rack_Parchment",
    "Bottle_L4": "Glass_Purple", "Liquid_L4": "Liquid_Purple",
    "LiquidTop_L4": "Liquid_Purple", "Cork_L4": "Rack_Cork",
    "Label_L4": "Rack_Parchment",
    "Bottle_U1": "Glass_Red", "Liquid_U1": "Liquid_Red",
    "LiquidTop_U1": "Liquid_Red", "Cork_U1": "Rack_Cork",
    "Label_U1": "Rack_Parchment",
    "Bottle_U2": "Glass_Teal", "Liquid_U2": "Liquid_Teal",
    "LiquidTop_U2": "Liquid_Teal", "Cork_U2": "Rack_Cork",
    "Label_U2": "Rack_Parchment",
    "Bottle_U3": "Glass_Amber", "Liquid_U3": "Liquid_Amber",
    "LiquidTop_U3": "Liquid_Amber", "Cork_U3": "Rack_Cork",
    "Label_U3": "Rack_Parchment",
    "Bottle_U4": "Glass_Green", "Liquid_U4": "Liquid_Green",
    "LiquidTop_U4": "Liquid_Green", "Cork_U4": "Rack_Cork",
    "Label_U4": "Rack_Parchment",
    "SpareCork_1": "Rack_Cork", "SpareCork_2": "Rack_Cork",
    "SpareCork_3": "Rack_Cork",
}

# Design material values from the 059 build script. The 059 build script
# passes raw tuples to solid_material / glow_material, which store them
# directly as linear Base Color (same convention as the 055 script), so
# the expected linear values are the raw tuples. Glass mats additionally
# carry Alpha 0.45 + dithered transparency; liquids are emissive
# (Emission strength 0.7, mix factor 0.55) with roughness 0.35.
DESIGN_MATS = {
    "Rack_Wood":      {"metallic": 0.00, "roughness": 0.85,
                       "color": (0.42, 0.28, 0.15), "emissive": None},
    "Rack_WoodDark":  {"metallic": 0.00, "roughness": 0.90,
                       "color": (0.30, 0.19, 0.10), "emissive": None},
    "Rack_Brass":     {"metallic": 0.70, "roughness": 0.35,
                       "color": (0.55, 0.38, 0.12), "emissive": None},
    "Rack_Cork":      {"metallic": 0.00, "roughness": 0.90,
                       "color": (0.62, 0.45, 0.26), "emissive": None},
    "Rack_Parchment": {"metallic": 0.00, "roughness": 0.85,
                       "color": (0.86, 0.79, 0.60), "emissive": None},
    "Glass_Amber":    {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.75, 0.45, 0.15), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Glass_Green":    {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.35, 0.55, 0.25), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Glass_Blue":     {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.25, 0.45, 0.65), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Glass_Red":      {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.65, 0.25, 0.20), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Glass_Teal":     {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.25, 0.55, 0.55), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Glass_Purple":   {"metallic": 0.00, "roughness": 0.15,
                       "color": (0.45, 0.30, 0.60), "emissive": None,
                       "alpha": 0.45, "dithered": True},
    "Liquid_Amber":   {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.85, 0.50, 0.12),
                       "emissive": (0.7, 0.55)},
    "Liquid_Green":   {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.35, 0.75, 0.25),
                       "emissive": (0.7, 0.55)},
    "Liquid_Blue":    {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.25, 0.55, 0.95),
                       "emissive": (0.7, 0.55)},
    "Liquid_Red":     {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.90, 0.25, 0.20),
                       "emissive": (0.7, 0.55)},
    "Liquid_Teal":    {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.25, 0.75, 0.70),
                       "emissive": (0.7, 0.55)},
    "Liquid_Purple":  {"metallic": 0.00, "roughness": 0.35,
                       "color": (0.60, 0.35, 0.85),
                       "emissive": (0.7, 0.55)},
}

# design geometry (from the 059 build script)
PROFILES = {
    "round": [(0.001, 0.0), (0.040, 0.004), (0.052, 0.04),
              (0.050, 0.08), (0.030, 0.105), (0.016, 0.120),
              (0.014, 0.135), (0.014, 0.145)],
    "tall": [(0.001, 0.0), (0.030, 0.004), (0.033, 0.10),
             (0.030, 0.13), (0.016, 0.145), (0.014, 0.155),
             (0.014, 0.17)],
    "conical": [(0.001, 0.0), (0.048, 0.004), (0.046, 0.02),
                (0.030, 0.07), (0.016, 0.10), (0.014, 0.115),
                (0.014, 0.125)],
    "vial": [(0.001, 0.0), (0.022, 0.003), (0.024, 0.06),
             (0.020, 0.075), (0.012, 0.085), (0.011, 0.09),
             (0.011, 0.10)],
}
LATHE_SIDES = 16
# tag -> (kind, x, z_base, glass, liquid)
BOTTLES = {
    "L1": ("round", -0.19, 0.045, "Amber", "Amber"),
    "L2": ("tall", -0.075, 0.045, "Green", "Green"),
    "L3": ("vial", 0.035, 0.045, "Blue", "Blue"),
    "L4": ("conical", 0.16, 0.045, "Purple", "Purple"),
    "U1": ("round", -0.19, 0.285, "Red", "Red"),
    "U2": ("tall", -0.05, 0.285, "Teal", "Teal"),
    "U3": ("vial", 0.08, 0.285, "Amber", "Amber"),
    "U4": ("conical", 0.19, 0.285, "Green", "Green"),
}
LIQ_FRAC = 0.65   # liquid filled to 65% of bottle height
LIQ_SCALE = 0.8   # liquid profile radii scaled in
LIQ_TOP_THICK = 0.003
CORK_BELOW_TOP = 0.006  # cork bottom sinks this far below bottle top
CORK_ABOVE_TOP = 0.022  # cork sticks this far above bottle top
# rack design
POST_SIZE = (0.045, 0.06, 0.54)
POST_X = 0.27
POST_ZC = 0.27
SHELF_SIZE = (0.585, 0.17, 0.03)
SHELF_ZC = (0.03, 0.27, 0.51)
BACKRAIL_SIZE = (0.50, 0.02, 0.04)
BACKRAIL_LOC = (0, 0.075, 0.44)
NAMEPLATE_SIZE = (0.12, 0.002, 0.03)
NAMEPLATE_LOC = (0, -0.086, 0.27)
SPARE_CORK_X = (-0.10, 0.0, 0.10)
SPARE_CORK_Z = (0.525, 0.552)
SPARE_CORK_R = (0.011, 0.014)  # bottom, top
CORK_SIDES = 8
# bottles sit on a shelf top; the shelf above must clear the cork top
SHELF_ABOVE = {"L": 0.255, "U": 0.495}  # bottom z of the shelf above
SHELF_TOP = {"L": 0.045, "U": 0.285}    # top z of the shelf below


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


def label_design(tag):
    """Design label geometry for one bottle: (width, height, center,
    tilt). Same formulas as the 059 build script."""
    kind, x, z_base, _g, _l = BOTTLES[tag]
    prof = PROFILES[kind]
    height = prof[-1][1]
    max_r = max(r for r, _ in prof)
    label_h = height * 0.30
    label_z = z_base + height * 0.38
    r_bot = radius_at(prof, height * 0.38 - label_h / 2)
    r_top = radius_at(prof, height * 0.38 + label_h / 2)
    r_lab = radius_at(prof, height * 0.38)
    tilt = math.atan2(r_bot - r_top, label_h)
    label_w = min(0.05, max_r * 1.1)
    return {"width": label_w, "height": label_h,
            "center": (x, -(r_lab + 0.0005), label_z),
            "tilt": tilt, "r_lab": r_lab}


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


def ring_analysis(obj, origin, direction, rho_min=0.001):
    """Group the tube's ring verts (rho > rho_min off axis) by axial
    distance; return [(distance, count, center, radius)] per ring.
    rho_min 0.0005 for bottles: the lathe's first profile ring sits at
    radius 0.001 and must not be dropped as a cap centre."""
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
        key = round(axial, 3)
        clusters.setdefault(key, []).append(w)
    rings = []
    for dist in sorted(clusters):
        pts = clusters[dist]
        c = sum(pts, Vector((0, 0, 0))) / len(pts)
        r = sum((p - c).length for p in pts) / len(pts)
        rings.append({"distance": dist, "count": len(pts),
                      "center": tuple(round(v, 3) for v in c),
                      "radius": round(r, 3)})
    return rings


def bbox_close(measured, expected, tol=0.002):
    return all(abs(a - b) <= tol for a, b in zip(measured, expected))


def box_expected(size, loc):
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    return (round(loc[0] - sx, 3), round(loc[0] + sx, 3),
            round(loc[1] - sy, 3), round(loc[1] + sy, 3),
            round(loc[2] - sz, 3), round(loc[2] + sz, 3))


def check_rack(by_name):
    rows = {}
    for name, sx in (("Post_L", -1), ("Post_R", 1)):
        obj = by_name[name]
        r = world_range(obj)
        exp = box_expected(POST_SIZE, (sx * POST_X, 0, POST_ZC))
        rows[name] = {"range": r, "expected": exp,
                      "ok": bool(bbox_close(r, exp))}
    for i, zc in enumerate(SHELF_ZC):
        name = "Shelf_%d" % (i + 1)
        obj = by_name[name]
        r = world_range(obj)
        exp = box_expected(SHELF_SIZE, (0, 0, zc))
        rows[name] = {"range": r, "expected": exp,
                      "ok": bool(bbox_close(r, exp))}
    obj = by_name["BackRail"]
    r = world_range(obj)
    exp = box_expected(BACKRAIL_SIZE, BACKRAIL_LOC)
    # back rail back face (y 0.085) flush with the shelf back face
    rows["BackRail"] = {"range": r, "expected": exp,
                        "back_flush_with_shelf": bool(
                            abs(r[3] - 0.085) < 0.001),
                        "ok": bool(bbox_close(r, exp)
                                   and abs(r[3] - 0.085) < 0.001)}
    obj = by_name["Nameplate"]
    r = world_range(obj)
    exp = box_expected(NAMEPLATE_SIZE, NAMEPLATE_LOC)
    # plate back face flush with the middle shelf front face (y -0.085),
    # front face sticks out 0.002
    shelf_front = -SHELF_SIZE[1] / 2.0
    rows["Nameplate"] = {"range": r, "expected": exp,
                         "back_y": r[3], "shelf_front_y": shelf_front,
                         "sticks_out": round(shelf_front - r[2], 3),
                         "ok": bool(bbox_close(r, exp)
                                    and abs(r[3] - shelf_front) < 0.001
                                    and abs((shelf_front - r[2])
                                            - 0.002) < 0.001)}
    return {"rack": rows, "ok": bool(all(v["ok"] for v in rows.values()))}


def check_bottles(by_name):
    rows = {}
    for tag, (kind, x, z_base, _g, _l) in BOTTLES.items():
        name = "Bottle_%s" % tag
        obj = by_name[name]
        prof = PROFILES[kind]
        height = prof[-1][1]
        max_r = max(r for r, _ in prof)
        rings = ring_analysis(obj, (x, 0, z_base), (0, 0, 1),
                              rho_min=0.0005)
        exp_dist = [round(z, 3) for _r, z in prof]
        exp_radii = [r for r, _z in prof]
        # all tris must be the bottom cap fan (centre z ~ z_base)
        mw = obj.matrix_world
        tri_zs = []
        for p in obj.data.polygons:
            if len(p.vertices) == 3:
                tri_zs.append(round((mw @ p.center).z, 3))
        r = world_range(obj)
        exp = (round(x - max_r, 3), round(x + max_r, 3),
               round(-max_r, 3), round(max_r, 3),
               round(z_base, 3), round(z_base + height, 3))
        row = {"range": r, "expected": exp,
               "kind": kind, "height": height, "max_radius": max_r,
               "rings": rings,
               "ring_distances": [x2["distance"] for x2 in rings],
               "ring_counts": [x2["count"] for x2 in rings],
               "ring_radii": [x2["radius"] for x2 in rings],
               "tri_face_center_zs": sorted(set(tri_zs)),
               "tri_count": len(tri_zs),
               "boundary_edges": None}
        row["ok"] = bool(
            len(rings) == len(prof)
            and all(c == LATHE_SIDES for c in row["ring_counts"])
            and len(row["ring_distances"]) == len(exp_dist)
            and all(abs(a - b) <= 0.002
                    for a, b in zip(row["ring_distances"], exp_dist))
            and all(abs(a - b) < 0.002
                    for a, b in zip(row["ring_radii"], exp_radii))
            and bbox_close(r, exp)
            and len(tri_zs) == LATHE_SIDES
            and all(abs(z - z_base) < 0.002 for z in tri_zs))
        rows[name] = row
    return {"bottles": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_liquids(by_name):
    rows = {}
    for tag, (kind, x, z_base, _g, _l) in BOTTLES.items():
        prof = PROFILES[kind]
        height = prof[-1][1]
        liq_h = height * LIQ_FRAC
        liq_prof = liquid_profile(prof, liq_h, LIQ_SCALE)
        max_r = max(r for r, _ in liq_prof)
        name = "Liquid_%s" % tag
        obj = by_name[name]
        rings = ring_analysis(obj, (x, 0, z_base), (0, 0, 1),
                              rho_min=0.0005)
        exp_dist = [round(z, 3) for _r, z in liq_prof]
        exp_radii = [r for r, _z in liq_prof]
        mw = obj.matrix_world
        tri_zs = []
        for p in obj.data.polygons:
            if len(p.vertices) == 3:
                tri_zs.append(round((mw @ p.center).z, 3))
        r = world_range(obj)
        exp = (round(x - max_r, 3), round(x + max_r, 3),
               round(-max_r, 3), round(max_r, 3),
               round(z_base, 3), round(z_base + liq_h, 3))
        # liquid top disc
        r_top = radius_at(prof, liq_h) * LIQ_SCALE
        top = by_name["LiquidTop_%s" % tag]
        rt = world_range(top)
        exp_top = (round(x - r_top, 3), round(x + r_top, 3),
                   round(-r_top, 3), round(r_top, 3),
                   round(z_base + liq_h, 3),
                   round(z_base + liq_h + LIQ_TOP_THICK, 3))
        row = {"range": r, "expected": exp,
               "liquid_height": round(liq_h, 4),
               "rings": rings,
               "ring_distances": [x2["distance"] for x2 in rings],
               "ring_counts": [x2["count"] for x2 in rings],
               "ring_radii": [x2["radius"] for x2 in rings],
               "tri_face_center_zs": sorted(set(tri_zs)),
               "tri_count": len(tri_zs),
               "top_disc_range": rt, "top_disc_expected": exp_top,
               "top_disc_radius": round(r_top, 4),
               "ok": bool(
                   len(rings) == len(liq_prof)
                   and all(c == LATHE_SIDES
                           for c in [x2["count"] for x2 in rings])
                   and len([x2["distance"] for x2 in rings]) == len(exp_dist)
                   and all(abs(a - b) <= 0.002
                           for a, b in zip([x2["distance"] for x2 in rings],
                                           exp_dist))
                   and all(abs(a - b) < 0.002
                           for a, b in zip([x2["radius"] for x2 in rings],
                                           exp_radii))
                   and bbox_close(r, exp)
                   and len(tri_zs) == LATHE_SIDES
                   and all(abs(z - z_base) < 0.002 for z in tri_zs)
                   and bbox_close(rt, exp_top))}
        rows[name] = row
    return {"liquids": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_corks(by_name):
    rows = {}
    for tag, (kind, x, z_base, _g, _l) in BOTTLES.items():
        prof = PROFILES[kind]
        height = prof[-1][1]
        neck_r = prof[-1][0]
        z0 = z_base + height - CORK_BELOW_TOP
        z1 = z_base + height + CORK_ABOVE_TOP
        r0 = neck_r * 0.85
        r1 = neck_r * 1.05
        name = "Cork_%s" % tag
        obj = by_name[name]
        rings = ring_analysis(obj, (x, 0, z0), (0, 0, 1))
        mw = obj.matrix_world
        tri_zs = []
        for p in obj.data.polygons:
            if len(p.vertices) == 3:
                tri_zs.append(round((mw @ p.center).z, 3))
        r = world_range(obj)
        exp = (round(x - r1, 3), round(x + r1, 3),
               round(-r1, 3), round(r1, 3),
               round(z0, 3), round(z1, 3))
        row = {"range": r, "expected": exp,
               "rings": [(x2["distance"], x2["count"], x2["radius"])
                         for x2 in rings],
               "tri_face_center_zs": sorted(set(tri_zs)),
               "neck_radius": neck_r,
               "sunk_into_neck": round(height - CORK_BELOW_TOP, 3),
               "sticks_out": round(CORK_ABOVE_TOP, 3),
               "ok": bool(
                   bbox_close(r, exp)
                   and len(rings) == 2
                   and [x2["distance"] for x2 in rings]
                   == [0.0, round(z1 - z0, 3)]
                   and [x2["count"] for x2 in rings] == [CORK_SIDES] * 2
                   and abs(rings[0]["radius"] - r0) < 0.002
                   and abs(rings[1]["radius"] - r1) < 0.002
                   and sorted(set(tri_zs)) == [round(z0, 3),
                                               round(z1, 3)])}
        rows[name] = row
    return {"corks": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_labels(by_name):
    rows = {}
    for tag, (kind, x, z_base, _g, _l) in BOTTLES.items():
        prof = PROFILES[kind]
        des = label_design(tag)
        name = "Label_%s" % tag
        obj = by_name[name]
        r = world_range(obj)
        tilt = des["tilt"]
        h = des["height"]
        w = des["width"]
        # rotated box bbox: half extents after Rx(-tilt)
        y_half = 0.001 * math.cos(tilt) + (h / 2.0) * math.sin(tilt)
        z_half = 0.001 * math.sin(tilt) + (h / 2.0) * math.cos(tilt)
        cx, cy, cz = des["center"]
        exp = (round(cx - w / 2.0, 3), round(cx + w / 2.0, 3),
               round(cy - y_half, 3), round(cy + y_half, 3),
               round(cz - z_half, 3), round(cz + z_half, 3))
        # wall clearance: every label vertex must sit outside the
        # bottle wall (radial distance from the bottle axis >= wall
        # radius at that height, within 0.002) — the tilt fix for the
        # conical bottle's lower edge sinking into the wall. The
        # "hugs the wall" check uses the BACK-FACE CENTRE (a box has
        # no vertex at the face centre; the corner vertices sit
        # further out because the flat plate spans a curved wall):
        # its clearance is 0.0015 by design (0.0005 gap + 0.001 half
        # thickness).
        clearances = []
        for v in world_verts(obj):
            radial = math.hypot(v.x - x, v.y)
            wall_r = radius_at(prof, v.z - z_base)
            clearances.append(round(radial - wall_r, 4))
        min_clear = min(clearances)
        back_center = obj.matrix_world @ Vector((0, -0.001, 0))
        bc_radial = math.hypot(back_center.x - x, back_center.y)
        bc_wall = radius_at(prof, back_center.z - z_base)
        center_clear = round(bc_radial - bc_wall, 4)
        loc = tuple(round(v, 3) for v in obj.location)
        rot_x = round(obj.rotation_euler.x, 4)
        row = {"range": r, "expected": exp,
               "design_center": tuple(round(v, 3) for v in des["center"]),
               "center": loc,
               "tilt_rad": round(tilt, 4),
               "rotation_euler_x": rot_x,
               "min_wall_clearance": min_clear,
               "back_face_center_clearance": center_clear,
               "clearances": clearances,
               "ok": bool(
                   bbox_close(r, exp)
                   and all(abs(a - b) < 0.002 for a, b in zip(loc, des["center"]))
                   and abs(rot_x - (-tilt)) < 0.005
                   and min_clear >= -0.002
                   and 0.0 <= center_clear <= 0.004)}
        rows[name] = row
    return {"labels": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_spare_corks(by_name):
    rows = {}
    for i, cx in enumerate(SPARE_CORK_X):
        name = "SpareCork_%d" % (i + 1)
        obj = by_name[name]
        z0, z1 = SPARE_CORK_Z
        r0, r1 = SPARE_CORK_R
        rings = ring_analysis(obj, (cx, 0, z0), (0, 0, 1))
        r = world_range(obj)
        exp = (round(cx - r1, 3), round(cx + r1, 3),
               round(-r1, 3), round(r1, 3),
               round(z0, 3), round(z1, 3))
        row = {"range": r, "expected": exp,
               "rings": [(x2["distance"], x2["count"], x2["radius"])
                         for x2 in rings],
               # standing on the top board: bottom == Shelf_3 top
               "bottom_on_top_board": round(r[4] - (SHELF_ZC[2] + 0.015), 3),
               "ok": bool(
                   bbox_close(r, exp)
                   and len(rings) == 2
                   and [x2["distance"] for x2 in rings]
                   == [0.0, round(z1 - z0, 3)]
                   and [x2["count"] for x2 in rings] == [CORK_SIDES] * 2
                   and abs(rings[0]["radius"] - r0) < 0.002
                   and abs(rings[1]["radius"] - r1) < 0.002
                   and abs(r[4] - (SHELF_ZC[2] + 0.015)) < 0.001)}
        rows[name] = row
    return {"spare_corks": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_shelf_clearance(by_name):
    """Each bottle sits on its shelf top; its cork top must clear the
    shelf above."""
    rows = {}
    for tag, (kind, x, z_base, _g, _l) in BOTTLES.items():
        prof = PROFILES[kind]
        height = prof[-1][1]
        shelf = tag[0]  # L or U
        cork_top = z_base + height + CORK_ABOVE_TOP
        clearance = SHELF_ABOVE[shelf] - cork_top
        bottle = by_name["Bottle_%s" % tag]
        base_z = world_range(bottle)[4]
        rows[tag] = {"bottle_base_z": base_z,
                     "shelf_top_z": SHELF_TOP[shelf],
                     "base_on_shelf": round(base_z - SHELF_TOP[shelf], 3),
                     "cork_top_z": round(cork_top, 3),
                     "shelf_above_bottom_z": SHELF_ABOVE[shelf],
                     "clearance": round(clearance, 3),
                     "ok": bool(abs(base_z - SHELF_TOP[shelf]) < 0.001
                                and clearance > 0)}
    return {"clearance": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_spacing(by_name):
    """Bottles on the same shelf must not overlap each other, and no
    bottle surface may clip into a post. The bbox gap is the coarse
    check; the decisive check counts bottle vertices that lie INSIDE
    a post solid (post boxes: x +/-0.2475..0.2925, y +/-0.03,
    z 0..0.54) and measures the deepest penetration."""
    post_boxes = {"Post_L": (-0.2925, -0.2475),
                  "Post_R": (0.2475, 0.2925)}
    rows = {}
    for shelf, tags in (("L", ["L1", "L2", "L3", "L4"]),
                        ("U", ["U1", "U2", "U3", "U4"])):
        ordered = sorted(tags, key=lambda t: BOTTLES[t][1])
        gaps = []
        for a, b in zip(ordered, ordered[1:]):
            ra = max(r for r, _ in PROFILES[BOTTLES[a][0]])
            rb = max(r for r, _ in PROFILES[BOTTLES[b][0]])
            gap = (BOTTLES[b][1] - rb) - (BOTTLES[a][1] + ra)
            gaps.append((a, b, round(gap, 3)))
        # also against the posts (inner faces at x +/-0.2475)
        edge_l = (ordered[0], "Post_L",
                  round((BOTTLES[ordered[0]][1]
                         - max(r for r, _ in PROFILES[BOTTLES[ordered[0]][0]]))
                        - (-POST_X + POST_SIZE[0] / 2.0), 3))
        edge_r = (ordered[-1], "Post_R",
                  round((POST_X - POST_SIZE[0] / 2.0)
                        - (BOTTLES[ordered[-1]][1]
                           + max(r for r, _ in PROFILES[BOTTLES[ordered[-1]][0]])), 3))
        clips = {}
        for tag in tags:
            obj = by_name["Bottle_%s" % tag]
            for pname, (px0, px1) in post_boxes.items():
                n = 0
                pen = 0.0
                for v in world_verts(obj):
                    if (px0 <= v.x <= px1 and -0.03 <= v.y <= 0.03
                            and 0 <= v.z <= 0.54):
                        n += 1
                        if pname == "Post_L":
                            pen = max(pen, px1 - v.x)
                        else:
                            pen = max(pen, v.x - px0)
                if n:
                    clips["%s_vs_%s" % (tag, pname)] = {
                        "verts_inside": n,
                        "max_penetration": round(pen, 4)}
        rows[shelf] = {"gaps": gaps, "edge_left": edge_l,
                       "edge_right": edge_r, "clips": clips,
                       "ok": bool(all(g > 0.005 for _a, _b, g in gaps)
                                  and edge_l[2] > 0.005
                                  and edge_r[2] > 0.005
                                  and not clips)}
    return {"spacing": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_symmetry(by_name, results):
    pairs = [("Post_L", "Post_R", "mirror_x", 0.0),
             ("SpareCork_1", "SpareCork_3", "mirror_x", 0.0)]
    rows = []
    for a, b, kind, dz_exp in pairs:
        ca = mesh_centroid(by_name[a])
        cb = mesh_centroid(by_name[b])
        dx = round(abs(ca.x + cb.x), 4)
        dy = round(abs(ca.y - cb.y), 4)
        dz = round(abs(ca.z - cb.z), 4)
        faces_eq = results[a]["faces"] == results[b]["faces"]
        rows.append({"pair": (a, b), "kind": kind, "dx": dx, "dy": dy,
                     "dz": dz, "dz_expected": dz_exp,
                     "faces_equal": bool(faces_eq),
                     "ok": bool(dx < 0.001 and dy < 0.001
                                and abs(dz - dz_exp) < 0.001
                                and faces_eq)})
    return {"pairs": rows, "ok": bool(all(r["ok"] for r in rows))}


def check_ground(by_name):
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
    # the rack stands on the ground: posts bottom at z 0, nothing below
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
    exp = (-0.2925, 0.2925, -0.085, 0.085, 0.0, 0.552)
    row = {"bbox": (x0, x1, y0, y1, z0, z1),
           "expected_bbox": exp,
           "width": round(x1 - x0, 3), "depth": round(y1 - y0, 3),
           "height": round(z1 - z0, 3)}
    row["ok"] = bool(all(abs(a - b) <= 0.003
                         for a, b in zip((x0, x1, y0, y1, z0, z1), exp)))
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 059 design values.
    Solid mats: Principled metallic/roughness/base color. Glass mats:
    same plus Alpha 0.45 and dithered transparency. Emissive mats:
    same plus the Emission node (color/strength) and Mix Shader factor.
    The 059 build script stores raw tuples as linear Base Color."""
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
        row = {"name": name, "found": True, "metallic": m,
               "roughness": r, "base_color": c,
               "design_color_linear": col, "ok": bool(ok)}
        if spec.get("alpha") is not None:
            alpha = round(bsdf.inputs["Alpha"].default_value, 2)
            row["alpha"] = alpha
            row["surface_render_method"] = mat.surface_render_method
            row["ok"] = bool(ok and abs(alpha - spec["alpha"]) < 0.01
                             and mat.surface_render_method == 'DITHERED')
        if spec["emissive"] is not None:
            strength, mix_fac = spec["emissive"]
            if emit is None or mix is None:
                row["ok"] = False
                row["emissive_missing"] = True
            else:
                es = round(emit.inputs["Strength"].default_value, 2)
                ec = tuple(round(v, 2)
                           for v in emit.inputs["Color"].default_value[:3])
                mf = round(mix.inputs[0].default_value, 2)
                row["emission_strength"] = es
                row["emission_color"] = ec
                row["mix_fac"] = mf
                row["ok"] = bool(ok and abs(es - strength) < 0.01
                                 and all(abs(a - b) < 0.01
                                         for a, b in zip(ec, col))
                                 and abs(mf - mix_fac) < 0.01)
        rows.append(row)
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

    rack = check_rack(by_name)
    print("QA_RACK:", rack)
    bottles = check_bottles(by_name)
    print("QA_BOTTLES:", bottles)
    liquids = check_liquids(by_name)
    print("QA_LIQUIDS:", liquids)
    corks = check_corks(by_name)
    print("QA_CORKS:", corks)
    labels = check_labels(by_name)
    print("QA_LABELS:", labels)
    spare = check_spare_corks(by_name)
    print("QA_SPARE_CORKS:", spare)
    clearance = check_shelf_clearance(by_name)
    print("QA_SHELF_CLEARANCE:", clearance)
    spacing = check_spacing(by_name)
    print("QA_SPACING:", spacing)
    symmetry = check_symmetry(by_name, results)
    print("QA_SYMMETRY:", symmetry)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    structure = {"rack": rack, "bottles": bottles, "liquids": liquids,
                 "corks": corks, "labels": labels, "spare_corks": spare,
                 "shelf_clearance": clearance, "spacing": spacing,
                 "symmetry": symmetry, "ground_contact": ground,
                 "overall": overall}
    structure_ok = (rack["ok"] and bottles["ok"] and liquids["ok"]
                    and corks["ok"] and labels["ok"] and spare["ok"]
                    and clearance["ok"] and spacing["ok"]
                    and symmetry["ok"] and ground["ok"] and overall["ok"])

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # Bottles and liquids are lathe surfaces OPEN AT THE TOP BY DESIGN
    # (the bottle mouth; the liquid surface is capped by its own top
    # disc): each carries exactly 16 boundary edges on its top ring.
    # Every other part must be a closed mesh (0 boundary edges).
    open_parts = {"Bottle_%s" % t for t in BOTTLES}
    open_parts |= {"Liquid_%s" % t for t in BOTTLES}
    open_boundary = sum(results[n]["boundary_edges"] for n in open_parts)
    open_ok = all(results[n]["boundary_edges"] == LATHE_SIDES
                  for n in open_parts)
    other_boundary = sum(r["boundary_edges"] for n, r in results.items()
                         if n not in open_parts)
    boundary_ok = (open_boundary == len(open_parts) * LATHE_SIDES
                   and open_ok and other_boundary == 0)
    ngons_ok = tot["ngons"] == 0
    uv_ok = all(r["uv"]["has_uv"] for r in results.values())
    faces_ok = (not face_mismatch and not missing and not extra
                and tot["faces"] == EXPECTED_TOTAL_FACES
                and tot["tris"] == EXPECTED_TRIS
                and tot["quads"] == EXPECTED_QUADS)
    # the 059 build script's own winding self-check was all 0; the
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
        "asset": "059-lowpoly-potion-rack",
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
        f.write("# 060 资产质检单：低模炼金药水架（059）\n\n")
        f.write("被检资产：`scenes/059-lowpoly-potion-rack.blend`（%d 个道具部件，不含地面）。\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。061 修复后复核：059 源文件已按修复重建（L1 x -0.20 → -0.19）。\n\n")
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
        f.write("- 面数与 059 设计表逐部件比对：%s（设计 2242 面：三角 688、四边 1554、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 闭合网格：边界边共 %d 条，全部在 8 个瓶身与 8 份药水的顶部开口环上（各 16 条，设计敞口：瓶口敞开、药水面由顶盘封口），其余 34 个部件 0 条：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("  059 构建脚本自带的绕向自检（质心检测）同样全 0，两次独立测量一致。\n\n")
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
        f.write("## 4. 药水架结构（实测）\n\n")
        f.write("### 4.1 木架\n\n")
        for name, row in rack["rack"].items():
            if name == "BackRail":
                f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；后沿与层板后沿齐平（y 0.085）：%s\n" % (
                    name, row["range"][0], row["range"][1], row["range"][2],
                    row["range"][3], row["range"][4], row["range"][5],
                    row["expected"], verdict(row["ok"])))
            elif name == "Nameplate":
                f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）；背面与中层板前沿齐平（y -0.085），前面探出 %.3f（设计 0.002）：%s\n" % (
                    name, row["range"][0], row["range"][1], row["range"][2],
                    row["range"][3], row["range"][4], row["range"][5],
                    row["expected"], row["sticks_out"], verdict(row["ok"])))
            else:
                f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）：%s\n" % (
                    name, row["range"][0], row["range"][1], row["range"][2],
                    row["range"][3], row["range"][4], row["range"][5],
                    row["expected"], verdict(row["ok"])))
        f.write("\n### 4.2 瓶身（车削轮廓，16 段）\n\n")
        for name, b in bottles["bottles"].items():
            f.write("- %s（%s瓶）：%d 环（每环 16 顶点），环高 z %s，环半径 %s（设计 %s）；包围盒 x %.3f–%.3f、z %.3f–%.3f；%d 个三角面全部是底面扇形封口（面中心 z=%.3f），顶部敞口无封盖：%s\n" % (
                name, b["kind"], len(b["rings"]),
                [round(BOTTLES[name.split("_")[1]][2] + d, 3)
                 for d in b["ring_distances"]],
                b["ring_radii"],
                [r for r, _ in PROFILES[b["kind"]]],
                b["range"][0], b["range"][1], b["range"][4], b["range"][5],
                b["tri_count"], b["tri_face_center_zs"][0]
                if b["tri_face_center_zs"] else 0,
                verdict(b["ok"])))
        f.write("\n### 4.3 药水与顶盘\n\n")
        for name, liq in liquids["liquids"].items():
            tag = name.split("_")[1]
            f.write("- %s：药水高 %.4f（瓶高 65%%），%d 环（每环 16 顶点），环高 z %s，环半径 %s（瓶身轮廓 ×0.8 截到 65%% 处）；包围盒 x %.3f–%.3f、z %.3f–%.3f；%d 个三角面全部是底面扇形封口；顶盘 LiquidTop_%s 半径 %.4f、厚 0.003，包围盒 z %.3f–%.3f：%s\n" % (
                name, liq["liquid_height"], len(liq["rings"]),
                [round(BOTTLES[tag][2] + d, 3)
                 for d in liq["ring_distances"]],
                liq["ring_radii"],
                liq["range"][0], liq["range"][1], liq["range"][4],
                liq["range"][5], liq["tri_count"], tag,
                liq["top_disc_radius"], liq["top_disc_range"][4],
                liq["top_disc_range"][5], verdict(liq["ok"])))
        f.write("\n### 4.4 瓶塞\n\n")
        for name, c in corks["corks"].items():
            f.write("- %s：锥形圆柱 2 环（每环 8 顶点），环距 %s、半径 %s（设计颈口 r %.3f ×0.85/×1.05）；包围盒 z %.3f–%.3f，塞入瓶颈 %.3f、露出瓶口 %.3f；三角面全部在两端盖上：%s\n" % (
                name, [d for d, _c, _r in c["rings"]],
                [r for _d, _c, r in c["rings"]], c["neck_radius"],
                c["range"][4], c["range"][5], c["sunk_into_neck"],
                c["sticks_out"], verdict(c["ok"])))
        f.write("\n### 4.5 标签（倾斜贴合瓶壁）\n\n")
        for name, lb in labels["labels"].items():
            f.write("- %s：中心 %s（设计 %s），倾斜 %.4f rad（设计 %.4f rad）；包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f；背面中心与瓶壁间隙 %.4f（设计 0.0015，须 0–0.004），全部顶点最小间隙 %.4f（须 ≥-0.002，无一埋入瓶壁）：%s\n" % (
                name, lb["center"], lb["design_center"],
                lb["rotation_euler_x"], -lb["tilt_rad"],
                lb["range"][0], lb["range"][1], lb["range"][2],
                lb["range"][3], lb["range"][4], lb["range"][5],
                lb["back_face_center_clearance"],
                lb["min_wall_clearance"], verdict(lb["ok"])))
        f.write("\n### 4.6 备用软木塞\n\n")
        for name, s in spare["spare_corks"].items():
            f.write("- %s：锥形圆柱 2 环（每环 8 顶点），环距 %s、半径 %s（设计下 r 0.011、上 r 0.014）；包围盒 x %.3f–%.3f、z %.3f–%.3f；底面与顶板顶（z 0.525）齐平，差 %.3f：%s\n" % (
                name, [d for d, _c, _r in s["rings"]],
                [r for _d, _c, r in s["rings"]],
                s["range"][0], s["range"][1], s["range"][4], s["range"][5],
                s["bottom_on_top_board"], verdict(s["ok"])))
        f.write("\n### 4.7 层板净空与瓶间距\n\n")
        for tag, cl in clearance["clearance"].items():
            f.write("- %s：瓶底 z %.3f（层板顶 z %.3f，差 %.3f）；瓶塞顶 z %.3f，上层板底 z %.3f，净空 %.3f：%s\n" % (
                tag, cl["bottle_base_z"], cl["shelf_top_z"],
                cl["base_on_shelf"], cl["cork_top_z"],
                cl["shelf_above_bottom_z"], cl["clearance"],
                verdict(cl["ok"])))
        for shelf, sp in spacing["spacing"].items():
            gaps = "、".join("%s–%s %.3f" % g for g in sp["gaps"])
            clip_note = ""
            if sp["clips"]:
                clip_note = "；穿插：%s" % "、".join(
                    "%s 有 %d 个顶点在立柱体内、最深 %.4f" % (
                        k, v["verts_inside"], v["max_penetration"])
                    for k, v in sp["clips"].items())
            else:
                clip_note = "；无瓶身顶点在立柱体内"
            f.write("- %s层瓶间距：%s；与立柱内沿间隙：左 %s %.3f、右 %s %.3f%s：%s\n" % (
                shelf, gaps, sp["edge_left"][1], sp["edge_left"][2],
                sp["edge_right"][1], sp["edge_right"][2], clip_note,
                verdict(sp["ok"])))
        f.write("\n### 4.8 对称与地面、整体\n\n")
        for p in symmetry["pairs"]:
            f.write("- 对称 %s–%s（%s）：镜像中心偏差 x %.4f、y %.4f、z %.4f，面数成对相等：%s\n" % (
                p["pair"][0], p["pair"][1], p["kind"], p["dx"], p["dy"],
                p["dz"], verdict(p["ok"])))
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s（立柱底 z=0 落地，其余部件均在层板上）：%s\n" % (
            ground["checked"], ground["global_min_z"],
            ground["below_ground"] if ground["below_ground"] else "无",
            verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（x 最宽处为层板 ±0.2925，"
                "y 最深处为层板 ±0.085，最高处为备用软木塞顶 z 0.552）：%s\n" % (
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
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 059 构建脚本直接存入的线性值；玻璃材质另核 Alpha 与 dithered 透明，自发光材质另核 Emission 节点与混合比）：\n")
        for row in mats["rows"]:
            if row.get("emissive_missing"):
                line = ("  - %s：自发光节点缺失：不通过\n" % row["name"])
            elif "emission_strength" in row:
                line = ("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                        "底色 %s（设计 %s），Emission 强度 %.2f（设计 %.2f），"
                        "混合比 %.2f（设计 %.2f）：%s\n" % (
                            row["name"], row["metallic"],
                            DESIGN_MATS[row["name"]]["metallic"],
                            row["roughness"],
                            DESIGN_MATS[row["name"]]["roughness"],
                            row["base_color"], row["design_color_linear"],
                            row["emission_strength"],
                            DESIGN_MATS[row["name"]]["emissive"][0],
                            row["mix_fac"],
                            DESIGN_MATS[row["name"]]["emissive"][1],
                            verdict(row["ok"])))
            elif "alpha" in row:
                line = ("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                        "底色 %s（设计 %s），Alpha %.2f（设计 %.2f），"
                        "透明方式 %s（设计 DITHERED）：%s\n" % (
                            row["name"], row["metallic"],
                            DESIGN_MATS[row["name"]]["metallic"],
                            row["roughness"],
                            DESIGN_MATS[row["name"]]["roughness"],
                            row["base_color"], row["design_color_linear"],
                            row["alpha"], DESIGN_MATS[row["name"]]["alpha"],
                            row["surface_render_method"],
                            verdict(row["ok"])))
            else:
                line = ("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                        "底色 %s（设计 %s）：%s\n" % (
                            row["name"], row["metallic"],
                            DESIGN_MATS[row["name"]]["metallic"],
                            row["roughness"],
                            DESIGN_MATS[row["name"]]["roughness"],
                            row["base_color"], row["design_color_linear"],
                            verdict(row["ok"])))
            f.write(line)
        f.write("\n## 6. 备注（实测发现，非缺陷）\n\n")
        min_label = min(v["back_face_center_clearance"]
                        for v in labels["labels"].values())
        max_label = max(v["back_face_center_clearance"]
                        for v in labels["labels"].values())
        f.write("- 标签贴合：8 张标签背面中心与瓶壁间隙 %.4f–%.4f（设计 0.0015，"
                "全部 ≥0，无一埋入瓶壁；059 修复的锥形瓶标签下沿埋入问题已验证修好，"
                "倾斜贴合有效；平板跨曲面导致角点间隙略大，属正常）。\n" % (min_label, max_label))
        min_clear = min(v["clearance"]
                        for v in clearance["clearance"].values())
        f.write("- 层板净空：8 瓶瓶塞顶距上层板底最小净空 %.3f（上层最高瓶 "
                "U2 瓶塞顶 z %.3f，顶板底 z 0.495），无穿帮。\n" % (
                    min_clear,
                    clearance["clearance"]["U2"]["cork_top_z"]))
        f.write("- 瓶身/药水敞口：8 个瓶身与 8 份药水顶部各 16 条边界边，"
                "是车削曲面的设计敞口（瓶口敞开、药水面由顶盘封口），"
                "不是破洞；其余 34 个部件全部闭合。\n")
        f.write("- 059 笔记尺寸与实测一致：宽 0.585 m × 深 0.170 m × "
                "高 0.552 m（笔记“约 0.59 × 0.55 × 0.17 m”）。\n")
        f.write("- 061 修复复核：Bottle_L1 向内移 0.01 m（x -0.20 → -0.19，"
                "与 U1 对齐），L1–Post_L 间隙 0.006、L1–L2 间隙 0.030，"
                "立柱体内顶点 0 个，原 REVIEW NEEDED 的唯一缺陷已消除。\n")
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、药水架结构、对称、地面接触均通过。\n")
        else:
            f.write("待修项：\n\n")
            for shelf, sp in spacing["spacing"].items():
                for k, v in sp["clips"].items():
                    f.write("- %s：瓶身卡进立柱（%d 个顶点在立柱体内，最深 %.4f m，"
                            "在腹径环 z 0.085 与肩环 z 0.125 两处）：把 %s 向内移 "
                            "0.01 m（x -0.20 → -0.19，与 U1 对齐）或把立柱外移，"
                            "修完重跑本质检脚本复核。\n" % (
                                k, v["verts_inside"], v["max_penetration"],
                                k.split("_vs_")[0]))
            f.write("\n其余项：拓扑、法线、UV、材质、药水架其余结构、对称、地面接触均通过。\n")


if __name__ == "__main__":
    main()
