# -*- coding: utf-8 -*-
"""047 低模场景：炼金实验室角落（Alchemy Lab Corner）
Low-poly alchemy laboratory interior: stone corner walls, stone tile
floor, heavy wooden workbench (mortar & pestle, test tube rack, alembic
flask, open spellbook, candle cluster), wall-mounted potion shelf with
colourful potion bottles, large iron cauldron on a hearth slab (green
bubbling liquid + fire glow), barrel + crate, hanging herb bundles,
wall shelf with jars, framed alchemy chart, candle sconce with warm
point light, stool + rug.
Flat shading, clean topology. Eevee beauty + wireframe renders, .blend
+ note. Camera auto-fitted with fit_camera_to_objects (target 0.78).
Run: blender --background --python 047-alchemy-lab-corner.py
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
                    add_ground, studio_lights, flat_shade, poly_count,
                    total_poly_count, setup_render, render,
                    fit_camera_to_objects, export_wireframe_segments)


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
    """Box from center + (sx, sy, sz), optional rotation."""
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


def tapered_cylinder(name, center, r_bottom, r_top, height, sides, mat):
    """Vertical (Z-axis) cylinder, triangle-fan caps (no N-gons).
    NOTE (040 lesson): verts are baked in WORLD coords, so a
    rotation_euler set afterwards rotates about the WORLD ORIGIN.
    To rotate one, build it at (0,0,0), set the rotation, then set
    .location."""
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


def candle(name, center, height, radius, wax_mat, flame_mat, parts,
           flame=True):
    """A standing candle + optional emissive flame (icosphere)."""
    cx, cy, cz = center
    parts.append(tapered_cylinder(name, (cx, cy, cz + height / 2.0),
                                  radius, radius * 0.9, height, 8, wax_mat))
    if flame:
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=radius * 0.8,
            location=(cx, cy, cz + height + radius * 0.9))
        fl = bpy.context.active_object
        fl.name = name + "_Flame"
        fl.data.materials.append(flame_mat)
        fl.scale = (1.0, 1.0, 1.7)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        flat_shade(fl)
        parts.append(fl)


def glass_material(name, color, alpha=0.35):
    """Semi-transparent glass: Principled BSDF with alpha, blended render
    (005 convention — opaque glass hides the coloured liquid inside)."""
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


def glow_material(name, color, strength=1.2):
    """Principled material with matching emission (glowing liquid)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat


def potion_bottle(name, center, height, radius, liquid_mat, glass_mat,
                  cork_mat, parts):
    """Small potion bottle: glass body + neck + cork + glowing liquid."""
    cx, cy, cz = center
    body_h = height * 0.62
    parts.append(tapered_cylinder(name + "_Body",
                                  (cx, cy, cz + body_h / 2.0),
                                  radius, radius * 0.85, body_h, 8,
                                  glass_mat))
    parts.append(tapered_cylinder(name + "_Liquid",
                                  (cx, cy, cz + body_h * 0.42),
                                  radius * 0.78, radius * 0.68,
                                  body_h * 0.7, 8, liquid_mat))
    parts.append(tapered_cylinder(name + "_Neck",
                                  (cx, cy, cz + body_h + height * 0.10),
                                  radius * 0.42, radius * 0.38,
                                  height * 0.22, 8, glass_mat))
    parts.append(tapered_cylinder(name + "_Cork",
                                  (cx, cy, cz + body_h + height * 0.22),
                                  radius * 0.40, radius * 0.44,
                                  height * 0.10, 8, cork_mat))


def book_row(parts, prefix, x0, x1, z_base, y_center, depth, palette,
             max_h=0.42):
    """A row of upright books on a shelf (size along X = width).
    Occasional leaning book (12%) and gap (10%)."""
    x = x0
    n = 0
    while x < x1 - 0.06:
        w = random.uniform(0.06, 0.11)
        h = random.uniform(0.28, max_h)
        if x + w > x1:
            break
        mat = random.choice(palette)
        tilt = 0.0
        if random.random() < 0.12:
            tilt = random.choice((-1, 1)) * math.radians(12)
        lift = (h / 2.0) * (1.0 - math.cos(tilt)) \
            + (w / 2.0) * abs(math.sin(tilt))
        parts.append(box("%s_%d" % (prefix, n),
                         (x + w / 2.0, y_center, z_base + h / 2.0 + lift),
                         (w, depth, h), mat, rot=(0.0, tilt, 0.0)))
        n += 1
        x += w + random.uniform(0.0, 0.015)
        if random.random() < 0.10:
            x += random.uniform(0.08, 0.18)
    return n


def main():
    clear_scene()
    make_world_gradient()
    add_ground(size=16.0, color=(0.30, 0.28, 0.26))
    key, fill, rim = studio_lights(target=(0.3, 0.3, 0.9))
    key.data.energy = 650.0
    fill.data.energy = 220.0
    rim.data.energy = 380.0

    # --- materials ---
    stone = solid_material("Alc_Stone", (0.45, 0.43, 0.40),
                           metallic=0.0, roughness=0.95)
    stone_dark = solid_material("Alc_StoneDark", (0.30, 0.28, 0.26),
                                metallic=0.0, roughness=0.95)
    beam_wood = solid_material("Alc_Beam", (0.28, 0.18, 0.09),
                               metallic=0.0, roughness=0.9)
    bench_wood = solid_material("Alc_Bench", (0.42, 0.28, 0.13),
                                metallic=0.0, roughness=0.85)
    bench_top = solid_material("Alc_BenchTop", (0.55, 0.37, 0.18),
                               metallic=0.0, roughness=0.75)
    shelf_wood = solid_material("Alc_Shelf", (0.38, 0.24, 0.11),
                                metallic=0.0, roughness=0.85)
    iron = solid_material("Alc_Iron", (0.15, 0.15, 0.17),
                          metallic=0.7, roughness=0.5)
    brass = solid_material("Alc_Brass", (0.75, 0.58, 0.20),
                           metallic=0.9, roughness=0.3)
    copper = solid_material("Alc_Copper", (0.65, 0.35, 0.18),
                            metallic=0.9, roughness=0.35)
    glass = glass_material("Alc_Glass", (0.45, 0.75, 0.72), alpha=0.38)
    cork = solid_material("Alc_Cork", (0.62, 0.45, 0.25),
                          metallic=0.0, roughness=1.0)
    paper = solid_material("Alc_Paper", (0.92, 0.88, 0.74),
                           metallic=0.0, roughness=0.9)
    parchment = solid_material("Alc_Parchment", (0.88, 0.80, 0.60),
                               metallic=0.0, roughness=0.9)
    wax = solid_material("Alc_Wax", (0.94, 0.88, 0.74),
                         metallic=0.0, roughness=0.7)
    herb_green = solid_material("Alc_Herb", (0.22, 0.42, 0.16),
                                metallic=0.0, roughness=1.0)
    herb_dry = solid_material("Alc_HerbDry", (0.55, 0.50, 0.25),
                              metallic=0.0, roughness=1.0)
    rug_red = solid_material("Alc_Rug", (0.40, 0.11, 0.13),
                             metallic=0.0, roughness=1.0)
    rug_trim = solid_material("Alc_RugTrim", (0.72, 0.58, 0.28),
                              metallic=0.0, roughness=1.0)
    chart_blue = solid_material("Alc_Chart", (0.08, 0.12, 0.30),
                                metallic=0.0, roughness=0.9)
    gold = solid_material("Alc_Gold", (0.85, 0.68, 0.25),
                          metallic=0.9, roughness=0.25)
    book_red = solid_material("Book_Red", (0.45, 0.10, 0.12),
                              metallic=0.0, roughness=0.8)
    book_green = solid_material("Book_Green", (0.10, 0.35, 0.15),
                                metallic=0.0, roughness=0.8)
    book_blue = solid_material("Book_Blue", (0.12, 0.20, 0.45),
                               metallic=0.0, roughness=0.8)
    book_purple = solid_material("Book_Purple", (0.35, 0.15, 0.45),
                                 metallic=0.0, roughness=0.8)
    book_brown = solid_material("Book_Brown", (0.45, 0.28, 0.12),
                                metallic=0.0, roughness=0.8)
    book_teal = solid_material("Book_Teal", (0.10, 0.35, 0.35),
                               metallic=0.0, roughness=0.8)
    palette = [book_red, book_green, book_blue, book_purple,
               book_brown, book_teal]
    liquid_green = glow_material("Liq_Green", (0.15, 0.70, 0.20), 1.2)
    liquid_purple = glow_material("Liq_Purple", (0.50, 0.20, 0.60), 1.0)
    liquid_red = glow_material("Liq_Red", (0.70, 0.15, 0.15), 1.0)
    liquid_blue = glow_material("Liq_Blue", (0.15, 0.30, 0.70), 1.0)
    liquid_amber = glow_material("Liq_Amber", (0.85, 0.55, 0.10), 1.0)
    liquids = [liquid_green, liquid_purple, liquid_red, liquid_blue,
               liquid_amber]
    flame_mat = bpy.data.materials.new("Alc_Flame")
    flame_mat.use_nodes = True
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Color"].default_value = (1.0, 0.55, 0.10, 1.0)
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Strength"].default_value = 4.0
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"].default_value = (1.0, 0.60, 0.10, 1.0)

    parts = []

    # --- corner walls: back (y=+2.2) + left (x=-2.2), stone upper,
    #     darker stone base, beam across the top + corner post ---
    parts.append(box("Wall_Back", (0.0, 2.2, 1.30),
                     (5.4, 0.30, 2.60), stone))
    parts.append(box("Wall_Left", (-2.2, 0.0, 1.30),
                     (0.30, 4.6, 2.60), stone))
    parts.append(box("StoneBase_Back", (0.0, 2.16, 0.40),
                     (5.4, 0.36, 0.80), stone_dark))
    parts.append(box("StoneBase_Left", (-2.16, 0.0, 0.40),
                     (0.36, 4.6, 0.80), stone_dark))
    parts.append(box("StoneRail_Back", (0.0, 2.12, 0.82),
                     (5.4, 0.42, 0.06), beam_wood))
    parts.append(box("StoneRail_Left", (-2.12, 0.0, 0.82),
                     (0.42, 4.6, 0.06), beam_wood))
    parts.append(box("Beam_Back", (0.0, 2.05, 2.45),
                     (5.4, 0.28, 0.22), beam_wood))
    parts.append(box("Beam_Left", (-2.05, 0.0, 2.45),
                     (0.28, 4.6, 0.22), beam_wood))
    parts.append(box("Post_Corner", (-2.05, 2.05, 1.30),
                     (0.28, 0.28, 2.60), beam_wood))

    # --- stone tile floor: 6 x 5 slabs, alternating shades ---
    random.seed(47)
    tile_shades = [(0.38, 0.36, 0.34), (0.46, 0.44, 0.42),
                   (0.33, 0.31, 0.30), (0.50, 0.48, 0.45)]
    for i in range(6):
        for j in range(5):
            px = -2.2 + 0.45 + i * 0.9
            py = -1.8 + 0.45 + j * 0.9
            tm = solid_material("Tile_%d_%d" % (i, j),
                                tile_shades[(i + j) % 4],
                                metallic=0.0, roughness=0.95)
            parts.append(box("Tile_%d_%d" % (i, j), (px, py, 0.015),
                             (0.86, 0.86, 0.03), tm))

    # --- heavy workbench against the back wall (center 0.3, 1.6) ---
    parts.append(box("Bench_Top", (0.3, 1.6, 0.85),
                     (2.6, 0.95, 0.08), bench_top))
    for dx, dy in ((-1.20, -0.38), (1.20, -0.38),
                   (-1.20, 0.38), (1.20, 0.38)):
        parts.append(box("BenchLeg_%d_%d" % (int(dx * 100), int(dy * 100)),
                         (0.3 + dx, 1.6 + dy, 0.405),
                         (0.12, 0.12, 0.81), bench_wood))
    parts.append(box("Bench_LowShelf", (0.3, 1.6, 0.25),
                     (2.4, 0.80, 0.05), shelf_wood))
    parts.append(box("Bench_Drawer", (0.3, 1.14, 0.62),
                     (1.10, 0.04, 0.24), stone_dark))
    for i, kx in enumerate((-0.15, 0.75)):
        knob = tapered_cylinder("BenchKnob_%d" % i, (0, 0, 0),
                                0.02, 0.02, 0.03, 8, brass)
        knob.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        knob.location = (kx, 1.115, 0.62)
        parts.append(knob)
    # crates + jars on the low shelf
    parts.append(box("BenchCrate_0", (-0.55, 1.6, 0.40),
                     (0.42, 0.55, 0.25), shelf_wood,
                     rot=(0.0, 0.0, math.radians(6.0))))
    parts.append(box("BenchCrate_1", (1.05, 1.6, 0.375),
                     (0.36, 0.50, 0.20), bench_wood,
                     rot=(0.0, 0.0, math.radians(-8.0))))
    potion_bottle("BenchJar_0", (-0.05, 1.62, 0.275), 0.22, 0.07,
                  liquid_blue, glass, cork, parts)
    potion_bottle("BenchJar_1", (0.35, 1.58, 0.275), 0.18, 0.06,
                  liquid_red, glass, cork, parts)

    # --- on the workbench: mortar & pestle, test tube rack, alembic,
    #     open spellbook, candle cluster, scattered herbs ---
    # mortar (bowl) + pestle
    parts.append(tapered_cylinder("Mortar", (0.3 + -0.95, 1.62, 0.96),
                                  0.07, 0.10, 0.10, 10, stone_dark))
    pestle = tapered_cylinder("Pestle", (0, 0, 0),
                              0.018, 0.028, 0.22, 8, bench_wood)
    pestle.rotation_euler = (math.radians(35.0), 0.0,
                             math.radians(25.0))
    pestle.location = (-0.62, 1.62, 1.03)
    parts.append(pestle)
    # test tube rack: 2 posts + top bar, 3 tubes with coloured liquid
    parts.append(box("Rack_PostL", (0.05, 1.75, 1.00),
                     (0.04, 0.04, 0.22), brass))
    parts.append(box("Rack_PostR", (0.45, 1.75, 1.00),
                     (0.04, 0.04, 0.22), brass))
    parts.append(box("Rack_Bar", (0.25, 1.75, 1.10),
                     (0.44, 0.06, 0.03), brass))
    for i, lm in enumerate((liquid_green, liquid_purple, liquid_amber)):
        tx = 0.12 + i * 0.13
        parts.append(tapered_cylinder("Tube_%d" % i,
                                      (tx, 1.75, 1.00),
                                      0.028, 0.028, 0.20, 8, glass))
        parts.append(tapered_cylinder("TubeLiq_%d" % i,
                                      (tx, 1.75, 0.96),
                                      0.022, 0.022, 0.11, 8, lm))
    # alembic flask: round-bottom glass flask + copper neck + tube
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.11,
                                          location=(0.95, 1.45, 0.99))
    flask = bpy.context.active_object
    flask.name = "Alembic_Flask"
    flask.data.materials.append(glass)
    flat_shade(flask)
    parts.append(flask)
    parts.append(tapered_cylinder("Alembic_Liquid",
                                  (0.95, 1.45, 0.95),
                                  0.085, 0.085, 0.05, 10, liquid_blue))
    parts.append(tapered_cylinder("Alembic_Neck",
                                  (0.95, 1.45, 1.13),
                                  0.035, 0.028, 0.12, 8, copper))
    arm = tapered_cylinder("Alembic_Arm", (0, 0, 0),
                           0.02, 0.02, 0.22, 8, copper)
    arm.rotation_euler = (0.0, math.radians(55.0), 0.0)
    arm.location = (1.10, 1.45, 1.16)
    parts.append(arm)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.06,
                                          location=(1.28, 1.45, 1.02))
    receiver = bpy.context.active_object
    receiver.name = "Alembic_Receiver"
    receiver.data.materials.append(glass)
    flat_shade(receiver)
    parts.append(receiver)
    parts.append(tapered_cylinder("Receiver_Liq",
                                  (1.28, 1.45, 0.99),
                                  0.045, 0.045, 0.03, 8, liquid_amber))
    # open spellbook on the bench
    parts.append(box("Spellbook_Cover", (-0.05, 1.45, 0.905),
                     (0.56, 0.42, 0.02), book_purple))
    parts.append(box("Spellbook_Left", (-0.18, 1.45, 0.92),
                     (0.26, 0.38, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(8.0))))
    parts.append(box("Spellbook_Right", (0.08, 1.45, 0.92),
                     (0.26, 0.38, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(-8.0))))
    # candle cluster on the bench (left end)
    parts.append(tapered_cylinder("BenchCand_Base", (-1.05, 1.75, 0.905),
                                  0.09, 0.06, 0.03, 10, brass))
    parts.append(tapered_cylinder("BenchCand_Stem", (-1.05, 1.75, 1.02),
                                  0.02, 0.02, 0.20, 8, brass))
    candle("BenchCandle", (-1.05, 1.75, 1.12), 0.12, 0.025,
           wax, flame_mat, parts)
    # scattered dried herbs on the bench
    for i, hx in enumerate((-0.55, -0.45, -0.35)):
        herb = box("BenchHerb_%d" % i, (hx, 1.35, 0.90),
                   (0.02, 0.16, 0.012), herb_dry,
                   rot=(math.radians(-8.0), 0.0, math.radians(i * 18.0)))
        parts.append(herb)
    # rolled scroll on the bench
    scroll = tapered_cylinder("BenchScroll", (0, 0, 0),
                              0.045, 0.045, 0.45, 10, parchment)
    scroll.rotation_euler = (0.0, math.radians(90.0), 0.0)
    scroll.location = (0.55, 1.85, 0.935)
    parts.append(scroll)

    # --- potion shelf on the back wall above the bench: 2 tiers ---
    parts.append(box("PotionShelf_EndL", (-0.95, 1.98, 1.50),
                     (0.05, 0.36, 0.55), shelf_wood))
    parts.append(box("PotionShelf_EndR", (1.55, 1.98, 1.50),
                     (0.05, 0.36, 0.55), shelf_wood))
    parts.append(box("PotionShelf_Top", (0.30, 1.98, 1.755),
                     (2.55, 0.36, 0.05), shelf_wood))
    parts.append(box("PotionShelf_Board", (0.30, 1.98, 1.42),
                     (2.50, 0.34, 0.05), shelf_wood))
    parts.append(box("PotionShelf_Back", (0.30, 2.14, 1.50),
                     (2.55, 0.04, 0.55), stone_dark))
    # bottles on both tiers (deterministic random)
    random.seed(47)
    n_bottles = 0
    for tier, zb in enumerate((1.445, 1.78)):
        x = -0.88
        k = 0
        while x < 1.48:
            w = random.uniform(0.11, 0.17)
            h = random.uniform(0.20, 0.30)
            r = random.uniform(0.05, 0.07)
            if x + w > 1.48:
                break
            lm = random.choice(liquids)
            potion_bottle("Potion_T%d_%d" % (tier, k),
                          (x + w / 2.0, 1.98, zb), h, r, lm, glass,
                          cork, parts)
            n_bottles += 1
            k += 1
            x += w + random.uniform(0.01, 0.05)
            if random.random() < 0.12:
                x += random.uniform(0.08, 0.15)
    # small book row on the top tier's right end
    n_books = book_row(parts, "ShelfBook", 1.05, 1.50, 1.78, 1.98, 0.28,
                       palette, max_h=0.30)

    # --- cauldron on a hearth slab (right side, floor) ---
    parts.append(box("Hearth_Slab", (1.70, 0.55, 0.03),
                     (1.30, 1.10, 0.06), stone_dark))
    parts.append(tapered_cylinder("Cauldron_Body", (1.70, 0.55, 0.42),
                                  0.30, 0.44, 0.55, 12, iron))
    parts.append(tapered_cylinder("Cauldron_Rim", (1.70, 0.55, 0.70),
                                  0.46, 0.46, 0.05, 12, iron))
    parts.append(tapered_cylinder("Cauldron_Liquid", (1.70, 0.55, 0.685),
                                  0.40, 0.40, 0.03, 12, liquid_green))
    # 3 bubbles on the liquid surface
    for i, (bx, by, br) in enumerate(((1.55, 0.45, 0.05),
                                      (1.85, 0.65, 0.07),
                                      (1.72, 0.38, 0.045))):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=br, location=(bx, by, 0.71))
        bub = bpy.context.active_object
        bub.name = "Bubble_%d" % i
        bub.data.materials.append(liquid_green)
        flat_shade(bub)
        parts.append(bub)
    # 3 legs, slightly splayed
    for i, a in enumerate((0.0, 2.094, 4.189)):
        lx = 1.70 + 0.26 * math.cos(a)
        ly = 0.55 + 0.26 * math.sin(a)
        leg = tapered_cylinder("CauldronLeg_%d" % i, (0, 0, 0),
                               0.03, 0.035, 0.20, 8, iron)
        leg.rotation_euler = (math.radians(12.0) * math.cos(a),
                              math.radians(12.0) * math.sin(a), 0.0)
        leg.location = (lx, ly, 0.13)
        parts.append(leg)
    # fire under the cauldron: 3 emissive cones + orange point light
    for i, (fx, fy) in enumerate(((1.58, 0.45), (1.82, 0.48),
                                  (1.70, 0.68))):
        parts.append(tapered_cylinder("Fire_%d" % i, (fx, fy, 0.10),
                                      0.09, 0.01, 0.14, 6, flame_mat))
    fire_light = bpy.data.lights.new("CauldronGlow", 'POINT')
    fire_light.energy = 220.0
    fire_light.color = (1.0, 0.55, 0.15)
    fire_light.shadow_soft_size = 0.3
    fire_obj = bpy.data.objects.new("CauldronGlow", fire_light)
    bpy.context.scene.collection.objects.link(fire_obj)
    fire_obj.location = (1.70, 0.55, 0.30)
    # ladle leaning on the cauldron rim
    ladle = tapered_cylinder("Ladle", (0, 0, 0),
                             0.018, 0.018, 0.55, 8, bench_wood)
    ladle.rotation_euler = (math.radians(28.0), 0.0, math.radians(-18.0))
    ladle.location = (1.95, 0.62, 0.85)
    parts.append(ladle)
    parts.append(tapered_cylinder("Ladle_Cup", (2.02, 0.68, 0.66),
                                  0.05, 0.065, 0.04, 10, copper))

    # --- barrel in the left corner + crate stack near the left wall ---
    parts.append(tapered_cylinder("Barrel", (-1.80, 1.70, 0.38),
                                  0.30, 0.34, 0.76, 12, bench_wood))
    parts.append(tapered_cylinder("Barrel_Top", (-1.80, 1.70, 0.76),
                                  0.30, 0.30, 0.03, 12, bench_top))
    parts.append(tapered_cylinder("Barrel_Band", (-1.80, 1.70, 0.62),
                                  0.345, 0.345, 0.04, 12, iron))
    parts.append(tapered_cylinder("Barrel_Band2", (-1.80, 1.70, 0.18),
                                  0.315, 0.315, 0.04, 12, iron))
    parts.append(box("Crate_0", (-1.85, 0.35, 0.22),
                     (0.45, 0.45, 0.44), shelf_wood,
                     rot=(0.0, 0.0, math.radians(8.0))))
    parts.append(box("Crate_1", (-1.82, 0.35, 0.63),
                     (0.38, 0.38, 0.36), bench_wood,
                     rot=(0.0, 0.0, math.radians(-6.0))))
    potion_bottle("CrateBottle", (-1.80, 0.55, 0.81), 0.20, 0.055,
                  liquid_purple, glass, cork, parts)

    # --- wall shelf on the left wall with jars (faces +x) ---
    parts.append(box("JarShelf_EndA", (-1.98, -0.55, 1.50),
                     (0.36, 0.05, 0.55), shelf_wood))
    parts.append(box("JarShelf_EndB", (-1.98, 1.15, 1.50),
                     (0.36, 0.05, 0.55), shelf_wood))
    parts.append(box("JarShelf_Top", (-1.98, 0.30, 1.755),
                     (0.36, 1.75, 0.05), shelf_wood))
    parts.append(box("JarShelf_Board", (-1.98, 0.30, 1.42),
                     (0.34, 1.70, 0.05), shelf_wood))
    random.seed(48)
    n_jars = 0
    for tier, zb in enumerate((1.445, 1.78)):
        y = -0.48
        k = 0
        while y < 1.08:
            w = random.uniform(0.11, 0.17)
            h = random.uniform(0.18, 0.26)
            r = random.uniform(0.05, 0.065)
            if y + w > 1.08:
                break
            lm = random.choice(liquids)
            potion_bottle("Jar_T%d_%d" % (tier, k),
                          (-1.98, y + w / 2.0, zb), h, r, lm, glass,
                          cork, parts)
            n_jars += 1
            k += 1
            y += w + random.uniform(0.01, 0.05)

    # --- hanging herb bundles from the back beam ---
    for i, hx in enumerate((-0.60, 0.10, 0.80)):
        parts.append(tapered_cylinder("HerbString_%d" % i,
                                      (hx, 1.98, 2.22),
                                      0.008, 0.008, 0.16, 6, cork))
        for j in range(3):
            a = j * 2.094
            lx = hx + 0.03 * math.cos(a)
            ly = 1.98 + 0.03 * math.sin(a)
            leaf = tapered_cylinder("HerbLeaf_%d_%d" % (i, j),
                                    (lx, ly, 1.98),
                                    0.012, 0.05, 0.28, 6,
                                    herb_green if j % 2 == 0 else herb_dry)
            parts.append(leaf)

    # --- framed alchemy chart on the back wall (right of the shelf) ---
    parts.append(box("Chart_Frame", (2.10, 2.03, 1.65),
                     (0.80, 0.06, 0.75), beam_wood))
    parts.append(box("Chart_Canvas", (2.10, 1.995, 1.65),
                     (0.68, 0.03, 0.63), chart_blue))
    parts.append(tapered_cylinder("Chart_Circle", (0, 0, 0),
                                  0.20, 0.20, 0.02, 16, gold))
    circle = parts[-1]
    circle.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    circle.location = (2.10, 1.975, 1.65)
    parts.append(box("Chart_Tri", (2.10, 1.975, 1.65),
                     (0.22, 0.02, 0.22), gold,
                     rot=(0.0, 0.0, math.radians(45.0))))
    for i, (sx, sy) in enumerate(((1.85, 1.90), (2.35, 1.88),
                                  (1.90, 1.42), (2.30, 1.45))):
        parts.append(box("Chart_Star_%d" % i, (sx, 1.975, sy),
                         (0.03, 0.02, 0.03), gold))

    # --- candle sconce on the left wall + warm point light ---
    parts.append(box("Sconce_Bracket", (-2.02, 1.45, 1.55),
                     (0.10, 0.08, 0.06), iron))
    parts.append(tapered_cylinder("Sconce_Cup", (-1.96, 1.45, 1.60),
                                  0.045, 0.035, 0.04, 8, brass))
    candle("SconceCandle", (-1.96, 1.45, 1.62), 0.13, 0.024,
           wax, flame_mat, parts)
    sconce_light = bpy.data.lights.new("SconceGlow", 'POINT')
    sconce_light.energy = 120.0
    sconce_light.color = (1.0, 0.70, 0.35)
    sconce_light.shadow_soft_size = 0.3
    sconce_obj = bpy.data.objects.new("SconceGlow", sconce_light)
    bpy.context.scene.collection.objects.link(sconce_obj)
    sconce_obj.location = (-1.90, 1.45, 1.80)

    # --- stool + rug in front of the workbench ---
    parts.append(box("Rug", (0.30, 0.55, 0.042),
                     (1.70, 1.20, 0.024), rug_red))
    parts.append(box("Rug_Trim", (0.30, 0.55, 0.056),
                     (1.50, 1.00, 0.006), rug_trim))
    parts.append(tapered_cylinder("Stool_Seat", (0.30, 0.55, 0.46),
                                  0.22, 0.22, 0.05, 10, bench_top))
    for i, a in enumerate((0.0, 2.094, 4.189)):
        lx = 0.30 + 0.16 * math.cos(a)
        ly = 0.55 + 0.16 * math.sin(a)
        leg = tapered_cylinder("StoolLeg_%d" % i, (0, 0, 0),
                               0.025, 0.03, 0.44, 8, bench_wood)
        leg.rotation_euler = (math.radians(10.0) * math.cos(a),
                              math.radians(10.0) * math.sin(a), 0.0)
        leg.location = (lx, ly, 0.22)
        parts.append(leg)
    parts.append(tapered_cylinder("Stool_Ring", (0.30, 0.55, 0.16),
                                  0.17, 0.17, 0.03, 10, iron))

    # --- books + scroll left on the floor by the bench ---
    parts.append(box("FloorBook_0", (-0.85, 0.55, 0.055),
                     (0.32, 0.26, 0.05), book_red,
                     rot=(0.0, 0.0, math.radians(12.0))))
    parts.append(box("FloorBook_1", (-0.83, 0.53, 0.105),
                     (0.30, 0.24, 0.05), book_green,
                     rot=(0.0, 0.0, math.radians(-6.0))))
    fscroll = tapered_cylinder("FloorScroll", (0, 0, 0),
                               0.04, 0.04, 0.40, 10, parchment)
    fscroll.rotation_euler = (math.radians(90.0), 0.0,
                             math.radians(30.0))
    fscroll.location = (1.15, 0.30, 0.045)
    parts.append(fscroll)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    print("ALC_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "047-alchemy-lab-corner.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "047-alchemy-lab-corner.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "alchemy_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("ALC_POLY total=%d tris=%d quads=%d ngons=%d bottles=%d "
          "jars=%d books=%d" % (total, tris, quads, ngons, n_bottles,
                                n_jars, n_books))
    for name, c in counts.items():
        print("ALC_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "047-alchemy-lab-corner.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 047 低模场景：炼金实验室角落\n\n")
        f.write("低多边形炼金实验室室内场景资产，平面着色（flat shading），"
                "干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 墙体：后墙（y=+2.2，5.4×2.6）+ 左墙（x=-2.2，4.6×2.6），"
                "上层石材、下层深色石基 + 木压条；木梁压顶 + 角柱\n")
        f.write("- 地面：6×5 石砖（0.86 见方，4 色交错）\n")
        f.write("- 工作台：2.6×0.95 重木台面 + 4 腿 + 下层架（木箱 2 个 + "
                "药水罐 2 个）+ 抽屉（黄铜拉手）\n")
        f.write("- 台面：研钵 + 研杵（倾斜 35°）、试管架（黄铜架 + 3 支试管，"
                "绿/紫/琥珀药液）、蒸馏器（圆底玻璃烧瓶 + 铜颈 + 导管 + "
                "接收瓶）、翻开的紫色法术书（两页微张 8°）、黄铜烛台"
                "（1 支蜡烛 + 火焰）、3 根干草药、横放羊皮卷轴\n")
        f.write("- 药水架：后墙 2.55 宽 × 0.55 高，2 层，共 %d 瓶药水"
                "（绿/紫/红/蓝/琥珀 5 色发光药液，玻璃瓶 + 软木塞），"
                "顶层右端 %d 本小书\n" % (n_bottles, n_books))
        f.write("- 坩埚：1.30×1.10 石质炉台上，铁锅（底 0.30 / 口 0.44，"
                "0.55 高）+ 铁箍口沿 + 绿色发光药液 + 3 个气泡 + 3 条"
                "微张铁腿；锅底 3 团火焰 + 橙色点光源（220W）；"
                "木柄铜勺斜靠锅沿\n")
        f.write("- 左角木桶（铁箍 2 道）+ 左墙木箱 2 个（顶上 1 瓶紫药水）\n")
        f.write("- 左墙药水罐架：2 层，共 %d 罐\n" % n_jars)
        f.write("- 悬挂草药：后梁下 3 束（绳 + 绿/干叶交错叶簇）\n")
        f.write("- 墙饰：炼金星图挂画（深蓝画布 + 金圆 + 旋转金三角 + "
                "4 颗金星），位于药水架右侧后墙\n")
        f.write("- 墙烛台：左墙铁托 + 黄铜烛杯 + 蜡烛 + 火焰，暖色点光源"
                "（120W）\n")
        f.write("- 凳子 + 地毯：三腿圆凳（铁环拉条），红色地毯（1.7×1.2，"
                "金色内边），位于工作台前方\n")
        f.write("- 地面散书：工作台旁 2 本平放的书 + 1 卷羊皮卷轴\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Alc_Stone / Alc_StoneDark：墙面石材 / 石基；"
                "Alc_Bench / Alc_BenchTop：工作台木材\n")
        f.write("- Liq_*：5 色发光药液（绿/紫/红/蓝/琥珀，Emission 1.0-1.2）\n")
        f.write("- Alc_Glass：半透明玻璃（alpha 0.38，BLEND，不投阴影，"
                "内层彩色药液可见）；Alc_Brass / Alc_Copper：黄铜/铜件\n")
        f.write("- Alc_Flame：火焰（Emission 橙，强度 4.0）+ 坩埚橙光"
                "（220W）+ 墙烛台暖光（120W）\n")
        f.write("- Alc_Herb / Alc_HerbDry：新鲜/干燥草药\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光 + "
                "坩埚橙光 + 墙烛台暖光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
