# -*- coding: utf-8 -*-
"""027 资产质检：对 025 低模战斧做真实 mesh 检查（拓扑/法线/UV/材质），
并实测战斧特有结构：斧柄渐细、握把包覆、斧底帽落地、斧头座贯穿、
斧刃扇形轮廓与斧头座交叠、刃口外凸开刃、顶楔坐于柄顶、
六种材质节点值（金属度/粗糙度/底色）。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 027-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "025-lowpoly-battleaxe.blend")
UV_JSON = os.path.join(ROOT, "scenes", "027-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "027-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "027-asset-qa-checklist.md")

# axe parts only (Ground / lights / camera are scene dressing)
PARTS = ["Haft", "Grip", "Pommel", "Socket", "Blade", "CuttingEdge",
         "TopWedge"]
# Design: no N-gons anywhere. Cylinder caps are triangle fans,
# boxes are 6 quads, blade front/back faces are centroid fans.
EXPECTED_NGONS = {}


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


def check_haft(parts):
    """Haft: 8-sided tapered cylinder, bottom radius 0.045 at z=0.00,
    top radius 0.035 at z=1.55, height 1.55."""
    haft = next(o for o in parts if o.name == "Haft")
    rows = ring_radii(haft)
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(haft)
    row = {"rings": rows, "z_min": zmin, "z_max": zmax,
           "height": round(zmax - zmin, 3)}
    ok = (len(rows) == 2
          and abs(rows[0]["radius"] - 0.045) < 0.001
          and abs(rows[1]["radius"] - 0.035) < 0.001
          and abs(zmin - 0.0) < 0.001 and abs(zmax - 1.55) < 0.001
          and rows[0]["radius"] > rows[1]["radius"])
    row["ok"] = bool(ok)
    return row


def check_grip(parts):
    """Grip: leather wrap around the haft near the bottom, z 0.02-0.30,
    radius ~0.05 > haft radius at that height (~0.044), centered on axis."""
    grip = next(o for o in parts if o.name == "Grip")
    haft = next(o for o in parts if o.name == "Haft")
    rows = ring_radii(grip)
    _, _, _, _, gzmin, gzmax = world_range(grip)
    _, _, _, _, hzmin, hzmax = world_range(haft)
    cx = sum(v.co.x for v in grip.data.vertices) / len(grip.data.vertices)
    cy = sum(v.co.y for v in grip.data.vertices) / len(grip.data.vertices)
    # haft radius at grip mid height (linear taper 0.045 -> 0.035 over 1.55)
    zmid = (gzmin + gzmax) / 2.0
    haft_r_at = 0.045 - (0.045 - 0.035) * (zmid / 1.55)
    row = {"rings": rows, "z": (gzmin, gzmax),
           "center_xy": (round(cx, 3), round(cy, 3)),
           "haft_radius_at_mid": round(haft_r_at, 3),
           "wraps_haft": bool(all(r["radius"] > haft_r_at + 0.003
                                  for r in rows))}
    ok = (hzmin - 0.001 <= gzmin and gzmax <= hzmax + 0.001
          and abs(cx) < 0.001 and abs(cy) < 0.001
          and row["wraps_haft"])
    row["ok"] = bool(ok)
    return row


def check_pommel(parts):
    """Pommel: iron cap at the very bottom, z 0.00-0.06, radius ~0.05,
    sits on the ground (min z = 0)."""
    pommel = next(o for o in parts if o.name == "Pommel")
    rows = ring_radii(pommel)
    _, _, _, _, zmin, zmax = world_range(pommel)
    row = {"rings": rows, "z": (zmin, zmax)}
    ok = (abs(zmin - 0.0) < 0.001 and abs(zmax - 0.06) < 0.001
          and all(abs(r["radius"] - 0.05) < 0.006 for r in rows))
    row["ok"] = bool(ok)
    return row


def check_socket(parts):
    """Socket: steel block 0.22x0.13x0.30, x -0.09..0.13, z 1.09-1.39.
    The haft (x=0, y=0) must pass through it, and the blade root (x=0)
    must start inside its x range."""
    socket = next(o for o in parts if o.name == "Socket")
    haft = next(o for o in parts if o.name == "Haft")
    blade = next(o for o in parts if o.name == "Blade")
    sxmin, sxmax, symin, symax, szmin, szmax = world_range(socket)
    _, _, _, _, hzmin, hzmax = world_range(haft)
    bxmin, bxmax, _, _, bzmin, bzmax = world_range(blade)
    row = {"bbox_x": (sxmin, sxmax), "bbox_y": (symin, symax),
           "bbox_z": (szmin, szmax),
           "size": (round(sxmax - sxmin, 3), round(symax - symin, 3),
                    round(szmax - szmin, 3)),
           "haft_through": bool(sxmin < 0 < sxmax and symin < 0 < symax
                                and hzmin < szmin and szmax < hzmax),
           "blade_root_inside": bool(sxmin <= bxmin <= sxmax),
           "blade_z_overlap": round(min(szmax, bzmax) - max(szmin, bzmin), 3)}
    ok = (abs(sxmin - (-0.09)) < 0.001 and abs(sxmax - 0.13) < 0.001
          and abs(szmin - 1.09) < 0.001 and abs(szmax - 1.39) < 0.001
          and row["haft_through"] and row["blade_root_inside"]
          and row["blade_z_overlap"] > 0.2)
    row["ok"] = bool(ok)
    return row


def check_blade(parts):
    """Blade: fan-shaped extruded hexagon, x 0.00-0.52, z 0.88-1.56,
    thickness 0.08 (y +-0.04). Front/back faces are centroid fans
    (12 tris), sides are 6 quads. Must pass through the socket zone
    and extend beyond it top and bottom."""
    blade = next(o for o in parts if o.name == "Blade")
    socket = next(o for o in parts if o.name == "Socket")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(blade)
    _, _, _, _, szmin, szmax = world_range(socket)
    tris = sum(1 for p in blade.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for p in blade.data.polygons if len(p.vertices) == 4)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "tris": tris, "quads": quads,
           "extends_above_socket": round(zmax - szmax, 3),
           "extends_below_socket": round(szmin - zmin, 3)}
    ok = (abs(xmin - 0.0) < 0.001 and abs(xmax - 0.52) < 0.001
          and abs(zmin - 0.88) < 0.001 and abs(zmax - 1.56) < 0.001
          and abs(ymin - (-0.04)) < 0.001 and abs(ymax - 0.04) < 0.001
          and tris == 12 and quads == 6
          and row["extends_above_socket"] > 0.1
          and row["extends_below_socket"] > 0.1)
    row["ok"] = bool(ok)
    return row


def check_edge(parts):
    """CuttingEdge: bright steel strip, x 0.50-0.56 (protrudes 0.04 past
    the blade's far edge at 0.52), y +-0.05 (thicker than the blade's
    +-0.04), z 1.01-1.43 inside the blade's z span."""
    edge = next(o for o in parts if o.name == "CuttingEdge")
    blade = next(o for o in parts if o.name == "Blade")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(edge)
    bxmin, bxmax, bymin, bymax, bzmin, bzmax = world_range(blade)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax),
           "protrudes_past_blade": round(xmax - bxmax, 3),
           "thicker_than_blade": round((ymax - ymin) - (bymax - bymin), 3)}
    ok = (abs(xmin - 0.50) < 0.001 and abs(xmax - 0.56) < 0.001
          and abs(zmin - 1.01) < 0.001 and abs(zmax - 1.43) < 0.001
          and row["protrudes_past_blade"] > 0.0
          and row["thicker_than_blade"] > 0.0
          and bzmin < zmin and zmax < bzmax)
    row["ok"] = bool(ok)
    return row


def check_wedge(parts):
    """TopWedge: wooden wedge on top of the haft, z 1.55-1.62, bottom
    flush with the haft top (z=1.55), centered on the axis."""
    wedge = next(o for o in parts if o.name == "TopWedge")
    haft = next(o for o in parts if o.name == "Haft")
    xmin, xmax, ymin, ymax, zmin, zmax = world_range(wedge)
    _, _, _, _, _, hzmax = world_range(haft)
    row = {"bbox_x": (xmin, xmax), "bbox_y": (ymin, ymax),
           "bbox_z": (zmin, zmax), "haft_top_z": hzmax,
           "bottom_minus_haft_top": round(zmin - hzmax, 3)}
    ok = (abs(zmin - 1.55) < 0.001 and abs(zmax - 1.62) < 0.001
          and abs(row["bottom_minus_haft_top"]) < 0.001
          and abs((xmin + xmax) / 2.0) < 0.001
          and abs((ymin + ymax) / 2.0) < 0.001)
    row["ok"] = bool(ok)
    return row


# design values from 025 build script: (metallic, roughness, base color)
DESIGN_MATS = {
    "Axe_Steel": (0.85, 0.35, (0.30, 0.31, 0.34)),
    "Axe_EdgeSteel": (0.90, 0.15, (0.62, 0.64, 0.68)),
    "Axe_Wood": (0.00, 0.80, (0.45, 0.28, 0.14)),
    "Axe_WoodDark": (0.00, 0.85, (0.30, 0.18, 0.09)),
    "Axe_Leather": (0.00, 0.90, (0.20, 0.12, 0.08)),
    "Axe_Iron": (0.70, 0.50, (0.16, 0.16, 0.18)),
}


def check_materials(parts):
    """Read Principled BSDF node values, not names."""
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
    missing_design = [n for n in DESIGN_MATS if n not in used]
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

    haft = check_haft(parts)
    print("QA_HAFT:", haft)
    grip = check_grip(parts)
    print("QA_GRIP:", grip)
    pommel = check_pommel(parts)
    print("QA_POMMEL:", pommel)
    socket = check_socket(parts)
    print("QA_SOCKET:", socket)
    blade = check_blade(parts)
    print("QA_BLADE:", blade)
    edge = check_edge(parts)
    print("QA_EDGE:", edge)
    wedge = check_wedge(parts)
    print("QA_WEDGE:", wedge)
    mats = check_materials(parts)
    print("QA_MATERIALS:", mats)

    structure = {"haft": haft, "grip": grip, "pommel": pommel,
                 "socket": socket, "blade": blade, "edge": edge,
                 "wedge": wedge}
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
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and tot["boundary_edges"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and structure_ok and mats["all_ok"])

    summary = {
        "asset": "025-lowpoly-battleaxe",
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
        f.write("# 027 资产质检单：低模战斧（025）\n\n")
        f.write("被检资产：`scenes/025-lowpoly-battleaxe.blend`（7 个战斧部件，不含场景地面/灯光/相机）\n")
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
        f.write("- N-gon：共 %d 个（设计值 0，圆柱盖面为三角扇、斧刃正反面为形心三角扇）：%s\n" % (
            tot["ngons"], verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 闭合网格（无边界边）：%s\n" % verdict(tot["boundary_edges"] == 0))
        f.write("- 最高顶点价数 %d（盖面中心扇形顶点价数 8，环上顶点价数 4；斧刃形心顶点价数 6）\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（7 个部件均已 Smart UV Project 展开）\n" % verdict(
            all(r["uv"]["has_uv"] for r in results.values())))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率（各部件独立 0–1 空间）：\n")
        for name in PARTS:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 战斧结构（实测）\n\n")
        f.write("- 斧柄渐细：底环 z=%.2f 半径 %.3f，顶环 z=%.2f 半径 %.3f，全高 %.2f（设计 0.045 → 0.035，高 1.55）：%s\n" % (
            haft["rings"][0]["z"], haft["rings"][0]["radius"],
            haft["rings"][1]["z"], haft["rings"][1]["radius"],
            haft["height"], verdict(haft["ok"])))
        f.write("- 握把包覆：z=%.2f–%.2f 在斧柄跨度内，中心 (%.3f, %.3f) 在轴线上，两环半径 %.3f / %.3f 均大于该高度斧柄半径 %.3f：%s\n" % (
            grip["z"][0], grip["z"][1], grip["center_xy"][0],
            grip["center_xy"][1], grip["rings"][0]["radius"],
            grip["rings"][1]["radius"], grip["haft_radius_at_mid"],
            verdict(grip["ok"])))
        f.write("- 斧底帽落地：z=%.2f–%.2f，底面 z=0.00 贴地，两环半径 %.3f / %.3f：%s\n" % (
            pommel["z"][0], pommel["z"][1], pommel["rings"][0]["radius"],
            pommel["rings"][1]["radius"], verdict(pommel["ok"])))
        f.write("- 斧头座：尺寸 %.3f×%.3f×%.3f（设计 0.22×0.13×0.30），x %.2f–%.2f，z %.2f–%.2f；斧柄穿过 %s，斧刃根部 x=%.2f 落在座内 %s，斧刃与座 z 向交叠 %.3f：%s\n" % (
            socket["size"][0], socket["size"][1], socket["size"][2],
            socket["bbox_x"][0], socket["bbox_x"][1],
            socket["bbox_z"][0], socket["bbox_z"][1],
            "是" if socket["haft_through"] else "否",
            blade["bbox_x"][0],
            "是" if socket["blade_root_inside"] else "否",
            socket["blade_z_overlap"], verdict(socket["ok"])))
        f.write("- 斧刃：x %.2f–%.2f，z %.2f–%.2f，y ±%.2f（厚 0.08）；三角面 %d（正反面形心扇）+ 四边面 %d（侧面）；上下各超出斧头座 %.3f / %.3f：%s\n" % (
            blade["bbox_x"][0], blade["bbox_x"][1],
            blade["bbox_z"][0], blade["bbox_z"][1],
            blade["bbox_y"][1], blade["tris"], blade["quads"],
            blade["extends_above_socket"], blade["extends_below_socket"],
            verdict(blade["ok"])))
        f.write("- 刃口开刃：x %.2f–%.2f，超出斧刃最远边 %.3f，比斧刃厚 %.3f（y ±%.2f 对 ±%.2f），z %.2f–%.2f 在斧刃跨度内：%s\n" % (
            edge["bbox_x"][0], edge["bbox_x"][1],
            edge["protrudes_past_blade"], edge["thicker_than_blade"],
            edge["bbox_y"][1], blade["bbox_y"][1],
            edge["bbox_z"][0], edge["bbox_z"][1], verdict(edge["ok"])))
        f.write("- 顶楔：z %.2f–%.2f，底面与斧柄顶 z=%.2f 齐平（差 %.3f），x/y 居中：%s\n\n" % (
            wedge["bbox_z"][0], wedge["bbox_z"][1], wedge["haft_top_z"],
            wedge["bottom_minus_haft_top"], verdict(wedge["ok"])))
        f.write("## 5. 材质 / 贴图\n\n")
        for obj_name, mat_name, has_image in mat_rows:
            f.write("- %s → `%s`：图片贴图 %s\n" % (
                obj_name, mat_name if mat_name else "（空槽）",
                "有" if has_image else "无（程序化 Principled 材质）"))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 材质节点值（Principled BSDF 实测 vs 设计值）：\n")
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
        f.write("**总体：%s**\n" % ("通过，可进游戏管线" if all_ok else "未通过，见上文不通过项"))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
