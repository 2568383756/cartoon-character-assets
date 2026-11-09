from pathlib import Path
from collections import Counter, defaultdict
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
REVIEW = ROOT / 'review'
LIP_LOOP = [1440, 1439, 1438, 1437, 1399, 124, 135, 134, 132, 133, 126, 128, 130, 131, 2655, 2657, 2658, 2660, 2661, 2662, 2663, 2666, 3733, 3726, 3725, 3720]
bpy.ops.wm.open_mainfile(filepath=str(OUT / '卡通人物_已绑骨.blend'))
source = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
outline = [(source.data.vertices[i].co.x, source.data.vertices[i].co.z) for i in LIP_LOOP]

def inside(x, z):
    result = False
    px, pz = outline[-1]
    for cx, cz in outline:
        if (cz > z) != (pz > z):
            cross = (px - cx) * (z - cz) / (pz - cz) + cx
            if x < cross:
                result = not result
        px, pz = cx, cz
    return result

bpy.ops.wm.open_mainfile(filepath=str(OUT / '卡通人物_已绑骨_优化.blend'))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
components = obj.data.attributes['component_index'].data
report = defaultdict(list)
for vertex in obj.data.vertices:
    p = vertex.co
    if abs(p.x) < 0.13 and p.y < -0.18 and 0.40 < p.z < 0.52 and inside(p.x, p.z):
        component = int(components[vertex.index].value)
        report[str(component)].append({'index': vertex.index, 'co': [round(v, 7) for v in p]})
summary = {key: {'count': len(items), 'min': [min(v['co'][axis] for v in items) for axis in range(3)], 'max': [max(v['co'][axis] for v in items) for axis in range(3)]} for key, items in report.items()}
materials = Counter()
for polygon in obj.data.polygons:
    center = polygon.center
    if -0.296 < center.y < -0.20 and inside(center.x, center.z):
        materials[obj.data.materials[polygon.material_index].name] += 1
(REVIEW / 'current_mouth_components.json').write_text(json.dumps({'summary': summary, 'materials': materials, 'vertices': report}, ensure_ascii=False, indent=2), encoding='utf-8')

palette = [(0.85, 0.08, 0.08, 1), (0.05, 0.75, 0.15, 1), (0.05, 0.25, 0.95, 1), (0.95, 0.65, 0.05, 1), (0.65, 0.1, 0.8, 1), (0.05, 0.75, 0.75, 1)]
slots = {}
for component in sorted(int(k) for k in report):
    material = bpy.data.materials.new(f'嘴部诊断部件_{component}')
    material.use_nodes = True
    color = palette[len(slots) % len(palette)]
    material.diffuse_color = color
    bsdf = next(node for node in material.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.8
    slots[component] = len(obj.data.materials)
    obj.data.materials.append(material)
for polygon in obj.data.polygons:
    component = int(components[polygon.vertices[0]].value)
    if component in slots:
        polygon.material_index = slots[component]
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.6
for name, location, energy, size in [('主光', (0.3, -0.8, 1.0), 35, 0.5), ('补光', (-0.4, -0.5, 0.4), 15, 0.4)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -0.12, 0.45)) - light.location).to_track_quat('-Z', 'Y').to_euler()
camera_data = bpy.data.cameras.new('嘴部诊断相机')
camera = bpy.data.objects.new('嘴部诊断相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.29
camera.location = (0, -0.85, 0.49)
camera.rotation_euler = (Vector((0, -0.12, 0.45)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(REVIEW / 'mouth_components_current.png')
bpy.ops.render.render(write_still=True)
print(json.dumps({'summary': summary, 'materials': materials}, ensure_ascii=False, indent=2))
