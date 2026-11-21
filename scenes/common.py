# -*- coding: utf-8 -*-
"""Shared helpers for the blender-portfolio build scripts.
Blender 5.3, headless, Eevee. Import from the build scripts:
    import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import *
"""
import bpy
import math
from mathutils import Vector


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def solid_material(name, color, metallic=0.0, roughness=0.6):
    """Principled BSDF material with a flat base color."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def wireframe_material(name="WireframeMat", line_color=(0.08, 0.08, 0.10),
                       face_color=(0.96, 0.96, 0.97), size=1.0):
    """Emission material: light faces + dark wireframe lines (Wireframe node)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    wf = nt.nodes.new("ShaderNodeWireframe")
    wf.inputs["Size"].default_value = size
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*face_color, 1.0)
    ramp.color_ramp.elements[1].position = 0.02
    ramp.color_ramp.elements[1].color = (*line_color, 1.0)
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(wf.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_world_gradient(top=(0.90, 0.92, 0.95), bottom=(0.62, 0.66, 0.72),
                        strength=1.0):
    """Soft vertical gradient world background (top light, bottom darker)."""
    world = bpy.data.worlds.new("StudioWorld")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    texcoord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, math.radians(90.0), 0.0)
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = 'LINEAR'
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*bottom, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*top, 1.0)
    nt.links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bpy.context.scene.world = world
    return world


def add_ground(size=12.0, color=(0.72, 0.74, 0.78)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    mat = solid_material("GroundMat", color, metallic=0.0, roughness=0.95)
    plane.data.materials.append(mat)
    return plane


def studio_lights(target=(0, 0, 1.0)):
    """Three-point studio lighting (key / fill / rim) as area lights."""
    def _area(name, loc, energy, size, color=(1.0, 1.0, 1.0)):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        data.color = color
        data.use_shadow = True
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        _point_at(obj, Vector(target))
        return obj

    key = _area("KeyLight", (3.0, -3.5, 4.5), 900.0, 2.5)
    fill = _area("FillLight", (-3.5, -2.0, 2.0), 300.0, 3.0)
    rim = _area("RimLight", (0.5, 4.0, 3.5), 500.0, 2.0,
                color=(0.85, 0.90, 1.0))
    return key, fill, rim


def fit_camera_to_objects(objects, direction=(0.0, -1.0, 0.35), lens=40.0,
                           target_fill=0.78, name="Camera",
                           res_x=1024, res_y=1024):
    """Place the camera so the given objects fill ~target_fill of the frame.

    Root cause of the recurring '构图偏空' notes (025 战斧、026 提灯、030 弩):
    every build script hand-tuned a fixed camera position, so small props
    ended up occupying only a few percent of the 1024x1024 frame
    (measured: 025 fill 2.7%, 026 fill 3.5%, 030 fill 4.4%).
    This helper instead measures the real bounding box, projects it through
    the camera, and moves the camera along `direction` until the largest
    projected span equals target_fill. Ground plane is excluded.

    Aspect trap (found 2026-11-21 on 031): world_to_camera_view measures
    against the CURRENT render resolution. Build scripts call this helper
    before setup_render, when the resolution is still the factory default
    1920x1080 (16:9) — the narrower vertical FOV inflates the measured
    span, so the camera is pushed too far out (031: dist 5.89 instead of
    3.44, figure only ~44% of the square frame). The helper therefore
    applies res_x/res_y (default 1024x1024, the repo standard) while
    measuring, then restores the previous resolution.
    Returns the camera object.
    """
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    # Apply the measurement frame (restored at the end) so the result
    # does not depend on whether setup_render ran before this call.
    prev_res = (scene.render.resolution_x, scene.render.resolution_y,
                scene.render.resolution_percentage)
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    meshes = [o for o in objects
              if o.type == 'MESH' and o.name != 'Ground']
    if not meshes:
        raise ValueError("fit_camera_to_objects: no mesh objects to frame")
    # World-space bounding box of all meshes.
    corners = []
    for o in meshes:
        mw = o.matrix_world
        for c in o.bound_box:
            corners.append(mw @ Vector(c))
    center = sum(corners, Vector((0.0, 0.0, 0.0))) / len(corners)
    radius = max((c - center).length for c in corners)
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    # Horizontal/vertical FOV (36 mm sensor, square frame -> same both ways).
    import math as _math
    fov = 2.0 * _math.atan(18.0 / lens)
    direction = Vector(direction).normalized()
    dist = radius / _math.tan(fov / 2.0) * 1.2
    for _ in range(3):
        cam.location = center + direction * dist
        _point_at(cam, center)
        bpy.context.view_layer.update()
        xs, ys = [], []
        for c in corners:
            x, y, d = world_to_camera_view(scene, cam, c)
            if d < 0:
                continue
            xs.append(x)
            ys.append(y)
        if not xs:
            break
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if span <= 0:
            break
        new_dist = dist * span / target_fill
        if abs(new_dist - dist) / dist < 0.02:
            dist = new_dist
            break
        dist = new_dist
    cam.location = center + direction * dist
    _point_at(cam, center)
    bpy.context.view_layer.update()
    scene.render.resolution_x, scene.render.resolution_y, \
        scene.render.resolution_percentage = prev_res
    print("FIT_CAMERA: dist=%.2f target_fill=%.2f" % (dist, target_fill))
    return cam


def _point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def make_camera(name, location, target, lens=50.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(location)
    _point_at(cam, Vector(target))
    bpy.context.scene.camera = cam
    return cam


def flat_shade(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = False


def poly_count(obj):
    return len(obj.data.polygons)


def total_poly_count(objects):
    return sum(poly_count(o) for o in objects if o.type == 'MESH')


def setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024,
                 filepath='/tmp/render.png', samples=64):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = 'PNG'
    if engine == 'BLENDER_EEVEE':
        scene.eevee.taa_render_samples = samples
        scene.eevee.use_shadows = True
    return scene


def render(filepath):
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    print("RENDERED:", filepath)


def export_wireframe_segments(objects, camera, filepath):
    """Project the visible mesh edges to normalized 2D coords (top-left origin)
    and dump them as JSON. Used to draw a wireframe overlay in PIL.
    An edge is visible if at least one linked face is front-facing."""
    import bmesh
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    cam_pos = camera.matrix_world.translation
    segments = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        mw = obj.matrix_world
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        for e in bm.edges:
            visible = False
            for f in e.link_faces:
                n = (mw.to_3x3() @ f.normal).normalized()
                c = mw @ f.calc_center_median()
                if n.dot((cam_pos - c).normalized()) > 0.001:
                    visible = True
                    break
            if not visible:
                continue
            v0 = mw @ e.verts[0].co
            v1 = mw @ e.verts[1].co
            x0, y0, d0 = world_to_camera_view(scene, camera, v0)
            x1, y1, d1 = world_to_camera_view(scene, camera, v1)
            if d0 < 0 or d1 < 0:
                continue
            segments.append([round(x0, 4), round(1.0 - y0, 4),
                             round(x1, 4), round(1.0 - y1, 4)])
        bm.free()
    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(segments, f)
    print("WIREFRAME_SEGMENTS:", len(segments), "->", filepath)
    return segments
