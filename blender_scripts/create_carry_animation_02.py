from pathlib import Path
import bpy
import math
import json
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables"
REVIEW = ROOT / "review" / "character_02"
SOURCE = OUT / "红衣卡通女孩_已绑骨.blend"
BLEND_PATH = OUT / "红衣卡通女孩_搬运走路.blend"
GLB_PATH = OUT / "红衣卡通女孩_搬运走路.glb"

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == "MESH")
rig = next(o for o in scene.objects if o.type == "ARMATURE")
original_action = rig.animation_data.action
original_action.use_fake_user = True
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 65
for pose_bone in rig.pose.bones:
    pose_bone.rotation_mode = "QUATERNION"
action = bpy.data.actions.new("搬运走路_双手前举")
action.use_fake_user = True
rig.animation_data.action = action
rest_foot_rotations = {
    suffix: rig.data.bones[f"foot{suffix}"].matrix_local.to_quaternion().copy()
    for suffix in ("_L", "_R")
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
        pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path="location", frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path="scale", frame=frame, group=pose_bone.name)


def pose_at(frame):
    phase = (frame - 1) / 64 * math.tau
    c = math.cos(phase)
    s = math.sin(phase)
    reset_pose()

    # Symmetric forward carry pose: no walking counter-swing and no prop.
    for suffix, side in (("_L", 1), ("_R", -1)):
        rotate_global(f"upper_arm{suffix}", (1, 0, 0), -0.58 + 0.010 * math.sin(phase * 2))
        rotate_global(f"upper_arm{suffix}", (0, 1, 0), 0.30 * side)
        rotate_global(f"forearm{suffix}", (1, 0, 0), -0.68 - 0.008 * math.sin(phase * 2))
        rotate_global(f"forearm{suffix}", (0, 1, 0), 0.12 * side)
        rotate_global(f"hand{suffix}", (0, 1, 0), 0.10 * side)

    # A full but clothing-safe stride for this character's short legs.
    rotate_global("thigh_L", (1, 0, 0), -0.52 * c if c >= 0 else -0.44 * c)
    rotate_global("thigh_R", (1, 0, 0), 0.44 * c if c >= 0 else 0.52 * c)
    rotate_global("shin_L", (1, 0, 0), 0.40 * max(c, 0) - 0.16 * max(-c, 0) + 0.07 * abs(s))
    rotate_global("shin_R", (1, 0, 0), -0.16 * max(c, 0) + 0.40 * max(-c, 0) + 0.07 * abs(s))
    for suffix, side in (("_L", 1), ("_R", -1)):
        roll = Quaternion(Vector((1, 0, 0)), 0.045 * side * s)
        set_global_rotation(f"foot{suffix}", roll @ rest_foot_rotations[suffix])

    support_offset = 0.035 - min(rig.pose.bones["foot_L"].tail.z, rig.pose.bones["foot_R"].tail.z)
    bob = 0.0018 * math.cos(phase * 2)
    translate_global("hips", (0, 0, support_offset + bob))
    rotate_global("spine", (1, 0, 0), 0.030 + 0.006 * math.sin(phase * 2))
    rotate_global("chest", (0, 0, 1), 0.015 * s)
    rotate_global("head", (1, 0, 0), -0.015 + 0.008 * math.sin(phase * 2 + 0.3))
    rotate_global("pigtail_L", (1, 0, 0), 0.035 * math.sin(phase * 2 - 0.4))
    rotate_global("pigtail_R", (1, 0, 0), -0.035 * math.sin(phase * 2 + 0.4))
    rotate_global("ribbon_tail_L", (1, 0, 0), 0.075 + 0.045 * math.sin(phase * 2 - 0.5))
    rotate_global("ribbon_tail_R", (1, 0, 0), -0.065 + 0.040 * math.sin(phase * 2 + 0.4))
    key_pose(frame)


for frame in list(range(1, 66, 4)) + [65]:
    scene.frame_set(frame)
    pose_at(frame)
scene.frame_set(1)
reset_pose()
scene.frame_set(1)

readme = bpy.data.texts.get("绑骨说明") or bpy.data.texts.new("绑骨说明")
readme.write("\n\n新增动作：搬运走路_双手前举\n1–65 帧，30 fps，64 帧无缝循环。双手在胸腹前方保持托举姿态，不生成道具；双腿交替迈步，加入髋部落地补偿、躯干稳定、发髻和飘带随动。原绑定测试动作保留。\n")

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
bpy.ops.export_scene.gltf(
    filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
    export_animations=True, export_animation_mode="ACTIONS",
    export_skins=True, export_yup=True, export_apply=True,
    export_materials="EXPORT", export_image_format="AUTO",
)
report = {
    "source": str(SOURCE), "blend": str(BLEND_PATH), "glb": str(GLB_PATH),
    "original_action_preserved": original_action.name, "carry_action": action.name,
    "frame_range": [1, 65], "fps": 30, "duration_seconds": 64 / 30,
    "bone_count": len(rig.pose.bones), "prop_added": False,
    "arm_pose": {"upper_arm_forward_rad": -0.58, "forearm_additional_forward_rad": -0.68},
    "leg_amplitude_rad": {"forward": 0.52, "backward": 0.44},
}
(REVIEW / "carry_animation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

# Inspection studio is added only after saving the deliverable files.
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("红衣女孩搬运动作检查环境")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background") if scene.world.node_tree else None
if background:
    background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
    background.inputs["Strength"].default_value = 0.55
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.004))
plane = bpy.context.object
plane.name = "红衣女孩搬运检查地面"
plane_mat = bpy.data.materials.new("红衣女孩搬运检查地面材质")
plane_mat.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(plane_mat)


def area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -0.04, 0.50)) - light.location).to_track_quat("-Z", "Y").to_euler()


area("红衣女孩搬运主光", (1.5, -2.5, 3.0), 350, 2.5, (1.0, 0.88, 0.76))
area("红衣女孩搬运补光", (-2.0, -1.0, 1.8), 230, 2.0, (0.74, 0.85, 1.0))
area("红衣女孩搬运轮廓光", (0.5, 2.0, 2.5), 400, 2.0, (0.86, 0.92, 1.0))
camera_data = bpy.data.cameras.new("红衣女孩搬运检查相机")
camera = bpy.data.objects.new("红衣女孩搬运检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 1.28
views = [
    ("front", (0, -3.5, 0.75)),
    ("three_quarter", (2.4, -3.2, 1.5)),
    ("side", (3.4, -0.15, 0.9)),
    ("back", (0, 3.5, 0.9)),
]
for frame in (1, 17, 33, 49):
    scene.frame_set(frame)
    for label, location in views:
        camera.location = location
        camera.rotation_euler = (Vector((0, -0.04, 0.50)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(REVIEW / f"carry02_{label}_{frame:02d}.png")
        bpy.ops.render.render(write_still=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
