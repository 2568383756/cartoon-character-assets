from pathlib import Path
import bpy
import json
import struct
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / 'deliverables' / '卡通人物_已绑骨_优化.glb'
REVIEW = ROOT / 'review'
data = GLB.read_bytes()
magic, version, total_length = struct.unpack_from('<4sII', data, 0)
chunk_length, chunk_type = struct.unpack_from('<I4s', data, 12)
assert magic == b'glTF' and version == 2 and chunk_type == b'JSON'
gltf = json.loads(data[20:20 + chunk_length].decode('utf-8'))
structure = {
    'byte_length': total_length,
    'nodes': len(gltf.get('nodes', [])),
    'meshes': len(gltf.get('meshes', [])),
    'skins': [{'joint_count': len(skin.get('joints', []))} for skin in gltf.get('skins', [])],
    'animations': [{'name': item.get('name'), 'channels': len(item.get('channels', []))} for item in gltf.get('animations', [])],
    'materials': [material.get('name') for material in gltf.get('materials', [])],
    'images': len(gltf.get('images', [])),
    'extensions_used': gltf.get('extensionsUsed', []),
}
assert structure['skins'] and structure['skins'][0]['joint_count'] == 22
assert len(structure['animations']) == 1 and structure['images'] == 1
(REVIEW / 'optimized_glb_structure.json').write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding='utf-8')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(GLB))
scene = bpy.context.scene
scene.render.fps = 30
rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
character = next(obj for obj in scene.objects if obj.type == 'MESH')
action = next(action for action in bpy.data.actions if '绑定测试' in action.name)
rig.animation_data_create()
# Evaluate exactly one imported action; otherwise Blender's automatic NLA strip
# and the manually assigned action can make inspection poses ambiguous.
for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
unweighted = [vertex.index for vertex in character.data.vertices if not vertex.groups or sum(group.weight for group in vertex.groups) < 0.999]
if unweighted:
    raise RuntimeError(f'GLB 回导存在未绑定顶点：{unweighted[:20]}')
if not character.data.uv_layers:
    raise RuntimeError('GLB 回导缺少 UV')

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.6

def area(name, location, energy, size, target):
    light_data = bpy.data.lights.new(name, 'AREA')
    light_data.energy = energy
    light_data.shape = 'DISK'
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(target) - light.location).to_track_quat('-Z', 'Y').to_euler()

area('回导主光', (0.3, -0.8, 1.0), 35, 0.5, (0, -0.12, 0.45))
area('回导补光', (-0.4, -0.5, 0.4), 15, 0.4, (0, -0.12, 0.45))
camera_data = bpy.data.cameras.new('回导检查相机')
camera = bpy.data.objects.new('回导检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
scene.frame_set(1)
camera.location = (0, -0.85, 0.49)
camera.rotation_euler = (Vector((0, -0.12, 0.45)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.ortho_scale = 0.29
scene.render.filepath = str(REVIEW / 'optimized_glb_mouth.png')
bpy.ops.render.render(write_still=True)

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.003))
plane = bpy.context.object
material = bpy.data.materials.new('回导检查地面材质')
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)
area('回导全身主光', (1.5, -2.5, 3.0), 350, 2.5, (0, 0, 0.5))
area('回导全身轮廓光', (0.5, 2.0, 2.5), 400, 2.0, (0, 0, 0.5))
scene.render.resolution_x = 800
scene.render.resolution_y = 800
camera_data.ortho_scale = 1.28
pose_report = {}
for name, frame, location in (
    ('step_left', 56, (0, -3.5, 0.75)),
    ('step_right', 72, (0, -3.5, 0.75)),
    ('step_left_side', 56, (2.8, -1.8, 0.9)),
):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose_report[str(frame)] = {
        bone: list(rig.pose.bones[bone].head)
        for bone in ('hand_L', 'hand_R', 'foot_L', 'foot_R')
    }
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'optimized_glb_{name}.png')
    bpy.ops.render.render(write_still=True)

roundtrip = {
    'armature_bones': len(rig.data.bones),
    'mesh_vertices': len(character.data.vertices),
    'mesh_polygons': len(character.data.polygons),
    'uv_layers': [layer.name for layer in character.data.uv_layers],
    'unweighted_vertices': unweighted,
    'actions': [item.name for item in bpy.data.actions],
    'materials': [material.name for material in character.data.materials],
    'posed_bone_heads': pose_report,
}
(REVIEW / 'optimized_glb_roundtrip_report.json').write_text(json.dumps(roundtrip, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'structure': structure, 'roundtrip': roundtrip}, ensure_ascii=False, indent=2))
