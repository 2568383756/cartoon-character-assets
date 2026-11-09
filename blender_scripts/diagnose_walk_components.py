from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨_优化.blend'))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
components = obj.data.attributes['component_index'].data
colors = {2: (0.9, 0.03, 0.03, 1), 6: (0.02, 0.08, 0.8, 1), 1: (0.95, 0.8, 0.02, 1), 22: (0.5, 0.02, 0.8, 1)}
materials = [obj.data.materials[0]]
slots = {}
for component, color in colors.items():
    material = bpy.data.materials.new(f'诊断部件_{component}')
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = next(node for node in material.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.8
    slots[component] = len(materials)
    materials.append(material)
obj.data.materials.clear()
for material in materials:
    obj.data.materials.append(material)
for polygon in obj.data.polygons:
    component = int(components[polygon.vertices[0]].value)
    polygon.material_index = slots.get(component, 0)
for index, material in enumerate(materials):
    if index == 0:
        material.diffuse_color = (0.6, 0.6, 0.6, 1)
scene.render.engine = 'BLENDER_EEVEE'
scene.world.use_nodes = True
background = next(node for node in scene.world.node_tree.nodes if node.bl_idname == 'ShaderNodeBackground')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.7
for name, location, energy in [('诊断主光', (0.8, -1.5, 1.5), 120), ('诊断补光', (-0.8, 0.5, 1.0), 80)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = 1.2
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 0.19)) - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camera_data = bpy.data.cameras.new('诊断相机')
camera = bpy.data.objects.new('诊断相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.48
for label, location in [('front', (0, -2.5, 0.35)), ('side', (2.5, -0.8, 0.4)), ('back', (0, 2.5, 0.35))]:
    scene.frame_set(56)
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.19)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(ROOT / 'review' / f'walk_components_{label}.png')
    bpy.ops.render.render(write_still=True)
print(slots)
