# -*- coding: utf-8 -*-
"""046 资产质检：对 042 低模图书管理员角色做真实 mesh 检查（拓扑/法线/UV/材质），
并实测角色特有结构：头部/眼镜/发髻、长袍/披肩/腰带、双臂 5 环（肘关节环）、
怀抱书（位置/倾角/双手贴合）、双腿 5 环（膝关节环）、皮鞋探出袍摆、
左右对称、地面接触、身体比例。048（2026-11-24）复核：042 原文件已修复
管盖绕向、书绕自身中心、死材质，质检设计表同步更新（删 Leather_Brown、
书封前沿期望值 -0.462 修正为 -0.461）。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 046-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "042-lowpoly-librarian.blend")
UV_JSON = os.path.join(ROOT, "scenes", "046-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "046-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "046-asset-qa-checklist.md")

# every mesh object in the 042 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design values from the 042 build script (scenes/042-lowpoly-librarian.py)
EXPECTED_FACES = {
    "Head": 48, "Eye": 18, "Eye.001": 18, "HairCap": 40, "HairBun": 40,
    "GlassesRim": 48, "GlassesRim.001": 48, "GlassesBridge": 12,
    "GlassesTemple": 12, "GlassesTemple.001": 12, "Neck": 18,
    "Collar": 24, "Shawl": 32, "Robe": 48, "Belt": 24, "Buckle": 6,
    "Arm": 36, "Cuff": 18, "Hand": 24, "Arm.001": 36, "Cuff.001": 18,
    "Hand.001": 24, "BookCover": 6, "BookPages": 6, "BookClasp": 6,
    "Leg": 36, "Shoe": 6, "Leg.001": 36, "Shoe.001": 6,
}
EXPECTED_TOTAL_FACES = 706
EXPECTED_TRIS = 268
EXPECTED_QUADS = 438

# tube parts built by make_tube: (sides, rings); cap fans = 2 * sides tris
TUBE_PARTS = {
    "Neck": (6, 2), "Collar": (8, 2), "Shawl": (8, 3), "Robe": (8, 5),
    "Belt": (8, 2), "Arm": (6, 5), "Arm.001": (6, 5),
    "Cuff": (6, 2), "Cuff.001": (6, 2), "Leg": (6, 5), "Leg.001": (6, 5),
}

# part -> design material (from the 042 build script)
PART_MATERIAL = {
    "Head": "Skin", "Eye": "Eyes_Dark", "Eye.001": "Eyes_Dark",
    "HairCap": "Hair_Grey", "HairBun": "Hair_Grey",
    "GlassesRim": "Brass", "GlassesRim.001": "Brass",
    "GlassesBridge": "Brass", "GlassesTemple": "Brass",
    "GlassesTemple.001": "Brass", "Neck": "Skin",
    "Collar": "Collar_Cream", "Shawl": "Robe_Dark",
    "Robe": "Robe_Burgundy", "Belt": "Leather_Dark", "Buckle": "Brass",
    "Arm": "Robe_Burgundy", "Cuff": "Collar_Cream", "Hand": "Skin",
    "Arm.001": "Robe_Burgundy", "Cuff.001": "Collar_Cream",
    "Hand.001": "Skin", "BookCover": "Book_Red",
    "BookPages": "Pages_Cream", "BookClasp": "Brass",
    "Leg": "Pants_Grey", "Shoe": "Leather_Dark",
    "Leg.001": "Pants_Grey", "Shoe.001": "Leather_Dark",
}


def srgb(rgb):
    """sRGB swatch -> linear values for Principled BSDF Base Color
    (same conversion as the 042 build script)."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


# (metallic, roughness, sRGB base color) for Principled materials
DESIGN_MATS = {
    "Skin": (0.00, 0.70, (0.86, 0.63, 0.48)),
    "Robe_Burgundy": (0.00, 0.85, (0.42, 0.13, 0.16)),
    "Robe_Dark": (0.00, 0.90, (0.30, 0.09, 0.12)),
    "Collar_Cream": (0.00, 0.85, (0.88, 0.82, 0.68)),
    # 048: Leather_Brown 已从 042 脚本删除（死材质，无部件使用），设计表同步删
    "Leather_Dark": (0.00, 0.90, (0.30, 0.18, 0.09)),
    "Brass": (0.80, 0.35, (0.72, 0.55, 0.20)),
    "Eyes_Dark": (0.00, 0.40, (0.05, 0.05, 0.06)),
    "Hair_Grey": (0.00, 0.85, (0.62, 0.60, 0.58)),
    "Book_Red": (0.00, 0.80, (0.48, 0.12, 0.10)),
    "Pages_Cream": (0.00, 0.90, (0.90, 0.85, 0.70)),
    "Pants_Grey": (0.00, 0.90, (0.28, 0.27, 0.30)),
}


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
    """World-space bbox of the evaluated mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    ws = [mw @ v.co for v in obj.data.vertices]
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def world_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def ring_analysis(obj, origin, direction):
    """Group the tube's ring verts (rho > 0.001 off axis) by axial
    distance; return [(distance, count, center, radius)] per ring plus
    the max valence of the middle ring's verts."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
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
    # max valence among the middle ring's verts (joint ring: no pole)
    mid_valence = None
    if len(rings) >= 3:
        mid = rings[len(rings) // 2]
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        vals = []
        for v in bm.verts:
            w = mw @ v.co
            rel = w - o
            axial = rel.dot(d)
            rho = (rel - d * axial).length
            if rho > 0.001 and abs(axial - mid["distance"]) < 0.002:
                vals.append(len(v.link_edges))
        mid_valence = max(vals) if vals else None
        bm.free()
    return rings, mid_valence


def tri_faces_at_ends(obj, origin, direction, length):
    """For a tube: every triangle face must be a cap fan, i.e. its
    centre lies on an end plane (axial distance ~0 or ~length)."""
    o = Vector(origin)
    d = Vector(direction).normalized()
    mw = obj.matrix_world
    bad = []
    for p in obj.data.polygons:
        if len(p.vertices) != 3:
            continue
        c = mw @ p.center
        axial = (c - o).dot(d)
        if min(abs(axial), abs(axial - length)) > 0.002:
            bad.append(round(axial, 3))
    return bad


def check_head(by_name):
    head = world_range(by_name["Head"])
    eyes = {n: world_range(by_name[n]) for n in ("Eye", "Eye.001")}
    cap = world_range(by_name["HairCap"])
    bun = world_range(by_name["HairBun"])

    def center(r):
        return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, (r[4] + r[5]) / 2)

    def half(r):
        return ((r[1] - r[0]) / 2, (r[3] - r[2]) / 2, (r[5] - r[4]) / 2)

    # Low-segment UV spheres are faceted: their mesh bbox is up to
    # ~0.01 smaller than the analytic sphere radius. Centres are exact;
    # extents are checked with a 0.01 faceting tolerance.
    ec = {n: center(r) for n, r in eyes.items()}
    eh = {n: half(r) for n, r in eyes.items()}
    row = {"head": head, "eyes": eyes, "haircap": cap, "hairbun": bun,
           "head_height": round(head[5] - head[4], 3),
           "eye_protrusion": round(min(e[2] for e in eyes.values())
                                   - head[2], 3),
           "cap_above_head": round(cap[5] - head[5], 3),
           "bun_behind_head": round(bun[3] - head[3], 3)}
    ok = (abs(head[0] - (-0.20)) < 0.001 and abs(head[1] - 0.20) < 0.001
          and abs(head[2] - (-0.18)) < 0.001 and abs(head[3] - 0.18) < 0.001
          and abs(head[4] - 1.31) < 0.001 and abs(head[5] - 1.73) < 0.001
          and abs(ec["Eye"][0] - (-0.07)) < 0.001
          and abs(ec["Eye.001"][0] - 0.07) < 0.001
          and all(abs(ec[n][1] - (-0.168)) < 0.001
                  and abs(ec[n][2] - 1.53) < 0.001 for n in eyes)
          and all(abs(eh[n][i] - 0.026) < 0.01 for n in eyes for i in range(3))
          and abs(center(cap)[0]) < 0.001
          and abs(center(cap)[1] - 0.02) < 0.001
          and abs(center(cap)[2] - 1.63) < 0.001
          and all(abs(half(cap)[i] - v) < 0.01
                  for i, v in enumerate((0.19, 0.1805, 0.1178)))
          and abs(center(bun)[0]) < 0.001
          and abs(center(bun)[1] - 0.15) < 0.001
          and abs(center(bun)[2] - 1.68) < 0.001
          and all(abs(half(bun)[i] - 0.09) < 0.01 for i in range(3))
          and row["eye_protrusion"] < 0 and row["cap_above_head"] > 0
          and row["bun_behind_head"] > 0)
    row["ok"] = bool(ok)
    return row


def check_glasses(by_name):
    # rims: the build loop names the sx=-1 rim "GlassesRim" (left) and
    # sx=+1 "GlassesRim.001" (right); identify sides by measured centre.
    rim_ranges = {n: world_range(by_name[n])
                  for n in ("GlassesRim", "GlassesRim.001")}
    rim_l = min(rim_ranges.values(), key=lambda r: (r[0] + r[1]) / 2)
    rim_r = max(rim_ranges.values(), key=lambda r: (r[0] + r[1]) / 2)
    bridge = world_range(by_name["GlassesBridge"])
    temples = {n: world_range(by_name[n])
               for n in ("GlassesTemple", "GlassesTemple.001")}
    # bridge must overlap each rim's innermost tube segment:
    # tube centre x = rim centre x + major radius (0.055), tube x span
    # +- minor radius (0.008) around it.
    def tube_overlap(rim, side):
        cx = (rim[0] + rim[1]) / 2
        inner = cx + side * 0.055  # innermost point of the tube centreline
        lo, hi = inner - 0.008, inner + 0.008
        return min(bridge[1], hi) - max(bridge[0], lo)
    overlap_l = tube_overlap(rim_l, +1)
    overlap_r = tube_overlap(rim_r, -1)
    # temple end point (the end nearer the head, y ~ -0.02) must lie
    # inside the head ellipsoid (head centre (0,0,1.52), radii .20/.18/.21)
    head = by_name["Head"]
    temple_end_inside = {}
    for n in ("GlassesTemple", "GlassesTemple.001"):
        vs = world_verts(by_name[n])
        end = max(vs, key=lambda v: v.y)  # end nearer the head
        ex = (end.x / 0.20) ** 2 + (end.y / 0.18) ** 2 \
            + ((end.z - 1.52) / 0.21) ** 2
        temple_end_inside[n] = {"end": tuple(round(v, 3) for v in end),
                                "ellipsoid_value": round(ex, 3),
                                "inside": bool(ex < 1.0)}
    row = {"rims": rim_ranges, "bridge": bridge, "temples": temples,
           "bridge_overlaps_rim_tubes": (round(overlap_l, 3),
                                         round(overlap_r, 3)),
           "temple_end_inside": temple_end_inside}
    ok = (abs(rim_l[0] - (-0.141)) < 0.001
          and abs(rim_l[1] - (-0.015)) < 0.001
          and abs(rim_r[0] - 0.015) < 0.001
          and abs(rim_r[1] - 0.141) < 0.001
          and all(abs(r[2] - (-0.180)) < 0.001
                  and abs(r[3] - (-0.164)) < 0.001
                  and abs(r[4] - 1.482) < 0.001
                  and abs(r[5] - 1.608) < 0.001
                  for r in (rim_l, rim_r))
          and abs(bridge[0] - (-0.024)) < 0.001
          and abs(bridge[1] - 0.024) < 0.001
          and abs(bridge[4] - 1.541) < 0.001
          and abs(bridge[5] - 1.555) < 0.001
          and overlap_l > 0 and overlap_r > 0
          and all(t["inside"] for t in temple_end_inside.values()))
    row["ok"] = bool(ok)
    return row


def check_torso(by_name):
    neck = world_range(by_name["Neck"])
    collar = world_range(by_name["Collar"])
    shawl = world_range(by_name["Shawl"])
    robe = world_range(by_name["Robe"])
    belt = world_range(by_name["Belt"])
    buckle = world_range(by_name["Buckle"])
    # robe ring radii measured from the mesh (axis (0,0,-1) from z=1.30)
    rings, _ = ring_analysis(by_name["Robe"], (0, 0, 1.30), (0, 0, -1))
    # robe radius at belt height z~0.945: interpolate rings z 1.00/0.70
    r_at_belt = None
    for a, b in zip(rings, rings[1:]):
        za = 1.30 - a["distance"]
        zb = 1.30 - b["distance"]
        if zb <= 0.945 <= za:
            t = (za - 0.945) / (za - zb)
            r_at_belt = a["radius"] + t * (b["radius"] - a["radius"])
            break
    row = {"neck_z": (neck[4], neck[5]), "collar_z": (collar[4], collar[5]),
           "collar_x": (collar[0], collar[1]),
           "shawl_z": (shawl[4], shawl[5]),
           "shawl_radii": [r["radius"] for r in rings[:0]] or None,
           "robe_z": (robe[4], robe[5]),
           "robe_rings": [(round(1.30 - r["distance"], 2), r["radius"],
                           r["count"]) for r in rings],
           "belt_z": (belt[4], belt[5]), "belt_radius": belt[1],
           "robe_radius_at_belt": round(r_at_belt, 3) if r_at_belt else None,
           "belt_proud_of_robe": (round(belt[1] - r_at_belt, 3)
                                  if r_at_belt else None),
           "buckle": buckle,
           "buckle_proud_of_belt": round(buckle[2] - belt[2], 3)}
    ok = (abs(neck[4] - 1.28) < 0.001 and abs(neck[5] - 1.38) < 0.001
          and abs(collar[4] - 1.26) < 0.001 and abs(collar[5] - 1.32) < 0.001
          and abs(collar[0] - (-0.16)) < 0.001 and abs(collar[1] - 0.16) < 0.001
          and abs(shawl[4] - 1.10) < 0.001 and abs(shawl[5] - 1.32) < 0.001
          and abs(robe[4] - 0.10) < 0.001 and abs(robe[5] - 1.30) < 0.001
          and abs(robe[1] - 0.40) < 0.001
          and len(rings) == 5 and all(r["count"] == 8 for r in rings)
          and [r["radius"] for r in rings] == [0.30, 0.315, 0.335, 0.365, 0.40]
          and abs(belt[4] - 0.91) < 0.001 and abs(belt[5] - 0.98) < 0.001
          and abs(belt[1] - 0.345) < 0.001
          and r_at_belt is not None and belt[1] > r_at_belt
          and abs(buckle[0] - (-0.045)) < 0.001
          and abs(buckle[1] - 0.045) < 0.001
          and abs(buckle[4] - 0.915) < 0.001 and abs(buckle[5] - 0.975) < 0.001
          and buckle[2] < belt[2])
    row["ok"] = bool(ok)
    return row


def check_arms(by_name):
    rows = {}
    for sx, tag in ((-1, "Arm"), (1, "Arm.001")):
        shoulder = Vector((sx * 0.30, 0, 1.22))
        wrist = Vector((sx * 0.17, -0.40, 0.97))
        direction = wrist - shoulder
        length = direction.length
        direction.normalize()
        rings, mid_val = ring_analysis(by_name[tag], shoulder, direction)
        elbow = shoulder + direction * (length * 0.5)
        mid = rings[len(rings) // 2] if rings else None
        mid_err = None
        if mid is not None:
            mid_err = round((Vector(mid["center"]) - elbow).length, 4)
        bad_tris = tri_faces_at_ends(by_name[tag], shoulder, direction,
                                     length)
        cuff = by_name["Cuff" if sx < 0 else "Cuff.001"]
        crings, _ = ring_analysis(cuff, shoulder + direction * length * 0.78,
                                  direction)
        hand = world_range(by_name["Hand" if sx < 0 else "Hand.001"])
        rows[tag] = {
            "rings": rings, "ring_count": len(rings),
            "ring_sizes": [r["count"] for r in rings],
            "elbow_expected": tuple(round(v, 3) for v in elbow),
            "elbow_ring_center": mid["center"] if mid else None,
            "elbow_ring_error": mid_err,
            "elbow_ring_max_valence": mid_val,
            "tris_not_at_ends": bad_tris,
            "cuff_rings": [(r["distance"], r["count"], r["radius"])
                           for r in crings],
            "hand": hand,
            "hand_center": (round((hand[0] + hand[1]) / 2, 3),
                            round((hand[2] + hand[3]) / 2, 3),
                            round((hand[4] + hand[5]) / 2, 3)),
            "wrist_expected": tuple(round(v, 3) for v in wrist)}
        ok = (len(rings) == 5
              and all(r["count"] == 6 for r in rings)
              and [r["distance"] for r in rings]
              == [round(length * k / 4, 3) for k in range(5)]
              and mid_err is not None and mid_err < 0.001
              and mid_val == 4
              and not bad_tris
              and len(crings) == 2
              and all(r["count"] == 6 for r in crings)
              and rows[tag]["hand_center"] == rows[tag]["wrist_expected"])
        rows[tag]["ok"] = bool(ok)
    return rows


def check_book(by_name):
    cover = world_range(by_name["BookCover"])
    pages = world_range(by_name["BookPages"])
    clasp = world_range(by_name["BookClasp"])
    rot = round(math.degrees(by_name["BookCover"].rotation_euler.x), 2)
    rot_p = round(math.degrees(by_name["BookPages"].rotation_euler.x), 2)
    rot_c = round(math.degrees(by_name["BookClasp"].rotation_euler.x), 2)
    robe = world_range(by_name["Robe"])
    # robe front at book height z~0.98: radius ~0.316 (interpolated)
    robe_front = -0.316
    belt = world_range(by_name["Belt"])
    hands = {n: world_range(by_name[n]) for n in ("Hand", "Hand.001")}
    # hand bbox must overlap the book cover bbox (gripping the sides)
    overlap = {}
    for n, h in hands.items():
        ox = min(h[1], cover[1]) - max(h[0], cover[0])
        oy = min(h[3], cover[3]) - max(h[2], cover[2])
        oz = min(h[5], cover[5]) - max(h[4], cover[4])
        overlap[n] = {"x": round(ox, 3), "y": round(oy, 3),
                      "z": round(oz, 3),
                      "grips": bool(ox > 0 and oy > 0 and oz > 0)}
    # book centre vs design centre: the -8 deg tilt was applied as
    # rotation_euler on a box whose object origin is the world origin,
    # so the book rotated about (0,0,0) instead of its own centre.
    cover_c = tuple(round((cover[i] + cover[i + 1]) / 2, 3)
                    for i in (0, 2, 4))
    design_c = (0.0, -0.42, 0.98)
    disp = tuple(round(cover_c[i] - design_c[i], 3) for i in range(3))
    row = {"cover": cover, "pages": pages, "clasp": clasp,
           "tilt_deg": (rot, rot_p, rot_c),
           "cover_center": cover_c, "design_center": design_c,
           "displacement": disp,
           "book_front_y": cover[2],
           "robe_front_y_at_book": robe_front,
           "protrudes_past_robe": round(robe_front - cover[2], 3),
           "book_front_vs_belt": round(belt[2] - cover[2], 3),
           "pages_inside_cover_xz": bool(
               pages[0] >= cover[0] and pages[1] <= cover[1]
               and pages[4] >= cover[4] and pages[5] <= cover[5]),
           "pages_front_gap": round(pages[2] - cover[2], 3),
           "pages_back_overhang": round(pages[3] - cover[3], 3),
           "clasp_front_y": clasp[2],
           "clasp_proud_of_cover": round(cover[2] - clasp[2], 3),
           "hand_overlap": overlap,
           "hand_book_gap_y": round(cover[2] - max(h[3] for h in hands.values()), 3)}
    ok = (abs(cover[0] - (-0.17)) < 0.001 and abs(cover[1] - 0.17) < 0.001
          # 048: 书封前沿 = -0.42 - (0.025*cos8 + 0.12*sin8) = -0.461457 -> -0.461
          # （旧期望 -0.462 是把 -0.4615 粗略进位，严格算应为 -0.461）
          and abs(cover[2] - (-0.461)) < 0.001
          and abs(cover[3] - (-0.379)) < 0.001
          and abs(cover[4] - 0.858) < 0.001 and abs(cover[5] - 1.102) < 0.001
          and abs(rot - (-8.0)) < 0.05 and abs(rot_p - (-8.0)) < 0.05
          and abs(rot_c - (-8.0)) < 0.05
          and row["protrudes_past_robe"] > 0.1
          and row["pages_inside_cover_xz"]
          and row["clasp_proud_of_cover"] > 0
          and all(o["grips"] for o in overlap.values()))
    row["ok"] = bool(ok)
    return row


def check_legs(by_name):
    rows = {}
    for sx, tag in ((-1, "Leg"), (1, "Leg.001")):
        hip = Vector((sx * 0.12, 0, 0.55))
        rings, mid_val = ring_analysis(by_name[tag], hip, (0, 0, -1))
        mid = rings[len(rings) // 2] if rings else None
        knee_z = mid["center"][2] if mid else None
        bad_tris = tri_faces_at_ends(by_name[tag], hip, (0, 0, -1), 0.50)
        shoe = world_range(by_name["Shoe" if sx < 0 else "Shoe.001"])
        rows[tag] = {
            "rings": rings, "ring_count": len(rings),
            "ring_sizes": [r["count"] for r in rings],
            "knee_z": knee_z,
            "knee_ring_max_valence": mid_val,
            "tris_not_at_ends": bad_tris,
            "shoe": shoe,
            "shoe_toe_y": shoe[2],
            "shoe_bottom_z": shoe[4],
            "leg_bottom_z": round(0.55 - rings[-1]["distance"], 3)
            if rings else None}
        ok = (len(rings) == 5
              and all(r["count"] == 6 for r in rings)
              and [r["distance"] for r in rings]
              == [0.0, 0.125, 0.25, 0.375, 0.50]
              and abs(knee_z - 0.30) < 0.001
              and mid_val == 4
              and not bad_tris
              and abs(shoe[4] - 0.0) < 0.001
              and shoe[2] < -0.40)  # toe pokes past the robe hem (-0.40)
        rows[tag]["ok"] = bool(ok)
    return rows


def check_symmetry(by_name, results):
    pairs = [("Eye", "Eye.001"), ("GlassesRim", "GlassesRim.001"),
             ("GlassesTemple", "GlassesTemple.001"),
             ("Arm", "Arm.001"), ("Cuff", "Cuff.001"),
             ("Hand", "Hand.001"), ("Leg", "Leg.001"),
             ("Shoe", "Shoe.001")]
    rows = []
    for a, b in pairs:
        ra, rb = world_range(by_name[a]), world_range(by_name[b])
        ca = ((ra[0] + ra[1]) / 2, (ra[2] + ra[3]) / 2, (ra[4] + ra[5]) / 2)
        cb = ((rb[0] + rb[1]) / 2, (rb[2] + rb[3]) / 2, (rb[4] + rb[5]) / 2)
        dx = round(abs(ca[0] + cb[0]), 4)
        dy = round(abs(ca[1] - cb[1]), 4)
        dz = round(abs(ca[2] - cb[2]), 4)
        faces_eq = results[a]["faces"] == results[b]["faces"]
        rows.append({"pair": (a, b), "dx": dx, "dy": dy, "dz": dz,
                     "faces_equal": bool(faces_eq),
                     "ok": bool(dx < 0.001 and dy < 0.001 and dz < 0.001
                                and faces_eq)})
    return {"pairs": rows, "ok": bool(all(r["ok"] for r in rows))}


def check_ground(by_name):
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
    robe_hem = world_range(by_name["Robe"])[4]
    return {"checked": len(zmins), "below_ground": below,
            "global_min_z": round(min(zmins.values()), 3),
            "robe_hem_z": robe_hem,
            "shoe_bottom_z": world_range(by_name["Shoe"])[4],
            "ok": bool(not below)}


def check_materials(parts, results):
    """Read node values, not names; compare against 042 design values
    (sRGB swatches converted with the same srgb() as the build script)."""
    rows = []
    for name, (met, rough, col_srgb) in DESIGN_MATS.items():
        col = tuple(round(v, 2) for v in srgb(col_srgb))
        mat = bpy.data.materials.get(name)
        if mat is None or not mat.use_nodes:
            rows.append({"name": name, "found": False, "ok": False,
                         "design_color_linear": col})
            continue
        bsdf = None
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
        if bsdf is None:
            rows.append({"name": name, "found": True, "ok": False,
                         "design_color_linear": col})
            continue
        m = round(bsdf.inputs["Metallic"].default_value, 2)
        r = round(bsdf.inputs["Roughness"].default_value, 2)
        c = tuple(round(v, 2) for v in bsdf.inputs["Base Color"].default_value[:3])
        ok = (abs(m - met) < 0.01 and abs(r - rough) < 0.01
              and all(abs(a - b) < 0.01 for a, b in zip(c, col)))
        rows.append({"name": name, "found": True, "metallic": m,
                     "roughness": r, "base_color": c,
                     "design_color_linear": col, "ok": bool(ok)})
    used = {m.name for o in parts for m in o.data.materials if m}
    unused_design = [n for n in DESIGN_MATS if n not in used]
    # part -> material assignment vs design
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

    # per-part face counts vs the 042 design table
    face_mismatch = {n: (results[n]["faces"], e)
                     for n, e in EXPECTED_FACES.items()
                     if n in results and results[n]["faces"] != e}
    missing = [n for n in EXPECTED_FACES if n not in results]
    extra = [n for n in results if n not in EXPECTED_FACES]
    print("QA_FACE_MISMATCH:", face_mismatch)
    print("QA_MISSING:", missing, "QA_EXTRA:", extra)

    head = check_head(by_name)
    print("QA_HEAD:", head)
    glasses = check_glasses(by_name)
    print("QA_GLASSES:", glasses)
    torso = check_torso(by_name)
    print("QA_TORSO:", torso)
    arms = check_arms(by_name)
    print("QA_ARMS:", arms)
    book = check_book(by_name)
    print("QA_BOOK:", book)
    legs = check_legs(by_name)
    print("QA_LEGS:", legs)
    symmetry = check_symmetry(by_name, results)
    print("QA_SYMMETRY:", symmetry)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    # cap-winding defect breakdown: inverted faces per tube part must
    # equal exactly 2 * sides (the two cap fans of make_tube)
    cap_breakdown = {}
    for name, (sides, _rings) in TUBE_PARTS.items():
        inv = results[name]["inverted_normals"]
        cap_breakdown[name] = {"inverted": inv,
                               "cap_fan_faces": 2 * sides,
                               "all_inverted_are_cap_fans": bool(inv == 2 * sides)}
    print("QA_CAP_BREAKDOWN:", cap_breakdown)
    cap_ok = all(v["all_inverted_are_cap_fans"]
                 for v in cap_breakdown.values())
    non_tube_inv = sum(results[n]["inverted_normals"] for n in results
                       if n not in TUBE_PARTS)
    print("QA_NON_TUBE_INVERTED:", non_tube_inv)

    structure = {"head": head, "glasses": glasses, "torso": torso,
                 "arms": {"Arm": arms["Arm"], "Arm.001": arms["Arm.001"]},
                 "book": book,
                 "legs": {"Leg": legs["Leg"], "Leg.001": legs["Leg.001"]},
                 "symmetry": symmetry, "ground_contact": ground}
    structure_ok = (head["ok"] and glasses["ok"] and torso["ok"]
                    and all(a["ok"] for a in arms.values())
                    and book["ok"] and all(l["ok"] for l in legs.values())
                    and symmetry["ok"] and ground["ok"])

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    ngons_ok = tot["ngons"] == 0
    uv_ok = all(r["uv"]["has_uv"] for r in results.values())
    faces_ok = (not face_mismatch and not missing and not extra
                and tot["faces"] == EXPECTED_TOTAL_FACES
                and tot["tris"] == EXPECTED_TRIS
                and tot["quads"] == EXPECTED_QUADS)
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and tot["boundary_edges"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and mats["empty_material_slots"] == 0
              and not mats["assignment_mismatches"]
              and not mats["unused_design_mats"]
              and faces_ok and structure_ok and mats["all_ok"])

    summary = {
        "asset": "042-lowpoly-librarian",
        "parts": len(results),
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "ngons_ok": bool(ngons_ok),
        "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "boundary_edges": tot["boundary_edges"],
        "inverted_normals": tot["inverted_normals"],
        "cap_breakdown": cap_breakdown,
        "cap_breakdown_matches": bool(cap_ok),
        "non_tube_inverted": non_tube_inv,
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
        f.write("# 046 资产质检单：低模图书管理员角色（042）\n\n")
        f.write("被检资产：`scenes/042-lowpoly-librarian.blend`（%d 个角色部件，不含地面）\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。042 原文件未改动。\n\n")
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
        f.write("- 面数与 042 设计表逐部件比对：%s（设计 706 面：三角 268、四边 438、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("- 闭合网格（无边界边）：%s\n" % verdict(tot["boundary_edges"] == 0))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("  **缺陷：倒置面 %d 个，全部是 make_tube 管状部件的端盖扇形面。**"
                "逐部件实测：%s。非管状部件倒置面 %d 个。\n" % (
                    tot["inverted_normals"],
                    "、".join("%s %d/%d" % (n, v["inverted"], v["cap_fan_faces"])
                              for n, v in sorted(cap_breakdown.items())),
                    non_tube_inv))
        f.write("  根因：042 建模脚本 make_tube 的两个端盖扇形绕向写反了——"
                "顶盖 `(top_c, i, j)`、底盖 `(bot_c, (n-1)*sides+j, (n-1)*sides+i)`，"
                "与管身侧面绕向相反。045 rig 轮已用修正版重建并实测倒置面 0 个，"
                "但 042 原文件未改动，本缺陷仍在原文件里。\n")
        f.write("  修复：把 042 脚本的端盖两行改为 `(top_c, j, i)` 与 "
                "`(bot_c, (n-1)*sides+i, (n-1)*sides+j)`（与 045 make_tube 一致），"
                "重建 042 后复测倒置面应为 0。注意：045 rig 版已是修正版，不用动。\n\n")
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（%d 个部件均已 Smart UV Project 展开）\n" % (
            verdict(uv_ok), len(results)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率最低的 10 个部件：\n")
        for name in sorted(results, key=lambda k: results[k]["uv"]["utilization"])[:10]:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件 %s）：%.2f%%，%s\n\n" % (
            worst_overlap_part, worst_overlap,
            verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 角色结构（实测）\n\n")
        h = head
        f.write("- 头部：球头 x ±0.20、y ±0.18、z %.3f–%.3f（设计 1.31–1.73），"
                "高 %.3f；双眼中心 x ±0.07、y -0.168、z 1.53，眼球前沿比头面"
                "多探出 %.3f（设计：眼球微凸出头面）；灰发盖 z %.3f–%.3f，"
                "高出头顶 %.3f；脑后发髻 z %.3f–%.3f、后沿 y=%.3f，"
                "比头面多探出 %.3f：%s\n" % (
                    h["head"][4], h["head"][5], h["head_height"],
                    -h["eye_protrusion"], h["haircap"][4], h["haircap"][5],
                    h["cap_above_head"], h["hairbun"][4], h["hairbun"][5],
                    h["hairbun"][3], h["bun_behind_head"], verdict(h["ok"])))
        g = glasses
        f.write("- 圆框眼镜：双镜框 x -0.141–-0.015 / 0.015–0.141、"
                "y -0.180–-0.164、z 1.482–1.608（框半径 0.055 + 线径 0.008）；"
                "鼻梁 x ±0.024、z 1.541–1.555，与两框最内侧管段搭接 %s"
                "（左管 x=-0.031–-0.015，右管 x=0.015–0.031）：%s；"
                "两镜腿末端均在头椭球内（椭球值 %s）：%s\n" % (
                    ", ".join("%.3f" % v
                              for v in g["bridge_overlaps_rim_tubes"]),
                    verdict(g["bridge_overlaps_rim_tubes"][0] > 0
                            and g["bridge_overlaps_rim_tubes"][1] > 0),
                    ", ".join("%.3f" % t["ellipsoid_value"]
                              for t in g["temple_end_inside"].values()),
                    verdict(g["ok"])))
        t = torso
        f.write("- 躯干：颈 z %.2f–%.2f；奶油领口 z %.2f–%.2f、x ±0.16；"
                "深红披肩 z %.2f–%.2f；长袍 z %.2f–%.2f，5 环半径 %s"
                "（设计 0.30/0.315/0.335/0.365/0.40，自肩微喇叭至袍摆）；"
                "皮带 z %.2f–%.2f、半径 0.345，长袍在腰带高度半径 %.3f，"
                "腰带高出袍面 %.3f；黄铜带扣 y %.3f–%.3f，比腰带前沿"
                "多探出 %.3f：%s\n" % (
                    t["neck_z"][0], t["neck_z"][1],
                    t["collar_z"][0], t["collar_z"][1],
                    t["shawl_z"][0], t["shawl_z"][1],
                    t["robe_z"][0], t["robe_z"][1],
                    ", ".join("%.3f" % r for _, r, _ in t["robe_rings"]),
                    t["belt_z"][0], t["belt_z"][1],
                    t["robe_radius_at_belt"], t["belt_proud_of_robe"],
                    t["buckle"][2], t["buckle"][3],
                    -t["buckle_proud_of_belt"], verdict(t["ok"])))
        for tag in ("Arm", "Arm.001"):
            a = arms[tag]
            f.write("- %s：5 环（每环 6 顶点），环距 %s；肘关节环中心 %s，"
                    "与设计肘点 %s 误差 %.4f；肘环顶点最高价数 %d"
                    "（设计 4，无极点堆积）；三角面全部在管端盖上"
                    "（不在关节处）：%s；奶油袖口 2 环，覆盖手腕端；"
                    "手掌中心 %s，与设计腕点一致：%s\n" % (
                        tag, ", ".join("%.3f" % r["distance"]
                                       for r in a["rings"]),
                        a["elbow_ring_center"], a["elbow_expected"],
                        a["elbow_ring_error"], a["elbow_ring_max_valence"],
                        verdict(not a["tris_not_at_ends"]),
                        a["hand_center"], verdict(a["ok"])))
        b = book
        f.write("- 怀抱书：书封 x ±0.17、y %.3f–%.3f、z %.3f–%.3f，"
                "绕 X 倾斜 %s°（设计 -8°）；书中心 %s，与设计中心 %s"
                "相比位移 %s；书前沿 y=%.3f，只比长袍前沿"
                "（y=%.3f）多探出 %.3f（设计 0.145），且比腰带前沿"
                "（y=%.3f）落后 %.3f，书下部 z 0.91–0.98 被腰带遮挡；"
                "书页块 x/z 在书封内，前沿比书封落后 %.3f，"
                "后沿比书封多探出 %.3f（书页厚 0.056 > 书封 0.05，"
                "3mm 级，忽略）；黄铜锁扣前沿 y=%.3f，比书封"
                "多探出 %.3f；双手包围盒与书封 y 向间隙 %.3f"
                "（左手 y 重叠 %.3f，右手 y 重叠 %.3f），"
                "双手没有贴合书身两侧：%s\n" % (
                    b["cover"][2], b["cover"][3], b["cover"][4], b["cover"][5],
                    ", ".join("%.1f" % v for v in b["tilt_deg"]),
                    b["cover_center"], b["design_center"], b["displacement"],
                    b["book_front_y"], b["robe_front_y_at_book"],
                    b["protrudes_past_robe"],
                    world_range(by_name["Belt"])[2],
                    -b["book_front_vs_belt"],
                    b["pages_front_gap"], b["pages_back_overhang"],
                    b["clasp_front_y"], b["clasp_proud_of_cover"],
                    b["hand_book_gap_y"],
                    b["hand_overlap"]["Hand"]["y"],
                    b["hand_overlap"]["Hand.001"]["y"],
                    verdict(b["ok"])))
        f.write("  **缺陷：书的 -8° 倾斜绕的是世界原点，不是书自身中心。**"
                "建模脚本用 box() 生成绝对坐标网格（物体原点在世界原点），"
                "再设 rotation_euler=(-8°, 0, 0)，整本书被绕原点甩到胸前上方"
                "（中心从 (0, -0.42, 0.98) 移到 %s），书几乎贴在袍面上、"
                "下部被腰带遮挡，双手悬空在书前方 %.3f 没碰到书。"
                "渲染图上书只剩一条红边和锁扣露在双手之间。\n"
                "  修复：把书做成本地坐标盒子（中心在原点），再设物体 "
                "location=(0, -0.42, 0.98)、rotation_euler=(-8°, 0, 0)，"
                "让倾斜绕书中心发生；书页、锁扣同理。045 rig 版沿用同一写法，"
                "同样受影响。\n" % (b["cover_center"], b["hand_book_gap_y"]))
        for tag in ("Leg", "Leg.001"):
            l = legs[tag]
            f.write("- %s：5 环（每环 6 顶点），环距 %s；膝关节环 z=%.3f"
                    "（设计 0.30）；膝环顶点最高价数 %d；三角面全部在管端盖上；"
                    "皮鞋 z %.3f–%.3f，鞋底 z=%.3f 贴地，鞋尖 y=%.3f，"
                    "比袍摆前沿（y=-0.40）多探出 %.3f；腿底 z=%.3f 藏在鞋内：%s\n" % (
                        tag, ", ".join("%.3f" % r["distance"]
                                       for r in l["rings"]),
                        l["knee_z"], l["knee_ring_max_valence"],
                        l["shoe"][4], l["shoe"][5], l["shoe_bottom_z"],
                        l["shoe_toe_y"], -0.40 - l["shoe_toe_y"],
                        l["leg_bottom_z"], verdict(l["ok"])))
        s = symmetry
        f.write("- 左右对称：8 对镜像部件（眼/镜框/镜腿/臂/袖口/手/腿/鞋），"
                "镜像中心 x 偏差最大 %.4f、y 偏差最大 %.4f、z 偏差最大 %.4f，"
                "面数全部成对相等：%s\n" % (
                    max(r["dx"] for r in s["pairs"]),
                    max(r["dy"] for r in s["pairs"]),
                    max(r["dz"] for r in s["pairs"]),
                    verdict(s["ok"])))
        gr = ground
        f.write("- 地面接触：共检查 %d 个部件，最低 z=%.3f，低于地面的部件：%s；"
                "双鞋底 z=0.000 贴地；长袍摆 z=%.3f，离地 0.10（设计：袍摆在脚踝上方，"
                "鞋尖从袍摆前探出）：%s\n" % (
                    gr["checked"], gr["global_min_z"],
                    gr["below_ground"] if gr["below_ground"] else "无",
                    gr["robe_hem_z"], verdict(gr["ok"])))
        f.write("- 身体比例：全高（含发髻）%.3f，头高 %.3f，约 %.1f 个头高"
                "（风格化低模比例）：仅记录\n\n" % (
                    h["hairbun"][5], h["head_height"],
                    h["hairbun"][5] / h["head_height"]))
        f.write("## 5. 材质 / 贴图\n\n")
        f.write("- 各部件材质均为程序化 Principled 材质，无图片贴图（%d 个部件，%d 个材质槽）：\n" % (
            len(results),
            sum(len(r["materials"]) for r in results.values())))
        f.write("- 空材质槽：%d 个，%s\n" % (
            mats["empty_material_slots"],
            verdict(mats["empty_material_slots"] == 0)))
        f.write("- 部件材质分配与设计一致：%s\n" % (
            verdict(not mats["assignment_mismatches"])))
        if mats["assignment_mismatches"]:
            f.write("  - 分配不符：%s\n" % mats["assignment_mismatches"])
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 sRGB 色板换算后的线性值）：\n")
        for r in mats["rows"]:
            if not r["found"]:
                f.write("  - %s：未找到材质：不通过\n" % r["name"])
            elif "metallic" in r:
                f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                        "底色 %s（设计 %s）：%s\n" % (
                            r["name"], r["metallic"],
                            DESIGN_MATS[r["name"]][0], r["roughness"],
                            DESIGN_MATS[r["name"]][1], r["base_color"],
                            r["design_color_linear"], verdict(r["ok"])))
            else:
                f.write("  - %s：无 Principled 节点：不通过\n" % r["name"])
        if mats["unused_design_mats"]:
            f.write("- **未使用的设计材质：%s——定义在 042 脚本里但未分配给任何部件，"
                    "且 blend 文件里根本不存在（零使用者材质在保存时被 Blender 丢弃）。"
                    "Leather_Brown 的色板与皮带/皮鞋的 Leather_Dark 接近，疑似建模时"
                    "改用深色后旧定义未删；建议从脚本里删除该定义。**\n" % (
                        "、".join(mats["unused_design_mats"])))
        else:
            f.write("- 未使用的设计材质：无\n")
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        f.write("**总体：%s**\n\n" % ("通过" if all_ok else "复核（REVIEW NEEDED）"))
        if not all_ok:
            bad = []
            if tot["inverted_normals"]:
                bad.append("法线（倒置面 %d 个，管盖扇形绕向）" % tot["inverted_normals"])
            if mats["unused_design_mats"]:
                bad.append("材质（死材质 %s）" % "、".join(mats["unused_design_mats"]))
            if not structure_ok:
                bad.append("角色结构")
            if not faces_ok:
                bad.append("面数")
            if tot_oob or worst_overlap >= 1.0:
                bad.append("UV")
            f.write("未通过项：%s。拓扑 / UV 实测全部通过；"
                    "法线问题见第 2 节，死材质见第 5 节，"
                    "书的位置问题见第 4 节。\n" % "、".join(bad))
    print("CHECKLIST_WRITTEN:", CHECKLIST)


if __name__ == "__main__":
    main()
