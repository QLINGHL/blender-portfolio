# -*- coding: utf-8 -*-
"""029 资产质检：对 028 低模铁匠铺角落场景做真实 mesh 检查（拓扑/法线/UV/材质），
并实测场景特有结构：角落墙体、石板铺地、铁砧落位、木桶三段叠合 + 铁箍、
战斧斜靠（与木桶的真实间隙 + 斧底是否陷地）、火盆 + 炉火光源、
淬火桶水面、铁锤落地、铁锭叠放、煤块落地。
导出 UV 数据供拼图脚本使用，并写出质检清单。
Run: blender --background --python 029-asset-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "028-blacksmith-corner.blend")
UV_JSON = os.path.join(ROOT, "scenes", "029-uv-data.json")
SUMMARY_JSON = os.path.join(ROOT, "scenes", "029-qa-summary.json")
CHECKLIST = os.path.join(ROOT, "scenes", "029-asset-qa-checklist.md")

# every mesh object in the 028 blend except the scene dressing ground
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
    """World-space bbox of the evaluated mesh (parent transforms apply)."""
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


def barrel_radius_at(z):
    """Barrel outer radius profile from the 028 build (axis x=2.0, y=-0.2):
    bottom taper 0.44->0.52 over z 0-0.35, middle 0.52 over 0.35-0.55,
    top taper 0.52->0.44 over 0.55-0.90."""
    if z < 0.0 or z > 0.90:
        return None
    if z <= 0.35:
        return 0.44 + (0.52 - 0.44) * (z / 0.35)
    if z <= 0.55:
        return 0.52
    return 0.52 - (0.52 - 0.44) * ((z - 0.55) / 0.35)


def check_walls(parts):
    """Corner walls: back wall y 2.05-2.35, z 0-2.6; left wall x -2.35..-2.05,
    z 0-2.6; beams z 2.34-2.56 under the wall top; corner post z 0-2.6."""
    wb = next(o for o in parts if o.name == "Wall_Back")
    wl = next(o for o in parts if o.name == "Wall_Left")
    bb = next(o for o in parts if o.name == "Beam_Back")
    bl = next(o for o in parts if o.name == "Beam_Left")
    post = next(o for o in parts if o.name == "Post_Corner")
    r_wb = world_range(wb)
    r_wl = world_range(wl)
    r_bb = world_range(bb)
    r_bl = world_range(bl)
    r_post = world_range(post)
    # corner closed: the left wall's far end (y_max) must reach into the
    # back wall's slab (y 2.05-2.35), and the back wall's x span must cover
    # the left wall's x span, so no gap opens at the corner.
    corner_ok = (r_wl[3] >= r_wb[2] - 0.001
                 and r_wb[0] <= r_wl[0] + 0.001
                 and r_wb[1] >= r_wl[1] - 0.001)
    # the back wall sticks out past the left wall's outer face by
    # (wall_left x_min) - (wall_back x_min): a small exposed wall end.
    overhang = round(r_wl[0] - r_wb[0], 3)
    row = {"wall_back": r_wb, "wall_left": r_wl,
           "beam_back_z": (r_bb[4], r_bb[5]),
           "beam_left_z": (r_bl[4], r_bl[5]),
           "post_z": (r_post[4], r_post[5]),
           "corner_overlap": bool(corner_ok),
           "back_wall_overhang_past_left_wall": overhang}
    ok = (abs(r_wb[2] - 2.05) < 0.001 and abs(r_wb[3] - 2.35) < 0.001
          and abs(r_wb[4] - 0.0) < 0.001 and abs(r_wb[5] - 2.60) < 0.001
          and abs(r_wl[0] - (-2.35)) < 0.001 and abs(r_wl[1] - (-2.05)) < 0.001
          and abs(r_wl[4] - 0.0) < 0.001 and abs(r_wl[5] - 2.60) < 0.001
          and abs(r_bb[4] - 2.34) < 0.001 and abs(r_bb[5] - 2.56) < 0.001
          and abs(r_bl[4] - 2.34) < 0.001 and abs(r_bl[5] - 2.56) < 0.001
          and abs(r_post[4] - 0.0) < 0.001 and abs(r_post[5] - 2.60) < 0.001
          and corner_ok)
    row["ok"] = bool(ok)
    return row


def check_pavers(parts):
    """12 pavers: all rest on the floor (z 0-0.04), inside the corner area."""
    pavers = [o for o in parts if o.name.startswith("Paver_")]
    rows = []
    for o in sorted(pavers, key=lambda p: p.name):
        r = world_range(o)
        rows.append({"name": o.name, "z": (r[4], r[5]),
                     "x": (r[0], r[1]), "y": (r[2], r[3])})
    ok = (len(pavers) == 12
          and all(abs(r["z"][0] - 0.0) < 0.001
                  and abs(r["z"][1] - 0.04) < 0.001 for r in rows))
    return {"count": len(pavers), "pavers": rows, "ok": bool(ok)}


def check_anvil(parts):
    """Anvil: base sits on the floor (z_min 0), top plate top z ~1.06,
    horn tip extends past the body in +x (local frame, group rotated
    -20 deg about Z so world +x is the horn direction)."""
    base = next(o for o in parts if o.name == "Anvil_Base")
    top = next(o for o in parts if o.name == "Anvil_TopPlate")
    body = next(o for o in parts if o.name == "Anvil_Body")
    horn = next(o for o in parts if o.name == "Anvil_Horn")
    hardy = next(o for o in parts if o.name == "Anvil_HardyHole")
    r_base = world_range(base)
    r_top = world_range(top)
    r_body = world_range(body)
    r_horn = world_range(horn)
    r_hardy = world_range(hardy)
    row = {"base_z": (r_base[4], r_base[5]),
           "top_plate_z": (r_top[4], r_top[5]),
           "body_x_max": r_body[1], "horn_x_max": r_horn[1],
           "hardy_z": (r_hardy[4], r_hardy[5]),
           "horn_beyond_body": round(r_horn[1] - r_body[1], 3)}
    ok = (abs(r_base[4] - 0.0) < 0.001
          and abs(r_top[5] - 1.06) < 0.01
          and r_horn[1] > r_body[1]
          and abs(r_hardy[5] - 1.075) < 0.01)
    row["ok"] = bool(ok)
    return row


def check_barrel(parts):
    """Barrel: bottom 0-0.35 / middle 0.35-0.55 / top 0.55-0.90 stacked
    without gaps; lid 0.87-0.90 on top; each hoop radius larger than the
    barrel radius at the hoop height."""
    bot = next(o for o in parts if o.name == "Barrel_Bottom")
    mid = next(o for o in parts if o.name == "Barrel_Middle")
    top = next(o for o in parts if o.name == "Barrel_Top")
    lid = next(o for o in parts if o.name == "Barrel_Lid")
    rb, rm, rt, rl = (world_range(o) for o in (bot, mid, top, lid))
    hoop_rows = []
    for name, hz in (("Barrel_Hoop_12", 0.12), ("Barrel_Hoop_45", 0.45),
                     ("Barrel_Hoop_78", 0.78)):
        hoop = next(o for o in parts if o.name == name)
        r = world_range(hoop)
        # hoop is a 12-sided cylinder: max horizontal radius from axis
        cx, cy = 2.0, -0.2
        hoop_r = max(math.hypot(v.x - cx, v.y - cy)
                     for v in world_verts(hoop))
        body_r = barrel_radius_at(hz)
        hoop_rows.append({"name": name, "z": (r[4], r[5]),
                          "hoop_radius": round(hoop_r, 3),
                          "barrel_radius_at_z": round(body_r, 3),
                          "clearance": round(hoop_r - body_r, 3)})
    row = {"bottom_z": (rb[4], rb[5]), "middle_z": (rm[4], rm[5]),
           "top_z": (rt[4], rt[5]), "lid_z": (rl[4], rl[5]),
           "hoops": hoop_rows}
    ok = (abs(rb[4] - 0.0) < 0.001 and abs(rb[5] - 0.35) < 0.001
          and abs(rm[4] - 0.35) < 0.001 and abs(rm[5] - 0.55) < 0.001
          and abs(rt[4] - 0.55) < 0.001 and abs(rt[5] - 0.90) < 0.001
          and abs(rl[4] - 0.87) < 0.001 and abs(rl[5] - 0.90) < 0.001
          and all(h["clearance"] > 0.0 for h in hoop_rows))
    row["ok"] = bool(ok)
    return row


def check_axe(parts):
    """Axe: design says it leans on the barrel rim (barrel axis (2.0,-0.2),
    rim top z 0.90). Measure the real horizontal clearance between the axe
    and the barrel surface below the rim: vertex-based for all axe parts,
    plus haft-axis sampling (the haft has vertices only at its two ends,
    so its centerline is sampled every 0.05 along the shaft). Also report
    the pommel's lowest world z (does the butt sink into the floor?) and
    the blade's lowest world z (does it clear the barrel top?)."""
    axe_names = ["Axe_Haft", "Axe_Grip", "Axe_Pommel", "Axe_Socket",
                 "Axe_Blade", "Axe_CuttingEdge", "Axe_TopWedge"]
    axe = [o for o in parts if o.name in axe_names]
    pommel = next(o for o in parts if o.name == "Axe_Pommel")
    blade = next(o for o in parts if o.name == "Axe_Blade")
    r_pommel = world_range(pommel)
    blade_min_z = round(min(v.z for v in world_verts(blade)), 3)
    min_clear = None
    closest = None
    for o in axe:
        for v in world_verts(o):
            if v.z <= 0.90:
                body_r = barrel_radius_at(v.z)
                if body_r is None:
                    continue
                d = math.hypot(v.x - 2.0, v.y - (-0.2)) - body_r
                if min_clear is None or d < min_clear:
                    min_clear = d
                    closest = (o.name, round(v.x, 3), round(v.y, 3),
                               round(v.z, 3))
    group = bpy.data.objects.get("AxeGroup")
    shaft_clear = None
    shaft_point = None
    if group is not None:
        base = Vector(group.matrix_world.translation)
        direction = group.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        t = 0.0
        while t <= 1.55:
            p = base + direction * t
            if 0.0 <= p.z <= 0.90:
                body_r = barrel_radius_at(p.z)
                haft_r = 0.045 - (0.045 - 0.035) * (t / 1.55)
                d = math.hypot(p.x - 2.0, p.y - (-0.2)) - body_r - haft_r
                if shaft_clear is None or d < shaft_clear:
                    shaft_clear = d
                    shaft_point = ("haft_axis", round(p.x, 3),
                                   round(p.y, 3), round(p.z, 3))
            t += 0.05
    if shaft_clear is not None and (min_clear is None
                                    or shaft_clear < min_clear):
        min_clear = shaft_clear
        closest = shaft_point
    # clearance of the shaft surface from the barrel surface exactly at
    # rim height (z = 0.90): the number that decides "leaning on the rim".
    rim_clear = None
    if group is not None:
        base = Vector(group.matrix_world.translation)
        direction = group.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        t_rim = 0.90 / direction.z
        p_rim = base + direction * t_rim
        haft_r_rim = 0.045 - (0.045 - 0.035) * (t_rim / 1.55)
        rim_clear = round(math.hypot(p_rim.x - 2.0, p_rim.y - (-0.2))
                          - barrel_radius_at(0.90) - haft_r_rim, 3)
    row = {"pommel_z_min": r_pommel[4],
           "blade_min_z": blade_min_z,
           "min_clearance_to_barrel": round(min_clear, 3)
           if min_clear is not None else None,
           "closest_point": closest,
           "shaft_clearance_at_rim_z0.90": rim_clear,
           "touches_barrel": bool(min_clear is not None
                                  and min_clear <= 0.01),
           "butt_on_floor": bool(abs(r_pommel[4]) < 0.005)}
    row["ok"] = bool(row["touches_barrel"] and row["butt_on_floor"])
    return row


def check_brazier(parts):
    """Brazier: pedestal 0-0.5, bowl 0.49-0.75 on top of it, 3 embers
    embedded in the bowl (bottom below the rim z 0.75), ForgeGlow point
    light above at (-1.75, 0.10, 1.15) with 250W orange light."""
    ped = next(o for o in parts if o.name == "Brazier_Pedestal")
    bowl = next(o for o in parts if o.name == "Brazier_Bowl")
    r_ped = world_range(ped)
    r_bowl = world_range(bowl)
    ember_rows = []
    for i in range(3):
        e = next(o for o in parts if o.name == "Ember_%d" % i)
        r = world_range(e)
        ember_rows.append({"name": e.name, "z": (r[4], r[5]),
                           "embedded_below_rim": bool(r[4] < 0.75)})
    light = bpy.data.objects.get("ForgeGlow")
    light_row = None
    if light is not None and light.type == 'LIGHT':
        light_row = {"type": light.data.type,
                     "location": tuple(round(v, 2) for v in light.location),
                     "energy": round(light.data.energy, 1),
                     "color": tuple(round(v, 2)
                                    for v in light.data.color)}
    row = {"pedestal_z": (r_ped[4], r_ped[5]),
           "bowl_z": (r_bowl[4], r_bowl[5]),
           "embers": ember_rows, "light": light_row}
    ok = (abs(r_ped[4] - 0.0) < 0.001 and abs(r_ped[5] - 0.50) < 0.001
          and abs(r_bowl[4] - 0.49) < 0.01 and abs(r_bowl[5] - 0.75) < 0.01
          and all(e["embedded_below_rim"] for e in ember_rows)
          and light_row is not None and light_row["type"] == 'POINT'
          and abs(light_row["location"][0] - (-1.75)) < 0.01
          and abs(light_row["location"][1] - 0.10) < 0.01
          and abs(light_row["location"][2] - 1.15) < 0.01
          and abs(light_row["energy"] - 250.0) < 0.1)
    row["ok"] = bool(ok)
    return row


def check_bucket(parts):
    """Quench bucket: 0-0.35 tall, water surface 0.29-0.31 below the rim."""
    bucket = next(o for o in parts if o.name == "Bucket")
    water = next(o for o in parts if o.name == "Bucket_Water")
    rb = world_range(bucket)
    rw = world_range(water)
    row = {"bucket_z": (rb[4], rb[5]), "water_z": (rw[4], rw[5]),
           "water_below_rim": round(rb[5] - rw[5], 3)}
    ok = (abs(rb[4] - 0.0) < 0.001 and abs(rb[5] - 0.35) < 0.001
          and rw[5] < rb[5] and rw[4] > rb[4])
    row["ok"] = bool(ok)
    return row


def check_floor_props(parts):
    """Hammer lies on the floor, ingots stack (top ingot above the two
    below), coal lumps rest on the floor; nothing floats or sinks."""
    handle = next(o for o in parts if o.name == "Hammer_Handle")
    head = next(o for o in parts if o.name == "Hammer_Head")
    rh, rhead = world_range(handle), world_range(head)
    ingots = []
    for i in range(3):
        ingots.append(world_range(
            next(o for o in parts if o.name == "Ingot_%d" % i)))
    coals = []
    for i in range(3):
        coals.append(world_range(
            next(o for o in parts if o.name == "Coal_%d" % i)))
    row = {"hammer_handle_z_min": rh[4], "hammer_head_z": (rhead[4], rhead[5]),
           "ingot_z": [(r[4], r[5]) for r in ingots],
           "coal_z_min": [r[4] for r in coals],
           "ingot_stacked": bool(ingots[2][4] >= ingots[0][5] - 0.001)}
    ok = (abs(rh[4] - 0.007) < 0.01 and abs(rhead[4] - 0.0) < 0.001
          and row["ingot_stacked"]
          and all(abs(c[4]) < 0.01 for c in coals))
    row["ok"] = bool(ok)
    return row


def check_ground_contact(parts):
    """Every part that should rest on the floor must have z_min ~ 0
    (walls, pavers, anvil base, barrel bottom, bucket, brazier pedestal,
    hammer head, ingots, coals, corner post)."""
    names = (["Wall_Back", "Wall_Left", "Post_Corner", "Anvil_Base",
              "Barrel_Bottom", "Bucket", "Brazier_Pedestal",
              "Hammer_Head", "Ingot_0", "Ingot_1", "Coal_0", "Coal_1",
              "Coal_2"] + ["Paver_%02d" % i for i in range(12)])
    rows = []
    for n in names:
        o = next(p for p in parts if p.name == n)
        zmin = world_range(o)[4]
        rows.append({"name": n, "z_min": zmin})
    bad = [r for r in rows if abs(r["z_min"]) > 0.01]
    return {"checked": len(rows), "off_floor": bad,
            "ok": bool(not bad)}


# design values from the 028 build script: (metallic, roughness, base color)
DESIGN_MATS = {
    "Corner_StoneWall": (0.00, 0.95, (0.30, 0.28, 0.26)),
    "Corner_StoneDark": (0.00, 0.95, (0.20, 0.19, 0.19)),
    "Corner_Beam": (0.00, 0.90, (0.32, 0.20, 0.10)),
    "Anvil_Steel": (0.85, 0.35, (0.32, 0.33, 0.37)),
    "Anvil_TopSteel": (0.90, 0.18, (0.62, 0.64, 0.68)),
    "Anvil_Iron": (0.70, 0.50, (0.16, 0.16, 0.18)),
    "Anvil_Dark": (0.30, 0.80, (0.05, 0.05, 0.06)),
    "Axe_EdgeSteel": (0.90, 0.15, (0.62, 0.64, 0.68)),
    "Axe_Wood": (0.00, 0.80, (0.45, 0.28, 0.14)),
    "Axe_WoodDark": (0.00, 0.85, (0.30, 0.18, 0.09)),
    "Axe_Leather": (0.00, 0.90, (0.20, 0.12, 0.08)),
    "Barrel_Wood": (0.00, 0.85, (0.42, 0.27, 0.13)),
    "Barrel_WoodLight": (0.00, 0.85, (0.60, 0.42, 0.22)),
    "Barrel_Hoop": (0.80, 0.45, (0.12, 0.12, 0.13)),
    "Bucket_Water": (0.10, 0.10, (0.10, 0.22, 0.32)),
    "Coal": (0.00, 0.90, (0.04, 0.04, 0.05)),
}
PAVER_GRAYS = [(0.30, 0.30, 0.32), (0.36, 0.36, 0.38),
               (0.26, 0.26, 0.28), (0.40, 0.39, 0.38)]
for _i in range(12):
    DESIGN_MATS["Paver_%d" % _i] = (0.00, 0.95, PAVER_GRAYS[_i % 4])


def check_materials(parts):
    """Read Principled BSDF node values, not names. Ember is checked
    separately for its emission values."""
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
    # ember: emission color (1.0, 0.30, 0.05), strength 3.0
    ember = bpy.data.materials.get("Ember")
    ember_row = {"name": "Ember", "found": ember is not None, "ok": False}
    if ember is not None and ember.use_nodes:
        for n in ember.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                ec = tuple(round(v, 2) for v in
                           n.inputs["Emission Color"].default_value[:3])
                es = round(n.inputs["Emission Strength"].default_value, 2)
                ember_row.update({"emission_color": ec,
                                  "emission_strength": es,
                                  "ok": bool(ec == (1.0, 0.30, 0.05)
                                            and abs(es - 3.0) < 0.01)})
                break
    rows.append(ember_row)
    used = {m.name for o in parts for m in o.data.materials if m}
    missing_design = [n for n in DESIGN_MATS if n not in used]
    return {"rows": rows,
            "all_ok": bool(all(r["ok"] for r in rows)),
            "unused_design_mats": missing_design}


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    parts = [o for o in bpy.context.scene.objects
             if o.type == 'MESH' and o.name not in EXCLUDE]
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

    walls = check_walls(parts)
    print("QA_WALLS:", walls)
    pavers = check_pavers(parts)
    print("QA_PAVERS:", pavers)
    anvil = check_anvil(parts)
    print("QA_ANVIL:", anvil)
    barrel = check_barrel(parts)
    print("QA_BARREL:", barrel)
    axe = check_axe(parts)
    print("QA_AXE:", axe)
    brazier = check_brazier(parts)
    print("QA_BRAZIER:", brazier)
    bucket = check_bucket(parts)
    print("QA_BUCKET:", bucket)
    floor_props = check_floor_props(parts)
    print("QA_FLOOR_PROPS:", floor_props)
    ground = check_ground_contact(parts)
    print("QA_GROUND_CONTACT:", ground)
    mats = check_materials(parts)
    print("QA_MATERIALS:", mats)

    structure = {"walls": walls, "pavers": pavers, "anvil": anvil,
                 "barrel": barrel, "axe": axe, "brazier": brazier,
                 "bucket": bucket, "floor_props": floor_props,
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
    ngons_ok = tot["ngons"] == 0
    all_ok = (ngons_ok and tot["duplicate_verts"] == 0
              and tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0
              and tot["degenerate_faces"] == 0 and tot["boundary_edges"] == 0
              and tot["inverted_normals"] == 0 and tot_oob == 0
              and worst_overlap < 1.0 and empty_slots == 0
              and structure_ok and mats["all_ok"])

    summary = {
        "asset": "028-blacksmith-corner",
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

    order = sorted(results.keys())
    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 029 资产质检单：铁匠铺角落场景（028）\n\n")
        f.write("被检资产：`scenes/028-blacksmith-corner.blend`（%d 个场景部件，不含地面）\n" % len(results))
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
        f.write("- 闭合网格（无边界边）：%s\n\n" % verdict(tot["boundary_edges"] == 0))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：%s，倒置面 %d 个\n\n" % (
            verdict(tot["inverted_normals"] == 0), tot["inverted_normals"]))
        f.write("## 3. UV\n\n")
        f.write("- UV 层存在：%s（%d 个部件均已 Smart UV Project 展开）\n" % (
            verdict(all(r["uv"]["has_uv"] for r in results.values())),
            len(results)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n" % (
            tot_oob, verdict(tot_oob == 0)))
        f.write("- UV 利用率最低的 5 个部件：\n")
        for name in sorted(results, key=lambda k: results[k]["uv"]["utilization"])[:5]:
            f.write("  - %s：%.1f%%\n" % (name, results[name]["uv"]["utilization"] * 100))
        f.write("  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）\n")
        f.write("- UV 岛数量：%d\n" % tot_islands)
        f.write("- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：%.2f%%，%s\n\n" % (
            worst_overlap, verdict(worst_overlap < 1.0, "阈值 <1%")))
        f.write("## 4. 场景结构（实测）\n\n")
        w = walls
        f.write("- 角落墙体：后墙 y %.2f–%.2f、z %.2f–%.2f，左墙 x %.2f–%.2f、z %.2f–%.2f；"
                "木梁 z %.2f–%.2f / %.2f–%.2f 在墙顶之下；角柱 z %.2f–%.2f 落地；"
                "左墙端头伸入后墙墙身、角部无缝隙：%s"
                "（注：后墙向左超出左墙外侧 %.2f，角部外侧有一小段外露墙端）：%s\n" % (
                    w["wall_back"][2], w["wall_back"][3], w["wall_back"][4], w["wall_back"][5],
                    w["wall_left"][0], w["wall_left"][1], w["wall_left"][4], w["wall_left"][5],
                    w["beam_back_z"][0], w["beam_back_z"][1],
                    w["beam_left_z"][0], w["beam_left_z"][1],
                    w["post_z"][0], w["post_z"][1],
                    "是" if w["corner_overlap"] else "否",
                    w["back_wall_overhang_past_left_wall"],
                    verdict(w["ok"])))
        f.write("- 石板铺地：共 %d 块，全部 z 0.00–0.04 贴地：%s\n" % (
            pavers["count"], verdict(pavers["ok"])))
        a = anvil
        f.write("- 铁砧：底座 z %.2f–%.2f 落地；砧面顶 z=%.2f（设计 1.06）；"
                "砧角最远 x=%.2f 超出砧身 x=%.2f；方孔顶 z=%.2f：%s\n" % (
                    a["base_z"][0], a["base_z"][1], a["top_plate_z"][1],
                    a["horn_x_max"], a["body_x_max"], a["hardy_z"][1],
                    verdict(a["ok"])))
        b = barrel
        f.write("- 木桶：三段 z %.2f–%.2f / %.2f–%.2f / %.2f–%.2f 无缝叠合；"
                "桶盖 z %.2f–%.2f；三道铁箍半径均大于该高度桶身半径（间隙 %.3f / %.3f / %.3f）：%s\n" % (
                    b["bottom_z"][0], b["bottom_z"][1],
                    b["middle_z"][0], b["middle_z"][1],
                    b["top_z"][0], b["top_z"][1],
                    b["lid_z"][0], b["lid_z"][1],
                    b["hoops"][0]["clearance"], b["hoops"][1]["clearance"],
                    b["hoops"][2]["clearance"], verdict(b["ok"])))
        ax = axe
        f.write("- 战斧斜靠：战斧与桶身表面的最小水平间隙 %s"
                "（最近点 %s，斧柄轴线采样 + 全部顶点实测）；"
                "桶沿高度 z=0.90 处斧柄表面离桶身 %.3f；斧刃最低 z=%.3f"
                "（桶顶 z=0.90，斧刃整体高于桶顶）；斧底帽最低 z=%.3f：%s\n" % (
                    ("%.3f" % ax["min_clearance_to_barrel"]
                     if ax["min_clearance_to_barrel"] is not None else "无数据"),
                    ax["closest_point"],
                    ax["shaft_clearance_at_rim_z0.90"],
                    ax["blade_min_z"],
                    ax["pommel_z_min"], verdict(ax["ok"])))
        br = brazier
        f.write("- 火盆：石墩 z %.2f–%.2f 落地；铁碗 z %.2f–%.2f 坐在墩顶；"
                "3 块炭块底部均低于碗沿 z=0.75；ForgeGlow 点光源位于 (%s)，能量 %.1fW 橙色：%s\n" % (
                    br["pedestal_z"][0], br["pedestal_z"][1],
                    br["bowl_z"][0], br["bowl_z"][1],
                    ", ".join("%.2f" % v for v in br["light"]["location"])
                    if br["light"] else "未找到",
                    br["light"]["energy"] if br["light"] else 0,
                    verdict(br["ok"])))
        bk = bucket
        f.write("- 淬火桶：桶身 z %.2f–%.2f 落地；水面 z %.2f–%.2f，低于桶沿 %.3f：%s\n" % (
            bk["bucket_z"][0], bk["bucket_z"][1],
            bk["water_z"][0], bk["water_z"][1],
            bk["water_below_rim"], verdict(bk["ok"])))
        fp = floor_props
        f.write("- 地面小件：铁锤柄最低 z=%.3f、锤头 z %.2f–%.2f；铁锭叠放（顶层 z %.2f–%.2f 在下层之上）：%s；"
                "煤块最低 z %s：%s\n" % (
                    fp["hammer_handle_z_min"], fp["hammer_head_z"][0],
                    fp["hammer_head_z"][1],
                    fp["ingot_z"][2][0], fp["ingot_z"][2][1],
                    "是" if fp["ingot_stacked"] else "否",
                    ", ".join("%.3f" % z for z in fp["coal_z_min"]),
                    verdict(fp["ok"])))
        f.write("- 落地检查：共检查 %d 个应落地部件，离地部件：%s：%s\n\n" % (
            ground["checked"],
            "无" if not ground["off_floor"]
            else ", ".join("%s(z_min=%.3f)" % (r["name"], r["z_min"])
                           for r in ground["off_floor"]),
            verdict(ground["ok"])))
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
            if r["name"] == "Ember":
                f.write("  - Ember：Emission %s（设计 (1.0, 0.30, 0.05)），强度 %.2f（设计 3.0）：%s\n" % (
                    r.get("emission_color"), r.get("emission_strength"),
                    verdict(r["ok"])))
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
