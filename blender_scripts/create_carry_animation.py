from pathlib import Path
import bpy
import math
import json
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
REVIEW = ROOT / 'review'
SOURCE = OUT / '卡通人物_已绑骨_优化.blend'
BLEND_PATH = OUT / '卡通人物_搬运走路.blend'
GLB_PATH = OUT / '卡通人物_搬运走路.glb'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
original_action = rig.animation_data.action
original_action.use_fake_user = True
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 65

for pose_bone in rig.pose.bones:
    pose_bone.rotation_mode = 'QUATERNION'

action = bpy.data.actions.new('搬运走路_双手前举')
action.use_fake_user = True
rig.animation_data.action = action


rest_foot_rotations = {
    suffix: rig.data.bones[f'foot{suffix}'].matrix_local.to_quaternion().copy()
    for suffix in ('_L', '_R')
}


def reset_pose():
    for pose_bone in rig.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def rotate_global(name, axis, angle):
    pose_bone = rig.pose.bones[name]
    matrix = pose_bone.matrix.copy()
    pivot = matrix.translation.copy()
    rotation = Quaternion(Vector(axis), angle).to_matrix().to_4x4()
    pose_bone.matrix = Matrix.Translation(pivot) @ rotation @ Matrix.Translation(-pivot) @ matrix
    bpy.context.view_layer.update()


def set_global_rotation(name, rotation):
    pose_bone = rig.pose.bones[name]
    matrix = pose_bone.matrix.copy()
    pivot = matrix.translation.copy()
    delta = rotation @ matrix.to_quaternion().inverted()
    pose_bone.matrix = Matrix.Translation(pivot) @ delta.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ matrix
    bpy.context.view_layer.update()


def translate_global(name, offset):
    pose_bone = rig.pose.bones[name]
    matrix = pose_bone.matrix.copy()
    matrix.translation += Vector(offset)
    pose_bone.matrix = matrix
    bpy.context.view_layer.update()


def key_pose(frame):
    for pose_bone in rig.pose.bones:
        pose_bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path='location', frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path='scale', frame=frame, group=pose_bone.name)


def pose_at(frame):
    phase = (frame - 1) / 64 * math.tau
    c = math.cos(phase)
    s = math.sin(phase)
    reset_pose()

    # Both hands stay in front of the torso to support an invisible object.
    # The two sides are deliberately symmetric; no walking counter-swing is applied.
    for suffix, side in (('_L', 1), ('_R', -1)):
        rotate_global(f'upper_arm{suffix}', (1, 0, 0), -0.48 + 0.012 * math.sin(phase * 2))
        rotate_global(f'upper_arm{suffix}', (0, 1, 0), 0.12 * side)
        rotate_global(f'forearm{suffix}', (1, 0, 0), -0.72 - 0.010 * math.sin(phase * 2))
        rotate_global(f'forearm{suffix}', (0, 1, 0), 0.06 * side)
        rotate_global(f'hand{suffix}', (0, 1, 0), 0.12 * side)

    # Enlarged in-place walk cycle. The final key repeats the first exactly.
    rotate_global('thigh_L', (1, 0, 0), -0.58 * c if c >= 0 else -0.48 * c)
    rotate_global('thigh_R', (1, 0, 0), 0.48 * c if c >= 0 else 0.58 * c)
    rotate_global('shin_L', (1, 0, 0), 0.45 * max(c, 0) - 0.18 * max(-c, 0) + 0.08 * abs(s))
    rotate_global('shin_R', (1, 0, 0), -0.18 * max(c, 0) + 0.45 * max(-c, 0) + 0.08 * abs(s))
    for suffix, side in (('_L', 1), ('_R', -1)):
        # Restore a near-level shoe in armature space instead of allowing the
        # accumulated thigh/shin rotation to present the whole sole forward.
        roll = Quaternion(Vector((1, 0, 0)), 0.055 * side * s)
        set_global_rotation(f'foot{suffix}', roll @ rest_foot_rotations[suffix])

    # Lower the pelvis just enough to keep the supporting shoe on the floor.
    # This removes the floating, high-stepping look without reducing stride.
    support_offset = 0.026 - min(rig.pose.bones['foot_L'].tail.z, rig.pose.bones['foot_R'].tail.z)
    bob = 0.002 * math.cos(phase * 2)
    translate_global('hips', (0, 0, support_offset + bob))
    rotate_global('spine', (1, 0, 0), 0.035 + 0.008 * math.sin(phase * 2))
    rotate_global('chest', (0, 0, 1), 0.018 * s)
    rotate_global('head', (1, 0, 0), -0.018 + 0.010 * math.sin(phase * 2 + 0.3))
    rotate_global('ribbon_tail_L', (1, 0, 0), 0.10 + 0.06 * math.sin(phase * 2 - 0.5))
    rotate_global('ribbon_tail_R', (1, 0, 0), -0.08 + 0.05 * math.sin(phase * 2 + 0.4))
    key_pose(frame)


for frame in list(range(1, 66, 4)) + [65]:
    scene.frame_set(frame)
    pose_at(frame)
scene.frame_set(1)
reset_pose()
scene.frame_set(1)

readme = bpy.data.texts.get('绑骨说明') or bpy.data.texts.new('绑骨说明')
readme.write('\n\n新增动作：搬运走路_双手前举\n1–65 帧，30 fps，64 帧无缝循环。双手在胸腹前方保持托举姿态，不生成道具；双腿保留较大跨步，加入轻微髋部起伏、躯干稳定和发带随动。原绑定测试动作保留。\n')

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
bpy.ops.export_scene.gltf(
    filepath=str(GLB_PATH), export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS',
    export_skins=True, export_yup=True, export_apply=True,
    export_materials='EXPORT', export_image_format='AUTO',
)

report = {
    'source': str(SOURCE), 'blend': str(BLEND_PATH), 'glb': str(GLB_PATH),
    'original_action_preserved': original_action.name,
    'carry_action': action.name,
    'frame_range': [1, 65], 'fps': 30, 'duration_seconds': 64 / 30,
    'bone_count': len(rig.pose.bones), 'prop_added': False,
    'arm_pose': {'upper_arm_forward_rad': -0.48, 'forearm_additional_forward_rad': -0.72},
    'leg_amplitude_rad': {'forward': 0.58, 'backward': 0.48},
}
(REVIEW / 'carry_animation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# Inspection-only studio setup is added after the native file and GLB are saved.
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.78, 0.82, 0.88, 1)
background.inputs['Strength'].default_value = 0.55
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.012))
plane = bpy.context.object
plane.name = '搬运动作检查用地面'
plane_mat = bpy.data.materials.new('搬运动作检查地面材质')
plane_mat.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(plane_mat)


def area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -0.05, 0.46)) - light.location).to_track_quat('-Z', 'Y').to_euler()


area('搬运检查主光', (1.5, -2.5, 3.0), 350, 2.5, (1.0, 0.86, 0.72))
area('搬运检查补光', (-2.0, -1.0, 1.8), 230, 2.0, (0.72, 0.84, 1.0))
area('搬运检查轮廓光', (0.5, 2.0, 2.5), 400, 2.0, (0.85, 0.92, 1.0))
camera_data = bpy.data.cameras.new('搬运动作检查相机')
camera = bpy.data.objects.new('搬运动作检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 1.25

views = [
    ('front', (0, -3.5, 0.75)),
    ('three_quarter', (2.4, -3.2, 1.5)),
    ('side', (3.4, -0.15, 0.9)),
    ('back', (0, 3.5, 0.9)),
]
for frame in (1, 17, 33, 49):
    scene.frame_set(frame)
    for label, location in views:
        camera.location = location
        camera.rotation_euler = (Vector((0, -0.04, 0.47)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(REVIEW / f'carry_{label}_{frame:02d}.png')
        bpy.ops.render.render(write_still=True)

print(json.dumps(report, ensure_ascii=False, indent=2))
