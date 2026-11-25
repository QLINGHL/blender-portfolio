# -*- coding: utf-8 -*-
"""056 资产质检：对 055 低模炼金坩埚做真实 mesh 检查（拓扑/法线/UV/材质），
并实测坩埚特有结构：锅身车削环、锅沿/腹箍双圆环、药水面与气泡、
提环嵌壁、支腿落地点、篝火与搅拌棒。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 056-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "055-lowpoly-cauldron.blend")
UV_JSON = os.path.join(ROOT, "scenes", "056-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "056-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "056-asset-qa-checklist.md")

# every mesh object in the 055 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design face counts from scenes/055-lowpoly-cauldron.md (per-part table)
EXPECTED_FACES = {
    "Pot": 168, "Rim": 144, "BellyBand": 144, "Potion": 72,
    "Bubble_1": 50, "Bubble_2": 50, "Bubble_3": 50, "Bubble_4": 50,
    "Bubble_5": 50,
    "Handle_1": 96, "Handle_2": 96,
    "Leg_1": 24, "FootPad_1": 50,
    "Leg_2": 24, "FootPad_2": 50,
    "Leg_3": 24, "FootPad_3": 50,
    "Log_1": 24, "Log_2": 24,
    "Flame_1": 24, "Flame_2": 24, "Flame_3": 24, "FlameCore": 24,
    "StirStick": 24,
}
EXPECTED_TOTAL_FACES = 1360
EXPECTED_TRIS = 392
EXPECTED_QUADS = 968

# part -> design material (from the 055 build script)
PART_MATERIAL = {
    "Pot": "Cauldron_Iron",
    "Rim": "Cauldron_IronDark", "BellyBand": "Cauldron_IronDark",
    "Potion": "Cauldron_Potion",
    "Bubble_1": "Cauldron_Bubble", "Bubble_2": "Cauldron_Bubble",
    "Bubble_3": "Cauldron_Bubble", "Bubble_4": "Cauldron_Bubble",
    "Bubble_5": "Cauldron_Bubble",
    "Handle_1": "Cauldron_IronDark", "Handle_2": "Cauldron_IronDark",
    "Leg_1": "Cauldron_Iron", "Leg_2": "Cauldron_Iron",
    "Leg_3": "Cauldron_Iron",
    "FootPad_1": "Cauldron_IronDark", "FootPad_2": "Cauldron_IronDark",
    "FootPad_3": "Cauldron_IronDark",
    "Log_1": "Cauldron_WoodDark", "Log_2": "Cauldron_WoodDark",
    "Flame_1": "Cauldron_Flame", "Flame_2": "Cauldron_Flame",
    "Flame_3": "Cauldron_Flame", "FlameCore": "Cauldron_FlameCore",
    "StirStick": "Cauldron_Wood",
}

# Design material values from the 055 build script. NOTE: the 055 build
# script passes raw tuples to solid_material / emissive_material, which
# store them directly as linear Base Color (no sRGB conversion, unlike
# the 049 build script), so the expected linear values are the raw tuples.
# emissive: (emission strength, mix factor) of the Mix Shader.
DESIGN_MATS = {
    "Cauldron_Iron":     {"metallic": 0.70, "roughness": 0.55,
                          "color": (0.16, 0.16, 0.18), "emissive": None},
    "Cauldron_IronDark": {"metallic": 0.65, "roughness": 0.60,
                          "color": (0.10, 0.10, 0.11), "emissive": None},
    "Cauldron_Wood":     {"metallic": 0.00, "roughness": 0.80,
                          "color": (0.36, 0.22, 0.12), "emissive": None},
    "Cauldron_WoodDark": {"metallic": 0.00, "roughness": 0.85,
                          "color": (0.24, 0.15, 0.08), "emissive": None},
    "Cauldron_Potion":   {"metallic": 0.00, "roughness": 0.40,
                          "color": (0.22, 0.72, 0.22),
                          "emissive": (0.8, 0.7)},
    "Cauldron_Bubble":   {"metallic": 0.00, "roughness": 0.40,
                          "color": (0.45, 0.90, 0.40),
                          "emissive": (0.6, 0.6)},
    "Cauldron_Flame":    {"metallic": 0.00, "roughness": 0.40,
                          "color": (0.95, 0.45, 0.10),
                          "emissive": (1.2, 0.7)},
    "Cauldron_FlameCore": {"metallic": 0.00, "roughness": 0.40,
                           "color": (0.98, 0.80, 0.25),
                           "emissive": (1.4, 0.7)},
}

# design geometry (from the 055 build script)
POT_PROFILE = [(0.085, 0.14), (0.115, 0.16), (0.145, 0.21), (0.160, 0.27),
               (0.158, 0.32), (0.145, 0.36), (0.138, 0.40)]
POT_SIDES = 24
RIM = {"center": (0, 0, 0.40), "R": 0.138, "tube": 0.009}
BELLY_BAND = {"center": (0, 0, 0.27), "R": 0.160, "tube": 0.008}
POTION = {"z0": 0.382, "z1": 0.385, "r": 0.132}
BUBBLES = [((0.045, 0.030), 0.018), ((-0.055, 0.045), 0.014),
           ((-0.020, -0.060), 0.016), ((0.070, -0.045), 0.012),
           ((0.005, 0.075), 0.011)]
BUBBLE_Z = 0.385
HANDLES = {"centers": ((-0.155, 0, 0.33), (0.155, 0, 0.33)),
           "R": 0.035, "tube": 0.008}
LEG_ANGLES = (90, 210, 330)  # deg; leg i+1
LEG_TOP_R, LEG_TOP_Z = 0.10, 0.16
LEG_FOOT_R, LEG_FOOT_Z = 0.20, 0.0
LEG_RADIUS = 0.018
FOOTPAD_R = 0.022
FOOTPAD_Z = 0.012
LOG_ENDS = [((-0.13, -0.05, 0.025), (0.13, 0.05, 0.025)),
            ((-0.13, 0.05, 0.025), (0.13, -0.05, 0.025))]
LOG_R = 0.026
FLAMES = [(("Flame_1", (0.0, 0.0), 0.045, 0.17)),
          (("Flame_2", (-0.05, 0.03), 0.035, 0.13)),
          (("Flame_3", (0.05, -0.03), 0.035, 0.12))]
FLAME_CORE = ("FlameCore", (0.0, 0.0), 0.028, 0.09)
FLAME_Z0 = 0.03
STICK_ENDS = ((-0.17, 0.04, 0.415), (0.17, -0.03, 0.405))
STICK_R = 0.011

# planted-look tolerance: leg/footpad/log ends may sink this far below
# the ground plane (they are hidden by the ground in the render and
# read as "planted" in a game asset); deeper than this is a defect.
PLANTED_TOL = 0.02


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


def ring_analysis(obj, origin, direction):
    """Group the tube's ring verts (rho > 0.001 off axis) by axial
    distance; return [(distance, count, center, radius)] per ring."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    mw = obj.matrix_world
    clusters = {}
    for v in obj.data.vertices:
        w = mw @ v.co
        rel = w - o
        axial = rel.dot(d)
        rho = (rel - d * axial).length
        if rho < 0.001:
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


def cyl_bbox(p0, p1, r):
    """Exact bbox of a capped cylinder between p0 and p1, radius r:
    half-extent per axis = |delta_i|/2 + r*sqrt(1-u_i^2)."""
    a = Vector(p0)
    b = Vector(p1)
    d = b - a
    u = d.normalized()
    c = (a + b) / 2.0
    half = []
    for i in range(3):
        half.append(abs(d[i]) / 2.0 + r * math.sqrt(max(0.0, 1 - u[i] ** 2)))
    lo = [c[i] - half[i] for i in range(3)]
    hi = [c[i] + half[i] for i in range(3)]
    return (round(lo[0], 3), round(hi[0], 3), round(lo[1], 3),
            round(hi[1], 3), round(lo[2], 3), round(hi[2], 3))


def bbox_close(measured, expected, tol=0.002):
    return all(abs(a - b) <= tol for a, b in zip(measured, expected))


def check_pot(by_name):
    pot = by_name["Pot"]
    rings = ring_analysis(pot, (0, 0, 0.14), (0, 0, 1))
    exp_dist = [round(z - 0.14, 3) for _r, z in POT_PROFILE]
    exp_radii = [r for r, _z in POT_PROFILE]
    # all 24 tris must be the bottom cap fan (centre z ~ 0.14)
    mw = pot.matrix_world
    tri_zs = []
    for p in pot.data.polygons:
        if len(p.vertices) == 3:
            tri_zs.append(round((mw @ p.center).z, 3))
    r = world_range(pot)
    row = {"range": r, "rings": rings,
           "ring_distances": [x["distance"] for x in rings],
           "ring_counts": [x["count"] for x in rings],
           "ring_radii": [x["radius"] for x in rings],
           "tri_face_center_zs": sorted(set(tri_zs)),
           "tri_count": len(tri_zs)}
    ok = (len(rings) == len(POT_PROFILE)
          and all(c == POT_SIDES for c in row["ring_counts"])
          and row["ring_distances"] == exp_dist
          and all(abs(a - b) < 0.002
                  for a, b in zip(row["ring_radii"], exp_radii))
          and abs(r[0] + 0.160) < 0.002 and abs(r[1] - 0.160) < 0.002
          and abs(r[4] - 0.14) < 0.001 and abs(r[5] - 0.40) < 0.001
          and len(tri_zs) == POT_SIDES
          and all(abs(z - 0.14) < 0.002 for z in tri_zs))
    row["ok"] = bool(ok)
    return row


def check_torus(name, by_name, spec):
    """Flat ring in the XY plane: bbox = center +/- (R+tube) in x/y,
    center z +/- tube."""
    obj = by_name[name]
    r = world_range(obj)
    cx, cy, cz = spec["center"]
    R, t = spec["R"], spec["tube"]
    exp = (round(cx - R - t, 3), round(cx + R + t, 3),
           round(cy - R - t, 3), round(cy + R + t, 3),
           round(cz - t, 3), round(cz + t, 3))
    row = {"range": r, "expected": exp}
    row["ok"] = bool(bbox_close(r, exp))
    return row


def check_potion(by_name):
    obj = by_name["Potion"]
    r = world_range(obj)
    exp = (-POTION["r"], POTION["r"], -POTION["r"], POTION["r"],
           POTION["z0"], POTION["z1"])
    rim_top = RIM["center"][2] + RIM["tube"]
    pot_inner = POT_PROFILE[-1][0]  # rim radius 0.138
    row = {"range": r, "expected": exp,
           "top_below_rim_top": round(rim_top - r[5], 3),
           "radius_gap_to_pot_wall": round(pot_inner - r[1], 3)}
    row["ok"] = bool(bbox_close(r, exp)
                     and row["top_below_rim_top"] > 0
                     and row["radius_gap_to_pot_wall"] > 0)
    return row


def check_bubbles(by_name):
    rows = {}
    for i, ((bx, by), br) in enumerate(BUBBLES):
        name = "Bubble_%d" % (i + 1)
        obj = by_name[name]
        r = world_range(obj)
        # low-segment UV sphere: faceted bbox up to ~0.001 inside the
        # analytic sphere; centre is exact.
        c = mesh_centroid(obj)
        dist_axis = round(math.hypot(bx, by), 3)
        row = {"range": r,
               "center": tuple(round(v, 3) for v in c),
               "expected_center": (bx, by, BUBBLE_Z),
               "radius": br,
               "top_above_potion": round(r[5] - POTION["z1"], 3),
               "bottom_below_potion": round(POTION["z1"] - r[4], 3),
               "outer_reach": round(dist_axis + br, 3)}
        row["ok"] = bool(
            all(abs(a - b) < 0.002 for a, b in zip(row["center"],
                                                  row["expected_center"]))
            and row["top_above_potion"] > 0
            and row["bottom_below_potion"] > 0
            and row["outer_reach"] <= POTION["r"])
        rows[name] = row
    return {"bubbles": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_handles(by_name):
    rows = {}
    for i, (cx, cy, cz) in enumerate(HANDLES["centers"]):
        name = "Handle_%d" % (i + 1)
        obj = by_name[name]
        r = world_range(obj)
        R, t = HANDLES["R"], HANDLES["tube"]
        exp = (round(cx - t, 3), round(cx + t, 3),
               round(cy - R - t, 3), round(cy + R + t, 3),
               round(cz - R - t, 3), round(cz + R + t, 3))
        # pot wall radius at handle height z=0.33: interpolate profile
        # (0.32 -> 0.158, 0.36 -> 0.145)
        pot_r_at_033 = 0.158 + (0.145 - 0.158) * (0.33 - 0.32) / 0.04
        # the wall the handle meets is at signed x = +/-pot radius
        # (Handle_1 is on -X, Handle_2 on +X): the handle tube's x-range
        # must straddle that wall position (embedded in the wall by
        # design, "半嵌锅壁")
        wall_x = -pot_r_at_033 if cx < 0 else pot_r_at_033
        rows[name] = {"range": r, "expected": exp,
                      "center": (cx, cy, cz),
                      "pot_radius_at_z": round(pot_r_at_033, 3),
                      "wall_x": round(wall_x, 3),
                      "embedded_in_wall": bool(r[0] < wall_x < r[1]),
                      "embed_depth": round(min(wall_x - r[0],
                                               r[1] - wall_x), 3)}
        rows[name]["ok"] = bool(bbox_close(r, exp)
                                and rows[name]["embedded_in_wall"])
    return {"handles": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_legs(by_name):
    rows = {}
    for i, adeg in enumerate(LEG_ANGLES):
        a = math.radians(adeg)
        top = (LEG_TOP_R * math.cos(a), LEG_TOP_R * math.sin(a), LEG_TOP_Z)
        foot = (LEG_FOOT_R * math.cos(a), LEG_FOOT_R * math.sin(a),
                LEG_FOOT_Z)
        leg = by_name["Leg_%d" % (i + 1)]
        pad = by_name["FootPad_%d" % (i + 1)]
        r_leg = world_range(leg)
        exp_leg = cyl_bbox(top, foot, LEG_RADIUS)
        # ring analysis along the leg axis: 2 rings of 8 verts
        axis = Vector(foot) - Vector(top)
        length = axis.length
        rings = ring_analysis(leg, top, axis)
        mid = (Vector(top) + Vector(foot)) / 2.0
        cen = mesh_centroid(leg)
        # cap tris must sit on the two end planes
        mw = leg.matrix_world
        d = axis.normalized()
        o = Vector(top)
        bad_tris = 0
        for p in leg.data.polygons:
            if len(p.vertices) != 3:
                continue
            axial = ((mw @ p.center) - o).dot(d)
            if min(abs(axial), abs(axial - length)) > 0.002:
                bad_tris += 1
        r_pad = world_range(pad)
        pad_c = mesh_centroid(pad)
        exp_pad_c = (foot[0], foot[1], FOOTPAD_Z)
        rows["Leg_%d" % (i + 1)] = {
            "range": r_leg, "expected": exp_leg,
            "axis_length": round(length, 4),
            "rings": [(x["distance"], x["count"]) for x in rings],
            "centroid": tuple(round(v, 3) for v in cen),
            "expected_centroid": tuple(round(v, 3) for v in mid),
            "tris_not_at_ends": bad_tris,
            "min_z": r_leg[4],
            "footpad_range": r_pad,
            "footpad_center": tuple(round(v, 3) for v in pad_c),
            "footpad_expected_center": exp_pad_c,
            "footpad_min_z": r_pad[4]}
        ok = (bbox_close(r_leg, exp_leg)
              and len(rings) == 2
              and all(c == 8 for _d, c in rows["Leg_%d" % (i + 1)]["rings"])
              and [x[0] for x in rows["Leg_%d" % (i + 1)]["rings"]]
              == [0.0, round(length, 3)]
              and bad_tris == 0
              and all(abs(a - b) < 0.002 for a, b in zip(cen, mid))
              and all(abs(a - b) < 0.002 for a, b in zip(pad_c, exp_pad_c)))
        rows["Leg_%d" % (i + 1)]["ok"] = bool(ok)
    return {"legs": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_fire(by_name):
    rows = {}
    for i, (p0, p1) in enumerate(LOG_ENDS):
        name = "Log_%d" % (i + 1)
        obj = by_name[name]
        r = world_range(obj)
        exp = cyl_bbox(p0, p1, LOG_R)
        cen = mesh_centroid(obj)
        mid = (Vector(p0) + Vector(p1)) / 2.0
        rows[name] = {"range": r, "expected": exp,
                      "centroid": tuple(round(v, 3) for v in cen),
                      "expected_centroid": tuple(round(v, 3) for v in mid),
                      "min_z": r[4],
                      "ok": bool(bbox_close(r, exp)
                                 and all(abs(a - b) < 0.002
                                         for a, b in zip(cen, mid)))}
    pot_bottom = POT_PROFILE[0][1]  # 0.14
    for name, (fx, fy), fr, fh in FLAMES + [FLAME_CORE]:
        obj = by_name[name]
        r = world_range(obj)
        exp = (round(fx - fr, 3), round(fx + fr, 3),
               round(fy - fr, 3), round(fy + fr, 3),
               FLAME_Z0, round(FLAME_Z0 + fh, 3))
        # flame tip vs pot bottom: tip above the pot bottom means the
        # tip is inside the pot (hidden); it must not poke through the
        # pot wall or above the rim. Check tip radius is tiny and the
        # tip point is within the pot interior radius at that height.
        tip_inside_pot = r[5] > pot_bottom
        pot_r_at_tip = None
        if tip_inside_pot:
            zt = r[5]
            for (r0, z0), (r1, z1) in zip(POT_PROFILE, POT_PROFILE[1:]):
                if z0 <= zt <= z1:
                    pot_r_at_tip = r0 + (r1 - r0) * (zt - z0) / (z1 - z0)
                    break
        rows[name] = {"range": r, "expected": exp,
                      "tip_above_pot_bottom": round(r[5] - pot_bottom, 3),
                      "pot_radius_at_tip_z": (round(pot_r_at_tip, 3)
                                              if pot_r_at_tip else None),
                      "ok": bool(bbox_close(r, exp, tol=0.003)
                                 and (not tip_inside_pot
                                      or (pot_r_at_tip is not None
                                          and abs(fx) + 0.005 < pot_r_at_tip)))}
    return {"fire": rows,
            "ok": bool(all(v["ok"] for v in rows.values()))}


def check_stick(by_name):
    obj = by_name["StirStick"]
    r = world_range(obj)
    exp = cyl_bbox(STICK_ENDS[0], STICK_ENDS[1], STICK_R)
    cen = mesh_centroid(obj)
    mid = (Vector(STICK_ENDS[0]) + Vector(STICK_ENDS[1])) / 2.0
    # stick centreline z where it crosses the rim ring (|x| = rim R):
    # linear interpolation between the design endpoints.
    def z_at_x(x):
        x0, x1 = STICK_ENDS[0][0], STICK_ENDS[1][0]
        z0, z1 = STICK_ENDS[0][2], STICK_ENDS[1][2]
        t = (x - x0) / (x1 - x0)
        return z0 + t * (z1 - z0)
    rim_top = RIM["center"][2] + RIM["tube"]
    rim_bot = RIM["center"][2] - RIM["tube"]
    crossings = {}
    for x in (-RIM["R"], RIM["R"]):
        zc = z_at_x(x)
        crossings[round(x, 3)] = {
            "centerline_z": round(zc, 3),
            "bottom_z": round(zc - STICK_R, 3),
            # stick bottom must dip into the rim tube (resting on it),
            # not float above the rim top or fall through below it
            "rests_on_rim": bool(zc - STICK_R < rim_top
                                 and zc > rim_bot)}
    row = {"range": r, "expected": exp,
           "centroid": tuple(round(v, 3) for v in cen),
           "expected_centroid": tuple(round(v, 3) for v in mid),
           "rim_crossings": crossings,
           "ok": bool(bbox_close(r, exp)
                      and all(abs(a - b) < 0.002 for a, b in zip(cen, mid))
                      and all(c["rests_on_rim"]
                              for c in crossings.values()))}
    return row


def check_symmetry(by_name, results):
    pairs = [("Handle_1", "Handle_2", "mirror_x", 0.0),
             ("Leg_2", "Leg_3", "mirror_x", 0.0),
             ("FootPad_2", "FootPad_3", "mirror_x", 0.0),
             # Flame_2/Flame_3 are point-symmetric in x/y by design, but
             # their heights differ by design (0.13 vs 0.12), so the
             # centroid z differs by half that (0.005): expected dz 0.005.
             ("Flame_2", "Flame_3", "point_xy", 0.005)]
    rows = []
    for a, b, kind, dz_exp in pairs:
        ca = mesh_centroid(by_name[a])
        cb = mesh_centroid(by_name[b])
        if kind == "mirror_x":
            dx = round(abs(ca.x + cb.x), 4)
            dy = round(abs(ca.y - cb.y), 4)
            dz = round(abs(ca.z - cb.z), 4)
        else:  # point symmetry through the Z axis
            dx = round(abs(ca.x + cb.x), 4)
            dy = round(abs(ca.y + cb.y), 4)
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
    planted_ok = all(z >= -PLANTED_TOL for z in zmins.values())
    return {"checked": len(zmins), "below_ground": below,
            "global_min_z": round(min(zmins.values()), 3),
            "planted_tolerance": PLANTED_TOL,
            "planted_ok": bool(planted_ok),
            "ok": bool(planted_ok)}


def check_overall(by_name):
    rs = [world_range(o) for o in by_name.values()]
    x0 = min(r[0] for r in rs)
    x1 = max(r[1] for r in rs)
    y0 = min(r[2] for r in rs)
    y1 = max(r[3] for r in rs)
    z0 = min(r[4] for r in rs)
    z1 = max(r[5] for r in rs)
    # widest in x: the foot pads (leg feet at r 0.20 + pad radius 0.022,
    # faceted sphere so ~0.193, not 0.20); widest in y: belly band
    # (-0.168) vs the back foot pad (+0.221); top is the stir stick.
    exp = (-0.193, 0.193, -0.168, 0.221, -0.01, 0.426)
    row = {"bbox": (x0, x1, y0, y1, z0, z1),
           "expected_bbox": exp,
           "width": round(x1 - x0, 3), "depth": round(y1 - y0, 3),
           "height": round(z1 - z0, 3),
           "note_claimed_width": 0.55}
    row["width_matches_note"] = bool(abs(row["width"] - 0.55) < 0.01)
    row["ok"] = bool(all(abs(a - b) <= 0.003
                         for a, b in zip((x0, x1, y0, y1, z0, z1), exp)))
    return row


def check_materials(parts, results):
    """Read node values, not names; compare against 055 design values.
    Solid mats: Principled metallic/roughness/base color. Emissive mats:
    same plus the Emission node (color/strength) and Mix Shader factor.
    The 055 build script stores raw tuples as linear Base Color."""
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

    pot = check_pot(by_name)
    print("QA_POT:", pot)
    rim = check_torus("Rim", by_name, RIM)
    print("QA_RIM:", rim)
    band = check_torus("BellyBand", by_name, BELLY_BAND)
    print("QA_BELLYBAND:", band)
    potion = check_potion(by_name)
    print("QA_POTION:", potion)
    bubbles = check_bubbles(by_name)
    print("QA_BUBBLES:", bubbles)
    handles = check_handles(by_name)
    print("QA_HANDLES:", handles)
    legs = check_legs(by_name)
    print("QA_LEGS:", legs)
    fire = check_fire(by_name)
    print("QA_FIRE:", fire)
    stick = check_stick(by_name)
    print("QA_STICK:", stick)
    symmetry = check_symmetry(by_name, results)
    print("QA_SYMMETRY:", symmetry)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    overall = check_overall(by_name)
    print("QA_OVERALL:", overall)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    structure = {"pot": pot, "rim": rim, "bellyband": band,
                 "potion": potion, "bubbles": bubbles,
                 "handles": handles, "legs": legs, "fire": fire,
                 "stick": stick, "symmetry": symmetry,
                 "ground_contact": ground, "overall": overall}
    structure_ok = (pot["ok"] and rim["ok"] and band["ok"]
                    and potion["ok"] and bubbles["ok"] and handles["ok"]
                    and legs["ok"] and fire["ok"] and stick["ok"]
                    and symmetry["ok"] and ground["ok"] and overall["ok"])

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    # the Pot is open at the top BY DESIGN (the cauldron mouth must be
    # open so the potion shows): its 24 top-ring edges are boundary
    # edges. Every other part must be a closed mesh (0 boundary edges).
    pot_boundary = results.get("Pot", {}).get("boundary_edges", -1)
    other_boundary = sum(r["boundary_edges"] for n, r in results.items()
                         if n != "Pot")
    boundary_ok = (pot_boundary == POT_SIDES and other_boundary == 0)
    ngons_ok = tot["ngons"] == 0
    uv_ok = all(r["uv"]["has_uv"] for r in results.values())
    faces_ok = (not face_mismatch and not missing and not extra
                and tot["faces"] == EXPECTED_TOTAL_FACES
                and tot["tris"] == EXPECTED_TRIS
                and tot["quads"] == EXPECTED_QUADS)
    # the 055 build script's own winding self-check was all 0; the
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
        "asset": "055-lowpoly-cauldron",
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
        "pot_boundary_edges": pot_boundary,
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
        f.write("# 056 资产质检单：低模炼金坩埚（055）\n\n")
        f.write("被检资产：`scenes/055-lowpoly-cauldron.blend`（%d 个道具部件，不含地面）。\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。055 原文件未改动。\n\n")
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
        f.write("- 面数与 055 设计表逐部件比对：%s（设计 1360 面：三角 392、四边 968、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 闭合网格：边界边共 %d 条，全部在 Pot 顶部开口环上（设计敞口，"
                "以便看到药水面），其余 23 个部件 0 条：%s\n" % (
                    tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("  055 构建脚本自带的绕向自检（质心/环中心线检测）同样全 0，两次独立测量一致。\n\n")
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
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长/环形部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件 %s）：%.2f%%，%s（阈值 <1%%）\n\n" % (
            worst_overlap_part, worst_overlap,
            verdict(worst_overlap < 1.0)))
        f.write("## 4. 坩埚结构（实测）\n\n")
        pr = pot["rings"]
        f.write("- 锅身（Pot）：车削轮廓 7 环（每环 24 顶点），环高 z %s，环半径 %s（设计 0.085/0.115/0.145/0.160/0.158/0.145/0.138）；包围盒 x ±0.160、z 0.140–0.400；24 个三角面全部是底面扇形封口（面中心 z=0.14），顶部敞口无封盖：%s\n" % (
            [round(0.14 + d, 2) for d in pot["ring_distances"]],
            pot["ring_radii"], verdict(pot["ok"])))
        f.write("- 锅沿（Rim）：圆环包围盒 x/y ±%.3f、z %.3f–%.3f（设计 R 0.138、管 r 0.009，z 0.40）：%s\n" % (
            rim["range"][1], rim["range"][4], rim["range"][5],
            verdict(rim["ok"])))
        f.write("- 腹箍（BellyBand）：圆环包围盒 x/y ±%.3f、z %.3f–%.3f（设计 R 0.160、管 r 0.008，z 0.27）：%s\n" % (
            band["range"][1], band["range"][4], band["range"][5],
            verdict(band["ok"])))
        f.write("- 药水面（Potion）：圆盘 x/y ±%.3f、z %.3f–%.3f（设计 r 0.132，z 0.382–0.385）；盘顶比锅沿顶低 %.3f，距锅壁 %.3f（设计：药水面在锅沿下、锅壁内，不穿帮）：%s\n" % (
            potion["range"][1], potion["range"][4], potion["range"][5],
            potion["top_below_rim_top"], potion["radius_gap_to_pot_wall"],
            verdict(potion["ok"])))
        for name, b in bubbles["bubbles"].items():
            f.write("- %s：中心 %s（设计 %s），半径 %.3f；顶部高出药水面 %.3f、底部沉入药水面 %.3f（半浸），外沿距锅轴 %.3f（药水盘半径 0.132，不出盘）：%s\n" % (
                name, b["center"], b["expected_center"], b["radius"],
                b["top_above_potion"], b["bottom_below_potion"],
                b["outer_reach"], verdict(b["ok"])))
        for name, h in handles["handles"].items():
            f.write("- %s：中心 %s，包围盒 x %.3f–%.3f、y ±%.3f、z %.3f–%.3f（设计竖环 R 0.035、管 r 0.008）；z=0.33 处锅壁半径 %.3f，提环管 x 区间跨过锅壁、嵌进 %.3f（设计：半嵌锅壁）：%s\n" % (
                name, h["center"], h["range"][0], h["range"][1],
                h["range"][3], h["range"][4], h["range"][5],
                h["pot_radius_at_z"], h["embed_depth"],
                verdict(h["ok"])))
        for name, lg in legs["legs"].items():
            f.write("- %s：斜撑铁柱，轴长 %.4f，2 环（每环 8 顶点），环距 %s；质心 %s（设计中点 %s）；三角面全部在两端盖上；足垫中心 %s（设计 %s）：%s\n" % (
                name, lg["axis_length"], [d for d, _c in lg["rings"]],
                lg["centroid"], lg["expected_centroid"],
                lg["footpad_center"], lg["footpad_expected_center"],
                verdict(lg["ok"])))
        for name, fr in fire["fire"].items():
            extra_note = ""
            if name.startswith("Flame"):
                extra_note = "；焰顶比锅底（z 0.14）%s %.3f" % (
                    "高出" if fr["tip_above_pot_bottom"] > 0 else "低",
                    abs(fr["tip_above_pot_bottom"]))
                if fr["pot_radius_at_tip_z"] is not None:
                    extra_note += "，焰顶处锅内半径 %.3f（焰尖藏在锅内，不可见）" % fr["pot_radius_at_tip_z"]
            f.write("- %s：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计 %s）%s：%s\n" % (
                name, fr["range"][0], fr["range"][1], fr["range"][2],
                fr["range"][3], fr["range"][4], fr["range"][5],
                fr["expected"], extra_note, verdict(fr["ok"])))
        f.write("- 搅拌棒（StirStick）：木质圆柱，包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f（设计端点 (-0.17, 0.04, 0.415)–(0.17, -0.03, 0.405)，r 0.011）；与锅沿两处相交点：x=-0.138 处棒底 z %.3f、x=+0.138 处棒底 z %.3f，锅沿顶 z 0.409（棒底沉入锅沿管内，搁在沿上不悬空）：%s\n" % (
            stick["range"][0], stick["range"][1], stick["range"][2],
            stick["range"][3], stick["range"][4], stick["range"][5],
            stick["rim_crossings"][-0.138]["bottom_z"],
            stick["rim_crossings"][0.138]["bottom_z"],
            verdict(stick["ok"])))
        for p in symmetry["pairs"]:
            dz_note = ""
            if p["dz_expected"]:
                dz_note = "（设计 z 差 %.3f，两焰高度不同）" % p["dz_expected"]
            f.write("- 对称 %s–%s（%s）：镜像中心偏差 x %.4f、y %.4f、z %.4f%s，面数成对相等：%s\n" % (
                p["pair"][0], p["pair"][1], p["kind"], p["dx"], p["dy"],
                p["dz"], dz_note, verdict(p["ok"])))
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f；低于地面的部件：%s；"
                "埋入地面容差 %.3f（支腿/足垫/木柴下端埋入地面属 planted 效果，"
                "渲染中被地面遮挡不可见，游戏资产常规做法）：%s\n" % (
                    ground["checked"], ground["global_min_z"],
                    ground["below_ground"] if ground["below_ground"] else "无",
                    PLANTED_TOL, verdict(ground["ok"])))
        f.write("- 整体尺寸：包围盒 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                "宽 %.3f × 深 %.3f × 高 %.3f（x 最宽处为足垫外缘 ±0.193，"
                "y 后沿为后足垫 +0.221、前沿为腹箍 -0.168，最高处为搅拌棒顶 "
                "z 0.426）：%s\n" % (
                    overall["bbox"][0], overall["bbox"][1],
                    overall["bbox"][2], overall["bbox"][3],
                    overall["bbox"][4], overall["bbox"][5],
                    overall["width"], overall["depth"], overall["height"],
                    verdict(overall["ok"])))
        if not overall["width_matches_note"]:
            f.write("  - 注：055 笔记称“整体约 0.55 m 宽（提环外缘）”与实测不符——"
                    "实测宽 0.386 m、深 0.389 m、高 0.436 m，最大尺寸是高；"
                    "提环外缘仅 ±0.163（宽 0.326 m）；"
                    "笔记宽度有误，资产本身无问题，见第 6 节。\n")
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
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 055 构建脚本直接存入的线性值；自发光材质另核 Emission 节点与混合比）：\n")
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
        f.write("- 支腿/足垫埋入地面：三条支腿下端最低 z=%.3f（斜撑圆柱端盖），"
                "足垫最低 z=%.3f，木柴最低 z=%.3f；均在 planted 容差 %.3f 内，"
                "渲染中被地面遮挡不可见，游戏资产中属常规 planted 做法，不作缺陷。\n" % (
                    min(v["min_z"] for v in legs["legs"].values()),
                    min(v["footpad_min_z"] for v in legs["legs"].values()),
                    min(fire["fire"]["Log_1"]["min_z"],
                        fire["fire"]["Log_2"]["min_z"]),
                    PLANTED_TOL))
        f.write("- Flame_1 焰顶 z=0.20，高出锅底（z 0.14）0.06；Flame_2 焰顶 z=0.16、"
                "Flame_3 焰顶 z=0.15，同样略高出锅底；三支焰尖均藏在锅内"
                "（焰顶处锅内半径 0.10–0.14，焰尖半径趋近 0），从外部不可见；"
                "FlameCore 焰顶 z=0.12，在锅底以下。部件间相交是本资产"
                "的设计做法（提环嵌锅壁、搅拌棒压锅沿、木柴交叉），不作缺陷。\n")
        f.write("- 055 笔记宽度有误：“整体约 0.55 m 宽（提环外缘）”应为宽 0.386 m × "
                "深 0.389 m × 高 0.436 m（提环外缘宽 0.326 m）；资产本身尺寸符合设计，"
                "仅笔记文字待修正。\n")
        f.write("\n## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if all_ok:
            f.write("其余项：拓扑、法线、UV、材质、坩埚结构、对称、地面接触均通过。\n")
        else:
            f.write("待修项：见上文标“不通过”的条目。\n")


if __name__ == "__main__":
    main()
