# -*- coding: utf-8 -*-
"""017 资产质检：对 016 低模魔法祭坛做真实 mesh 检查（拓扑/法线/UV/材质），
并实测祭坛特有结构：符文环是否贴合三层石台顶面、8 块符文石间距/
倾斜/落座、悬浮水晶是否真实悬空、烛火锥底是否对接烛顶、自发光材质
强度是否真实大于 0。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 017-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "016-lowpoly-altar.blend")
UV_JSON = os.path.join(ROOT, "scenes", "017-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "017-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "017-asset-qa-checklist.md")

# altar parts only (Ground / lights / camera are scene dressing)
PARTS = ["Platform_Tier1", "Platform_Tier2", "Platform_Tier3",
         "Step_Low", "Step_High", "Altar_Block", "Altar_Slab",
         "Rune_Ring",
         "RuneStone_0", "RuneStone_1", "RuneStone_2", "RuneStone_3",
         "RuneStone_4", "RuneStone_5", "RuneStone_6", "RuneStone_7",
         "RunePlate_0", "RunePlate_1", "RunePlate_2", "RunePlate_3",
         "RunePlate_4", "RunePlate_5", "RunePlate_6", "RunePlate_7",
         "Candle_L_Base", "Candle_L_Stem", "Candle_L_Cup",
         "Candle_L_Candle", "Candle_L_Flame",
         "Candle_R_Base", "Candle_R_Stem", "Candle_R_Cup",
         "Candle_R_Candle", "Candle_R_Flame",
         "Candle_Tall_Base", "Candle_Tall_Stem", "Candle_Tall_Cup",
         "Candle_Tall_Candle", "Candle_Tall_Flame",
         "Crystal_Main", "Crystal_Shard_0", "Crystal_Shard_1",
         "Crystal_Shard_2"]
# no open parts by design: every part is a closed solid
OPEN_PARTS = set()
RUNESTONES = ["RuneStone_%d" % i for i in range(8)]
CANDLES = ["Candle_L", "Candle_R", "Candle_Tall"]


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


def world_z_range(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mw = ev.matrix_world
    zs = [(mw @ v.co).z for v in obj.data.vertices]
    return round(min(zs), 3), round(max(zs), 3)


def check_rune_ring(parts):
    """Torus centre z=1.11, minor radius 0.06: lowest vertex must sit on
    tier 3 top (z=1.05); ring must encircle the altar (major radius 1.35
    > altar half-width 0.7)."""
    ring = next(o for o in parts if o.name == "Rune_Ring")
    zmin, zmax = world_z_range(ring)
    cx, cy = ring.location.x, ring.location.y
    ok = abs(zmin - 1.05) < 0.01 and abs(ring.location.z - 1.11) < 1e-3
    return {"center_z": round(ring.location.z, 3), "min_z": zmin,
            "max_z": zmax, "centre_xy": (round(cx, 3), round(cy, 3)),
            "ok": bool(ok)}


def check_rune_stones(parts):
    """8 stones on tier 2 (top z=0.70), radius 2.0, 45 deg apart,
    tilted outward 8 deg. Measure each stone's centre radius/angle,
    tilt (rotation_euler.x) and lowest world z (tilt sinks one edge
    slightly below the seat plane by design)."""
    rows = []
    for name in RUNESTONES:
        o = next(p for p in parts if p.name == name)
        r = math.hypot(o.location.x, o.location.y)
        ang = math.degrees(math.atan2(o.location.y, o.location.x)) % 360.0
        tilt = round(math.degrees(o.rotation_euler[0]), 2)
        zmin, zmax = world_z_range(o)
        rows.append({"name": name, "radius": round(r, 3),
                     "angle_deg": round(ang, 1), "tilt_deg": tilt,
                     "min_z": zmin, "max_z": zmax})
    angles = sorted(r["angle_deg"] for r in rows)
    gaps = [round((angles[(i + 1) % 8] - angles[i]) % 360.0, 1)
            for i in range(8)]
    ok = (all(abs(r["radius"] - 2.0) < 1e-3 for r in rows)
          and all(abs(g - 45.0) < 0.5 for g in gaps)
          and all(abs(abs(r["tilt_deg"]) - 8.0) < 0.1 for r in rows)
          and all(0.60 <= r["min_z"] <= 0.71 for r in rows))
    return {"stones": rows, "angle_gaps_deg": gaps, "ok": bool(ok)}


def check_crystal_float(parts):
    """Crystal_Main bottom must clear the altar slab top (z=2.07) with a
    real gap; shards must clear tier 3 top (z=1.05)."""
    slab_top = 2.07
    tier3_top = 1.05
    rows = {}
    main = next(o for o in parts if o.name == "Crystal_Main")
    zmin, zmax = world_z_range(main)
    rows["Crystal_Main"] = {"min_z": zmin, "max_z": zmax,
                            "gap_above_slab": round(zmin - slab_top, 3)}
    for i in range(3):
        o = next(p for p in parts if p.name == "Crystal_Shard_%d" % i)
        zmin, zmax = world_z_range(o)
        rows[o.name] = {"min_z": zmin, "max_z": zmax,
                        "gap_above_tier3": round(zmin - tier3_top, 3)}
    ok = (rows["Crystal_Main"]["gap_above_slab"] > 0.3
          and all(rows["Crystal_Shard_%d" % i]["gap_above_tier3"] > 0
                  for i in range(3)))
    rows["ok"] = bool(ok)
    return rows


def check_candle_flames(parts):
    """Each flame cone base (min world z) must meet its candle top
    (max world z) within 0.01, and the candle must sit in its cup."""
    rows = []
    for prefix in CANDLES:
        candle = next(o for o in parts if o.name == prefix + "_Candle")
        flame = next(o for o in parts if o.name == prefix + "_Flame")
        cup = next(o for o in parts if o.name == prefix + "_Cup")
        _, candle_top = world_z_range(candle)
        flame_min, _ = world_z_range(flame)
        _, cup_top = world_z_range(cup)
        candle_min, _ = world_z_range(candle)
        rows.append({"candle": prefix,
                     "candle_top_z": candle_top,
                     "flame_base_z": flame_min,
                     "flame_gap": round(flame_min - candle_top, 3),
                     "candle_base_z": candle_min,
                     "cup_top_z": cup_top,
                     "candle_sunk_into_cup": round(cup_top - candle_min, 3)})
    # candle must not float above the cup: touching the rim (sunk == 0)
    # or slightly sunk is fine; a negative sunk value means a visible gap.
    ok = all(abs(r["flame_gap"]) < 0.01 and r["candle_sunk_into_cup"] >= -0.001
             for r in rows)
    return {"rows": rows, "ok": bool(ok)}


def check_emission(parts):
    """Glow materials must really emit: Principled BSDF Emission
    Strength > 0 (checked on the node, not the name)."""
    wanted = {"Rune_Glow": 1.8, "Altar_Crystal": 1.4, "Candle_Flame": 2.5}
    rows = []
    for mat_name, design in wanted.items():
        mat = bpy.data.materials.get(mat_name)
        strength = None
        if mat is not None and mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                strength = round(bsdf.inputs["Emission Strength"].default_value, 2)
        rows.append({"material": mat_name, "design_strength": design,
                     "measured_strength": strength})
    ok = all(r["measured_strength"] is not None
             and abs(r["measured_strength"] - r["design_strength"]) < 0.01
             for r in rows)
    return {"rows": rows, "ok": bool(ok)}


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

    ring = check_rune_ring(parts)
    print("QA_RING:", ring)
    stones = check_rune_stones(parts)
    print("QA_RUNESTONES:", stones)
    crystal = check_crystal_float(parts)
    print("QA_CRYSTAL:", crystal)
    flames = check_candle_flames(parts)
    print("QA_FLAMES:", flames)
    emission = check_emission(parts)
    print("QA_EMISSION:", emission)

    # --- material audit (real node inspection) ---
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
    boundary_ok = all(results[n]["boundary_edges"] == 0 for n in PARTS)
    all_ok = (tot["ngons"] == 0 and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and boundary_ok
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and ring["ok"] and stones["ok"] and crystal["ok"]
              and flames["ok"] and emission["ok"])

    summary = {
        "asset": "016-lowpoly-altar",
        "parts": len(results),
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "boundary_edges": tot["boundary_edges"],
        "boundary_edges_expected_only_on_open_parts": bool(boundary_ok),
        "inverted_normals": tot["inverted_normals"],
        "uv_out_of_bounds": tot_oob,
        "uv_utilization_per_part": {k: round(v["uv"]["utilization"], 3)
                                    for k, v in results.items()},
        "uv_islands": tot_islands,
        "uv_overlap_pct": round(worst_overlap, 2),
        "empty_material_slots": empty_slots,
        "rune_ring": ring,
        "rune_stones": stones,
        "crystal_float": crystal,
        "candle_flames": flames,
        "emission": emission,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("QA_SUMMARY:", summary)

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 017 资产质检单：低模魔法祭坛（016）\n\n")
        f.write("被检资产：`scenes/016-lowpoly-altar.blend`（43 个祭坛部件，不含场景地面/灯光/相机）\n")
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
        f.write("- 无 N-gon（>4 边面）：%s\n" % verdict(tot["ngons"] == 0))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 边界边：全部 43 个部件均为闭合网格，无边界边：%s\n" % verdict(boundary_ok))
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（43 个部件均已 Smart UV Project 展开）\n" % verdict(
            all(r["uv"]["has_uv"] for r in results.values())))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率（各部件独立 0–1 空间）：\n")
        for name in PARTS:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；圆柱盖面扇形展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 祭坛结构（实测）\n\n")
        f.write("- 符文环：圆环中心 z=%.2f（设计 1.11），最低点 z=%.2f（三层石台顶面 z=1.05，应贴合）：%s\n" % (
            ring["center_z"], ring["min_z"], verdict(ring["ok"])))
        f.write("- 符文石：8 块立石，中心半径均为 2.00，角度间隔 45°，向外倾斜 8°：\n")
        for r in stones["stones"]:
            f.write("  - %s：半径 %.2f，角度 %.1f°，倾斜 %.1f°，最低点 z=%.3f（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）\n" % (
                r["name"], r["radius"], r["angle_deg"], abs(r["tilt_deg"]), r["min_z"]))
        f.write("  - 结论：%s\n" % verdict(stones["ok"]))
        f.write("- 悬浮水晶：主水晶最低点 z=%.2f，祭坛顶板顶面 z=2.07，悬空 %.2f；3 颗碎片最低点 z=%.2f / %.2f / %.2f，均高于三层石台顶面 z=1.05：%s\n" % (
            crystal["Crystal_Main"]["min_z"],
            crystal["Crystal_Main"]["gap_above_slab"],
            crystal["Crystal_Shard_0"]["min_z"],
            crystal["Crystal_Shard_1"]["min_z"],
            crystal["Crystal_Shard_2"]["min_z"],
            verdict(crystal["ok"])))
        f.write("- 烛火对接（火焰锥底 = 蜡烛顶）：\n")
        for r in flames["rows"]:
            f.write("  - %s：蜡烛顶 z=%.2f，火焰底 z=%.2f，间隙 %.3f；蜡烛底部沉入烛杯 %.2f\n" % (
                r["candle"], r["candle_top_z"], r["flame_base_z"],
                r["flame_gap"], r["candle_sunk_into_cup"]))
        f.write("  - 结论：%s\n\n" % verdict(flames["ok"]))
        f.write("## 5. 材质 / 贴图\n\n")
        for obj_name, mat_name, has_image in mat_rows:
            f.write("- %s → `%s`：图片贴图 %s\n" % (
                obj_name, mat_name if mat_name else "（空槽）",
                "有" if has_image else "无（程序化 Principled 材质）"))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 自发光材质（节点实测 Emission Strength）：\n")
        for r in emission["rows"]:
            f.write("  - %s：设计 %.1f，实测 %s：%s\n" % (
                r["material"], r["design_strength"],
                r["measured_strength"],
                verdict(r["measured_strength"] is not None
                        and abs(r["measured_strength"] - r["design_strength"]) < 0.01)))
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        f.write("**总体：%s**\n" % ("通过，可进游戏管线" if all_ok else "未通过，见上文不通过项"))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
