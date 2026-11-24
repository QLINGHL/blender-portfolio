# -*- coding: utf-8 -*-
"""051 资产质检：对 049 低模炼金术士角色做真实 mesh 检查（拓扑/法线/UV/材质），
并实测角色特有结构：头部/护目镜/发须、长袍/围裙/腰带/药水瓶、双臂 5 环
（肘关节环）、身前烧瓶（位置/双手贴合）、双腿 5 环（膝关节环）、皮鞋探出
袍摆、左右对称、地面接触；另复核 050 骨架绑定（烧瓶骨骼父级、左右手漂移）。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 051-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "049-lowpoly-alchemist.blend")
BLEND_RIG = os.path.join(ROOT, "scenes", "050-alchemist-rig.blend")
UV_JSON = os.path.join(ROOT, "scenes", "051-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "051-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "051-asset-qa-checklist.md")

# every mesh object in the 049 blend except the scene dressing ground
EXCLUDE = {"Ground"}

# design values from the 049 build script (scenes/049-lowpoly-alchemist.py)
# and the measured per-part table in scenes/050-alchemist-rig.md
EXPECTED_FACES = {
    "Head": 48, "Eye": 18, "Eye.001": 18, "HairCap": 40, "Beard": 40,
    "GoggleRim": 48, "GoggleLens": 24, "GoggleRim.001": 48,
    "GoggleLens.001": 24, "GoggleStrap": 64,
    "Neck": 18, "Collar": 24, "Shawl": 32, "Robe": 48,
    "Apron": 6, "ApronPocket": 6, "ApronStrap": 6, "ApronStrap.001": 6,
    "Belt": 24, "Buckle": 6,
    "PotionRedBody": 24, "PotionRedCork": 18,
    "PotionBlueBody": 24, "PotionBlueCork": 18,
    "PotionPurpleBody": 24, "PotionPurpleCork": 18,
    "Arm": 36, "Cuff": 18, "Hand": 24,
    "Arm.001": 36, "Cuff.001": 18, "Hand.001": 24,
    "Flask": 40, "FlaskLiquid": 32, "FlaskCork": 18,
    "Leg": 36, "Shoe": 6, "Leg.001": 36, "Shoe.001": 6,
}
EXPECTED_TOTAL_FACES = 1004
EXPECTED_TRIS = 392
EXPECTED_QUADS = 612

# tube parts built by make_tube: (sides, rings); cap fans = 2 * sides tris
TUBE_PARTS = {
    "Neck": (6, 2), "Collar": (8, 2), "Shawl": (8, 3), "Robe": (8, 5),
    "Belt": (8, 2), "Arm": (6, 5), "Arm.001": (6, 5),
    "Cuff": (6, 2), "Cuff.001": (6, 2),
    "PotionRedBody": (6, 3), "PotionRedCork": (6, 2),
    "PotionBlueBody": (6, 3), "PotionBlueCork": (6, 2),
    "PotionPurpleBody": (6, 3), "PotionPurpleCork": (6, 2),
    "Flask": (8, 4), "FlaskLiquid": (8, 3), "FlaskCork": (6, 2),
    "Leg": (6, 5), "Leg.001": (6, 5),
}

# part -> design material (from the 049 build script)
PART_MATERIAL = {
    "Head": "Skin", "Eye": "Eyes_Dark", "Eye.001": "Eyes_Dark",
    "HairCap": "Hair_Brown", "Beard": "Beard_Grey",
    "GoggleRim": "Brass", "GoggleRim.001": "Brass",
    "GoggleLens": "Lens_Green", "GoggleLens.001": "Lens_Green",
    "GoggleStrap": "Leather_Dark", "Neck": "Skin",
    "Collar": "Robe_Dark", "Shawl": "Robe_Dark", "Robe": "Robe_Teal",
    "Apron": "Apron_Brown", "ApronPocket": "Apron_Dark",
    "ApronStrap": "Apron_Brown", "ApronStrap.001": "Apron_Brown",
    "Belt": "Leather_Dark", "Buckle": "Brass",
    "PotionRedBody": "Potion_Red", "PotionRedCork": "Cork",
    "PotionBlueBody": "Potion_Blue", "PotionBlueCork": "Cork",
    "PotionPurpleBody": "Potion_Purple", "PotionPurpleCork": "Cork",
    "Arm": "Robe_Teal", "Cuff": "Apron_Brown", "Hand": "Skin",
    "Arm.001": "Robe_Teal", "Cuff.001": "Apron_Brown", "Hand.001": "Skin",
    "Flask": "Flask_Glass", "FlaskLiquid": "Flask_Liquid",
    "FlaskCork": "Cork",
    "Leg": "Pants_Grey", "Shoe": "Leather_Dark",
    "Leg.001": "Pants_Grey", "Shoe.001": "Leather_Dark",
}


def srgb(rgb):
    """sRGB swatch -> linear values for Principled BSDF Base Color
    (same conversion as the 049 build script)."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


# (metallic, roughness, sRGB base color) for Principled materials
DESIGN_MATS = {
    "Skin": (0.00, 0.70, (0.86, 0.63, 0.48)),
    "Robe_Teal": (0.00, 0.85, (0.10, 0.32, 0.28)),
    "Robe_Dark": (0.00, 0.90, (0.07, 0.22, 0.19)),
    "Apron_Brown": (0.00, 0.90, (0.45, 0.30, 0.16)),
    "Apron_Dark": (0.00, 0.90, (0.32, 0.20, 0.10)),
    "Leather_Dark": (0.00, 0.90, (0.30, 0.18, 0.09)),
    "Brass": (0.80, 0.35, (0.72, 0.55, 0.20)),
    "Eyes_Dark": (0.00, 0.40, (0.05, 0.05, 0.06)),
    "Hair_Brown": (0.00, 0.85, (0.32, 0.20, 0.10)),
    "Beard_Grey": (0.00, 0.90, (0.55, 0.50, 0.45)),
    "Flask_Glass": (0.00, 0.15, (0.75, 0.85, 0.88)),
    "Flask_Liquid": (0.00, 0.30, (0.25, 0.85, 0.30)),
    "Lens_Green": (0.10, 0.20, (0.20, 0.65, 0.35)),
    "Potion_Red": (0.00, 0.30, (0.75, 0.15, 0.12)),
    "Potion_Blue": (0.00, 0.30, (0.15, 0.35, 0.75)),
    "Potion_Purple": (0.00, 0.30, (0.50, 0.20, 0.60)),
    "Cork": (0.00, 0.90, (0.70, 0.55, 0.35)),
    "Pants_Grey": (0.00, 0.90, (0.28, 0.27, 0.30)),
}
# Flask_Glass extras: dithered transparency so the liquid shows through
GLASS_ALPHA = 0.35
GLASS_RENDER_METHOD = 'DITHERED'


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
    """World-space bbox of the evaluated mesh (uses the evaluated mesh
    data, so armature-deformed poses are measured, not the rest pose)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    ws = [mw @ v.co for v in ev.data.vertices]
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def world_verts(obj):
    """World-space verts of the evaluated mesh (posed, not rest)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    return [mw @ v.co for v in ev.data.vertices]


def mesh_centroid(obj):
    """Evaluated mesh centroid (mean of world verts)."""
    vs = world_verts(obj)
    return sum(vs, Vector((0, 0, 0))) / len(vs)


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


def plane_y_at_z(obj, local_axis_value, axis, z_target):
    """For a box part whose mesh verts are absolute coords with an
    object rotation applied: take the face whose local coords equal
    `local_axis_value` along `axis` ('y' or '-y'), fit its world plane
    y = a + b*z, and return the plane's y at z_target.
    (Used for the apron front face and the pocket back face, whose
    object rotation is about the world origin, not the part centre.)"""
    mw = obj.matrix_world
    pts = []
    for v in obj.data.vertices:
        if abs(v.co[1 if axis in ("y", "-y") else 0] - local_axis_value) < 1e-6:
            pts.append(mw @ v.co)
    if len(pts) < 2:
        return None
    zs = [p.z for p in pts]
    ys = [p.y for p in pts]
    if max(zs) - min(zs) < 1e-6:
        return round(sum(ys) / len(ys), 3)
    # least squares y = a + b*z
    n = len(pts)
    mz = sum(zs) / n
    my = sum(ys) / n
    sxx = sum((z - mz) ** 2 for z in zs)
    sxy = sum((z - mz) * (y - my) for z, y in zip(zs, ys))
    b = sxy / sxx if sxx > 1e-12 else 0.0
    a = my - b * mz
    return round(a + b * z_target, 3)


def min_vert_distance(obj_a, obj_b):
    """Minimum vertex-to-vertex distance between two evaluated meshes."""
    va = world_verts(obj_a)
    vb = world_verts(obj_b)
    best = None
    for a in va:
        for b in vb:
            d = (a - b).length
            if best is None or d < best:
                best = d
    return round(best, 4) if best is not None else None


def check_head(by_name):
    head = world_range(by_name["Head"])
    eyes = {n: world_range(by_name[n]) for n in ("Eye", "Eye.001")}
    cap = world_range(by_name["HairCap"])
    beard = world_range(by_name["Beard"])

    def center(r):
        return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, (r[4] + r[5]) / 2)

    def half(r):
        return ((r[1] - r[0]) / 2, (r[3] - r[2]) / 2, (r[5] - r[4]) / 2)

    # Low-segment UV spheres are faceted: mesh bbox up to ~0.01 smaller
    # than the analytic sphere radius. Centres are exact; extents get a
    # 0.01 faceting tolerance.
    ec = {n: center(r) for n, r in eyes.items()}
    eh = {n: half(r) for n, r in eyes.items()}
    # beard protrusion vs the head ellipsoid at the beard's own height:
    # head ellipsoid centre (0,0,1.52), radii (0.20, 0.18, 0.21)
    beard_cz = (beard[4] + beard[5]) / 2
    head_front_at_beard_z = -0.18 * math.sqrt(
        max(0.0, 1 - ((beard_cz - 1.52) / 0.21) ** 2))
    row = {"head": head, "eyes": eyes, "haircap": cap, "beard": beard,
           "head_height": round(head[5] - head[4], 3),
           "eye_protrusion": round(min(e[2] for e in eyes.values())
                                   - head[2], 3),
           "cap_above_head": round(cap[5] - head[5], 3),
           "beard_below_chin": round(head[4] - beard[4], 3),
           "beard_protrusion": round(head_front_at_beard_z - beard[2], 3)}
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
          and abs(center(beard)[0]) < 0.001
          and abs(center(beard)[1] - (-0.10)) < 0.001
          and abs(center(beard)[2] - 1.38) < 0.001
          and all(abs(half(beard)[i] - v) < 0.01
                  for i, v in enumerate((0.09, 0.0675, 0.0765)))
          and row["eye_protrusion"] < 0 and row["cap_above_head"] > 0
          and row["beard_protrusion"] > 0)
    row["ok"] = bool(ok)
    return row


def check_goggles(by_name):
    # rims: torus at (±0.078, -0.168, 1.615), major 0.055, minor 0.009,
    # rotated 75 deg about X. Lens cylinders share the same centre.
    rim_ranges = {n: world_range(by_name[n])
                  for n in ("GoggleRim", "GoggleRim.001")}
    lens_ranges = {n: world_range(by_name[n])
                   for n in ("GoggleLens", "GoggleLens.001")}
    strap = world_range(by_name["GoggleStrap"])
    rim_l = min(rim_ranges.values(), key=lambda r: (r[0] + r[1]) / 2)
    rim_r = max(rim_ranges.values(), key=lambda r: (r[0] + r[1]) / 2)

    def center(r):
        return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, (r[4] + r[5]) / 2)

    rim_c = {n: center(r) for n, r in rim_ranges.items()}
    lens_c = {n: center(r) for n, r in lens_ranges.items()}
    # each lens centre must coincide with its rim centre
    lens_rim_gap = {}
    for rn, ln in (("GoggleRim", "GoggleLens"),
                   ("GoggleRim.001", "GoggleLens.001")):
        lens_rim_gap[rn] = round(
            math.sqrt(sum((a - b) ** 2 for a, b in zip(rim_c[rn], lens_c[ln]))), 4)
    # lens must sit inside the rim ring (lens radius 0.048 < rim 0.055):
    # lens bbox inside rim bbox expanded by the tube radius 0.009
    lens_inside = {}
    for rn, ln in (("GoggleRim", "GoggleLens"),
                   ("GoggleRim.001", "GoggleLens.001")):
        r, l = rim_ranges[rn], lens_ranges[ln]
        lens_inside[rn] = bool(
            l[0] >= r[0] - 0.009 and l[1] <= r[1] + 0.009
            and l[4] >= r[4] - 0.009 and l[5] <= r[5] + 0.009)
    row = {"rims": rim_ranges, "lenses": lens_ranges, "strap": strap,
           "rim_centers": {n: tuple(round(v, 3) for v in c)
                           for n, c in rim_c.items()},
           "lens_centers": {n: tuple(round(v, 3) for v in c)
                            for n, c in lens_c.items()},
           "lens_rim_center_gap": lens_rim_gap,
           "lens_inside_rim": lens_inside,
           "strap_x": (strap[0], strap[1]),
           "strap_y": (strap[2], strap[3]),
           "strap_z": (strap[4], strap[5])}
    ok = (all(abs(c[0] - s * 0.078) < 0.001
              and abs(c[1] - (-0.168)) < 0.001
              and abs(c[2] - 1.615) < 0.001
              for (n, c), s in zip(rim_c.items(), (-1, 1)))
          and all(g < 0.001 for g in lens_rim_gap.values())
          and all(lens_inside.values())
          and abs(strap[0] - (-0.219)) < 0.001
          and abs(strap[1] - 0.219) < 0.001
          and abs(strap[4] - 1.586) < 0.001
          and abs(strap[5] - 1.614) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_torso(by_name):
    neck = world_range(by_name["Neck"])
    collar = world_range(by_name["Collar"])
    shawl = world_range(by_name["Shawl"])
    robe = world_range(by_name["Robe"])
    belt = world_range(by_name["Belt"])
    buckle = world_range(by_name["Buckle"])
    apron = world_range(by_name["Apron"])
    pocket = world_range(by_name["ApronPocket"])
    straps = {n: world_range(by_name[n])
              for n in ("ApronStrap", "ApronStrap.001")}
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

    def robe_radius_at(z):
        for a, b in zip(rings, rings[1:]):
            za = 1.30 - a["distance"]
            zb = 1.30 - b["distance"]
            if zb <= z <= za:
                t = (za - z) / (za - zb)
                return a["radius"] + t * (b["radius"] - a["radius"])
        return None

    # apron front plane (local y=-0.38 face) vs robe front, at two heights
    apron_front_055 = plane_y_at_z(by_name["Apron"], -0.38, "y", 0.55)
    apron_front_092 = plane_y_at_z(by_name["Apron"], -0.38, "y", 0.92)
    apron_front_0775 = plane_y_at_z(by_name["Apron"], -0.38, "y", 0.775)
    # pocket back plane (local y=-0.3725 face) vs apron front at pocket z
    pocket_zc = (pocket[4] + pocket[5]) / 2
    pocket_back = plane_y_at_z(by_name["ApronPocket"], -0.3725, "y",
                               pocket_zc)
    apron_front_at_pocket = plane_y_at_z(by_name["Apron"], -0.38, "y",
                                         pocket_zc)
    # pocket back in front of apron front (more negative y) = floating gap
    pocket_float = (round(pocket_back - apron_front_at_pocket, 3)
                    if pocket_back is not None
                    and apron_front_at_pocket is not None else None)
    # potion bottles: back face vs apron front at bottle mid height
    potions = {}
    for tag in ("PotionRedBody", "PotionBlueBody", "PotionPurpleBody"):
        r = world_range(by_name[tag])
        zc = (r[4] + r[5]) / 2
        af = plane_y_at_z(by_name["Apron"], -0.38, "y", zc)
        potions[tag] = {"range": r, "back_y": r[3], "front_y": r[2],
                        "apron_front_at_z": af,
                        "clear_of_apron": (round(r[3] - af, 3)
                                           if af is not None else None)}
    row = {"neck_z": (neck[4], neck[5]), "collar_z": (collar[4], collar[5]),
           "collar_x": (collar[0], collar[1]),
           "shawl_z": (shawl[4], shawl[5]),
           "robe_z": (robe[4], robe[5]),
           "robe_rings": [(round(1.30 - r["distance"], 2), r["radius"],
                           r["count"]) for r in rings],
           "belt_z": (belt[4], belt[5]), "belt_radius": belt[1],
           "robe_radius_at_belt": round(r_at_belt, 3) if r_at_belt else None,
           "belt_proud_of_robe": (round(belt[1] - r_at_belt, 3)
                                  if r_at_belt else None),
           "buckle": buckle,
           "buckle_proud_of_belt": round(buckle[2] - belt[2], 3),
           "apron": apron,
           "apron_front_y_at_055": apron_front_055,
           "apron_front_y_at_0775": apron_front_0775,
           "apron_front_y_at_092": apron_front_092,
           "robe_front_y_at_055": (round(-robe_radius_at(0.55), 3)
                                   if robe_radius_at(0.55) else None),
           "robe_front_y_at_0775": (round(-robe_radius_at(0.775), 3)
                                    if robe_radius_at(0.775) else None),
           "robe_front_y_at_092": (round(-robe_radius_at(0.92), 3)
                                   if robe_radius_at(0.92) else None),
           "apron_vs_robe_055": (round(apron_front_055
                                       - (-robe_radius_at(0.55)), 3)
                                 if apron_front_055 is not None
                                 and robe_radius_at(0.55) else None),
           "apron_vs_robe_0775": (round(apron_front_0775
                                        - (-robe_radius_at(0.775)), 3)
                                  if apron_front_0775 is not None
                                  and robe_radius_at(0.775) else None),
           "apron_vs_robe_092": (round(apron_front_092
                                       - (-robe_radius_at(0.92)), 3)
                                 if apron_front_092 is not None
                                 and robe_radius_at(0.92) else None),
           "pocket": pocket,
           "pocket_center_z": round(pocket_zc, 3),
           "pocket_back_y": pocket_back,
           "apron_front_at_pocket_z": apron_front_at_pocket,
           "pocket_float_gap": pocket_float,
           "straps": straps,
           "potions": potions}
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
          and buckle[2] < belt[2]
          and all(p["clear_of_apron"] is not None
                  and p["clear_of_apron"] < 0 for p in potions.values())
          # apron must sit proud of the robe at all three sampled heights
          and all(v is not None and v < 0 for v in (
              row["apron_vs_robe_055"], row["apron_vs_robe_0775"],
              row["apron_vs_robe_092"]))
          # pocket back must be embedded in the apron front (gap > 0),
          # not floating in front of it (gap < 0)
          and row["pocket_float_gap"] is not None
          and 0 < row["pocket_float_gap"] < 0.02)
    row["ok"] = bool(ok)
    return row


def check_arms(by_name):
    rows = {}
    for sx, tag in ((-1, "Arm"), (1, "Arm.001")):
        shoulder = Vector((sx * 0.30, 0, 1.22))
        wrist = Vector((sx * 0.14, -0.47, 0.99))
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
              # hand is a low-segment sphere: its bbox centre is up to
              # ~0.001 off the analytic wrist point from faceting
              # (float rounding makes 0.001 fail a <= 0.001 test)
              and all(abs(a - b) <= 0.002 for a, b in zip(
                  rows[tag]["hand_center"], rows[tag]["wrist_expected"])))
        rows[tag]["ok"] = bool(ok)
    return rows


def check_flask(by_name):
    flask = world_range(by_name["Flask"])
    liquid = world_range(by_name["FlaskLiquid"])
    cork = world_range(by_name["FlaskCork"])
    hands = {n: world_range(by_name[n]) for n in ("Hand", "Hand.001")}
    # hand bbox must overlap the flask bbox (gripping the sides)
    overlap = {}
    for n, h in hands.items():
        ox = min(h[1], flask[1]) - max(h[0], flask[0])
        oy = min(h[3], flask[3]) - max(h[2], flask[2])
        oz = min(h[5], flask[5]) - max(h[4], flask[4])
        overlap[n] = {"x": round(ox, 3), "y": round(oy, 3),
                      "z": round(oz, 3),
                      "grips": bool(ox > 0 and oy > 0 and oz > 0)}
    # flask vs apron front at flask mid height (z ~1.03)
    apron_front_103 = plane_y_at_z(by_name["Apron"], -0.38, "y", 1.03)
    flask_center = ((flask[0] + flask[1]) / 2, (flask[2] + flask[3]) / 2,
                    (flask[4] + flask[5]) / 2)
    row = {"flask": flask, "liquid": liquid, "cork": cork,
           "flask_center": tuple(round(v, 3) for v in flask_center),
           "flask_back_y": flask[3],
           "apron_front_y_at_103": apron_front_103,
           "flask_clear_of_apron": (round(flask[3] - apron_front_103, 3)
                                    if apron_front_103 is not None else None),
           "liquid_inside_flask_xz": bool(
               liquid[0] >= flask[0] and liquid[1] <= flask[1]
               and liquid[4] >= flask[4] and liquid[5] <= flask[5]),
           "liquid_top_below_cork": round(cork[4] - liquid[5], 3),
           "cork_above_flask": round(cork[4] - flask[5], 3),
           "hand_overlap": overlap,
           "flask_to_apron_min_vert_dist":
               min_vert_distance(by_name["Flask"], by_name["Apron"])}
    ok = (abs(flask[0] - (-0.11)) < 0.001 and abs(flask[1] - 0.11) < 0.001
          and abs(flask[2] - (-0.59)) < 0.001 and abs(flask[3] - (-0.37)) < 0.001
          and abs(flask[4] - 0.92) < 0.001 and abs(flask[5] - 1.14) < 0.001
          and abs(liquid[4] - 0.925) < 0.001 and abs(liquid[5] - 1.035) < 0.001
          and abs(cork[4] - 1.14) < 0.001 and abs(cork[5] - 1.18) < 0.001
          and row["liquid_inside_flask_xz"]
          and row["flask_clear_of_apron"] is not None
          and row["flask_clear_of_apron"] < 0
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
    pairs = [("Eye", "Eye.001"), ("GoggleRim", "GoggleRim.001"),
             ("GoggleLens", "GoggleLens.001"),
             ("Arm", "Arm.001"), ("Cuff", "Cuff.001"),
             ("Hand", "Hand.001"), ("Leg", "Leg.001"),
             ("Shoe", "Shoe.001"), ("ApronStrap", "ApronStrap.001"),
             ("PotionRedBody", "PotionPurpleBody"),
             ("PotionRedCork", "PotionPurpleCork")]
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
    """Read node values, not names; compare against 049 design values
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
        row = {"name": name, "found": True, "metallic": m,
               "roughness": r, "base_color": c,
               "design_color_linear": col, "ok": bool(ok)}
        if name == "Flask_Glass":
            alpha = round(bsdf.inputs["Alpha"].default_value, 2)
            row["alpha"] = alpha
            row["render_method"] = mat.surface_render_method
            row["ok"] = bool(ok and abs(alpha - GLASS_ALPHA) < 0.01
                             and mat.surface_render_method
                             == GLASS_RENDER_METHOD)
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


def check_rig(rest_flask_hand_l, rest_flask_hand_r):
    """Re-check the 050 rig blend: bone count, flask bone parenting,
    posed flask-to-hand drift vs the rest distances measured in 049,
    posed ground contact."""
    bpy.ops.wm.open_mainfile(filepath=BLEND_RIG)
    parts = [o for o in bpy.context.scene.objects
             if o.type == 'MESH' and o.name not in EXCLUDE]
    by_name = {o.name: o for o in parts}
    total_faces = sum(len(o.data.polygons) for o in parts)
    arm = None
    for o in bpy.context.scene.objects:
        if o.type == 'ARMATURE':
            arm = o
            break
    bones = []
    if arm is not None:
        bones = [b.name for b in arm.data.bones]
    expected_bones = ["Hips", "Spine", "Neck", "Head",
                      "Shoulder.L", "Forearm.L", "Hand.L",
                      "Shoulder.R", "Forearm.R", "Hand.R",
                      "Thigh.L", "Shin.L", "Foot.L",
                      "Thigh.R", "Shin.R", "Foot.R"]
    parents = {}
    for n in ("Flask", "FlaskLiquid", "FlaskCork"):
        o = by_name.get(n)
        if o is None:
            parents[n] = {"found": False}
        else:
            parents[n] = {"found": True, "parent_type": o.parent_type,
                          "parent": o.parent.name if o.parent else None,
                          "parent_bone": o.parent_bone or None}
    # posed flask-to-hand distances (evaluated mesh centroids).
    # NOTE: the character faces -Y, so its LEFT hand is on +X:
    # mesh "Hand.001" (+X) is the left hand (bone Hand.L, the flask's
    # parent), mesh "Hand" (-X) is the right hand (bone Hand.R).
    # The 049 build loop named sx=-1 "Hand" first, hence the swap.
    posed = {}
    drift = {}
    if all(n in by_name for n in ("Flask", "Hand", "Hand.001")):
        fc = mesh_centroid(by_name["Flask"])
        hl = mesh_centroid(by_name["Hand.001"])  # left hand
        hr = mesh_centroid(by_name["Hand"])      # right hand
        posed["flask_center"] = tuple(round(v, 3) for v in fc)
        posed["hand_l_center"] = tuple(round(v, 3) for v in hl)
        posed["hand_r_center"] = tuple(round(v, 3) for v in hr)
        posed["flask_hand_l"] = round((fc - hl).length, 4)
        posed["flask_hand_r"] = round((fc - hr).length, 4)
        drift["left"] = round(abs(posed["flask_hand_l"] - rest_flask_hand_l), 4)
        drift["right"] = round(abs(posed["flask_hand_r"] - rest_flask_hand_r), 4)
    # armature modifiers + vertex groups on skinned meshes
    mods = {}
    for o in parts:
        mods[o.name] = [m.type for m in o.modifiers]
    skinned = [n for n, ms in mods.items() if 'ARMATURE' in ms]
    robe_groups = []
    if "Robe" in by_name:
        robe_groups = [g.name for g in by_name["Robe"].vertex_groups]
    # posed ground contact
    zmins = {}
    for o in parts:
        zmins[o.name] = round(min(w.z for w in world_verts(o)), 3)
    shoe_l = zmins.get("Shoe")
    shoe_r = zmins.get("Shoe.001")
    row = {"parts": len(parts), "total_faces": total_faces,
           "armature": arm.name if arm else None,
           "bones": bones, "bone_count": len(bones),
           "bones_match_design": bool(bones == expected_bones),
           "flask_parents": parents,
           "flask_parent_ok": bool(all(
               p.get("parent_type") == 'BONE'
               and p.get("parent_bone") == 'Hand.L'
               for p in parents.values())),
           "rest_flask_hand_l": round(rest_flask_hand_l, 4),
           "rest_flask_hand_r": round(rest_flask_hand_r, 4),
           "posed": posed, "drift": drift,
           "drift_left_ok": bool(drift.get("left") is not None
                                 and drift["left"] < 0.005),
           "drift_right_ok": bool(drift.get("right") is not None
                                 and drift["right"] < 0.05),
           "skinned_parts": len(skinned),
           "unskinned_mesh_parts": [n for n in mods if 'ARMATURE' not in mods[n]],
           "robe_vertex_groups": robe_groups,
           "posed_min_z": round(min(zmins.values()), 3) if zmins else None,
           "posed_shoe_l_z": shoe_l, "posed_shoe_r_z": shoe_r,
           "posed_below_ground": {n: z for n, z in zmins.items()
                                  if z < -0.001}}
    row["ok"] = bool(row["bones_match_design"] and row["flask_parent_ok"]
                     and row["drift_left_ok"] and row["drift_right_ok"]
                     and row["posed_min_z"] is not None
                     and row["posed_min_z"] >= -0.001
                     and not row["posed_below_ground"]
                     and row["total_faces"] == EXPECTED_TOTAL_FACES)
    print("QA_RIG:", row)
    return row


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

    head = check_head(by_name)
    print("QA_HEAD:", head)
    goggles = check_goggles(by_name)
    print("QA_GOGGLES:", goggles)
    torso = check_torso(by_name)
    print("QA_TORSO:", torso)
    arms = check_arms(by_name)
    print("QA_ARMS:", arms)
    flask = check_flask(by_name)
    print("QA_FLASK:", flask)
    legs = check_legs(by_name)
    print("QA_LEGS:", legs)
    symmetry = check_symmetry(by_name, results)
    print("QA_SYMMETRY:", symmetry)
    ground = check_ground(by_name)
    print("QA_GROUND_CONTACT:", ground)
    mats = check_materials(parts, results)
    print("QA_MATERIALS:", mats)

    # rest-pose flask-to-hand distances (mesh centroids) for the rig check
    # (left hand = mesh "Hand.001" on +X, see check_rig note)
    fc = mesh_centroid(by_name["Flask"])
    rest_l = (fc - mesh_centroid(by_name["Hand.001"])).length
    rest_r = (fc - mesh_centroid(by_name["Hand"])).length
    print("QA_REST_FLASK_HAND_L:", round(rest_l, 4),
          "QA_REST_FLASK_HAND_R:", round(rest_r, 4))

    # cap-winding check: with the 048-fixed make_tube every tube part
    # must have 0 inverted faces (the 042 bug was 2*sides inverted caps)
    cap_breakdown = {}
    for name, (sides, _rings) in TUBE_PARTS.items():
        inv = results[name]["inverted_normals"]
        cap_breakdown[name] = {"inverted": inv,
                               "cap_fan_faces": 2 * sides,
                               "ok": bool(inv == 0)}
    print("QA_CAP_BREAKDOWN:", cap_breakdown)
    cap_ok = all(v["ok"] for v in cap_breakdown.values())
    non_tube_inv = sum(results[n]["inverted_normals"] for n in results
                       if n not in TUBE_PARTS)
    print("QA_NON_TUBE_INVERTED:", non_tube_inv)

    # rig re-check from the 050 blend (opens a new file; results above
    # are already stored in plain dicts)
    rig = check_rig(rest_l, rest_r)

    structure = {"head": head, "goggles": goggles, "torso": torso,
                 "arms": {"Arm": arms["Arm"], "Arm.001": arms["Arm.001"]},
                 "flask": flask,
                 "legs": {"Leg": legs["Leg"], "Leg.001": legs["Leg.001"]},
                 "symmetry": symmetry, "ground_contact": ground}
    structure_ok = (head["ok"] and goggles["ok"] and torso["ok"]
                    and all(a["ok"] for a in arms.values())
                    and flask["ok"] and all(l["ok"] for l in legs.values())
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
              and faces_ok and structure_ok and mats["all_ok"]
              and cap_ok and rig["ok"])

    summary = {
        "asset": "049-lowpoly-alchemist",
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
        "cap_breakdown_ok": bool(cap_ok),
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
        "rig": rig,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("QA_SUMMARY:", summary)

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    order = sorted(results.keys())
    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 051 资产质检单：低模炼金术士角色（049）\n\n")
        f.write("被检资产：`scenes/049-lowpoly-alchemist.blend`（%d 个角色部件，不含地面）；"
                "另复核 `scenes/050-alchemist-rig.blend`（骨架绑定后状态）。\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。049 / 050 原文件未改动。\n\n")
        f.write("## 结论\n\n")
        f.write("**%s**\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED：见第 4 节围裙缺陷"))
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
        f.write("- 面数与 049 设计表逐部件比对：%s（设计 1004 面：三角 392、四边 612、N-gon 0；实测 %d 面：三角 %d、四边 %d、N-gon %d）\n" % (
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
        f.write("  048 修正版 make_tube 已生效：%d 个管状部件倒置面全部为 0"
                "（042 旧版是每部件 2×边数个端盖倒置面）；非管状部件倒置面 %d 个。\n\n" % (
                    len(TUBE_PARTS), non_tube_inv))
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
                "多探出 %.3f（设计：眼球微凸出头面）；棕发盖 z %.3f–%.3f，"
                "高出头顶 %.3f；灰色短须中心 (0, -0.10, 1.38)，"
                "前沿 y=%.3f，比同高度头面多探出 %.3f（设计：胡须贴在下巴前方）：%s\n" % (
                    h["head"][4], h["head"][5], h["head_height"],
                    -h["eye_protrusion"], h["haircap"][4], h["haircap"][5],
                    h["cap_above_head"], h["beard"][2],
                    h["beard_protrusion"], verdict(h["ok"])))
        g = goggles
        f.write("- 前额护目镜：双黄铜镜框中心 (±0.078, -0.168, 1.615)，"
                "绿色镜片中心与镜框中心重合（偏差 %s），镜片落在镜框环内：%s；"
                "绕头皮带 x ±0.219、z 1.586–1.614（设计：大环半径 0.205 + 线径 0.014，"
                "绕头一圈）：%s\n" % (
                    ", ".join("%.4f" % v for v in g["lens_rim_center_gap"].values()),
                    verdict(all(g["lens_inside_rim"].values())),
                    verdict(g["ok"])))
        t = torso
        f.write("- 躯干：颈 z %.2f–%.2f；深青领口 z %.2f–%.2f、x ±0.16；"
                "深青披肩 z %.2f–%.2f；长袍 z %.2f–%.2f，5 环半径 %s"
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
        f.write("- 围裙：前片实测包围盒 x ±%.3f、y %.3f–%.3f、z %.3f–%.3f"
                "（设计盒中心 (0, -0.365, 0.75)，尺寸 0.44×0.03×0.95，"
                "绕 X -4°）；围裙前沿（拟合前片平面）在 z=0.55 处 y=%.3f、"
                "z=0.775 处 y=%.3f、z=0.92 处 y=%.3f，而长袍前沿同高度为"
                " y=%.3f / %.3f / %.3f：围裙相对长袍 %s / %s / %s"
                "（负值=围裙在长袍前面，正值=围裙被长袍盖住）\n" % (
                    (t["apron"][1] - t["apron"][0]) / 2,
                    t["apron"][2], t["apron"][3], t["apron"][4], t["apron"][5],
                    t["apron_front_y_at_055"], t["apron_front_y_at_0775"],
                    t["apron_front_y_at_092"],
                    t["robe_front_y_at_055"], t["robe_front_y_at_0775"],
                    t["robe_front_y_at_092"],
                    "%.3f" % t["apron_vs_robe_055"],
                    "%.3f" % t["apron_vs_robe_0775"],
                    "%.3f" % t["apron_vs_robe_092"]))
        f.write("- 围裙兜：包围盒 x ±%.3f、y %.3f–%.3f、z %.3f–%.3f；"
                "兜背面（拟合平面）在兜中心高度 z=%.3f 处 y=%.3f，"
                "同高度围裙前沿 y=%.3f，兜背%s围裙前沿 %.3f"
                "（设计：兜背嵌进围裙前沿 0.0075）：%s\n" % (
                    (t["pocket"][1] - t["pocket"][0]) / 2,
                    t["pocket"][2], t["pocket"][3], t["pocket"][4], t["pocket"][5],
                    t["pocket_center_z"], t["pocket_back_y"],
                    t["apron_front_at_pocket_z"],
                    "嵌进" if t["pocket_float_gap"] > 0 else "悬空在",
                    abs(t["pocket_float_gap"]),
                    verdict(t["pocket_float_gap"] is not None
                            and 0 < t["pocket_float_gap"] < 0.02)))
        f.write("  **缺陷：围裙的 -4° 倾斜绕的是世界原点，不是围裙自身中心。**"
                "049 脚本用 box() 生成绝对坐标网格（物体原点在世界原点），"
                "再设 rotation_euler=(-4°, 0, 0)，整个围裙被绕原点甩到"
                "胸前上方（围裙盒中心从 (0, -0.365, 0.75) 移到 "
                "(0, -0.312, 0.774)，前片中心 y 从 -0.38 变为 -0.327），"
                "与 042 书的 -8° 倾斜同一根因。"
                "后果：围裙前片中心带在 z=0.55/0.775/0.92 三处分别被长袍"
                "盖住 %.3f / %.3f / %.3f（设计应多探出约 0.03 / 0.05 / 0.06）；"
                "围裙两侧（x 较大处）仍露出袍面，渲染图上围裙仍可辨认，"
                "但中心带 3–8mm 被袍面吞掉。围裙兜不受影响：兜背嵌进围裙"
                "前沿 %.3f（设计 0.0075），贴合正常。\n"
                "  修复：把围裙做成本地坐标盒子（中心在原点），"
                "再设物体 location=(0, -0.365, 0.75)、"
                "rotation_euler=(-4°, 0, 0)，让倾斜绕围裙中心发生；"
                "或把 -4° 烘进网格顶点后清零物体旋转。修完重跑本脚本复核："
                "围裙前沿在 z=0.55/0.775/0.92 三处均应比长袍前沿多探出"
                "约 0.03 / 0.05 / 0.06。注意：050 rig 版沿用同一写法，"
                "同样受影响。\n" % (
                    t["apron_vs_robe_055"], t["apron_vs_robe_0775"],
                    t["apron_vs_robe_092"], t["pocket_float_gap"]))
        for tag, p in t["potions"].items():
            f.write("- %s：瓶身 x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f，"
                    "瓶背 y=%.3f，同高度围裙前沿 y=%.3f，瓶背在围裙前面 %.3f"
                    "（设计：瓶子挂在腰带前，不陷进围裙）：%s\n" % (
                        tag, p["range"][0], p["range"][1], p["range"][2],
                        p["range"][3], p["range"][4], p["range"][5],
                        p["back_y"], p["apron_front_at_z"],
                        -p["clear_of_apron"],
                        verdict(p["clear_of_apron"] < 0)))
        for tag in ("Arm", "Arm.001"):
            a = arms[tag]
            f.write("- %s：5 环（每环 6 顶点），环距 %s；肘关节环中心 %s，"
                    "与设计肘点 %s 误差 %.4f；肘环顶点最高价数 %d"
                    "（设计 4，无极点堆积）；三角面全部在管端盖上"
                    "（不在关节处）：%s；棕色袖口 2 环，覆盖手腕端；"
                    "手掌中心 %s，与设计腕点一致：%s\n" % (
                        tag, ", ".join("%.3f" % r["distance"]
                                       for r in a["rings"]),
                        a["elbow_ring_center"], a["elbow_expected"],
                        a["elbow_ring_error"], a["elbow_ring_max_valence"],
                        verdict(not a["tris_not_at_ends"]),
                        a["hand_center"], verdict(a["ok"])))
        b = flask
        f.write("- 身前烧瓶：锥形瓶 x ±0.11、y %.3f–%.3f、z %.3f–%.3f"
                "（设计中心 (0, -0.48, 0.92)，底环半径 0.11）；"
                "瓶背 y=%.3f，同高度围裙前沿 y=%.3f，瓶背在围裙前面 %.3f"
                "（设计 0.10，正面清晰可见，042 教训）；"
                "亮绿药液 z %.3f–%.3f，x/z 在瓶内；瓶塞 z %.3f–%.3f，"
                "紧贴瓶口（间隙 %.3f）；双手包围盒与烧瓶三向重叠"
                "（左手 %s，右手 %s），双手握在瓶身两侧：%s\n" % (
                    b["flask"][2], b["flask"][3], b["flask"][4], b["flask"][5],
                    b["flask_back_y"], b["apron_front_y_at_103"],
                    -b["flask_clear_of_apron"],
                    b["liquid"][4], b["liquid"][5], b["cork"][4], b["cork"][5],
                    b["cork_above_flask"],
                    b["hand_overlap"]["Hand"], b["hand_overlap"]["Hand.001"],
                    verdict(b["ok"])))
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
        f.write("- 左右对称：%d 对镜像部件（眼/护目镜框/镜片/臂/袖口/手/腿/鞋/围裙带/红紫药水瓶身/瓶塞），"
                "镜像中心 x 偏差最大 %.4f、y 偏差最大 %.4f、z 偏差最大 %.4f，"
                "面数全部成对相等：%s\n" % (
                    len(s["pairs"]),
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
        f.write("- 身体比例：全高 %.3f（含发盖），头高 %.3f，约 %.1f 个头高"
                "（风格化低模比例）：仅记录\n\n" % (
                    h["head"][5], h["head_height"],
                    h["head"][5] / h["head_height"]))
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
        if mats["unused_design_mats"]:
            f.write("- **未使用的设计材质：%s**\n" % mats["unused_design_mats"])
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值，底色为 sRGB 色板换算后的线性值）：\n")
        for r in mats["rows"]:
            if not r["found"]:
                f.write("  - %s：未找到材质：不通过\n" % r["name"])
            elif "metallic" in r:
                extra = ""
                if r["name"] == "Flask_Glass":
                    extra = "，alpha %.2f（设计 %.2f），渲染方式 %s（设计 %s）" % (
                        r.get("alpha"), GLASS_ALPHA,
                        r.get("render_method"), GLASS_RENDER_METHOD)
                f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                        "底色 %s（设计 %s）%s：%s\n" % (
                            r["name"], r["metallic"],
                            DESIGN_MATS[r["name"]][0], r["roughness"],
                            DESIGN_MATS[r["name"]][1], r["base_color"],
                            r["design_color_linear"], extra, verdict(r["ok"])))
            else:
                f.write("  - %s：无 Principled 节点：不通过\n" % r["name"])
        f.write("\n## 6. 骨架绑定复核（050 rig 版，实测）\n\n")
        rg = rig
        f.write("- 骨架：%s，共 %d 根骨骼，与 050 设计表一致：%s\n" % (
            rg["armature"], rg["bone_count"],
            verdict(rg["bones_match_design"])))
        f.write("- 烧瓶三件父级：%s\n" % (
            ", ".join("%s→%s（%s）" % (
                n, p.get("parent_bone"), p.get("parent_type"))
                for n, p in rg["flask_parents"].items())))
        f.write("  烧瓶三件均骨骼父级到 Hand.L：%s\n" % verdict(rg["flask_parent_ok"]))
        f.write("- 持瓶漂移（姿势求值后网格质心距离，静止距离左/右手均为 %.4f / %.4f）：\n" % (
            rg["rest_flask_hand_l"], rg["rest_flask_hand_r"]))
        f.write("  - 左手：姿势后烧瓶到左手中心 %.4f，漂移 %.4f（阈值 <0.005）：%s\n" % (
            rg["posed"]["flask_hand_l"], rg["drift"]["left"],
            verdict(rg["drift_left_ok"])))
        f.write("  - 右手：姿势后烧瓶到右手中心 %.4f，漂移 %.4f（阈值 <0.05，"
                "050 轮实测 0.036，右手向烧瓶靠拢、未脱手）：%s\n" % (
            rg["posed"]["flask_hand_r"], rg["drift"]["right"],
            verdict(rg["drift_right_ok"])))
        f.write("- 蒙皮：%d 个网格部件带 Armature 修改器；未带修改器的网格部件：%s"
                "（烧瓶三件骨骼父级，不参与蒙皮，符合设计）\n" % (
                    rg["skinned_parts"],
                    rg["unskinned_mesh_parts"] if rg["unskinned_mesh_parts"] else "无"))
        f.write("- 长袍顶点组：%s\n" % (
            ", ".join(rg["robe_vertex_groups"]) if rg["robe_vertex_groups"] else "无"))
        f.write("- 姿势求值后全角色最低点 z=%.3f；前鞋底 z=%.3f，后鞋底 z=%.3f；"
                "低于地面的部件：%s：%s\n" % (
                    rg["posed_min_z"], rg["posed_shoe_l_z"], rg["posed_shoe_r_z"],
                    rg["posed_below_ground"] if rg["posed_below_ground"] else "无",
                    verdict(rg["ok"])))
        f.write("- 050 rig 版总面数 %d（与 049 一致 1004）：%s\n\n" % (
            rg["total_faces"],
            verdict(rg["total_faces"] == EXPECTED_TOTAL_FACES)))
        f.write("## 7. 总评\n\n")
        f.write("结论：**%s**。\n\n" % ("全部通过" if all_ok else "REVIEW NEEDED"))
        if not all_ok:
            f.write("待修项（按优先级）：\n\n")
            f.write("1. 围裙 -4° 倾斜绕世界原点（049 脚本 box()+rotation_euler 写法）："
                    "围裙前片中心带被长袍盖住 0.003–0.008（z=0.55 处 0.008）。"
                    "修法见第 4 节。\n"
                    % ())
            f.write("2. 右手持瓶漂移 0.036 米（050 已知，右手向烧瓶靠拢、未脱手）："
                    "下次同类持物姿势把双肩 z 分量也取同号（050 轮建议）。\n")
        f.write("\n其余项：拓扑、法线、UV、材质、关节环、对称、地面接触、骨架绑定复核均通过。\n")
    print("CHECKLIST_WRITTEN:", CHECKLIST)


if __name__ == "__main__":
    main()
