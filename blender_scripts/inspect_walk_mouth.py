from pathlib import Path
from collections import Counter
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review'
OUT = ROOT / 'deliverables'
LIP_LOOP = [1440, 1439, 1438, 1437, 1399, 124, 135, 134, 132, 133, 126, 128, 130, 131, 2655, 2657, 2658, 2660, 2661, 2662, 2663, 2666, 3733, 3726, 3725, 3720]

# Extract the exact source texture and mouth UV coordinates.
bpy.ops.wm.open_mainfile(filepath=str(OUT / '卡通人物_已绑骨.blend'))
source = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
uv_layer = source.data.uv_layers.active
mouth_uv = []
for index in LIP_LOOP:
    vertex = source.data.vertices[index]
    face_uvs = []
    for polygon in source.data.polygons:
        if index in polygon.vertices:
            for loop_index in polygon.loop_indices:
                if source.data.loops[loop_index].vertex_index == index:
                    face_uvs.append(list(uv_layer.data[loop_index].uv))
    mouth_uv.append({'index': index, 'co': list(vertex.co), 'uv': face_uvs})
images = []
for image in bpy.data.images:
    if image.type != 'IMAGE' or not image.has_data:
        continue
    target = REVIEW / f'source_texture_{image.name.replace("/", "_")}.png'
    image.filepath_raw = str(target)
    image.file_format = 'PNG'
    image.save()
    images.append({'name': image.name, 'size': list(image.size), 'path': str(target)})
components = Counter(int(item.value) for item in source.data.attributes['component_index'].data)
(REVIEW / 'mouth_uv_texture.json').write_text(json.dumps({'images': images, 'mouth_uv': mouth_uv, 'components': components}, ensure_ascii=False, indent=2), encoding='utf-8')

# Render intermediate walk poses, not just the two extreme keys.
bpy.ops.wm.open_mainfile(filepath=str(OUT / '卡通人物_已绑骨_优化.blend'))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 700
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.7

def area(name, location, energy, size, target):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(target) - light.location).to_track_quat('-Z', 'Y').to_euler()

area('步态检查主光', (0.8, -1.5, 1.5), 120, 1.2, (0, 0, 0.2))
area('步态检查补光', (-0.8, 0.5, 1.0), 80, 1.0, (0, 0, 0.2))
camera_data = bpy.data.cameras.new('步态检查相机')
camera = bpy.data.objects.new('步态检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.48
frames = [44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88]
for frame in frames:
    scene.frame_set(frame)
    camera.location = (0.65, -2.5, 0.48)
    target = Vector((0, 0, 0.19))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'walk_check_{frame:02d}.png')
    bpy.ops.render.render(write_still=True)

for frame in (56, 72):
    scene.frame_set(frame)
    camera.location = (-0.65, 2.5, 0.48)
    camera.rotation_euler = (Vector((0, 0, 0.19)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'walk_back_{frame}.png')
    bpy.ops.render.render(write_still=True)

print(json.dumps({'images': images, 'components': components, 'walk_frames': frames, 'back_closeups': [56, 72]}, ensure_ascii=False))
