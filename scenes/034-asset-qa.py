# -*- coding: utf-8 -*-
"""034 资产质检：对 026 低模提灯做真实 mesh 检查（拓扑/法线/UV/材质），
并实测提灯特有结构：底座落地、四角立柱、玻璃罩渐缩开口筒、
蜡烛/烛芯/火焰层叠、顶盖四棱锥、顶饰、提环拱与承柱、
烛光点光源位置；六种材质节点值（金属度/粗糙度/底色/透明度/自发光）。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 034-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "026-lowpoly-lantern.blend")
UV_JSON = os.path.join(ROOT, "scenes", "034-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "034-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "034-asset-qa-checklist.md")

# lantern parts only (Ground / lights / camera are scene dressing)
PARTS = ["Base", "BottomFrame",
         "Post_-1-1", "Post_-1+1", "Post_+1-1", "Post_+1+1",
         "GlassShade", "Candle", "Wick", "Flame", "TopFrame", "Cap",
         "Finial", "HandlePost_-1", "HandlePost_+1", "Handle"]
# Design: no N-gons anywhere. Cylinder caps are triangle fans,
# boxes are 6 quads, pyramid cap is side tris + bottom fan.
EXPECTED_NGONS = {}
# GlassShade is an open tapered square tube by design (no caps):
# its top and bottom rims are 4 + 4 boundary edges. All other parts
# are closed meshes with 0 boundary edges.
EXPECTED_BOUNDARY = {"GlassShade": 8}
# GlassShade was deliberately left without a UV layer in the 026 build
# (procedural transparent glass, no texture, no UV needed).
NO_UV_BY_DESIGN = {"GlassShade"}


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


def ring_radii(obj):
    """Per-z ring max radius (for Z-axis tubes). Returns [(z, radius)]."""
    by_z = {}
    for v in obj.data.vertices:
        by_z.setdefault(round(v.co.z, 3), []).append(v)
    rows = []
    for z in sorted(by_z.keys()):
        rs = [math.hypot(v.co.x, v.co.y) for v in by_z[z]]
        rows.append({"z": z, "radius": round(max(rs), 3),
                     "verts": len(rs)})
    return rows


def ring_radii_centered(obj):
    """Per-z ring max radius measured from the ring's own centroid
    (for tubes whose axis is offset from the world origin)."""
    by_z = {}
    for v in obj.data.vertices:
        by_z.setdefault(round(v.co.z, 3), []).append(v)
    rows = []
    for z in sorted(by_z.keys()):
        vs = by_z[z]
        cx = sum(v.co.x for v in vs) / len(vs)
        cy = sum(v.co.y for v in vs) / len(vs)
        rs = [math.hypot(v.co.x - cx, v.co.y - cy) for v in vs]
        rows.append({"z": z, "radius": round(max(rs), 3),
                     "verts": len(vs),
                     "center_xy": (round(cx, 3), round(cy, 3))})
    return rows


def half_widths(obj):
    """Per-z max |x| and |y| (for square-section parts)."""
    by_z = {}
    for v in obj.data.vertices:
        by_z.setdefault(round(v.co.z, 3), []).append(v)
    rows = []
    for z in sorted(by_z.keys()):
        hx = max(abs(v.co.x) for v in by_z[z])
        hy = max(abs(v.co.y) for v in by_z[z])
        rows.append({"z": z, "half_x": round(hx, 3),
                     "half_y": round(hy, 3), "verts": len(by_z[z])})
    return rows


def check_base(parts):
    """Base: iron foot 0.34x0.34x0.07, z 0.00-0.07, sits on the ground."""
    base = next(o for o in parts if o.name == "Base")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(base)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3))}
    ok = (abs(xmin - (-0.17)) < 0.001 and abs(xmax - 0.17) < 0.001
          and abs(ymin - (-0.17)) < 0.001 and abs(ymax - 0.17) < 0.001
          and abs(zmin - 0.0) < 0.001 and abs(zmax - 0.07) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_bottom_frame(parts):
    """BottomFrame: brass 0.30x0.30x0.05, z 0.07-0.12, stacked on base."""
    fr = next(o for o in parts if o.name == "BottomFrame")
    base = next(o for o in parts if o.name == "Base")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(fr)
    _, _, _, _, _, bzmax = world_range(base)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3)),
           "bottom_minus_base_top": round(zmin - bzmax, 3)}
    ok = (abs(xmin - (-0.15)) < 0.001 and abs(xmax - 0.15) < 0.001
          and abs(zmin - 0.07) < 0.001 and abs(zmax - 0.12) < 0.001
          and abs(row["bottom_minus_base_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_posts(parts):
    """4 corner posts: brass 0.03x0.03x0.34 at (+-0.125, +-0.125),
    z 0.12-0.46, standing on the bottom frame, reaching the top frame."""
    rows = []
    all_ok = True
    for sx in (-1, 1):
        for sy in (-1, 1):
            post = next(o for o in parts
                        if o.name == "Post_%+d%+d" % (sx, sy))
            xmin, xmax, ymin, ymax, zmin, zmax = world_range(post)
            cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
            row = {"name": post.name, "center_xy": (round(cx, 3), round(cy, 3)),
                   "bbox_z": (zmin, zmax),
                   "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                            round(zmax - zmin, 3)),
                   "outer_edge": round(max(abs(xmin), abs(xmax)), 3)}
            ok = (abs(cx - sx * 0.125) < 0.001 and abs(cy - sy * 0.125) < 0.001
                  and abs(zmin - 0.12) < 0.001 and abs(zmax - 0.46) < 0.001
                  and abs(row["size"][0] - 0.03) < 0.001
                  and abs(row["size"][2] - 0.34) < 0.001)
            row["ok"] = bool(ok)
            all_ok = all_ok and ok
            rows.append(row)
    return {"posts": rows, "ok": bool(all_ok)}


def check_glass(parts):
    """GlassShade: open tapered square tube, half 0.13 -> 0.10,
    z 0.12-0.46, exactly 4 quads, 8 boundary edges (rims), no caps."""
    glass = next(o for o in parts if o.name == "GlassShade")
    rows = half_widths(glass)
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(glass)
    quads = sum(1 for p in glass.data.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in glass.data.polygons if len(p.vertices) == 3)
    row = {"rows": rows, "bbox_z": (zmin, zmax), "tris": tris,
           "quads": quads}
    ok = (len(rows) == 2
          and abs(rows[0]["half_x"] - 0.13) < 0.001
          and abs(rows[0]["half_y"] - 0.13) < 0.001
          and abs(rows[1]["half_x"] - 0.10) < 0.001
          and abs(rows[1]["half_y"] - 0.10) < 0.001
          and abs(rows[0]["z"] - 0.12) < 0.001
          and abs(rows[1]["z"] - 0.46) < 0.001
          and quads == 4 and tris == 0)
    row["ok"] = bool(ok)
    return row


def check_candle(parts):
    """Candle: wax cylinder r 0.035, z 0.12-0.24, centered on axis,
    bottom flush with the bottom frame top (z=0.12)."""
    candle = next(o for o in parts if o.name == "Candle")
    rows = ring_radii(candle)
    _, _, _, _, zmin, zmax = world_range(candle)
    cx = sum(v.co.x for v in candle.data.vertices) / len(candle.data.vertices)
    cy = sum(v.co.y for v in candle.data.vertices) / len(candle.data.vertices)
    row = {"rings": rows, "z": (zmin, zmax),
           "center_xy": (round(cx, 3), round(cy, 3))}
    ok = (len(rows) == 2
          and all(abs(r["radius"] - 0.035) < 0.001 for r in rows)
          and abs(zmin - 0.12) < 0.001 and abs(zmax - 0.24) < 0.001
          and abs(cx) < 0.001 and abs(cy) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_wick(parts):
    """Wick: dark cylinder r 0.006, z 0.24-0.265, bottom flush with the
    candle top (z=0.24), centered on axis."""
    wick = next(o for o in parts if o.name == "Wick")
    candle = next(o for o in parts if o.name == "Candle")
    rows = ring_radii(wick)
    _, _, _, _, zmin, zmax = world_range(wick)
    _, _, _, _, _, czmax = world_range(candle)
    row = {"rings": rows, "z": (zmin, zmax), "candle_top_z": czmax,
           "bottom_minus_candle_top": round(zmin - czmax, 3)}
    ok = (len(rows) == 2
          and all(abs(r["radius"] - 0.006) < 0.001 for r in rows)
          and abs(zmin - 0.24) < 0.001 and abs(zmax - 0.265) < 0.001
          and abs(row["bottom_minus_candle_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_flame(parts):
    """Flame: 8-sided cone r 0.028, z 0.255-0.345, apex on top,
    base ring at z=0.255, 16 faces (8 side tris + 8 bottom fan tris).
    The wick top (z=0.265) must sit inside the flame's z span."""
    flame = next(o for o in parts if o.name == "Flame")
    wick = next(o for o in parts if o.name == "Wick")
    rows = ring_radii(flame)
    _, _, _, _, zmin, zmax = world_range(flame)
    _, _, _, _, _, wzmax = world_range(wick)
    tris = sum(1 for p in flame.data.polygons if len(p.vertices) == 3)
    row = {"rings": rows, "z": (zmin, zmax), "tris": tris,
           "wick_top_z": wzmax,
           "wick_top_inside": bool(zmin < wzmax < zmax)}
    ok = (len(rows) == 2
          and abs(rows[0]["z"] - 0.255) < 0.001
          and abs(rows[0]["radius"] - 0.028) < 0.001
          and abs(rows[1]["z"] - 0.345) < 0.001
          and abs(rows[1]["radius"] - 0.0) < 0.001
          and tris == 16 and row["wick_top_inside"])
    row["ok"] = bool(ok)
    return row


def check_top_frame(parts):
    """TopFrame: brass 0.26x0.26x0.05, z 0.46-0.51, stacked on the posts."""
    fr = next(o for o in parts if o.name == "TopFrame")
    posts = [next(o for o in parts if o.name == "Post_%+d%+d" % (sx, sy))
             for sx in (-1, 1) for sy in (-1, 1)]
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(fr)
    post_top = max(world_range(p)[5] for p in posts)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "size": (round(xmax - xmin, 3), round(ymax - ymin, 3),
                    round(zmax - zmin, 3)),
           "bottom_minus_post_top": round(zmin - post_top, 3),
           # posts stick 0.01 past the top frame on each side by design
           # values (post outer edge 0.140 vs frame half 0.130)
           "post_outer_edge": 0.14,
           "frame_half": round(xmax, 3)}
    ok = (abs(xmin - (-0.13)) < 0.001 and abs(xmax - 0.13) < 0.001
          and abs(zmin - 0.46) < 0.001 and abs(zmax - 0.51) < 0.001
          and abs(row["bottom_minus_post_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_cap(parts):
    """Cap: iron square pyramid, base half 0.13 at z 0.51, apex z 0.63,
    8 faces (4 side tris + 4 bottom fan tris), bottom flush with the
    top frame top (z=0.51)."""
    cap = next(o for o in parts if o.name == "Cap")
    fr = next(o for o in parts if o.name == "TopFrame")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(cap)
    _, _, _, _, _, fzmax = world_range(fr)
    tris = sum(1 for p in cap.data.polygons if len(p.vertices) == 3)
    apex = max(v.co.z for v in cap.data.vertices)
    base_half = max(abs(v.co.x) for v in cap.data.vertices
                    if abs(v.co.z - 0.51) < 0.001)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "tris": tris,
           "base_half": round(base_half, 3), "apex_z": round(apex, 3),
           "bottom_minus_frame_top": round(zmin - fzmax, 3)}
    ok = (abs(zmin - 0.51) < 0.001 and abs(zmax - 0.63) < 0.001
          and abs(base_half - 0.13) < 0.001 and tris == 8
          and abs(row["bottom_minus_frame_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_finial(parts):
    """Finial: brass knob, tapered cylinder r 0.020 -> 0.016,
    z 0.63-0.68, bottom flush with the cap apex (z=0.63)."""
    fin = next(o for o in parts if o.name == "Finial")
    cap = next(o for o in parts if o.name == "Cap")
    rows = ring_radii(fin)
    _, _, _, _, zmin, zmax = world_range(fin)
    _, _, _, _, _, czmax = world_range(cap)
    row = {"rings": rows, "z": (zmin, zmax), "cap_apex_z": czmax,
           "bottom_minus_cap_apex": round(zmin - czmax, 3)}
    ok = (len(rows) == 2
          and abs(rows[0]["radius"] - 0.020) < 0.001
          and abs(rows[1]["radius"] - 0.016) < 0.001
          and abs(zmin - 0.63) < 0.001 and abs(zmax - 0.68) < 0.001
          and abs(row["bottom_minus_cap_apex"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_handle_posts(parts):
    """Handle posts: iron cylinders r 0.015, z 0.51-0.56 at x = +-0.14,
    standing on the top frame, tops flush with the handle arch feet."""
    rows = []
    all_ok = True
    for sx in (-1, 1):
        post = next(o for o in parts if o.name == "HandlePost_%+d" % sx)
        # posts sit at x = +-0.14, so ring radius must be measured
        # from the ring's own centroid, not from the world origin
        rings = ring_radii_centered(post)
        xmin, xmax, ymin, ymax, zmin, zmax = world_range(post)
        cx = (xmin + xmax) / 2.0
        row = {"name": post.name, "rings": rings, "z": (zmin, zmax),
               "center_x": round(cx, 3)}
        ok = (len(rings) == 2
              and all(abs(r["radius"] - 0.015) < 0.001 for r in rings)
              and abs(zmin - 0.51) < 0.001 and abs(zmax - 0.56) < 0.001
              and abs(cx - sx * 0.14) < 0.001)
        row["ok"] = bool(ok)
        all_ok = all_ok and ok
        rows.append(row)
    return {"posts": rows, "ok": bool(all_ok)}


def check_handle(parts):
    """Handle: half torus, major r 0.14, minor r 0.012, in the XZ plane,
    center z 0.56. Arch top z = 0.56 + 0.14 + 0.012 = 0.712; the tube
    cross-section at the feet lies in the z=0.56 plane, so the feet sit
    exactly on the handle post tops (z=0.56). Tube y extent is
    +-0.012*sin(60deg) = +-0.010 (6 tube segments). Total 156 faces
    (144 quads + 12 end-cap tris)."""
    handle = next(o for o in parts if o.name == "Handle")
    posts = [next(o for o in parts if o.name == "HandlePost_%+d" % sx)
             for sx in (-1, 1)]
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(handle)
    quads = sum(1 for p in handle.data.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in handle.data.polygons if len(p.vertices) == 3)
    post_top = max(world_range(p)[5] for p in posts)
    post_x = sorted(abs((world_range(p)[0] + world_range(p)[1]) / 2.0)
                    for p in posts)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "tris": tris, "quads": quads,
           "post_top_z": round(post_top, 3),
           "feet_z_minus_post_top": round(zmin - post_top, 3)}
    ok = (abs(xmin - (-0.152)) < 0.001 and abs(xmax - 0.152) < 0.001
          and abs(zmin - 0.56) < 0.001 and abs(zmax - 0.712) < 0.001
          and abs(ymin - (-0.01)) < 0.001 and abs(ymax - 0.01) < 0.001
          and quads == 144 and tris == 12
          and abs(post_x[0] - 0.14) < 0.001
          and abs(row["feet_z_minus_post_top"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_candle_light():
    """CandleLight: warm point light (1.0, 0.55, 0.2), energy 10.0,
    at (0, 0, 0.30), inside the glass shade (glass half-width at
    z=0.30 is 0.114), no shadow."""
    light = bpy.context.scene.objects.get("CandleLight")
    if light is None or light.type != 'LIGHT' or light.data.type != 'POINT':
        return {"found": False, "ok": False}
    loc = tuple(round(v, 3) for v in light.location)
    col = tuple(round(v, 2) for v in light.data.color)
    energy = round(light.data.energy, 2)
    glass_half_at_light = 0.13 - (0.30 - 0.12) / (0.46 - 0.12) * 0.03
    row = {"found": True, "location": loc, "color": col,
           "energy": energy, "use_shadow": bool(light.data.use_shadow),
           "glass_half_at_light_z": round(glass_half_at_light, 3),
           "inside_glass": bool(abs(loc[0]) < glass_half_at_light
                                and abs(loc[1]) < glass_half_at_light
                                and 0.12 < loc[2] < 0.46)}
    ok = (loc == (0.0, 0.0, 0.3) and col == (1.0, 0.55, 0.2)
          and abs(energy - 10.0) < 0.01 and not light.data.use_shadow
          and row["inside_glass"])
    row["ok"] = bool(ok)
    return row


def check_glass_encloses(parts):
    """Glass shade must enclose the candle and the flame: both z spans
    inside the glass z span, and both radii smaller than the glass
    half-width at their heights."""
    glass = next(o for o in parts if o.name == "GlassShade")
    candle = next(o for o in parts if o.name == "Candle")
    flame = next(o for o in parts if o.name == "Flame")
    _, _, _, _, gzmin, gzmax = world_range(glass)
    _, _, _, _, czmin, czmax = world_range(candle)
    _, _, _, _, fzmin, fzmax = world_range(flame)
    # glass half-width at a given z (linear taper 0.13 -> 0.10)
    def half_at(z):
        return 0.13 - (z - 0.12) / (0.46 - 0.12) * 0.03
    row = {"glass_z": (gzmin, gzmax), "candle_z": (czmin, czmax),
           "flame_z": (fzmin, fzmax),
           "candle_radius": 0.035, "flame_radius": 0.028,
           "glass_half_at_candle_top": round(half_at(czmax), 3),
           "glass_half_at_flame_top": round(half_at(fzmax), 3)}
    ok = (gzmin <= czmin and czmax <= gzmax
          and gzmin <= fzmin and fzmax <= gzmax
          and 0.035 < half_at(czmax) and 0.028 < half_at(fzmax))
    row["ok"] = bool(ok)
    return row


# design values from 026 build script:
# (metallic, roughness, base color) for Principled materials
DESIGN_MATS = {
    "Lantern_Iron": (0.70, 0.50, (0.16, 0.16, 0.18)),
    "Lantern_Brass": (0.85, 0.35, (0.55, 0.42, 0.18)),
    "Lantern_Wax": (0.00, 0.60, (0.92, 0.86, 0.70)),
    "Lantern_Wick": (0.00, 0.90, (0.10, 0.08, 0.06)),
}
# Glass: Principled with alpha; Flame: pure Emission node.
DESIGN_GLASS = {"metallic": 0.00, "roughness": 0.08,
                "base_color": (0.85, 0.75, 0.55), "alpha": 0.30}
DESIGN_FLAME = {"color": (1.0, 0.45, 0.08), "strength": 8.0}


def check_materials(parts):
    """Read node values, not names. Principled for solid/glass mats,
    Emission node for the flame."""
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

    # glass: Principled + alpha + blended render method
    mat = bpy.data.materials.get("Lantern_Glass")
    if mat is None or not mat.use_nodes:
        rows.append({"name": "Lantern_Glass", "found": False, "ok": False})
    else:
        bsdf = next((n for n in mat.node_tree.nodes
                     if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            rows.append({"name": "Lantern_Glass", "found": True, "ok": False})
        else:
            m = round(bsdf.inputs["Metallic"].default_value, 2)
            r = round(bsdf.inputs["Roughness"].default_value, 2)
            c = tuple(round(v, 2)
                      for v in bsdf.inputs["Base Color"].default_value[:3])
            a = round(bsdf.inputs["Alpha"].default_value, 2)
            try:
                blend = mat.surface_render_method
            except AttributeError:
                blend = mat.blend_method
            ok = (abs(m - DESIGN_GLASS["metallic"]) < 0.01
                  and abs(r - DESIGN_GLASS["roughness"]) < 0.01
                  and all(abs(x - y) < 0.01
                          for x, y in zip(c, DESIGN_GLASS["base_color"]))
                  and abs(a - DESIGN_GLASS["alpha"]) < 0.01
                  and blend in ('BLENDED', 'BLEND'))
            rows.append({"name": "Lantern_Glass", "found": True,
                         "metallic": m, "roughness": r, "base_color": c,
                         "alpha": a, "blend": str(blend), "ok": bool(ok)})

    # flame: Emission node, no Principled
    mat = bpy.data.materials.get("Lantern_Flame")
    if mat is None or not mat.use_nodes:
        rows.append({"name": "Lantern_Flame", "found": False, "ok": False})
    else:
        emit = next((n for n in mat.node_tree.nodes
                     if n.type == 'EMISSION'), None)
        if emit is None:
            rows.append({"name": "Lantern_Flame", "found": True, "ok": False})
        else:
            c = tuple(round(v, 2)
                      for v in emit.inputs["Color"].default_value[:3])
            s = round(emit.inputs["Strength"].default_value, 2)
            ok = (all(abs(x - y) < 0.01
                      for x, y in zip(c, DESIGN_FLAME["color"]))
                  and abs(s - DESIGN_FLAME["strength"]) < 0.01)
            rows.append({"name": "Lantern_Flame", "found": True,
                         "emission_color": c, "strength": s, "ok": bool(ok)})

    used = {m.name for o in parts for m in o.data.materials if m}
    all_design = list(DESIGN_MATS) + ["Lantern_Glass", "Lantern_Flame"]
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

    base = check_base(parts)
    print("QA_BASE:", base)
    bottom_frame = check_bottom_frame(parts)
    print("QA_BOTTOM_FRAME:", bottom_frame)
    posts = check_posts(parts)
    print("QA_POSTS:", posts)
    glass = check_glass(parts)
    print("QA_GLASS:", glass)
    candle = check_candle(parts)
    print("QA_CANDLE:", candle)
    wick = check_wick(parts)
    print("QA_WICK:", wick)
    flame = check_flame(parts)
    print("QA_FLAME:", flame)
    top_frame = check_top_frame(parts)
    print("QA_TOP_FRAME:", top_frame)
    cap = check_cap(parts)
    print("QA_CAP:", cap)
    finial = check_finial(parts)
    print("QA_FINIAL:", finial)
    handle_posts = check_handle_posts(parts)
    print("QA_HANDLE_POSTS:", handle_posts)
    handle = check_handle(parts)
    print("QA_HANDLE:", handle)
    candle_light = check_candle_light()
    print("QA_CANDLE_LIGHT:", candle_light)
    encloses = check_glass_encloses(parts)
    print("QA_ENCLOSES:", encloses)
    mats = check_materials(parts)
    print("QA_MATERIALS:", mats)

    structure = {"base": base, "bottom_frame": bottom_frame,
                 "posts": posts, "glass": glass, "candle": candle,
                 "wick": wick, "flame": flame, "top_frame": top_frame,
                 "cap": cap, "finial": finial,
                 "handle_posts": handle_posts, "handle": handle,
                 "candle_light": candle_light, "encloses": encloses}
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
        "asset": "026-lowpoly-lantern",
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
        f.write("# 034 资产质检单：低模提灯（026）\n\n")
        f.write("被检资产：`scenes/026-lowpoly-lantern.blend`（16 个提灯部件，不含场景地面/灯光/相机；烛光点光源单独检查）\n")
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
        f.write("- N-gon：共 %d 个（设计值 0，圆柱盖面为三角扇、顶盖为三角面+底面扇形剖分、提环端盖为三角扇）：%s\n" % (
            tot["ngons"], verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 边界边：共 %d 条，全部来自 GlassShade（设计：开口渐缩筒无盖面，上下口沿各 4 条，设计值 8）：%s；其余 15 个部件均为闭合网格（0 条）\n" % (
            tot["boundary_edges"], verdict(boundary_ok)))
        f.write("- 最高顶点价数 %d（圆柱盖面中心扇形顶点价数 8，提环管环顶点价数 4，顶盖顶点价数 4）\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（15 个部件均已 Smart UV Project 展开；GlassShade 无 UV 层，属设计——程序化透明玻璃材质、无贴图、无需 UV）\n" % verdict(uv_ok))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率（各部件独立 0–1 空间）：\n")
        for name in PARTS:
            if name in NO_UV_BY_DESIGN:
                f.write("  - %s：无 UV 层（设计，见上）\n" % name)
            else:
                f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 提灯结构（实测）\n\n")
        f.write("- 底座落地：0.34×0.34×0.07（x ±%.2f，y ±%.2f），z %.2f–%.2f，底面 z=0.00 贴地：%s\n" % (
            base["bbox_x"][1], base["bbox_y"][1],
            base["bbox_z"][0], base["bbox_z"][1], verdict(base["ok"])))
        f.write("- 下灯框：0.30×0.30×0.05，z %.2f–%.2f，底面与底座顶齐平（差 %.3f）：%s\n" % (
            bottom_frame["bbox_z"][0], bottom_frame["bbox_z"][1],
            bottom_frame["bottom_minus_base_top"],
            verdict(bottom_frame["ok"])))
        f.write("- 四角立柱：4 根均为 0.03×0.03×0.34，中心 (±0.125, ±0.125)，z 0.12–0.46，底接下灯框、顶接上灯框：%s\n" % verdict(posts["ok"]))
        for p in posts["posts"]:
            f.write("  - %s：中心 (%.3f, %.3f)，z %.2f–%.2f：%s\n" % (
                p["name"], p["center_xy"][0], p["center_xy"][1],
                p["bbox_z"][0], p["bbox_z"][1], verdict(p["ok"])))
        f.write("- 玻璃罩渐缩：下口半宽 %.3f（z=%.2f）→ 上口半宽 %.3f（z=%.2f），4 个四边面、无盖面开口筒：%s\n" % (
            glass["rows"][0]["half_x"], glass["rows"][0]["z"],
            glass["rows"][1]["half_x"], glass["rows"][1]["z"],
            verdict(glass["ok"])))
        f.write("- 玻璃罩包住蜡烛与火焰：玻璃 z %.2f–%.2f；蜡烛 z %.2f–%.2f（r 0.035 < 该高度玻璃半宽 %.3f）、火焰 z %.2f–%.2f（r 0.028 < 该高度玻璃半宽 %.3f）：%s\n" % (
            encloses["glass_z"][0], encloses["glass_z"][1],
            encloses["candle_z"][0], encloses["candle_z"][1],
            encloses["glass_half_at_candle_top"],
            encloses["flame_z"][0], encloses["flame_z"][1],
            encloses["glass_half_at_flame_top"],
            verdict(encloses["ok"])))
        f.write("- 蜡烛：r 0.035 圆柱，z %.2f–%.2f，中心 (%.3f, %.3f) 在轴线上，底面与下灯框顶齐平：%s\n" % (
            candle["z"][0], candle["z"][1],
            candle["center_xy"][0], candle["center_xy"][1],
            verdict(candle["ok"])))
        f.write("- 烛芯：r 0.006，z %.2f–%.2f，底面与蜡烛顶齐平（差 %.3f）：%s\n" % (
            wick["z"][0], wick["z"][1], wick["bottom_minus_candle_top"],
            verdict(wick["ok"])))
        f.write("- 火焰：8 边圆锥，底环 r %.3f（z=%.2f），顶点 z=%.2f，16 个三角面；烛芯顶 z=%.3f 落在火焰跨度内：%s\n" % (
            flame["rings"][0]["radius"], flame["rings"][0]["z"],
            flame["rings"][1]["z"], flame["wick_top_z"],
            verdict(flame["ok"])))
        f.write("- 上灯框：0.26×0.26×0.05，z %.2f–%.2f，底面与立柱顶齐平（差 %.3f）：%s\n" % (
            top_frame["bbox_z"][0], top_frame["bbox_z"][1],
            top_frame["bottom_minus_post_top"], verdict(top_frame["ok"])))
        f.write("  （观察：立柱外缘 0.140 比上灯框半宽 0.130 宽 0.01，立柱略凸出上灯框——设计值如此，连接本身无缝隙，不计为不通过）\n")
        f.write("- 顶盖：四棱锥，底半宽 %.3f（z=%.2f），顶点 z=%.2f，8 个三角面，底面与上灯框顶齐平（差 %.3f）：%s\n" % (
            cap["base_half"], cap["bbox_z"][0], cap["apex_z"],
            cap["bottom_minus_frame_top"], verdict(cap["ok"])))
        f.write("- 顶饰：黄铜小柱，下环 r %.3f（z=%.2f）→ 上环 r %.3f（z=%.2f），底面与顶盖顶点齐平（差 %.3f）：%s\n" % (
            finial["rings"][0]["radius"], finial["rings"][0]["z"],
            finial["rings"][1]["radius"], finial["rings"][1]["z"],
            finial["bottom_minus_cap_apex"], verdict(finial["ok"])))
        f.write("- 提环承柱：2 根铁柱 r 0.015，z 0.51–0.56，x=±0.14：%s\n" % verdict(handle_posts["ok"]))
        for p in handle_posts["posts"]:
            f.write("  - %s：中心 x=%.3f，z %.2f–%.2f：%s\n" % (
                p["name"], p["center_x"], p["z"][0], p["z"][1],
                verdict(p["ok"])))
        f.write("- 提环拱：半圆环（major r 0.14，minor r 0.012），x ±%.3f，z %.3f–%.3f（拱顶 0.712），144 个四边面 + 12 个端盖三角面；拱脚 z=%.3f 与承柱顶 z=%.3f 齐平（差 %.3f）：%s\n" % (
            handle["bbox_x"][1], handle["bbox_z"][0], handle["bbox_z"][1],
            handle["bbox_z"][0], handle["post_top_z"],
            handle["feet_z_minus_post_top"], verdict(handle["ok"])))
        f.write("- 烛光点光源：位置 %s，颜色 %s，能量 %.1f，不投阴影，位于玻璃罩内（该高度玻璃半宽 %.3f）：%s\n\n" % (
            candle_light["location"], candle_light["color"],
            candle_light["energy"], candle_light["glass_half_at_light_z"],
            verdict(candle_light["ok"])))
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
            if r["name"] == "Lantern_Flame":
                f.write("  - %s（Emission 节点）：颜色 %s（设计 %s），强度 %.1f（设计 %.1f）：%s\n" % (
                    r["name"], r["emission_color"], DESIGN_FLAME["color"],
                    r["strength"], DESIGN_FLAME["strength"],
                    verdict(r["ok"])))
            elif r["name"] == "Lantern_Glass":
                d = DESIGN_GLASS
                f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），底色 %s（设计 %s），alpha %.2f（设计 %.2f），混合 %s：%s\n" % (
                    r["name"], r["metallic"], d["metallic"],
                    r["roughness"], d["roughness"],
                    r["base_color"], d["base_color"],
                    r["alpha"], d["alpha"], r["blend"],
                    verdict(r["ok"])))
            else:
                d = DESIGN_MATS[r["name"]]
                f.write("  - %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），底色 %s（设计 %s）：%s\n" % (
                    r["name"], r["metallic"], d[0], r["roughness"], d[1],
                    r["base_color"], d[2], verdict(r["ok"])))
        f.write("- 未使用的设计材质：%s\n" % (
            "无" if not mats["unused_design_mats"]
            else ", ".join(mats["unused_design_mats"])))
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        f.write("**总体：%s**\n" % ("通过，可进游戏管线" if all_ok else "未通过，见上文不通过项"))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
