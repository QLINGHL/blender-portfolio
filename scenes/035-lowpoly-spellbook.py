# -*- coding: utf-8 -*-
"""035 低模游戏道具：魔法书（Spellbook）
Low-poly game spellbook: closed book lying flat, deep-purple leather
covers, cream page block with page-line grooves, rounded spine,
brass rune ring + five-point star + amethyst octahedron on the top
cover, iron clasp with stud, brass corner protectors, crimson
bookmark ribbon. Game-asset standard, flat shading, clean topology.
Overall ~0.56 m wide x 0.78 m deep x 0.10 m thick.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 035-lowpoly-spellbook.py
"""
import os
import sys
import math
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    fit_camera_to_objects, export_wireframe_segments)


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
    """Axis-aligned box from center + (sx, sy, sz). Outward winding."""
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
    return mesh_from_data(name, verts, faces, mat)


def rot_box(name, center, size, angle_z, mat):
    """Box rotated about the Z axis by angle_z (radians)."""
    obj = box(name, center, size, mat)
    obj.rotation_euler = (0, 0, angle_z)
    return obj


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points, open fan caps."""
    from mathutils import Vector
    a = Vector(p0)
    b = Vector(p1)
    axis = b - a
    length = axis.length
    axis.normalize()
    up = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(up).normalized()
    v = axis.cross(u).normalized()
    verts = []
    for p in (a, b):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append(tuple(p + radius * (math.cos(ang) * u
                                             + math.sin(ang) * v)))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append(tuple(a))
    c1 = len(verts)
    verts.append(tuple(b))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def torus_xy(name, center, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying flat in the XY plane, centered at `center`.
    Closed tube, no caps needed."""
    cx, cy, cz = center
    verts = []
    for i in range(arc_segments):
        th = 2.0 * math.pi * i / arc_segments
        rx, ry = math.cos(th), math.sin(th)
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + (R + r * math.cos(ph)) * rx,
                          cy + (R + r * math.cos(ph)) * ry,
                          cz + r * math.sin(ph)))
    faces = []
    for i in range(arc_segments):
        ni = (i + 1) % arc_segments
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            faces.append((i * tube_segments + j, ni * tube_segments + j,
                          ni * tube_segments + k, i * tube_segments + k))
    return mesh_from_data(name, verts, faces, mat)


def octahedron(name, center, a, mat):
    """Regular octahedron, 8 triangle faces, outward winding."""
    cx, cy, cz = center
    top = (cx, cy, cz + a)
    bot = (cx, cy, cz - a)
    e = [(cx + a, cy, cz), (cx, cy + a, cz),
         (cx - a, cy, cz), (cx, cy - a, cz)]
    verts = [top, bot] + e
    faces = [
        (0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
        (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5),
    ]
    return mesh_from_data(name, verts, faces, mat)


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def check_winding(obj):
    """Count faces whose normal points inward (dot with the vector from
    the mesh centroid to the face center is negative)."""
    import bmesh
    from mathutils import Vector
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


def check_torus_winding_xy(obj, R, center):
    """Winding check for the flat rune ring: compare each face normal
    with the direction from the nearest point on the ring centerline
    (radius R in the XY plane at center) to the face center."""
    import bmesh
    from mathutils import Vector
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = 0
    cx, cy, cz = center
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        dx, dy = c.x - cx, c.y - cy
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nearest = Vector((cx + R * dx / L, cy + R * dy / L, cz))
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.05))

    leather = solid_material("Spellbook_Leather", (0.05, 0.02, 0.12),
                             metallic=0.0, roughness=0.8)
    leather_dark = solid_material("Spellbook_LeatherDark",
                                  (0.03, 0.015, 0.07),
                                  metallic=0.0, roughness=0.85)
    pages = solid_material("Spellbook_Pages", (0.85, 0.78, 0.60),
                           metallic=0.0, roughness=0.9)
    page_line = solid_material("Spellbook_PageLine", (0.68, 0.60, 0.44),
                               metallic=0.0, roughness=0.9)
    brass = solid_material("Spellbook_Brass", (0.45, 0.28, 0.06),
                           metallic=0.85, roughness=0.35)
    iron = solid_material("Spellbook_Iron", (0.20, 0.20, 0.22),
                          metallic=0.7, roughness=0.5)
    gem = solid_material("Spellbook_Amethyst", (0.25, 0.05, 0.45),
                         metallic=0.3, roughness=0.2)
    ribbon = solid_material("Spellbook_Ribbon", (0.35, 0.02, 0.05),
                            metallic=0.0, roughness=0.8)

    parts = []
    # --- bottom cover: leather, 0.56 x 0.76 x 0.018, z 0.000-0.018 ---
    parts.append(box("CoverBottom", (0, 0, 0.009), (0.56, 0.76, 0.018),
                     leather))
    # --- page block: cream, 0.50 x 0.70 x 0.062, z 0.018-0.080 ---
    #     inset 0.03 from fore-edge / head / tail, flush at the spine.
    parts.append(box("PageBlock", (0.0, 0, 0.049), (0.50, 0.70, 0.062),
                     pages))
    # --- top cover: leather, 0.56 x 0.76 x 0.018, z 0.080-0.098 ---
    parts.append(box("CoverTop", (0, 0, 0.089), (0.56, 0.76, 0.018),
                     leather))
    # --- spine: rounded, cylinder along Y at x=-0.28, r 0.022 ---
    parts.append(cyl_between("Spine", (-0.28, -0.38, 0.049),
                             (-0.28, 0.38, 0.049), 0.022, 12, leather_dark))
    # --- page lines: 3 thin grooves on the fore-edge (x=+0.25 face) ---
    for i, z in enumerate((0.032, 0.049, 0.066)):
        parts.append(box("PageLineFore_%d" % (i + 1),
                         (0.251, 0, z), (0.004, 0.70, 0.006), page_line))
    # --- page lines: 3 thin grooves on the head edge (y=+0.35 face) ---
    for i, z in enumerate((0.032, 0.049, 0.066)):
        parts.append(box("PageLineHead_%d" % (i + 1),
                         (0.0, 0.351, z), (0.50, 0.004, 0.006), page_line))
    # --- page lines: 3 thin grooves on the tail edge (y=-0.35 face) ---
    for i, z in enumerate((0.032, 0.049, 0.066)):
        parts.append(box("PageLineTail_%d" % (i + 1),
                         (0.0, -0.351, z), (0.50, 0.004, 0.006), page_line))
    # --- rune ring: flat brass torus on the top cover, R 0.14, r 0.012 ---
    ring = torus_xy("RuneRing", (0, 0, 0.100), 0.14, 0.012, 32, 8, brass)
    parts.append(ring)
    # --- rune star: 5 thin brass bars crossing at the cover center,
    #     rotated 72 deg apart, lying on the top cover ---
    for i in range(5):
        ang = math.radians(72.0 * i)
        parts.append(rot_box("RuneStar_%d" % (i + 1), (0, 0, 0.101),
                             (0.024, 0.26, 0.006), ang, brass))
    # --- center gem: amethyst octahedron, a 0.035, on the cover center ---
    parts.append(octahedron("Gem", (0, 0, 0.115), 0.035, gem))
    # --- clasp: iron strap over the fore-edge ---
    #     top strap on the cover + vertical strap down the fore-edge
    parts.append(box("ClaspTop", (0.20, 0, 0.101), (0.16, 0.05, 0.006),
                     iron))
    parts.append(box("ClaspFront", (0.283, 0, 0.049), (0.006, 0.05, 0.10),
                     iron))
    # --- clasp stud: small iron cylinder on the top strap ---
    parts.append(cyl_between("ClaspStud", (0.20, 0, 0.104),
                             (0.20, 0, 0.116), 0.014, 8, iron))
    # --- corner protectors: 4 flat brass plates on the top cover ---
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box("Corner_%+d%+d" % (sx, sy),
                             (sx * 0.245, sy * 0.345, 0.101),
                             (0.07, 0.07, 0.006), brass))
    # --- bookmark ribbon: crimson strip sticking out of the tail edge ---
    parts.append(box("Bookmark", (0.10, -0.40, 0.049),
                     (0.035, 0.12, 0.004), ribbon))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    flipped["RuneRing"] = check_torus_winding_xy(ring, 0.14, (0, 0, 0.100))
    print("SPELLBOOK_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "035-lowpoly-spellbook.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "035-lowpoly-spellbook.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "spellbook_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("SPELLBOOK_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("SPELLBOOK_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "035-lowpoly-spellbook.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 035 低模游戏道具：魔法书\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "合拢的魔法书平放于地面，3/4 俯视角度展示。\n\n")
        f.write("## 结构\n\n")
        f.write("- 下封面（CoverBottom）：深紫皮革 0.56×0.76×0.018，"
                "z 0.000–0.018\n")
        f.write("- 书页块（PageBlock）：米色 0.50×0.70×0.062，z 0.018–0.080；"
                "前切口/天头/地脚各内缩 0.03，书脊侧齐平\n")
        f.write("- 上封面（CoverTop）：深紫皮革 0.56×0.76×0.018，"
                "z 0.080–0.098\n")
        f.write("- 书脊（Spine）：深色皮革圆柱，沿 Y 轴 x=-0.28，r 0.022，"
                "长 0.76，半嵌进书身形成圆脊\n")
        f.write("- 书页纹（PageLine）：前切口/天头/地脚各 3 条细槽，"
                "深米色 0.006 厚，微凸出页块表面 0.002\n")
        f.write("- 符文环（RuneRing）：黄铜圆环平放于上封面，R 0.14，"
                "管 r 0.012，32×8 段\n")
        f.write("- 符文星（RuneStar）：5 条黄铜细条，72° 均布，"
                "0.024×0.26×0.006，交于封面中心\n")
        f.write("- 宝石（Gem）：紫水晶正八面体，a 0.035，位于封面中心，"
                "高出封面约 0.05\n")
        f.write("- 锁扣（Clasp）：铁质；顶部扣带 0.16×0.05 横跨封面，"
                "前切口竖带 0.006×0.05×0.10，顶部圆柱扣钉 r 0.014\n")
        f.write("- 护角（Corner）：4 块黄铜平板 0.07×0.07×0.006，"
                "位于上封面四角\n")
        f.write("- 书签（Bookmark）：绯红缎带 0.035×0.12×0.004，"
                "从地脚伸出书外 0.05\n")
        f.write("- 整体约 0.56 m 宽 × 0.78 m 深 × 0.115 m 厚（含宝石）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("符文环为闭合圆环几何，绕向用环中心线检测（质心检测不适用于环形）；"
                "其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Spellbook_Leather：上下封面深紫皮革（roughness 0.8）\n")
        f.write("- Spellbook_LeatherDark：书脊深色皮革（roughness 0.85）\n")
        f.write("- Spellbook_Pages：书页米色（roughness 0.9）\n")
        f.write("- Spellbook_PageLine：书页纹深米色（roughness 0.9）\n")
        f.write("- Spellbook_Brass：符文环/符文星/护角黄铜"
                "（metallic 0.85，roughness 0.35）\n")
        f.write("- Spellbook_Iron：锁扣铁质（metallic 0.7，roughness 0.5）\n")
        f.write("- Spellbook_Amethyst：宝石紫水晶"
                "（metallic 0.3，roughness 0.2）\n")
        f.write("- Spellbook_Ribbon：书签绯红缎带（roughness 0.8）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
