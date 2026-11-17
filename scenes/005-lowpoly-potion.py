# -*- coding: utf-8 -*-
"""005 低模游戏道具：药水瓶
Build a low-poly game potion bottle (lathe body / inner liquid / cork /
parchment label / wax seal), render a beauty shot and a wireframe shot
with Eevee, save .blend + a description note.
Run: blender --background --python 005-lowpoly-potion.py
"""
import os
import sys
import math
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


def build_lathe(name, profile, sides, mat, cap_bottom=True, cap_top=True):
    """Lathe from a bottom->top list of (z, r) rings. Rings are CCW in top
    view, same winding as 001's blade so side normals point outward."""
    verts, faces = [], []
    for z, r in profile:
        base = len(verts)
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(a), r * math.sin(a), z))
        if base > 0:
            prev = base - sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.append((prev + i, prev + j, base + j, base + i))
    if cap_bottom:
        z0, _ = profile[0]
        c = len(verts)
        verts.append((0, 0, z0))
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((c, j, i))
    if cap_top:
        z1, _ = profile[-1]
        c = len(verts)
        verts.append((0, 0, z1))
        top = (len(profile) - 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((c, top + i, top + j))
    return mesh_from_data(name, verts, faces, mat)


def glass_material(name, color, alpha=0.35):
    """Semi-transparent glass: Principled BSDF with alpha, blended render."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.08
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        mat.blend_method = 'BLEND'
    try:
        mat.shadow_method = 'NONE'
    except AttributeError:
        pass
    return mat


def build_label(name, z0, z1, r0, r1, center_deg=-90.0, span_deg=100.0,
                arc_segments=6, offset=0.006, mat=None):
    """Curved parchment label: a cylindrical patch hugging the bottle belly,
    facing the camera (-Y)."""
    verts, faces = [], []
    for z, r in ((z0, r0 + offset), (z1, r1 + offset)):
        base = len(verts)
        for k in range(arc_segments + 1):
            a = math.radians(center_deg - span_deg / 2.0
                             + span_deg * k / arc_segments)
            verts.append((r * math.cos(a), r * math.sin(a), z))
        if base > 0:
            prev = base - (arc_segments + 1)
            for k in range(arc_segments):
                faces.append((prev + k, prev + k + 1,
                              base + k + 1, base + k))
    return mesh_from_data(name, verts, faces, mat)


def build_wax_seal(name, center, radius=0.06, sides=12, mat=None):
    """Flat disc in the YZ plane, normal facing -Y (toward the camera)."""
    cx, cy, cz = center
    verts = [(cx, cy, cz)]
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        verts.append((cx + radius * math.cos(a), cy,
                      cz + radius * math.sin(a)))
    faces = [(0, i + 1, (i + 1) % sides + 1) for i in range(sides)]
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
    add_ground()
    studio_lights(target=(0, 0, 0.8))

    glass = glass_material("Bottle_Glass", (0.45, 0.75, 0.72), alpha=0.38)
    liquid_mat = solid_material("Potion_Liquid", (0.78, 0.12, 0.14),
                                metallic=0.0, roughness=0.15)
    cork_mat = solid_material("Cork_Wood", (0.62, 0.44, 0.24),
                              metallic=0.0, roughness=0.85)
    label_mat = solid_material("Label_Parchment", (0.92, 0.85, 0.66),
                               metallic=0.0, roughness=0.9)
    wax_mat = solid_material("Wax_Seal", (0.55, 0.08, 0.10),
                             metallic=0.0, roughness=0.5)

    # Bottle body: 10-sided lathe, base -> belly -> shoulder -> neck -> lip
    body_profile = [
        (0.00, 0.30), (0.05, 0.30), (0.12, 0.34), (0.50, 0.36),
        (0.85, 0.33), (1.05, 0.24), (1.18, 0.15), (1.30, 0.13),
        (1.42, 0.145),
    ]
    bottle = build_lathe("Bottle", body_profile, 10, glass)

    # Inner liquid: same silhouette scaled in, flat surface at z = 1.00
    liquid_profile = [
        (0.03, 0.27), (0.12, 0.305), (0.50, 0.325),
        (0.85, 0.295), (1.00, 0.225),
    ]
    liquid = build_lathe("Liquid", liquid_profile, 10, liquid_mat)

    # Cork: tapered 8-sided plug + slightly wider top cap
    cork_profile = [
        (1.38, 0.105), (1.50, 0.115), (1.56, 0.135), (1.62, 0.135),
    ]
    cork = build_lathe("Cork", cork_profile, 8, cork_mat)

    # Label: curved patch on the belly, facing the camera
    label = build_label("Label", 0.35, 0.78, 0.355, 0.345, mat=label_mat)

    # Wax seal: small disc on the label, facing the camera
    seal = build_wax_seal("WaxSeal", (0.0, -0.368, 0.56), radius=0.06,
                          sides=12, mat=wax_mat)

    parts = [bottle, liquid, cork, label, seal]

    for obj in parts:
        smart_uv_unwrap(obj)

    cam = make_camera("Camera", (0, -4.2, 1.1), (0, 0, 0.8), lens=50.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    # --- beauty render, then save .blend with beauty materials ---
    render(os.path.join(ROOT, "renders", "005-lowpoly-potion.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "005-lowpoly-potion.blend"))

    # --- wireframe: export visible projected edges (drawn in PIL) ---
    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "potion_wire.json"))

    counts = {o.name: poly_count(o) for o in parts}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts for p in o.data.polygons if len(p.vertices) > 4)
    print("POTION_POLY total=%d tris=%d quads=%d ngons=%d" % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("POTION_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "005-lowpoly-potion.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 005 低模游戏道具：药水瓶\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 瓶身：10 边车削轮廓（底座 → 肚 → 肩 → 颈 → 瓶口唇），半透明玻璃\n")
        f.write("- 药水：瓶内同形缩小液面，液面高度 z = 1.00，亮红药水\n")
        f.write("- 瓶塞：8 边锥形木塞 + 加宽顶盖\n")
        f.write("- 标签：贴合瓶肚的弧形羊皮纸标签（面向相机）\n")
        f.write("- 蜡封：标签上的红色圆形蜡封\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n" % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 材质\n\n")
        f.write("- Bottle_Glass：半透明青绿玻璃（alpha 0.38，roughness 0.08，不投阴影）\n")
        f.write("- Potion_Liquid：亮红药水（roughness 0.15）\n")
        f.write("- Cork_Wood：木色软木塞（roughness 0.85）\n")
        f.write("- Label_Parchment：羊皮纸标签（roughness 0.9）\n")
        f.write("- Wax_Seal：深红蜡封（roughness 0.5）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
