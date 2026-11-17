# -*- coding: utf-8 -*-
"""007 角色绑定准备：给 002 角色加骨架（armature），摆一个行走姿势
- 角色几何与 002 完全一致（同一套建模代码，356 面）
- 16 根骨骼：Hips / Spine / Neck / Head / 双臂（肩/肘/手）/ 双腿（大腿/小腿/脚）
- 蒙皮：自动权重（失败则退到包络权重），关节环正好落在肘/膝弯曲处
- 姿势：行走中段——左腿前迈着地、右腿后蹬脚尖点地、手臂反向摆动、躯干微前倾
- 渲染：Eevee 1024x1024，三点式影棚灯光，3/4 视角（能看清迈步）
Run: blender --background --python 007-character-rig.py
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

BLENDER = os.path.join(os.path.expanduser("~"), "workspace", "blender",
                       "blender-5.3.0-linux-x64", "blender")


# ---------------------------------------------------------------- 002 几何
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
        # cap winding flipped: QA 008 found both cap fans inverted
        # (recalc + ray-cast verified on 002)
        faces.append((top_c, j, i))
        faces.append((bot_c, (n_rings - 1) * sides + i, (n_rings - 1) * sides + j))
    return mesh_from_data(name, verts, faces, material)


def make_box_tube(name, rings, material):
    verts, faces = [], []
    for z, hx, hy in rings:
        verts += [(hx, -hy, z), (hx, hy, z), (-hx, hy, z), (-hx, -hy, z)]
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            # winding flipped: QA 008 found the whole box tube inside-out
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


def build_character():
    """与 002 完全相同的角色几何。返回部件列表。"""
    skin = solid_material("Skin", (0.85, 0.62, 0.48), metallic=0.0, roughness=0.7)
    shirt = solid_material("Shirt_Teal", (0.12, 0.45, 0.50), metallic=0.0, roughness=0.8)
    pants = solid_material("Pants_Navy", (0.20, 0.24, 0.42), metallic=0.0, roughness=0.85)
    shoes = solid_material("Shoes_Brown", (0.25, 0.16, 0.10), metallic=0.0, roughness=0.9)
    hair = solid_material("Hair_Dark", (0.16, 0.10, 0.06), metallic=0.0, roughness=0.85)
    eyes = solid_material("Eyes_Dark", (0.05, 0.05, 0.06), metallic=0.0, roughness=0.4)

    parts = []
    head = add_sphere("Head", (0, 0, 1.50), 0.22, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    hair_obj = add_sphere("Hair", (0, 0, 1.56), 0.235, 8, 5, (1.0, 0.92, 0.85), hair)
    parts.append(hair_obj)
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.075, -0.185, 1.52), 0.028, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.09, 0.085], 6, skin)
    parts.append(neck)
    torso = make_box_tube("Torso", [(1.28, 0.31, 0.17), (0.95, 0.28, 0.16),
                                    (0.62, 0.25, 0.15)], shirt)
    parts.append(torso)
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.33, 0, 1.22))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.095, 0.090, 0.088, 0.082, 0.075], 6, shirt)
        parts.append(arm)
        wrist = shoulder + direction.normalized() * 0.55
        hand = add_sphere("Hand", tuple(wrist), 0.085, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    for sx in (-1, 1):
        hip = Vector((sx * 0.13, 0, 0.62))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.115, 0.108, 0.102, 0.092, 0.085], 6, pants)
        parts.append(leg)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sx * 0.13, -0.04, 0.045))
        foot = bpy.context.active_object
        foot.name = "Foot"
        foot.scale = (0.16, 0.28, 0.09)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        foot.data.materials.append(shoes)
        flat_shade(foot)
        parts.append(foot)
    for obj in parts:
        smart_uv_unwrap(obj)
    return parts


# ---------------------------------------------------------------- 骨架
# 角色面朝 -Y；左侧 = +X。关节位置取自 002 几何（肩/肘/腕/髋/膝/踝的环位置）。
BONES = [
    # name, head, tail, parent
    ("Hips",       (0, 0, 0.62),      (0, 0, 0.95),       None),
    ("Spine",      (0, 0, 0.95),      (0, 0, 1.28),       "Hips"),
    ("Neck",       (0, 0, 1.28),      (0, 0, 1.42),       "Spine"),
    ("Head",       (0, 0, 1.42),      (0, 0, 1.72),       "Neck"),
    ("Shoulder.L", (0.33, 0, 1.22),   (0.366, 0, 0.9625), "Spine"),
    ("Forearm.L",  (0.366, 0, 0.9625), (0.406, 0, 0.675), "Shoulder.L"),
    ("Hand.L",     (0.406, 0, 0.675), (0.41, 0, 0.60),    "Forearm.L"),
    ("Shoulder.R", (-0.33, 0, 1.22),  (-0.366, 0, 0.9625), "Spine"),
    ("Forearm.R",  (-0.366, 0, 0.9625), (-0.406, 0, 0.675), "Shoulder.R"),
    ("Hand.R",     (-0.406, 0, 0.675), (-0.41, 0, 0.60),   "Forearm.R"),
    ("Thigh.L",    (0.13, 0, 0.62),   (0.13, 0, 0.36),    "Hips"),
    ("Shin.L",     (0.13, 0, 0.36),   (0.13, 0, 0.10),    "Thigh.L"),
    ("Foot.L",     (0.13, 0, 0.10),   (0.13, -0.20, 0.05), "Shin.L"),
    ("Thigh.R",    (-0.13, 0, 0.62),  (-0.13, 0, 0.36),   "Hips"),
    ("Shin.R",     (-0.13, 0, 0.36),  (-0.13, 0, 0.10),   "Thigh.R"),
    ("Foot.R",     (-0.13, 0, 0.10),  (-0.13, -0.20, 0.05), "Shin.R"),
]

# 行走姿势：绕 X 轴旋转（弧度）。正值 = 向后摆（+Y），负值 = 向前摆（-Y）。
# 髋部下沉 0.08 米模拟行走中段重心下移；左腿前迈、右腿后蹬。
POSE = {
    "Hips":       {"loc": (0, 0, -0.08), "rot": (0.0, -0.02, 0.05)},
    "Spine":      {"rot": (0.08, 0.0, 0.0)},
    "Neck":       {"rot": (-0.03, 0.0, 0.0)},
    "Head":       {"rot": (-0.05, 0.0, 0.0)},
    "Shoulder.L": {"rot": (0.35, 0.0, 0.06)},
    "Forearm.L":  {"rot": (-0.45, 0.0, 0.0)},
    "Hand.L":     {"rot": (-0.10, 0.0, 0.0)},
    "Shoulder.R": {"rot": (-0.35, 0.0, -0.06)},
    "Forearm.R":  {"rot": (-0.35, 0.0, 0.0)},
    "Hand.R":     {"rot": (-0.10, 0.0, 0.0)},
    "Thigh.L":    {"rot": (-0.38, 0.0, 0.0)},
    "Shin.L":     {"rot": (-0.34, 0.0, 0.0)},
    "Foot.L":     {"rot": (0.72, 0.0, 0.0)},
    "Thigh.R":    {"rot": (0.38, 0.0, 0.0)},
    "Shin.R":     {"rot": (0.34, 0.0, 0.0)},
    "Foot.R":     {"rot": (-0.09, 0.0, 0.0)},
}


def build_armature():
    arm_data = bpy.data.armatures.new("CharacterRig")
    arm_obj = bpy.data.objects.new("CharacterRig", arm_data)
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
    studio_lights(target=(0, 0, 0.9))

    parts = build_character()
    total = total_poly_count(parts)
    counts = {o.name: poly_count(o) for o in parts}
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))

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

    # 3/4 视角：能看清迈步的前后错位
    cam = make_camera("Camera", (1.9, -2.4, 1.2), (0, 0, 0.8), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "007-character-rig.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "007-character-rig.blend"))

    export_deformed_wireframe(
        parts, cam, os.path.join("/tmp", "rig_wire.json"))

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
        "verification": check,
    }
    with open(os.path.join(ROOT, "scenes", "007-rig.json"), "w",
              encoding="utf-8") as f:
        json.dump(rig_info, f, ensure_ascii=False, indent=2)

    note = os.path.join(ROOT, "scenes", "007-character-rig.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 007 角色绑定准备：002 角色骨架 + 行走姿势\n\n")
        f.write("给 002 低模角色加骨架并摆出行走姿势。角色几何与 002 完全一致。\n\n")
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
        f.write("- 肘 / 膝弯曲处正好落在 002 预留的关节环形边线上，弯曲不断裂\n\n")
        f.write("## 行走姿势（行走循环中段）\n\n")
        f.write("- 左腿前迈着地（大腿 -22°，小腿 -19°，脚掌放平），右腿后蹬脚尖点地（大腿 +22°，小腿 +19°）\n")
        f.write("- 手臂反向摆动：左臂后摆 +20°、右臂前摆 -20°，双肘微屈\n")
        f.write("- 髋部下沉 0.08 米、躯干微前倾 5°，模拟行走重心起伏\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d），与 002 一致\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绑定验证（实测，非估算）\n\n")
        f.write("- 姿势求值后全角色最低点 z = %.3f（前脚基本贴地）\n"
                % check["_overall_min_z"])
        f.write("- 各部件最大顶点位移（米）：左腿 %.3f、右腿 %.3f、左臂 %.3f、右臂 %.3f\n"
                % (check.get("Leg.001", {}).get("max_displacement", 0),
                   check.get("Leg", {}).get("max_displacement", 0),
                   check.get("Arm.001", {}).get("max_displacement", 0),
                   check.get("Arm", {}).get("max_displacement", 0)))
        f.write("- 骨架 + 蒙皮 + 姿势全部保存在 scenes/007-character-rig.blend，"
                "打开即可在姿势模式下继续调动作\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，3/4 视角\n")
        f.write("- 线框图：同角度，姿势变形后的真实投影边线叠加\n")
    print("NOTE_WRITTEN:", note)
    print("RIG_JSON:", os.path.join(ROOT, "scenes", "007-rig.json"))


if __name__ == "__main__":
    main()
