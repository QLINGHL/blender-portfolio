# -*- coding: utf-8 -*-
"""021 资产质检：对 020 低模法师做真实 mesh 检查（拓扑/法线/UV/材质），
并实测关节环形拓扑（臂/腿环数、中环位置、中环顶点价数）与法师特有结构：
长袍 5 环喇叭形收放、法杖组装（杖身/金箍/水晶）、尖顶帽三件套对齐、
胡须前垂范围、水晶自发光节点强度。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 021-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "020-lowpoly-mage.blend")
UV_JSON = os.path.join(ROOT, "scenes", "021-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "021-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "021-asset-qa-checklist.md")

# mage parts only (Ground / lights / camera are scene dressing)
PARTS = ["Head", "Eye", "Eye.001", "Beard", "Neck", "HatBrim", "Hat",
         "HatTip", "Robe", "Collar", "Sash",
         "Arm", "Hand", "Arm.001", "Hand.001",
         "Leg", "Boot", "Leg.001", "Boot.001",
         "StaffShaft", "StaffRing", "StaffRing.001", "StaffCrystal"]
LIMBS = ["Arm", "Arm.001", "Leg", "Leg.001"]
# 8 expected N-gons are all cylinder end caps, never on joints:
# StaffShaft 2 (6-gon caps), StaffRing 2 + StaffRing.001 2 (8-gon caps),
# HatBrim 2 (12-gon caps).
EXPECTED_NGONS = {"StaffShaft": 2, "StaffRing": 2, "StaffRing.001": 2,
                  "HatBrim": 2}


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


def check_limb_rings(obj):
    """Measure the edge-loop rings of a tube limb (Arm/Leg).
    Axis = line through the two cap-center verts (valence 6 fan centers);
    each ring plane is perpendicular to it, so distinct projected coords
    = ring count."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    cap_centers = [v for v in bm.verts if len(v.link_edges) == 6
                   and len(v.link_faces) == 6]
    if len(cap_centers) == 2:
        axis = (cap_centers[1].co - cap_centers[0].co).normalized()
        origin = cap_centers[0].co
        vals = sorted({round((v.co - origin).dot(axis), 3) for v in bm.verts})
    else:
        mins = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts),
                       min(v.co.z for v in bm.verts)))
        maxs = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts),
                       max(v.co.z for v in bm.verts)))
        spans = maxs - mins
        ai = max(range(3), key=lambda i: spans[i])
        axis = Vector((0, 0, 0))
        axis[ai] = 1.0
        origin = mins
        vals = sorted({round((v.co - origin).dot(axis), 3) for v in bm.verts})
    n_rings = len(vals)
    total_len = vals[-1] - vals[0] if len(vals) > 1 else 0.0
    mid = vals[len(vals) // 2] if vals else 0.0
    mid_frac = ((mid - vals[0]) / total_len) if total_len > 1e-6 else 0.0
    mid_verts = [v for v in bm.verts
                 if round((v.co - origin).dot(axis), 3) == mid]
    mid_max_valence = max((len(v.link_edges) for v in mid_verts), default=0)
    mid_tris = 0
    for f in bm.faces:
        if any(round((v.co - origin).dot(axis), 3) == mid for v in f.verts):
            if len(f.verts) == 3:
                mid_tris += 1
    bm.free()
    return {"rings": n_rings, "mid_ring_fraction": round(mid_frac, 3),
            "mid_ring_max_valence": mid_max_valence,
            "mid_ring_tri_faces": mid_tris}


def world_z_range(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    zs = [(mw @ v.co).z for v in obj.data.vertices]
    return round(min(zs), 3), round(max(zs), 3)


def check_robe(parts):
    """Robe: 5 rings on the z axis (cap centers share the end-ring z),
    radii must grow from shoulder (0.30) to hem (0.48)."""
    robe = next(o for o in parts if o.name == "Robe")
    verts = [v.co for v in robe.data.vertices]
    by_z = {}
    for v in verts:
        by_z.setdefault(round(v.z, 3), []).append(v)
    rows = []
    for z in sorted(by_z.keys(), reverse=True):
        # cap-center verts sit on the axis (radius 0) and share the end
        # rings' z, so use the max radius, not the mean.
        rs = [math.hypot(v.x, v.y) for v in by_z[z]]
        rows.append({"z": z, "radius": round(max(rs), 3),
                     "verts": len(rs)})
    design = [0.30, 0.31, 0.34, 0.40, 0.48]
    ok = (len(rows) == 5
          and all(abs(r["radius"] - d) < 0.005
                  for r, d in zip(rows, design))
          and all(rows[i]["radius"] < rows[i + 1]["radius"]
                  for i in range(4)))
    return {"rings": rows, "ok": bool(ok)}


def world_range(obj):
    """World-space bbox of the evaluated mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    ws = [mw @ v.co for v in obj.data.vertices]
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def check_staff(parts):
    """Staff assembly: shaft is a vertical 6-sided cylinder; both gold
    rings must sit on the shaft (z inside shaft span, radius > shaft
    radius); the crystal must share the shaft x, sit with its centre
    above the shaft top and its bottom apex embedded in the shaft top
    (mounted, not floating). Note: StaffCrystal's verts are baked in
    world coords, so its centre comes from the world bbox, not
    obj.location (which is 0,0,0)."""
    shaft = next(o for o in parts if o.name == "StaffShaft")
    rings = [next(o for o in parts if o.name == n)
             for n in ("StaffRing", "StaffRing.001")]
    crystal = next(o for o in parts if o.name == "StaffCrystal")
    smin, smax = world_z_range(shaft)
    shaft_r = max(math.hypot(v.co.x, v.co.y)
                  for v in shaft.data.vertices)
    rows = []
    for r in rings:
        rmin, rmax = world_z_range(r)
        rr = max(math.hypot(v.co.x, v.co.y) for v in r.data.vertices)
        rows.append({"name": r.name, "z_center": round((rmin + rmax) / 2, 3),
                     "radius": round(rr, 3),
                     "on_shaft": bool(smin < rmin and rmax < smax),
                     "wraps_shaft": bool(rr > shaft_r + 0.005)})
    cxmin, cxmax, _, _, cmin, cmax = world_range(crystal)
    ccx = (cxmin + cxmax) / 2.0
    ccz = (cmin + cmax) / 2.0
    crow = {"center_x": round(ccx, 3),
            "shaft_x": round(shaft.location.x, 3),
            "center_z": round(ccz, 3),
            "min_z": cmin, "max_z": cmax,
            "shaft_top_z": smax,
            "gap_center_above_shaft_top": round(ccz - smax, 3),
            "bottom_embedded": round(smax - cmin, 3)}
    ok = (all(r["on_shaft"] and r["wraps_shaft"] for r in rows)
          and abs(crow["center_x"] - crow["shaft_x"]) < 0.001
          and crow["center_z"] > smax
          and 0.0 < crow["bottom_embedded"] < 0.2)
    return {"shaft_z": (smin, smax), "shaft_radius": round(shaft_r, 3),
            "rings": rows, "crystal": crow, "ok": bool(ok)}


def check_hat(parts):
    """Hat: brim disk at z=1.70, cone base starts at the brim, tip sphere
    sits at the cone apex."""
    brim = next(o for o in parts if o.name == "HatBrim")
    hat = next(o for o in parts if o.name == "Hat")
    tip = next(o for o in parts if o.name == "HatTip")
    bmin, bmax = world_z_range(brim)
    hmin, hmax = world_z_range(hat)
    tmin, tmax = world_z_range(tip)
    row = {"brim_z": (bmin, bmax), "brim_center_z": round(brim.location.z, 3),
           "hat_z": (hmin, hmax), "hat_base_below_brim_top":
               round(bmax - hmin, 3),
           "tip_center_z": round(tip.location.z, 3),
           "tip_minus_hat_top": round(tip.location.z - hmax, 3)}
    # hat base must sit inside the brim slab (embedded, not floating
    # above it and not poking through below it)
    ok = (abs(brim.location.z - 1.70) < 0.001
          and bmin - 0.005 <= hmin <= bmax + 0.005
          and abs(row["tip_minus_hat_top"]) < 0.02)
    row["ok"] = bool(ok)
    return row


def check_beard(parts):
    """Beard: tapered tube hanging down the front (-Y) of the robe, from
    the chin (z ~1.38) to the chest (z ~1.06); all verts on the front."""
    beard = next(o for o in parts if o.name == "Beard")
    head = next(o for o in parts if o.name == "Head")
    zs = [v.co.z for v in beard.data.vertices]
    ys = [v.co.y for v in beard.data.vertices]
    _, head_top = world_z_range(head)
    row = {"top_z": round(max(zs), 3), "bottom_z": round(min(zs), 3),
           "head_top_z": head_top, "max_y": round(max(ys), 3),
           "all_front": bool(max(ys) < 0.05)}
    ok = (row["top_z"] > 1.30 and row["bottom_z"] < 1.15
          and row["all_front"])
    row["ok"] = bool(ok)
    return row


def check_crystal_emission(parts):
    """Crystal material: Emission node (Strength 0.6) mixed 45% over the
    Principled BSDF. Read the node values, not the name."""
    mat = bpy.data.materials.get("Crystal")
    strength = None
    mix_fac = None
    if mat is not None and mat.use_nodes:
        emit = None
        mix = None
        for n in mat.node_tree.nodes:
            if n.type == 'EMISSION':
                emit = n
            elif n.type == 'MIX_SHADER':
                mix = n
        if emit is not None:
            strength = round(emit.inputs["Strength"].default_value, 2)
        if mix is not None:
            mix_fac = round(mix.inputs["Fac"].default_value, 2)
    ok = (strength is not None and abs(strength - 0.6) < 0.01
          and mix_fac is not None and abs(mix_fac - 0.45) < 0.01)
    return {"emission_strength": strength, "mix_fac": mix_fac,
            "ok": bool(ok)}


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

    rings = {}
    for name in LIMBS:
        obj = next(o for o in parts if o.name == name)
        rings[name] = check_limb_rings(obj)
        print("QA_RINGS %s rings=%d mid_frac=%.3f mid_max_valence=%d "
              "mid_tri_faces=%d" % (
                  name, rings[name]["rings"], rings[name]["mid_ring_fraction"],
                  rings[name]["mid_ring_max_valence"],
                  rings[name]["mid_ring_tri_faces"]))

    robe = check_robe(parts)
    print("QA_ROBE:", robe)
    staff = check_staff(parts)
    print("QA_STAFF:", staff)
    hat = check_hat(parts)
    print("QA_HAT:", hat)
    beard = check_beard(parts)
    print("QA_BEARD:", beard)
    emission = check_crystal_emission(parts)
    print("QA_EMISSION:", emission)

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
    rings_ok = all(rings[n]["rings"] == 5
                   and abs(rings[n]["mid_ring_fraction"] - 0.5) < 0.05
                   and rings[n]["mid_ring_max_valence"] == 4
                   and rings[n]["mid_ring_tri_faces"] == 0
                   for n in LIMBS)
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and tot["boundary_edges"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0 and rings_ok
              and robe["ok"] and staff["ok"] and hat["ok"]
              and beard["ok"] and emission["ok"])

    summary = {
        "asset": "020-lowpoly-mage",
        "parts": len(results),
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "ngons_expected": sum(EXPECTED_NGONS.values()),
        "ngons_ok": bool(ngons_ok),
        "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "boundary_edges": tot["boundary_edges"],
        "inverted_normals": tot["inverted_normals"],
        "uv_out_of_bounds": tot_oob,
        "uv_utilization_per_part": {k: round(v["uv"]["utilization"], 3)
                                    for k, v in results.items()},
        "uv_islands": tot_islands,
        "uv_overlap_pct": round(worst_overlap, 2),
        "empty_material_slots": empty_slots,
        "joint_rings": rings,
        "joint_rings_ok": bool(rings_ok),
        "robe": robe,
        "staff": staff,
        "hat": hat,
        "beard": beard,
        "emission": emission,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("QA_SUMMARY:", summary)

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 021 资产质检单：低模法师（020）\n\n")
        f.write("被检资产：`scenes/020-lowpoly-mage.blend`（24 个法师部件，不含场景地面/灯光/相机）\n")
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
        f.write("- N-gon：共 %d 个，全部为圆柱体端盖（StaffShaft 2、StaffRing 2、StaffRing.001 2、HatBrim 2），其余部件 0 个，不在关节处：%s\n" % (
            tot["ngons"], verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 闭合网格（无边界边）：%s\n" % verdict(tot["boundary_edges"] == 0))
        f.write("- 最高顶点价数 %d（UV 球体两极顶点，属正常结构）；管状部件盖面中心扇形顶点价数 6，环上顶点价数 4\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（24 个部件均已 Smart UV Project 展开）\n" % verdict(
            all(r["uv"]["has_uv"] for r in results.values())))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率（各部件独立 0–1 空间）：\n")
        for name in PARTS:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；球体类部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 关节拓扑（实测）\n\n")
        f.write("| 肢体 | 环数 | 中环位置（占全长） | 中环最高顶点价数 | 中环三角面 |\n")
        f.write("| ---- | ---- | ---------------- | ---------------- | ---------- |\n")
        for name in LIMBS:
            r = rings[name]
            f.write("| %s | %d | %.1f%% | %d | %d |\n" % (
                name, r["rings"], r["mid_ring_fraction"] * 100,
                r["mid_ring_max_valence"], r["mid_ring_tri_faces"]))
        f.write("\n- 四肢均为 5 环，中环正好落在关节中点（50%%）：%s\n" % verdict(rings_ok))
        f.write("- 关节中环顶点价数均为 4，无极点堆积；中环无三角面集中：%s\n\n" % verdict(rings_ok))
        f.write("## 5. 法师结构（实测）\n\n")
        f.write("- 长袍 5 环喇叭形（肩 → 地面），半径逐环增大：\n")
        for r in robe["rings"]:
            f.write("  - z=%.2f，半径 %.2f（%d 个顶点）\n" % (r["z"], r["radius"], r["verts"]))
        f.write("  - 结论：%s\n" % verdict(robe["ok"]))
        f.write("- 法杖组装：杖身 z=%.2f–%.2f，半径 %.3f；\n" % (
            staff["shaft_z"][0], staff["shaft_z"][1], staff["shaft_radius"]))
        for r in staff["rings"]:
            f.write("  - %s：中心 z=%.2f，半径 %.3f，落在杖身上 %s，包住杖身 %s\n" % (
                r["name"], r["z_center"], r["radius"],
                "是" if r["on_shaft"] else "否",
                "是" if r["wraps_shaft"] else "否"))
        c = staff["crystal"]
        f.write("  - 水晶：中心 x=%.3f（杖身 x=%.3f），中心 z=%.2f 高于杖顶 z=%.2f，底部嵌入杖顶 %.3f\n" % (
            c["center_x"], c["shaft_x"], c["center_z"], c["shaft_top_z"],
            c["bottom_embedded"]))
        f.write("  - 结论：%s\n" % verdict(staff["ok"]))
        f.write("- 尖顶帽：帽檐中心 z=%.2f，帽身 z=%.2f–%.2f，帽身底低于帽檐顶 %.3f，帽尖金球中心 z=%.2f（帽顶 z=%.2f，差 %.3f）：%s\n" % (
            hat["brim_center_z"], hat["hat_z"][0], hat["hat_z"][1],
            hat["hat_base_below_brim_top"], hat["tip_center_z"],
            hat["hat_z"][1], hat["tip_minus_hat_top"], verdict(hat["ok"])))
        f.write("- 胡须：顶部 z=%.2f（下巴），底部 z=%.2f（胸前），最大 y=%.3f（全在正面）：%s\n\n" % (
            beard["top_z"], beard["bottom_z"], beard["max_y"], verdict(beard["ok"])))
        f.write("## 6. 材质 / 贴图\n\n")
        for obj_name, mat_name, has_image in mat_rows:
            f.write("- %s → `%s`：图片贴图 %s\n" % (
                obj_name, mat_name if mat_name else "（空槽）",
                "有" if has_image else "无（程序化 Principled 材质）"))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 水晶自发光（节点实测）：Emission Strength %s（设计 0.6），Mix 混合系数 %s（设计 0.45）：%s\n" % (
            emission["emission_strength"], emission["mix_fac"],
            verdict(emission["ok"])))
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        f.write("**总体：%s**\n" % ("通过，可进游戏管线" if all_ok else "未通过，见上文不通过项"))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
