# -*- coding: utf-8 -*-
"""011 低模场景：小木屋（低多边形环境资产）
Low-poly log cabin scene: stacked-log walls with a real door opening,
gabled roof, chimney, surface windows, steps, pine tree, rocks and a
stone path. Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 011-lowpoly-cabin.py
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


def box(name, center, size, mat, rot=(0.0, 0.0, 0.0)):
    """Box from center + (sx, sy, sz), optional rotation.
    Geometry is built in local space so rotation pivots on the center."""
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz),
        (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz),
        (sx, sy, sz), (-sx, sy, sz),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = center
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def cylinder(name, center, radius, height, sides, mat,
             rot=(0.0, 0.0, 0.0)):
    """Vertical (Z-axis) cylinder, optionally rotated.
    Geometry is built in local space so rotation pivots on the center."""
    verts = []
    for z in (-height / 2.0, height / 2.0):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((radius * math.cos(a),
                          radius * math.sin(a), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(sides + i for i in range(sides)))
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = center
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def cone(name, center, radius, height, sides, mat):
    """Cone (pointed top), vertical."""
    cx, cy, cz = center
    verts = [(cx, cy, cz + height / 2.0)]
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        verts.append((cx + radius * math.cos(a),
                      cy + radius * math.sin(a), cz - height / 2.0))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((0, 1 + j, 1 + i))
    faces.append(tuple(reversed(range(1, sides + 1))))
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


def main():
    clear_scene()
    make_world_gradient()
    add_ground(size=16.0, color=(0.42, 0.60, 0.30))
    studio_lights(target=(0, 0, 1.2))

    log = solid_material("Cabin_Log", (0.55, 0.38, 0.20),
                         metallic=0.0, roughness=0.85)
    log_end = solid_material("Cabin_LogEnd", (0.72, 0.55, 0.34),
                             metallic=0.0, roughness=0.9)
    roof_mat = solid_material("Cabin_Roof", (0.35, 0.16, 0.12),
                              metallic=0.0, roughness=0.9)
    gable_mat = solid_material("Cabin_Gable", (0.48, 0.33, 0.18),
                               metallic=0.0, roughness=0.85)
    door_mat = solid_material("Cabin_Door", (0.30, 0.18, 0.08),
                              metallic=0.0, roughness=0.8)
    frame_mat = solid_material("Cabin_Frame", (0.62, 0.46, 0.26),
                               metallic=0.0, roughness=0.85)
    glass_mat = solid_material("Cabin_Glass", (0.45, 0.65, 0.80),
                               metallic=0.1, roughness=0.15)
    stone_mat = solid_material("Cabin_Stone", (0.55, 0.55, 0.58),
                               metallic=0.0, roughness=0.95)
    brick_mat = solid_material("Cabin_Brick", (0.55, 0.25, 0.18),
                               metallic=0.0, roughness=0.9)
    pine_mat = solid_material("Pine_Needles", (0.16, 0.38, 0.18),
                              metallic=0.0, roughness=0.9)
    trunk_mat = solid_material("Pine_Trunk", (0.35, 0.22, 0.12),
                               metallic=0.0, roughness=0.9)
    rock_mat = solid_material("Rock", (0.50, 0.50, 0.52),
                              metallic=0.0, roughness=0.95)
    brass = solid_material("Brass_Handle", (0.78, 0.60, 0.20),
                           metallic=0.9, roughness=0.3)

    parts = []
    # --- cabin dimensions ---
    W, D = 4.0, 3.0          # footprint (x, y)
    LOG_R = 0.14             # log radius
    ROWS = 8                 # log rows -> wall height 2.24
    WALL_H = 2 * LOG_R * ROWS
    DOOR_W, DOOR_H = 0.95, 1.70
    SIDES = 8

    # --- log walls: front/back logs run along X, side logs along Y ---
    # front wall (y = -D/2): rows below door top split around the door
    for r in range(ROWS):
        z = LOG_R + r * 2 * LOG_R
        if z + LOG_R <= DOOR_H + 0.01:
            # split: left segment and right segment around the door gap
            seg_len = (W - DOOR_W) / 2.0
            for sgn, cx in ((-1, -(DOOR_W / 2 + seg_len / 2)),
                            (1, DOOR_W / 2 + seg_len / 2)):
                parts.append(cylinder(
                    "Log_Front_R%d_%s" % (r, "L" if sgn < 0 else "R"),
                    (cx, -D / 2, z), LOG_R, seg_len, SIDES, log,
                    rot=(0.0, math.radians(90.0), 0.0)))
        else:
            parts.append(cylinder("Log_Front_R%d" % r, (0, -D / 2, z),
                                  LOG_R, W, SIDES, log,
                                  rot=(0.0, math.radians(90.0), 0.0)))
        # back wall: full logs
        parts.append(cylinder("Log_Back_R%d" % r, (0, D / 2, z),
                              LOG_R, W, SIDES, log,
                              rot=(0.0, math.radians(90.0), 0.0)))
        # side walls: logs along Y, inset so corners interlock visually
        for sx in (-W / 2, W / 2):
            parts.append(cylinder(
                "Log_Side_R%d_%s" % (r, "L" if sx < 0 else "R"),
                (sx, 0, z), LOG_R, D - 2 * LOG_R, SIDES, log,
                rot=(math.radians(90.0), 0.0, 0.0)))
    # log-end caps: small discs on the front/back wall ends (cross-section)
    for r in range(ROWS):
        z = LOG_R + r * 2 * LOG_R
        for sx in (-W / 2, W / 2):
            parts.append(cylinder("LogEnd_F_R%d_%s" % (r, "L" if sx < 0 else "R"),
                                  (sx, -D / 2 - 0.005, z), LOG_R * 0.92,
                                  0.03, SIDES, log_end,
                                  rot=(math.radians(90.0), 0.0, 0.0)))
            parts.append(cylinder("LogEnd_B_R%d_%s" % (r, "L" if sx < 0 else "R"),
                                  (sx, D / 2 + 0.005, z), LOG_R * 0.92,
                                  0.03, SIDES, log_end,
                                  rot=(math.radians(90.0), 0.0, 0.0)))

    # --- gable triangles at x = +/-W/2 (prism, thickness 0.14) ---
    # triangle in (y, z): base y=-D/2..D/2 at z=WALL_H, apex (0, WALL_H+1.1)
    GABLE_H = 1.10
    for sx in (-W / 2, W / 2):
        t = 0.07
        verts = [
            (sx - t, -D / 2, WALL_H), (sx + t, -D / 2, WALL_H),
            (sx + t, D / 2, WALL_H), (sx - t, D / 2, WALL_H),
            (sx - t, 0.0, WALL_H + GABLE_H),
            (sx + t, 0.0, WALL_H + GABLE_H),
        ]
        faces = [(0, 4, 3), (1, 2, 5), (0, 1, 5, 4),
                 (3, 4, 5, 2), (0, 3, 2, 1)]
        parts.append(mesh_from_data(
            "Gable_%s" % ("L" if sx < 0 else "R"), verts, faces, gable_mat))

    # --- roof: two sloped slabs + ridge beam ---
    EAVE_Y, EAVE_Z = D / 2 + 0.45, WALL_H - 0.15
    RIDGE_Z = WALL_H + GABLE_H + 0.12
    slope_len = math.hypot(EAVE_Y, RIDGE_Z - EAVE_Z)
    slope_ang = math.atan2(RIDGE_Z - EAVE_Z, EAVE_Y)
    for sgn in (-1, 1):
        mid_y = sgn * EAVE_Y / 2.0
        mid_z = (EAVE_Z + RIDGE_Z) / 2.0
        parts.append(box("Roof_%s" % ("F" if sgn < 0 else "B"),
                         (0, mid_y, mid_z),
                         (W + 0.9, slope_len + 0.15, 0.12), roof_mat,
                         rot=(-sgn * slope_ang, 0.0, 0.0)))
    parts.append(box("RidgeBeam", (0, 0, RIDGE_Z + 0.02),
                     (W + 0.95, 0.22, 0.14), log_end))

    # --- chimney on the back roof slope ---
    parts.append(box("Chimney", (1.2, 0.75, 3.30),
                     (0.55, 0.55, 1.30), brick_mat))
    parts.append(box("Chimney_Cap", (1.2, 0.75, 3.98),
                     (0.70, 0.70, 0.10), stone_mat))
    parts.append(box("Chimney_Top", (1.2, 0.75, 4.06),
                     (0.40, 0.40, 0.12), brick_mat))

    # --- door (front wall, recessed panel + frame + handle) ---
    parts.append(box("Door_Frame_L", (-(DOOR_W / 2 + 0.07), -D / 2 - 0.03,
                                      DOOR_H / 2),
                     (0.14, 0.10, DOOR_H + 0.14), frame_mat))
    parts.append(box("Door_Frame_R", ((DOOR_W / 2 + 0.07), -D / 2 - 0.03,
                                      DOOR_H / 2),
                     (0.14, 0.10, DOOR_H + 0.14), frame_mat))
    parts.append(box("Door_Frame_Top", (0, -D / 2 - 0.03, DOOR_H + 0.07),
                     (DOOR_W + 0.28, 0.10, 0.14), frame_mat))
    parts.append(box("Door_Panel", (0, -D / 2 - 0.02, DOOR_H / 2),
                     (DOOR_W, 0.08, DOOR_H), door_mat))
    parts.append(box("Door_Plank_V", (0, -D / 2 - 0.07, DOOR_H / 2),
                     (0.06, 0.03, DOOR_H - 0.1), log_end))
    parts.append(box("Door_Handle", (DOOR_W / 2 - 0.16, -D / 2 - 0.09, 0.95),
                     (0.07, 0.07, 0.07), brass))
    # steps in front of the door
    parts.append(box("Step_1", (0, -D / 2 - 0.45, 0.10),
                     (1.3, 0.6, 0.20), stone_mat))
    parts.append(box("Step_2", (0, -D / 2 - 0.85, 0.05),
                     (1.5, 0.5, 0.10), stone_mat))

    # --- windows on the front wall (surface-mounted frames + glass) ---
    # log surface sits at y=-D/2-LOG_R=-1.64: mount frames proud of it
    for wx in (-1.30, 1.30):
        parts.append(box("Window_Frame_%d" % int(abs(wx) * 10),
                         (wx, -D / 2 - 0.18, 1.35),
                         (0.85, 0.10, 0.95), frame_mat))
        parts.append(box("Window_Glass_%d" % int(abs(wx) * 10),
                         (wx, -D / 2 - 0.21, 1.35),
                         (0.65, 0.06, 0.75), glass_mat))
        parts.append(box("Window_BarV_%d" % int(abs(wx) * 10),
                         (wx, -D / 2 - 0.24, 1.35),
                         (0.05, 0.03, 0.75), frame_mat))
        parts.append(box("Window_BarH_%d" % int(abs(wx) * 10),
                         (wx, -D / 2 - 0.24, 1.35),
                         (0.65, 0.03, 0.05), frame_mat))
        parts.append(box("Window_Sill_%d" % int(abs(wx) * 10),
                         (wx, -D / 2 - 0.22, 0.86),
                         (0.95, 0.16, 0.07), stone_mat))
    # back window (one, centered)
    parts.append(box("Window_Back_Frame", (0, D / 2 + 0.18, 1.35),
                     (0.85, 0.10, 0.95), frame_mat))
    parts.append(box("Window_Back_Glass", (0, D / 2 + 0.21, 1.35),
                     (0.65, 0.06, 0.75), glass_mat))

    # --- pine tree at (-3.9, -0.8): front-left, visible in frame ---
    tx, ty = -3.9, -0.8
    parts.append(cylinder("Pine_Trunk", (tx, ty, 0.45), 0.13, 0.9, 8,
                          trunk_mat))
    for i, (r, h, z) in enumerate(((1.15, 1.3, 1.45),
                                   (0.88, 1.15, 2.25),
                                   (0.60, 1.0, 2.95))):
        parts.append(cone("Pine_Cone_%d" % i, (tx, ty, z), r, h, 8,
                          pine_mat))

    # --- rocks (icospheres, low detail) ---
    random.seed(7)
    for i, (rx, ry, s) in enumerate(((-2.6, -2.4, 0.42),
                                     (2.9, 1.6, 0.55),
                                     (3.3, -1.4, 0.34))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=s,
                                              location=(rx, ry, s * 0.55))
        rock = bpy.context.active_object
        rock.name = "Rock_%d" % i
        rock.data.materials.append(rock_mat)
        rock.scale = (1.0, random.uniform(0.7, 0.9), 0.62)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        flat_shade(rock)
        parts.append(rock)

    # --- stone path from the steps toward the camera ---
    for i, (px, py) in enumerate(((0.05, -2.9), (-0.12, -3.6),
                                  (0.10, -4.3), (-0.06, -5.0))):
        parts.append(cylinder("PathStone_%d" % i, (px, py, 0.035),
                              0.38, 0.07, 8, stone_mat))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    cam = make_camera("Camera", (5.8, -6.4, 4.2), (0, 0, 1.3), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "011-lowpoly-cabin.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "011-lowpoly-cabin.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "cabin_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("CABIN_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CABIN_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "011-lowpoly-cabin.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 011 低模场景：小木屋\n\n")
        f.write("低多边形环境场景资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 原木墙：8 排 8 边原木叠砌（前/后墙沿 X、侧墙沿 Y），"
                "前墙门洞处 6 排原木左右分段留出 0.95m 宽门洞\n")
        f.write("- 端头圆盘：前后墙两端各 8 个原木截面圆盘（浅色木纹）\n")
        f.write("- 山墙：两侧三角形棱柱，墙高 2.24m、山墙高 1.10m\n")
        f.write("- 屋顶：两块斜坡板（坡角约 36°，出檐 0.45m）+ 脊梁\n")
        f.write("- 烟囱：砖砌烟囱 + 石盖板，立于后坡屋顶\n")
        f.write("- 门：木门板 + 门框 + 竖纹饰条 + 黄铜把手，门前两级石阶\n")
        f.write("- 窗：前墙两扇（框 + 玻璃 + 十字窗棂 + 石窗台），"
                "后墙一扇\n")
        f.write("- 环境：松树 1 棵（三层锥形树冠 + 树干）、"
                "低多边形岩石 3 块、石板小径 4 块\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Cabin_Log：原木（roughness 0.85）\n")
        f.write("- Cabin_LogEnd：原木截面浅色\n")
        f.write("- Cabin_Roof：深红棕屋顶\n")
        f.write("- Cabin_Gable：山墙木色\n")
        f.write("- Cabin_Door：深色木门；Cabin_Frame：浅色窗框/门框\n")
        f.write("- Cabin_Glass：蓝灰玻璃（roughness 0.15）\n")
        f.write("- Cabin_Stone：石阶/窗台/石板；Cabin_Brick：砖烟囱\n")
        f.write("- Pine_Needles：松针绿；Pine_Trunk：树干棕\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
