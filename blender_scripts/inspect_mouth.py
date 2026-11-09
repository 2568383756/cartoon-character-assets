from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨.blend'))
scene = bpy.context.scene
scene.frame_set(1)
obj = next(o for o in scene.objects if o.type == 'MESH')
components = {}
attribute = obj.data.attributes.get('component_index')
for vertex in obj.data.vertices:
    component = attribute.data[vertex.index].value if attribute else 0
    components.setdefault(component, []).append(vertex.co.copy())
rows = []
for component, points in sorted(components.items()):
    rows.append({
        'component': component,
        'vertices': len(points),
        'min': [round(min(p[i] for p in points), 5) for i in range(3)],
        'max': [round(max(p[i] for p in points), 5) for i in range(3)],
        'center': [round(sum(p[i] for p in points) / len(points), 5) for i in range(3)],
    })
report = {'components': rows, 'polygons': len(obj.data.polygons), 'vertices': len(obj.data.vertices)}
(REVIEW / 'mouth_components.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

# Inspection cameras are temporary and never saved back into the character file.
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.6

def area(name, location, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -0.12, 0.45)) - light.location).to_track_quat('-Z', 'Y').to_euler()

area('嘴部检查主光', (0.3, -0.8, 1.0), 35, 0.5)
area('嘴部检查补光', (-0.4, -0.5, 0.4), 15, 0.4)
camera_data = bpy.data.cameras.new('嘴部检查相机')
camera = bpy.data.objects.new('嘴部检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (0, -0.85, 0.49)
target = Vector((0, -0.12, 0.45))
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.29
scene.render.filepath = str(REVIEW / 'mouth_closeup_before.png')
bpy.ops.render.render(write_still=True)

wire = obj.copy()
wire.data = obj.data.copy()
scene.collection.objects.link(wire)
wire.name = '嘴部检查线框_临时'
wire.parent = None
wire.modifiers.clear()
black = bpy.data.materials.new('嘴部检查线框黑色')
black.diffuse_color = (0.005, 0.005, 0.005, 1)
wire.data.materials.clear()
wire.data.materials.append(black)
modifier = wire.modifiers.new('实际网格边', 'WIREFRAME')
modifier.thickness = 0.00038
modifier.use_replace = True
modifier.use_even_offset = True
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'TEXTURE'
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.render.filepath = str(REVIEW / 'mouth_wire_before.png')
bpy.ops.render.render(write_still=True)
