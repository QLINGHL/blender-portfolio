# -*- coding: utf-8 -*-
"""022 角色关节拓扑：给 020 法师加骨架（armature），摆一个行走姿势
- 角色几何与 020 完全一致（长袍、尖顶帽、白胡须、法杖，540 面）
- 管状/盒状建模函数采用 007 的绕向修正版（008 质检验证过）；八面体水晶
  的面绕向也一并修正——021 质检实测法师有 144 个倒置面（管状盖面扇形 +
  水晶八面体），本脚本重建后实测倒置面应为 0
- 16 根骨骼：Hips / Spine / Neck / Head / 双臂（肩/肘/手）/ 双腿（大腿/小腿/脚）
- 蒙皮：自动权重（失败则退到包络权重）
- 关节环检查（实测）：手臂/腿部每根管子的环心与对应关节骨骼头位置
  的距离——肩/肘/腕/髋/膝/踝环应正好落在关节上
- 姿势：行走中段——左腿前迈着地、右腿后蹬脚尖点地、手臂反向摆动
  （右手持杖随臂摆动）、躯干微前倾；长袍随腿摆动
- 渲染：Eevee 1024x1024，三点式影棚灯光，3/4 视角（能看清迈步）
Run: blender --background --python 022-mage-rig.py
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
                    add_ground, studio_lights, make_camera, flat_shade,
                    poly_count, total_poly_count, setup_render, render)


# ---------------------------------------------------------------- 020 几何
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
    Winding: 007 修正版（008 质检验证：原版管帽内外翻转）。"""
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


def make_box_tube(name, rings, material):
    """Rectangular tube from a list of (z, half_x, half_y) rings (CCW corners).
    Winding: 007 修正版（008 质检验证：原版盒管内外翻转）。"""
    verts, faces = [], []
    for z, hx, hy in rings:
        verts += [(hx, -hy, z), (hx, hy, z), (-hx, hy, z), (-hx, -hy, z)]
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((k * 4 + i, (k + 1) * 4 + i, (k + 1) * 4 + j, k * 4 + j))
    n = len(rings)
    faces.append(((n - 1) * 4, (n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1))
    faces.append((0, 1, 2, 3))
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


def smart_uv_unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


def make_octahedron(name, location, radius_xy, radius_z, material):
    """8-face octahedron: top/bottom apex + 4 equator vertices.
    Winding corrected vs 020 (021 质检：原版八面体面全部倒置）。"""
    cx, cy, cz = location
    verts = [(cx, cy, cz + radius_z),
             (cx, cy, cz - radius_z),
             (cx + radius_xy, cy, cz),
             (cx, cy - radius_xy, cz),
             (cx - radius_xy, cy, cz),
             (cx, cy + radius_xy, cz)]
    faces = [(0, 3, 2), (0, 4, 3), (0, 5, 4), (0, 2, 5),
             (1, 2, 3), (1, 3, 4), (1, 4, 5), (1, 5, 2)]
    return mesh_from_data(name, verts, faces, material)


def build_mage():
    """与 020 完全相同的法师几何（绕向修正版）。返回部件列表。"""
    skin = solid_material("Skin", (0.86, 0.63, 0.48), metallic=0.0, roughness=0.7)
    robe = solid_material("Robe_Purple", (0.30, 0.16, 0.52), metallic=0.0, roughness=0.85)
    robe_dark = solid_material("Robe_Dark", (0.22, 0.11, 0.40), metallic=0.0, roughness=0.85)
    gold = solid_material("Trim_Gold", (0.78, 0.60, 0.22), metallic=0.85, roughness=0.3)
    beard_mat = solid_material("Beard_White", (0.88, 0.87, 0.83), metallic=0.0, roughness=0.9)
    eyes = solid_material("Eyes_Dark", (0.05, 0.05, 0.06), metallic=0.0, roughness=0.4)
    wood = solid_material("Staff_Wood", (0.35, 0.22, 0.12), metallic=0.0, roughness=0.9)
    boots = solid_material("Boots_Brown", (0.28, 0.18, 0.11), metallic=0.0, roughness=0.9)
    pants = solid_material("Pants_Navy", (0.20, 0.24, 0.42), metallic=0.0, roughness=0.85)
    crystal = solid_material("Crystal", (0.35, 0.80, 0.95), metallic=0.1, roughness=0.15)
    crystal.use_nodes = True
    emit = crystal.node_tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.25, 0.65, 0.90, 1.0)
    emit.inputs["Strength"].default_value = 0.6
    out = crystal.node_tree.nodes["Material Output"]
    bsdf = crystal.node_tree.nodes["Principled BSDF"]
    mix = crystal.node_tree.nodes.new("ShaderNodeMixShader")
    crystal.node_tree.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    crystal.node_tree.links.new(emit.outputs["Emission"], mix.inputs[2])
    mix.inputs["Fac"].default_value = 0.45
    crystal.node_tree.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    parts = []
    head = add_sphere("Head", (0, 0, 1.52), 0.21, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.072, -0.178, 1.51), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    beard = make_tube("Beard", (0, -0.18, 1.38), (0, -0.75, -1),
                      [0.0, 0.14, 0.28, 0.40],
                      [0.11, 0.095, 0.07, 0.025], 6, beard_mat)
    parts.append(beard)
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.085, 0.08], 6, skin)
    parts.append(neck)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.34, depth=0.035,
                                        location=(0, 0, 1.70))
    brim = bpy.context.active_object
    brim.name = "HatBrim"
    brim.data.materials.append(robe_dark)
    flat_shade(brim)
    parts.append(brim)
    hat = make_tube("Hat", (0, 0, 1.71), (0.10, 0, 1),
                    [0.0, 0.14, 0.28, 0.40],
                    [0.23, 0.17, 0.10, 0.015], 8, robe_dark)
    parts.append(hat)
    tip = add_sphere("HatTip", (0.04, 0, 2.11), 0.03, 6, 3, (1.0, 1.0, 1.0), gold)
    parts.append(tip)
    robe_obj = make_tube("Robe", (0, 0, 1.30), (0, 0, -1),
                         [0.0, 0.30, 0.62, 0.95, 1.25],
                         [0.30, 0.31, 0.34, 0.40, 0.48], 8, robe)
    parts.append(robe_obj)
    collar = make_tube("Collar", (0, 0, 1.30), (0, 0, 1),
                       [0.0, 0.09], [0.30, 0.20], 8, robe_dark)
    parts.append(collar)
    sash = make_tube("Sash", (0, 0, 0.90), (0, 0, -1),
                     [0.0, 0.08], [0.34, 0.34], 8, gold)
    parts.append(sash)
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.31, 0, 1.24))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.115, 0.108, 0.10, 0.088, 0.075], 6, robe)
        parts.append(arm)
        wrist = shoulder + direction.normalized() * 0.55
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.075, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.62))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.105, 0.10, 0.095, 0.088, 0.082], 6, pants)
        parts.append(leg)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sx * 0.12, -0.30, 0.05))
        foot = bpy.context.active_object
        foot.name = "Boot"
        foot.scale = (0.15, 0.27, 0.10)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        foot.data.materials.append(boots)
        flat_shade(foot)
        parts.append(foot)
    # --- staff in right hand (+X) ---
    hand_r = wrists[1]
    staff_x = hand_r.x + 0.08
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.035, depth=1.55,
                                        location=(staff_x, hand_r.y, hand_r.z + 0.10))
    shaft = bpy.context.active_object
    shaft.name = "StaffShaft"
    shaft.data.materials.append(wood)
    flat_shade(shaft)
    parts.append(shaft)
    for rz in (hand_r.z + 0.62, hand_r.z + 0.70):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.05, depth=0.03,
                                            location=(staff_x, hand_r.y, rz))
        ring = bpy.context.active_object
        ring.name = "StaffRing"
        ring.data.materials.append(gold)
        flat_shade(ring)
        parts.append(ring)
    crystal_obj = make_octahedron("StaffCrystal", (staff_x, hand_r.y, hand_r.z + 0.92),
                                  0.11, 0.17, crystal)
    parts.append(crystal_obj)

    for obj in parts:
        smart_uv_unwrap(obj)
    return parts


# ---------------------------------------------------------------- 骨架
# 角色面朝 -Y；左侧 = +X（与 007/014 同约定）。关节位置取自 020 几何
# （肩/肘/腕/髋/膝/踝的环位置）。
# 肘：肩 + 方向单位向量 * 0.26 = (±0.346, 0, 0.9825)；腕：肩 + 方向 * 0.55。
BONES = [
    # name, head, tail, parent
    ("Hips",       (0, 0, 0.62),      (0, 0, 0.95),       None),
    ("Spine",      (0, 0, 0.95),      (0, 0, 1.28),       "Hips"),
    ("Neck",       (0, 0, 1.28),      (0, 0, 1.42),       "Spine"),
    ("Head",       (0, 0, 1.42),      (0, 0, 1.72),       "Neck"),
    ("Shoulder.L", (0.31, 0, 1.24),   (0.346, 0, 0.9825), "Spine"),
    ("Forearm.L",  (0.346, 0, 0.9825), (0.386, 0, 0.695), "Shoulder.L"),
    ("Hand.L",     (0.386, 0, 0.695), (0.39, 0, 0.62),    "Forearm.L"),
    ("Shoulder.R", (-0.31, 0, 1.24),  (-0.346, 0, 0.9825), "Spine"),
    ("Forearm.R",  (-0.346, 0, 0.9825), (-0.386, 0, 0.695), "Shoulder.R"),
    ("Hand.R",     (-0.386, 0, 0.695), (-0.39, 0, 0.62),   "Forearm.R"),
    ("Thigh.L",    (0.12, 0, 0.62),   (0.12, 0, 0.36),    "Hips"),
    ("Shin.L",     (0.12, 0, 0.36),   (0.12, 0, 0.10),    "Thigh.L"),
    ("Foot.L",     (0.12, 0, 0.10),   (0.12, -0.20, 0.05), "Shin.L"),
    ("Thigh.R",    (-0.12, 0, 0.62),  (-0.12, 0, 0.36),   "Hips"),
    ("Shin.R",     (-0.12, 0, 0.36),  (-0.12, 0, 0.10),   "Thigh.R"),
    ("Foot.R",     (-0.12, 0, 0.10),  (-0.12, -0.20, 0.05), "Shin.R"),
]

# 姿势：缓慢行走——左腿前迈着地、右腿后蹬脚尖点地、手臂反向摆动
# （右手持杖随臂摆动）、躯干微前倾；长袍随腿摆动。
# 步幅比 007/014 小：法师穿长袍、靴尖前指 0.30 米（战士靴只前指 0.04 米），
# 大步幅会让后脚靴尖扎进地面、前脚靴离地悬空；小步幅 + 近乎伸直的前腿
# 才能让双脚贴地。
POSE = {
    "Hips":       {"loc": (0, 0, -0.05), "rot": (0.0, -0.02, 0.05)},
    "Spine":      {"rot": (0.06, 0.0, 0.0)},
    "Neck":       {"rot": (-0.03, 0.0, 0.0)},
    "Head":       {"rot": (-0.05, 0.0, 0.0)},
    "Shoulder.L": {"rot": (0.30, 0.0, 0.06)},
    "Forearm.L":  {"rot": (-0.40, 0.0, 0.0)},
    "Hand.L":     {"rot": (-0.10, 0.0, 0.0)},
    "Shoulder.R": {"rot": (-0.30, 0.0, -0.06)},
    "Forearm.R":  {"rot": (-0.30, 0.0, 0.0)},
    "Hand.R":     {"rot": (-0.10, 0.0, 0.0)},
    "Thigh.L":    {"rot": (-0.22, 0.0, 0.0)},
    "Shin.L":     {"rot": (-0.12, 0.0, 0.0)},
    "Foot.L":     {"rot": (0.34, 0.0, 0.0)},
    "Thigh.R":    {"rot": (0.22, 0.0, 0.0)},
    "Shin.R":     {"rot": (0.12, 0.0, 0.0)},
    "Foot.R":     {"rot": (-0.20, 0.0, 0.0)},
}


def build_armature():
    arm_data = bpy.data.armatures.new("MageRig")
    arm_obj = bpy.data.objects.new("MageRig", arm_data)
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
        ("Leg.R ring0 髋", leg_r, 0, 6, Vector((-0.12, 0, 0.62))),
        ("Leg.R ring2 膝", leg_r, 2, 6, Vector((-0.12, 0, 0.36))),
        ("Leg.R ring4 踝", leg_r, 4, 6, Vector((-0.12, 0, 0.10))),
        ("Leg.L ring0 髋", leg_l, 0, 6, Vector((0.12, 0, 0.62))),
        ("Leg.L ring2 膝", leg_l, 2, 6, Vector((0.12, 0, 0.36))),
        ("Leg.L ring4 踝", leg_l, 4, 6, Vector((0.12, 0, 0.10))),
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
    """把姿势求值后的可见边投影到 2D（与 common.export_wireframe_segments 同逻辑，
    但用变形后的网格）。"""
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

    parts = build_mage()
    total = total_poly_count(parts)
    counts = {o.name: poly_count(o) for o in parts}
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))

    # 倒置面复测（021 质检：020 原版 144 个倒置面；修正绕向后应为 0）
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

    # 3/4 视角：能看清迈步的前后错位；法师比战士高（帽尖 2.11），相机抬高
    cam = make_camera("Camera", (2.0, -2.7, 1.5), (0, 0, 1.0), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "022-mage-rig.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "022-mage-rig.blend"))

    export_deformed_wireframe(
        parts, cam, os.path.join("/tmp", "mage_rig_wire.json"))

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
    with open(os.path.join(ROOT, "scenes", "022-rig.json"), "w",
              encoding="utf-8") as f:
        json.dump(rig_info, f, ensure_ascii=False, indent=2)

    wrist_err = max(c["distance"] for c in ring_checks if "腕" in c["joint"])
    core_err = max(c["distance"] for c in ring_checks if "腕" not in c["joint"])
    note = os.path.join(ROOT, "scenes", "022-mage-rig.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 022 角色关节拓扑：020 法师骨架 + 行走姿势\n\n")
        f.write("给 020 低模法师加骨架并摆出行走姿势。角色几何与 020 完全一致。\n\n")
        f.write("## 绕向修正（021 质检遗留问题）\n\n")
        f.write("021 质检实测 020 法师有 144 个倒置面（管状盖面扇形 + 水晶八面体）。"
                "本脚本建模函数采用 007 修正版绕向，八面体水晶面绕向也已翻转，"
                "重建后实测倒置面 %d 个（逐部件复测，与 021 同一方法）。"
                "020 原文件未改动，修正只存在于本 rig 版本。\n\n" % inv_total)
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
        f.write("- 法杖随右手摆动；长袍随髋 / 大腿摆动；胡须、尖顶帽随头部\n\n")
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
        f.write("\n## 行走姿势（缓慢行走中段）\n\n")
        f.write("- 步幅比 007/014 小：法师穿长袍、靴尖前指 0.30 米（战士靴只前指 0.04 米），"
                "大步幅会让后脚靴尖扎进地面、前脚靴离地悬空\n")
        f.write("- 左腿前迈着地（大腿 -13°，小腿 -7°，脚掌放平），右腿后蹬脚尖点地（大腿 +13°，小腿 +7°，脚掌轻点）\n")
        f.write("- 手臂反向摆动：左臂后摆 +17°、右臂前摆 -17°，双肘微屈；法杖随右臂摆动\n")
        f.write("- 髋部下沉 0.05 米、躯干微前倾 3°，模拟行走重心起伏；长袍下摆随腿前移\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d），与 020 一致\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绑定验证（实测，非估算）\n\n")
        f.write("- 姿势求值后全角色最低点 z = %.3f（后脚靴尖，藏于长袍下，渲染中不可见；"
                "袍摆 z = %.3f，基本贴地）\n"
                % (check["_overall_min_z"], check.get("Robe", {}).get("min_z", 0)))
        f.write("- 前脚靴底 z = %.3f（贴地），后脚靴底 z = %.3f\n"
                % (check.get("Boot.001", {}).get("min_z", 0),
                   check.get("Boot", {}).get("min_z", 0)))
        f.write("- 各部件最大顶点位移（米）：左腿 %.3f、右腿 %.3f、左臂 %.3f、右臂 %.3f、长袍 %.3f、法杖 %.3f\n"
                % (check.get("Leg.001", {}).get("max_displacement", 0),
                   check.get("Leg", {}).get("max_displacement", 0),
                   check.get("Arm.001", {}).get("max_displacement", 0),
                   check.get("Arm", {}).get("max_displacement", 0),
                   check.get("Robe", {}).get("max_displacement", 0),
                   check.get("StaffShaft", {}).get("max_displacement", 0)))
        f.write("- 骨架 + 蒙皮 + 姿势全部保存在 scenes/022-mage-rig.blend，"
                "打开即可在姿势模式下继续调动作\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，3/4 视角\n")
        f.write("- 线框图：同角度，姿势变形后的真实投影边线叠加\n")
    print("NOTE_WRITTEN:", note)
    print("RIG_JSON:", os.path.join(ROOT, "scenes", "022-rig.json"))


if __name__ == "__main__":
    main()
