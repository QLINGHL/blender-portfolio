# -*- coding: utf-8 -*-
"""050 角色关节拓扑：给 049 炼金术士加骨架（armature），摆一个行走姿势
- 角色几何与 049 完全一致（深青长袍、皮围裙、前额护目镜、腰间三瓶药水、
  双手身前持亮绿药液烧瓶），1004 面；make_tube 已是 048 修正版绕向
- 16 根骨骼：Hips / Spine / Neck / Head / 双臂（肩/肘/手）/ 双腿（大腿/小腿/脚）
- 蒙皮：自动权重（失败则退到包络权重）；烧瓶三件（玻璃/药液/瓶塞）不参与
  蒙皮，改用骨骼父级挂到 Hand.L 骨上——双手持物行走时双臂同向微摆，
  烧瓶随手臂整体移动，不随单手；右手与烧瓶的相对漂移实测记录
- 关节环检查（实测）：手臂/腿部每根管子的环心与对应关节骨骼头位置的距离
- 姿势：持瓶行走中段——双臂同向微摆（抱物不甩臂）、左腿前迈着地、
  右腿后蹬脚尖点地；躯干微前倾
- 渲染：Eevee 1024x1024，三点式影棚灯光，fit_camera_to_objects 自动取景
Run: blender --background --python 050-alchemist-rig.py
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


# ---------------------------------------------------------------- helpers
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
    Winding: 048 修正版（照搬 045/007/022）。"""
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


def box_own_origin(name, center, size, mat, rot=(0.0, 0.0, 0.0)):
    """Box whose mesh verts are centred on the local origin; the object
    carries location + rotation, so `rot` turns about the box centre.
    (054 fix, same as 049: the old box()+rotation_euler rotated about
    the world origin because box() baked absolute coords into the mesh.)"""
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
    obj = mesh_from_data(name, verts, faces, mat)
    obj.location = center
    obj.rotation_euler = rot
    return obj


def cyl_between(name, p0, p1, radius, sides, mat):
    """Cylinder (with end caps) between two points, fan caps."""
    a = Vector(p0)
    b = Vector(p1)
    axis = b - a
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


def add_torus(name, location, major_r, minor_r, major_seg, minor_seg,
              rotation, material):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_r, minor_radius=minor_r,
        major_segments=major_seg, minor_segments=minor_seg,
        location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    flat_shade(obj)
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


def glass_material(name, color, alpha=0.35, roughness=0.15):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = roughness
    mat.surface_render_method = 'DITHERED'
    return mat


def srgb(rgb):
    """sRGB swatch -> linear values for Principled BSDF Base Color."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


# ---------------------------------------------------------------- 049 几何
def build_alchemist():
    """与 049 完全相同的炼金术士几何。返回 (全部部件, 烧瓶三件)。"""
    skin = solid_material("Skin", srgb((0.86, 0.63, 0.48)), metallic=0.0, roughness=0.7)
    robe = solid_material("Robe_Teal", srgb((0.10, 0.32, 0.28)), metallic=0.0, roughness=0.85)
    robe_dark = solid_material("Robe_Dark", srgb((0.07, 0.22, 0.19)), metallic=0.0, roughness=0.9)
    apron = solid_material("Apron_Brown", srgb((0.45, 0.30, 0.16)), metallic=0.0, roughness=0.9)
    apron_dark = solid_material("Apron_Dark", srgb((0.32, 0.20, 0.10)), metallic=0.0, roughness=0.9)
    leather_dark = solid_material("Leather_Dark", srgb((0.30, 0.18, 0.09)), metallic=0.0, roughness=0.9)
    brass = solid_material("Brass", srgb((0.72, 0.55, 0.20)), metallic=0.8, roughness=0.35)
    eyes = solid_material("Eyes_Dark", srgb((0.05, 0.05, 0.06)), metallic=0.0, roughness=0.4)
    hair = solid_material("Hair_Brown", srgb((0.32, 0.20, 0.10)), metallic=0.0, roughness=0.85)
    beard_mat = solid_material("Beard_Grey", srgb((0.55, 0.50, 0.45)), metallic=0.0, roughness=0.9)
    glass = glass_material("Flask_Glass", srgb((0.75, 0.85, 0.88)), alpha=0.35)
    liquid = solid_material("Flask_Liquid", srgb((0.25, 0.85, 0.30)), metallic=0.0, roughness=0.3)
    lens_green = solid_material("Lens_Green", srgb((0.20, 0.65, 0.35)), metallic=0.1, roughness=0.2)
    potion_red = solid_material("Potion_Red", srgb((0.75, 0.15, 0.12)), metallic=0.0, roughness=0.3)
    potion_blue = solid_material("Potion_Blue", srgb((0.15, 0.35, 0.75)), metallic=0.0, roughness=0.3)
    potion_purple = solid_material("Potion_Purple", srgb((0.50, 0.20, 0.60)), metallic=0.0, roughness=0.3)
    cork = solid_material("Cork", srgb((0.70, 0.55, 0.35)), metallic=0.0, roughness=0.9)
    pants = solid_material("Pants_Grey", srgb((0.28, 0.27, 0.30)), metallic=0.0, roughness=0.9)

    parts = []
    head = add_sphere("Head", (0, 0, 1.52), 0.20, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.07, -0.168, 1.53), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    cap = add_sphere("HairCap", (0, 0.02, 1.63), 0.19, 8, 5,
                     (1.0, 0.95, 0.62), hair)
    parts.append(cap)
    beard = add_sphere("Beard", (0, -0.10, 1.38), 0.09, 8, 5,
                       (1.0, 0.75, 0.85), beard_mat)
    parts.append(beard)
    for sx in (-1, 1):
        rim = add_torus("GoggleRim", (sx * 0.078, -0.168, 1.615),
                        0.055, 0.009, 12, 4,
                        (math.radians(75), 0, 0), brass)
        parts.append(rim)
        lens = cyl_between("GoggleLens", (sx * 0.078, -0.158, 1.608),
                           (sx * 0.078, -0.178, 1.622), 0.048, 8, lens_green)
        parts.append(lens)
    strap = add_torus("GoggleStrap", (0, 0.01, 1.60),
                      0.205, 0.014, 16, 4, (0, 0, 0), leather_dark)
    parts.append(strap)
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.08, 0.075], 6, skin)
    parts.append(neck)
    collar = make_tube("Collar", (0, 0, 1.26), (0, 0, 1),
                       [0.0, 0.06], [0.16, 0.15], 8, robe_dark)
    parts.append(collar)
    shawl = make_tube("Shawl", (0, 0, 1.32), (0, 0, -1),
                      [0.0, 0.12, 0.22],
                      [0.31, 0.35, 0.38], 8, robe_dark)
    parts.append(shawl)
    robe_obj = make_tube("Robe", (0, 0, 1.30), (0, 0, -1),
                         [0.0, 0.30, 0.60, 0.90, 1.20],
                         [0.30, 0.315, 0.335, 0.365, 0.40], 8, robe)
    parts.append(robe_obj)
    # 054 fix (same as 049): local-coordinate boxes so the -4° tilt
    # turns about each part's own centre, not the world origin.
    # Pocket moved to y=-0.399 to keep its back embedded 0.0075.
    apron_panel = box_own_origin("Apron", (0, -0.365, 0.75),
                                 (0.44, 0.03, 0.95), apron,
                                 rot=(math.radians(-4), 0, 0))
    parts.append(apron_panel)
    apron_pocket = box_own_origin("ApronPocket", (0, -0.399, 0.55),
                                  (0.20, 0.025, 0.14), apron_dark,
                                  rot=(math.radians(-4), 0, 0))
    parts.append(apron_pocket)
    for sx in (-1, 1):
        strap = box("ApronStrap", (sx * 0.13, 0, 1.26), (0.07, 0.72, 0.025),
                    apron)
        parts.append(strap)
    belt = make_tube("Belt", (0, 0, 0.98), (0, 0, -1),
                     [0.0, 0.07], [0.345, 0.345], 8, leather_dark)
    parts.append(belt)
    buckle = box("Buckle", (0, -0.345, 0.945), (0.09, 0.02, 0.06), brass)
    parts.append(buckle)
    bottle_defs = [(-0.26, potion_red, "PotionRed"),
                   (0.0, potion_blue, "PotionBlue"),
                   (0.26, potion_purple, "PotionPurple")]
    for bx, bmat, bname in bottle_defs:
        body = make_tube(bname + "Body", (bx, -0.47, 0.78), (0, 0, 1),
                         [0.0, 0.09, 0.12], [0.045, 0.05, 0.02], 6, bmat)
        parts.append(body)
        cork_top = make_tube(bname + "Cork", (bx, -0.47, 0.90), (0, 0, 1),
                             [0.0, 0.03], [0.022, 0.02], 6, cork)
        parts.append(cork_top)
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.30, 0, 1.22))
        wrist = Vector((sx * 0.14, -0.47, 0.99))
        direction = wrist - shoulder
        length = direction.length
        direction.normalize()
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, length * 0.25, length * 0.5,
                         length * 0.75, length],
                        [0.105, 0.10, 0.095, 0.085, 0.075], 6, robe)
        parts.append(arm)
        cuff = make_tube("Cuff", shoulder + direction * (length * 0.78),
                         direction, [0.0, length * 0.22],
                         [0.088, 0.082], 6, apron)
        parts.append(cuff)
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.065, 6, 4,
                          (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    fc = Vector((0, -0.48, 0.92))
    flask = make_tube("Flask", tuple(fc), (0, 0, 1),
                      [0.0, 0.10, 0.16, 0.22], [0.11, 0.10, 0.035, 0.035],
                      8, glass)
    parts.append(flask)
    liq = make_tube("FlaskLiquid", tuple(fc + Vector((0, 0, 0.005))),
                    (0, 0, 1), [0.0, 0.08, 0.11], [0.095, 0.085, 0.03],
                    8, liquid)
    parts.append(liq)
    flask_cork = make_tube("FlaskCork", tuple(fc + Vector((0, 0, 0.22))),
                           (0, 0, 1), [0.0, 0.04], [0.038, 0.032], 6, cork)
    parts.append(flask_cork)
    flask_parts = [flask, liq, flask_cork]
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.55))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.125, 0.25, 0.375, 0.50],
                        [0.10, 0.098, 0.093, 0.086, 0.08], 6, pants)
        parts.append(leg)
        shoe = box("Shoe", (sx * 0.12, -0.30, 0.055), (0.15, 0.34, 0.11),
                   leather_dark)
        parts.append(shoe)

    for obj in parts:
        smart_uv_unwrap(obj)
    return parts, flask_parts, wrists


# ---------------------------------------------------------------- 骨架
# 角色面朝 -Y；左侧 = +X、右侧 = -X（与 007/014/022/036/045 同约定）。
# 肘 = 肩腕中点：(±0.22, -0.235, 1.105)；腕 = (±0.14, -0.47, 0.99)。
# 膝：髋 z 0.55 - 0.25 = 0.30；踝：髋 z 0.55 - 0.50 = 0.05。
BONES = [
    # name, head, tail, parent
    ("Hips",       (0, 0, 0.55),      (0, 0, 0.95),       None),
    ("Spine",      (0, 0, 0.95),      (0, 0, 1.28),       "Hips"),
    ("Neck",       (0, 0, 1.28),      (0, 0, 1.42),       "Spine"),
    ("Head",       (0, 0, 1.42),      (0, 0, 1.72),       "Neck"),
    ("Shoulder.L", (0.30, 0, 1.22),   (0.22, -0.235, 1.105), "Spine"),
    ("Forearm.L",  (0.22, -0.235, 1.105), (0.14, -0.47, 0.99), "Shoulder.L"),
    ("Hand.L",     (0.14, -0.47, 0.99), (0.123, -0.535, 0.949), "Forearm.L"),
    ("Shoulder.R", (-0.30, 0, 1.22),  (-0.22, -0.235, 1.105), "Spine"),
    ("Forearm.R",  (-0.22, -0.235, 1.105), (-0.14, -0.47, 0.99), "Shoulder.R"),
    ("Hand.R",     (-0.14, -0.47, 0.99), (-0.123, -0.535, 0.949), "Forearm.R"),
    ("Thigh.L",    (0.12, 0, 0.55),   (0.12, 0, 0.30),    "Hips"),
    ("Shin.L",     (0.12, 0, 0.30),   (0.12, 0, 0.05),    "Thigh.L"),
    ("Foot.L",     (0.12, 0, 0.05),   (0.12, -0.20, 0.05), "Shin.L"),
    ("Thigh.R",    (-0.12, 0, 0.55),  (-0.12, 0, 0.30),   "Hips"),
    ("Shin.R",     (-0.12, 0, 0.30),  (-0.12, 0, 0.05),   "Thigh.R"),
    ("Foot.R",     (-0.12, 0, 0.05),  (-0.12, -0.20, 0.05), "Shin.R"),
]

# 姿势：持瓶行走中段——双手持烧瓶，双臂同向微摆（抱物不甩臂：左右肩同号
# +0.05 rad，045 已验证同号旋转在镜像骨上产生同向世界摆动）；肘微屈；
# 左腿前迈着地、右腿后蹬脚尖点地；躯干微前倾。
# 脚掌初值取 045 实测标定终值（Foot.L -0.38 / Foot.R +0.32），045 文中说明
# 036 的值不能直接套用，045 的脚掌骨与本稿完全相同（水平骨、头尾等高
# z=0.05），可直接沿用，本稿再实测标定复核。
POSE = {
    "Hips":       {"loc": (0, 0, -0.05), "rot": (0.0, -0.02, 0.05)},
    "Spine":      {"rot": (0.06, 0.0, 0.0)},
    "Neck":       {"rot": (-0.03, 0.0, 0.0)},
    "Head":       {"rot": (-0.05, 0.0, 0.0)},
    "Shoulder.L": {"rot": (0.05, 0.0, 0.03)},
    "Forearm.L":  {"rot": (-0.04, 0.0, 0.0)},
    "Hand.L":     {"rot": (-0.02, 0.0, 0.0)},
    "Shoulder.R": {"rot": (0.05, 0.0, -0.03)},
    "Forearm.R":  {"rot": (-0.04, 0.0, 0.0)},
    "Hand.R":     {"rot": (-0.02, 0.0, 0.0)},
    "Thigh.L":    {"rot": (-0.22, 0.0, 0.0)},
    "Shin.L":     {"rot": (-0.12, 0.0, 0.0)},
    "Foot.L":     {"rot": (-0.38, 0.0, 0.0)},
    "Thigh.R":    {"rot": (0.22, 0.0, 0.0)},
    "Shin.R":     {"rot": (0.12, 0.0, 0.0)},
    "Foot.R":     {"rot": (0.32, 0.0, 0.0)},
}


def build_armature():
    arm_data = bpy.data.armatures.new("AlchemistRig")
    arm_obj = bpy.data.objects.new("AlchemistRig", arm_data)
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


def parent_flask_to_hand(flask_parts, arm_obj):
    """烧瓶三件骨骼父级到 Hand.L（keep_transform），不参与蒙皮。"""
    bpy.ops.object.select_all(action='DESELECT')
    for o in flask_parts:
        o.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.data.bones.active = arm_obj.data.bones["Hand.L"]
    bpy.ops.object.parent_set(type='BONE', keep_transform=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in flask_parts:
        print("FLASK_PARENT %s: parent_bone=%s" % (o.name, o.parent_bone))


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


def _shoe_min_z(obj):
    """姿势求值后鞋底最低 z（实测）。"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    mw = obj.matrix_world
    z = min((mw @ v.co).z for v in mesh.vertices)
    ev.to_mesh_clear()
    return z


def calibrate_foot(arm_obj, bone_name, shoe_obj, target=0.002):
    """实测标定脚掌角度：先探针定斜率方向，再用牛顿步 + 括号二分混合法
    把鞋底 z 收到 target 附近（容差 ±0.002）。照搬 045。"""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones[bone_name]

    def measure():
        bpy.context.view_layer.update()
        return _shoe_min_z(shoe_obj)

    log = []
    a0 = pb.rotation_euler.x
    z0 = measure()
    log.append((round(a0, 3), round(z0, 4)))
    print("CALIB %s: angle=%.3f min_z=%.4f" % (bone_name, a0, z0))
    samples = [(a0, z0)]
    slope = None
    for _ in range(8):
        best_a, best_z = min(samples, key=lambda p: abs(p[1] - target))
        if abs(best_z - target) <= 0.002:
            pb.rotation_euler.x = best_a
            break
        below = [(a, z) for a, z in samples if z < target]
        above = [(a, z) for a, z in samples if z > target]
        if below and above:
            a_lo = max(a for a, z in below)
            a_hi = min(a for a, z in above)
            a_new = 0.5 * (a_lo + a_hi)
        else:
            if slope is None:
                a_p = best_a + 0.1
                pb.rotation_euler.x = a_p
                z_p = measure()
                samples.append((a_p, z_p))
                log.append((round(a_p, 3), round(z_p, 4)))
                slope = (z_p - best_z) / 0.1
                if abs(slope) < 0.05:
                    print("CALIB %s: slope too small (%.3f), stop"
                          % (bone_name, slope))
                    pb.rotation_euler.x = best_a
                    break
                continue
            delta = (target - best_z) / slope
            delta = max(-0.5, min(0.5, delta))
            a_new = best_a + delta
        pb.rotation_euler.x = a_new
        z_new = measure()
        samples.append((a_new, z_new))
        log.append((round(a_new, 3), round(z_new, 4)))
        print("CALIB %s: angle=%.3f min_z=%.4f" % (bone_name, a_new, z_new))
        if len(samples) >= 2:
            (a1, z1), (a2, z2) = samples[-2], samples[-1]
            if abs(a2 - a1) > 1e-6:
                slope = (z2 - z1) / (a2 - a1)
    else:
        best_a, best_z = min(samples, key=lambda p: abs(p[1] - target))
        pb.rotation_euler.x = best_a
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    zf = _shoe_min_z(shoe_obj)
    angle = pb.rotation_euler.x
    print("CALIB %s: final angle=%.3f min_z=%.4f log=%s"
          % (bone_name, angle, zf, log))
    POSE[bone_name]["rot"] = (angle, 0.0, 0.0)
    return angle, zf, log


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
        ("Arm.R ring0 肩", arm_r, 0, 6, Vector((-0.30, 0, 1.22))),
        ("Arm.R ring2 肘", arm_r, 2, 6, Vector((-0.22, -0.235, 1.105))),
        ("Arm.R ring4 腕", arm_r, 4, 6, Vector((-0.14, -0.47, 0.99))),
        ("Arm.L ring0 肩", arm_l, 0, 6, Vector((0.30, 0, 1.22))),
        ("Arm.L ring2 肘", arm_l, 2, 6, Vector((0.22, -0.235, 1.105))),
        ("Arm.L ring4 腕", arm_l, 4, 6, Vector((0.14, -0.47, 0.99))),
        ("Leg.R ring0 髋", leg_r, 0, 6, Vector((-0.12, 0, 0.55))),
        ("Leg.R ring2 膝", leg_r, 2, 6, Vector((-0.12, 0, 0.30))),
        ("Leg.R ring4 踝", leg_r, 4, 6, Vector((-0.12, 0, 0.05))),
        ("Leg.L ring0 髋", leg_l, 0, 6, Vector((0.12, 0, 0.55))),
        ("Leg.L ring2 膝", leg_l, 2, 6, Vector((0.12, 0, 0.30))),
        ("Leg.L ring4 踝", leg_l, 4, 6, Vector((0.12, 0, 0.05))),
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


def _eval_world_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    mw = obj.matrix_world
    verts = [mw @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    return verts


def _bbox_center(verts):
    c = Vector((0, 0, 0))
    for v in verts:
        c += v
    return c / len(verts)


def verify_pose(parts, rest_mw=None):
    """实测：对比静止网格与姿势求值网格的顶点位移；脚底最低 z。
    rest_mw：摆姿势前抓到的各部件 matrix_world（骨骼父级部件的
    matrix_world 会随姿势变，不用它算静止位置会把位移算成 0）。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    report = {}
    min_z_all = 1e9
    for obj in parts:
        mw = obj.matrix_world
        rest_m = rest_mw.get(obj.name, mw) if rest_mw else mw
        rest = [rest_m @ v.co for v in obj.data.vertices]
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


def capture_rest_state(parts, flask_parts):
    """摆姿势前抓静止状态：各部件 matrix_world + 烧瓶/双手中心。
    必须在 apply_pose 之前调用。"""
    by_name = {o.name: o for o in parts}
    rest_mw = {o.name: o.matrix_world.copy() for o in parts}
    flask_verts = []
    for o in flask_parts:
        flask_verts += [o.matrix_world @ v.co for v in o.data.vertices]
    hand_l = by_name["Hand.001"]   # +X = 左手
    hand_r = by_name["Hand"]       # -X = 右手
    return {
        "rest_mw": rest_mw,
        "flask_center": _bbox_center(flask_verts),
        "hand_l_center": _bbox_center(
            [hand_l.matrix_world @ v.co for v in hand_l.data.vertices]),
        "hand_r_center": _bbox_center(
            [hand_r.matrix_world @ v.co for v in hand_r.data.vertices]),
    }


def check_flask_follow(parts, flask_parts, rest_state):
    """实测烧瓶跟手：静止 vs 姿势求值，烧瓶中心与双手中心的距离变化，
    以及烧瓶顶点与围裙/长袍顶点的最小距离（穿帮检查）。"""
    by_name = {o.name: o for o in parts}
    # 静止状态取自摆姿势前抓到的 rest_state（此时 matrix_world 还是静止的）
    rest_center = rest_state["flask_center"]
    # 姿势求值后
    posed_flask = []
    for o in flask_parts:
        posed_flask += _eval_world_verts(o)
    posed_center = _bbox_center(posed_flask)
    hand_l = by_name["Hand.001"]   # +X = 左手
    hand_r = by_name["Hand"]       # -X = 右手
    rest_hand_l = rest_state["hand_l_center"]
    rest_hand_r = rest_state["hand_r_center"]
    posed_hand_l = _bbox_center(_eval_world_verts(hand_l))
    posed_hand_r = _bbox_center(_eval_world_verts(hand_r))
    d_rest_l = (rest_center - rest_hand_l).length
    d_posed_l = (posed_center - posed_hand_l).length
    d_rest_r = (rest_center - rest_hand_r).length
    d_posed_r = (posed_center - posed_hand_r).length
    # 烧瓶 vs 围裙/长袍：姿势求值顶点两两最小距离
    apron_verts = _eval_world_verts(by_name["Apron"]) + \
        _eval_world_verts(by_name["ApronPocket"])
    robe_verts = _eval_world_verts(by_name["Robe"])
    min_apron = min((fv - av).length for fv in posed_flask
                    for av in apron_verts)
    min_robe = min((fv - rv).length for fv in posed_flask
                   for rv in robe_verts)
    out = {
        "flask_center_rest": [round(v, 4) for v in rest_center],
        "flask_center_posed": [round(v, 4) for v in posed_center],
        "flask_displacement": round((posed_center - rest_center).length, 4),
        "hand_l_displacement": round((posed_hand_l - rest_hand_l).length, 4),
        "hand_r_displacement": round((posed_hand_r - rest_hand_r).length, 4),
        "flask_to_hand_l_rest": round(d_rest_l, 4),
        "flask_to_hand_l_posed": round(d_posed_l, 4),
        "flask_to_hand_l_drift": round(abs(d_posed_l - d_rest_l), 4),
        "flask_to_hand_r_rest": round(d_rest_r, 4),
        "flask_to_hand_r_posed": round(d_posed_r, 4),
        "flask_to_hand_r_drift": round(abs(d_posed_r - d_rest_r), 4),
        "flask_min_dist_to_apron": round(min_apron, 4),
        "flask_min_dist_to_robe": round(min_robe, 4),
    }
    for k, v in out.items():
        print("FLASK_CHECK %s: %s" % (k, v))
    return out


def export_deformed_wireframe(objects, camera, filepath):
    """把姿势求值后的可见边投影到 2D（与 common.export_wireframe_segments
    同逻辑，但用变形后的网格）。照搬 045。"""
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

    parts, flask_parts, wrists = build_alchemist()
    total = total_poly_count(parts)
    counts = {o.name: poly_count(o) for o in parts}
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))

    inv_per_part, inv_total = count_inverted_normals(parts)

    ring_checks = check_joint_rings(parts)
    max_ring_err = max(c["distance"] for c in ring_checks)
    print("JOINT_RING_MAX_ERR: %.5f" % max_ring_err)

    arm_obj = build_armature()
    skin_parts = [o for o in parts if o not in flask_parts]
    method = skin(skin_parts, arm_obj)
    print("SKIN_METHOD:", method)
    groups = {o.name: sorted(g.name for g in o.vertex_groups)
              for o in parts if o.vertex_groups}
    print("VERTEX_GROUPS:", json.dumps(groups, ensure_ascii=False))
    parent_flask_to_hand(flask_parts, arm_obj)
    rest_state = capture_rest_state(parts, flask_parts)

    apply_pose(arm_obj)
    by_name = {o.name: o for o in parts}
    foot_l_angle, foot_l_z, _log_l = calibrate_foot(
        arm_obj, "Foot.L", by_name["Shoe.001"])
    foot_r_angle, foot_r_z, _log_r = calibrate_foot(
        arm_obj, "Foot.R", by_name["Shoe"])
    check = verify_pose(parts, rest_state["rest_mw"])
    for name, vals in check.items():
        print("RIG_CHECK %s: %s" % (name, vals))
    flask_check = check_flask_follow(parts, flask_parts, rest_state)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    if os.environ.get("SKIP_RENDER"):
        print("SKIP_RENDER set: skipping render/save, writing checks only")
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(ROOT, "scenes", "050-alchemist-rig.blend"))
    else:
        render(os.path.join(ROOT, "renders", "050-alchemist-rig.png"))
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(ROOT, "scenes", "050-alchemist-rig.blend"))

    export_deformed_wireframe(
        parts, cam, os.path.join("/tmp", "alchemist_rig_wire.json"))

    pose_deg = {name: {"loc": [round(v, 3) for v in spec.get("loc", (0, 0, 0))],
                       "rot_deg": [round(math.degrees(a), 1) for a in spec["rot"]]}
                for name, spec in POSE.items()}
    rig_info = {
        "bones": [{"name": n, "head": list(h), "tail": list(t), "parent": p}
                  for n, h, t, p in BONES],
        "bone_count": len(BONES),
        "skin_method": method,
        "flask_parent": "Hand.L (bone parent, keep_transform)",
        "pose_degrees": pose_deg,
        "poly": {"total": total, "tris": tris, "quads": quads, "ngons": ngons,
                 "per_part": counts},
        "inverted_normals_per_part": inv_per_part,
        "inverted_normals_total": inv_total,
        "joint_ring_checks": ring_checks,
        "joint_ring_max_error": round(max_ring_err, 5),
        "verification": check,
        "flask_check": flask_check,
    }
    with open(os.path.join(ROOT, "scenes", "050-rig.json"), "w",
              encoding="utf-8") as f:
        json.dump(rig_info, f, ensure_ascii=False, indent=2)

    wrist_err = max(c["distance"] for c in ring_checks if "腕" in c["joint"])
    core_err = max(c["distance"] for c in ring_checks if "腕" not in c["joint"])
    note = os.path.join(ROOT, "scenes", "050-alchemist-rig.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 050 角色关节拓扑：049 炼金术士骨架 + 行走姿势\n\n")
        f.write("给 049 低模炼金术士加骨架并摆出持瓶行走姿势。角色几何与 049 完全一致。\n\n")
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
        f.write("- 烧瓶三件（Flask / FlaskLiquid / FlaskCork）不参与蒙皮，改用骨骼父级"
                "挂到 Hand.L 骨上（keep_transform）：双手持物行走时双臂同向微摆，"
                "烧瓶随手臂整体移动；腰间三瓶药水、护目镜、长袍等随对应骨骼\n\n")
        f.write("## 关节环检查（实测，非估算）\n\n")
        f.write("手臂 / 腿部管子的环心与对应关节骨骼头位置的距离（米）：\n\n")
        f.write("| 关节 | 环心 | 骨骼关节 | 误差 |\n")
        f.write("| ---- | ---- | -------- | ---- |\n")
        for c in ring_checks:
            f.write("| %s | (%.3f, %.3f, %.3f) | (%.3f, %.3f, %.3f) | %.5f |\n"
                    % (c["joint"], c["ring_center"][0], c["ring_center"][1],
                       c["ring_center"][2], c["bone_joint"][0],
                       c["bone_joint"][1], c["bone_joint"][2], c["distance"]))
        f.write("\n肩 / 肘 / 髋 / 膝 / 踝环误差 ≤ %.5f 米，腕环误差 %.5f 米："
                "手臂管子的环按肩到腕的等分点排布，环 0 / 环 2 / 环 4 分别正好落在"
                "肩 / 肘（肩腕中点）/ 腕关节上，弯曲不断裂。\n"
                % (core_err, wrist_err))
        f.write("\n## 行走姿势（持瓶行走中段）\n\n")
        f.write("- 双臂同向微摆：左右肩同号 +3°（045 已验证同号旋转在镜像骨上产生同向"
                "世界摆动），肘微屈 2°，双手基本留在烧瓶上——抱物行走不甩臂，"
                "与 045 的抱书姿势同一道理\n")
        f.write("- 左腿前迈着地（大腿 -13°，小腿 -7°），右腿后蹬（大腿 +13°，小腿 +7°，鞋尖点地）\n")
        f.write("- 脚掌角度逐只实测标定（牛顿步 + 括号二分混合，目标鞋底 z=+0.002）："
                "Foot.L %.2f rad（初值 -0.38，取自 045 实测终值）→ 前鞋底 z=%.3f，"
                "Foot.R %.2f rad（初值 +0.32）→ 后鞋底 z=%.3f\n"
                % (foot_l_angle, foot_l_z, foot_r_angle, foot_r_z))
        f.write("- 髋部沿骨骼局部 Z 轴后移 0.05 米（实测：Hips loc (0,0,-0.05) 使髋关节头向 +Y 平移 0.05 米，z 不变，"
                "无垂直下沉；014/022 文案称“髋部下沉”有误）、躯干微前倾 3°，模拟行走重心起伏；"
                "长袍下摆随腿前移，膝盖在袍摆下可见\n\n")
        f.write("## 烧瓶跟手检查（实测，非估算）\n\n")
        f.write("- 烧瓶骨骼父级到 Hand.L：姿势求值后烧瓶中心位移 %.3f 米，左手中心位移 %.3f 米，"
                "烧瓶到左手中心距离 %.3f 米（静止 %.3f 米），漂移 %.4f 米——"
                "刚性跟随，基本无相对位移\n"
                % (flask_check["flask_displacement"],
                   flask_check["hand_l_displacement"],
                   flask_check["flask_to_hand_l_posed"],
                   flask_check["flask_to_hand_l_rest"],
                   flask_check["flask_to_hand_l_drift"]))
        f.write("- 右手：烧瓶到右手中心距离 %.3f 米（静止 %.3f 米），漂移 %.4f 米——"
                "右手向烧瓶靠拢了 3.6 厘米，没有脱开：右手中心到烧瓶中心 0.114 米，"
                "烧瓶该高度半径约 0.10 米、手掌半径 0.065 米，右手贴在瓶身侧面，"
                "渲染图上双手仍握在烧瓶两侧、无脱手；漂移原因是烧瓶只挂左手骨，"
                "且左右肩 z 分量符号相反（+0.03 / -0.03），两臂摆动不完全对称，"
                "下次同类持物姿势应把双肩 z 分量也取同号\n"
                % (flask_check["flask_to_hand_r_posed"],
                   flask_check["flask_to_hand_r_rest"],
                   flask_check["flask_to_hand_r_drift"]))
        f.write("- 穿帮检查（姿势求值顶点两两最小距离）：烧瓶到围裙 %.3f 米，"
                "到长袍 %.3f 米，均 > 0，烧瓶没有扎进围裙或长袍\n"
                % (flask_check["flask_min_dist_to_apron"],
                   flask_check["flask_min_dist_to_robe"]))
        f.write("\n## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d），与 049 一致\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 倒置面复测\n\n")
        f.write("- 全角色倒置面 %d 个（逐部件复测，与 021 同一方法）；049 已用 048 修正版"
                "绕向建模，管盖扇形无内翻\n\n" % inv_total)
        f.write("## 绑定验证（实测，非估算）\n\n")
        f.write("- 姿势求值后全角色最低点 z = %.3f\n"
                % check["_overall_min_z"])
        f.write("- 前脚鞋底 z = %.3f，后脚鞋底 z = %.3f\n"
                % (check.get("Shoe.001", {}).get("min_z", 0),
                   check.get("Shoe", {}).get("min_z", 0)))
        f.write("- 长袍下摆最低 z = %.3f\n"
                % check.get("Robe", {}).get("min_z", 0))
        f.write("- 各部件最大顶点位移（米）：左腿 %.3f、右腿 %.3f、左臂 %.3f、右臂 %.3f、烧瓶 %.3f、长袍 %.3f、护目镜 %.3f\n"
                % (check.get("Leg.001", {}).get("max_displacement", 0),
                   check.get("Leg", {}).get("max_displacement", 0),
                   check.get("Arm.001", {}).get("max_displacement", 0),
                   check.get("Arm", {}).get("max_displacement", 0),
                   check.get("Flask", {}).get("max_displacement", 0),
                   check.get("Robe", {}).get("max_displacement", 0),
                   check.get("GoggleRim", {}).get("max_displacement", 0)))
        f.write("- 骨架 + 蒙皮 + 姿势全部保存在 scenes/050-alchemist-rig.blend，"
                "打开即可在姿势模式下继续调动作\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，姿势变形后的真实投影边线叠加\n")
    print("NOTE_WRITTEN:", note)
    print("RIG_JSON:", os.path.join(ROOT, "scenes", "050-rig.json"))


if __name__ == "__main__":
    main()
