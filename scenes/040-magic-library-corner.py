# -*- coding: utf-8 -*-
"""040 低模场景：魔法图书馆角落（Magic Library Corner）
Low-poly magic library interior: plaster + wood-wainscot corner walls,
wooden plank floor, tall bookshelf (5 tiers, ~60 books, leaning books +
horizontal stack), low bookshelf on the left wall with a globe, library
ladder leaning on the tall shelf, wooden desk with open spellbook,
3-arm candelabra, ink pot + quill, book stack and scroll, tall floor
candelabra with warm point light, framed star chart, rug + chair.
Flat shading, clean topology. Eevee beauty + wireframe renders, .blend
+ note. Camera auto-fitted with fit_camera_to_objects (target 0.78).
Run: blender --background --python 040-magic-library-corner.py
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
    NOTE (2026-11-23, 040): verts are baked in WORLD coords, so a
    rotation_euler set afterwards rotates about the WORLD ORIGIN, not
    the cylinder centre. To rotate one, build it at (0,0,0), set the
    rotation, then set .location (moon/scroll/knobs were displaced by
    this bug in the first 040 render)."""
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


def book_row(parts, prefix, x0, x1, z_base, y_center, depth, palette,
             max_h=0.42):
    """A row of upright books on a shelf (size along X = width).
    Occasional leaning book (12%) and gap (10%). Deterministic via
    the caller's random seed."""
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
    add_ground(size=16.0, color=(0.30, 0.22, 0.14))
    key, fill, rim = studio_lights(target=(0.3, 0.3, 0.9))
    key.data.energy = 650.0
    fill.data.energy = 220.0
    rim.data.energy = 380.0

    # --- materials ---
    plaster = solid_material("Lib_Plaster", (0.76, 0.70, 0.58),
                             metallic=0.0, roughness=0.95)
    wainscot = solid_material("Lib_Wainscot", (0.40, 0.26, 0.13),
                              metallic=0.0, roughness=0.85)
    beam_wood = solid_material("Lib_Beam", (0.30, 0.19, 0.09),
                               metallic=0.0, roughness=0.9)
    shelf_wood = solid_material("Lib_Shelf", (0.38, 0.24, 0.11),
                                metallic=0.0, roughness=0.85)
    shelf_dark = solid_material("Lib_ShelfDark", (0.28, 0.17, 0.08),
                                metallic=0.0, roughness=0.9)
    desk_wood = solid_material("Lib_Desk", (0.46, 0.30, 0.14),
                               metallic=0.0, roughness=0.8)
    desk_top = solid_material("Lib_DeskTop", (0.56, 0.38, 0.19),
                              metallic=0.0, roughness=0.7)
    brass = solid_material("Lib_Brass", (0.75, 0.58, 0.20),
                           metallic=0.9, roughness=0.3)
    gold = solid_material("Lib_Gold", (0.85, 0.68, 0.25),
                          metallic=0.9, roughness=0.25)
    iron = solid_material("Lib_Iron", (0.16, 0.16, 0.18),
                          metallic=0.7, roughness=0.5)
    paper = solid_material("Lib_Paper", (0.92, 0.88, 0.74),
                           metallic=0.0, roughness=0.9)
    parchment = solid_material("Lib_Parchment", (0.88, 0.80, 0.60),
                               metallic=0.0, roughness=0.9)
    ink = solid_material("Lib_Ink", (0.05, 0.05, 0.10),
                         metallic=0.0, roughness=0.15)
    rug_red = solid_material("Lib_Rug", (0.42, 0.11, 0.13),
                             metallic=0.0, roughness=1.0)
    rug_trim = solid_material("Lib_RugTrim", (0.72, 0.58, 0.28),
                              metallic=0.0, roughness=1.0)
    chart_blue = solid_material("Lib_Chart", (0.08, 0.12, 0.30),
                                metallic=0.0, roughness=0.9)
    globe_blue = solid_material("Lib_Globe", (0.15, 0.35, 0.60),
                                metallic=0.0, roughness=0.6)
    wax = solid_material("Lib_Wax", (0.94, 0.88, 0.74),
                         metallic=0.0, roughness=0.7)
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
    book_ochre = solid_material("Book_Ochre", (0.65, 0.50, 0.15),
                                metallic=0.0, roughness=0.8)
    palette = [book_red, book_green, book_blue, book_purple,
               book_brown, book_teal, book_ochre]
    flame_mat = bpy.data.materials.new("Lib_Flame")
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
                     (5.4, 0.42, 0.06), shelf_dark))
    parts.append(box("WainscotRail_Left", (-2.12, 0.0, 1.02),
                     (0.42, 4.6, 0.06), shelf_dark))
    parts.append(box("Beam_Back", (0.0, 2.05, 2.45),
                     (5.4, 0.28, 0.22), beam_wood))
    parts.append(box("Beam_Left", (-2.05, 0.0, 2.45),
                     (0.28, 4.6, 0.22), beam_wood))
    parts.append(box("Post_Corner", (-2.05, 2.05, 1.30),
                     (0.28, 0.28, 2.60), beam_wood))

    # --- wooden plank floor (8 planks along X, alternating shades) ---
    random.seed(40)
    plank_shades = [(0.42, 0.28, 0.14), (0.50, 0.34, 0.18),
                    (0.38, 0.25, 0.12), (0.55, 0.38, 0.20)]
    for i in range(8):
        px = -2.1 + i * 0.6
        pm = solid_material("Plank_%d" % i, plank_shades[i % 4],
                            metallic=0.0, roughness=0.9)
        parts.append(box("Plank_%02d" % i, (px, 0.0, 0.015),
                         (0.58, 4.6, 0.03), pm))

    # --- tall bookshelf against the back wall: x -1.6..0.9, y ~1.95,
    #     2.35 high, 5 book tiers ---
    parts.append(box("Shelf_Left", (-1.575, 1.95, 1.175),
                     (0.05, 0.40, 2.35), shelf_wood))
    parts.append(box("Shelf_Right", (0.875, 1.95, 1.175),
                     (0.05, 0.40, 2.35), shelf_wood))
    parts.append(box("Shelf_Top", (-0.35, 1.95, 2.325),
                     (2.5, 0.40, 0.05), shelf_wood))
    parts.append(box("Shelf_Plinth", (-0.35, 1.95, 0.05),
                     (2.5, 0.44, 0.10), shelf_dark))
    parts.append(box("Shelf_Back", (-0.35, 2.13, 1.175),
                     (2.5, 0.04, 2.35), shelf_dark))
    for i, sz in enumerate((0.55, 1.00, 1.45, 1.90)):
        parts.append(box("ShelfBoard_%d" % i, (-0.35, 1.95, sz),
                         (2.45, 0.38, 0.05), shelf_wood))
    # book rows: bases at plinth top 0.10 and board tops 0.575/1.025/
    # 1.475/1.925; inner x range -1.55..0.85, book depth 0.30
    random.seed(40)
    n_books = 0
    for t, (zb, mh) in enumerate(((0.10, 0.42), (0.575, 0.40),
                                  (1.025, 0.40), (1.475, 0.40),
                                  (1.925, 0.35))):
        n_books += book_row(parts, "Book_T%d" % t, -1.55, 0.85, zb, 1.95,
                            0.30, palette, max_h=mh)
    # horizontal stack on tier 2 (z=1.025): 3 flat books at the right end
    for i in range(3):
        parts.append(box("BookStack_%d" % i,
                         (0.68, 1.95, 1.05 + i * 0.055),
                         (0.30, 0.28, 0.05), palette[(i + 2) % len(palette)],
                         rot=(0.0, 0.0, math.radians((i - 1) * 7.0))))

    # --- low bookshelf on the left wall: y -0.6..1.4, x ~-1.95,
    #     1.15 high, 2 book tiers (books face +x) ---
    parts.append(box("LowShelf_EndA", (-1.95, -0.575, 0.575),
                     (0.40, 0.05, 1.15), shelf_wood))
    parts.append(box("LowShelf_EndB", (-1.95, 1.375, 0.575),
                     (0.40, 0.05, 1.15), shelf_wood))
    parts.append(box("LowShelf_Top", (-1.95, 0.40, 1.125),
                     (0.40, 2.0, 0.05), shelf_wood))
    parts.append(box("LowShelf_Plinth", (-1.95, 0.40, 0.05),
                     (0.44, 2.0, 0.10), shelf_dark))
    parts.append(box("LowShelf_Back", (-2.13, 0.40, 0.575),
                     (0.04, 2.0, 1.15), shelf_dark))
    parts.append(box("LowShelf_Board", (-1.95, 0.40, 0.55),
                     (0.38, 1.95, 0.05), shelf_wood))
    # books along Y: reuse book_row by swapping axes via a manual loop
    random.seed(41)
    n_low = 0
    for t, (zb, mh) in enumerate(((0.10, 0.42), (0.575, 0.40))):
        y = -0.50
        k = 0
        while y < 1.30 - 0.06:
            w = random.uniform(0.06, 0.11)
            h = random.uniform(0.28, mh)
            if y + w > 1.30:
                break
            mat = random.choice(palette)
            tilt = 0.0
            if random.random() < 0.12:
                tilt = random.choice((-1, 1)) * math.radians(12)
            lift = (h / 2.0) * (1.0 - math.cos(tilt)) \
                + (w / 2.0) * abs(math.sin(tilt))
            parts.append(box("LBook_T%d_%d" % (t, k),
                             (-1.95, y + w / 2.0, zb + h / 2.0 + lift),
                             (0.30, w, h), mat,
                             rot=(tilt, 0.0, 0.0)))
            k += 1
            n_low += 1
            y += w + random.uniform(0.0, 0.015)
            if random.random() < 0.10:
                y += random.uniform(0.08, 0.18)
    # globe on top of the low shelf
    parts.append(tapered_cylinder("Globe_Stand", (-1.95, 1.05, 1.19),
                                  0.03, 0.025, 0.08, 8, brass))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.17,
                                          location=(-1.95, 1.05, 1.40))
    globe = bpy.context.active_object
    globe.name = "Globe"
    globe.data.materials.append(globe_blue)
    flat_shade(globe)
    parts.append(globe)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.19, minor_radius=0.012,
                                     major_segments=16, minor_segments=6,
                                     location=(-1.95, 1.05, 1.40),
                                     rotation=(math.radians(70), 0, 0))
    ring = bpy.context.active_object
    ring.name = "Globe_Ring"
    ring.data.materials.append(gold)
    flat_shade(ring)
    parts.append(ring)

    # --- library ladder leaning on the tall shelf (x=-1.1) ---
    # bottom (y=1.05, z=0) -> top (y=1.72, z=2.10), tilt ~17.7 deg
    lean = math.radians(-17.7)
    for j, rx in enumerate((-1.35, -0.85)):
        parts.append(box("LadderRail_%d" % j, (rx, 1.385, 1.05),
                         (0.05, 0.05, 2.20), beam_wood,
                         rot=(lean, 0.0, 0.0)))
    for i in range(6):
        t = 0.15 + i * 0.14
        parts.append(box("LadderRung_%d" % i,
                         (-1.10, 1.05 + 0.67 * t, 2.10 * t),
                         (0.46, 0.05, 0.05), shelf_wood,
                         rot=(lean, 0.0, 0.0)))

    # --- desk in front of the bookshelf (center 1.05, 0.55) ---
    parts.append(box("Desk_Top", (1.05, 0.55, 0.78),
                     (1.7, 0.90, 0.06), desk_top))
    for dx, dy in ((-0.75, -0.35), (0.75, -0.35),
                   (-0.75, 0.35), (0.75, 0.35)):
        parts.append(box("DeskLeg_%d_%d" % (int(dx * 100), int(dy * 100)),
                         (1.05 + dx, 0.55 + dy, 0.375),
                         (0.08, 0.08, 0.75), desk_wood))
    parts.append(box("Desk_Drawer", (1.05, 0.09, 0.60),
                     (1.40, 0.04, 0.28), shelf_dark))
    for i, kx in enumerate((0.55, 1.55)):
        knob = tapered_cylinder("DeskKnob_%d" % i, (0, 0, 0),
                                0.02, 0.02, 0.03, 8, brass)
        knob.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        knob.location = (kx, 0.065, 0.60)
        parts.append(knob)
    parts.append(box("Desk_Modesty", (1.05, 0.95, 0.55),
                     (1.50, 0.04, 0.35), desk_wood))
    # open spellbook on the desk (cover + two pages tilted 8 deg)
    parts.append(box("Spellbook_Cover", (0.55, 0.55, 0.82),
                     (0.56, 0.42, 0.02), book_blue))
    parts.append(box("Spellbook_Left", (0.42, 0.55, 0.835),
                     (0.26, 0.38, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(8.0))))
    parts.append(box("Spellbook_Right", (0.68, 0.55, 0.835),
                     (0.26, 0.38, 0.015), paper,
                     rot=(0.0, 0.0, math.radians(-8.0))))
    # 3-arm candelabra on the desk
    parts.append(tapered_cylinder("Candelabra_Base", (1.55, 0.35, 0.825),
                                  0.09, 0.06, 0.03, 10, brass))
    parts.append(tapered_cylinder("Candelabra_Stem", (1.55, 0.35, 0.99),
                                  0.02, 0.02, 0.30, 8, brass))
    parts.append(box("Candelabra_ArmL", (1.47, 0.35, 1.08),
                     (0.16, 0.03, 0.03), brass))
    parts.append(box("Candelabra_ArmR", (1.63, 0.35, 1.08),
                     (0.16, 0.03, 0.03), brass))
    parts.append(tapered_cylinder("Candelabra_CupL", (1.40, 0.35, 1.10),
                                  0.035, 0.03, 0.03, 8, brass))
    parts.append(tapered_cylinder("Candelabra_CupR", (1.70, 0.35, 1.10),
                                  0.035, 0.03, 0.03, 8, brass))
    parts.append(tapered_cylinder("Candelabra_CupC", (1.55, 0.35, 1.15),
                                  0.035, 0.03, 0.03, 8, brass))
    candle("DeskCandle_L", (1.40, 0.35, 1.115), 0.12, 0.025,
           wax, flame_mat, parts)
    candle("DeskCandle_R", (1.70, 0.35, 1.115), 0.12, 0.025,
           wax, flame_mat, parts)
    candle("DeskCandle_C", (1.55, 0.35, 1.165), 0.14, 0.025,
           wax, flame_mat, parts)
    # ink pot + quill
    parts.append(tapered_cylinder("InkPot", (0.45, 0.85, 0.85),
                                  0.05, 0.045, 0.08, 10, iron))
    parts.append(tapered_cylinder("Ink_Surface", (0.45, 0.85, 0.885),
                                  0.04, 0.04, 0.01, 10, ink))
    quill = box("Quill", (0.52, 0.85, 0.90),
                (0.015, 0.16, 0.012), paper,
                rot=(math.radians(-30.0), 0.0, math.radians(20.0)))
    parts.append(quill)
    # stack of 3 books on the desk
    for i in range(3):
        parts.append(box("DeskBook_%d" % i,
                         (1.45, 0.80, 0.835 + i * 0.055),
                         (0.34, 0.26, 0.05), palette[(i + 4) % len(palette)],
                         rot=(0.0, 0.0, math.radians((i - 1) * 9.0))))
    # rolled scroll lying on the desk
    scroll = tapered_cylinder("Scroll", (0, 0, 0),
                              0.045, 0.045, 0.45, 10, parchment)
    scroll.rotation_euler = (0.0, math.radians(90.0), 0.0)
    scroll.location = (0.75, 0.85, 0.855)
    parts.append(scroll)
    for sx in (0.51, 0.99):
        knob = tapered_cylinder("ScrollKnob_%d" % int(sx * 100),
                                (0, 0, 0), 0.055, 0.055, 0.02, 8,
                                desk_wood)
        knob.rotation_euler = (0.0, math.radians(90.0), 0.0)
        knob.location = (sx, 0.85, 0.855)
        parts.append(knob)

    # --- tall floor candelabra near the low shelf ---
    parts.append(tapered_cylinder("FloorCand_Base", (-1.55, 0.75, 0.02),
                                  0.16, 0.10, 0.04, 10, brass))
    parts.append(tapered_cylinder("FloorCand_Pole", (-1.55, 0.75, 0.68),
                                  0.03, 0.025, 1.28, 8, brass))
    parts.append(tapered_cylinder("FloorCand_Tray", (-1.55, 0.75, 1.33),
                                  0.14, 0.11, 0.03, 10, brass))
    for i, a in enumerate((0.0, 2.094, 4.189)):
        fx = -1.55 + 0.09 * math.cos(a)
        fy = 0.75 + 0.09 * math.sin(a)
        candle("FloorCandle_%d" % i, (fx, fy, 1.345), 0.14, 0.025,
               wax, flame_mat, parts)
    floor_light = bpy.data.lights.new("FloorCandGlow", 'POINT')
    floor_light.energy = 180.0
    floor_light.color = (1.0, 0.70, 0.35)
    floor_light.shadow_soft_size = 0.3
    floor_light_obj = bpy.data.objects.new("FloorCandGlow", floor_light)
    bpy.context.scene.collection.objects.link(floor_light_obj)
    floor_light_obj.location = (-1.55, 0.75, 1.50)

    # --- framed star chart on the back wall above the desk ---
    parts.append(box("Chart_Frame", (1.70, 2.03, 1.65),
                     (0.95, 0.06, 0.75), shelf_dark))
    parts.append(box("Chart_Canvas", (1.70, 1.995, 1.65),
                     (0.83, 0.03, 0.63), chart_blue))
    moon = tapered_cylinder("Chart_Moon", (0, 0, 0),
                            0.12, 0.12, 0.02, 12, gold)
    moon.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    moon.location = (1.70, 1.975, 1.68)
    parts.append(moon)
    for i, (sx, sy) in enumerate(((1.45, 1.85), (1.95, 1.80),
                                  (1.50, 1.45), (1.90, 1.50),
                                  (1.70, 1.42))):
        parts.append(box("Chart_Star_%d" % i, (sx, 1.975, sy),
                         (0.03, 0.02, 0.03), gold))

    # --- rug + chair in front of the desk ---
    parts.append(box("Rug", (0.9, 0.15, 0.042),
                     (2.6, 1.7, 0.024), rug_red))
    parts.append(box("Rug_Trim", (0.9, 0.15, 0.056),
                     (2.4, 1.5, 0.006), rug_trim))
    parts.append(box("Chair_Seat", (1.05, -0.35, 0.45),
                     (0.50, 0.45, 0.05), desk_wood))
    for dx, dy in ((-0.20, -0.17), (0.20, -0.17),
                   (-0.20, 0.17), (0.20, 0.17)):
        parts.append(box("ChairLeg_%d_%d" % (int(dx * 100), int(dy * 100)),
                         (1.05 + dx, -0.35 + dy, 0.225),
                         (0.05, 0.05, 0.45), shelf_dark))
    for dx in (-0.20, 0.20):
        parts.append(box("ChairBack_%d" % int(dx * 100),
                         (1.05 + dx, -0.55, 0.70),
                         (0.05, 0.05, 0.50), desk_wood))
    parts.append(box("ChairBack_Top", (1.05, -0.55, 0.95),
                     (0.50, 0.05, 0.08), desk_wood))

    # --- two books left on the floor by the ladder ---
    parts.append(box("FloorBook_0", (-0.60, 1.20, 0.055),
                     (0.32, 0.26, 0.05), book_red,
                     rot=(0.0, 0.0, math.radians(12.0))))
    parts.append(box("FloorBook_1", (-0.58, 1.18, 0.105),
                     (0.30, 0.24, 0.05), book_green,
                     rot=(0.0, 0.0, math.radians(-6.0))))

    for obj in parts:
        if obj.type == 'MESH':
            smart_uv_unwrap(obj)

    flipped = {o.name: check_winding(o) for o in parts if o.type == 'MESH'}
    print("LIB_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.35),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "040-magic-library-corner.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "040-magic-library-corner.blend"))

    export_wireframe_segments(
        parts, cam, os.path.join("/tmp", "library_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("LIB_POLY total=%d tris=%d quads=%d ngons=%d books_tall=%d "
          "books_low=%d" % (total, tris, quads, ngons, n_books, n_low))
    for name, c in counts.items():
        print("LIB_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "040-magic-library-corner.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 040 低模场景：魔法图书馆角落\n\n")
        f.write("低多边形魔法图书馆室内场景资产，平面着色（flat shading），"
                "干净拓扑。\n\n")
        f.write("## 结构\n\n")
        f.write("- 墙体：后墙（y=+2.2，5.4×2.6）+ 左墙（x=-2.2，4.6×2.6），"
                "上层灰泥、下层木护墙板 + 压条；木梁压顶 + 角柱\n")
        f.write("- 地面：8 块木地板（0.58 宽，灰度交错）\n")
        f.write("- 高书架：后墙 2.5 宽 × 2.35 高，5 层书格，"
                "共 %d 本书（红绿蓝紫棕青赭 7 色封面，12%% 斜靠、"
                "10%% 留空），第 3 层右端 3 本平放叠书\n" % n_books)
        f.write("- 矮书架：左墙 2.0 长 × 1.15 高，2 层书格，共 %d 本书；"
                "顶上地球仪（蓝球 + 金色子午环）\n" % n_low)
        f.write("- 图书馆梯子：两根立柱 + 6 根横档，向书架倾斜 17.7°\n")
        f.write("- 书桌：1.7×0.90 台面 + 4 腿 + 抽屉（黄铜拉手）+ 挡板；"
                "桌上翻开的蓝色法术书（两页微张 8°）、三臂黄铜烛台"
                "（3 支蜡烛 + 火焰）、墨水瓶 + 羽毛笔、3 本叠书、"
                "横放羊皮卷轴（两端木轴）\n")
        f.write("- 落地烛台：黄铜底座 + 1.28 高立柱 + 托盘，3 支蜡烛 + "
                "火焰，暖色点光源（180W）\n")
        f.write("- 墙饰：星图挂画（深蓝画布 + 金月 + 5 颗金星），"
                "位于书桌上方后墙\n")
        f.write("- 地毯 + 椅子：红色地毯（2.6×1.7，金色内边），"
                "木椅（座面 + 4 腿 + 靠背），位于书桌前方\n")
        f.write("- 地面散书：梯子旁 2 本平放的书\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Lib_Plaster：墙面灰泥；Lib_Wainscot：木护墙板；"
                "Lib_Shelf / Lib_Desk：书架 / 书桌木材\n")
        f.write("- Book_*：7 色书封（红绿蓝紫棕青赭）\n")
        f.write("- Lib_Brass / Lib_Gold：黄铜烛台、地球仪支架 / 金月金星\n")
        f.write("- Lib_Flame：火焰（Emission 橙，强度 4.0）+ "
                "FloorCandGlow 点光源（180W，暖色）\n")
        f.write("- Lib_Chart：星图深蓝画布；Lib_Globe：地球仪蓝球\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光 + "
                "落地烛台暖光，40mm 镜头\n")
        f.write("- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
