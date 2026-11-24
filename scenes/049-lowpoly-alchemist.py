# -*- coding: utf-8 -*-
"""049 低模游戏角色：炼金术士
Low-poly alchemist game character, bind-ready: deep teal robe with a
brown leather apron (front panel + shoulder straps), brass goggles
pushed up on the forehead, a leather belt with three potion bottles
(red / blue / purple), and an Erlenmeyer flask with glowing green
liquid held in both hands in front of the chest.
Arms and legs are 5-ring tubes: the middle ring lands exactly on the
elbow / knee joint loop. Flat shading, Eevee beauty + wireframe shots.
Camera is auto-fitted with fit_camera_to_objects (target fill 0.78).
042 lesson applied: the held prop sits well in front of the robe and
apron (robe front ~-0.33, apron front ~-0.38, flask centre y=-0.48)
so it stays visible; shoes bottom at z=0.
Run: blender --background --python 049-lowpoly-alchemist.py
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
    Rings are edge loops — joints land exactly on a ring.
    Winding: 048 修正版（照搬 045/007/022：管盖扇形绕向与 042 旧版相反，
    旧版 148 个倒置面全是管盖扇形）。"""
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


def glass_material(name, color, alpha=0.35, roughness=0.15):
    """Semi-transparent glass (Eevee dithered) so liquid inside shows."""
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


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 1.0))

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
    # --- head (front is -Y) ---
    head = add_sphere("Head", (0, 0, 1.52), 0.20, 8, 6, (1.0, 0.9, 1.05), skin)
    parts.append(head)
    # --- eyes ---
    for sx in (-1, 1):
        eye = add_sphere("Eye", (sx * 0.07, -0.168, 1.53), 0.026, 6, 3,
                         (1.0, 1.0, 1.0), eyes)
        parts.append(eye)
    # --- brown hair cap + short grey beard ---
    cap = add_sphere("HairCap", (0, 0.02, 1.63), 0.19, 8, 5,
                     (1.0, 0.95, 0.62), hair)
    parts.append(cap)
    beard = add_sphere("Beard", (0, -0.10, 1.38), 0.09, 8, 5,
                       (1.0, 0.75, 0.85), beard_mat)
    parts.append(beard)
    # --- forehead goggles: two brass rims + green lenses, tilted up,
    #     plus a leather strap around the head ---
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
    # --- neck ---
    neck = make_tube("Neck", (0, 0, 1.28), (0, 0, 1), [0.0, 0.10],
                     [0.08, 0.075], 6, skin)
    parts.append(neck)
    # --- shirt collar at the neckline ---
    collar = make_tube("Collar", (0, 0, 1.26), (0, 0, 1),
                       [0.0, 0.06], [0.16, 0.15], 8, robe_dark)
    parts.append(collar)
    # --- shoulder shawl: flared tube, dark teal ---
    shawl = make_tube("Shawl", (0, 0, 1.32), (0, 0, -1),
                      [0.0, 0.12, 0.22],
                      [0.31, 0.35, 0.38], 8, robe_dark)
    parts.append(shawl)
    # --- long robe: 5 rings, flaring to a hem just above the ground ---
    robe_obj = make_tube("Robe", (0, 0, 1.30), (0, 0, -1),
                         [0.0, 0.30, 0.60, 0.90, 1.20],
                         [0.30, 0.315, 0.335, 0.365, 0.40], 8, robe)
    parts.append(robe_obj)
    # --- apron: front panel following the robe flare (slight tilt),
    #     front face at y ~ -0.38, plus two shoulder straps ---
    apron_panel = box("Apron", (0, -0.365, 0.75), (0.44, 0.03, 0.95), apron)
    apron_panel.rotation_euler = (math.radians(-4), 0, 0)
    parts.append(apron_panel)
    apron_pocket = box("ApronPocket", (0, -0.385, 0.55), (0.20, 0.025, 0.14),
                       apron_dark)
    apron_pocket.rotation_euler = (math.radians(-4), 0, 0)
    parts.append(apron_pocket)
    for sx in (-1, 1):
        strap = box("ApronStrap", (sx * 0.13, 0, 1.26), (0.07, 0.72, 0.025),
                    apron)
        parts.append(strap)
    # --- belt + brass buckle ---
    belt = make_tube("Belt", (0, 0, 0.98), (0, 0, -1),
                     [0.0, 0.07], [0.345, 0.345], 8, leather_dark)
    parts.append(belt)
    buckle = box("Buckle", (0, -0.345, 0.945), (0.09, 0.02, 0.06), brass)
    parts.append(buckle)
    # --- three potion bottles hanging from the belt (front arc).
    #     Bottles sit at y=-0.42, clearly in front of the apron face
    #     (~-0.38), so all three read instead of sinking into the apron. ---
    bottle_defs = [(-0.26, potion_red, "PotionRed"),
                   (0.0, potion_blue, "PotionBlue"),
                   (0.26, potion_purple, "PotionPurple")]
    for bx, bmat, bname in bottle_defs:
        body = make_tube(bname + "Body", (bx, -0.42, 0.78), (0, 0, 1),
                         [0.0, 0.09, 0.12], [0.045, 0.05, 0.02], 6, bmat)
        parts.append(body)
        cork_top = make_tube(bname + "Cork", (bx, -0.42, 0.90), (0, 0, 1),
                             [0.0, 0.03], [0.022, 0.02], 6, cork)
        parts.append(cork_top)
    # --- arms: 5 rings, middle ring = elbow joint loop; angled forward
    #     to hold the flask in front of the chest ---
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
    # --- Erlenmeyer flask held in both hands, well in front of the
    #     apron (apron front ~-0.38, flask centre y=-0.48): glass cone +
    #     neck + cork + bright green liquid inside, tilted slightly
    #     toward the viewer so the liquid reads. ---
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
    # --- legs under the robe: 5 rings, middle ring = knee joint loop ---
    for sx in (-1, 1):
        hip = Vector((sx * 0.12, 0, 0.55))
        leg = make_tube("Leg", hip, (0, 0, -1),
                        [0.0, 0.125, 0.25, 0.375, 0.50],
                        [0.10, 0.098, 0.093, 0.086, 0.08], 6, pants)
        parts.append(leg)
        # shoe: toe pokes forward past the robe hem, bottom at z=0
        shoe = box("Shoe", (sx * 0.12, -0.30, 0.055), (0.15, 0.34, 0.11),
                   leather_dark)
        parts.append(shoe)

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "049-lowpoly-alchemist.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "049-lowpoly-alchemist.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "alchemist_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("ALCHEMIST_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("ALCHEMIST_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "049-lowpoly-alchemist.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 049 低模游戏角色：炼金术士\n\n")
        f.write("低多边形风格化炼金术士，平面着色（flat shading），绑定就绪。接 047 炼金实验室场景的人物线。\n\n")
        f.write("## 造型\n\n")
        f.write("- 头部：皮肤球头 + 棕色发盖 + 灰色短须 + 前额黄铜护目镜（双圆环镜框 + 绿色镜片 + 绕头皮带），护目镜推上额头\n")
        f.write("- 上身：深青长袍（5 环，自肩部微喇叭下摆至脚踝）+ 深青披肩 + 棕色皮围裙（前片 + 兜 + 双肩带）\n")
        f.write("- 腰部：深棕皮带 + 黄铜带扣，正面挂三瓶药水（红 / 蓝 / 紫，瓶身 + 瓶塞）\n")
        f.write("- 双手身前持一只锥形烧瓶：透明玻璃锥体 + 瓶颈 + 瓶塞，内装亮绿药液；烧瓶中心 y=-0.48，位于围裙前片（y≈-0.38）前方 0.10，正面清晰可见（042 教训）\n")
        f.write("- 腿部藏于袍下：灰裤 + 深棕皮鞋，鞋尖从袍摆前探出，鞋底 z=0 落地\n\n")
        f.write("## 关节拓扑（绑定就绪）\n\n")
        f.write("- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）\n")
        f.write("- 腿部：5 个环形边线，中间环正好落在膝关节\n")
        f.write("- 手腕另有皮质袖口（2 环），不遮挡肘部关节环\n")
        f.write("- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配\n")
        f.write("- 关节处无三角面集中、无极点（pole）堆积\n")
        f.write("- N-gon 均为圆柱体端盖（颈、领口、披肩、长袍、皮带、袖口、裤腿、药水瓶等），不在关节处\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Robe_Teal / Robe_Dark：深青长袍与深青披肩\n")
        f.write("- Apron_Brown / Apron_Dark：棕色围裙与围裙兜；Leather_Dark：皮带、皮鞋、护目镜带\n")
        f.write("- Brass：护目镜框、带扣；Lens_Green：护目镜镜片\n")
        f.write("- Flask_Glass / Flask_Liquid：烧瓶玻璃与亮绿药液；Potion_Red/Blue/Purple：三瓶药水\n")
        f.write("- Skin / Eyes_Dark / Hair_Brown / Beard_Grey：皮肤、眼睛、棕发、灰须\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
