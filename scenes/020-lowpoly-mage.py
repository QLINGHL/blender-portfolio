# -*- coding: utf-8 -*-
"""020 低模游戏角色：法师
Low-poly mage game character, bind-ready: long robe, pointed hat, beard,
wooden staff topped with an octahedral crystal, 5-ring arms (elbow joint
loop in the middle) and 5-ring legs under the robe (knee joint loop).
Flat shading, Eevee beauty + wireframe shots.
Run: blender --background --python 020-lowpoly-mage.py
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


def make_octahedron(name, location, radius_xy, radius_z, material):
    """8-face octahedron: top/bottom apex + 4 equator vertices."""
    cx, cy, cz = location
    verts = [(cx, cy, cz + radius_z),
             (cx, cy, cz - radius_z),
             (cx + radius_xy, cy, cz),
             (cx, cy - radius_xy, cz),
             (cx - radius_xy, cy, cz),
             (cx, cy + radius_xy, cz)]
    faces = [(0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
             (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5)]
    return mesh_from_data(name, verts, faces, material)


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

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
    # glowing crystal: emission tint on top of the base color
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
    # --- head ---
    head = add_sphere("Head", (0, 0, 1.52), 0.21, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- eyes (front is -Y) ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.072, -0.178, 1.51), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- beard: tapered tube from the chin down the front of the robe ---
    beard = make_tube("Beard", (0, -0.18, 1.38), (0, -0.75, -1),
                      [0.0, 0.14, 0.28, 0.40],
                      [0.11, 0.095, 0.07, 0.025], 6, beard_mat)
    parts.append(beard)
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.085, 0.08], 6, skin)
    parts.append(neck)
    # --- pointed hat: brim disk + slightly tilted cone ---
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
    # hat tip: tiny gold sphere so the point reads at a glance
    tip = add_sphere("HatTip", (0.04, 0, 2.11), 0.03, 6, 3, (1.0, 1.0, 1.0), gold)
    parts.append(tip)
    # --- robe: 5 rings, flared from shoulders to the floor ---
    robe_obj = make_tube("Robe", (0, 0, 1.30), (0, 0, -1),
                         [0.0, 0.30, 0.62, 0.95, 1.25],
                         [0.30, 0.31, 0.34, 0.40, 0.48], 8, robe)
    parts.append(robe_obj)
    # --- collar: short flared ring at the neckline ---
    collar = make_tube("Collar", (0, 0, 1.30), (0, 0, 1),
                       [0.0, 0.09], [0.30, 0.20], 8, robe_dark)
    parts.append(collar)
    # --- gold rope sash at the waist: octagonal band hugging the robe ---
    sash = make_tube("Sash", (0, 0, 0.90), (0, 0, -1),
                     [0.0, 0.08], [0.34, 0.34], 8, gold)
    parts.append(sash)
    # --- arms: 5 rings, middle ring = elbow joint loop; wide robe sleeves ---
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
    # --- legs under the robe: 5 rings, middle ring = knee joint loop ---
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
    # --- staff in right hand (+X): wooden shaft, gold rings, octahedral crystal ---
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

    cam = make_camera("Camera", (0, -3.8, 1.25), (0, 0, 1.0), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "020-lowpoly-mage.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "020-lowpoly-mage.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "mage_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("CHAR_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CHAR_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "020-lowpoly-mage.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 020 低模游戏角色：法师\n\n")
        f.write("低多边形风格化法师，平面着色（flat shading），绑定就绪。\n\n")
        f.write("## 造型\n\n")
        f.write("- 紫色长袍：5 环喇叭形长袍（肩 → 地面），深紫色领口 + 金色腰绳\n")
        f.write("- 尖顶帽：12 边帽檐 + 微倾 8 边锥形帽身，帽尖金色小球\n")
        f.write("- 白胡须：下巴垂至胸前的 4 环锥形胡须\n")
        f.write("- 右手持杖：木杖 + 两道金箍 + 八面体水晶（微发光材质）\n")
        f.write("- 袍下双腿 + 前指式方靴，靴尖从袍摆下露出\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节（藏于长袍下，绑定时仍可用）\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n")
        f.write("- 8 个 N-gon 均为圆柱体端盖（杖身 2 个、杖箍 4 个、帽檐 2 个），不在关节处\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Robe_Purple / Robe_Dark：紫色长袍与深紫帽身、领口\n")
        f.write("- Trim_Gold：金色腰绳 / 帽尖小球 / 法杖金箍\n")
        f.write("- Crystal：八面体水晶（Principled + 45%% 发光混合）\n")
        f.write("- Staff_Wood：木杖；Beard_White：白胡须；Pants_Navy / Boots_Brown：袍下裤腿与靴子\n")
        f.write("- Skin / Eyes_Dark：皮肤、眼睛\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
