# -*- coding: utf-8 -*-
"""042 低模游戏角色：图书管理员
Low-poly librarian game character, bind-ready: long burgundy robe with
a cream collar, round wire glasses, grey hair in a bun, leather belt
with a brass buckle, and a leather-bound book held in both arms.
Arms and legs are 5-ring tubes: the middle ring lands exactly on the
elbow / knee joint loop. Flat shading, Eevee beauty + wireframe shots.
Camera is auto-fitted with fit_camera_to_objects (target fill 0.78).
Run: blender --background --python 042-lowpoly-librarian.py
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


def srgb(rgb):
    """sRGB swatch -> linear values for Principled BSDF Base Color."""
    def conv(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(conv(c) for c in rgb)


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

    skin = solid_material("Skin", srgb((0.86, 0.63, 0.48)), metallic=0.0, roughness=0.7)
    robe = solid_material("Robe_Burgundy", srgb((0.42, 0.13, 0.16)), metallic=0.0, roughness=0.85)
    robe_dark = solid_material("Robe_Dark", srgb((0.30, 0.09, 0.12)), metallic=0.0, roughness=0.9)
    cream = solid_material("Collar_Cream", srgb((0.88, 0.82, 0.68)), metallic=0.0, roughness=0.85)
    leather = solid_material("Leather_Brown", srgb((0.42, 0.26, 0.13)), metallic=0.0, roughness=0.85)
    leather_dark = solid_material("Leather_Dark", srgb((0.30, 0.18, 0.09)), metallic=0.0, roughness=0.9)
    brass = solid_material("Brass", srgb((0.72, 0.55, 0.20)), metallic=0.8, roughness=0.35)
    eyes = solid_material("Eyes_Dark", srgb((0.05, 0.05, 0.06)), metallic=0.0, roughness=0.4)
    hair = solid_material("Hair_Grey", srgb((0.62, 0.60, 0.58)), metallic=0.0, roughness=0.85)
    book_cover = solid_material("Book_Red", srgb((0.48, 0.12, 0.10)), metallic=0.0, roughness=0.8)
    pages = solid_material("Pages_Cream", srgb((0.90, 0.85, 0.70)), metallic=0.0, roughness=0.9)
    pants = solid_material("Pants_Grey", srgb((0.28, 0.27, 0.30)), metallic=0.0, roughness=0.9)

    parts = []
    # --- head (front is -Y) ---
    head = add_sphere("Head", (0, 0, 1.52), 0.20, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- eyes ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.07, -0.168, 1.53), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- grey hair: cap on top + bun at the back ---
    cap = add_sphere("HairCap", (0, 0.02, 1.63), 0.19, 8, 5,
                     (1.0, 0.95, 0.62), hair)
    parts.append(cap)
    bun = add_sphere("HairBun", (0, 0.15, 1.68), 0.09, 8, 5,
                     (1.0, 1.0, 1.0), hair)
    parts.append(bun)
    # --- round wire glasses: two torus rims + bridge + temples ---
    for sx in (-1, 1):
        rim = add_torus("GlassesRim", (sx * 0.078, -0.172, 1.545),
                        0.055, 0.008, 12, 4,
                        (math.radians(90), 0, 0), brass)
        parts.append(rim)
    bridge = cyl_between("GlassesBridge", (-0.024, -0.178, 1.548),
                         (0.024, -0.178, 1.548), 0.007, 4, brass)
    parts.append(bridge)
    for sx in (-1, 1):
        temple = cyl_between("GlassesTemple", (sx * 0.13, -0.175, 1.545),
                             (sx * 0.19, -0.02, 1.55), 0.006, 4, brass)
        parts.append(temple)
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.08, 0.075], 6, skin)
    parts.append(neck)
    # --- cream collar: short tube at the neckline ---
    collar = make_tube("Collar", (0, 0, 1.26), (0, 0, 1),
                       [0.0, 0.06], [0.16, 0.15], 8, cream)
    parts.append(collar)
    # --- shawl over the shoulders: flared tube, dark burgundy ---
    shawl = make_tube("Shawl", (0, 0, 1.32), (0, 0, -1),
                      [0.0, 0.12, 0.22],
                      [0.31, 0.35, 0.38], 8, robe_dark)
    parts.append(shawl)
    # --- long robe: 5 rings, flaring to a hem just above the ground ---
    robe_obj = make_tube("Robe", (0, 0, 1.30), (0, 0, -1),
                         [0.0, 0.30, 0.60, 0.90, 1.20],
                         [0.30, 0.315, 0.335, 0.365, 0.40], 8, robe)
    parts.append(robe_obj)
    # --- belt + brass buckle ---
    belt = make_tube("Belt", (0, 0, 0.98), (0, 0, -1),
                     [0.0, 0.07], [0.345, 0.345], 8, leather_dark)
    parts.append(belt)
    buckle = box("Buckle", (0, -0.345, 0.945), (0.09, 0.02, 0.06), brass)
    parts.append(buckle)
    # --- arms: 5 rings, middle ring = elbow joint loop; angled forward
    #     to hold the book in front of the chest ---
    wrists = {}
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.30, 0, 1.22))
        wrist = Vector((sx * 0.17, -0.40, 0.97))
        direction = wrist - shoulder
        length = direction.length
        direction.normalize()
        arm = make_tube("Arm", shoulder, direction,
                        [0.0, length * 0.25, length * 0.5,
                         length * 0.75, length],
                        [0.105, 0.10, 0.095, 0.085, 0.075], 6, robe)
        parts.append(arm)
        # cream cuff at the wrist
        cuff = make_tube("Cuff", shoulder + direction * (length * 0.78),
                         direction, [0.0, length * 0.22],
                         [0.088, 0.082], 6, cream)
        parts.append(cuff)
        wrists[sx] = wrist
        hand = add_sphere("Hand", tuple(wrist), 0.065, 6, 4,
                          (1.0, 0.9, 0.8), skin)
        parts.append(hand)
    # --- book held in both hands: leather cover + cream page block,
    #     tilted slightly toward the viewer. Book center sits well in
    #     front of the robe/belt (robe front ~-0.32, belt front ~-0.345
    #     at this height) so the book stays visible. ---
    bc = Vector((0, -0.42, 0.98))
    book = box("BookCover", tuple(bc), (0.34, 0.05, 0.24), book_cover)
    book.rotation_euler = (math.radians(-8), 0, 0)
    parts.append(book)
    page_block = box("BookPages", tuple(bc + Vector((0, 0.002, 0))),
                     (0.31, 0.056, 0.21), pages)
    page_block.rotation_euler = (math.radians(-8), 0, 0)
    parts.append(page_block)
    # book spine band (brass clasp across the cover)
    clasp = box("BookClasp", tuple(bc + Vector((0, -0.027, 0))),
                (0.05, 0.008, 0.24), brass)
    clasp.rotation_euler = (math.radians(-8), 0, 0)
    parts.append(clasp)
    # --- legs under the robe: 5 rings, middle ring = knee joint loop ---
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.55))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.125, 0.25, 0.375, 0.50],
                        [0.10, 0.098, 0.093, 0.086, 0.08], 6, pants)
        parts.append(leg)
        # shoe: toe pokes forward past the robe hem
        shoe = box("Shoe", (sx * 0.12, -0.30, 0.055), (0.15, 0.34, 0.11),
                   leather_dark)
        parts.append(shoe)

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "042-lowpoly-librarian.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "042-lowpoly-librarian.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "librarian_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("LIBRARIAN_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("LIBRARIAN_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "042-lowpoly-librarian.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 042 低模游戏角色：图书管理员\n\n")
        f.write("低多边形风格化图书管理员，平面着色（flat shading），绑定就绪。\n\n")
        f.write("## 造型\n\n")
        f.write("- 头部：皮肤球头 + 灰发（顶部发盖 + 脑后发髻）+ 圆框黄铜眼镜（双圆环镜框 + 鼻梁 + 镜腿）\n")
        f.write("- 上身：酒红长袍（5 环，自肩部微喇叭下摆至脚踝）+ 深红披肩 + 奶油色领口\n")
        f.write("- 腰部：深棕皮带 + 黄铜带扣（正面）\n")
        f.write("- 双臂前伸怀抱一本皮面书：红色书封 + 奶油书页 + 黄铜锁扣，书身微向前倾 8°\n")
        f.write("- 腿部藏于袍下：灰裤 + 深棕皮鞋，鞋尖从袍摆前探出\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节\n")
        f.write("- 手腕另有奶油袖口（2 环），不遮挡肘部关节环\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n")
        f.write("- N-gon 均为圆柱体端盖（颈、领口、披肩、长袍、皮带、袖口、裤腿等），不在关节处\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Robe_Burgundy / Robe_Dark：酒红长袍与深红披肩\n")
        f.write("- Collar_Cream / Pages_Cream：奶油领口与书页\n")
        f.write("- Leather_Brown / Leather_Dark：皮带、皮鞋；Brass：眼镜、带扣、书锁扣\n")
        f.write("- Skin / Eyes_Dark / Hair_Grey：皮肤、眼睛、灰发；Book_Red：书封\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
