# -*- coding: utf-8 -*-
"""044 低模游戏道具：魔法水晶球（Magic Crystal Ball）
Low-poly game magic crystal ball: a dark-wood pedestal base with brass
trim, carved brass petals and studs, four claw prongs cradling a
transmissive crystal sphere; a tilted brass rune ring with eight rune
tablets orbits the sphere, and a violet glow core + sparkle gem sit
inside the ball. Game-asset standard, flat shading.
Overall ~0.55 m wide x ~0.62 m tall (sphere center z 0.34, r 0.16).
Eevee beauty + wireframe renders, .blend + note.
Run: blender --background --python 044-lowpoly-crystal-ball.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
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
    """Cylinder (with end caps) between two points."""
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


def tapered_cyl_z(name, z0, z1, r0, r1, sides, mat):
    """Vertical tapered cylinder (with end caps) along Z."""
    verts = []
    for z, r in ((z0, r0), (z1, r1)):
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append((r * math.cos(ang), r * math.sin(ang), z))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    c0 = len(verts)
    verts.append((0, 0, z0))
    c1 = len(verts)
    verts.append((0, 0, z1))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((c0, j, i))
        faces.append((c1, sides + i, sides + j))
    return mesh_from_data(name, verts, faces, mat)


def torus_xy(name, center, R, r, arc_segments, tube_segments, mat):
    """Torus ring lying flat in the XY plane, centered at `center`.
    Closed tube, no caps needed."""
    cx, cy, cz = center
    verts = []
    for i in range(arc_segments):
        th = 2.0 * math.pi * i / arc_segments
        rx, ry = math.cos(th), math.sin(th)
        for j in range(tube_segments):
            ph = 2.0 * math.pi * j / tube_segments
            verts.append((cx + (R + r * math.cos(ph)) * rx,
                          cy + (R + r * math.cos(ph)) * ry,
                          cz + r * math.sin(ph)))
    faces = []
    for i in range(arc_segments):
        ni = (i + 1) % arc_segments
        for j in range(tube_segments):
            k = (j + 1) % tube_segments
            faces.append((i * tube_segments + j, ni * tube_segments + j,
                          ni * tube_segments + k, i * tube_segments + k))
    return mesh_from_data(name, verts, faces, mat)


def crystal_material(name):
    """Crystal ball: alpha-blended glass. Transmission in Eevee renders
    the world background through the ball and hides the emissive glow
    core inside (first render: milky opaque sphere, no violet glow
    visible), so use a transparent Principled mix instead — the inner
    glow and sparkle show through reliably."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.60, 0.66, 1.0, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.08
    bsdf.inputs["Alpha"].default_value = 0.35
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        mat.blend_method = 'BLEND'
    return mat


def emissive_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


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
    """Count faces whose normal points inward (dot with the vector from
    the mesh centroid to the face center is negative)."""
    import bmesh
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


def check_torus_winding_xy(obj, R, center):
    """Winding check for a flat ring: compare each face normal with the
    direction from the nearest point on the ring centerline to the face
    center. Must run while the torus is still unrotated in the XY plane."""
    import bmesh
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    flipped = 0
    cx, cy, cz = center
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal).normalized()
        c = mw @ f.calc_center_median()
        dx, dy = c.x - cx, c.y - cy
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nearest = Vector((cx + R * dx / L, cy + R * dy / L, cz))
        if n.dot((c - nearest).normalized()) < -0.001:
            flipped += 1
    bm.free()
    return flipped


def main():
    clear_scene()
    make_world_gradient()
    add_ground()
    studio_lights(target=(0, 0, 0.3))

    wood = solid_material("Ball_Wood", (0.34, 0.21, 0.11),
                          metallic=0.0, roughness=0.75)
    wood_dark = solid_material("Ball_WoodDark", (0.22, 0.13, 0.07),
                               metallic=0.0, roughness=0.8)
    brass = solid_material("Ball_Brass", (0.68, 0.50, 0.18),
                           metallic=0.9, roughness=0.35)
    brass_dark = solid_material("Ball_BrassDark", (0.50, 0.36, 0.13),
                                metallic=0.85, roughness=0.45)
    crystal = crystal_material("Ball_Crystal")
    glow = emissive_material("Ball_GlowCore", (0.55, 0.35, 1.0), 4.0)
    sparkle = emissive_material("Ball_Sparkle", (0.95, 0.9, 1.0), 6.0)

    parts = []
    flipped = {}

    # --- base: bottom plinth, z 0-0.03, r 0.24 -> 0.22 ---
    parts.append(tapered_cyl_z("Plinth", 0.0, 0.03, 0.24, 0.22, 24,
                               wood_dark))
    # --- brass trim ring on the plinth, z 0.03 ---
    trim = torus_xy("TrimRing", (0, 0, 0.03), 0.225, 0.008, 24, 6, brass)
    flipped[trim.name] = check_torus_winding_xy(trim, 0.225, (0, 0, 0.03))
    parts.append(trim)
    # --- base body: tapered, z 0.03-0.13, r 0.20 -> 0.16 ---
    parts.append(tapered_cyl_z("BaseBody", 0.03, 0.13, 0.20, 0.16, 24,
                               wood))
    # --- brass band at the top of the body, z 0.13 ---
    band = torus_xy("BaseBand", (0, 0, 0.13), 0.165, 0.007, 24, 6, brass)
    flipped[band.name] = check_torus_winding_xy(band, 0.165, (0, 0, 0.13))
    parts.append(band)
    # --- cup: flared rim holding the sphere, z 0.13-0.17, r 0.16 -> 0.185 ---
    parts.append(tapered_cyl_z("Cup", 0.13, 0.17, 0.16, 0.185, 24,
                               wood_dark))
    # --- cup lip torus, z 0.17 ---
    lip = torus_xy("CupLip", (0, 0, 0.17), 0.185, 0.010, 24, 6, brass)
    flipped[lip.name] = check_torus_winding_xy(lip, 0.185, (0, 0, 0.17))
    parts.append(lip)

    # --- carved petals: 8 brass leaves around the base body ---
    # NB: box() bakes absolute coords, so build the petal at the origin
    # and place it with a matrix (translate @ Rz(a) @ tilt-out 12 deg).
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        r = 0.185
        cx, cy = r * math.cos(a), r * math.sin(a)
        petal = box("Petal_%d" % (i + 1), (0, 0, 0),
                    (0.014, 0.055, 0.095), brass_dark)
        rot = Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(
            math.radians(12.0), 4, 'Y')
        petal.matrix_world = Matrix.Translation(
            (cx, cy, 0.08)) @ rot
        parts.append(petal)

    # --- studs: 12 hexagonal brass studs around the plinth edge ---
    for i in range(12):
        a = 2.0 * math.pi * i / 12.0
        r = 0.228
        x, y = r * math.cos(a), r * math.sin(a)
        stud = cyl_between("Stud_%02d" % (i + 1),
                           (x, y, 0.004), (x, y, 0.014), 0.009, 6, brass)
        parts.append(stud)

    # --- claw prongs: 4 brass claws from the cup rim up to the sphere ---
    for i in range(4):
        a = math.pi / 4.0 + i * math.pi / 2.0
        p0 = (0.170 * math.cos(a), 0.170 * math.sin(a), 0.155)
        p1 = (0.128 * math.cos(a), 0.128 * math.sin(a), 0.285)
        claw = cyl_between("Claw_%d" % (i + 1), p0, p1, 0.011, 6, brass)
        parts.append(claw)

    # --- crystal ball: UV sphere r 0.16, center z 0.34 ---
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12,
                                         radius=0.16,
                                         location=(0, 0, 0.34))
    ball = bpy.context.active_object
    ball.name = "CrystalBall"
    ball.data.materials.append(crystal)
    flat_shade(ball)
    parts.append(ball)

    # --- glow core inside the ball: r 0.09 emissive violet sphere ---
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8,
                                         radius=0.09,
                                         location=(0, 0, 0.34))
    core = bpy.context.active_object
    core.name = "GlowCore"
    core.data.materials.append(glow)
    flat_shade(core)
    parts.append(core)

    # --- sparkle gem: small icosahedron, bright, slightly above center ---
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.032,
                                          location=(0, 0, 0.375))
    gem = bpy.context.active_object
    gem.name = "SparkleGem"
    gem.data.materials.append(sparkle)
    flat_shade(gem)
    parts.append(gem)

    # --- rune ring: brass torus R 0.20 around the sphere, tilted 25 deg ---
    ring = torus_xy("RuneRing", (0, 0, 0), 0.20, 0.012, 32, 8, brass)
    flipped[ring.name] = check_torus_winding_xy(ring, 0.20, (0, 0, 0))
    ring.location = (0, 0, 0.34)
    ring.rotation_euler = (math.radians(25.0), 0, 0)
    parts.append(ring)

    # --- rune tablets: 8 small boxes parented to the ring, on its circle ---
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        tab = box("RuneTablet_%d" % (i + 1), (0, 0, 0),
                  (0.05, 0.008, 0.062), brass_dark)
        # local coords on the ring circle; tangential orientation
        tab.location = (0.20 * math.cos(a), 0.20 * math.sin(a), 0)
        tab.rotation_euler = (0, 0, a + math.pi / 2.0)
        tab.parent = ring
        parts.append(tab)

    for obj in parts:
        if obj.type == 'MESH' and obj.name not in (
                "CrystalBall", "GlowCore", "SparkleGem"):
            smart_uv_unwrap(obj)

    for o in parts:
        if o.type == 'MESH' and o.name not in flipped:
            flipped[o.name] = check_winding(o)
    print("BALL_WINDING:", flipped)

    cam = fit_camera_to_objects(parts, direction=(0.0, -1.0, 0.30),
                                lens=40.0, target_fill=0.78)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)

    render(os.path.join(ROOT, "renders", "044-lowpoly-crystal-ball.png"))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(ROOT, "scenes",
                              "044-lowpoly-crystal-ball.blend"))

    # wireframe overlay: structural parts only (skip the inner glow/gem,
    # they sit inside the transmissive ball)
    wire_parts = [o for o in parts if o.name not in ("GlowCore",
                                                     "SparkleGem")]
    export_wireframe_segments(
        wire_parts, cam, os.path.join("/tmp", "ball_wire.json"))

    counts = {o.name: poly_count(o) for o in parts if o.type == 'MESH'}
    total = total_poly_count(parts)
    tris = sum(1 for o in parts if o.type == 'MESH'
               for p in o.data.polygons if len(p.vertices) == 3)
    quads = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) == 4)
    ngons = sum(1 for o in parts if o.type == 'MESH'
                for p in o.data.polygons if len(p.vertices) > 4)
    print("BALL_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name, c in counts.items():
        print("BALL_POLY %s=%d" % (name, c))

    note = os.path.join(ROOT, "scenes", "044-lowpoly-crystal-ball.md")
    with open(note, "w", encoding="utf-8") as f:
        f.write("# 044 低模游戏道具：魔法水晶球\n\n")
        f.write("低多边形游戏道具资产，平面着色（flat shading），干净拓扑。"
                "水晶球置于雕花木底座上，符文环斜绕球体，3/4 俯视角度。\n\n")
        f.write("## 结构\n\n")
        f.write("- 底座底盘（Plinth）：锥形圆柱，z 0–0.03，r 0.24→0.22，"
                "24 段，深木色\n")
        f.write("- 底盘饰环（TrimRing）：黄铜圆环，z 0.03，R 0.225，"
                "管 r 0.008\n")
        f.write("- 底座身（BaseBody）：锥形圆柱，z 0.03–0.13，"
                "r 0.20→0.16，24 段，木色\n")
        f.write("- 底座箍带（BaseBand）：黄铜圆环，z 0.13，R 0.165，"
                "管 r 0.007\n")
        f.write("- 托杯（Cup）：外翻锥形圆柱，z 0.13–0.17，"
                "r 0.16→0.185，深木色\n")
        f.write("- 杯口唇缘（CupLip）：黄铜圆环，z 0.17，R 0.185，"
                "管 r 0.010\n")
        f.write("- 雕花叶瓣（Petal_1–8）：黄铜扁盒 0.014×0.055×0.095，"
                "绕底座身一圈，外倾 12°\n")
        f.write("- 底盘铆钉（Stud_01–12）：六边形黄铜柱，r 0.009，"
                "z 0.004–0.014，绕底盘边缘一圈\n")
        f.write("- 爪托（Claw_1–4）：黄铜锥形柱，r 0.011，6 段，"
                "从杯口（r 0.17，z 0.155）斜伸至球面（r 0.128，z 0.285）\n")
        f.write("- 水晶球（CrystalBall）：UV 球，r 0.16，球心 z 0.34，"
                "24×12 段；Principled 透明材质（alpha 0.35，BLEND，"
                "roughness 0.08，淡紫）——Eevee 透射会把球内辉光核"
                "遮成乳白实心球，改用透明混合后辉光可见\n")
        f.write("- 辉光核（GlowCore）：r 0.09 紫色自发光球，球心 z 0.34，"
                "强度 4.0，透过球体可见\n")
        f.write("- 闪光宝石（SparkleGem）：二十面体 r 0.032，z 0.375，"
                "白色自发光，强度 6.0\n")
        f.write("- 符文环（RuneRing）：黄铜圆环，R 0.20，管 r 0.012，"
                "绕球心 z 0.34，绕 X 轴倾 25°\n")
        f.write("- 符文牌（RuneTablet_1–8）：黄铜扁盒 0.05×0.008×0.062，"
                "以环为父级，均布于环上，切向排列\n")
        f.write("- 整体约 0.55 m 宽 × 0.62 m 高（球顶 z 0.50，"
                "符文环上缘约 z 0.56）\n\n")
        f.write("## 面数\n\n")
        f.write("- 总面数：%d（三角面 %d，四边面 %d，N-gon %d）\n"
                % (total, tris, quads, ngons))
        for name, c in counts.items():
            f.write("- %s：%d\n" % (name, c))
        f.write("\n## 绕向自检\n\n")
        f.write("圆环类部件用环中心线检测（符文环在倾斜前检测）；"
                "其余部件用质心检测。\n\n")
        for name, n in flipped.items():
            f.write("- %s：内翻面 %d\n" % (name, n))
        f.write("\n## 材质\n\n")
        f.write("- Ball_Wood：底座身木色（roughness 0.75）\n")
        f.write("- Ball_WoodDark：底盘/托杯深木色（roughness 0.8）\n")
        f.write("- Ball_Brass：饰环/箍带/杯口/爪托/符文环黄铜"
                "（metallic 0.9，roughness 0.35）\n")
        f.write("- Ball_BrassDark：雕花叶瓣/符文牌暗黄铜"
                "（metallic 0.85，roughness 0.45）\n")
        f.write("- Ball_Crystal：水晶球透明材质（alpha 0.35，BLEND，"
                "roughness 0.08）\n")
        f.write("- Ball_GlowCore：辉光核紫色自发光（强度 4.0）\n")
        f.write("- Ball_Sparkle：闪光宝石白色自发光（强度 6.0）\n\n")
        f.write("## 渲染\n\n")
        f.write("- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头\n")
        f.write("- 相机自动取景（fit_camera_to_objects，目标填充 78%）\n")
        f.write("- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定；"
                "辉光核与闪光宝石在球体内，不参与线框）\n")
    print("NOTE_WRITTEN:", note)


if __name__ == "__main__":
    main()
