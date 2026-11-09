from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨_优化.blend'))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
attribute = obj.data.attributes['component_index']
palette = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d']
materials = []
for index, hex_color in enumerate(palette):
    rgb = tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    material = bpy.data.materials.new(f'诊断所有部件_{index:02d}')
    material.use_nodes = True
    material.diffuse_color = (*rgb, 1)
    bsdf = next(node for node in material.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled')
    for link in list(bsdf.inputs['Base Color'].links):
        material.node_tree.links.remove(link)
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = 0.75
    materials.append(material)
obj.data.materials.clear()
for material in materials:
    obj.data.materials.append(material)
report = {}
for component in range(23):
    vertices = [v for v in obj.data.vertices if int(attribute.data[v.index].value) == component]
    lower = [v for v in vertices if v.co.z < 0.24 and abs(v.co.x) < 0.25 and v.co.y < 0.02]
    report[str(component)] = {
        'count': len(vertices),
        'lower_front_count': len(lower),
        'lower_front': [{'index': v.index, 'co': [round(c, 6) for c in v.co], 'groups': {obj.vertex_groups[g.group].name: round(g.weight, 4) for g in v.groups}} for v in lower],
    }
for polygon in obj.data.polygons:
    polygon.material_index = int(attribute.data[polygon.vertices[0]].value)
(REVIEW / 'all_lower_components.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.7
for name, location, energy in [('主光', (0.8, -1.5, 1.5), 120), ('补光', (-0.8, 0.5, 1.0), 80)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = 1.2
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 0.19)) - light.location).to_track_quat('-Z', 'Y').to_euler()
camera_data = bpy.data.cameras.new('所有部件诊断相机')
camera = bpy.data.objects.new('所有部件诊断相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.48
for frame in (56, 72):
    scene.frame_set(frame)
    camera.location = (0.65, -2.5, 0.48)
    camera.rotation_euler = (Vector((0, 0, 0.19)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'all_lower_components_{frame}.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps({key: value['lower_front_count'] for key, value in report.items()}, ensure_ascii=False))
