# -*- coding: utf-8 -*-
"""016 低模场景：魔法祭坛（低多边形环境资产）
Low-poly magic altar scene: three-tier stone platform, glowing rune
ring, eight tilted rune stones with glowing rune plates, altar block
with slab top, three candlesticks (two on the altar, one tall on the
platform), floating crystal + shards, front steps. Eevee beauty +
wireframe renders, .blend + note.
Run: blender --background --python 016-lowpoly-altar.py
"""
import os
import sys
import math
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


def box(name, center, size, mat, rot=(0.0, 0.0, 0.0)):
    """Box from center + (sx, sy, sz), optional rotation."""
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz),
        (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz),
        (sx, sy, sz), (-sx, sy, sz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    # NOTE (017 QA): the original winding was backwards on all six faces
    # (every box measured 6 inverted normals, same bug 012 found in 010);
    # the order above is the corrected outward winding, verified by
    # recalc_face_normals.
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = center
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def cylinder(name, center, radius, height, sides, mat,
             rot=(0.0, 0.0, 0.0)):
    """Vertical (Z-axis) cylinder with fan-triangulated caps (no N-gons)."""
    verts = []
    for z in (-height / 2.0, height / 2.0):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((radius * math.cos(a),
                          radius * math.sin(a), z))
    verts.append((0.0, 0.0, -height / 2.0))   # bottom center
    verts.append((0.0, 0.0, height / 2.0))    # top center
    bc, tc = 2 * sides, 2 * sides + 1
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
        faces.append((bc, j, i))              # bottom fan
        faces.append((tc, sides + i, sides + j))  # top fan
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = center
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def cone(name, center, radius, height, sides, mat):
    """Cone (pointed top), vertical, fan-triangulated base."""
    cx, cy, cz = center
    verts = [(cx, cy, cz + height / 2.0)]
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        verts.append((cx + radius * math.cos(a),
                      cy + radius * math.sin(a), cz - height / 2.0))
    verts.append((cx, cy, cz - height / 2.0))  # base center
    bc = sides + 1
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((0, 1 + i, 1 + j))
        faces.append((bc, 1 + j, 1 + i))
    # NOTE (017 QA): the original winding was backwards on all 16 faces
    # (side + base fan); the order above is the corrected outward winding.
    return mesh_from_data(name, verts, faces, mat)


def octahedron(name, center, scale, mat, rot=(0.0, 0.0, 0.0)):
    """Octahedron (8 triangular faces), scaled (sx, sy, sz)."""
    cx, cy, cz = center
    sx, sy, sz = scale
    verts = [
        (cx, cy, cz + sz), (cx, cy, cz - sz),
        (cx + sx, cy, cz), (cx - sx, cy, cz),
        (cx, cy + sy, cz), (cx, cy - sy, cz),
    ]
    faces = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5),
    ]
    obj = mesh_from_data(name, verts, faces, mat)
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def glow_material(name, color, strength=1.0, roughness=0.4):
    """Principled material with an emission component."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def candlestick(prefix, base_xy, base_z, stem_h, brass, wax, flame_mat):
    """Base + stem + cup + candle + flame cone. Returns list of parts."""
    bx, by = base_xy
    parts = []
    parts.append(cylinder(prefix + "_Base", (bx, by, base_z + 0.025),
                          0.09, 0.05, 8, brass))
    parts.append(cylinder(prefix + "_Stem",
                          (bx, by, base_z + 0.05 + stem_h / 2.0),
                          0.03, stem_h, 8, brass))
    cup_z = base_z + 0.05 + stem_h
    parts.append(cylinder(prefix + "_Cup", (bx, by, cup_z + 0.02),
                          0.06, 0.04, 8, brass))
    candle_z = cup_z + 0.04
    parts.append(cylinder(prefix + "_Candle",
                          (bx, by, candle_z + 0.11),
                          0.045, 0.22, 8, wax))
    flame_z = candle_z + 0.22
    parts.append(cone(prefix + "_Flame", (bx, by, flame_z + 0.06),
                      0.035, 0.12, 8, flame_mat))
    return parts


def main():
    clear_scene()
    make_world_gradient(top=(0.82, 0.85, 0.91), bottom=(0.42, 0.45, 0.55))
    add_ground(size=16.0, color=(0.28, 0.30, 0.36))
    studio_lights(target=(0, 0, 1.6))

    stone_dark = solid_material("Altar_StoneDark", (0.20, 0.21, 0.26),
                                metallic=0.0, roughness=0.95)
    stone_mid = solid_material("Altar_StoneMid", (0.29, 0.30, 0.35),
                               metallic=0.0, roughness=0.95)
    stone_light = solid_material("Altar_StoneLight", (0.38, 0.39, 0.44),
                                 metallic=0.0, roughness=0.95)
    altar_stone = solid_material("Altar_Block", (0.18, 0.19, 0.26),
                                 metallic=0.0, roughness=0.9)
    rune_stone = solid_material("Rune_Stone", (0.25, 0.26, 0.33),
                                metallic=0.0, roughness=0.9)
    rune_glow = glow_material("Rune_Glow", (0.10, 0.60, 0.95),
                              strength=1.8, roughness=0.3)
    crystal_mat = glow_material("Altar_Crystal", (0.15, 0.55, 0.95),
                                strength=1.4, roughness=0.15)
    brass = solid_material("Altar_Brass", (0.78, 0.60, 0.20),
                           metallic=0.9, roughness=0.3)
    wax = solid_material("Candle_Wax", (0.95, 0.90, 0.75),
                         metallic=0.0, roughness=0.6)
    flame_mat = glow_material("Candle_Flame", (1.0, 0.55, 0.15),
                              strength=2.5, roughness=0.3)

    parts = []
    # --- three-tier stone platform (top z = 0.35 / 0.70 / 1.05) ---
    parts.append(cylinder("Platform_Tier1", (0, 0, 0.175),
                          3.0, 0.35, 16, stone_dark))
    parts.append(cylinder("Platform_Tier2", (0, 0, 0.525),
                          2.4, 0.35, 16, stone_mid))
    parts.append(cylinder("Platform_Tier3", (0, 0, 0.875),
                          1.8, 0.35, 16, stone_light))

    # --- front steps onto tier 1 ---
    parts.append(box("Step_Low", (0, -3.45, 0.09),
                     (1.4, 0.5, 0.18), stone_mid))
    parts.append(box("Step_High", (0, -3.15, 0.26),
                     (1.2, 0.4, 0.16), stone_light))

    # --- central altar block + slab top (slab top z = 2.07) ---
    parts.append(box("Altar_Block", (0, 0, 1.50),
                     (1.1, 0.7, 0.9), altar_stone))
    parts.append(box("Altar_Slab", (0, 0, 2.01),
                     (1.4, 1.0, 0.12), stone_light))

    # --- rune ring: glowing torus lying on tier 3 around the altar ---
    bpy.ops.mesh.primitive_torus_add(major_radius=1.35, minor_radius=0.06,
                                     major_segments=24, minor_segments=4,
                                     location=(0, 0, 1.11))
    ring = bpy.context.active_object
    ring.name = "Rune_Ring"
    ring.data.materials.append(rune_glow)
    flat_shade(ring)
    parts.append(ring)

    # --- eight rune stones on tier 2 (top z = 0.70), tilted outward 8 deg ---
    TILT = math.radians(-8.0)
    for i in range(8):
        th = math.radians(i * 45.0)
        cx, cy = 2.0 * math.cos(th), 2.0 * math.sin(th)
        stone = box("RuneStone_%d" % i, (cx, cy, 1.15),
                    (0.35, 0.12, 0.9), rune_stone,
                    rot=(TILT, 0.0, th - math.pi / 2.0))
        parts.append(stone)
        # glowing rune plate on the inner face of the stone
        px = cx - 0.075 * math.cos(th)
        py = cy - 0.075 * math.sin(th)
        plate = box("RunePlate_%d" % i, (px, py, 1.15),
                    (0.20, 0.02, 0.45), rune_glow,
                    rot=(TILT, 0.0, th - math.pi / 2.0))
        parts.append(plate)

    # --- candlesticks: two on the altar slab, one tall on tier 3 ---
    parts += candlestick("Candle_L", (-0.45, 0.0), 2.07, 0.35,
                         brass, wax, flame_mat)
    parts += candlestick("Candle_R", (0.45, 0.0), 2.07, 0.35,
                         brass, wax, flame_mat)
    parts += candlestick("Candle_Tall", (1.25, 0.95), 1.05, 0.55,
                         brass, wax, flame_mat)

    # --- floating crystal + three shards above the altar ---
    parts.append(octahedron("Crystal_Main", (0, 0, 3.15),
                            (0.30, 0.30, 0.45), crystal_mat,
                            rot=(0.0, 0.0, math.radians(45.0))))
    for i, (ang, z) in enumerate(((30.0, 2.95), (150.0, 3.30),
                                  (270.0, 3.05))):
        a = math.radians(ang)
        parts.append(octahedron("Crystal_Shard_%d" % i,
                                (0.85 * math.cos(a), 0.85 * math.sin(a), z),
                                (0.12, 0.12, 0.18), crystal_mat,
                                rot=(0.0, 0.0, math.radians(ang))))

    # --- accent point lights: cool glow at the crystal, warm at candles ---
    def _point(name, loc, energy, color):
        data = bpy.data.lights.new(name, 'POINT')
        data.energy = energy
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        return obj

    _point("CrystalLight", (0, 0, 3.05), 40.0, (0.4, 0.8, 1.0))
    _point("CandleLight", (0, 0, 2.80), 12.0, (1.0, 0.6, 0.25))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    cam = make_camera("Camera", (5.6, -6.2, 4.2), (0, 0, 1.5), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "016-lowpoly-altar.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "016-lowpoly-altar.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "altar_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("ALTAR_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("ALTAR_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "016-lowpoly-altar.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 016 低模场景：魔法祭坛\n\n")
        f.write("低多边形环境场景资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 三层石台：16 边圆柱逐层收窄（半径 3.0 / 2.4 / 1.8，"
                "每层高 0.35），顶面 z=1.05\n")
        f.write("- 祭坛：中央石块 1.1x0.7x0.9 + 顶板 1.4x1.0x0.12"
                "（顶面 z=2.07）\n")
        f.write("- 符文环：发光圆环（主半径 1.35，24x4 段），平铺于三层"
                "石台顶面，环绕祭坛\n")
        f.write("- 符文石：8 块立石（0.35x0.12x0.9），45° 均布于二层石台"
                "（半径 2.0），向外倾斜 8°，内侧各贴一块发光符文板\n")
        f.write("- 烛台：祭坛顶板上两支（黄铜底座 + 杆 + 烛杯 + 蜡烛 + "
                "火焰锥），三层石台上一支高烛台（杆高 0.55）\n")
        f.write("- 悬浮水晶：中央八面体水晶（0.30x0.30x0.45，z=3.15）+ "
                "3 颗小碎片环绕\n")
        f.write("- 台阶：祭坛正面两级石阶，通向一层石台\n")
        f.write("- 补光：水晶处冷色点光（40）+ 烛光处暖色点光（12）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Altar_StoneDark / Mid / Light：三层石台（roughness 0.95）\n")
        f.write("- Altar_Block：祭坛石块；Rune_Stone：符文石\n")
        f.write("- Rune_Glow：青色自发光（强度 1.8），符文环 + 符文板\n")
        f.write("- Altar_Crystal：蓝色水晶自发光（强度 1.4）\n")
        f.write("- Altar_Brass：黄铜烛台（metallic 0.9）\n")
        f.write("- Candle_Wax：米白蜡烛；Candle_Flame：橙色火焰自发光（2.5）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
