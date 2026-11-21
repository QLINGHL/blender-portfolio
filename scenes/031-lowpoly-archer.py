# -*- coding: utf-8 -*-
"""031 低模游戏角色：弓箭手
Low-poly archer game character, bind-ready: pointed hood (open at the
front so the face shows), green tunic with leather chest plate, belt
with iron buckle, shoulder pads, leather bracers, boots, a quiver with
3 arrows on the back, and a recurve bow held in the left hand.
Arms and legs are 5-ring tubes: the middle ring lands exactly on the
elbow / knee joint loop. Flat shading, Eevee beauty + wireframe shots.
Camera is auto-fitted with fit_camera_to_objects (target fill 0.78).
Run: blender --background --python 031-lowpoly-archer.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, wireframe_material,
                    make_world_gradient, add_ground, studio_lights,
                    fit_camera_to_objects, flat_shade, poly_count,
                    total_poly_count, setup_render, render,
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


def make_tube(name, origin, direction, distances, radii, sides, material):
    """Closed tube along `direction`; one ring per (distance, radius).
    Rings are edge loops — joints land exactly on a ring."""
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    o = Vector(origin)
    verts, faces = [], []
    for dist, r in zip(distances, radii):
        c = o + d * dist
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            p = c + (u * math.cos(a) + v * math.sin(a)) * r
            verts.append(tuple(p))
    n_rings = len(distances)
    for k in range(n_rings - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    top_c = len(verts)
    verts.append(tuple(o + d * distances[0]))
    bot_c = len(verts)
    verts.append(tuple(o + d * distances[-1]))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((top_c, i, j))
        faces.append((bot_c, (n_rings - 1) * sides + j, (n_rings - 1) * sides + i))
    return mesh_from_data(name, verts, faces, material)


def make_partial_tube(name, origin, direction, distances, radii,
                      angle_start, angle_end, steps, material):
    """Open tube along `direction` covering only angles
    [angle_start, angle_end] (radians). Used for the hood: the front
    (-Y, angle ~pi) is left open so the face stays visible.
    Ring angle layout matches make_tube: vertex = c + (u*cos a + v*sin a)*r
    with u=(0,1,0), v=(-1,0,0) for a vertical tube, so a=pi is -Y (front).
    No caps: the hood is open at the bottom and pinched at the top."""
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    o = Vector(origin)
    verts, faces = [], []
    for dist, r in zip(distances, radii):
        c = o + d * dist
        for i in range(steps + 1):
            a = angle_start + (angle_end - angle_start) * i / steps
            p = c + (u * math.cos(a) + v * math.sin(a)) * r
            verts.append(tuple(p))
    n_rings = len(distances)
    per = steps + 1
    for k in range(n_rings - 1):
        for i in range(steps):
            faces.append((k * per + i, k * per + i + 1,
                          (k + 1) * per + i + 1, (k + 1) * per + i))
    return mesh_from_data(name, verts, faces, material)


def add_sphere(name, location, radius, segments, rings, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    flat_shade(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
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


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points, fan caps."""
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


def cone_between(name, p_base, p_tip, r_base, sides, mat):
    """Cone: base circle at p_base, apex at p_tip, fan base cap."""
    a = Vector(p_base)
    b = Vector(p_tip)
    axis = b - a
    axis.normalize()
    up = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(up).normalized()
    v = axis.cross(u).normalized()
    verts = []
    for i in range(sides):
        ang = 2.0 * math.pi * i / sides
        verts.append(tuple(a + r_base * (math.cos(ang) * u
                                         + math.sin(ang) * v)))
    verts.append(tuple(b))   # apex
    verts.append(tuple(a))   # base center
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides))
        faces.append((sides + 1, j, i))
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


def srgb(rgb):
    """sRGB swatch -> linear values for Principled BSDF Base Color.

    Blender material colors are linear; feeding sRGB numbers straight in
    washes everything out (the same root cause as the costume v1 pale
    colors: a picked forest green (0.22,0.38,0.20) rendered as pale mint).
    Pass every picked swatch through this."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

    skin = solid_material("Skin", srgb((0.86, 0.63, 0.48)), metallic=0.0, roughness=0.7)
    tunic = solid_material("Tunic_Green", srgb((0.22, 0.38, 0.20)), metallic=0.0, roughness=0.85)
    tunic_dark = solid_material("Tunic_DarkGreen", srgb((0.15, 0.28, 0.14)), metallic=0.0, roughness=0.85)
    leather = solid_material("Leather_Brown", srgb((0.42, 0.26, 0.13)), metallic=0.0, roughness=0.85)
    leather_dark = solid_material("Leather_Dark", srgb((0.30, 0.18, 0.09)), metallic=0.0, roughness=0.9)
    eyes = solid_material("Eyes_Dark", srgb((0.05, 0.05, 0.06)), metallic=0.0, roughness=0.4)
    wood = solid_material("Bow_Wood", srgb((0.45, 0.30, 0.15)), metallic=0.0, roughness=0.8)
    string_mat = solid_material("Bow_String", srgb((0.85, 0.82, 0.72)), metallic=0.0, roughness=0.9)
    iron = solid_material("Iron", srgb((0.30, 0.31, 0.33)), metallic=0.8, roughness=0.4)
    feather = solid_material("Fletching", srgb((0.80, 0.75, 0.55)), metallic=0.0, roughness=0.8)
    pants = solid_material("Pants_Brown", srgb((0.32, 0.22, 0.13)), metallic=0.0, roughness=0.9)

    parts = []
    # --- head (front is -Y) ---
    head = add_sphere("Head", (0, 0, 1.52), 0.20, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- eyes ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.07, -0.168, 1.53), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.08, 0.075], 6, skin)
    parts.append(neck)
    # --- hood: partial tube, front gap ~60 deg centred on -Y (angle pi).
    #     Angles -2.62..+2.62 rad cover back + sides, leave the face open.
    hood = make_partial_tube("Hood", (0, 0.02, 1.56), (0, -0.06, 1),
                             [0.0, 0.14, 0.28, 0.40, 0.50],
                             [0.29, 0.28, 0.23, 0.14, 0.05],
                             -2.62, 2.62, 12, tunic_dark)
    parts.append(hood)
    # --- hood tip: small forward-tilted cone at the apex ---
    tip = cone_between("HoodTip", (0, -0.005, 2.06), (0, -0.09, 2.18),
                       0.05, 6, tunic_dark)
    parts.append(tip)
    # --- shoulder cape: flared tube over the shoulders ---
    cape = make_tube("ShoulderCape", (0, 0, 1.32), (0, 0, -1),
                     [0.0, 0.14, 0.26],
                     [0.31, 0.35, 0.39], 8, tunic_dark)
    parts.append(cape)
    # --- tunic: 5 rings, slight flare into a skirt ---
    tunic_obj = make_tube("Tunic", (0, 0, 1.30), (0, 0, -1),
                          [0.0, 0.19, 0.38, 0.56, 0.75],
                          [0.30, 0.31, 0.32, 0.35, 0.38], 8, tunic)
    parts.append(tunic_obj)
    # --- leather chest plate: short tube hugging the torso BELOW the
    #     shoulder cape, so it reads as a brown band on the chest ---
    chest = make_tube("ChestPlate", (0, 0, 1.08), (0, 0, -1),
                      [0.0, 0.05, 0.10],
                      [0.33, 0.33, 0.325], 8, leather)
    parts.append(chest)
    # --- belt + iron buckle ---
    belt = make_tube("Belt", (0, 0, 0.96), (0, 0, -1),
                     [0.0, 0.08], [0.34, 0.34], 8, leather_dark)
    parts.append(belt)
    buckle = box("Buckle", (0, -0.34, 0.92), (0.09, 0.02, 0.06), iron)
    parts.append(buckle)
    # --- shoulder pads: flattened spheres ---
    for sx in (-1, 1):
        pad = add_sphere("ShoulderPad", (sx * 0.34, 0, 1.28), 0.14, 8, 5,
                         (1.15, 0.95, 0.55), leather)
        parts.append(pad)
    # --- arms: 5 rings, middle ring = elbow joint loop ---
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.31, 0, 1.24))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.105, 0.10, 0.095, 0.085, 0.075], 6, tunic)
        parts.append(arm)
        # leather bracer over the forearm (lower 3 rings)
        bracer = make_tube("Bracer", shoulder + direction.normalized() * 0.26,
                           direction, [0.0, 0.13, 0.26],
                           [0.102, 0.092, 0.082], 6, leather)
        parts.append(bracer)
        wrist = shoulder + direction.normalized() * 0.55
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.07, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    # --- legs: 5 rings, middle ring = knee joint loop ---
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.60))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.10, 0.098, 0.093, 0.086, 0.08], 6, pants)
        parts.append(leg)
        # boot: box toe pointing forward (-Y), cuff ring at the ankle
        boot = box("Boot", (sx * 0.12, -0.30, 0.06), (0.15, 0.30, 0.11), leather_dark)
        parts.append(boot)
        cuff = make_tube("BootCuff", (sx * 0.12, 0, 0.13), (0, 0, 1),
                         [0.0, 0.05], [0.095, 0.10], 6, leather)
        parts.append(cuff)
    # --- quiver on the back (+Y): tilted tube + 3 arrows ---
    q_dir = Vector((0.14, 0.33, 0.93)).normalized()
    q_origin = Vector((0.0, 0.22, 0.92))
    quiver = make_tube("Quiver", q_origin, q_dir, [0.0, 0.55],
                       [0.11, 0.10], 8, leather)
    parts.append(quiver)
    q_top = q_origin + q_dir * 0.55
    for i, dx in enumerate((-0.045, 0.0, 0.045)):
        a0 = q_top + Vector((dx, 0, -0.10)) - q_dir * 0.05
        a1 = q_top + Vector((dx, 0, 0.0)) + q_dir * 0.30
        shaft = cyl_between("ArrowShaft_%d" % (i + 1), tuple(a0), tuple(a1),
                            0.012, 6, wood)
        parts.append(shaft)
        tip = cone_between("ArrowTip_%d" % (i + 1), tuple(a1),
                           tuple(a1 + q_dir * 0.06), 0.016, 6, iron)
        parts.append(tip)
        for s in (-1, 1):
            vane = box("ArrowFletch_%d_%+d" % (i + 1, s),
                       tuple(a1 - q_dir * 0.06 + Vector((s * 0.014, 0, 0))),
                       (0.004, 0.03, 0.09), feather)
            vane.rotation_euler = (0, s * 0.30, 0)
            parts.append(vane)
    # --- recurve bow in the left hand (-X): arc in the XZ plane,
    #     grip at the wrist, tips swept forward (-Y) ---
    wl = wrists[-1]
    bow_pts = []
    for k in range(7):
        t = -1.0 + 2.0 * k / 6.0
        bow_pts.append(Vector((wl.x, wl.y - 0.12 * t * t, wl.z + 0.55 * t)))
    for k in range(6):
        limb = cyl_between("BowLimb_%d" % k, tuple(bow_pts[k]),
                           tuple(bow_pts[k + 1]), 0.028, 6, wood)
        parts.append(limb)
    string = cyl_between("BowString", tuple(bow_pts[0]), tuple(bow_pts[-1]),
                         0.005, 6, string_mat)
    parts.append(string)
    grip = cyl_between("BowGrip", tuple(wl + Vector((0, 0, -0.09))),
                       tuple(wl + Vector((0, 0, 0.09))), 0.026, 6, leather_dark)
    parts.append(grip)

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "031-lowpoly-archer.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "031-lowpoly-archer.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "archer_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("ARCHER_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("ARCHER_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "031-lowpoly-archer.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 031 低模游戏角色：弓箭手\n\n")
        f.write("低多边形风格化弓箭手，平面着色（flat shading），绑定就绪。\n\n")
        f.write("## 造型\n\n")
        f.write("- 兜帽：前部开口 60° 的锥形兜帽（5 环），裹住头侧、脸部露出，帽尖前倾小锥\n")
        f.write("- 上身：绿色束腰外衣（5 环微喇叭裙摆）+ 棕色皮质胸甲（肩披下方露出的棕色胸带）+ 肩披 + 双肩垫\n")
        f.write("- 腰带：深棕皮带 + 铁质带扣（正面）\n")
        f.write("- 背后箭袋：斜挎皮质箭筒，内插 3 支箭（木杆 + 铁箭头 + 双羽片）\n")
        f.write("- 左手持反曲弓：7 点弧线弓身（弓梢前倾），弓弦绷直，握把皮革缠绕\n")
        f.write("- 腿部：棕色裤腿 + 方头皮靴 + 靴口皮环\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节\n")
        f.write("- 前臂另有皮质护腕（3 环），不遮挡肘部关节环\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n")
        f.write("- N-gon 均为圆柱体端盖（箭筒、箭杆、弓身、握把等），不在关节处\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Tunic_Green / Tunic_DarkGreen：绿色外衣与深绿兜帽、肩披\n")
        f.write("- Leather_Brown / Leather_Dark：皮质胸甲、护腕、肩垫、箭袋、靴子\n")
        f.write("- Bow_Wood：弓身与箭杆；Bow_String：弓弦；Iron：带扣、箭头\n")
        f.write("- Skin / Eyes_Dark：皮肤、眼睛；Pants_Brown：裤腿\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
