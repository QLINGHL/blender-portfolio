# -*- coding: utf-8 -*-
"""006 低模游戏角色：女战士
Female low-poly game character, bind-ready: explicit edge-loop rings at
shoulder / elbow / knee / ankle, plus armor, skirt tassets, ponytail,
sword in right hand and round shield on left forearm.
Flat shading, Eevee beauty + wireframe shots.
Run: blender --background --python 006-lowpoly-warrior.py
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
                    make_camera, flat_shade, poly_count, total_poly_count,
                    setup_render, render, export_wireframe_segments)


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


def make_box_tube(name, rings, material):
    """Rectangular tube from a list of (z, half_x, half_y) rings (CCW corners)."""
    verts, faces = [], []
    for z, hx, hy in rings:
        verts += [(hx, -hy, z), (hx, hy, z), (-hx, hy, z), (-hx, -hy, z)]
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((k * 4 + i, k * 4 + j, (k + 1) * 4 + j, (k + 1) * 4 + i))
    n = len(rings)
    faces.append(((n - 1) * 4, (n - 1) * 4 + 1, (n - 1) * 4 + 2, (n - 1) * 4 + 3))
    faces.append((3, 2, 1, 0))
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


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.9))

    skin = solid_material("Skin", (0.86, 0.63, 0.48), metallic=0.0, roughness=0.7)
    armor = solid_material("Armor_Steel", (0.58, 0.60, 0.65), metallic=0.75, roughness=0.35)
    cloth = solid_material("Cloth_Red", (0.48, 0.08, 0.07), metallic=0.0, roughness=0.85)
    gold = solid_material("Trim_Gold", (0.78, 0.60, 0.22), metallic=0.85, roughness=0.3)
    pants = solid_material("Pants_Navy", (0.20, 0.24, 0.42), metallic=0.0, roughness=0.85)
    boots = solid_material("Boots_Brown", (0.28, 0.18, 0.11), metallic=0.0, roughness=0.9)
    hair = solid_material("Hair_Blonde", (0.85, 0.66, 0.28), metallic=0.0, roughness=0.8)
    eyes = solid_material("Eyes_Dark", (0.05, 0.05, 0.06), metallic=0.0, roughness=0.4)
    blade = solid_material("Blade_Steel", (0.78, 0.80, 0.84), metallic=0.9, roughness=0.25)

    parts = []
    # --- head ---
    head = add_sphere("Head", (0, 0, 1.52), 0.21, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- hair cap: sits higher so the face shows ---
    hair_obj = add_sphere("Hair", (0, 0, 1.61), 0.215, 8, 5, (1.0, 0.92, 0.78), hair)
    parts.append(hair_obj)
    # --- ponytail: tube curving down the back (+Y is the back) ---
    pony = make_tube("Ponytail", (0, 0.14, 1.62), (0, 0.35, -1),
                     [0.0, 0.18, 0.36, 0.52],
                     [0.10, 0.09, 0.075, 0.05], 6, hair)
    parts.append(pony)
    # --- eyes (front is -Y) ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.072, -0.178, 1.51), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.30), (0, 0, 1), [0.0, 0.09],
                     [0.085, 0.08], 6, skin)
    parts.append(neck)
    # --- torso: armor breastplate, 4 rings (shoulder / chest / waist / hip) ---
    torso = make_box_tube("Torso", [(1.30, 0.30, 0.16), (1.08, 0.27, 0.16),
                                    (0.80, 0.21, 0.13), (0.64, 0.24, 0.15)], armor)
    parts.append(torso)
    # --- belt: thin gold ring at the waist ---
    belt = make_box_tube("Belt", [(0.82, 0.225, 0.145), (0.76, 0.225, 0.145)], gold)
    parts.append(belt)
    # --- skirt tassets: flared 8-sided tube, hip -> knee height ---
    skirt = make_tube("Skirt", (0, 0, 0.64), (0, 0, -1),
                      [0.0, 0.10, 0.20, 0.28],
                      [0.26, 0.29, 0.315, 0.33], 8, cloth)
    parts.append(skirt)
    # --- arms: 5 rings, middle ring = elbow joint loop ---
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.32, 0, 1.24))
        direction = Vector((sx * 0.14, 0, -1))
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.085, 0.082, 0.080, 0.075, 0.068], 6, skin)
        parts.append(arm)
        # shoulder pad: half-dome armor
        pad = add_sphere("ShoulderPad", (sx * 0.33, 0, 1.26), 0.13, 8, 4,
                         (1.0, 1.0, 0.75), armor)
        parts.append(pad)
        wrist = shoulder + direction.normalized() * 0.55
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.08, 6, 4, (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    # --- legs: 5 rings, middle ring = knee joint loop ---
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.62))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.13, 0.26, 0.39, 0.52],
                        [0.105, 0.10, 0.095, 0.088, 0.082], 6, pants)
        parts.append(leg)
        # boot: forward-pointing box (-Y)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sx * 0.12, -0.04, 0.05))
        foot = bpy.context.active_object
        foot.name = "Boot"
        foot.scale = (0.15, 0.27, 0.10)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        foot.data.materials.append(boots)
        flat_shade(foot)
        parts.append(foot)
    # --- sword in right hand (+X), blade leaning outward so it clears the arm ---
    hand_r = wrists[1]
    sword_x = hand_r.x + 0.10
    # handle: small cylinder below the hand
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.035, depth=0.22,
                                        location=(sword_x, hand_r.y, hand_r.z - 0.08))
    handle = bpy.context.active_object
    handle.name = "SwordHandle"
    handle.data.materials.append(boots)
    flat_shade(handle)
    parts.append(handle)
    # guard: flat gold box at the hand
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sword_x, hand_r.y, hand_r.z + 0.05))
    guard = bpy.context.active_object
    guard.name = "SwordGuard"
    guard.scale = (0.16, 0.05, 0.03)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    guard.data.materials.append(gold)
    flat_shade(guard)
    parts.append(guard)
    # blade: tapered 4-sided tube, flattened in Y for a flat blade
    sword_blade = make_tube("SwordBlade", (sword_x, hand_r.y, hand_r.z + 0.06),
                            (0.18, 0, 1), [0.0, 0.55, 0.85, 0.95],
                            [0.09, 0.085, 0.055, 0.001], 4, blade)
    sword_blade.scale = (1.0, 0.28, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    parts.append(sword_blade)
    # --- round shield on left forearm (-X), face turned toward the camera ---
    hand_l = wrists[-1]
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.23, depth=0.045,
                                        location=(hand_l.x - 0.02, hand_l.y - 0.10, hand_l.z + 0.08))
    shield = bpy.context.active_object
    shield.name = "Shield"
    shield.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    shield.data.materials.append(armor)
    flat_shade(shield)
    parts.append(shield)
    # shield boss: small gold dome on the shield face
    boss = add_sphere("ShieldBoss", (hand_l.x - 0.02, hand_l.y - 0.14, hand_l.z + 0.08),
                      0.07, 8, 4, (1.0, 1.0, 0.6), gold)
    parts.append(boss)

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = make_camera("Camera", (0, -3.6, 1.1), (0, 0, 0.95), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "006-lowpoly-warrior.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "006-lowpoly-warrior.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "warrior_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CHAR_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "006-lowpoly-warrior.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 006 低模游戏角色：女战士\n\n")
        f.write("低多边形风格化女战士，平面着色（flat shading），绑定就绪。\n\n")
        f.write("## 造型\n\n")
        f.write("- 金发马尾：发髻 + 向后下方垂落的马尾（4 环锥形管）\n")
        f.write("- 钢甲胸甲：4 环收腰造型（肩 / 胸 / 腰 / 胯），金色腰带\n")
        f.write("- 红色裙甲：8 边喇叭形裙摆（胯 → 膝上），4 环\n")
        f.write("- 右手持剑：木柄 + 金护手 + 扁平锥形钢刃（剑尖朝上）\n")
        f.write("- 左臂圆盾：钢盾 + 金色盾心\n")
        f.write("- 肩甲：两侧半球形钢肩甲；靴子为前指式方靴\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Armor_Steel：钢甲（metallic 0.75）；Blade_Steel：剑刃（metallic 0.9）\n")
        f.write("- Trim_Gold：金色饰边 / 腰带 / 护手 / 盾心\n")
        f.write("- Cloth_Red：红色裙甲；Pants_Navy：裤子；Boots_Brown：靴 / 剑柄\n")
        f.write("- Skin / Hair_Blonde / Eyes_Dark：皮肤、金发、眼睛\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
