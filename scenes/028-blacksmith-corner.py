# -*- coding: utf-8 -*-
"""028 低模场景：铁匠铺角落（Blacksmith Corner）
Low-poly blacksmith shop corner scene: stone corner walls + wooden beam,
anvil (023 design, rotated), battle axe (025 design, leaning on the
barrel), staved wooden barrel with iron hoops, brazier with glowing
coals + warm point light, quench bucket, hammer, iron ingots, coal
lumps and stone floor pavers. Flat shading, clean topology.
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 028-blacksmith-corner.py
"""
import os
import sys
import math
import random
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


def box(name, center, size, mat, rot=(0.0, 0.0, 0.0)):
    """Box from center + (sx, sy, sz), optional rotation.
    Geometry is built in local space so rotation pivots on the center."""
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
    if rot != (0.0, 0.0, 0.0):
        obj.rotation_euler = rot
    return obj


def tapered_box(name, center, bottom_size, top_size, height, mat):
    """Box frustum: bottom rect (bx, by) at z-h/2, top rect (tx, ty)
    at z+h/2. Outward winding, no N-gons (caps are quads)."""
    cx, cy, cz = center
    bx, by = bottom_size[0] / 2.0, bottom_size[1] / 2.0
    tx, ty = top_size[0] / 2.0, top_size[1] / 2.0
    hz = height / 2.0
    verts = [
        (cx - bx, cy - by, cz - hz), (cx + bx, cy - by, cz - hz),
        (cx + bx, cy + by, cz - hz), (cx - bx, cy + by, cz - hz),
        (cx - tx, cy - ty, cz + hz), (cx + tx, cy - ty, cz + hz),
        (cx + tx, cy + ty, cz + hz), (cx - tx, cy + ty, cz + hz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return mesh_from_data(name, verts, faces, mat)


def tapered_cylinder(name, center, r_bottom, r_top, height, sides, mat):
    """Vertical (Z-axis) cylinder with different bottom/top radius.
    Caps are triangle fans from a center vertex (no N-gons)."""
    cx, cy, cz = center
    verts = []
    for z, r in ((cz - height / 2.0, r_bottom),
                 (cz + height / 2.0, r_top)):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append((cx + r * math.cos(a),
                          cy + r * math.sin(a), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    verts.append((cx, cy, cz - height / 2.0))
    verts.append((cx, cy, cz + height / 2.0))
    c_bot, c_top = 2 * sides, 2 * sides + 1
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_bot, j, i))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c_top, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def extruded_profile(name, profile, thickness, mat):
    """Extrude a 2D (x, z) profile along Y by `thickness`, centered on y=0.
    Profile must be CCW in the (x, z) plane. Front/back faces are
    triangulated from the profile centroid, so no N-gons."""
    t = thickness / 2.0
    n = len(profile)
    cx = sum(p[0] for p in profile) / n
    cz = sum(p[1] for p in profile) / n
    verts = []
    for (x, z) in profile:
        verts.append((x, -t, z))
    for (x, z) in profile:
        verts.append((x, t, z))
    c_back = 2 * n
    c_front = 2 * n + 1
    verts.append((cx, -t, cz))
    verts.append((cx, t, cz))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((c_back, i, j))
        faces.append((c_front, n + j, n + i))
        faces.append((i, n + i, n + j, j))
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


def check_winding(obj):
    """Count faces whose normal points inward."""
    import bmesh
    from mathutils import Vector
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    center = Vector((0, 0, 0))
    for v in bm.verts:
        center += mw @ v.co
    center /= len(bm.verts)
    flipped = 0
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        if n.dot((c - center).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def make_empty(name, location, rotation=(0.0, 0.0, 0.0)):
    empty = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(empty)
    empty.location = location
    empty.rotation_euler = rotation
    return empty


def main():
    clear_scene()
    make_world_gradient()
    add_ground(size=16.0, color=(0.28, 0.28, 0.30))
    key, fill, rim = studio_lights(target=(0.3, 0.3, 0.8))
    key.data.energy = 650.0
    fill.data.energy = 220.0
    rim.data.energy = 380.0

    # --- materials ---
    stone_wall = solid_material("Corner_StoneWall", (0.30, 0.28, 0.26),
                                metallic=0.0, roughness=0.95)
    stone_dark = solid_material("Corner_StoneDark", (0.20, 0.19, 0.19),
                                metallic=0.0, roughness=0.95)
    beam_wood = solid_material("Corner_Beam", (0.32, 0.20, 0.10),
                               metallic=0.0, roughness=0.9)
    steel = solid_material("Anvil_Steel", (0.32, 0.33, 0.37),
                           metallic=0.85, roughness=0.35)
    top_steel = solid_material("Anvil_TopSteel", (0.62, 0.64, 0.68),
                               metallic=0.9, roughness=0.18)
    iron = solid_material("Anvil_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    dark = solid_material("Anvil_Dark", (0.05, 0.05, 0.06),
                          metallic=0.3, roughness=0.8)
    edge_steel = solid_material("Axe_EdgeSteel", (0.62, 0.64, 0.68),
                                metallic=0.9, roughness=0.15)
    axe_wood = solid_material("Axe_Wood", (0.45, 0.28, 0.14),
                              metallic=0.0, roughness=0.8)
    axe_wood_dark = solid_material("Axe_WoodDark", (0.30, 0.18, 0.09),
                                   metallic=0.0, roughness=0.85)
    leather = solid_material("Axe_Leather", (0.20, 0.12, 0.08),
                             metallic=0.0, roughness=0.9)
    barrel_wood = solid_material("Barrel_Wood", (0.42, 0.27, 0.13),
                                 metallic=0.0, roughness=0.85)
    barrel_wood_light = solid_material("Barrel_WoodLight",
                                       (0.60, 0.42, 0.22),
                                       metallic=0.0, roughness=0.85)
    hoop_iron = solid_material("Barrel_Hoop", (0.12, 0.12, 0.13),
                               metallic=0.8, roughness=0.45)
    water = solid_material("Bucket_Water", (0.10, 0.22, 0.32),
                           metallic=0.1, roughness=0.1)
    coal_mat = solid_material("Coal", (0.04, 0.04, 0.05),
                              metallic=0.0, roughness=0.9)
    ember_mat = bpy.data.materials.new("Ember")
    ember_mat.use_nodes = True
    ember_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Color"].default_value = (1.0, 0.30, 0.05, 1.0)
    ember_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Strength"].default_value = 3.0
    ember_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"].default_value = (0.25, 0.05, 0.01, 1.0)

    parts = []

    # --- corner walls: back wall (y=+2.2) + left wall (x=-2.2) ---
    parts.append(box("Wall_Back", (0.0, 2.2, 1.30),
                     (5.4, 0.30, 2.60), stone_wall))
    parts.append(box("Wall_Left", (-2.2, 0.0, 1.30),
                     (0.30, 4.6, 2.60), stone_wall))
    # darker stone base course along both walls
    parts.append(box("WallBase_Back", (0.0, 2.16, 0.20),
                     (5.4, 0.36, 0.40), stone_dark))
    parts.append(box("WallBase_Left", (-2.16, 0.0, 0.20),
                     (0.36, 4.6, 0.40), stone_dark))
    # wooden beam across the corner top + corner post
    parts.append(box("Beam_Back", (0.0, 2.05, 2.45),
                     (5.4, 0.28, 0.22), beam_wood))
    parts.append(box("Beam_Left", (-2.05, 0.0, 2.45),
                     (0.28, 4.6, 0.22), beam_wood))
    parts.append(box("Post_Corner", (-2.05, 2.05, 1.30),
                     (0.28, 0.28, 2.60), beam_wood))

    # --- stone floor pavers around the work area ---
    random.seed(28)
    paver_grays = [(0.30, 0.30, 0.32), (0.36, 0.36, 0.38),
                   (0.26, 0.26, 0.28), (0.40, 0.39, 0.38)]
    for i, (px, py) in enumerate(((-0.9, -0.6), (0.0, -0.6), (0.9, -0.6),
                                  (-0.9, 0.3), (0.0, 0.3), (0.9, 0.3),
                                  (-0.9, 1.2), (0.0, 1.2), (0.9, 1.2),
                                  (1.8, 0.3), (1.8, 1.2), (-1.8, 0.3))):
        g = paver_grays[i % len(paver_grays)]
        paver_mat = solid_material("Paver_%d" % i, g,
                                   metallic=0.0, roughness=0.95)
        parts.append(box("Paver_%02d" % i, (px, py, 0.02),
                         (0.86, 0.86, 0.04), paver_mat,
                         rot=(0.0, 0.0, random.uniform(-0.03, 0.03))))

    # --- anvil (023 design), grouped under an empty, rotated -20 deg ---
    anvil_group = make_empty("AnvilGroup", (-0.45, 0.35, 0.0),
                             rotation=(0.0, 0.0, math.radians(-20.0)))
    anvil_parts = []
    anvil_parts.append(box("Anvil_Base", (0, 0, 0.09),
                           (1.50, 0.80, 0.18), iron))
    anvil_parts.append(box("Anvil_Pedestal", (0, 0, 0.25),
                           (1.00, 0.55, 0.14), iron))
    anvil_parts.append(tapered_box("Anvil_Waist", (0, 0, 0.47),
                                   (0.60, 0.42), (0.45, 0.34), 0.30, steel))
    anvil_parts.append(box("Anvil_Body", (0, 0, 0.80),
                           (1.05, 0.42, 0.36), steel))
    anvil_parts.append(box("Anvil_TopPlate", (0, 0, 1.02),
                           (1.30, 0.50, 0.08), top_steel))
    horn = tapered_cylinder("Anvil_Horn", (0, 0, 0),
                            0.21, 0.02, 0.60, 8, steel)
    horn.rotation_euler = (0.0, math.pi / 2.0, 0.0)
    horn.location = (0.85, 0, 0.86)
    anvil_parts.append(horn)
    anvil_parts.append(box("Anvil_Heel", (-0.62, 0, 0.86),
                           (0.22, 0.46, 0.30), steel))
    anvil_parts.append(box("Anvil_HardyHole", (-0.45, 0, 1.065),
                           (0.09, 0.09, 0.02), dark))
    anvil_parts.append(tapered_cylinder("Anvil_PritchelHole",
                                        (0.35, 0, 1.065),
                                        0.035, 0.035, 0.02, 8, dark))
    for o in anvil_parts:
        o.parent = anvil_group
    parts.extend(anvil_parts)

    # --- wooden barrel (staved, 12 sides, bulged) at (2.0, -0.2) ---
    bx, by = 2.0, -0.2
    parts.append(tapered_cylinder("Barrel_Bottom", (bx, by, 0.175),
                                  0.44, 0.52, 0.35, 12, barrel_wood))
    parts.append(tapered_cylinder("Barrel_Middle", (bx, by, 0.45),
                                  0.52, 0.52, 0.20, 12, barrel_wood))
    parts.append(tapered_cylinder("Barrel_Top", (bx, by, 0.725),
                                  0.52, 0.44, 0.35, 12, barrel_wood))
    parts.append(tapered_cylinder("Barrel_Lid", (bx, by, 0.885),
                                  0.40, 0.40, 0.03, 12, barrel_wood_light))
    for hz, hr in ((0.12, 0.49), (0.45, 0.535), (0.78, 0.49)):
        parts.append(tapered_cylinder("Barrel_Hoop_%d" % int(hz * 100),
                                      (bx, by, hz), hr, hr, 0.05, 12,
                                      hoop_iron))

    # --- battle axe (025 design), leaning on the barrel rim ---
    # built in a local frame (haft base at origin), grouped under an
    # empty tilted 15 deg about Y; base at (1.18, -0.2, 0) so the shaft
    # crosses the barrel rim (x=1.45) at z~0.9.
    axe_group = make_empty("AxeGroup", (1.18, -0.2, 0.0),
                           rotation=(0.0, math.radians(-15.0), 0.0))
    axe_parts = []
    axe_parts.append(tapered_cylinder("Axe_Haft", (0, 0, 0.775),
                                      0.045, 0.035, 1.55, 8, axe_wood))
    axe_parts.append(tapered_cylinder("Axe_Grip", (0, 0, 0.16),
                                      0.052, 0.050, 0.28, 8, leather))
    axe_parts.append(tapered_cylinder("Axe_Pommel", (0, 0, 0.03),
                                      0.050, 0.045, 0.06, 8, iron))
    axe_parts.append(box("Axe_Socket", (0.02, 0, 1.24),
                         (0.22, 0.13, 0.30), steel))
    blade_profile = [
        (0.00, 1.02), (0.40, 0.88), (0.52, 1.02),
        (0.52, 1.42), (0.40, 1.56), (0.00, 1.44),
    ]
    axe_parts.append(extruded_profile("Axe_Blade", blade_profile, 0.08,
                                      steel))
    axe_parts.append(box("Axe_CuttingEdge", (0.53, 0, 1.22),
                         (0.06, 0.10, 0.42), edge_steel))
    axe_parts.append(box("Axe_TopWedge", (0, 0, 1.585),
                         (0.09, 0.09, 0.07), axe_wood_dark))
    for o in axe_parts:
        o.parent = axe_group
    parts.extend(axe_parts)

    # --- brazier on the left side (visible from the camera):
    #     stone pedestal + iron bowl + glowing coals, with a warm
    #     point light above it ---
    parts.append(box("Brazier_Pedestal", (-1.75, 0.10, 0.25),
                     (0.45, 0.45, 0.50), stone_dark))
    parts.append(tapered_cylinder("Brazier_Bowl", (-1.75, 0.10, 0.62),
                                  0.16, 0.34, 0.26, 8, iron))
    for i, (ex, ey) in enumerate(((-1.82, 0.05), (-1.68, 0.13),
                                  (-1.75, 0.17))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.09,
                                              location=(ex, ey, 0.78))
        ember = bpy.context.active_object
        ember.name = "Ember_%d" % i
        ember.data.materials.append(ember_mat)
        flat_shade(ember)
        parts.append(ember)
    forge_light = bpy.data.lights.new("ForgeGlow", 'POINT')
    forge_light.energy = 250.0
    forge_light.color = (1.0, 0.55, 0.20)
    forge_light.shadow_soft_size = 0.3
    forge_obj = bpy.data.objects.new("ForgeGlow", forge_light)
    bpy.context.scene.collection.objects.link(forge_obj)
    forge_obj.location = (-1.75, 0.10, 1.15)

    # --- quench bucket in front of the anvil's left side ---
    parts.append(tapered_cylinder("Bucket", (-1.50, -0.70, 0.175),
                                  0.28, 0.24, 0.35, 10, barrel_wood))
    parts.append(tapered_cylinder("Bucket_Water", (-1.50, -0.70, 0.30),
                                  0.235, 0.235, 0.02, 10, water))
    parts.append(tapered_cylinder("Bucket_Hoop", (-1.50, -0.70, 0.10),
                                  0.285, 0.285, 0.04, 10, hoop_iron))

    # --- hammer lying on the floor near the anvil ---
    hammer_group = make_empty("HammerGroup", (0.55, -0.95, 0.0),
                              rotation=(0.0, 0.0, math.radians(35.0)))
    handle = tapered_cylinder("Hammer_Handle", (0, 0, 0.035),
                              0.028, 0.022, 0.50, 8, axe_wood)
    handle.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    hammer_parts = [handle]
    hammer_parts.append(box("Hammer_Head", (0, 0.28, 0.035),
                            (0.07, 0.18, 0.07), iron))
    for o in hammer_parts:
        o.parent = hammer_group
    parts.extend(hammer_parts)

    # --- iron ingots stacked in front of the anvil + coal lumps by
    #     the brazier ---
    for i, (ix, iy, iz) in enumerate(((0.65, -0.45, 0.035),
                                      (0.93, -0.45, 0.035),
                                      (0.79, -0.45, 0.105))):
        parts.append(box("Ingot_%d" % i, (ix, iy, iz),
                         (0.26, 0.12, 0.07), iron,
                         rot=(0.0, 0.0, math.radians(8.0 if i == 2 else 0.0))))
    random.seed(5)
    for i, (cx, cy) in enumerate(((-1.50, 0.55), (-1.60, -0.25),
                                  (-1.35, -0.35))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.09,
                                              location=(cx, cy, 0.06))
        lump = bpy.context.active_object
        lump.name = "Coal_%d" % i
        lump.data.materials.append(coal_mat)
        lump.scale = (1.0, random.uniform(0.7, 0.9), 0.62)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        flat_shade(lump)
        parts.append(lump)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    print("CORNER_WINDING:", flipped)

    cam = make_camera("Camera", (4.0, -4.6, 2.6), (0.1, 0.4, 0.75),
                      lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "028-blacksmith-corner.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "028-blacksmith-corner.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "blacksmith_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("CORNER_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("CORNER_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "028-blacksmith-corner.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 028 低模场景：铁匠铺角落\n\n")
        f.write("低多边形环境场景资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 角落墙体：后墙（y=+2.2，5.4×2.6）+ 左墙（x=-2.2，4.6×2.6），"
                "石材；深色石基座沿墙脚，木梁压顶 + 角柱\n")
        f.write("- 地面：12 块石板铺地（0.86×0.86，灰度交错，微旋转）\n")
        f.write("- 铁砧：复用 023 设计（底座/台阶/腰身/砧身/抛光砧面/砧角/"
                "砧尾 + 方孔/圆孔），整体绕 Z 转 -20°，位于 (-0.45, 0.35)\n")
        f.write("- 木桶：12 边鼓形桶身（三段渐变筒：底 0.44→0.52→顶 0.44），"
                "高 0.90，浅色桶盖 + 3 道铁箍，位于 (2.0, -0.2)\n")
        f.write("- 战斧：复用 025 设计（斧柄/皮革握把/斧底帽/斧头座/扇形斧刃/"
                "亮钢刃口/顶楔），整体绕 Y 倾 15° 斜靠在桶沿上，斧柄底端位于 "
                "(1.18, -0.2)，斧身在 z≈0.9 处搭在桶沿\n")
        f.write("- 火盆：石墩 + 铁碗 + 3 块发光炭块（Emission 橙光），"
                "位于左墙边 (-1.75, 0.10)，"
                "上方暖色点光源（250W，橙色）模拟炉火辉光\n")
        f.write("- 淬火桶：10 边小木桶 + 水面（深蓝低粗糙度）+ 铁箍，"
                "位于铁砧左前方 (-1.50, -0.70)\n")
        f.write("- 铁锤：平放在地面，木柄 + 铁头，位于 (0.55, -0.95)，"
                "转 35°\n")
        f.write("- 铁锭 3 块（叠放，铁砧前方）+ 煤块 3 块（火盆边）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Corner_StoneWall：墙体石材（roughness 0.95）\n")
        f.write("- Anvil_Steel / Anvil_TopSteel：砧身 / 抛光砧面\n")
        f.write("- Barrel_Wood：桶身；Barrel_Hoop：铁箍\n")
        f.write("- Ember：发光炭块（Emission 橙，强度 3.0）+ ForgeGlow 点光源\n")
        f.write("- Bucket_Water：淬火水面（roughness 0.1）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光 + 炉火暖光，"
                "40mm 镜头\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
