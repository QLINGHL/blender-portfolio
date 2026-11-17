# -*- coding: utf-8 -*-
"""009 补渲 top45：把地面从 12 放大到 30，避免高角度俯视时地面边缘
穿帮进画面，只重渲 top45 一张，不动其他三张。
Run: blender --background --python 009-fix-top45.py
"""
import os
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLEND = os.path.join(ROOT, "scenes", "009-multi-object-training-data.blend")

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
ground = scene.objects["Ground"]
ground.dimensions = (30.0, 30.0, 0.0)

cam = scene.camera
loc = (4.6, -4.6, 6.0)
target = (0.0, 0.0, 1.2)
cam.location = Vector(loc)
direction = Vector(target) - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.filepath = "/tmp/view009_top45.png"
bpy.ops.render.render(write_still=True)
print("TOP45_RERENDERED")

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("BLEND_SAVED:", BLEND)
