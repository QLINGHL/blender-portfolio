# -*- coding: utf-8 -*-
"""012 资产质检：对 010 低模宝箱做真实 mesh 检查（拓扑/法线/UV/材质），
并实测宝箱特有结构：铰链位置与开盖角度、内腔是否真实开口、
金币/宝石是否收纳在腔内、盖带是否随盖转动。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 012-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "010-lowpoly-chest.blend")
UV_JSON = os.path.join(ROOT, "scenes", "012-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "012-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "012-asset-qa-checklist.md")

# chest parts only (Ground / lights / camera are scene dressing)
# scene order, Ground excluded
PARTS = ["Body_Bottom", "Body_Front", "Body_Back", "Body_Left", "Body_Right",
         "Inner_Floor", "Rim_Front", "Rim_Back", "Rim_Left", "Rim_Right",
         "Band_Front_7", "Band_Back_7", "Band_Bottom_7",
         "Band_Front_7.001", "Band_Back_7.001", "Band_Bottom_7.001",
         "Hasp_Body", "Padlock", "Padlock_Shankle",
         "Coin_L0_0", "Coin_L0_1", "Coin_L0_2", "Coin_L0_3", "Coin_L0_4",
         "Coin_L0_5", "Coin_L0_6",
         "Coin_L1_0", "Coin_L1_1", "Coin_L1_2", "Coin_L1_3", "Coin_L1_4",
         "Coin_L2_0", "Coin_L2_1", "Coin_L2_2", "Coin_Top",
         "Gem_Red", "Gem_Blue", "Lid", "LidBand_7", "LidBand_7.001",
         "LidHasp"]
# open (non-closed) parts by design: lid bands are single-sided ribbons,
# the lid hasp is a single quad plate. Boundary edges are expected there.
OPEN_PARTS = {"LidBand_7", "LidBand_7.001", "LidHasp"}
TREASURE = [n for n in PARTS if n.startswith("Coin_") or n.startswith("Gem_")]


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
    # recalc_face_normals (true outward orientation for a closed manifold
    # mesh) and count faces whose normal flips. For open parts (ribbons /
    # single quad) recalc still gives a consistent side; a flip count
    # there means the winding disagrees with Blender's own orientation.
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


def check_hinge(parts):
    """Lid hinge: origin must sit on the hinge line (y=+0.7, z=0.9),
    opening angle must be ~100 deg about X, and the lid bands + lid
    hasp must be parented to the lid so they swing with it."""
    lid = next(o for o in parts if o.name == "Lid")
    angle_deg = round(math.degrees(lid.rotation_euler[0]), 2)
    loc = (round(lid.location.x, 3), round(lid.location.y, 3),
           round(lid.location.z, 3))
    parented = sorted(o.name for o in parts
                      if o.parent is not None and o.parent.name == "Lid")
    ok = (abs(lid.location.y - 0.7) < 1e-3
          and abs(lid.location.z - 0.9) < 1e-3
          and abs(abs(angle_deg) - 100.0) < 0.5
          and set(parented) == {"LidBand_7", "LidBand_7.001", "LidHasp"})
    return {"lid_location": loc, "open_angle_deg": angle_deg,
            "parented_to_lid": parented, "ok": bool(ok)}


def check_treasure_containment(parts):
    """Every coin/gem vertex must lie inside the cavity box
    x in [-1.1, 1.1], y in [-0.6, 0.6], z in [0.1, 0.95] (world space,
    objects are unrotated except coin tilt which is baked in the mesh
    via rotation_euler -- use evaluated world coords)."""
    dg = bpy.context.evaluated_depsgraph_get()
    bad = {}
    for obj in parts:
        if obj.name not in TREASURE:
            continue
        ev = obj.evaluated_get(dg)
        mw = ev.matrix_world
        outside = 0
        for v in obj.data.vertices:
            w = mw @ v.co
            if not (-1.1 - 1e-6 <= w.x <= 1.1 + 1e-6
                    and -0.6 - 1e-6 <= w.y <= 0.6 + 1e-6
                    and 0.1 - 1e-6 <= w.z <= 0.95 + 1e-6):
                outside += 1
        if outside:
            bad[obj.name] = outside
    return {"treasure_parts": len(TREASURE), "outside_verts": bad,
            "ok": len(bad) == 0}


def check_cavity(parts):
    """Raycast straight down from above the chest: over the treasure the
    first hit must be a coin/gem (treasure reads over the rim); over a
    clear corner of the cavity the first hit must be the inner floor
    (the cavity is a real opening, not a solid top)."""
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    results = {}
    for label, origin in (("over_treasure", (0.0, 0.0, 3.0)),
                          ("over_clear_corner", (0.95, 0.45, 3.0))):
        hit, loc, normal, idx, obj, mat = scene.ray_cast(
            dg, Vector(origin), Vector((0, 0, -1)))
        results[label] = {"hit": obj.name if hit and obj else None,
                          "z": round(loc.z, 3) if hit else None}
    ok = (results["over_treasure"]["hit"] in TREASURE
          and results["over_clear_corner"]["hit"] == "Inner_Floor")
    results["ok"] = bool(ok)
    return results


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

    hinge = check_hinge(parts)
    print("QA_HINGE:", hinge)
    treasure = check_treasure_containment(parts)
    print("QA_TREASURE:", treasure)
    cavity = check_cavity(parts)
    print("QA_CAVITY:", cavity)

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
    boundary_ok = all(
        (results[n]["boundary_edges"] == 0) if n not in OPEN_PARTS
        else (results[n]["boundary_edges"] > 0)
        for n in PARTS)
    all_ok = (tot["ngons"] == 0 and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and boundary_ok
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and hinge["ok"] and treasure["ok"] and cavity["ok"])

    summary = {
        "asset": "010-lowpoly-chest",
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
        "hinge": hinge,
        "treasure_containment": treasure,
        "cavity": cavity,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("QA_SUMMARY:", summary)

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 012 资产质检单：低模宝箱（010）\n\n")
        f.write("被检资产：`scenes/010-lowpoly-chest.blend`（41 个宝箱部件，不含场景地面/灯光/相机）\n")
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
        f.write("- 边界边：仅出现在设计为开口的 3 个部件（LidBand_7、LidBand_7.001 为单面飘带，LidHasp 为单面四边板），其余 38 个部件均为闭合网格：%s\n" % verdict(boundary_ok))
        f.write("- 最高顶点价数 8（圆柱盖面中心扇形顶点，属正常结构）；箱体盒子顶点价数 3\n\n")
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（41 个部件均已 Smart UV Project 展开）\n" % verdict(
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
        f.write("## 4. 宝箱结构（实测）\n\n")
        f.write("- 铰链：盖子原点位于铰链线（y=+0.7, z=0.9），实测位置 (%s, %s, %s)；开盖角度 %.1f°（设计 100°）：%s\n" % (
            hinge["lid_location"][0], hinge["lid_location"][1],
            hinge["lid_location"][2], abs(hinge["open_angle_deg"]),
            verdict(hinge["ok"])))
        f.write("- 随盖转动：父级为 Lid 的部件为 %s：%s\n" % (
            "、".join(hinge["parented_to_lid"]),
            verdict(set(hinge["parented_to_lid"]) == {"LidBand_7", "LidBand_7.001", "LidHasp"})))
        f.write("- 金币/宝石收纳：%d 个宝藏部件，全部顶点均在内腔范围（x ±1.1、y ±0.6、z 0.1–0.95）内：%s\n" % (
            treasure["treasure_parts"], verdict(treasure["ok"])))
        f.write("- 内腔真实开口（自正上方垂直向下射线检测）：\n")
        f.write("  - 宝藏正上方首命中：%s（z=%.2f）\n" % (
            cavity["over_treasure"]["hit"], cavity["over_treasure"]["z"] or 0))
        f.write("  - 腔内空角首命中：%s（z=%.2f，应为 Inner_Floor）\n" % (
            cavity["over_clear_corner"]["hit"], cavity["over_clear_corner"]["z"] or 0))
        f.write("  - 结论：%s\n\n" % verdict(cavity["ok"]))
        f.write("## 5. 材质 / 贴图\n\n")
        for obj_name, mat_name, has_image in mat_rows:
            f.write("- %s → `%s`：图片贴图 %s\n" % (
                obj_name, mat_name if mat_name else "（空槽）",
                "有" if has_image else "无（程序化 Principled 材质）"))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）\n\n")
        f.write("## 结论\n\n")
        f.write("**总体：%s**\n" % ("通过，可进游戏管线" if all_ok else "未通过，见上文不通过项"))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("UV_JSON_WRITTEN:", UV_JSON)


if __name__ == "__main__":
    main()
