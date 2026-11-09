from pathlib import Path
import bpy
import math
import json
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "character_02"
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "working" / "character_02_aligned.blend"))
obj = next(item for item in bpy.context.scene.objects if item.type == "MESH")
obj.name = "红衣卡通女孩"
obj.data.name = "红衣卡通女孩_FBX网格"
for material in obj.data.materials:
    if material:
        material.name = "红衣卡通女孩 · 主贴图"

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
    "root": ((0, 0, 0), (0, 0, 0.08), None),
    "hips": ((0, -0.015, 0.22), (0, -0.015, 0.30), "root"),
    "spine": ((0, -0.015, 0.30), (0, -0.020, 0.39), "hips"),
    "chest": ((0, -0.020, 0.39), (0, -0.020, 0.47), "spine"),
    "neck": ((0, -0.020, 0.47), (0, -0.020, 0.52), "chest"),
    "head": ((0, -0.020, 0.50), (0, -0.010, 0.94), "neck"),
}
for suffix, side in (("_L", 1), ("_R", -1)):
    bones[f"upper_arm{suffix}"] = ((side * 0.125, -0.025, 0.415), (side * 0.205, -0.040, 0.315), "chest")
    bones[f"forearm{suffix}"] = ((side * 0.205, -0.040, 0.315), (side * 0.265, -0.045, 0.230), f"upper_arm{suffix}")
    bones[f"hand{suffix}"] = ((side * 0.265, -0.045, 0.230), (side * 0.300, -0.060, 0.195), f"forearm{suffix}")
    bones[f"thigh{suffix}"] = ((side * 0.098, -0.016, 0.245), (side * 0.103, -0.020, 0.150), "hips")
    bones[f"shin{suffix}"] = ((side * 0.103, -0.020, 0.150), (side * 0.105, -0.030, 0.065), f"thigh{suffix}")
    bones[f"foot{suffix}"] = ((side * 0.105, -0.030, 0.065), (side * 0.105, -0.130, 0.035), f"shin{suffix}")
    bones[f"pigtail{suffix}"] = ((side * 0.275, 0.105, 0.620), (side * 0.435, 0.145, 0.535), "head")
    bones[f"ribbon_tail{suffix}"] = ((side * 0.290, 0.055, 0.620), (side * 0.315, 0.040, 0.425), "head")

arm_data = bpy.data.armatures.new("红衣卡通女孩_骨架")
rig = bpy.data.objects.new("Rig_红衣卡通女孩", arm_data)
bpy.context.scene.collection.objects.link(rig)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
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
rig["用途"] = "红衣卡通女孩全身绑定；按新模型实际比例定位，前方 -Y，角色左侧 +X"
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
    return {name: value / total for name, value in weights.items()} if total > 0 else {"hips": 1.0}


def distance_to_segment(point, start, end):
    start, end = Vector(start), Vector(end)
    direction = end - start
    factor = max(0.0, min(1.0, (point - start).dot(direction) / direction.length_squared))
    return (point - (start + factor * direction)).length


def arm_weights(point, side):
    suffix = "_L" if side > 0 else "_R"
    weights = {}
    segments = (
        (f"upper_arm{suffix}", 1.0),
        (f"forearm{suffix}", 1.0),
        (f"hand{suffix}", 0.75),
    )
    for name, multiplier in segments:
        start, end, _ = bones[name]
        distance = distance_to_segment(point, start, end)
        weights[name] = multiplier / ((distance + 0.007) ** 6)
    chest_start = bones["chest"][0]
    chest_end = bones[f"upper_arm{suffix}"][0]
    chest_distance = distance_to_segment(point, chest_start, chest_end)
    weights["chest"] = 0.30 / ((chest_distance + 0.010) ** 6)
    return normalized(weights)


def torso_weights(point):
    spine_blend = smoothstep((point.z - 0.245) / 0.13)
    chest_blend = smoothstep((point.z - 0.365) / 0.09)
    return normalized({
        "hips": 1.0 - spine_blend,
        "spine": spine_blend * (1.0 - chest_blend),
        "chest": spine_blend * chest_blend,
    })


def pants_weights(point):
    suffix = "_L" if point.x > 0 else "_R"
    shin_blend = smoothstep((0.175 - point.z) / 0.075)
    return normalized({f"thigh{suffix}": 1.0 - shin_blend, f"shin{suffix}": shin_blend})


head_components = {0, 4, 13, 14, 15, 16, 17, 22, 25, 26, 35, 38}
pigtail_components = {5, 7, 9, 10, 18, 19, 27, 28, 29, 30}
ribbon_components = {31, 32, 33, 34}
arm_components = {11, 12}
pants_components = {23, 24}
shoe_components = {2, 3}
hand_components = {6, 8}
for vertex in obj.data.vertices:
    point = vertex.co
    component = component_of[vertex.index]
    side = 1 if point.x > 0 else -1
    suffix = "_L" if side > 0 else "_R"
    if component in head_components:
        weights = {"head": 1.0}
    elif component in pigtail_components:
        weights = {f"pigtail{suffix}": 1.0}
    elif component in ribbon_components:
        weights = {f"ribbon_tail{suffix}": 1.0}
    elif component in arm_components:
        weights = arm_weights(point, side)
    elif component in pants_components:
        weights = pants_weights(point)
    elif component in shoe_components:
        weights = {f"foot{suffix}": 1.0}
    elif component in hand_components:
        weights = {f"hand{suffix}": 1.0}
    else:
        weights = torso_weights(point)
    for name, weight in normalized(weights).items():
        groups[name].add([vertex.index], weight, "REPLACE")

modifier = obj.modifiers.new("骨骼蒙皮", "ARMATURE")
modifier.object = rig
modifier.use_deform_preserve_volume = True
obj.parent = rig
obj.matrix_parent_inverse = Matrix.Identity(4)

rig.animation_data_create()
action = bpy.data.actions.new("绑定测试_挥手与步伐")
action.use_fake_user = True
rig.animation_data.action = action
scene = bpy.context.scene
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 65
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


for frame in (1, 17, 33, 49, 65):
    scene.frame_set(frame)
    reset_pose()
    if frame in (17, 33):
        rotate_global("upper_arm_L", (0, 1, 0), -0.65)
        rotate_global("forearm_L", (0, 1, 0), -0.15)
        rotate_global("head", (0, 1, 0), 0.10)
        rotate_global("pigtail_L", (1, 0, 0), 0.08)
        rotate_global("ribbon_tail_R", (1, 0, 0), -0.08)
    elif frame == 49:
        rotate_global("thigh_L", (1, 0, 0), -0.35)
        rotate_global("shin_L", (1, 0, 0), 0.28)
        rotate_global("thigh_R", (1, 0, 0), 0.30)
        rotate_global("shin_R", (1, 0, 0), -0.12)
    key_pose(frame)
scene.frame_set(1)
reset_pose()

readme = bpy.data.texts.new("绑骨说明")
readme.write("红衣卡通女孩基础绑定\n\n来源：用户提供的新 FBX，保留原网格、UV 与 4096×4096 主贴图。\n骨架：22 根骨骼，按新模型实际肩肘腕、髋膝踝与发髻位置设置，前方 -Y，角色左侧 +X。\n可动部位：躯干、头、双臂、双手、双腿、双脚、双发髻、双飘带。\n动作：绑定测试_挥手与步伐，1–65 帧，30 fps。\n未拆分：手指骨骼、精细面部表情、IK 控制器。\n原始文件与旧角色文件均未覆盖。\n")

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
blend_path = OUT / "红衣卡通女孩_已绑骨.blend"
glb_path = OUT / "红衣卡通女孩_已绑骨.glb"
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.export_scene.gltf(
    filepath=str(glb_path), export_format="GLB", use_selection=True,
    export_animations=True, export_animation_mode="ACTIONS",
    export_skins=True, export_yup=True, export_apply=True,
    export_materials="EXPORT", export_image_format="AUTO",
)

unweighted = [vertex.index for vertex in obj.data.vertices if sum(group.weight for group in vertex.groups) < 0.999]
report = {
    "source": "新 FBX",
    "vertices": len(obj.data.vertices),
    "polygons": len(obj.data.polygons),
    "connected_components": len(components),
    "bones": list(bones),
    "bone_count": len(bones),
    "unweighted_vertices": unweighted,
    "maximum_influences": max(len(vertex.groups) for vertex in obj.data.vertices),
    "animation": action.name,
    "frame_range": [1, 65],
    "component_mapping": {
        "head": sorted(head_components), "pigtails_and_bows": sorted(pigtail_components),
        "ribbon_tails": sorted(ribbon_components), "sleeves": sorted(arm_components),
        "pants": sorted(pants_components), "shoes": sorted(shoe_components), "hands": sorted(hand_components),
        "torso_dress_belt": sorted(set(range(len(components))) - head_components - pigtail_components - ribbon_components - arm_components - pants_components - shoe_components - hand_components),
    },
    "blend": str(blend_path), "glb": str(glb_path),
}
(REVIEW / "rig_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 850
scene.render.resolution_y = 850
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("红衣卡通女孩检查环境")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background") if scene.world.node_tree else None
if background:
    background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
    background.inputs["Strength"].default_value = 0.55
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.004))
plane = bpy.context.object
plane.name = "新角色检查用地面"
material = bpy.data.materials.new("新角色检查地面材质")
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)


def area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 0.5)) - light.location).to_track_quat("-Z", "Y").to_euler()


area("新角色主光", (1.5, -2.5, 3.0), 350, 2.5, (1.0, 0.88, 0.76))
area("新角色补光", (-2.0, -1.0, 1.8), 230, 2.0, (0.74, 0.85, 1.0))
area("新角色轮廓光", (0.5, 2.0, 2.5), 400, 2.0, (0.86, 0.92, 1.0))
camera_data = bpy.data.cameras.new("新角色检查相机")
camera = bpy.data.objects.new("新角色检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 1.28
for label, frame, location in (
    ("rest_front", 1, (0, -3.5, 0.75)),
    ("rest_three_quarter", 1, (2.4, -3.2, 1.5)),
    ("rest_side", 1, (3.4, -0.15, 0.9)),
    ("rest_back", 1, (0, 3.5, 0.9)),
    ("wave", 17, (2.4, -3.2, 1.5)),
    ("step", 49, (2.4, -3.2, 1.5)),
):
    scene.frame_set(frame)
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"rig_{label}.png")
    bpy.ops.render.render(write_still=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
