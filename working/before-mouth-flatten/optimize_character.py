from pathlib import Path
import bpy
import bmesh
import json
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
REVIEW = ROOT / 'review'
SOURCE = OUT / '卡通人物_已绑骨.blend'
BLEND_PATH = OUT / '卡通人物_已绑骨_优化.blend'
GLB_PATH = OUT / '卡通人物_已绑骨_优化.glb'
# Trace the complete high-curvature lip boundary, including both corner vertices.
LIP_LOOP = [1440, 1439, 1438, 1437, 1399, 124, 135, 134, 132, 133, 126, 128, 130, 131, 2655, 2657, 2658, 2660, 2661, 2662, 2663, 2666, 3733, 3726, 3725, 3720]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.frame_set(1)
obj = next(o for o in scene.objects if o.type == 'MESH')
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
original = {'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons), 'edges': len(obj.data.edges)}

bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
loop = [bm.verts[index] for index in LIP_LOOP]
if len(set(loop)) != 26:
    raise RuntimeError('唇缘循环包含重复顶点，停止修改')
lip_edges = []
for index, vertex in enumerate(loop):
    target = loop[(index + 1) % len(loop)]
    edge = next((linked for linked in vertex.link_edges if target in linked.verts), None)
    if edge is None:
        raise RuntimeError(f'唇缘边不连续：{vertex.index} → {target.index}')
    lip_edges.append(edge)

# Cache coordinates because grid-fill subdivision may invalidate old BMVert handles.
loop_coordinates = [vertex.co.copy() for vertex in loop]
expected = []
for index, start in enumerate(loop_coordinates):
    end = loop_coordinates[(index + 1) % len(loop_coordinates)]
    before = loop_coordinates[(index - 1) % len(loop_coordinates)]
    after = loop_coordinates[(index + 2) % len(loop_coordinates)]
    midpoint = (start + end) * 0.5
    rounded = (-before + 9.0 * start + 9.0 * end - after) / 16.0
    expected.append((midpoint, rounded))

# Interpolate UVs, corner attributes and the deform layer while splitting.
result = bmesh.ops.subdivide_edges(bm, edges=lip_edges, cuts=1, use_grid_fill=True)
new_ring_vertices = [item for item in result['geom'] if isinstance(item, bmesh.types.BMVert)]
if len(new_ring_vertices) != len(loop_coordinates):
    raise RuntimeError(f'唇缘新增顶点数量异常：{len(new_ring_vertices)}，预期 {len(loop_coordinates)}')
unused = list(expected)
for vertex in new_ring_vertices:
    key, rounded = min(unused, key=lambda item: (item[0] - vertex.co).length_squared)
    if (key - vertex.co).length > 0.00001:
        raise RuntimeError('无法将新增顶点对应到唇缘边中点')
    vertex.co = rounded
    unused.remove((key, rounded))
loop_after = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in loop_coordinates]

# Add support around the lip fold and inside the oral cavity, not across the head.
def mouth_region(point):
    return abs(point.x) < 0.15 and point.y < -0.18 and 0.385 < point.z < 0.522

local_faces = [face for face in bm.faces if any(mouth_region(v.co) for v in face.verts)]
local_edges = set(edge for face in local_faces for edge in face.edges)
# Keep the newly rounded 52-segment lip loop intact while adding support.
ring_vertices = set(loop_after + new_ring_vertices)
ring_edges_after = {
    edge for vertex in ring_vertices for edge in vertex.link_edges
    if edge.other_vert(vertex) in ring_vertices
}
if len(ring_edges_after) != len(loop_coordinates) * 2:
    raise RuntimeError(f'加密后的唇缘不是连续 52 段：{len(ring_edges_after)}')
support_edges = [edge for edge in local_edges if edge not in ring_edges_after]
support_result = bmesh.ops.subdivide_edges(bm, edges=support_edges, cuts=1, use_grid_fill=True)

# Gentle relaxation is restricted to interior vertices, away from the lip silhouette.
interior = []
for vertex in bm.verts:
    p = vertex.co
    if vertex in ring_vertices:
        continue
    if abs(p.x) < 0.12 and -0.285 < p.y < -0.19 and 0.405 < p.z < 0.512:
        interior.append(vertex)
for _ in range(1):
    positions = {}
    for vertex in interior:
        neighbors = [edge.other_vert(vertex).co.copy() for edge in vertex.link_edges]
        if neighbors:
            average = sum(neighbors, Vector()) / len(neighbors)
            positions[vertex] = vertex.co.lerp(average, 0.12)
    for vertex, position in positions.items():
        vertex.co = position

bm.normal_update()
bm.to_mesh(obj.data)
bm.free()
obj.data.update()

# The source shorts reached the knee and were partly weighted to the shin.
# Keep the waistband anchored, transition down to the thighs, and remove the
# shin influences that otherwise create spikes at the enlarged walk poses.
def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)

component_attribute = obj.data.attributes.get('component_index')
if component_attribute is None:
    raise RuntimeError('缺少部件索引，无法安全修正裤腿权重')
hips_group = obj.vertex_groups['hips']
pants_vertices = 0
for vertex in obj.data.vertices:
    if component_attribute.data[vertex.index].value != 6:
        continue
    pants_vertices += 1
    side_blend = smoothstep((abs(vertex.co.x) - 0.015) / 0.07)
    down_blend = smoothstep((0.19 - vertex.co.z) / 0.065)
    thigh_weight = side_blend * down_blend
    thigh = obj.vertex_groups['thigh_L' if vertex.co.x > 0 else 'thigh_R']
    for group in list(obj.vertex_groups):
        group.remove([vertex.index])
    if thigh_weight < 0.999999:
        hips_group.add([vertex.index], 1.0 - thigh_weight, 'REPLACE')
    if thigh_weight > 0.000001:
        thigh.add([vertex.index], thigh_weight, 'REPLACE')

# Increase stride and counter-swing only at the two existing walk key poses.
action = rig.animation_data.action
for pose_bone in rig.pose.bones:
    pose_bone.rotation_mode = 'QUATERNION'

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
        pose_bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path='location', frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert(data_path='scale', frame=frame, group=pose_bone.name)

for frame, direction in ((56, 1), (72, -1)):
    scene.frame_set(frame)
    reset_pose()
    rotate_global('thigh_L', (1, 0, 0), -0.58 * direction)
    rotate_global('shin_L', (1, 0, 0), 0.58 * direction)
    rotate_global('thigh_R', (1, 0, 0), 0.48 * direction)
    rotate_global('shin_R', (1, 0, 0), -0.30 * direction)
    rotate_global('upper_arm_L', (1, 0, 0), 0.36 * direction)
    rotate_global('upper_arm_R', (1, 0, 0), -0.36 * direction)
    rotate_global('ribbon_tail_L', (1, 0, 0), 0.16)
    rotate_global('ribbon_tail_R', (1, 0, 0), -0.12)
    key_pose(frame)
scene.frame_set(1)
reset_pose()

unweighted = []
invalid_weights = []
for vertex in obj.data.vertices:
    total = sum(group.weight for group in vertex.groups)
    if not vertex.groups or total < 0.999:
        unweighted.append(vertex.index)
    if total > 1.001:
        invalid_weights.append({'vertex': vertex.index, 'sum': total})
if unweighted or invalid_weights:
    raise RuntimeError(f'蒙皮权重检查失败：unweighted={unweighted[:20]}, invalid={invalid_weights[:20]}')
if not obj.data.uv_layers:
    raise RuntimeError('网格缺少 UV，停止导出')
for material in obj.data.materials:
    if material:
        material.name = '卡通人物 · 主贴图'

readme = bpy.data.texts.get('绑骨说明') or bpy.data.texts.new('绑骨说明')
readme.clear()
readme.write('卡通人物基础绑定 · 局部优化版\n\n来源：用户提供的 FBX，保留原主贴图与 UV。\n骨架：22 根骨骼，前方 -Y，+X 为角色左侧。\n嘴部：唇缘由 26 段加密为 52 段，唇缘邻接面与口腔内部局部增加支撑边；不是全脸重拓扑。\n动作：绑定测试_挥手与步伐，1–96 帧，30 fps；56、72 帧加大跨步和反向摆臂。\n未拆分：手指骨骼、精细面部表情、IK 控制器。\n原始文件及上一版绑定文件均未覆盖。\n')

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
bpy.ops.export_scene.gltf(
    filepath=str(GLB_PATH), export_format='GLB', use_selection=True,
    export_animations=True, export_skins=True, export_yup=True,
    export_apply=True, export_materials='EXPORT', export_image_format='AUTO',
)

report = {
    'source_blend': str(SOURCE), 'blend': str(BLEND_PATH), 'glb': str(GLB_PATH),
    'original': original,
    'optimized': {'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons), 'edges': len(obj.data.edges)},
    'lip_loop_original_segments': len(loop), 'lip_loop_optimized_segments': len(loop) * 2,
    'support_edges_subdivided': len(support_edges), 'interior_vertices_relaxed': len(interior),
    'uv_layers': [layer.name for layer in obj.data.uv_layers],
    'unweighted_vertices': unweighted, 'invalid_weight_sums': invalid_weights,
    'bone_count': len(rig.pose.bones), 'action': action.name,
    'pants_vertices_reweighted': pants_vertices,
    'walk_keys': {
        '56': {'thigh_L': -0.58, 'shin_L': 0.58, 'thigh_R': 0.48, 'shin_R': -0.30, 'upper_arm_L': 0.36, 'upper_arm_R': -0.36},
        '72': {'thigh_L': 0.58, 'shin_L': -0.58, 'thigh_R': -0.48, 'shin_R': 0.30, 'upper_arm_L': -0.36, 'upper_arm_R': 0.36},
    },
}
(REVIEW / 'optimization_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# Inspection-only cameras, lights and wire copy are added after saving/exporting.
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
background.inputs['Strength'].default_value = 0.6

def area(name, location, energy, size, target=(0, -0.12, 0.45)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(target) - light.location).to_track_quat('-Z', 'Y').to_euler()

area('优化检查主光', (0.3, -0.8, 1.0), 35, 0.5)
area('优化检查补光', (-0.4, -0.5, 0.4), 15, 0.4)
camera_data = bpy.data.cameras.new('优化检查相机')
camera = bpy.data.objects.new('优化检查相机', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
scene.frame_set(1)
camera.location = (0, -0.85, 0.49)
camera.rotation_euler = (Vector((0, -0.12, 0.45)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.ortho_scale = 0.29
scene.render.filepath = str(REVIEW / 'mouth_closeup_after.png')
bpy.ops.render.render(write_still=True)

wire = obj.copy()
wire.data = obj.data.copy()
scene.collection.objects.link(wire)
wire.name = '嘴部优化检查线框_临时'
wire.parent = None
wire.modifiers.clear()
black = bpy.data.materials.new('嘴部优化检查线框黑色')
black.diffuse_color = (0.005, 0.005, 0.005, 1)
wire.data.materials.clear()
wire.data.materials.append(black)
modifier = wire.modifiers.new('实际网格边', 'WIREFRAME')
modifier.thickness = 0.00020
modifier.use_replace = True
modifier.use_even_offset = True
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.render.filepath = str(REVIEW / 'mouth_wire_after.png')
bpy.ops.render.render(write_still=True)
wire.hide_render = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 800
scene.render.resolution_y = 800
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.003))
plane = bpy.context.object
plane.name = '优化检查用地面'
plane_mat = bpy.data.materials.new('优化检查用地面材质')
plane_mat.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(plane_mat)
area('全身检查主光', (1.5, -2.5, 3.0), 350, 2.5, (0, 0, 0.5))
area('全身检查轮廓光', (0.5, 2.0, 2.5), 400, 2.0, (0, 0, 0.5))
camera_data.ortho_scale = 1.28
for name, frame, location in (
    ('rest', 1, (2.4, -3.2, 1.6)),
    ('step_left', 56, (0, -3.5, 0.75)),
    ('step_right', 72, (0, -3.5, 0.75)),
    ('step_left_side', 56, (2.8, -1.8, 0.9)),
):
    scene.frame_set(frame)
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'optimized_{name}.png')
    bpy.ops.render.render(write_still=True)

print(json.dumps(report, ensure_ascii=False, indent=2))
