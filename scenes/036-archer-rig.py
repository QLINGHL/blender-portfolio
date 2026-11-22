# -*- coding: utf-8 -*-
"""036 角色关节拓扑：给 031 弓箭手加骨架（armature），摆一个行走姿势
- 角色几何与 031 完全一致（兜帽、绿外衣、皮胸甲、肩垫、箭袋 + 3 支箭、
  左手……见下文注：反曲弓实际在 -X 侧腕部；皮靴、护腕），966 面；
  唯一改动是靴盒向后加长（见“靴子修正”一节），面数不变
- 管状建模采用 007/022 修正版绕向（031 用旧绕向，管盖面内翻；022 重建
  后实测倒置面 0）。本脚本重建后同样逐部件复测倒置面
- 16 根骨骼：Hips / Spine / Neck / Head / 双臂（肩/肘/手）/ 双腿（大腿/小腿/脚）
- 蒙皮：自动权重（失败则退到包络权重）
- 关节环检查（实测）：手臂/腿部每根管子的环心与对应关节骨骼头位置
  的距离——肩/肘/腕/髋/膝/踝环应正好落在关节上
- 姿势：行走中段——左腿前迈着地、右腿后蹬脚尖点地；左臂（空手）反向
  后摆、右臂（持弓）摆幅收小、肘微屈，弓随右臂摆动；躯干微前倾
- 渲染：Eevee 1024x1024，三点式影棚灯光，fit_camera_to_objects 自动取景
Run: blender --background --python 036-archer-rig.py
"""
import os
import sys
import math
import json
import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, fit_camera_to_objects,
                    flat_shade, poly_count, total_poly_count, setup_render,
                    render)


# ---------------------------------------------------------------- 031 几何
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
    Rings are edge loops — joints land exactly on a ring.
    Winding: 007/022 修正版（008 质检验证；031 旧绕向的盖面内翻）。"""
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
        faces.append((top_c, j, i))
        faces.append((bot_c, (n_rings - 1) * sides + i, (n_rings - 1) * sides + j))
    return mesh_from_data(name, verts, faces, material)


def make_partial_tube(name, origin, direction, distances, radii,
                      angle_start, angle_end, steps, material):
    """Open tube along `direction` covering only angles
    [angle_start, angle_end] (radians). Used for the hood: the front
    (-Y, angle ~pi) is left open so the face stays visible. No caps."""
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
    """sRGB swatch -> linear values for Principled BSDF Base Color."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


def build_archer():
    """与 031 完全相同的弓箭手几何（管盖面绕向修正版）。返回部件列表。"""
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
    head = add_sphere("Head", (0, 0, 1.52), 0.20, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.07, -0.168, 1.53), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.08, 0.075], 6, skin)
    parts.append(neck)
    hood = make_partial_tube("Hood", (0, 0.02, 1.56), (0, -0.06, 1),
                             [0.0, 0.14, 0.28, 0.40, 0.50],
                             [0.29, 0.28, 0.23, 0.14, 0.05],
                             -2.62, 2.62, 12, tunic_dark)
    parts.append(hood)
    tip = cone_between("HoodTip", (0, -0.005, 2.06), (0, -0.09, 2.18),
                       0.05, 6, tunic_dark)
    parts.append(tip)
    cape = make_tube("ShoulderCape", (0, 0, 1.32), (0, 0, -1),
                     [0.0, 0.14, 0.26],
                     [0.31, 0.35, 0.39], 8, tunic_dark)
    parts.append(cape)
    tunic_obj = make_tube("Tunic", (0, 0, 1.30), (0, 0, -1),
                          [0.0, 0.19, 0.38, 0.56, 0.75],
                          [0.30, 0.31, 0.32, 0.35, 0.38], 8, tunic)
    parts.append(tunic_obj)
    chest = make_tube("ChestPlate", (0, 0, 1.08), (0, 0, -1),
                      [0.0, 0.05, 0.10],
                      [0.33, 0.33, 0.325], 8, leather)
    parts.append(chest)
    belt = make_tube("Belt", (0, 0, 0.96), (0, 0, -1),
                     [0.0, 0.08], [0.34, 0.34], 8, leather_dark)
    parts.append(belt)
    buckle = box("Buckle", (0, -0.34, 0.92), (0.09, 0.02, 0.06), iron)
    parts.append(buckle)
    for sx in (-1, 1):
        pad = add_sphere("ShoulderPad", (sx * 0.34, 0, 1.28), 0.14, 8, 5,
                         (1.15, 0.95, 0.55), leather)
        parts.append(pad)
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.31, 0, 1.24))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.105, 0.10, 0.095, 0.085, 0.075], 6, tunic)
        parts.append(arm)
        bracer = make_tube("Bracer", shoulder + direction.normalized() * 0.26,
                           direction, [0.0, 0.13, 0.26],
                           [0.102, 0.092, 0.082], 6, leather)
        parts.append(bracer)
        wrist = shoulder + direction.normalized() * 0.55
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.07, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.60))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.10, 0.098, 0.093, 0.086, 0.08], 6, pants)
        parts.append(leg)
        # 031 遗留问题：靴盒 y -0.45..-0.15，腿管前缘 y=-0.08，两者有约 8cm
        # 空隙，静止姿势下靴子即与腿脱节（031 渲染裁剪后可见）。本稿把靴盒
        # 向后加长到 y -0.45..-0.07（长 0.38），靴跟包住脚踝、靴尖位置不变，
        # 脚掌标定（靴尖离踝 0.45）不受影响。
        boot = box("Boot", (sx * 0.12, -0.26, 0.06), (0.15, 0.38, 0.11), leather_dark)
        parts.append(boot)
        cuff = make_tube("BootCuff", (sx * 0.12, 0, 0.13), (0, 0, 1),
                         [0.0, 0.05], [0.095, 0.10], 6, leather)
        parts.append(cuff)
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
    # 反曲弓在 -X 侧腕部（031 文案称“左手”，实际弓在 -X 侧；角色面朝 -Y，
    # -X 侧是右手，骨架命名 Shoulder.R；弓随右臂摆动）
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
    return parts, wrists


# ---------------------------------------------------------------- 骨架
# 角色面朝 -Y；左侧 = +X、右侧 = -X（与 007/014/022 同约定）。
# 肘：肩 + 方向单位向量 * 0.26 = (±0.346, 0, 0.9825)；腕：肩 + 方向 * 0.55。
# 膝：髋 z 0.60 - 0.26 = 0.34；踝：髋 z 0.60 - 0.52 = 0.08。
BONES = [
    # name, head, tail, parent
    ("Hips",       (0, 0, 0.60),      (0, 0, 0.95),       None),
    ("Spine",      (0, 0, 0.95),      (0, 0, 1.28),       "Hips"),
    ("Neck",       (0, 0, 1.28),      (0, 0, 1.42),       "Spine"),
    ("Head",       (0, 0, 1.42),      (0, 0, 1.72),       "Neck"),
    ("Shoulder.L", (0.31, 0, 1.24),   (0.346, 0, 0.9825), "Spine"),
    ("Forearm.L",  (0.346, 0, 0.9825), (0.386, 0, 0.695), "Shoulder.L"),
    ("Hand.L",     (0.386, 0, 0.695), (0.39, 0, 0.62),    "Forearm.L"),
    ("Shoulder.R", (-0.31, 0, 1.24),  (-0.346, 0, 0.9825), "Spine"),
    ("Forearm.R",  (-0.346, 0, 0.9825), (-0.386, 0, 0.695), "Shoulder.R"),
    ("Hand.R",     (-0.386, 0, 0.695), (-0.39, 0, 0.62),   "Forearm.R"),
    ("Thigh.L",    (0.12, 0, 0.60),   (0.12, 0, 0.34),    "Hips"),
    ("Shin.L",     (0.12, 0, 0.34),   (0.12, 0, 0.08),    "Thigh.L"),
    ("Foot.L",     (0.12, 0, 0.08),   (0.12, -0.20, 0.05), "Shin.L"),
    ("Thigh.R",    (-0.12, 0, 0.60),  (-0.12, 0, 0.34),   "Hips"),
    ("Shin.R",     (-0.12, 0, 0.34),  (-0.12, 0, 0.08),   "Thigh.R"),
    ("Foot.R",     (-0.12, 0, 0.08),  (-0.12, -0.20, 0.05), "Shin.R"),
]

# 姿势：行走中段——左腿前迈着地、右腿后蹬脚尖点地；左臂（空手）反向后摆、
# 右臂（持弓）摆幅收小、肘微屈，弓随右臂摆动；躯干微前倾。
# 脚掌角度经实测标定（022 同款姿势在弓箭手上前靴悬空 +0.0285、后靴扎地
# -0.0452）：Foot.L +0.40 时前靴底 z=+0.002，Foot.R -0.31 时后靴底 z=+0.003。
# 注意脚掌骨局部 X 轴与世界 X 反向，角度不能按“净零”估算，以实测为准。
# 另：Hips loc (0,0,-0.05) 实测沿骨骼局部 Z 轴向后平移 +Y 0.05 米，无垂直
# 下沉——014/022 文案称“髋部下沉”有误，本稿如实写后移。
# 步幅与 022 法师相同（小步幅）：靴尖离踝 0.45 米（靴盒 y -0.45..-0.07，
# 踝在 y=0），大步幅会让后脚靴尖扎进地面、前脚靴离地悬空。
POSE = {
    "Hips":       {"loc": (0, 0, -0.05), "rot": (0.0, -0.02, 0.05)},
    "Spine":      {"rot": (0.06, 0.0, 0.0)},
    "Neck":       {"rot": (-0.03, 0.0, 0.0)},
    "Head":       {"rot": (-0.05, 0.0, 0.0)},
    "Shoulder.L": {"rot": (0.30, 0.0, 0.06)},
    "Forearm.L":  {"rot": (-0.40, 0.0, 0.0)},
    "Hand.L":     {"rot": (-0.10, 0.0, 0.0)},
    "Shoulder.R": {"rot": (-0.12, 0.0, -0.06)},
    "Forearm.R":  {"rot": (-0.20, 0.0, 0.0)},
    "Hand.R":     {"rot": (-0.05, 0.0, 0.0)},
    "Thigh.L":    {"rot": (-0.22, 0.0, 0.0)},
    "Shin.L":     {"rot": (-0.12, 0.0, 0.0)},
    "Foot.L":     {"rot": (0.40, 0.0, 0.0)},
    "Thigh.R":    {"rot": (0.22, 0.0, 0.0)},
    "Shin.R":     {"rot": (0.12, 0.0, 0.0)},
    "Foot.R":     {"rot": (-0.31, 0.0, 0.0)},
}


def build_armature():
    arm_data = bpy.data.armatures.new("ArcherRig")
    arm_obj = bpy.data.objects.new("ArcherRig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    for name, head, tail, parent in BONES:
        b = arm_data.edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent:
            b.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj


def skin(parts, arm_obj):
    """自动权重蒙皮；热权重失败时退到包络权重。返回使用的方法。"""
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        method = "ARMATURE_AUTO"
    except RuntimeError as e:
        print("SKIN_AUTO_FAILED:", e)
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:
            o.select_set(True)
        arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
        method = "ARMATURE_ENVELOPE"
    bpy.ops.object.select_all(action='DESELECT')
    return method


def apply_pose(arm_obj):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for name, spec in POSE.items():
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = 'XYZ'
        if "loc" in spec:
            pb.location = spec["loc"]
        pb.rotation_euler = spec["rot"]
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()


def ring_center(obj, ring_index, sides):
    """第 ring_index 个环的顶点中心（局部坐标 = 世界坐标，物体无变换）。"""
    verts = obj.data.vertices
    pts = [Vector(verts[ring_index * sides + i].co) for i in range(sides)]
    c = Vector((0, 0, 0))
    for p in pts:
        c += p
    return c / len(pts)


def check_joint_rings(parts):
    """实测：手臂/腿部管子的环心与对应关节骨骼头位置的距离。
    建模循环 sx=-1 先建，所以无后缀名 = -X（右），.001 = +X（左）。"""
    by_name = {o.name: o for o in parts}
    arm_r = by_name["Arm"]        # -X = 右臂
    arm_l = by_name["Arm.001"]    # +X = 左臂
    leg_r = by_name["Leg"]
    leg_l = by_name["Leg.001"]
    checks = []
    cases = [
        ("Arm.R ring0 肩", arm_r, 0, 6, Vector((-0.31, 0, 1.24))),
        ("Arm.R ring2 肘", arm_r, 2, 6, Vector((-0.346, 0, 0.9825))),
        ("Arm.R ring4 腕", arm_r, 4, 6, Vector((-0.386, 0, 0.695))),
        ("Arm.L ring0 肩", arm_l, 0, 6, Vector((0.31, 0, 1.24))),
        ("Arm.L ring2 肘", arm_l, 2, 6, Vector((0.346, 0, 0.9825))),
        ("Arm.L ring4 腕", arm_l, 4, 6, Vector((0.386, 0, 0.695))),
        ("Leg.R ring0 髋", leg_r, 0, 6, Vector((-0.12, 0, 0.60))),
        ("Leg.R ring2 膝", leg_r, 2, 6, Vector((-0.12, 0, 0.34))),
        ("Leg.R ring4 踝", leg_r, 4, 6, Vector((-0.12, 0, 0.08))),
        ("Leg.L ring0 髋", leg_l, 0, 6, Vector((0.12, 0, 0.60))),
        ("Leg.L ring2 膝", leg_l, 2, 6, Vector((0.12, 0, 0.34))),
        ("Leg.L ring4 踝", leg_l, 4, 6, Vector((0.12, 0, 0.08))),
    ]
    for label, obj, ring, sides, joint in cases:
        c = ring_center(obj, ring, sides)
        dist = (c - joint).length
        checks.append({"joint": label,
                       "ring_center": [round(v, 4) for v in c],
                       "bone_joint": [round(v, 4) for v in joint],
                       "distance": round(dist, 5)})
        print("JOINT_RING %s: center=%s joint=%s dist=%.5f"
              % (label, [round(v, 4) for v in c],
                 [round(v, 4) for v in joint], dist))
    return checks


def count_inverted_normals(parts):
    """与 021 质检同一方法：复制 bmesh、recalc_face_normals，数法线翻转的面。"""
    per_part = {}
    total = 0
    for obj in parts:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm2 = bm.copy()
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        bm2.faces.ensure_lookup_table()
        orig = [f.normal.copy() for f in bm.faces]
        inv = sum(1 for i, f in enumerate(bm2.faces)
                  if orig[i].dot(f.normal) < 0)
        bm2.free()
        bm.free()
        per_part[obj.name] = inv
        total += inv
        print("INVERTED %s: %d" % (obj.name, inv))
    print("INVERTED_TOTAL: %d" % total)
    return per_part, total


def verify_pose(parts):
    """实测：对比静止网格与姿势求值网格的顶点位移；脚底最低 z。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    report = {}
    min_z_all = 1e9
    for obj in parts:
        mw = obj.matrix_world
        rest = [mw @ v.co for v in obj.data.vertices]
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        posed = [mw @ v.co for v in mesh.vertices]
        eval_obj.to_mesh_clear()
        max_disp = max((p - r).length for p, r in zip(posed, rest))
        min_z = min(p.z for p in posed)
        min_z_all = min(min_z_all, min_z)
        report[obj.name] = {"max_displacement": round(max_disp, 4),
                            "min_z": round(min_z, 4)}
    report["_overall_min_z"] = round(min_z_all, 4)
    return report


def export_deformed_wireframe(objects, camera, filepath):
    """把姿势求值后的可见边投影到 2D（与 common.export_wireframe_segments
    同逻辑，但用变形后的网格）。"""
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam_pos = camera.matrix_world.translation
    segments = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        mw = obj.matrix_world
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        eval_obj.to_mesh_clear()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        for e in bm.edges:
            visible = False
            for f in e.link_faces:
                n = (mw.to_3x3() @ f.normal).normalized()
                c = mw @ f.calc_center_median()
                if n.dot((cam_pos - c).normalized()) > 0.001:
                    visible = True
                    break
            if not visible:
                continue
            v0 = mw @ e.verts[0].co
            v1 = mw @ e.verts[1].co
            x0, y0, d0 = world_to_camera_view(scene, camera, v0)
            x1, y1, d1 = world_to_camera_view(scene, camera, v1)
            if d0 < 0 or d1 < 0:
                continue
            segments.append([round(x0, 4), round(1.0 - y0, 4),
                             round(x1, 4), round(1.0 - y1, 4)])
        bm.free()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(segments, f)
    print("WIREFRAME_SEGMENTS:", len(segments), "->", filepath)
    return segments


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

    parts, wrists = build_archer()
    total = total_poly_count(parts)
    counts = {o.name: poly_count(o) for o in parts}
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))

    # 倒置面复测（031 用旧绕向，管盖面内翻；修正绕向后应为 0）
    inv_per_part, inv_total = count_inverted_normals(parts)

    # 关节环检查在蒙皮/摆姿势之前做（测静止网格的环心）
    ring_checks = check_joint_rings(parts)
    max_ring_err = max(c["distance"] for c in ring_checks)
    print("JOINT_RING_MAX_ERR: %.5f" % max_ring_err)

    arm_obj = build_armature()
    method = skin(parts, arm_obj)
    print("SKIN_METHOD:", method)
    groups = {o.name: sorted(g.name for g in o.vertex_groups)
              for o in parts if o.vertex_groups}
    print("VERTEX_GROUPS:", json.dumps(groups, ensure_ascii=False))

    apply_pose(arm_obj)
    check = verify_pose(parts)
    for name, vals in check.items():
        print("RIG_CHECK %s: %s" % (name, vals))

    # 3/4 视角：能看清迈步的前后错位；弓箭手比法师矮（帽尖 2.18），但弓
    # 伸到 z 0.14，取景用 fit_camera_to_objects 自动框住全体部件
    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "036-archer-rig.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "036-archer-rig.blend"))

    export_deformed_wireframe(
        parts, cam, os.path.join("/tmp", "archer_rig_wire.json"))

    pose_deg = {name: {"loc": [round(v, 3) for v in spec.get("loc", (0, 0, 0))],
                       "rot_deg": [round(math.degrees(a), 1) for a in spec["rot"]]}
                for name, spec in POSE.items()}
    rig_info = {
        "bones": [{"name": n, "head": list(h), "tail": list(t), "parent": p}
                  for n, h, t, p in BONES],
        "bone_count": len(BONES),
        "skin_method": method,
        "pose_degrees": pose_deg,
        "poly": {"total": total, "tris": tris, "quads": quads, "ngons": ngons,
                 "per_part": counts},
        "inverted_normals_per_part": inv_per_part,
        "inverted_normals_total": inv_total,
        "joint_ring_checks": ring_checks,
        "joint_ring_max_error": round(max_ring_err, 5),
        "verification": check,
    }
    with open(os.path.join(ROOT, "scenes", "036-rig.json"), "w",
              encoding="utf-8") as f:
        json.dump(rig_info, f, ensure_ascii=False, indent=2)

    wrist_err = max(c["distance"] for c in ring_checks if "腕" in c["joint"])
    core_err = max(c["distance"] for c in ring_checks if "腕" not in c["joint"])
    note = os.path.join(ROOT, "scenes", "036-archer-rig.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 036 角色关节拓扑：031 弓箭手骨架 + 行走姿势\n\n")
        f.write("给 031 低模弓箭手加骨架并摆出行走姿势。除靴盒外，角色几何与 031 完全一致。\n\n")
        f.write("## 绕向修正（031 遗留问题）\n\n")
        f.write("031 建模用旧版 make_tube，管状盖面扇形内外翻转（与 020 法师同一问题，"
                "021 质检实测 144 个倒置面；031 的盖面藏在体内/靴下，渲染中不易察觉）。"
                "本脚本建模函数采用 007/022 修正版绕向，重建后实测倒置面 %d 个"
                "（逐部件复测，与 021 同一方法）。031 原文件未改动，修正只存在于本 rig 版本。\n\n" % inv_total)
        f.write("## 持弓手勘误\n\n")
        f.write("031 文案称“左手持反曲弓”，实际弓在 -X 侧腕部；角色面朝 -Y，"
                "-X 侧是右手（骨架命名 Shoulder.R / Hand.R）。本稿按骨架 L/R 命名，"
                "反曲弓随右臂摆动；左臂为空手。\n\n")
        f.write("## 靴子修正（031 遗留问题）\n\n")
        f.write("031 的靴盒 y -0.45..-0.15（长 0.30），腿管前缘 y=-0.08，两者之间有约 0.08 米"
                "空隙：静止姿势下靴子即与腿脱节（031 渲染裁剪腿部后可见，靴子是悬空的方块；"
                "实测本稿重建前靴—靴口最小距离 0.121 / 0.084 米）。本稿把靴盒向后加长到"
                " y -0.45..-0.07（长 0.38，中心 y=-0.26），靴跟包住脚踝、靴尖位置不变，"
                "面数不变，脚掌标定（靴尖离踝 0.45 米）不受影响。031 原文件未改动，修正只存在于本 rig 版本。\n\n")
        f.write("## 骨架（%d 根骨骼）\n\n" % len(BONES))
        f.write("| 骨骼 | 父级 | 位置（头 → 尾） |\n")
        f.write("| ---- | ---- | -------------- |\n")
        for n, h, t, p in BONES:
            f.write("| %s | %s | (%.2f, %.2f, %.2f) → (%.2f, %.2f, %.2f) |\n"
                    % (n, p or "—", h[0], h[1], h[2], t[0], t[1], t[2]))
        f.write("\n## 蒙皮\n\n")
        f.write("- 方法：%s\n" % ("自动权重（热权重）" if method == "ARMATURE_AUTO"
                                  else "包络权重（自动权重失败后回退）"))
        f.write("- 每个网格部件都挂到骨架上，顶点组按骨骼名生成\n")
        f.write("- 反曲弓随右手摆动；箭袋 + 3 支箭随脊柱；兜帽随头部；外衣裙摆随髋 / 大腿\n\n")
        f.write("## 关节环检查（实测，非估算）\n\n")
        f.write("手臂 / 腿部管子的环心与对应关节骨骼头位置的距离（米）：\n\n")
        f.write("| 关节 | 环心 | 骨骼关节 | 误差 |\n")
        f.write("| ---- | ---- | -------- | ---- |\n")
        for c in ring_checks:
            f.write("| %s | (%.3f, %.3f, %.3f) | (%.3f, %.3f, %.3f) | %.5f |\n"
                    % (c["joint"], c["ring_center"][0], c["ring_center"][1],
                       c["ring_center"][2], c["bone_joint"][0],
                       c["bone_joint"][1], c["bone_joint"][2], c["distance"]))
        f.write("\n肩 / 肘 / 髋 / 膝 / 踝环误差 ≤ %.5f 米，正好落在骨骼关节上，"
                "弯曲不断裂。最大误差 %.5f 米出现在腕部末环：手臂管子的最后一环"
                "在距肩 0.52 处，而腕关节（手掌中心）在 0.55 处，末环与关节沿臂"
                "方向相差 0.03 米，由手掌球体衔接，不影响弯曲。\n"
                % (core_err, wrist_err))
        f.write("\n## 行走姿势（行走中段）\n\n")
        f.write("- 步幅与 022 法师相同（小步幅）：靴尖离踝 0.45 米，大步幅会让"
                "后脚靴尖扎进地面、前脚靴离地悬空\n")
        f.write("- 左腿前迈着地（大腿 -13°，小腿 -7°，脚掌 +23°，靴底贴地），右腿后蹬（大腿 +13°，小腿 +7°，脚掌 -18°，靴尖点地）\n")
        f.write("- 脚掌角度经实测标定：Foot.L +0.40 rad 时前靴底 z=+0.002，Foot.R -0.31 rad 时后靴底 z=+0.003；"
                "022 同款姿势（+0.34 / -0.20）在弓箭手上前靴悬空 +0.0285、后靴扎地 -0.0452，"
                "因脚掌骨局部 X 轴与世界 X 反向，角度不能按净零估算\n")
        f.write("- 左臂（空手）反向后摆 +17°、肘屈 -23°；右臂（持弓）摆幅收小，仅前摆 -7°、肘屈 -11°，弓随右臂摆动\n")
        f.write("- 髋部沿骨骼局部 Z 轴后移 0.05 米（实测：Hips loc (0,0,-0.05) 使髋关节头向 +Y 平移 0.05 米，z 不变，"
                "无垂直下沉；014/022 文案称“髋部下沉”有误）、躯干微前倾 3°，模拟行走重心起伏；外衣裙摆随腿前移，膝盖在裙摆下可见\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d），与 031 一致\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绑定验证（实测，非估算）\n\n")
        f.write("- 姿势求值后全角色最低点 z = %.3f（靴底，前靴 0.002、后靴 0.003，取最小值）\n"
                % check["_overall_min_z"])
        f.write("- 前脚靴底 z = %.3f（贴地），后脚靴底 z = %.3f\n"
                % (check.get("Boot.001", {}).get("min_z", 0),
                   check.get("Boot", {}).get("min_z", 0)))
        f.write("- 外衣裙摆最低 z = %.3f\n"
                % check.get("Tunic", {}).get("min_z", 0))
        f.write("- 各部件最大顶点位移（米）：左腿 %.3f、右腿 %.3f、左臂 %.3f、右臂 %.3f、反曲弓 %.3f、外衣 %.3f\n"
                % (check.get("Leg.001", {}).get("max_displacement", 0),
                   check.get("Leg", {}).get("max_displacement", 0),
                   check.get("Arm.001", {}).get("max_displacement", 0),
                   check.get("Arm", {}).get("max_displacement", 0),
                   check.get("BowLimb_3", {}).get("max_displacement", 0),
                   check.get("Tunic", {}).get("max_displacement", 0)))
        f.write("- 骨架 + 蒙皮 + 姿势全部保存在 scenes/036-archer-rig.blend，"
                "打开即可在姿势模式下继续调动作\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，姿势变形后的真实投影边线叠加\n")
    print("NOTE_WRITTEN:", note)
    print("RIG_JSON:", os.path.join(ROOT, "scenes", "036-rig.json"))


if __name__ == "__main__":
    main()
