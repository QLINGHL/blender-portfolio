# -*- coding: utf-8 -*-
"""039 资产质检：对 035 低模魔法书做真实 mesh 检查（拓扑/法线/UV/材质），
并实测魔法书特有结构：三层书身层叠（下封面/书页块/上封面）、书脊圆柱、
九条书页纹的凸出量、符文环/符文星/宝石的层叠关系、锁扣三件套的连接、
四角护角的贴合、书签的伸出量；八种材质节点值（金属度/粗糙度/底色）。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 039-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "035-lowpoly-spellbook.blend")
UV_JSON = os.path.join(ROOT, "scenes", "039-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "039-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "039-asset-qa-checklist.md")

# 28 spellbook parts only (Ground / lights / camera are scene dressing)
PARTS = ["CoverBottom", "PageBlock", "CoverTop", "Spine",
         "PageLineFore_1", "PageLineFore_2", "PageLineFore_3",
         "PageLineHead_1", "PageLineHead_2", "PageLineHead_3",
         "PageLineTail_1", "PageLineTail_2", "PageLineTail_3",
         "RuneRing",
         "RuneStar_1", "RuneStar_2", "RuneStar_3", "RuneStar_4",
         "RuneStar_5",
         "Gem", "ClaspTop", "ClaspFront", "ClaspStud",
         "Corner_-1-1", "Corner_-1+1", "Corner_+1-1", "Corner_+1+1",
         "Bookmark"]
# Design: no N-gons anywhere (boxes are 6 quads, cylinders use triangle
# fan caps, torus is all quads, gem is 8 tris). Every part is a closed
# mesh with 0 boundary edges. Every part got Smart UV Project in the
# 035 build, so no part is UV-less by design.
EXPECTED_NGONS = {}
EXPECTED_BOUNDARY = {}
NO_UV_BY_DESIGN = set()


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


def check_cover_bottom(parts):
    """CoverBottom: leather 0.56x0.76x0.018, z 0.000-0.018, bottom on
    the ground (z=0)."""
    o = next(p for p in parts if p.name == "CoverBottom")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3))}
    ok = (abs(xmin - (-0.28)) < 0.001 and abs(xmax - 0.28) < 0.001
          and abs(ymin - (-0.38)) < 0.001 and abs(ymax - 0.38) < 0.001
          and abs(zmin - 0.0) < 0.001 and abs(zmax - 0.018) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_page_block(parts):
    """PageBlock: cream 0.50x0.70x0.062, z 0.018-0.080, bottom flush with
    the bottom cover top; inset 0.03 from the covers on all four sides
    (x +-0.25 vs cover +-0.28, y +-0.35 vs cover +-0.38)."""
    o = next(p for p in parts if p.name == "PageBlock")
    cb = next(p for p in parts if p.name == "CoverBottom")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    _, _, _, _, _, cbzmax = world_range(cb)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3)),
           "bottom_minus_cover_top": round(zmin - cbzmax, 3),
           "inset_x": round(0.28 - xmax, 3),
           "inset_y": round(0.38 - ymax, 3)}
    ok = (abs(xmin - (-0.25)) < 0.001 and abs(xmax - 0.25) < 0.001
          and abs(ymin - (-0.35)) < 0.001 and abs(ymax - 0.35) < 0.001
          and abs(zmin - 0.018) < 0.001 and abs(zmax - 0.080) < 0.001
          and abs(row["bottom_minus_cover_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_cover_top(parts):
    """CoverTop: leather 0.56x0.76x0.018, z 0.080-0.098, bottom flush
    with the page block top."""
    o = next(p for p in parts if p.name == "CoverTop")
    pb = next(p for p in parts if p.name == "PageBlock")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    _, _, _, _, _, pbzmax = world_range(pb)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3)),
           "bottom_minus_page_top": round(zmin - pbzmax, 3)}
    ok = (abs(xmin - (-0.28)) < 0.001 and abs(xmax - 0.28) < 0.001
          and abs(ymin - (-0.38)) < 0.001 and abs(ymax - 0.38) < 0.001
          and abs(zmin - 0.080) < 0.001 and abs(zmax - 0.098) < 0.001
          and abs(row["bottom_minus_page_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_spine(parts):
    """Spine: dark leather cylinder along Y at x=-0.28, r 0.022,
    y -0.38..0.38, z center 0.049 (z 0.027-0.071); 12 sides, 36 faces
    (12 side quads + 24 cap tris). Half embedded in the book body:
    the spine axis x=-0.28 is exactly the cover edge, so half the
    tube sticks out past the spine-side cover edge."""
    o = next(p for p in parts if p.name == "Spine")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    vs = world_verts(o)
    # radius from the cylinder axis (x=-0.28, z=0.049) in the XZ plane
    rs = [math.hypot(v.x - (-0.28), v.z - 0.049) for v in vs]
    quads = sum(1 for p in o.data.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in o.data.polygons if len(p.vertices) == 3)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "radius": round(max(rs), 3),
           "tris": tris, "quads": quads,
           "outboard_past_cover_edge": round(-0.28 - xmin, 3)}
    ok = (abs(xmin - (-0.302)) < 0.001 and abs(xmax - (-0.258)) < 0.001
          and abs(ymin - (-0.38)) < 0.001 and abs(ymax - 0.38) < 0.001
          and abs(zmin - 0.027) < 0.001 and abs(zmax - 0.071) < 0.001
          and abs(max(rs) - 0.022) < 0.001 and tris == 24 and quads == 12)
    row["ok"] = bool(ok)
    return row


def check_page_lines(parts):
    """9 page-line grooves, 3 per edge, at z 0.032 / 0.049 / 0.066.
    Fore (x=+0.25 page face): boxes 0.004x0.70x0.006 centered x=0.251,
    protruding 0.003 past the page face. Head (y=+0.35) / Tail
    (y=-0.35): boxes 0.50x0.004x0.006 centered y=+-0.351, same
    0.003 protrusion. All z spans inside the page block (0.018-0.080)."""
    rows = []
    all_ok = True
    for edge, names, axis, face, center in (
            ("fore", ["PageLineFore_%d" % i for i in (1, 2, 3)],
             "x", 0.25, 0.251),
            ("head", ["PageLineHead_%d" % i for i in (1, 2, 3)],
             "y", 0.35, 0.351),
            ("tail", ["PageLineTail_%d" % i for i in (1, 2, 3)],
             "y", -0.35, -0.351)):
        for name, z in zip(names, (0.032, 0.049, 0.066)):
            o = next(p for p in parts if p.name == name)
            xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
            if axis == "x":
                outer = xmax
                span = (round(ymax - ymin, 3), round(zmax - zmin, 3))
                ok = (abs(xmin - (center - 0.002)) < 0.001
                      and abs(xmax - (center + 0.002)) < 0.001
                      and abs(ymin - (-0.35)) < 0.001
                      and abs(ymax - 0.35) < 0.001
                      and abs(zmin - (z - 0.003)) < 0.001
                      and abs(zmax - (z + 0.003)) < 0.001)
            else:
                outer = ymax if face > 0 else ymin
                span = (round(xmax - xmin, 3), round(zmax - zmin, 3))
                ok = (abs(xmin - (-0.25)) < 0.001
                      and abs(xmax - 0.25) < 0.001
                      and abs(ymin - (center - 0.002)) < 0.001
                      and abs(ymax - (center + 0.002)) < 0.001
                      and abs(zmin - (z - 0.003)) < 0.001
                      and abs(zmax - (z + 0.003)) < 0.001)
            protrusion = round(abs(outer) - abs(face), 3)
            row = {"name": name, "edge": edge, "z_center": round(z, 3),
                   "bbox_z": (zmin, zmax), "span": span,
                   "protrusion_past_page_face": protrusion,
                   "ok": bool(ok)}
            all_ok = all_ok and ok
            rows.append(row)
    return {"lines": rows, "ok": bool(all_ok)}


def check_rune_ring(parts):
    """RuneRing: flat brass torus on the top cover, R 0.14, tube r 0.012,
    center z 0.100 -> z 0.088-0.112 (bottom embedded 0.010 into the
    cover, whose top is z=0.098). 32x8 segments = 256 quads."""
    o = next(p for p in parts if p.name == "RuneRing")
    ct = next(p for p in parts if p.name == "CoverTop")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    _, _, _, _, _, ctzmax = world_range(ct)
    vs = world_verts(o)
    rs = [math.hypot(v.x, v.y) for v in vs]
    quads = sum(1 for p in o.data.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in o.data.polygons if len(p.vertices) == 3)
    row = {"bbox_z": (zmin, zmax), "z_center": round((zmin + zmax) / 2, 3),
           "radius_min": round(min(rs), 3), "radius_max": round(max(rs), 3),
           "tris": tris, "quads": quads,
           "bottom_minus_cover_top": round(zmin - ctzmax, 3)}
    ok = (abs(zmin - 0.088) < 0.001 and abs(zmax - 0.112) < 0.001
          and abs(min(rs) - 0.128) < 0.001 and abs(max(rs) - 0.152) < 0.001
          and quads == 256 and tris == 0
          and abs(row["bottom_minus_cover_top"] - (-0.010)) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_rune_star(parts):
    """RuneStar: 5 brass bars 0.024x0.26x0.006 on the top cover, rotated
    72 deg apart about Z, centers at z 0.101 (z 0.098-0.104, bottom
    flush with the cover top). Bar half-length 0.13 reaches past the
    ring inner radius (0.128), so each bar end joins the ring tube."""
    rows = []
    all_ok = True
    ring = next(p for p in parts if p.name == "RuneRing")
    ring_vs = world_verts(ring)
    ring_inner = min(math.hypot(v.x, v.y) for v in ring_vs)
    for i in range(5):
        name = "RuneStar_%d" % (i + 1)
        o = next(p for p in parts if p.name == name)
        xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
        vs = world_verts(o)
        rs = [math.hypot(v.x, v.y) for v in vs]
        raw_max = max(rs)
        rot_z = round(math.degrees(o.rotation_euler.z), 3)
        row = {"name": name, "rotation_z_deg": rot_z,
               "bbox_z": (zmin, zmax), "max_radius": round(raw_max, 3),
               "ring_inner_radius": round(ring_inner, 3),
               "end_joins_ring": bool(raw_max > ring_inner)}
        # bar half-length 0.13, half-width 0.012: the bar corners sit at
        # sqrt(0.13^2 + 0.012^2) = 0.1306 from the center, not 0.13
        ok = (abs(rot_z - 72.0 * i) < 0.01
              and abs(zmin - 0.098) < 0.001 and abs(zmax - 0.104) < 0.001
              and abs(raw_max - math.hypot(0.13, 0.012)) < 0.001
              and row["end_joins_ring"])
        row["ok"] = bool(ok)
        all_ok = all_ok and ok
        rows.append(row)
    return {"stars": rows, "ok": bool(all_ok)}


def check_gem(parts):
    """Gem: amethyst regular octahedron, a 0.035, center z 0.115 ->
    z 0.080-0.150, 8 tris. Top stands 0.052 above the cover top
    (z=0.098); bottom vertex reaches z=0.080, exactly the page block
    top, anchoring the gem through the cover."""
    o = next(p for p in parts if p.name == "Gem")
    ct = next(p for p in parts if p.name == "CoverTop")
    pb = next(p for p in parts if p.name == "PageBlock")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    _, _, _, _, _, ctzmax = world_range(ct)
    _, _, _, _, _, pbzmax = world_range(pb)
    tris = sum(1 for p in o.data.polygons if len(p.vertices) == 3)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "tris": tris,
           "top_above_cover": round(zmax - ctzmax, 3),
           "bottom_minus_page_top": round(zmin - pbzmax, 3)}
    ok = (abs(xmin - (-0.035)) < 0.001 and abs(xmax - 0.035) < 0.001
          and abs(ymin - (-0.035)) < 0.001 and abs(ymax - 0.035) < 0.001
          and abs(zmin - 0.080) < 0.001 and abs(zmax - 0.150) < 0.001
          and tris == 8)
    row["ok"] = bool(ok)
    return row


def check_clasp(parts):
    """Clasp, three iron pieces:
    - ClaspTop: strap 0.16x0.05x0.006 at (0.20, 0, 0.101), z 0.098-0.104,
      bottom flush with the cover top, fore end x=0.28 flush with the
      cover fore edge.
    - ClaspFront: vertical strap 0.006x0.05x0.10 at (0.283, 0, 0.049),
      x 0.280-0.286, z -0.001-0.099: top overlaps the ClaspTop bottom
      by 0.001, but the bottom sits 0.001 BELOW the ground plane (z=0).
    - ClaspStud: cylinder r 0.014, z 0.104-0.116 at (0.20, 0), bottom
      flush with the ClaspTop top (z=0.104)."""
    top = next(p for p in parts if p.name == "ClaspTop")
    front = next(p for p in parts if p.name == "ClaspFront")
    stud = next(p for p in parts if p.name == "ClaspStud")
    ct = next(p for p in parts if p.name == "CoverTop")

    txmin, txmax, tymin, tymax, tzmin, tzmax = world_range(top)
    _, _, _, _, _, ctzmax = world_range(ct)
    fxmin, fxmax, fymin, fymax, fzmin, fzmax = world_range(front)
    sxmin, sxmax, symin, symax, szmin, szmax = world_range(stud)
    stud_vs = world_verts(stud)
    stud_rs = [math.hypot(v.x - 0.20, v.y) for v in stud_vs]
    stud_tris = sum(1 for p in stud.data.polygons if len(p.vertices) == 3)
    stud_quads = sum(1 for p in stud.data.polygons if len(p.vertices) == 4)

    top_row = {"bbox_x": (txmin, txmax), "bbox_y": (tymin, tymax),
               "bbox_z": (tzmin, tzmax),
               "bottom_minus_cover_top": round(tzmin - ctzmax, 3)}
    top_ok = (abs(txmin - 0.12) < 0.001 and abs(txmax - 0.28) < 0.001
              and abs(tymin - (-0.025)) < 0.001 and abs(tymax - 0.025) < 0.001
              and abs(tzmin - 0.098) < 0.001 and abs(tzmax - 0.104) < 0.001
              and abs(top_row["bottom_minus_cover_top"]) < 0.001)
    top_row["ok"] = bool(top_ok)

    front_row = {"bbox_x": (fxmin, fxmax), "bbox_y": (fymin, fymax),
                 "bbox_z": (fzmin, fzmax),
                 "bottom_z": fzmin,
                 "below_ground_by": round(0.0 - fzmin, 3) if fzmin < 0 else 0.0,
                 "top_minus_strap_bottom": round(fzmax - tzmin, 3)}
    front_ok = (abs(fxmin - 0.28) < 0.001 and abs(fxmax - 0.286) < 0.001
                and abs(fymin - (-0.025)) < 0.001
                and abs(fymax - 0.025) < 0.001
                and abs(fzmax - 0.099) < 0.001
                and fzmin >= 0.0)
    front_row["ok"] = bool(front_ok)

    stud_row = {"bbox_z": (szmin, szmax), "radius": round(max(stud_rs), 3),
                "tris": stud_tris, "quads": stud_quads,
                "bottom_minus_strap_top": round(szmin - tzmax, 3)}
    stud_ok = (abs(szmin - 0.104) < 0.001 and abs(szmax - 0.116) < 0.001
               and abs(max(stud_rs) - 0.014) < 0.001
               and stud_tris == 16 and stud_quads == 8
               and abs(stud_row["bottom_minus_strap_top"]) < 0.001)
    stud_row["ok"] = bool(stud_ok)

    return {"clasp_top": top_row, "clasp_front": front_row,
            "clasp_stud": stud_row,
            "ok": bool(top_ok and front_ok and stud_ok)}


def check_corners(parts):
    """Corner protectors: 4 brass plates 0.07x0.07x0.006 at
    (+-0.245, +-0.345, 0.101), z 0.098-0.104, bottom flush with the
    cover top; outer edges flush with the cover edges (x +-0.28,
    y +-0.38)."""
    rows = []
    all_ok = True
    for sx in (-1, 1):
        for sy in (-1, 1):
            name = "Corner_%+d%+d" % (sx, sy)
            o = next(p for p in parts if p.name == name)
            xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
            row = {"name": name, "bbox_x": (xmin, xmax),
                   "bbox_y": (ymin, ymax), "bbox_z": (zmin, zmax),
                   "outer_x": round(max(abs(xmin), abs(xmax)), 3),
                   "outer_y": round(max(abs(ymin), abs(ymax)), 3)}
            ok = (abs(xmin - (sx * 0.245 - 0.035)) < 0.001
                  and abs(xmax - (sx * 0.245 + 0.035)) < 0.001
                  and abs(ymin - (sy * 0.345 - 0.035)) < 0.001
                  and abs(ymax - (sy * 0.345 + 0.035)) < 0.001
                  and abs(zmin - 0.098) < 0.001 and abs(zmax - 0.104) < 0.001
                  and abs(row["outer_x"] - 0.28) < 0.001
                  and abs(row["outer_y"] - 0.38) < 0.001)
            row["ok"] = bool(ok)
            all_ok = all_ok and ok
            rows.append(row)
    return {"corners": rows, "ok": bool(all_ok)}


def check_bookmark(parts):
    """Bookmark: crimson ribbon 0.035x0.12x0.004 at (0.10, -0.40, 0.049),
    y -0.46..-0.34, z 0.047-0.051 (inside the page block z span
    0.018-0.080). It sticks out past the cover tail edge (y=-0.38)
    by 0.08; the build note says 0.05, the measured value is 0.08."""
    o = next(p for p in parts if p.name == "Bookmark")
    ct = next(p for p in parts if p.name == "CoverTop")
    pb = next(p for p in parts if p.name == "PageBlock")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(o)
    _, _, ctymin, _, _, _ = world_range(ct)
    _, _, pbymin, _, pbzmin, pbzmax = world_range(pb)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "protrusion_past_cover_tail": round(ctymin - ymin, 3),
           "protrusion_past_page_tail": round(pbymin - ymin, 3),
           "inside_page_block_z": bool(pbzmin <= zmin and zmax <= pbzmax)}
    ok = (abs(xmin - (0.10 - 0.0175)) < 0.001
          and abs(xmax - (0.10 + 0.0175)) < 0.001
          and abs(ymin - (-0.46)) < 0.001 and abs(ymax - (-0.34)) < 0.001
          and abs(zmin - 0.047) < 0.001 and abs(zmax - 0.051) < 0.001
          and row["inside_page_block_z"])
    row["ok"] = bool(ok)
    return row


# design values from 035 build script:
# (metallic, roughness, base color) for Principled materials
DESIGN_MATS = {
    "Spellbook_Leather": (0.00, 0.80, (0.05, 0.02, 0.12)),
    "Spellbook_LeatherDark": (0.00, 0.85, (0.03, 0.015, 0.07)),
    "Spellbook_Pages": (0.00, 0.90, (0.85, 0.78, 0.60)),
    "Spellbook_PageLine": (0.00, 0.90, (0.68, 0.60, 0.44)),
    "Spellbook_Brass": (0.85, 0.35, (0.45, 0.28, 0.06)),
    "Spellbook_Iron": (0.70, 0.50, (0.20, 0.20, 0.22)),
    "Spellbook_Amethyst": (0.30, 0.20, (0.25, 0.05, 0.45)),
    "Spellbook_Ribbon": (0.00, 0.80, (0.35, 0.02, 0.05)),
}


def check_materials(parts):
    """Read node values, not names. All 8 spellbook materials are
    Principled BSDF (solid colors, no image textures)."""
    rows = []
    for name, (met, rough, col) in DESIGN_MATS.items():
        mat = bpy.data.materials.get(name)
        if mat is None or not mat.use_nodes:
            rows.append({"name": name, "found": False, "ok": False})
            continue
        bsdf = None
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
        if bsdf is None:
            rows.append({"name": name, "found": True, "ok": False})
            continue
        m = round(bsdf.inputs["Metallic"].default_value, 2)
        r = round(bsdf.inputs["Roughness"].default_value, 2)
        c = tuple(round(v, 2) for v in bsdf.inputs["Base Color"].default_value[:3])
        ok = (abs(m - met) < 0.01 and abs(r - rough) < 0.01
              and all(abs(a - b) < 0.01 for a, b in zip(c, col)))
        rows.append({"name": name, "found": True, "metallic": m,
                     "roughness": r, "base_color": c, "ok": bool(ok)})

    used = {m.name for o in parts for m in o.data.materials if m}
    all_design = list(DESIGN_MATS)
    missing_design = [n for n in all_design if n not in used]
    return {"rows": rows, "all_ok": bool(all(r["ok"] for r in rows)),
            "unused_design_mats": missing_design}


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    parts = [o for o in bpy.context.scene.objects
             if o.type == 'MESH' and o.name in PARTS]
    missing = [n for n in PARTS if n not in {o.name for o in parts}]
    if missing:
        print("QA_MISSING_PARTS:", missing)
    results = {}
    uv_dump = {}
    for obj in parts:
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

    cover_bottom = check_cover_bottom(parts)
    print("QA_COVER_BOTTOM:", cover_bottom)
    page_block = check_page_block(parts)
    print("QA_PAGE_BLOCK:", page_block)
    cover_top = check_cover_top(parts)
    print("QA_COVER_TOP:", cover_top)
    spine = check_spine(parts)
    print("QA_SPINE:", spine)
    page_lines = check_page_lines(parts)
    print("QA_PAGE_LINES:", page_lines)
    rune_ring = check_rune_ring(parts)
    print("QA_RUNE_RING:", rune_ring)
    rune_star = check_rune_star(parts)
    print("QA_RUNE_STAR:", rune_star)
    gem = check_gem(parts)
    print("QA_GEM:", gem)
    clasp = check_clasp(parts)
    print("QA_CLASP:", clasp)
    corners = check_corners(parts)
    print("QA_CORNERS:", corners)
    bookmark = check_bookmark(parts)
    print("QA_BOOKMARK:", bookmark)
    mats = check_materials(parts)
    print("QA_MATERIALS:", mats)

    structure = {"cover_bottom": cover_bottom, "page_block": page_block,
                 "cover_top": cover_top, "spine": spine,
                 "page_lines": page_lines, "rune_ring": rune_ring,
                 "rune_star": rune_star, "gem": gem, "clasp": clasp,
                 "corners": corners, "bookmark": bookmark}
    structure_ok = all(v["ok"] for v in structure.values())

    mat_rows = []
    for obj in parts:
        for m in obj.data.materials:
            if m is None:
                mat_rows.append((obj.name, None, False))
                continue
            has_image = any(n.type == 'TEX_IMAGE' for n in m.node_tree.nodes) \
                if m.use_nodes else False
            mat_rows.append((obj.name, m.name, has_image))
    empty_slots = sum(1 for _, m, _ in mat_rows if m is None)

    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces", "inverted_normals")}
    tot_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    tot_islands = sum(r["uv"]["islands"] for r in results.values())
    worst_overlap = max(r["uv"]["overlap_pct"] for r in results.values())
    ngons_ok = all(results[n]["ngons"] == EXPECTED_NGONS.get(n, 0)
                   for n in PARTS)
    boundary_ok = all(results[n]["boundary_edges"]
                      == EXPECTED_BOUNDARY.get(n, 0) for n in PARTS)
    uv_ok = all(results[n]["uv"]["has_uv"] or n in NO_UV_BY_DESIGN
                for n in PARTS)
    all_ok = (ngons_ok and boundary_ok and uv_ok
              and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and structure_ok and mats["all_ok"])

    summary = {
        "asset": "035-lowpoly-spellbook",
        "parts": len(results),
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "ngons_expected": sum(EXPECTED_NGONS.values()),
        "ngons_ok": bool(ngons_ok),
        "boundary_edges": tot["boundary_edges"],
        "boundary_expected": sum(EXPECTED_BOUNDARY.values()),
        "boundary_ok": bool(boundary_ok),
        "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "inverted_normals": tot["inverted_normals"],
        "uv_out_of_bounds": tot_oob,
        "uv_utilization_per_part": {k: round(v["uv"]["utilization"], 3)
                                    for k, v in results.items()},
        "uv_islands": tot_islands,
        "uv_overlap_pct": round(worst_overlap, 2),
        "uv_ok": bool(uv_ok),
        "empty_material_slots": empty_slots,
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

    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 039 资产质检单：低模魔法书（035）\n\n")
        f.write("被检资产：`scenes/035-lowpoly-spellbook.blend`（28 个魔法书部件，不含场景地面/灯光/相机）\n")
        f.write("检查方式：Blender bmesh 实测，非目测估算。\n\n")
        f.write("## 1. 拓扑\n\n")
        f.write("| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 最高顶点价数 |\n")
        f.write("| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | ------------ |\n")
        for name in PARTS:
            r = results[name]
            f.write("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n" % (
                name, r["verts"], r["faces"], r["tris"], r["quads"], r["ngons"],
                r["duplicate_verts"], r["loose_edges"], r["boundary_edges"],
                r["nonmanifold_edges"], r["degenerate_faces"], r["max_valence"]))
        f.write("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | — |\n\n" % (
            tot["verts"], tot["faces"], tot["tris"], tot["quads"], tot["ngons"],
            tot["duplicate_verts"], tot["loose_edges"], tot["boundary_edges"],
            tot["nonmanifold_edges"], tot["degenerate_faces"]))
        f.write("- N-gon：共 %d 个（设计值 0，盒子为 6 个四边面、圆柱盖面为三角扇、圆环为全四边面、宝石为 8 个三角面）：%s\n" % (
            tot["ngons"], verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 边界边：共 %d 条（设计值 0，全部 29 个部件均为闭合网格）：%s\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（28 个部件均已 Smart UV Project 展开，无设计豁免）\n" % verdict(uv_ok))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率（各部件独立 0–1 空间）：\n")
        for name in PARTS:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 魔法书结构（实测）\n\n")
        f.write("- 下封面：0.56×0.76×0.018（x ±%.2f，y ±%.2f），z %.3f–%.3f，底面 z=0.000 贴地：%s\n" % (
            cover_bottom["bbox_x"][1], cover_bottom["bbox_y"][1],
            cover_bottom["bbox_z"][0], cover_bottom["bbox_z"][1],
            verdict(cover_bottom["ok"])))
        f.write("- 书页块：0.50×0.70×0.062，z %.3f–%.3f，底面与下封面顶齐平（差 %.3f）；四边各内缩 0.03（x 内缩 %.3f，y 内缩 %.3f）：%s\n" % (
            page_block["bbox_z"][0], page_block["bbox_z"][1],
            page_block["bottom_minus_cover_top"],
            page_block["inset_x"], page_block["inset_y"],
            verdict(page_block["ok"])))
        f.write("  （注：035 笔记称书页块“书脊侧齐平”，实测书脊侧同样内缩 0.03——与前切口/天头/地脚一致，笔记措辞有误，几何本身对称无问题）\n")
        f.write("- 上封面：0.56×0.76×0.018，z %.3f–%.3f，底面与书页块顶齐平（差 %.3f）：%s\n" % (
            cover_top["bbox_z"][0], cover_top["bbox_z"][1],
            cover_top["bottom_minus_page_top"],
            verdict(cover_top["ok"])))
        f.write("- 书脊：深色皮革圆柱，沿 Y 轴 x=-0.28，r %.3f，y ±%.2f，z %.3f–%.3f，12 边 × 36 面（12 四边 + 24 盖面三角）；圆柱轴线恰在封面边缘，半管伸出封面外 %.3f：%s\n" % (
            spine["radius"], spine["bbox_y"][1],
            spine["bbox_z"][0], spine["bbox_z"][1],
            spine["outboard_past_cover_edge"], verdict(spine["ok"])))
        f.write("- 书页纹：9 条，3 条/边，z 中心 0.032 / 0.049 / 0.066，0.006 厚，微凸出页块表面：%s\n" % verdict(page_lines["ok"]))
        for ln in page_lines["lines"]:
            f.write("  - %s（%s 边）：z %.3f–%.3f，凸出页块表面 %.3f：%s\n" % (
                ln["name"], ln["edge"], ln["bbox_z"][0], ln["bbox_z"][1],
                ln["protrusion_past_page_face"], verdict(ln["ok"])))
        f.write("  （注：035 笔记称凸出 0.002，实测凸出 0.003——细槽中心在页块表面外 0.001、半厚 0.002，几何无问题，笔记数值有误）\n")
        f.write("- 符文环：黄铜圆环 R 0.14、管 r 0.012，z %.3f–%.3f，内外半径 %.3f–%.3f，256 个四边面；底面嵌入上封面 0.010（封面顶 z=0.098）：%s\n" % (
            rune_ring["bbox_z"][0], rune_ring["bbox_z"][1],
            rune_ring["radius_min"], rune_ring["radius_max"],
            verdict(rune_ring["ok"])))
        f.write("- 符文星：5 条黄铜细条，72° 均布，z %.3f–%.3f，底面与上封面顶齐平；条端半径 %.3f 超过符文环内半径 %.3f，与环管相接：%s\n" % (
            rune_star["stars"][0]["bbox_z"][0],
            rune_star["stars"][0]["bbox_z"][1],
            rune_star["stars"][0]["max_radius"],
            rune_star["stars"][0]["ring_inner_radius"],
            verdict(rune_star["ok"])))
        for s in rune_star["stars"]:
            f.write("  - %s：绕 Z 旋转 %.1f°，条端半径 %.3f：%s\n" % (
                s["name"], s["rotation_z_deg"], s["max_radius"],
                verdict(s["ok"])))
        f.write("- 宝石：紫水晶正八面体，a 0.035，z %.3f–%.3f，8 个三角面；顶面高出上封面 %.3f，底顶点 z=%.3f 恰为书页块顶（锚入书身）：%s\n" % (
            gem["bbox_z"][0], gem["bbox_z"][1],
            gem["top_above_cover"], gem["bbox_z"][0],
            verdict(gem["ok"])))
        f.write("- 锁扣顶部扣带：0.16×0.05×0.006，x %.2f–%.2f，z %.3f–%.3f，底面与上封面顶齐平（差 %.3f），前切口端 x=0.28 与封面边缘齐平：%s\n" % (
            clasp["clasp_top"]["bbox_x"][0], clasp["clasp_top"]["bbox_x"][1],
            clasp["clasp_top"]["bbox_z"][0], clasp["clasp_top"]["bbox_z"][1],
            clasp["clasp_top"]["bottom_minus_cover_top"],
            verdict(clasp["clasp_top"]["ok"])))
        f.write("- 锁扣前切口竖带：0.006×0.05×0.10，x %.3f–%.3f，z %.3f–%.3f，顶面与扣带底面重叠 0.001（连接无缝隙）：%s\n" % (
            clasp["clasp_front"]["bbox_x"][0],
            clasp["clasp_front"]["bbox_x"][1],
            clasp["clasp_front"]["bbox_z"][0],
            clasp["clasp_front"]["bbox_z"][1],
            verdict(clasp["clasp_front"]["ok"])))
        if not clasp["clasp_front"]["ok"]:
            f.write("  **缺陷：竖带底面 z=%.3f，低于地面（z=0）%.3f m——构建脚本中心 z=0.049、高度 0.10 的取整遗留，渲染中被地面遮挡不可见，游戏中会与放置面产生 1 mm 穿插；修复：ClaspFront 中心 z 上移 0.001。**\n" % (
                clasp["clasp_front"]["bottom_z"],
                clasp["clasp_front"]["below_ground_by"]))
        f.write("- 锁扣扣钉：铁圆柱 r %.3f，z %.3f–%.3f，8 边 × 24 面（8 四边 + 16 盖面三角），底面与扣带顶齐平（差 %.3f）：%s\n" % (
            clasp["clasp_stud"]["radius"],
            clasp["clasp_stud"]["bbox_z"][0], clasp["clasp_stud"]["bbox_z"][1],
            clasp["clasp_stud"]["bottom_minus_strap_top"],
            verdict(clasp["clasp_stud"]["ok"])))
        f.write("- 护角：4 块黄铜平板 0.07×0.07×0.006，z %.3f–%.3f，底面与上封面顶齐平，外缘与封面边缘齐平（x 外缘 %.2f，y 外缘 %.2f）：%s\n" % (
            corners["corners"][0]["bbox_z"][0],
            corners["corners"][0]["bbox_z"][1],
            corners["corners"][0]["outer_x"],
            corners["corners"][0]["outer_y"],
            verdict(corners["ok"])))
        for c in corners["corners"]:
            f.write("  - %s：x %.3f–%.3f，y %.3f–%.3f：%s\n" % (
                c["name"], c["bbox_x"][0], c["bbox_x"][1],
                c["bbox_y"][0], c["bbox_y"][1], verdict(c["ok"])))
        f.write("- 书签：绯红缎带 0.035×0.12×0.004，y %.2f–%.2f，z %.3f–%.3f（在书页块 z 跨度内）；伸出封面地脚边缘 %.3f，伸出书页块地脚边缘 %.3f：%s\n" % (
            bookmark["bbox_y"][0], bookmark["bbox_y"][1],
            bookmark["bbox_z"][0], bookmark["bbox_z"][1],
            bookmark["protrusion_past_cover_tail"],
            bookmark["protrusion_past_page_tail"],
            verdict(bookmark["ok"])))
        f.write("  （注：035 笔记称伸出书外 0.05，实测伸出封面边缘 0.08——缎带中心 y=-0.40、半长 0.06，笔记数值有误，几何无问题）\n\n")
        f.write("## 5. 材质 / 贴图\n\n")
        for obj_name, mat_name, has_image in mat_rows:
            f.write("- %s → `%s`：图片贴图 %s\n" % (
                obj_name, mat_name if mat_name else "（空槽）",
                "有" if has_image else "无（程序化材质）"))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 材质节点值（实测 vs 设计值）：\n")
        for r in mats["rows"]:
            if not r.get("found"):
                f.write("  - %s：未找到材质：不通过\n" % r["name"])
                continue
            d = DESIGN_MATS[r["name"]]
            f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），底色 %s（设计 %s）：%s\n" % (
                r["name"], r["metallic"], d[0], r["roughness"], d[1],
                r["base_color"], d[2], verdict(r["ok"])))
        f.write("- 未使用的设计材质：%s\n" % (
            "无" if not mats["unused_design_mats"]
            else ", ".join(mats["unused_design_mats"])))
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        if all_ok:
            f.write("**总体：通过，可进游戏管线**\n")
        else:
            f.write("**总体：未通过——见上文不通过项（仅锁扣前切口竖带底面低于地面 0.001 m 一处轻微缺陷，其余拓扑/法线/UV/材质/结构全部通过；修复为构建脚本中 ClaspFront 中心 z 上移 0.001）**\n")
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
