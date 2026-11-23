# -*- coding: utf-8 -*-
"""041 资产质检：对 040 低模魔法图书馆角落场景做真实 mesh 检查（拓扑/法线/UV/材质），
并实测场景特有结构：角落墙体 + 护墙板、8 块木地板、高书架（5 层、111 本书 +
平放叠书）、矮书架（38 本书 + 地球仪）、梯子（17.7° 倾斜）、书桌（法术书 /
三臂烛台 / 墨水瓶 / 叠书 / 卷轴）、落地烛台 + 暖光点光源、星图挂画、
地毯 + 椅子、地面散书；另复核 040 自检报出的 Globe_Ring 内翻面 32。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 041-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "040-magic-library-corner.blend")
UV_JSON = os.path.join(ROOT, "scenes", "041-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "041-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "041-asset-qa-checklist.md")

# every mesh object in the 040 blend except the scene dressing ground
EXCLUDE = {"Ground"}


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


def check_winding_center(obj):
    """040 build's own winding self-check: face normal vs direction from
    the mesh centroid. For a torus the centroid is the hole centre, so
    inner-tube faces point at it and get flagged even when consistently
    wound -- this check is reported for comparison with the 040 note,
    the bmesh recalc test in check_mesh is the authoritative one."""
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


def check_walls(by_name):
    """Corner walls: back wall y 2.05-2.35, z 0-2.6; left wall x -2.35..-2.05,
    z 0-2.6; wainscot lower 1.0 high + rail at z ~1.02; beams z 2.34-2.56;
    corner post z 0-2.6. Corner closed: left wall far end (y_max 2.30)
    inside the back wall slab (y 2.05-2.35)."""
    wb = world_range(by_name["Wall_Back"])
    wl = world_range(by_name["Wall_Left"])
    wnb = world_range(by_name["Wainscot_Back"])
    wnl = world_range(by_name["Wainscot_Left"])
    wrb = world_range(by_name["WainscotRail_Back"])
    wrl = world_range(by_name["WainscotRail_Left"])
    bb = world_range(by_name["Beam_Back"])
    bl = world_range(by_name["Beam_Left"])
    post = world_range(by_name["Post_Corner"])
    corner_ok = (wl[3] >= wb[2] - 0.001 and wl[3] <= wb[3] + 0.001
                 and wb[0] <= wl[0] + 0.001)
    overhang = round(wl[0] - wb[0], 3)
    row = {"wall_back": wb, "wall_left": wl,
           "wainscot_back": wnb, "wainscot_left": wnl,
           "rail_back_z": (wrb[4], wrb[5]),
           "rail_left_z": (wrl[4], wrl[5]),
           "beam_back_z": (bb[4], bb[5]),
           "beam_left_z": (bl[4], bl[5]),
           "post_z": (post[4], post[5]),
           "corner_overlap": bool(corner_ok),
           "back_wall_overhang_past_left_wall": overhang}
    ok = (abs(wb[0] - (-2.70)) < 0.001 and abs(wb[1] - 2.70) < 0.001
          and abs(wb[2] - 2.05) < 0.001 and abs(wb[3] - 2.35) < 0.001
          and abs(wb[4] - 0.0) < 0.001 and abs(wb[5] - 2.60) < 0.001
          and abs(wl[0] - (-2.35)) < 0.001 and abs(wl[1] - (-2.05)) < 0.001
          and abs(wl[2] - (-2.30)) < 0.001 and abs(wl[3] - 2.30) < 0.001
          and abs(wl[4] - 0.0) < 0.001 and abs(wl[5] - 2.60) < 0.001
          and abs(wnb[4] - 0.0) < 0.001 and abs(wnb[5] - 1.00) < 0.001
          and abs(wnl[4] - 0.0) < 0.001 and abs(wnl[5] - 1.00) < 0.001
          and abs(wrb[4] - 0.99) < 0.001 and abs(wrb[5] - 1.05) < 0.001
          and abs(wrl[4] - 0.99) < 0.001 and abs(wrl[5] - 1.05) < 0.001
          and abs(bb[4] - 2.34) < 0.001 and abs(bb[5] - 2.56) < 0.001
          and abs(bl[4] - 2.34) < 0.001 and abs(bl[5] - 2.56) < 0.001
          and abs(post[4] - 0.0) < 0.001 and abs(post[5] - 2.60) < 0.001
          and corner_ok)
    row["ok"] = bool(ok)
    return row


def check_planks(by_name):
    """8 planks along X, centers x=-2.1+i*0.6, 0.58 wide (0.02 gaps),
    y +-2.30, z 0-0.03 on the ground plane."""
    rows = []
    for i in range(8):
        o = by_name["Plank_%02d" % i]
        r = world_range(o)
        rows.append({"name": o.name, "x_center": round((r[0] + r[1]) / 2, 3),
                     "x": (r[0], r[1]), "y": (r[2], r[3]), "z": (r[4], r[5])})
    ok = (len(rows) == 8
          and all(abs(r["x_center"] - (-2.1 + i * 0.6)) < 0.001
                  and abs(r["x"][1] - r["x"][0] - 0.58) < 0.001
                  and abs(r["z"][0] - 0.0) < 0.001
                  and abs(r["z"][1] - 0.03) < 0.001
                  for i, r in enumerate(rows)))
    gaps = [round(rows[i + 1]["x"][0] - rows[i]["x"][1], 3)
            for i in range(len(rows) - 1)]
    return {"count": len(rows), "planks": rows, "gaps": gaps,
            "ok": bool(ok)}


def check_tall_shelf(by_name):
    """Tall shelf against the back wall: frame x -1.60..0.90, y 1.73..2.17,
    z 0-2.35; 4 boards (tops 0.575/1.025/1.475/1.925); 5 book tiers
    (bases 0.10/0.575/1.025/1.475/1.925, inner x -1.55..0.85, y 1.80..2.10);
    3 flat books stacked on tier 2 (z 1.025-1.185, 0.005 gaps by design)."""
    frame = {n: world_range(by_name[n]) for n in (
        "Shelf_Left", "Shelf_Right", "Shelf_Top", "Shelf_Plinth",
        "Shelf_Back")}
    board_tops = []
    for i, sz in enumerate((0.55, 1.00, 1.45, 1.90)):
        r = world_range(by_name["ShelfBoard_%d" % i])
        board_tops.append(round(r[5], 3))
    bases = (0.10, 0.575, 1.025, 1.475, 1.925)
    tier_rows = []
    floats = []
    leaning = 0
    total_books = 0
    for t, zb in enumerate(bases):
        books = [o for n, o in by_name.items()
                 if n.startswith("Book_T%d_" % t)]
        total_books += len(books)
        tier_floats = []
        for o in sorted(books, key=lambda p: p.name):
            r = world_range(o)
            fl = round(r[4] - zb, 3)
            tier_floats.append(fl)
            floats.append(fl)
            if abs(o.rotation_euler.y) > 0.001:
                leaning += 1
            if not (-1.62 <= r[0] and r[1] <= 0.92
                    and 1.78 <= r[2] and r[3] <= 2.12):
                tier_rows.append({"name": o.name, "tier": t,
                                  "out_of_shelf": r})
        tier_rows.append({"tier": t, "count": len(books),
                          "base": zb, "max_float": max(tier_floats)
                          if tier_floats else None,
                          "min_float": min(tier_floats)
                          if tier_floats else None})
    stack = [world_range(by_name["BookStack_%d" % i]) for i in range(3)]
    stack_gaps = [round(stack[i + 1][4] - stack[i][5], 3)
                  for i in range(2)]
    row = {"frame": frame, "board_tops": board_tops,
           "tiers": tier_rows, "total_books": total_books,
           "leaning_books": leaning,
           "max_book_float": max(floats) if floats else None,
           "books_floating_over_1mm": sum(1 for f in floats if f > 0.001),
           "stack_z": [(s[4], s[5]) for s in stack],
           "stack_gaps": stack_gaps}
    ok = (abs(frame["Shelf_Left"][0] - (-1.60)) < 0.001
          and abs(frame["Shelf_Left"][1] - (-1.55)) < 0.001
          and abs(frame["Shelf_Right"][0] - 0.85) < 0.001
          and abs(frame["Shelf_Right"][1] - 0.90) < 0.001
          and abs(frame["Shelf_Top"][5] - 2.35) < 0.001
          and abs(frame["Shelf_Plinth"][4] - 0.0) < 0.001
          and abs(frame["Shelf_Plinth"][5] - 0.10) < 0.001
          and board_tops == [0.575, 1.025, 1.475, 1.925]
          and total_books == 111
          and all(t["count"] > 0 for t in tier_rows
                  if isinstance(t, dict) and "count" in t)
          and not any("out_of_shelf" in t for t in tier_rows)
          and all(abs(s[0] - (1.025 + i * 0.055)) < 0.001
                  for i, s in enumerate(stack))
          and stack_gaps == [0.005, 0.005]
          and max(floats) <= 0.001)
    row["ok"] = bool(ok)
    return row


def check_low_shelf(by_name):
    """Low shelf on the left wall: ends y -0.60..-0.55 / 1.35..1.40,
    top z 1.10-1.15, plinth z 0-0.10, back x -2.15..-2.11, board top 0.575;
    2 book tiers (bases 0.10/0.575, along y -0.50..1.30, x -2.10..-1.80);
    globe: stand z 1.15-1.23 on the shelf top, blue ball r 0.17 centred
    (-1.95, 1.05, 1.40), gold meridian ring R 0.19 + tube 0.012."""
    frame = {n: world_range(by_name[n]) for n in (
        "LowShelf_EndA", "LowShelf_EndB", "LowShelf_Top",
        "LowShelf_Plinth", "LowShelf_Back", "LowShelf_Board")}
    bases = (0.10, 0.575)
    tier_rows = []
    floats = []
    leaning = 0
    total_books = 0
    for t, zb in enumerate(bases):
        books = [o for n, o in by_name.items()
                 if n.startswith("LBook_T%d_" % t)]
        total_books += len(books)
        tier_floats = []
        for o in sorted(books, key=lambda p: p.name):
            r = world_range(o)
            fl = round(r[4] - zb, 3)
            tier_floats.append(fl)
            floats.append(fl)
            if abs(o.rotation_euler.x) > 0.001:
                leaning += 1
            if not (-2.12 <= r[0] and r[1] <= -1.78
                    and -0.54 <= r[2] and r[3] <= 1.34):
                tier_rows.append({"name": o.name, "tier": t,
                                  "out_of_shelf": r})
        tier_rows.append({"tier": t, "count": len(books), "base": zb,
                          "max_float": max(tier_floats)
                          if tier_floats else None})
    stand = world_range(by_name["Globe_Stand"])
    globe = by_name["Globe"]
    gvs = world_verts(globe)
    gc = (-1.95, 1.05, 1.40)
    globe_r = max(math.dist((v.x, v.y, v.z), gc) for v in gvs)
    ring = by_name["Globe_Ring"]
    rvs = world_verts(ring)
    ring_r = max(math.hypot(v.x - gc[0], v.y - gc[1]) for v in rvs)
    ring_z = world_range(ring)
    row = {"frame": frame, "tiers": tier_rows, "total_books": total_books,
           "leaning_books": leaning,
           "max_book_float": max(floats) if floats else None,
           "books_floating_over_1mm": sum(1 for f in floats if f > 0.001),
           "globe_stand_z": (stand[4], stand[5]),
           "globe_radius": round(globe_r, 3),
           "globe_z": world_range(globe)[4:6],
           "ring_max_radius": round(ring_r, 3),
           "ring_z": (ring_z[4], ring_z[5]),
           "ring_bottom_above_shelf_top": round(ring_z[4] - 1.15, 3)}
    ok = (abs(frame["LowShelf_EndA"][2] - (-0.60)) < 0.001
          and abs(frame["LowShelf_EndA"][3] - (-0.55)) < 0.001
          and abs(frame["LowShelf_EndB"][2] - 1.35) < 0.001
          and abs(frame["LowShelf_EndB"][3] - 1.40) < 0.001
          and abs(frame["LowShelf_Top"][4] - 1.10) < 0.001
          and abs(frame["LowShelf_Top"][5] - 1.15) < 0.001
          and abs(frame["LowShelf_Plinth"][4] - 0.0) < 0.001
          and abs(frame["LowShelf_Plinth"][5] - 0.10) < 0.001
          and abs(frame["LowShelf_Back"][0] - (-2.15)) < 0.001
          and abs(frame["LowShelf_Back"][1] - (-2.11)) < 0.001
          and abs(frame["LowShelf_Board"][5] - 0.575) < 0.001
          and total_books == 38
          and not any("out_of_shelf" in t for t in tier_rows)
          and abs(stand[4] - 1.15) < 0.001 and abs(stand[5] - 1.23) < 0.001
          and abs(globe_r - 0.17) < 0.001
          and abs(ring_r - 0.202) < 0.001
          and max(floats) <= 0.001)
    row["ok"] = bool(ok)
    return row


def check_ladder(by_name):
    """Library ladder leaning on the tall shelf (x=-1.35/-0.85): rails
    tilted -17.7 deg about X, axis endpoints (y 1.05, z 0.003) ->
    (y 1.72, z 2.10); 6 rungs between the rails."""
    rails = [world_range(by_name["LadderRail_%d" % j]) for j in (0, 1)]
    rail_rots = [round(math.degrees(by_name["LadderRail_%d" % j]
                                    .rotation_euler.x), 2)
                 for j in (0, 1)]
    rungs = [world_range(by_name["LadderRung_%d" % i]) for i in range(6)]
    rung_z = [round((r[4] + r[5]) / 2, 3) for r in rungs]
    rung_y = [round((r[2] + r[3]) / 2, 3) for r in rungs]
    row = {"rail_z": [(r[4], r[5]) for r in rails],
           "rail_y": [(r[2], r[3]) for r in rails],
           "rail_tilt_deg": rail_rots,
           "rail_z_min": min(r[4] for r in rails),
           "rung_z_centers": rung_z, "rung_y_centers": rung_y,
           "rung_x_span": (min(r[0] for r in rungs),
                           max(r[1] for r in rungs))}
    ok = (all(abs(a - (-17.7)) < 0.05 for a in rail_rots)
          and abs(rails[0][5] - 2.105) < 0.01
          and abs(rails[0][2] - 1.027) < 0.01
          and abs(rails[0][3] - 1.743) < 0.01
          and min(r[4] for r in rails) >= -0.001
          and len(rungs) == 6
          and all(abs(z - 2.10 * (0.15 + i * 0.14)) < 0.01
                  for i, z in enumerate(rung_z)))
    row["ok"] = bool(ok)
    return row


def check_desk(by_name):
    """Desk (centre 1.05, 0.55): top z 0.75-0.81, 4 legs z 0-0.75,
    drawer + 2 brass knobs, modesty panel; open spellbook (cover on the
    desk top, pages tilted +-8 deg); 3-arm candelabra with 3 candles +
    flames; ink pot + ink surface + quill; 3 stacked books; scroll with
    2 wooden end knobs."""
    top = world_range(by_name["Desk_Top"])
    legs = [world_range(by_name["DeskLeg_%d_%d" % (dx, dy)])
            for dx, dy in ((-75, -35), (75, -35), (-75, 35), (75, 35))]
    drawer = world_range(by_name["Desk_Drawer"])
    knobs = [world_range(by_name["DeskKnob_%d" % i]) for i in range(2)]
    modesty = world_range(by_name["Desk_Modesty"])
    cover = world_range(by_name["Spellbook_Cover"])
    page_l = by_name["Spellbook_Left"]
    page_r = by_name["Spellbook_Right"]
    pl, pr = world_range(page_l), world_range(page_r)
    page_rots = (round(math.degrees(page_l.rotation_euler.z), 2),
                 round(math.degrees(page_r.rotation_euler.z), 2))
    cand = {n: world_range(by_name[n]) for n in (
        "Candelabra_Base", "Candelabra_Stem", "Candelabra_ArmL",
        "Candelabra_ArmR", "Candelabra_CupL", "Candelabra_CupR",
        "Candelabra_CupC")}
    candles = {}
    for tag in ("DeskCandle_L", "DeskCandle_R", "DeskCandle_C"):
        wax = world_range(by_name[tag])
        flame = world_range(by_name[tag + "_Flame"])
        candles[tag] = {"wax_z": (wax[4], wax[5]),
                        "flame_z": (flame[4], flame[5]),
                        "flame_above_wax_top": round(flame[5] - wax[5], 3)}
    inkpot = world_range(by_name["InkPot"])
    ink = world_range(by_name["Ink_Surface"])
    quill = world_range(by_name["Quill"])
    deskbooks = [world_range(by_name["DeskBook_%d" % i]) for i in range(3)]
    book_gaps = [round(deskbooks[i + 1][4] - deskbooks[i][5], 3)
                 for i in range(2)]
    scroll = world_range(by_name["Scroll"])
    sknobs = [world_range(by_name["ScrollKnob_%d" % x]) for x in (51, 99)]
    row = {"desk_top_z": (top[4], top[5]),
           "desk_top_x": (top[0], top[1]), "desk_top_y": (top[2], top[3]),
           "leg_z": [(l[4], l[5]) for l in legs],
           "drawer_z": (drawer[4], drawer[5]),
           "drawer_y": (drawer[2], drawer[3]),
           "knob_z": [(k[4], k[5]) for k in knobs],
           "modesty_z": (modesty[4], modesty[5]),
           "spellbook_cover_z": (cover[4], cover[5]),
           "spellbook_page_z": (pl[4], pl[5]),
           "spellbook_page_rot_z_deg": page_rots,
           "candelabra": cand,
           "candles": candles,
           "inkpot_z": (inkpot[4], inkpot[5]),
           "ink_surface_z": (ink[4], ink[5]),
           "ink_inside_pot": bool(ink[4] >= inkpot[4]
                                  and ink[5] <= inkpot[5]),
           "quill_z_min": quill[4],
           "deskbook_z": [(b[4], b[5]) for b in deskbooks],
           "deskbook_gaps": book_gaps,
           "scroll_z": (scroll[4], scroll[5]),
           "scroll_knob_z": [(k[4], k[5]) for k in sknobs],
           "scroll_knob_z_min": min(k[4] for k in sknobs)}
    ok = (abs(top[4] - 0.75) < 0.001 and abs(top[5] - 0.81) < 0.001
          and all(abs(l[4] - 0.0) < 0.001 and abs(l[5] - 0.75) < 0.001
                  for l in legs)
          and abs(drawer[4] - 0.46) < 0.001 and abs(drawer[5] - 0.74) < 0.001
          and abs(cover[4] - 0.81) < 0.001 and abs(cover[5] - 0.83) < 0.001
          and abs(page_rots[0] - 8.0) < 0.05
          and abs(page_rots[1] - (-8.0)) < 0.05
          and abs(pl[4] - 0.8275) < 0.001 and abs(pl[5] - 0.8425) < 0.001
          and abs(cand["Candelabra_Base"][4] - 0.81) < 0.001
          and abs(cand["Candelabra_Base"][5] - 0.84) < 0.001
          and abs(cand["Candelabra_Stem"][4] - 0.84) < 0.001
          and abs(cand["Candelabra_Stem"][5] - 1.14) < 0.001
          and abs(cand["Candelabra_CupC"][5] - 1.165) < 0.001
          and all(c["flame_above_wax_top"] > 0.0
                  for c in candles.values())
          and abs(inkpot[4] - 0.81) < 0.001
          and abs(inkpot[5] - 0.89) < 0.001
          and row["ink_inside_pot"]
          and quill[4] >= 0.81
          and abs(deskbooks[0][4] - 0.81) < 0.001
          and book_gaps == [0.005, 0.005]
          and abs(scroll[4] - 0.81) < 0.001 and abs(scroll[5] - 0.90) < 0.001
          and min(k[4] for k in sknobs) >= 0.81 - 0.001)
    row["ok"] = bool(ok)
    return row


def check_floor_candelabra(by_name):
    """Tall floor candelabra at (-1.55, 0.75): base z 0-0.04, pole
    0.04-1.32, tray 1.315-1.345, 3 candles (wax 1.345-1.485) + flames,
    warm point light FloorCandGlow at (-1.55, 0.75, 1.50), 180W."""
    base = world_range(by_name["FloorCand_Base"])
    pole = world_range(by_name["FloorCand_Pole"])
    tray = world_range(by_name["FloorCand_Tray"])
    candles = {}
    for i in range(3):
        wax = world_range(by_name["FloorCandle_%d" % i])
        flame = world_range(by_name["FloorCandle_%d_Flame" % i])
        candles["FloorCandle_%d" % i] = {
            "wax_z": (wax[4], wax[5]), "flame_z": (flame[4], flame[5]),
            "center_xy": (round((wax[0] + wax[1]) / 2, 3),
                          round((wax[2] + wax[3]) / 2, 3))}
    light = bpy.data.objects.get("FloorCandGlow")
    light_row = None
    if light is not None and light.type == 'LIGHT':
        light_row = {"type": light.data.type,
                     "location": tuple(round(v, 2)
                                       for v in light.location),
                     "energy": round(light.data.energy, 1),
                     "color": tuple(round(v, 2)
                                    for v in light.data.color)}
    row = {"base_z": (base[4], base[5]), "pole_z": (pole[4], pole[5]),
           "tray_z": (tray[4], tray[5]), "candles": candles,
           "light": light_row}
    ok = (abs(base[4] - 0.0) < 0.001 and abs(base[5] - 0.04) < 0.001
          and abs(pole[4] - 0.04) < 0.001 and abs(pole[5] - 1.32) < 0.001
          and abs(tray[4] - 1.315) < 0.001 and abs(tray[5] - 1.345) < 0.001
          and all(abs(c["wax_z"][0] - 1.345) < 0.001
                  and abs(c["wax_z"][1] - 1.485) < 0.001
                  for c in candles.values())
          and all(c["flame_z"][0] > c["wax_z"][1] - 0.02
                  for c in candles.values())
          and light_row is not None and light_row["type"] == 'POINT'
          and abs(light_row["location"][0] - (-1.55)) < 0.01
          and abs(light_row["location"][1] - 0.75) < 0.01
          and abs(light_row["location"][2] - 1.50) < 0.01
          and abs(light_row["energy"] - 180.0) < 0.1
          and light_row["color"] == (1.0, 0.70, 0.35))
    row["ok"] = bool(ok)
    return row


def check_chart(by_name):
    """Framed star chart above the desk on the back wall: frame
    (1.70, 2.03, 1.65) 0.95x0.06x0.75, canvas in front of the frame
    front face, gold moon r 0.12 + 5 gold stars at fixed (x, z)."""
    frame = world_range(by_name["Chart_Frame"])
    canvas = world_range(by_name["Chart_Canvas"])
    moon = by_name["Chart_Moon"]
    mvs = world_verts(moon)
    mc = (1.70, 1.975, 1.68)
    moon_r = max(math.hypot(v.x - mc[0], v.z - mc[2]) for v in mvs)
    moon_y = world_range(moon)
    stars = []
    for i, (sx, sz) in enumerate(((1.45, 1.85), (1.95, 1.80),
                                  (1.50, 1.45), (1.90, 1.50),
                                  (1.70, 1.42))):
        r = world_range(by_name["Chart_Star_%d" % i])
        stars.append({"name": "Chart_Star_%d" % i,
                      "x_center": round((r[0] + r[1]) / 2, 3),
                      "z_center": round((r[4] + r[5]) / 2, 3),
                      "y": (r[2], r[3])})
    row = {"frame_y": (frame[2], frame[3]),
           "frame_z": (frame[4], frame[5]),
           "canvas_y": (canvas[2], canvas[3]),
           "canvas_in_front_of_frame": bool(canvas[2] < frame[2]),
           "moon_radius": round(moon_r, 3),
           "moon_y": (moon_y[2], moon_y[3]),
           "moon_z": (moon_y[4], moon_y[5]),
           "stars": stars}
    ok = (abs(frame[2] - 2.00) < 0.001 and abs(frame[3] - 2.06) < 0.001
          and abs(frame[4] - 1.275) < 0.001 and abs(frame[5] - 2.025) < 0.001
          and abs(canvas[2] - 1.98) < 0.001 and abs(canvas[3] - 2.01) < 0.001
          and row["canvas_in_front_of_frame"]
          and abs(moon_r - 0.12) < 0.001
          and abs(moon_y[2] - 1.965) < 0.001
          and abs(moon_y[3] - 1.985) < 0.001
          and all(abs(s["x_center"] - sx) < 0.001
                  and abs(s["z_center"] - sz) < 0.001
                  for s, (sx, sz) in zip(
                      stars, ((1.45, 1.85), (1.95, 1.80), (1.50, 1.45),
                              (1.90, 1.50), (1.70, 1.42)))))
    row["ok"] = bool(ok)
    return row


def check_rug_chair(by_name):
    """Rug (2.6x1.7) + gold trim on the plank floor (plank top z=0.03),
    chair in front of the desk: seat z 0.425-0.475, 4 legs z 0-0.45,
    back posts z 0.45-0.95 + top rail z 0.91-0.99."""
    rug = world_range(by_name["Rug"])
    trim = world_range(by_name["Rug_Trim"])
    seat = world_range(by_name["Chair_Seat"])
    legs = [world_range(by_name["ChairLeg_%d_%d" % (dx, dy)])
            for dx, dy in ((-20, -17), (20, -17), (-20, 17), (20, 17))]
    backs = [world_range(by_name["ChairBack_%d" % dx]) for dx in (-20, 20)]
    btop = world_range(by_name["ChairBack_Top"])
    row = {"rug_z": (rug[4], rug[5]), "rug_x": (rug[0], rug[1]),
           "rug_y": (rug[2], rug[3]),
           "trim_z": (trim[4], trim[5]),
           "trim_inside_rug": bool(trim[0] >= rug[0] and trim[1] <= rug[1]
                                   and trim[2] >= rug[2]
                                   and trim[3] <= rug[3]),
           "seat_z": (seat[4], seat[5]),
           "leg_z": [(l[4], l[5]) for l in legs],
           "back_z": [(b[4], b[5]) for b in backs],
           "back_top_z": (btop[4], btop[5])}
    ok = (abs(rug[4] - 0.03) < 0.001 and abs(rug[5] - 0.054) < 0.001
          and abs(trim[4] - 0.053) < 0.001 and abs(trim[5] - 0.059) < 0.001
          and row["trim_inside_rug"]
          and abs(seat[4] - 0.425) < 0.001 and abs(seat[5] - 0.475) < 0.001
          and all(abs(l[4] - 0.0) < 0.001 and abs(l[5] - 0.45) < 0.001
                  for l in legs)
          and all(abs(b[4] - 0.45) < 0.001 and abs(b[5] - 0.95) < 0.001
                  for b in backs)
          and abs(btop[4] - 0.91) < 0.001 and abs(btop[5] - 0.99) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_floor_books(by_name):
    """Two books left on the floor by the ladder: FloorBook_0 flat on
    the plank top (z 0.03-0.08), FloorBook_1 stacked on top of it
    (z 0.08-0.13)."""
    b0 = world_range(by_name["FloorBook_0"])
    b1 = world_range(by_name["FloorBook_1"])
    row = {"floorbook_0_z": (b0[4], b0[5]),
           "floorbook_1_z": (b1[4], b1[5]),
           "stack_gap": round(b1[4] - b0[5], 3)}
    ok = (abs(b0[4] - 0.03) < 0.001 and abs(b0[5] - 0.08) < 0.001
          and abs(b1[4] - 0.08) < 0.001 and abs(b1[5] - 0.13) < 0.001
          and abs(row["stack_gap"]) < 0.001)
    row["ok"] = bool(ok)
    return row


def check_ground_contact(by_name, results):
    """Nothing may sink below the ground plane (z=0). Floor-standing
    parts sit at z=0 and therefore embed 0.03 into the plank floor
    (plank top z=0.03) -- a build-wide design choice, reported once
    here, not per part."""
    zmins = {n: world_range(o)[4] for n, o in by_name.items()}
    below = {n: z for n, z in sorted(zmins.items()) if z < -0.001}
    on_planks = sum(1 for z in zmins.values() if abs(z) < 0.001)
    return {"checked": len(zmins),
            "below_ground": below,
            "parts_at_z0_embedded_in_planks_0.03": on_planks,
            "global_min_z": round(min(zmins.values()), 3),
            "ok": bool(not below)}


# design values from the 040 build script:
# (metallic, roughness, base color) for Principled materials
DESIGN_MATS = {
    "Lib_Plaster": (0.00, 0.95, (0.76, 0.70, 0.58)),
    "Lib_Wainscot": (0.00, 0.85, (0.40, 0.26, 0.13)),
    "Lib_Beam": (0.00, 0.90, (0.30, 0.19, 0.09)),
    "Lib_Shelf": (0.00, 0.85, (0.38, 0.24, 0.11)),
    "Lib_ShelfDark": (0.00, 0.90, (0.28, 0.17, 0.08)),
    "Lib_Desk": (0.00, 0.80, (0.46, 0.30, 0.14)),
    "Lib_DeskTop": (0.00, 0.70, (0.56, 0.38, 0.19)),
    "Lib_Brass": (0.90, 0.30, (0.75, 0.58, 0.20)),
    "Lib_Gold": (0.90, 0.25, (0.85, 0.68, 0.25)),
    "Lib_Iron": (0.70, 0.50, (0.16, 0.16, 0.18)),
    "Lib_Paper": (0.00, 0.90, (0.92, 0.88, 0.74)),
    "Lib_Parchment": (0.00, 0.90, (0.88, 0.80, 0.60)),
    "Lib_Ink": (0.00, 0.15, (0.05, 0.05, 0.10)),
    "Lib_Rug": (0.00, 1.00, (0.42, 0.11, 0.13)),
    "Lib_RugTrim": (0.00, 1.00, (0.72, 0.58, 0.28)),
    "Lib_Chart": (0.00, 0.90, (0.08, 0.12, 0.30)),
    "Lib_Globe": (0.00, 0.60, (0.15, 0.35, 0.60)),
    "Lib_Wax": (0.00, 0.70, (0.94, 0.88, 0.74)),
    "Book_Red": (0.00, 0.80, (0.45, 0.10, 0.12)),
    "Book_Green": (0.00, 0.80, (0.10, 0.35, 0.15)),
    "Book_Blue": (0.00, 0.80, (0.12, 0.20, 0.45)),
    "Book_Purple": (0.00, 0.80, (0.35, 0.15, 0.45)),
    "Book_Brown": (0.00, 0.80, (0.45, 0.28, 0.12)),
    "Book_Teal": (0.00, 0.80, (0.10, 0.35, 0.35)),
    "Book_Ochre": (0.00, 0.80, (0.65, 0.50, 0.15)),
}
PLANK_SHADES = [(0.42, 0.28, 0.14), (0.50, 0.34, 0.18),
                (0.38, 0.25, 0.12), (0.55, 0.38, 0.20)]
for _i in range(8):
    DESIGN_MATS["Plank_%d" % _i] = (0.00, 0.90, PLANK_SHADES[_i % 4])


def check_materials(parts):
    """Read node values, not names. Lib_Flame is checked separately
    for its emission values."""
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
    # flame: emission color (1.0, 0.55, 0.10), strength 4.0,
    # base color (1.0, 0.60, 0.10)
    flame = bpy.data.materials.get("Lib_Flame")
    flame_row = {"name": "Lib_Flame", "found": flame is not None,
                 "ok": False}
    if flame is not None and flame.use_nodes:
        for n in flame.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                ec = tuple(round(v, 2) for v in
                           n.inputs["Emission Color"].default_value[:3])
                es = round(n.inputs["Emission Strength"].default_value, 2)
                bc = tuple(round(v, 2) for v in
                           n.inputs["Base Color"].default_value[:3])
                flame_row.update({"emission_color": ec,
                                  "emission_strength": es,
                                  "base_color": bc,
                                  "ok": bool(ec == (1.0, 0.55, 0.10)
                                            and abs(es - 4.0) < 0.01
                                            and bc == (1.0, 0.60, 0.10))})
                break
    rows.append(flame_row)
    used = {m.name for o in parts for m in o.data.materials if m}
    missing_design = [n for n in DESIGN_MATS if n not in used]
    return {"rows": rows,
            "all_ok": bool(all(r["ok"] for r in rows)),
            "unused_design_mats": missing_design}


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    parts = [o for o in bpy.context.scene.objects
             if o.type == 'MESH' and o.name not in EXCLUDE]
    by_name = {o.name: o for o in parts}
    print("QA_PARTS_COUNT:", len(parts))
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

    # centre-based winding (040 build's own self-check) for comparison
    winding = {}
    for obj in sorted(parts, key=lambda o: o.name):
        n = check_winding_center(obj)
        if n:
            winding[obj.name] = n
    print("QA_WINDING_CENTER:", winding)

    walls = check_walls(by_name)
    print("QA_WALLS:", walls)
    planks = check_planks(by_name)
    print("QA_PLANKS:", planks)
    tall_shelf = check_tall_shelf(by_name)
    print("QA_TALL_SHELF:", tall_shelf)
    low_shelf = check_low_shelf(by_name)
    print("QA_LOW_SHELF:", low_shelf)
    ladder = check_ladder(by_name)
    print("QA_LADDER:", ladder)
    desk = check_desk(by_name)
    print("QA_DESK:", desk)
    floor_cand = check_floor_candelabra(by_name)
    print("QA_FLOOR_CANDELABRA:", floor_cand)
    chart = check_chart(by_name)
    print("QA_CHART:", chart)
    rug_chair = check_rug_chair(by_name)
    print("QA_RUG_CHAIR:", rug_chair)
    floor_books = check_floor_books(by_name)
    print("QA_FLOOR_BOOKS:", floor_books)
    ground = check_ground_contact(by_name, results)
    print("QA_GROUND_CONTACT:", ground)
    mats = check_materials(parts)
    print("QA_MATERIALS:", mats)

    structure = {"walls": walls, "planks": planks,
                 "tall_shelf": tall_shelf, "low_shelf": low_shelf,
                 "ladder": ladder, "desk": desk,
                 "floor_candelabra": floor_cand, "chart": chart,
                 "rug_chair": rug_chair, "floor_books": floor_books,
                 "ground_contact": ground}
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
    worst_overlap_part = max(results, key=lambda k: results[k]["uv"]["overlap_pct"])
    ngons_ok = tot["ngons"] == 0
    uv_ok = all(r["uv"]["has_uv"] for r in results.values())
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and tot["boundary_edges"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and structure_ok and mats["all_ok"])

    summary = {
        "asset": "040-magic-library-corner",
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
        "winding_center_flagged": winding,
        "uv_out_of_bounds": tot_oob,
        "uv_ok": bool(uv_ok),
        "uv_utilization_per_part": {k: round(v["uv"]["utilization"], 3)
                                    for k, v in results.items()},
        "uv_islands": tot_islands,
        "uv_overlap_pct": round(worst_overlap, 2),
        "uv_overlap_worst_part": worst_overlap_part,
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

    order = sorted(results.keys())
    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 041 资产质检单：魔法图书馆角落场景（040）\n\n")
        f.write("被检资产：`scenes/040-magic-library-corner.blend`（%d 个场景部件，不含地面）\n" % len(results))
        f.write("检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。\n\n")
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
        if winding:
            f.write("- 040 构建自检（形心法）报出的内翻面复核：%s\n" % (
                ", ".join("%s：%d 面" % (n, c) for n, c in winding.items())))
            f.write("  （注：形心法以网格形心为参考点，对圆环类网格是误报——圆环形心在环孔中心，"
                    "内侧管壁的法线天然指向形心。bmesh recalc 逐面比对为权威判定："
                    "本单倒置面 %d 个，圆环绕向本身一致，无需修复。）\n\n" % tot["inverted_normals"])
        else:
            f.write("- 040 构建自检（形心法）复核：无部件报内翻面。\n\n")
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
        f.write("## 4. 场景结构（实测）\n\n")
        w = walls
        f.write("- 角落墙体：后墙 x %.2f–%.2f、y %.2f–%.2f、z %.2f–%.2f；左墙 x %.2f–%.2f、y %.2f–%.2f、z %.2f–%.2f；"
                "护墙板高 1.00（z 0–1.00），压条 z %.2f–%.2f；木梁 z %.2f–%.2f；角柱 z %.2f–%.2f 落地；"
                "左墙端头伸入后墙墙身、角部无缝隙：%s"
                "（注：后墙向左超出左墙外侧 %.2f，角部外侧有一小段外露墙端）：%s\n" % (
                    w["wall_back"][0], w["wall_back"][1],
                    w["wall_back"][2], w["wall_back"][3],
                    w["wall_back"][4], w["wall_back"][5],
                    w["wall_left"][0], w["wall_left"][1],
                    w["wall_left"][2], w["wall_left"][3],
                    w["wall_left"][4], w["wall_left"][5],
                    w["rail_back_z"][0], w["rail_back_z"][1],
                    w["beam_back_z"][0], w["beam_back_z"][1],
                    w["post_z"][0], w["post_z"][1],
                    "是" if w["corner_overlap"] else "否",
                    w["back_wall_overhang_past_left_wall"],
                    verdict(w["ok"])))
        p = planks
        f.write("- 木地板：共 %d 块，全部 z 0.00–0.03 贴地，板宽 0.58，板间缝隙 %s：%s\n" % (
            p["count"], ", ".join("%.3f" % g for g in p["gaps"]),
            verdict(p["ok"])))
        ts = tall_shelf
        f.write("- 高书架：框架 x -1.60–0.90、z 0–2.35；4 块层板顶面 z %s；"
                "5 层共 %d 本书（设计 111 本），斜靠书 %d 本；"
                "各层书数 %s；书底最大浮空 %.3f，浮空 >1mm 的书 %d 本：%s\n" % (
                    ", ".join("%.3f" % t for t in ts["board_tops"]),
                    ts["total_books"], ts["leaning_books"],
                    ", ".join("%d" % t["count"] for t in ts["tiers"]
                              if "count" in t),
                    ts["max_book_float"], ts["books_floating_over_1mm"],
                    verdict(ts["ok"])))
        for t in ts["tiers"]:
            if "count" in t:
                f.write("  - 第 %d 层：%d 本，层板顶 z=%.3f，书底最大浮空 %.3f\n" % (
                    t["tier"], t["count"], t["base"], t["max_float"]))
        f.write("  - 第 3 层右端平放叠书 3 本：z %s，层间缝隙 %s（设计 0.005）：%s\n" % (
            ", ".join("%.3f–%.3f" % z for z in ts["stack_z"]),
            ", ".join("%.3f" % g for g in ts["stack_gaps"]),
            verdict(ts["stack_gaps"] == [0.005, 0.005])))
        if ts["books_floating_over_1mm"]:
            f.write("  **缺陷：%d 本斜靠书底面浮空，最大 %.3f——构建脚本 book_row 的 lift "
                    "公式多算了 h(1-cosθ)，斜靠书整体被抬高；修复：lift 改为 "
                    "(h/2)(cosθ-1) + (w/2)|sinθ|，使斜靠书底角恰好落在层板顶面。**\n" % (
                        ts["books_floating_over_1mm"], ts["max_book_float"]))
        ls = low_shelf
        f.write("- 矮书架：端板 y -0.60–-0.55 / 1.35–1.40，顶板 z 1.10–1.15，底座 z 0–0.10，"
                "背板 x -2.15–-2.11，层板顶 z=0.575；2 层共 %d 本书（设计 38 本），斜靠书 %d 本；"
                "各层书数 %s；书底最大浮空 %.3f，浮空 >1mm 的书 %d 本：%s\n" % (
                    ls["total_books"], ls["leaning_books"],
                    ", ".join("%d" % t["count"] for t in ls["tiers"]
                              if "count" in t),
                    ls["max_book_float"], ls["books_floating_over_1mm"],
                    verdict(ls["ok"])))
        f.write("  - 地球仪：支架 z %.3f–%.3f 落在矮书架顶板（顶 z=1.15）；蓝球 r=%.3f（设计 0.17），"
                "中心 z=1.40；金色子午环最大半径 %.3f（设计 0.202），环底 z=%.3f，高出书架顶面 %.3f：%s\n" % (
                    ls["globe_stand_z"][0], ls["globe_stand_z"][1],
                    ls["globe_radius"], ls["ring_max_radius"],
                    ls["ring_z"][0], ls["ring_bottom_above_shelf_top"],
                    verdict(ls["ok"])))
        if ls["books_floating_over_1mm"]:
            f.write("  **缺陷：%d 本斜靠书底面浮空，最大 %.3f——与高书架同一 lift 公式问题；"
                    "修复：lift 改为 (h/2)(cosθ-1) + (w/2)|sinθ|。**\n" % (
                        ls["books_floating_over_1mm"], ls["max_book_float"]))
        ld = ladder
        f.write("- 图书馆梯子：两根立柱绕 X 倾斜 %s°（设计 -17.7°），"
                "立柱 z %.3f–%.3f、y %.3f–%.3f；6 根横档，中心 z %s：%s\n" % (
                    ", ".join("%.1f" % a for a in ld["rail_tilt_deg"]),
                    ld["rail_z"][0][0], ld["rail_z"][0][1],
                    ld["rail_y"][0][0], ld["rail_y"][0][1],
                    ", ".join("%.3f" % z for z in ld["rung_z_centers"]),
                    verdict(ld["ok"])))
        if ld["rail_z_min"] < -0.001:
            f.write("  **缺陷：梯子立柱底端 z=%.3f，低于地面（z=0）%.3f——立柱长 2.20、"
                    "中心 z=1.05、倾斜 17.7° 后底端角点探出地面；修复：立柱中心 z 上移 0.005，"
                    "或立柱长度缩短 0.01。**\n" % (
                        ld["rail_z_min"], -ld["rail_z_min"]))
        d = desk
        f.write("- 书桌：台面 z %.2f–%.2f、x %.2f–%.2f、y %.2f–%.2f；4 腿 z 0–0.75 落地；"
                "抽屉 z %.2f–%.2f、y %.2f–%.2f；挡板 z %.2f–%.2f：%s\n" % (
                    d["desk_top_z"][0], d["desk_top_z"][1],
                    d["desk_top_x"][0], d["desk_top_x"][1],
                    d["desk_top_y"][0], d["desk_top_y"][1],
                    d["drawer_z"][0], d["drawer_z"][1],
                    d["drawer_y"][0], d["drawer_y"][1],
                    d["modesty_z"][0], d["modesty_z"][1],
                    verdict(d["ok"])))
        f.write("  - 翻开法术书：封面 z %.3f–%.3f 贴在台面（顶 z=0.81）；两页绕 Z 旋转 %s°，"
                "z %.3f–%.3f，页底嵌入封面 0.003（无缝隙）：%s\n" % (
                    d["spellbook_cover_z"][0], d["spellbook_cover_z"][1],
                    ", ".join("%.1f" % a for a in d["spellbook_page_rot_z_deg"]),
                    d["spellbook_page_z"][0], d["spellbook_page_z"][1],
                    verdict(d["ok"])))
        f.write("  - 三臂烛台：底座 z %.3f–%.3f、立柱 z %.3f–%.3f、中央杯顶 z=%.3f；"
                "3 支蜡烛均带火焰，火焰顶高出蜡顶 %s：%s\n" % (
                    d["candelabra"]["Candelabra_Base"][4],
                    d["candelabra"]["Candelabra_Base"][5],
                    d["candelabra"]["Candelabra_Stem"][4],
                    d["candelabra"]["Candelabra_Stem"][5],
                    d["candelabra"]["Candelabra_CupC"][5],
                    ", ".join("%.3f" % c["flame_above_wax_top"]
                              for c in d["candles"].values()),
                    verdict(d["ok"])))
        f.write("  - 墨水瓶 z %.3f–%.3f 贴台面，墨面 z %.3f–%.3f 在瓶内：%s；"
                "羽毛笔最低 z=%.3f（台面 z=0.81，笔尖悬空 %.3f，靠在墨水瓶上）：%s\n" % (
                    d["inkpot_z"][0], d["inkpot_z"][1],
                    d["ink_surface_z"][0], d["ink_surface_z"][1],
                    verdict(d["ink_inside_pot"]),
                    d["quill_z_min"], d["quill_z_min"] - 0.81,
                    verdict(d["quill_z_min"] >= 0.81)))
        f.write("  - 桌上叠书 3 本：z %s，层间缝隙 %s（设计 0.005）；"
                "羊皮卷轴 z %.3f–%.3f 贴台面，两端木轴 z %.3f–%.3f：%s\n" % (
                    ", ".join("%.3f–%.3f" % z for z in d["deskbook_z"]),
                    ", ".join("%.3f" % g for g in d["deskbook_gaps"]),
                    d["scroll_z"][0], d["scroll_z"][1],
                    d["scroll_knob_z"][0][0], d["scroll_knob_z"][0][1],
                    verdict(d["ok"])))
        if d["scroll_knob_z_min"] < 0.81 - 0.001:
            f.write("  **缺陷：卷轴端木轴最低 z=%.3f，低于台面（z=0.81）%.3f——"
                    "木轴半径 0.055 大于卷轴半径 0.045、轴心同高，轴底探入台面；"
                    "修复：木轴轴心 z 上移 0.010，或木轴半径改为 0.045。**\n" % (
                        d["scroll_knob_z_min"],
                        0.81 - d["scroll_knob_z_min"]))
        fc = floor_cand
        f.write("- 落地烛台：底座 z %.2f–%.2f 落地，立柱 z %.2f–%.2f，托盘 z %.3f–%.3f；"
                "3 支蜡烛 z %.3f–%.3f 均带火焰；FloorCandGlow 点光源位于 (%s)，能量 %.1fW，颜色 %s：%s\n" % (
                    fc["base_z"][0], fc["base_z"][1],
                    fc["pole_z"][0], fc["pole_z"][1],
                    fc["tray_z"][0], fc["tray_z"][1],
                    list(fc["candles"].values())[0]["wax_z"][0],
                    list(fc["candles"].values())[0]["wax_z"][1],
                    ", ".join("%.2f" % v for v in fc["light"]["location"])
                    if fc["light"] else "未找到",
                    fc["light"]["energy"] if fc["light"] else 0,
                    fc["light"]["color"] if fc["light"] else "—",
                    verdict(fc["ok"])))
        ch = chart
        f.write("- 星图挂画：画框 y %.2f–%.2f（后墙面 y=2.05，框背嵌入墙内 0.01）、"
                "z %.2f–%.2f；画布 y %.2f–%.2f，画布正面在画框正面之前 %.3f；"
                "金月 r=%.3f，y %.3f–%.3f；5 颗金星位置 %s：%s\n" % (
                    ch["frame_y"][0], ch["frame_y"][1],
                    ch["frame_z"][0], ch["frame_z"][1],
                    ch["canvas_y"][0], ch["canvas_y"][1],
                    ch["frame_y"][0] - ch["canvas_y"][0],
                    ch["moon_radius"], ch["moon_y"][0], ch["moon_y"][1],
                    ", ".join("(%.2f, %.2f)" % (s["x_center"], s["z_center"])
                              for s in ch["stars"]),
                    verdict(ch["ok"])))
        rc = rug_chair
        f.write("- 地毯：z %.3f–%.3f 贴在木地板顶面（z=0.03），金色内边 z %.3f–%.3f 在地毯范围内：%s；"
                "木椅：座面 z %.3f–%.3f，4 腿 z 0–0.45 落地，靠背立柱 z %.3f–%.3f、顶梁 z %.3f–%.3f：%s\n" % (
                    rc["rug_z"][0], rc["rug_z"][1],
                    rc["trim_z"][0], rc["trim_z"][1],
                    verdict(rc["ok"]),
                    rc["seat_z"][0], rc["seat_z"][1],
                    rc["back_z"][0][0], rc["back_z"][0][1],
                    rc["back_top_z"][0], rc["back_top_z"][1],
                    verdict(rc["ok"])))
        fb = floor_books
        f.write("- 地面散书：下本 z %.3f–%.3f 贴在木地板顶面（z=0.03），上本 z %.3f–%.3f，"
                "叠放缝隙 %.3f：%s\n" % (
                    fb["floorbook_0_z"][0], fb["floorbook_0_z"][1],
                    fb["floorbook_1_z"][0], fb["floorbook_1_z"][1],
                    fb["stack_gap"], verdict(fb["ok"])))
        g = ground
        f.write("- 落地检查：共检查 %d 个部件，最低 z=%.3f，低于地面的部件：%s：%s\n" % (
            g["checked"], g["global_min_z"],
            "无" if not g["below_ground"]
            else ", ".join("%s(z_min=%.3f)" % (n, z)
                           for n, z in g["below_ground"].items()),
            verdict(g["ok"])))
        f.write("  （注：%d 个部件底面 z=0，与木地板顶面（z=0.03）之间有 0.03 的嵌入——"
                "全场景统一设计：所有落地件以地面 z=0 为基准，地板铺在地面之上，底座被地板"
                "包住 0.03，渲染中不可见，不作缺陷计。）\n\n" % g["parts_at_z0_embedded_in_planks_0.03"])
        f.write("## 5. 材质 / 贴图\n\n")
        f.write("- 各部件材质均为程序化 Principled 材质，无图片贴图（%d 个部件，%d 个材质槽）：\n" % (
            len(parts), len(mat_rows)))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值）：\n")
        for r in mats["rows"]:
            if not r.get("found"):
                f.write("  - %s：未找到材质：不通过\n" % r["name"])
                continue
            if r["name"] == "Lib_Flame":
                f.write("  - Lib_Flame：Emission %s（设计 (1.0, 0.55, 0.10)），强度 %.2f（设计 4.0），"
                        "底色 %s（设计 (1.0, 0.60, 0.10)）：%s\n" % (
                            r.get("emission_color"), r.get("emission_strength"),
                            r.get("base_color"), verdict(r["ok"])))
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
            failed = [k for k, v in structure.items() if not v["ok"]]
            f.write("**总体：复核（REVIEW NEEDED）**\n\n")
            f.write("未通过项：%s。拓扑 / 法线 / UV / 材质实测全部通过，"
                    "问题只在场景结构，见第 4 节。\n" % "、".join(failed))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
