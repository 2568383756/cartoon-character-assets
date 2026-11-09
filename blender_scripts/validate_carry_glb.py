from pathlib import Path
import bpy
import json
import struct
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / 'deliverables' / '卡通人物_搬运走路.glb'
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
assert len(structure['animations']) == 2, structure['animations']
assert any('搬运' in item['name'] for item in structure['animations'])
assert structure['images'] == 1
(REVIEW / 'carry_glb_structure.json').write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding='utf-8')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(GLB))
scene = bpy.context.scene
scene.render.fps = 30
rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
character = next(obj for obj in scene.objects if obj.type == 'MESH')
action = next(action for action in bpy.data.actions if '搬运' in action.name)
rig.animation_data_create()
for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
unweighted = [v.index for v in character.data.vertices if not v.groups or sum(g.weight for g in v.groups) < 0.999]
if unweighted:
    raise RuntimeError(f'GLB 回导存在未绑定顶点：{unweighted[:20]}')
if not character.data.uv_layers:
    raise RuntimeError('GLB 回导缺少 UV')

start = action.frame_range[0]
end = action.frame_range[1]
loop_start = {}
loop_end = {}
hand_positions = []
leg_poses = []
foot_min_z = []
for index in range(17):
    frame = start + (end - start) * index / 16
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    matrices = {bone.name: bone.matrix.copy() for bone in rig.pose.bones}
    if index == 0:
        loop_start = matrices
    if index == 16:
        loop_end = matrices
    hand_positions.append({
        'frame': frame,
        'left': list(rig.pose.bones['hand_L'].head),
        'right': list(rig.pose.bones['hand_R'].head),
    })
    leg_poses.append(tuple(round(v, 5) for row in rig.pose.bones['thigh_L'].matrix for v in row))
    foot_min_z.append(min(rig.pose.bones['foot_L'].tail.z, rig.pose.bones['foot_R'].tail.z))
loop_error = max(abs(loop_start[name][row][col] - loop_end[name][row][col]) for name in loop_start for row in range(4) for col in range(4))
left_series = [Vector(row['left']) for row in hand_positions]
right_series = [Vector(row['right']) for row in hand_positions]
hand_travel = {
    'left_m': max((point - left_series[0]).length for point in left_series),
    'right_m': max((point - right_series[0]).length for point in right_series),
}
if loop_error > 0.0002:
    raise RuntimeError(f'搬运循环首尾不一致：{loop_error}')
if len(set(leg_poses)) < 8:
    raise RuntimeError('腿部动作采样不足')

report = {
    'armature_bones': len(rig.data.bones),
    'mesh_vertices': len(character.data.vertices),
    'mesh_polygons': len(character.data.polygons),
    'uv_layers': [layer.name for layer in character.data.uv_layers],
    'unweighted_vertices': unweighted,
    'actions': [item.name for item in bpy.data.actions],
    'materials': [material.name for material in character.data.materials],
    'carry_action_frame_range': [start, end],
    'sampled_poses': 17,
    'unique_leg_poses': len(set(leg_poses)),
    'loop_matrix_max_error': loop_error,
    'hand_travel_from_start': hand_travel,
    'support_foot_tail_min_z_range_m': [min(foot_min_z), max(foot_min_z)],
    'prop_added': False,
}
(REVIEW / 'carry_glb_roundtrip_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# Render the actual re-imported GLB at the opposite stride extremes.
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 850
scene.render.resolution_y = 850
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.78, 0.82, 0.88, 1)
background.inputs['Strength'].default_value = 0.55
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.012))
plane = bpy.context.object
material = bpy.data.materials.new('搬运回导检查地面')
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)


def area(name, location, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -0.04, 0.47)) - light.location).to_track_quat('-Z', 'Y').to_euler()


area('搬运回导主光', (1.5, -2.5, 3.0), 350, 2.5)
area('搬运回导补光', (-2.0, -1.0, 1.8), 230, 2.0)
area('搬运回导轮廓光', (0.5, 2.0, 2.5), 400, 2.0)
camera_data = bpy.data.cameras.new('搬运回导检查相机')
camera = bpy.data.objects.new('搬运回导检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 1.25
for label, fraction, location in (
    ('left_three_quarter', 0.0, (2.4, -3.2, 1.5)),
    ('right_three_quarter', 0.5, (2.4, -3.2, 1.5)),
    ('right_side', 0.5, (3.4, -0.15, 0.9)),
):
    frame = start + (end - start) * fraction
    scene.frame_set(int(frame), subframe=frame - int(frame))
    camera.location = location
    camera.rotation_euler = (Vector((0, -0.04, 0.47)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'carry_glb_{label}.png')
    bpy.ops.render.render(write_still=True)

print(json.dumps({'structure': structure, 'roundtrip': report}, ensure_ascii=False, indent=2))
