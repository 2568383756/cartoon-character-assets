from pathlib import Path
import bpy
import math
import json
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "working" / "model_fbx.blend"))
obj = next(item for item in bpy.context.scene.objects if item.type == "MESH")
obj.name = "卡通人物"
obj.data.name = "卡通人物_FBX网格"
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
obj.rotation_euler.z = -math.pi / 2
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for material in obj.data.materials:
    if material:
        material.name = "卡通人物 · 主贴图"

adjacency = [[] for _ in obj.data.vertices]
for edge in obj.data.edges:
    a, b = edge.vertices
    adjacency[a].append(b)
    adjacency[b].append(a)
remaining = set(range(len(obj.data.vertices)))
components = []
while remaining:
    seed = remaining.pop()
    stack = [seed]
    indices = [seed]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
                indices.append(neighbor)
    components.append(indices)
components.sort(key=len, reverse=True)
component_of = [0] * len(obj.data.vertices)
attribute = obj.data.attributes.get("component_index") or obj.data.attributes.new("component_index", "INT", "POINT")
for component, indices in enumerate(components):
    for index in indices:
        component_of[index] = component
        attribute.data[index].value = component

bones = {
    "root": ((0, 0, 0), (0, 0, 0.10), None),
    "hips": ((0, 0, 0.16), (0, 0, 0.24), "root"),
    "spine": ((0, 0, 0.24), (0, 0, 0.33), "hips"),
    "chest": ((0, 0, 0.33), (0, 0, 0.40), "spine"),
    "neck": ((0, 0, 0.40), (0, 0, 0.45), "chest"),
    "head": ((0, -0.015, 0.45), (0, 0, 0.82), "neck"),
}
for suffix, side in (("_L", 1), ("_R", -1)):
    bones[f"upper_arm{suffix}"] = ((side * 0.075, 0, 0.34), (side * 0.175, -0.015, 0.265), "chest")
    bones[f"forearm{suffix}"] = ((side * 0.175, -0.015, 0.265), (side * 0.225, -0.04, 0.19), f"upper_arm{suffix}")
    bones[f"hand{suffix}"] = ((side * 0.225, -0.04, 0.19), (side * 0.225, -0.065, 0.135), f"forearm{suffix}")
    bones[f"thigh{suffix}"] = ((side * 0.075, 0, 0.19), (side * 0.09, -0.005, 0.11), "hips")
    bones[f"shin{suffix}"] = ((side * 0.09, -0.005, 0.11), (side * 0.10, -0.025, 0.05), f"thigh{suffix}")
    bones[f"foot{suffix}"] = ((side * 0.10, -0.025, 0.05), (side * 0.10, -0.15, 0.025), f"shin{suffix}")
    bones[f"ribbon{suffix}"] = ((side * 0.03, 0.19, 0.46), (side * 0.28, 0.22, 0.43), "head")
    bones[f"ribbon_tail{suffix}"] = ((side * 0.035, 0.20, 0.43), (side * 0.13, 0.24, 0.29), "head")

arm_data = bpy.data.armatures.new("卡通人物_骨架")
rig = bpy.data.objects.new("Rig_卡通人物", arm_data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, (head, tail, parent) in bones.items():
    bone = arm_data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if parent:
        bone.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
arm_data.display_type = "OCTAHEDRAL"
rig.show_in_front = True
rig["用途"] = "卡通人物基础全身骨架；+X 为角色左侧，前方为 -Y"
rig["骨骼数量"] = len(bones)

for group in list(obj.vertex_groups):
    obj.vertex_groups.remove(group)
groups = {name: obj.vertex_groups.new(name=name) for name in bones if name != "root"}

def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)

def normalized(weights):
    weights = {name: value for name, value in weights.items() if value > 0.000001}
    total = sum(weights.values())
    if total <= 0:
        return {"hips": 1.0}
    return {name: value / total for name, value in weights.items()}

def distance_to_segment(point, start, end):
    start, end = Vector(start), Vector(end)
    direction = end - start
    factor = max(0.0, min(1.0, (point - start).dot(direction) / direction.length_squared))
    return (point - (start + factor * direction)).length

def arm_weights(point, side):
    suffix = "_L" if side > 0 else "_R"
    segments = {
        f"upper_arm{suffix}": (bones[f"upper_arm{suffix}"][0], bones[f"upper_arm{suffix}"][1], 1.0),
        f"forearm{suffix}": (bones[f"forearm{suffix}"][0], bones[f"forearm{suffix}"][1], 1.0),
        f"hand{suffix}": (bones[f"hand{suffix}"][0], bones[f"hand{suffix}"][1], 1.0),
        "chest": ((0, 0, 0.35), bones[f"upper_arm{suffix}"][0], 0.32),
    }
    weights = {}
    for name, (start, end, multiplier) in segments.items():
        distance = distance_to_segment(point, start, end)
        weights[name] = multiplier / ((distance + 0.012) ** 6)
    return normalized(weights)

def torso_weights(point):
    spine_blend = smoothstep((point.z - 0.18) / 0.16)
    chest_blend = smoothstep((point.z - 0.30) / 0.085)
    return normalized({
        "hips": 1.0 - spine_blend,
        "spine": spine_blend * (1.0 - chest_blend),
        "chest": spine_blend * chest_blend,
    })

def head_weights(point):
    head_blend = smoothstep((point.z - 0.395) / 0.065)
    return normalized({"chest": (1.0 - head_blend) * 0.20, "neck": (1.0 - head_blend) * 0.80, "head": head_blend})

def shorts_weights(point):
    side = 1 if point.x >= 0 else -1
    suffix = "_L" if side > 0 else "_R"
    side_blend = smoothstep((abs(point.x) - 0.015) / 0.07)
    shin_blend = smoothstep((0.16 - point.z) / 0.10)
    return normalized({
        "hips": 1.0 - side_blend,
        f"thigh{suffix}": side_blend * (1.0 - shin_blend),
        f"shin{suffix}": side_blend * shin_blend,
    })

def ribbon_weights(point, forced_side=None):
    side = forced_side if forced_side is not None else (1 if point.x >= 0 else -1)
    suffix = "_L" if side > 0 else "_R"
    side_blend = smoothstep((abs(point.x) - 0.025) / 0.10)
    if forced_side is not None:
        side_blend = 1.0
    tail_blend = 1.0 - smoothstep((point.z - 0.34) / 0.10)
    return normalized({
        "head": 1.0 - side_blend,
        f"ribbon{suffix}": side_blend * (1.0 - tail_blend),
        f"ribbon_tail{suffix}": side_blend * tail_blend,
    })

for vertex in obj.data.vertices:
    point = vertex.co
    component = component_of[vertex.index]
    if component == 0:
        weights = head_weights(point)
    elif component == 1:
        weights = ribbon_weights(point)
    elif component in (2, 22):
        weights = torso_weights(point)
    elif component in (3, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20):
        weights = {"head": 1.0}
    elif component in (4, 5):
        weights = {f"foot{'_L' if point.x > 0 else '_R'}": 1.0}
    elif component == 6:
        weights = shorts_weights(point)
    elif component in (7, 8):
        weights = {f"hand{'_L' if point.x > 0 else '_R'}": 1.0}
    elif component in (12, 13):
        weights = arm_weights(point, 1 if point.x > 0 else -1)
    elif component == 21:
        weights = ribbon_weights(point, 1 if point.x > 0 else -1)
    else:
        weights = {"hips": 1.0}
    for name, weight in normalized(weights).items():
        groups[name].add([vertex.index], weight, "REPLACE")

modifier = obj.modifiers.new("骨骼蒙皮", "ARMATURE")
modifier.object = rig
modifier.use_deform_preserve_volume = True
obj.parent = rig
obj.matrix_parent_inverse = Matrix.Identity(4)

rig.animation_data_create()
action = bpy.data.actions.new("绑定测试_挥手与步伐")
rig.animation_data.action = action
scene = bpy.context.scene
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 96
for pose_bone in rig.pose.bones:
    pose_bone.rotation_mode = "QUATERNION"

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

def key_pose(frame):
    for pose_bone in rig.pose.bones:
        pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path="location", frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path="scale", frame=frame, group=pose_bone.name)

for frame in (1, 12, 24, 40, 56, 72, 96):
    scene.frame_set(frame)
    reset_pose()
    if frame in (12, 24):
        rotate_global("upper_arm_L", (0, 1, 0), -0.72)
        rotate_global("forearm_L", (0, 1, 0), -0.18)
        rotate_global("hand_L", (0, 0, 1), 0.28 if frame == 12 else -0.20)
        rotate_global("head", (0, 1, 0), 0.12)
        rotate_global("ribbon_L", (1, 0, 0), 0.12)
        rotate_global("ribbon_tail_R", (1, 0, 0), -0.10)
    elif frame in (56, 72):
        direction = 1 if frame == 56 else -1
        rotate_global("thigh_L", (1, 0, 0), -0.42 * direction)
        rotate_global("shin_L", (1, 0, 0), 0.55 * direction)
        rotate_global("thigh_R", (1, 0, 0), 0.30 * direction)
        rotate_global("shin_R", (1, 0, 0), -0.20 * direction)
        rotate_global("upper_arm_L", (1, 0, 0), 0.20 * direction)
        rotate_global("upper_arm_R", (1, 0, 0), -0.20 * direction)
        rotate_global("ribbon_tail_L", (1, 0, 0), 0.16)
        rotate_global("ribbon_tail_R", (1, 0, 0), -0.12)
    key_pose(frame)
scene.frame_set(1)
reset_pose()

readme = bpy.data.texts.new("绑骨说明")
readme.write("卡通人物基础绑定\n\n来源：用户提供的 FBX，保留原网格、UV 与主贴图。\n骨架：22 根骨骼，前方 -Y，+X 为角色左侧。\n可动部位：躯干、头、双臂、双手、双腿、双脚、脑后发带。\n动作：绑定测试_挥手与步伐，1–96 帧，30 fps。\n未拆分：手指骨骼、精细面部表情、IK 控制器。\n原始文件未覆盖。\n")

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
blend_path = OUT / "卡通人物_已绑骨.blend"
glb_path = OUT / "卡通人物_已绑骨.glb"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.export_scene.gltf(
    filepath=str(glb_path),
    export_format="GLB",
    use_selection=True,
    export_animations=True,
    export_skins=True,
    export_yup=True,
    export_apply=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)

unweighted = []
influence_counts = []
for vertex in obj.data.vertices:
    total = sum(group.weight for group in vertex.groups)
    if total < 0.999:
        unweighted.append(vertex.index)
    influence_counts.append(len(vertex.groups))
report = {
    "source": "FBX",
    "vertices": len(obj.data.vertices),
    "polygons": len(obj.data.polygons),
    "connected_components": len(components),
    "bones": list(bones),
    "bone_count": len(bones),
    "unweighted_vertices": unweighted,
    "maximum_influences": max(influence_counts),
    "animation": action.name,
    "frame_range": [1, 96],
    "blend": str(blend_path),
    "glb": str(glb_path),
}
(REVIEW / "rig_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
background.inputs["Strength"].default_value = 0.5
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.003))
plane = bpy.context.object
plane.name = "检查用地面"
material = bpy.data.materials.new("检查用地面材质")
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)

def add_area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 0.5)) - light.location).to_track_quat("-Z", "Y").to_euler()

add_area("主光", (1.5, -2.5, 3.0), 350, 2.5, (1.0, 0.86, 0.72))
add_area("补光", (-2.0, -1.0, 1.8), 230, 2.0, (0.72, 0.84, 1.0))
add_area("轮廓光", (0.5, 2.0, 2.5), 400, 2.0, (0.85, 0.92, 1.0))
camera_data = bpy.data.cameras.new("检查相机")
camera = bpy.data.objects.new("检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 1.28
for name, frame, location in (
    ("rest", 1, (2.4, -3.2, 1.6)),
    ("wave", 12, (0, -3.5, 0.75)),
    ("step_left", 56, (2.4, -3.2, 1.6)),
    ("step_right", 72, (0, -3.5, 0.75)),
):
    scene.frame_set(frame)
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"rig_{name}.png")
    bpy.ops.render.render(write_still=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
