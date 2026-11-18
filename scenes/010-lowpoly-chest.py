# -*- coding: utf-8 -*-
"""010 低模游戏道具：宝箱（可开盖，内外结构）
Low-poly game treasure chest: open-top body built from five panels (real
interior cavity), arched lid hinged open ~100 deg, gold coin pile, iron
bands, lock hasp. Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 010-lowpoly-chest.py
"""
import os
import sys
import math
import random
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, make_camera, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    export_wireframe_segments)


def mesh_from_data(name, verts, faces, material=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    flat_shade(obj)
    return obj


def box(name, center, size, mat):
    """Axis-aligned box from center + (sx, sy, sz)."""
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    # NOTE (012 QA): the original winding was backwards on all six faces
    # (every box measured 6 inverted normals); the order above is the
    # corrected outward winding, verified by recalc_face_normals.
    return mesh_from_data(name, verts, faces, mat)


def cylinder(name, center, radius, height, sides, mat, rot_x=0.0):
    """Vertical (Z-axis) cylinder, optionally tilted around X."""
    cx, cy, cz = center
    verts = []
    for z in (cz - height / 2.0, cz + height / 2.0):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((cx + radius * math.cos(a),
                          cy + radius * math.sin(a), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    # NOTE (012 QA): the old cap N-gons (one 8-gon per end) are replaced by
    # triangle fans with a center vertex, so the asset has zero N-gons
    # (game-pipeline standard, same as 002/008). Winding matches the
    # original caps, verified by recalc_face_normals.
    cx0, cy0 = cx, cy
    verts.append((cx0, cy0, cz - height / 2.0))
    verts.append((cx0, cy0, cz + height / 2.0))
    c_bot, c_top = 2 * sides, 2 * sides + 1
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_bot, j, i))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_top, sides + i, sides + j))
    obj = mesh_from_data(name, verts, faces, mat)
    if rot_x:
        obj.rotation_euler[0] = rot_x
    return obj


def build_lid(name, x_half=1.2, y_half=0.7, z_base=0.9, arc_segments=8,
              mat=None, trim_mat=None):
    """Arched lid, mesh built relative to the hinge line (y=+y_half,
    z=z_base) so the object origin sits on the hinge; rotating the object
    about X opens it. Cross-section: semicircle arc + flat bottom plate,
    extruded along X with end caps."""
    verts, faces = [], []
    # arc profile in (y, z) relative to hinge: theta 0..pi
    arc = []
    for k in range(arc_segments + 1):
        th = math.pi * k / arc_segments
        # y from +y_half (hinge side) to -y_half (front lip)
        y = y_half * math.cos(th) - y_half
        z = y_half * math.sin(th)
        arc.append((y, z))
    # two end rings at x = -x_half and +x_half: only the arc profile
    # points (arc[0] == (y=0, z=0) and arc[8] == (y=-2*y_half, z=0) are
    # already the bottom-plate corners, so no extra verts are added).
    # NOTE (012 QA): the old code added two extra verts per ring that
    # duplicated arc[0]/arc[8], producing 4 duplicate verts, 4 degenerate
    # cap triangles and 8 boundary edges on the lid; the fan below is
    # the corrected version.
    for x in (-x_half, x_half):
        base = len(verts)
        for (y, z) in arc:
            verts.append((x, y, z))
    n = arc_segments + 1  # verts per ring
    # top arc quads between rings
    for k in range(arc_segments):
        faces.append((k, k + 1, n + k + 1, n + k))
    # bottom plate quad (flat underside, faces -Z)
    faces.append((0, n, n + arc_segments, arc_segments))
    # end caps: fan from arc[0]; ring 0 faces -X, ring 1 faces +X
    for k in range(1, arc_segments):
        faces.append((0, k + 1, k))
        faces.append((n, n + k, n + k + 1))
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = (0.0, y_half, z_base)
    return obj


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

    wood = solid_material("Chest_Wood", (0.40, 0.24, 0.10),
                          metallic=0.0, roughness=0.8)
    wood_dark = solid_material("Chest_WoodDark", (0.30, 0.18, 0.08),
                               metallic=0.0, roughness=0.85)
    wood_inner = solid_material("Chest_WoodInner", (0.36, 0.22, 0.10),
                                metallic=0.0, roughness=0.9)
    iron = solid_material("Iron_Band", (0.22, 0.22, 0.24),
                          metallic=0.85, roughness=0.35)
    gold = solid_material("Gold_Coin", (0.95, 0.72, 0.18),
                          metallic=0.9, roughness=0.25)
    gem_red = solid_material("Gem_Red", (0.75, 0.08, 0.12),
                             metallic=0.1, roughness=0.15)
    gem_blue = solid_material("Gem_Blue", (0.10, 0.25, 0.75),
                              metallic=0.1, roughness=0.15)
    brass = solid_material("Brass_Lock", (0.78, 0.60, 0.20),
                           metallic=0.9, roughness=0.3)

    parts = []
    T = 0.10          # wall thickness
    W, D, H = 2.4, 1.4, 0.9   # outer body size

    # --- body: five panels, real open-top cavity ---
    parts.append(box("Body_Bottom", (0, 0, T / 2), (W, D, T), wood_dark))
    parts.append(box("Body_Front", (0, -(D / 2 - T / 2), T + (H - T) / 2),
                     (W, T, H - T), wood))
    parts.append(box("Body_Back", (0, (D / 2 - T / 2), T + (H - T) / 2),
                     (W, T, H - T), wood))
    parts.append(box("Body_Left", (-(W / 2 - T / 2), 0, T + (H - T) / 2),
                     (T, D - 2 * T, H - T), wood))
    parts.append(box("Body_Right", ((W / 2 - T / 2), 0, T + (H - T) / 2),
                     (T, D - 2 * T, H - T), wood))
    # inner floor lining (visible inside the cavity)
    parts.append(box("Inner_Floor", (0, 0, T + 0.01),
                     (W - 2 * T, D - 2 * T, 0.02), wood_inner))
    # top rim trim (frame around the opening)
    parts.append(box("Rim_Front", (0, -(D / 2 - T / 2), H + 0.02),
                     (W, T + 0.04, 0.04), wood_dark))
    parts.append(box("Rim_Back", (0, (D / 2 - T / 2), H + 0.02),
                     (W, T + 0.04, 0.04), wood_dark))
    parts.append(box("Rim_Left", (-(W / 2 - T / 2), 0, H + 0.02),
                     (T + 0.04, D - 2 * T, 0.04), wood_dark))
    parts.append(box("Rim_Right", ((W / 2 - T / 2), 0, H + 0.02),
                     (T + 0.04, D - 2 * T, 0.04), wood_dark))

    # --- iron bands around the body at x = +/-0.7 (front/back/bottom) ---
    for bx in (-0.7, 0.7):
        parts.append(box("Band_Front_%d" % int(abs(bx) * 10),
                         (bx, -(D / 2 + 0.005), H / 2),
                         (0.14, 0.03, H), iron))
        parts.append(box("Band_Back_%d" % int(abs(bx) * 10),
                         (bx, (D / 2 + 0.005), H / 2),
                         (0.14, 0.03, H), iron))
        parts.append(box("Band_Bottom_%d" % int(abs(bx) * 10),
                         (bx, 0, 0.005), (0.14, D, 0.03), iron))

    # --- lock hasp on the front (body side) + brass padlock ---
    parts.append(box("Hasp_Body", (0, -(D / 2 + 0.01), H - 0.12),
                     (0.22, 0.03, 0.3), iron))
    parts.append(box("Padlock", (0, -(D / 2 + 0.06), H - 0.28),
                     (0.2, 0.1, 0.26), brass))
    parts.append(box("Padlock_Shankle", (0, -(D / 2 + 0.04), H - 0.10),
                     (0.16, 0.05, 0.08), iron))

    # --- gold coin pile inside the cavity (deterministic layout) ---
    # Heaped high (top ~0.72) so the treasure reads over the front rim
    # from a three-quarter camera angle.
    random.seed(42)
    coin_r, coin_h = 0.16, 0.035
    pile = []
    for layer, (count, z) in enumerate(((7, 0.30), (5, 0.44), (3, 0.58))):
        for i in range(count):
            a = 2.0 * math.pi * i / count + layer * 0.6
            r = 0.42 if layer == 0 else (0.30 if layer == 1 else 0.16)
            x = r * math.cos(a) + random.uniform(-0.04, 0.04)
            y = r * math.sin(a) * 0.55 + random.uniform(-0.04, 0.04)
            c = cylinder("Coin_L%d_%d" % (layer, i), (x, y, z),
                         coin_r, coin_h, 8, gold,
                         rot_x=random.uniform(-0.12, 0.12))
            pile.append(c)
    pile.append(cylinder("Coin_Top", (0.05, 0.0, 0.70), coin_r, coin_h, 8,
                         gold, rot_x=0.35))
    parts.extend(pile)
    # two gems on top of the pile
    gem1 = cylinder("Gem_Red", (0.22, -0.08, 0.76), 0.09, 0.12, 6,
                    gem_red)
    gem2 = cylinder("Gem_Blue", (-0.26, 0.14, 0.76), 0.08, 0.10, 6,
                    gem_blue)
    parts.extend([gem1, gem2])

    # --- arched lid, hinged open ~100 deg ---
    lid = build_lid("Lid", x_half=W / 2, y_half=D / 2, z_base=H,
                    arc_segments=8, mat=wood)
    lid.rotation_euler[0] = math.radians(-100.0)
    parts.append(lid)
    # lid bands (rotate with the lid: parent them to it).
    # Each band is a ribbon hugging the lid arc: radius 0.715 (lid arc
    # radius 0.7 + 0.015 offset), centred on the arc centre (y=-0.7, z=0)
    # in lid-local coords, spanning theta 0..pi.
    for bx in (-0.7, 0.7):
        bverts, bfaces = [], []
        for k in range(9):
            th = math.pi * k / 8
            y = -0.7 + 0.715 * math.cos(th)
            z = 0.715 * math.sin(th)
            bverts.append((bx - 0.07, y, z))
            bverts.append((bx + 0.07, y, z))
        for k in range(8):
            bfaces.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))
        strip = mesh_from_data("LidBand_%d" % int(abs(bx) * 10),
                               bverts, bfaces, iron)
        strip.parent = lid
        parts.append(strip)
    # lid hasp plate: hangs down from the lid's front lip (local z < 0),
    # parented to the lid so it swings open with it
    lid_hasp = mesh_from_data(
        "LidHasp",
        [(-0.11, -2 * 0.7 - 0.015, -0.32), (0.11, -2 * 0.7 - 0.015, -0.32),
         (0.11, -2 * 0.7 - 0.015, 0.0), (-0.11, -2 * 0.7 - 0.015, 0.0)],
        [(0, 1, 2, 3)], iron)
    lid_hasp.parent = lid
    parts.append(lid_hasp)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    cam = make_camera("Camera", (3.6, -3.8, 3.4), (0, 0, 0.9), lens=45.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "010-lowpoly-chest.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "010-lowpoly-chest.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "chest_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("CHEST_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CHEST_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "010-lowpoly-chest.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 010 低模游戏道具：宝箱（可开盖）\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 箱体：5 块板拼出真实内腔（底 + 前后左右壁，壁厚 0.10），内衬底板 + 顶部包边框\n")
        f.write("- 箱盖：8 段半圆拱形盖，铰链在后沿（y=+0.7, z=0.9），绕 X 轴打开 100°\n")
        f.write("- 金币堆：16 枚 8 边金币，三层堆叠（7/5/3）+ 顶层 1 枚，金色金属材质\n")
        f.write("- 宝石：红、蓝宝石各 1 枚，堆在金币顶上\n")
        f.write("- 铁包边：箱体前后 + 底部各 2 道，箱盖前唇 2 道（随盖转动）\n")
        f.write("- 锁扣：箱体前板铁搭扣 + 黄铜挂锁 + 锁梁\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Chest_Wood：箱体木色（roughness 0.8）\n")
        f.write("- Chest_WoodDark：底板 / 包边深木色\n")
        f.write("- Iron_Band：铁包边（metallic 0.85）\n")
        f.write("- Gold_Coin：金币（metallic 0.9）\n")
        f.write("- Gem_Red / Gem_Blue：红蓝宝石\n")
        f.write("- Brass_Lock：黄铜挂锁（metallic 0.9）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
