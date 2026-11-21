# -*- coding: utf-8 -*-
"""033 低模场景：药水店柜台（Potion Shop Counter）
Low-poly potion shop interior scene: plaster + wood-wainscot corner
walls, wooden plank floor, long shop counter with brass trim, wall
shelves stocked with coloured potion bottles, a hanging lantern with
warm point light, counter props (bottles, open ledger, candle, coin
stack, pouch), a bubbling cauldron and a stool on a rug.
Flat shading, clean topology. Eevee beauty + wireframe renders, .blend
+ note. Camera auto-fitted with fit_camera_to_objects (target 0.78).
Run: blender --background --python 033-potion-shop-counter.py
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


def tapered_box(name, center, bottom_size, top_size, height, mat):
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
    """Vertical (Z-axis) cylinder, triangle-fan caps (no N-gons)."""
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


def make_empty(name, location, rotation=(0.0, 0.0, 0.0)):
    empty = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(empty)
    empty.location = location
    empty.rotation_euler = rotation
    return empty


def potion_bottle(name, center, kind, liquid_mat, cork_mat, label_mat,
                  parts, scale=1.0):
    """A stylised potion bottle. kind: 'tall' | 'round' | 'vial'.
    Bottle body is the potion colour (opaque stylised glass)."""
    cx, cy, cz = center
    s = scale
    if kind == 'tall':
        parts.append(tapered_cylinder(name + "_Body", (cx, cy, cz + 0.11 * s),
                                      0.085 * s, 0.070 * s, 0.22 * s, 8,
                                      liquid_mat))
        parts.append(tapered_cylinder(name + "_Neck", (cx, cy, cz + 0.25 * s),
                                      0.045 * s, 0.040 * s, 0.08 * s, 8,
                                      liquid_mat))
        parts.append(tapered_cylinder(name + "_Cork", (cx, cy, cz + 0.315 * s),
                                      0.042 * s, 0.048 * s, 0.05 * s, 8,
                                      cork_mat))
        parts.append(box(name + "_Label", (cx, cy - 0.078 * s, cz + 0.11 * s),
                         (0.09 * s, 0.012 * s, 0.10 * s), label_mat))
    elif kind == 'round':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.11 * s,
                                              location=(cx, cy, cz + 0.11 * s))
        body = bpy.context.active_object
        body.name = name + "_Body"
        body.data.materials.append(liquid_mat)
        body.scale = (1.0, 1.0, 1.15)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        flat_shade(body)
        parts.append(body)
        parts.append(tapered_cylinder(name + "_Neck", (cx, cy, cz + 0.26 * s),
                                      0.045 * s, 0.040 * s, 0.07 * s, 8,
                                      liquid_mat))
        parts.append(tapered_cylinder(name + "_Cork", (cx, cy, cz + 0.315 * s),
                                      0.042 * s, 0.048 * s, 0.05 * s, 8,
                                      cork_mat))
    else:  # vial
        parts.append(tapered_cylinder(name + "_Body", (cx, cy, cz + 0.07 * s),
                                      0.05 * s, 0.045 * s, 0.14 * s, 8,
                                      liquid_mat))
        parts.append(tapered_cylinder(name + "_Cork", (cx, cy, cz + 0.155 * s),
                                      0.048 * s, 0.052 * s, 0.04 * s, 8,
                                      cork_mat))


def main():
    clear_scene()
    make_world_gradient()
    add_ground(size=16.0, color=(0.30, 0.22, 0.14))
    key, fill, rim = studio_lights(target=(0.3, 0.3, 0.9))
    key.data.energy = 650.0
    fill.data.energy = 220.0
    rim.data.energy = 380.0

    # --- materials ---
    plaster = solid_material("Shop_Plaster", (0.78, 0.72, 0.62),
                             metallic=0.0, roughness=0.95)
    wainscot = solid_material("Shop_Wainscot", (0.42, 0.27, 0.13),
                              metallic=0.0, roughness=0.85)
    beam_wood = solid_material("Shop_Beam", (0.32, 0.20, 0.10),
                               metallic=0.0, roughness=0.9)
    counter_wood = solid_material("Shop_Counter", (0.48, 0.31, 0.15),
                                  metallic=0.0, roughness=0.8)
    counter_dark = solid_material("Shop_CounterDark", (0.33, 0.20, 0.09),
                                  metallic=0.0, roughness=0.85)
    counter_top = solid_material("Shop_CounterTop", (0.58, 0.40, 0.20),
                                 metallic=0.0, roughness=0.7)
    brass = solid_material("Shop_Brass", (0.75, 0.58, 0.20),
                           metallic=0.9, roughness=0.3)
    iron = solid_material("Shop_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    shelf_wood = solid_material("Shop_Shelf", (0.40, 0.26, 0.12),
                                metallic=0.0, roughness=0.85)
    cork = solid_material("Shop_Cork", (0.72, 0.55, 0.32),
                          metallic=0.0, roughness=0.95)
    label = solid_material("Shop_Label", (0.90, 0.85, 0.68),
                           metallic=0.0, roughness=0.9)
    paper = solid_material("Shop_Paper", (0.92, 0.88, 0.74),
                           metallic=0.0, roughness=0.9)
    book_red = solid_material("Shop_BookCover", (0.45, 0.10, 0.12),
                              metallic=0.0, roughness=0.8)
    gold = solid_material("Shop_Gold", (0.85, 0.68, 0.25),
                          metallic=0.9, roughness=0.25)
    rug_red = solid_material("Shop_Rug", (0.45, 0.12, 0.12),
                             metallic=0.0, roughness=1.0)
    rug_trim = solid_material("Shop_RugTrim", (0.75, 0.60, 0.30),
                              metallic=0.0, roughness=1.0)
    brew_green = solid_material("Shop_Brew", (0.15, 0.55, 0.15),
                                metallic=0.0, roughness=0.15)
    # potion liquids (opaque stylised glass)
    pot_red = solid_material("Potion_Red", (0.75, 0.12, 0.14),
                             metallic=0.0, roughness=0.12)
    pot_green = solid_material("Potion_Green", (0.12, 0.55, 0.18),
                               metallic=0.0, roughness=0.12)
    pot_blue = solid_material("Potion_Blue", (0.12, 0.30, 0.75),
                              metallic=0.0, roughness=0.12)
    pot_purple = solid_material("Potion_Purple", (0.45, 0.20, 0.65),
                                metallic=0.0, roughness=0.12)
    pot_amber = solid_material("Potion_Amber", (0.85, 0.50, 0.10),
                               metallic=0.0, roughness=0.12)
    pot_pink = solid_material("Potion_Pink", (0.85, 0.35, 0.55),
                              metallic=0.0, roughness=0.12)
    lamp_glass = bpy.data.materials.new("Shop_LampGlass")
    lamp_glass.use_nodes = True
    lamp_glass.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Color"].default_value = (1.0, 0.75, 0.35, 1.0)
    lamp_glass.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Strength"].default_value = 1.5
    lamp_glass.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"].default_value = (0.95, 0.75, 0.40, 1.0)
    flame_mat = bpy.data.materials.new("Shop_Flame")
    flame_mat.use_nodes = True
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Color"].default_value = (1.0, 0.55, 0.10, 1.0)
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Emission Strength"].default_value = 4.0
    flame_mat.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"].default_value = (1.0, 0.60, 0.10, 1.0)

    parts = []

    # --- corner walls: back (y=+2.2) + left (x=-2.2), plaster upper,
    #     wood wainscot lower, beam across the top + corner post ---
    parts.append(box("Wall_Back", (0.0, 2.2, 1.30),
                     (5.4, 0.30, 2.60), plaster))
    parts.append(box("Wall_Left", (-2.2, 0.0, 1.30),
                     (0.30, 4.6, 2.60), plaster))
    parts.append(box("Wainscot_Back", (0.0, 2.16, 0.50),
                     (5.4, 0.36, 1.00), wainscot))
    parts.append(box("Wainscot_Left", (-2.16, 0.0, 0.50),
                     (0.36, 4.6, 1.00), wainscot))
    parts.append(box("WainscotRail_Back", (0.0, 2.12, 1.02),
                     (5.4, 0.42, 0.06), counter_dark))
    parts.append(box("WainscotRail_Left", (-2.12, 0.0, 1.02),
                     (0.42, 4.6, 0.06), counter_dark))
    parts.append(box("Beam_Back", (0.0, 2.05, 2.45),
                     (5.4, 0.28, 0.22), beam_wood))
    parts.append(box("Beam_Left", (-2.05, 0.0, 2.45),
                     (0.28, 4.6, 0.22), beam_wood))
    parts.append(box("Post_Corner", (-2.05, 2.05, 1.30),
                     (0.28, 0.28, 2.60), beam_wood))

    # --- wooden plank floor (8 planks along X, alternating shades) ---
    random.seed(33)
    plank_shades = [(0.42, 0.28, 0.14), (0.50, 0.34, 0.18),
                    (0.38, 0.25, 0.12), (0.55, 0.38, 0.20)]
    for i in range(8):
        px = -2.1 + i * 0.6
        g = plank_shades[i % len(plank_shades)]
        pm = solid_material("Plank_%d" % i, g,
                            metallic=0.0, roughness=0.9)
        parts.append(box("Plank_%02d" % i, (px, 0.0, 0.015),
                         (0.58, 4.6, 0.03), pm))

    # --- shop counter: body + top slab + front panels + brass trim ---
    # counter runs along X, front face at y=-0.28, top at z=1.00
    parts.append(box("Counter_Body", (0.3, 0.1, 0.46),
                     (3.0, 0.75, 0.92), counter_wood))
    parts.append(box("Counter_Top", (0.3, 0.1, 0.96),
                     (3.2, 0.90, 0.08), counter_top))
    parts.append(box("Counter_Kick", (0.3, -0.20, 0.06),
                     (3.0, 0.12, 0.12), counter_dark))
    parts.append(box("Counter_Trim", (0.3, -0.285, 0.92),
                     (3.2, 0.04, 0.05), brass))
    for i in range(4):
        px = -0.9 + i * 0.8
        parts.append(box("CounterPanel_%d" % i, (px, -0.26, 0.46),
                         (0.62, 0.05, 0.80), counter_dark))
        parts.append(box("CounterPanelTrim_%d" % i, (px, -0.285, 0.46),
                         (0.66, 0.02, 0.84), brass))

    # --- wall shelves on the back wall (y=1.95), 2 tiers ---
    for sz, shelf_z in ((1.50, 1.50), (1.95, 1.95)):
        parts.append(box("Shelf_%d" % int(sz * 100), (0.3, 1.98, shelf_z),
                         (2.6, 0.30, 0.06), shelf_wood))
        for bx in (-0.8, 1.4):
            parts.append(box("ShelfBracket_%d_%d" % (int(sz * 100), int(bx * 10)),
                             (bx, 2.02, shelf_z - 0.12),
                             (0.06, 0.18, 0.18), iron))
    # shelf bottles: lower tier (z=1.53) + upper tier (z=1.98)
    shelf_bottles = [
        ("ShelfBtl_A", -0.75, 1.53, 'tall', pot_red, 1.0),
        ("ShelfBtl_B", -0.45, 1.53, 'round', pot_green, 1.0),
        ("ShelfBtl_C", -0.12, 1.53, 'tall', pot_blue, 1.1),
        ("ShelfBtl_D", 0.22, 1.53, 'vial', pot_purple, 1.0),
        ("ShelfBtl_E", 0.45, 1.53, 'tall', pot_amber, 0.9),
        ("ShelfBtl_F", 0.72, 1.53, 'round', pot_pink, 0.9),
        ("ShelfBtl_G", 1.00, 1.53, 'vial', pot_green, 1.0),
        ("ShelfBtl_H", 1.25, 1.53, 'tall', pot_purple, 0.9),
        ("ShelfBtl_I", -0.60, 1.98, 'vial', pot_blue, 1.0),
        ("ShelfBtl_J", -0.30, 1.98, 'tall', pot_amber, 1.0),
        ("ShelfBtl_K", 0.05, 1.98, 'round', pot_red, 0.9),
        ("ShelfBtl_L", 0.40, 1.98, 'tall', pot_green, 1.0),
        ("ShelfBtl_M", 0.75, 1.98, 'vial', pot_pink, 1.0),
        ("ShelfBtl_N", 1.05, 1.98, 'tall', pot_blue, 0.9),
    ]
    for name, bx, bz, kind, mat, s in shelf_bottles:
        potion_bottle(name, (bx, 1.98, bz), kind, mat, cork, label,
                      parts, scale=s)

    # --- hanging lantern above the counter (chain from the beam) ---
    # chain links: 5 small iron boxes down from z=2.45 to z=2.05
    for i in range(5):
        parts.append(box("LampChain_%d" % i, (0.3, 0.1, 2.40 - i * 0.08),
                         (0.05, 0.05, 0.07), iron))
    # lantern frame: top cap + 4 corner posts + bottom plate
    parts.append(tapered_cylinder("Lamp_Cap", (0.3, 0.1, 2.02),
                                  0.16, 0.06, 0.08, 6, iron))
    parts.append(box("Lamp_Glass", (0.3, 0.1, 1.86),
                     (0.22, 0.22, 0.24), lamp_glass))
    for dx, dy in ((-0.11, -0.11), (0.11, -0.11),
                   (-0.11, 0.11), (0.11, 0.11)):
        parts.append(box("LampPost_%d_%d" % (int(dx * 100), int(dy * 100)),
                         (0.3 + dx, 0.1 + dy, 1.86),
                         (0.03, 0.03, 0.26), iron))
    parts.append(box("Lamp_Base", (0.3, 0.1, 1.72),
                     (0.26, 0.26, 0.03), iron))
    parts.append(tapered_cylinder("Lamp_Candle", (0.3, 0.1, 1.80),
                                  0.035, 0.035, 0.10, 8, paper))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.045,
                                          location=(0.3, 0.1, 1.88))
    flame = bpy.context.active_object
    flame.name = "Lamp_Flame"
    flame.data.materials.append(flame_mat)
    flame.scale = (1.0, 1.0, 1.6)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    flat_shade(flame)
    parts.append(flame)
    lamp_light = bpy.data.lights.new("LampGlow", 'POINT')
    lamp_light.energy = 220.0
    lamp_light.color = (1.0, 0.70, 0.35)
    lamp_light.shadow_soft_size = 0.3
    lamp_obj = bpy.data.objects.new("LampGlow", lamp_light)
    bpy.context.scene.collection.objects.link(lamp_obj)
    lamp_obj.location = (0.3, 0.1, 1.80)

    # --- counter props: bottles, open ledger, candle, coins, pouch ---
    potion_bottle("CounterBtl_A", (-0.75, 0.15, 1.00), 'tall', pot_red,
                  cork, label, parts, scale=1.1)
    potion_bottle("CounterBtl_B", (-0.45, 0.05, 1.00), 'round', pot_blue,
                  cork, label, parts, scale=1.0)
    potion_bottle("CounterBtl_C", (1.05, 0.15, 1.00), 'vial', pot_green,
                  cork, label, parts, scale=1.2)
    # open ledger: two angled page slabs + red cover underneath
    parts.append(box("Ledger_Cover", (0.15, 0.10, 1.015),
                     (0.62, 0.46, 0.02), book_red))
    parts.append(box("Ledger_Left", (0.0, 0.10, 1.035),
                     (0.28, 0.42, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(8.0))))
    parts.append(box("Ledger_Right", (0.30, 0.10, 1.035),
                     (0.28, 0.42, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(-8.0))))
    # candle in brass holder on the counter
    parts.append(tapered_cylinder("Candle_Holder", (1.45, 0.05, 1.02),
                                  0.07, 0.05, 0.04, 8, brass))
    parts.append(tapered_cylinder("Candle", (1.45, 0.05, 1.08),
                                  0.035, 0.030, 0.10, 8, paper))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.03,
                                          location=(1.45, 0.05, 1.15))
    cflame = bpy.context.active_object
    cflame.name = "Candle_Flame"
    cflame.data.materials.append(flame_mat)
    cflame.scale = (1.0, 1.0, 1.6)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    flat_shade(cflame)
    parts.append(cflame)
    # coin stack (3 gold coins) + pouch
    for i in range(3):
        parts.append(tapered_cylinder("Coin_%d" % i, (0.75, -0.10, 1.015 + i * 0.025),
                                      0.07, 0.07, 0.025, 10, gold))
    parts.append(tapered_cylinder("Pouch", (1.15, -0.12, 1.05),
                                  0.10, 0.06, 0.10, 8, counter_dark))
    parts.append(box("Pouch_Tie", (1.15, -0.12, 1.11),
                     (0.14, 0.03, 0.02), brass))

    # --- cauldron beside the counter's right end (visible from camera) ---
    parts.append(tapered_cylinder("Cauldron_Pot", (2.05, 0.10, 0.45),
                                  0.28, 0.36, 0.55, 12, iron))
    parts.append(tapered_cylinder("Cauldron_Brew", (2.05, 0.10, 0.70),
                                  0.32, 0.32, 0.03, 12, brew_green))
    for i, (lx, ly) in enumerate(((1.82, -0.07), (2.28, -0.07), (2.05, 0.33))):
        parts.append(box("CauldronLeg_%d" % i, (lx, ly, 0.09),
                         (0.07, 0.07, 0.18), iron))
    # wooden spoon sticking out of the brew, tilted
    spoon = tapered_cylinder("Cauldron_Spoon", (0, 0, 0),
                             0.02, 0.015, 0.55, 6, counter_dark)
    spoon.rotation_euler = (math.radians(35.0), 0.0, math.radians(20.0))
    spoon.location = (2.05, 0.10, 0.90)
    parts.append(spoon)
    # brew bubbles: 3 small green spheres on the surface
    for i, (bx, by) in enumerate(((1.95, 0.03), (2.15, 0.15), (2.05, 0.00))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.045,
                                              location=(bx, by, 0.72))
        bub = bpy.context.active_object
        bub.name = "BrewBubble_%d" % i
        bub.data.materials.append(brew_green)
        flat_shade(bub)
        parts.append(bub)

    # --- rug + stool in front of the counter ---
    # rug sits ON TOP of the floor planks (plank top z=0.03)
    parts.append(box("Rug", (0.3, -0.95, 0.042),
                     (2.2, 1.1, 0.024), rug_red))
    parts.append(box("Rug_Trim", (0.3, -0.95, 0.056),
                     (2.0, 0.9, 0.006), rug_trim))
    parts.append(tapered_cylinder("Stool_Seat", (0.3, -0.95, 0.44),
                                  0.26, 0.26, 0.06, 12, counter_wood))
    for i, a in enumerate((0.0, 2.094, 4.189)):
        lx = 0.3 + 0.20 * math.cos(a)
        ly = -0.95 + 0.20 * math.sin(a)
        leg = tapered_cylinder("StoolLeg_%d" % i, (lx, ly, 0.21),
                               0.03, 0.025, 0.42, 6, counter_dark)
        parts.append(leg)

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    print("SHOP_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "033-potion-shop-counter.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes", "033-potion-shop-counter.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "potion_shop_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("SHOP_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("SHOP_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "033-potion-shop-counter.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 033 低模场景：药水店柜台\n\n")
        f.write("低多边形药水店室内场景资产，平面着色（flat shading），干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 墙体：后墙（y=+2.2，5.4×2.6）+ 左墙（x=-2.2，4.6×2.6），"
                "上层灰泥、下层木护墙板 + 压条；木梁压顶 + 角柱\n")
        f.write("- 地面：8 块木地板（0.58 宽，灰度交错）\n")
        f.write("- 柜台：3.0×0.75×0.92 柜身 + 3.2×0.90×0.08 台面，"
                "正面 4 块深色嵌板 + 黄铜包边，踢脚线 + 黄铜饰条\n")
        f.write("- 药水架：后墙两层木架（z=1.50 / 1.95，2.6 长），铁支架，"
                "共 14 瓶药水（高瓶 / 圆腹瓶 / 小瓶，红绿蓝紫琥珀粉 6 色，"
                "软木塞 + 米色标签）\n")
        f.write("- 吊灯：5 节铁链自横梁垂下，铁框 + 发光玻璃罩（Emission 暖黄），"
                "内有蜡烛 + 火焰（Emission 橙），暖色点光源（220W）\n")
        f.write("- 柜台道具：3 瓶药水（红高瓶 / 蓝圆腹瓶 / 绿小瓶），"
                "翻开的红皮账本（两页微张 8°），黄铜烛台 + 蜡烛 + 火焰，"
                "3 枚金币叠放，束口钱袋 + 黄铜扎带\n")
        f.write("- 大锅：右侧铁锅（12 边，0.55 高）+ 绿色药液面 + 3 条铁腿，"
                "木勺斜插（35°），药液面 3 个气泡\n")
        f.write("- 地毯 + 圆凳：红色地毯（2.2×1.1，黄铜色内边），"
                "圆凳（12 边座面 + 3 条垂直凳腿），位于柜台前方\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Shop_Plaster：墙面灰泥；Shop_Wainscot：木护墙板\n")
        f.write("- Shop_Counter / Shop_CounterTop：柜身 / 台面木材；"
                "Shop_Brass：黄铜饰条 / 烛台 / 钱袋扎带\n")
        f.write("- Potion_*：6 色药水（不透明风格化玻璃，roughness 0.12）\n")
        f.write("- Shop_LampGlass：吊灯发光玻璃（Emission 暖黄 1.5）+ "
                "LampGlow 点光源（220W，暖色）\n")
        f.write("- Shop_Flame：火焰（Emission 橙，强度 4.0）\n")
        f.write("- Shop_Brew：绿色药液（roughness 0.15）+ 气泡\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光 + 吊灯暖光，"
                "40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
