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
rounded_vertices = [None] * len(loop_coordinates)
for vertex in new_ring_vertices:
    candidate_index, (key, rounded) = min(enumerate(unused), key=lambda item: (item[1][0] - vertex.co).length_squared)
    if (key - vertex.co).length > 0.00001:
        raise RuntimeError('无法将新增顶点对应到唇缘边中点')
    vertex.co = rounded
    edge_index = expected.index((key, rounded))
    rounded_vertices[edge_index] = vertex
    unused.pop(candidate_index)
loop_after = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in loop_coordinates]

# Add support around the lip fold and inside the oral cavity, not across the head.
def mouth_region(point):
    return abs(point.x) < 0.15 and point.y < -0.18 and 0.385 < point.z < 0.522

local_faces = [face for face in bm.faces if any(mouth_region(v.co) for v in face.verts)]
local_edges = set(edge for face in local_faces for edge in face.edges)
ordered_ring = []
for index, vertex in enumerate(loop_after):
    ordered_ring.extend((vertex, rounded_vertices[index]))
ring_vertices = set(ordered_ring)
ring_edges_after = {
    edge for vertex in ring_vertices for edge in vertex.link_edges
    if edge.other_vert(vertex) in ring_vertices
}
if len(ring_edges_after) != len(loop_coordinates) * 2:
    raise RuntimeError(f'加密后的唇缘不是连续 52 段：{len(ring_edges_after)}')
support_edges = [edge for edge in local_edges if edge not in ring_edges_after]
ordered_ring_coordinates = [vertex.co.copy() for vertex in ordered_ring]
support_result = bmesh.ops.subdivide_edges(bm, edges=support_edges, cuts=1, use_grid_fill=True)
# Subdividing neighboring support edges can invalidate the original BMVert handles.
ordered_ring = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in ordered_ring_coordinates]
ring_vertices = set(ordered_ring)
if len(ring_vertices) != len(ordered_ring_coordinates):
    raise RuntimeError('支撑边细分后无法完整恢复唇缘顶点')

# Relax the lip silhouette in all three axes to remove small angular kinks.
# This keeps the overall smile arc rather than collapsing it to a straight line.
for _ in range(3):
    ring_positions = {}
    for index, vertex in enumerate(ordered_ring):
        before = ordered_ring[(index - 1) % len(ordered_ring)].co
        after = ordered_ring[(index + 1) % len(ordered_ring)].co
        ring_positions[vertex] = vertex.co.lerp((before + after) * 0.5, 0.30)
    for vertex, position in ring_positions.items():
        vertex.co = position

# Fit one gentle quadratic depth surface across the lip and its outer skin.
# The previous ring-only operation can leave a ledge against the cheek. Here
# the blend fades with distance, while the oral cavity and tongue stay intact.
import numpy as np
outer_skin = [
    vertex for vertex in bm.verts
    if abs(vertex.co.x) < 0.14 and 0.39 < vertex.co.z < 0.54 and vertex.co.y < -0.275
]
outer_points = np.array([tuple(vertex.co) for vertex in outer_skin], dtype=float)
x = outer_points[:, 0]
z = outer_points[:, 2]
design = np.column_stack((np.ones(len(x)), x, z, x * x, x * z, z * z))
coefficients, _, _, _ = np.linalg.lstsq(design, outer_points[:, 1], rcond=None)
ring_xz = [Vector((vertex.co.x, vertex.co.z)) for vertex in ordered_ring]
outer_skin_flattened = 0
for vertex in outer_skin:
    p = vertex.co
    distance = min((Vector((p.x, p.z)) - point).length for point in ring_xz)
    blend = 0.94 * np.exp(-((distance / 0.048) ** 2))
    if abs(p.x) < 0.085 and p.z > 0.490:
        blend = max(blend, 0.94)
    fitted_y = float(np.dot([1.0, p.x, p.z, p.x * p.x, p.x * p.z, p.z * p.z], coefficients))
    p.y += (fitted_y - p.y) * float(blend)
    outer_skin_flattened += 1

# Relax the narrow transition around the lip. More support edges prevent long
# thin folds; the depth projection above handles the outer cheek transition.
lip_outline = [(point.x, point.z) for point in loop_coordinates]

def point_inside_outline(x, z, outline=lip_outline):
    inside = False
    previous_x, previous_z = outline[-1]
    for current_x, current_z in outline:
        if (current_z > z) != (previous_z > z):
            crossing_x = (previous_x - current_x) * (z - current_z) / (previous_z - current_z) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_z = current_x, current_z
    return inside

old_oral_faces = []
for face in bm.faces:
    center = face.calc_center_median()
    center_inside = (abs(center.x) < 0.12 and center.y < -0.19 and 0.405 < center.z < 0.512
            and point_inside_outline(center.x, center.z))
    touches_old_interior = any(
        vertex not in ring_vertices and abs(vertex.co.x) < 0.12 and vertex.co.y < -0.19
        and 0.405 < vertex.co.z < 0.512 and point_inside_outline(vertex.co.x, vertex.co.z)
        for vertex in face.verts
    )
    if center_inside or touches_old_interior:
        old_oral_faces.append(face)

# Replace the old folded cavity with one continuous radial surface. Select by
# face centre as well as position: some thin old wall faces cross the nominal
# outline and would otherwise remain attached to 14 of the 52 lip segments.
# Keep the complete lip rim and the outer cheek faces, then remove loose interior
# vertices before building three regular inner rings plus one centre vertex.
old_interior_vertices = len({vertex for face in old_oral_faces for vertex in face.verts if vertex not in ring_vertices})
old_interior_faces = len(old_oral_faces)
rim_coordinates = [vertex.co.copy() for vertex in ordered_ring]
bmesh.ops.delete(bm, geom=old_oral_faces, context='FACES')
ordered_ring = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in rim_coordinates]
# Fourteen upper-lip wall faces lie just above the original XZ outline. On each
# still-closed rim edge, remove only the face behind the rim (positive Y), never
# the more frontal cheek face. This preserves the outer lip transition.
trailing_oral_faces = set()
for index, vertex in enumerate(ordered_ring):
    following = ordered_ring[(index + 1) % len(ordered_ring)]
    edge = next((item for item in vertex.link_edges if following in item.verts), None)
    if edge is None or edge.is_boundary:
        continue
    rim_y = (vertex.co.y + following.co.y) * 0.5
    for face in edge.link_faces:
        if face.normal.y > 0.1 or face.calc_center_median().y > rim_y + 0.0005:
            trailing_oral_faces.add(face)
if trailing_oral_faces:
    old_interior_faces += len(trailing_oral_faces)
    bmesh.ops.delete(bm, geom=list(trailing_oral_faces), context='FACES')
ordered_ring = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in rim_coordinates]
ring_vertices = set(ordered_ring)
loose_interior = [vertex for vertex in bm.verts if vertex not in ring_vertices and not vertex.link_faces]
if loose_interior:
    bmesh.ops.delete(bm, geom=loose_interior, context='VERTS')
ordered_ring = [min(bm.verts, key=lambda vertex: (vertex.co - point).length_squared) for point in rim_coordinates]
closed_segments = 0
for index, vertex in enumerate(ordered_ring):
    following = ordered_ring[(index + 1) % len(ordered_ring)]
    edge = next((item for item in vertex.link_edges if following in item.verts), None)
    if edge and edge.is_boundary:
        closed_segments += 1
if closed_segments != len(ordered_ring):
    raise RuntimeError(f'口腔唇缘未完整释放：{closed_segments}，预期 {len(ordered_ring)}')

rim_points = np.array([tuple(vertex.co) for vertex in ordered_ring], dtype=float)
rim_x = rim_points[:, 0]
rim_z = rim_points[:, 2]
rim_design = np.column_stack((np.ones(len(rim_x)), rim_x, rim_z, rim_x * rim_x, rim_x * rim_z, rim_z * rim_z))
rim_coefficients, _, _, _ = np.linalg.lstsq(rim_design, rim_points[:, 1], rcond=None)
rim_center = sum(rim_coordinates, Vector()) / len(rim_coordinates)
deform_layer = bm.verts.layers.deform.active
if deform_layer is None:
    deform_layer = bm.verts.layers.deform.new()
head_group_index = obj.vertex_groups['head'].index

def rim_depth(x, z):
    return float(np.dot([1.0, x, z, x * x, x * z, z * z], rim_coefficients))

def oral_vertex(co):
    vertex = bm.verts.new(co)
    vertex[deform_layer][head_group_index] = 1.0
    return vertex

inner_loops = []
for fraction in (0.75, 0.50, 0.25):
    inner_loop = []
    for point in rim_coordinates:
        x = rim_center.x + (point.x - rim_center.x) * fraction
        z = rim_center.z + (point.z - rim_center.z) * fraction
        y = rim_depth(x, z) + 0.002 * (1.0 - fraction * fraction)
        inner_loop.append(oral_vertex((x, y, z)))
    inner_loops.append(inner_loop)
center_vertex = oral_vertex((rim_center.x, rim_depth(rim_center.x, rim_center.z) + 0.002, rim_center.z))
oral_faces = []
outer_loop = ordered_ring
for inner_loop in inner_loops:
    for index in range(len(outer_loop)):
        following = (index + 1) % len(outer_loop)
        face = bm.faces.new((outer_loop[index], outer_loop[following], inner_loop[following], inner_loop[index]))
        face.smooth = True
        oral_faces.append(face)
    outer_loop = inner_loop
for index in range(len(outer_loop)):
    following = (index + 1) % len(outer_loop)
    face = bm.faces.new((outer_loop[index], outer_loop[following], center_vertex))
    face.smooth = True
    oral_faces.append(face)
for face in oral_faces:
    face.normal_update()
    if face.normal.y > 0:
        face.normal_flip()
inner_vertices_projected = sum(len(loop) for loop in inner_loops) + 1

bm.normal_update()
bm.to_mesh(obj.data)
bm.free()
obj.data.update()

# The source shorts reached the knee and were partly weighted to the shin.
# Keep the waistband, crotch and upper seat anchored to the hips. Only the
# lower leg openings follow the thighs; shin influences are removed entirely.
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
    down_blend = smoothstep((0.085 - vertex.co.z) / 0.025)
    thigh_weight = side_blend * down_blend
    thigh = obj.vertex_groups['thigh_L' if vertex.co.x > 0 else 'thigh_R']
    for group in list(obj.vertex_groups):
        group.remove([vertex.index])
    if thigh_weight < 0.999999:
        hips_group.add([vertex.index], 1.0 - thigh_weight, 'REPLACE')
    if thigh_weight > 0.000001:
        thigh.add([vertex.index], thigh_weight, 'REPLACE')

# Component 6 is the shorts. Component-colour renders confirmed that the
# remaining blue spike was a side pants face rotating in front of the robe.
# Narrow every pants vertex, with a stronger reduction on the covered upper
# seat, while keeping the lower openings and the enlarged leg motion intact.
covered_pants_vertices = 0
for vertex in obj.data.vertices:
    if component_attribute.data[vertex.index].value != 6:
        continue
    original_co = vertex.co.copy()
    covered = 0.55 + 0.45 * smoothstep((original_co.z - 0.075) / 0.060)
    center_x = 0.09 if original_co.x > 0 else -0.09
    target_x = center_x + (original_co.x - center_x) * 0.65
    target_y = -0.055 + (original_co.y + 0.055) * 0.25
    vertex.co.x = original_co.x + (target_x - original_co.x) * covered
    vertex.co.y = original_co.y + (target_y - original_co.y) * covered
    covered_pants_vertices += 1

# Keep the complete robe, including its blue decorated front panel, on the
# source hip weights. No extra robe-to-thigh weights are added; the remaining
# protrusion is handled on the pants geometry above.
robe_side_vertices = 0

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

# The source mouth UVs cross unrelated brown/dark atlas islands. Use clean,
# matte interior materials instead of sampling those streaks on the tongue.
def srgb_channel(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

def mouth_material(name, hex_color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    rgb = [int(hex_color[index:index + 2], 16) / 255.0 for index in (1, 3, 5)]
    linear_color = tuple(srgb_channel(value) for value in rgb)
    material.diffuse_color = (*linear_color, 1)
    nodes = material.node_tree.nodes
    bsdf = next((node for node in nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if bsdf is None:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = next((node for node in nodes if node.bl_idname == 'ShaderNodeOutputMaterial'), None)
    if output is None:
        output = nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (*linear_color, 1)
    bsdf.inputs['Roughness'].default_value = 0.88
    bsdf.inputs['Specular IOR Level'].default_value = 0.22
    return material

# A single matte coral surface removes the jagged boundary between the old
# cavity and tongue materials while retaining the modelled mouth aperture.
oral_material = mouth_material('卡通人物 · 平整口腔', '#D7756D')
oral_slot = len(obj.data.materials)
obj.data.materials.append(oral_material)

# The shorts' UVs contain misplaced red/brown atlas islands. Deliberately use a
# clean matte navy on all component-6 faces; all other original UVs and textures
# remain untouched. This is an appearance simplification, not a texture repair.
pants_material = mouth_material('卡通人物 · 深藏蓝裤子', '#263F61')
pants_slot = len(obj.data.materials)
obj.data.materials.append(pants_material)
pants_material_faces = 0
mouth_face_counts = {'uniform_oral': 0}
for polygon in obj.data.polygons:
    if component_attribute.data[polygon.vertices[0]].value == 6:
        polygon.material_index = pants_slot
        pants_material_faces += 1
        continue
    center = polygon.center
    # Restrict recoloring to the actual aperture. A rectangular region also
    # catches the chin and the outer lip, which must keep the original skin.
    if -0.315 < center.y < -0.20 and point_inside_outline(center.x, center.z):
        polygon.material_index = oral_slot
        mouth_face_counts['uniform_oral'] += 1

readme = bpy.data.texts.get('绑骨说明') or bpy.data.texts.new('绑骨说明')
readme.clear()
readme.write('卡通人物基础绑定 · 局部优化版\n\n来源：用户提供的 FBX。除裤子外，保留原主贴图与 UV。\n骨架：22 根骨骼，前方 -Y，+X 为角色左侧。\n嘴部：唇缘由 26 段加密为 52 段并平顺；删除旧口腔褶皱内壁，以 3 圈规则内环和中心点重建连续浅碗状曲面，最大凹入约 2 毫米，统一为哑光珊瑚色；不是全脸重拓扑。\n裤子：裤腰、裤裆固定到髋部，仅裤脚跟随大腿；全部裤片适度收拢，上部收拢更强，避免侧面裤片跨步时翻到衣摆前方；统一为哑光深藏蓝材质，以消除错误贴图岛产生的红棕色杂色，属于有意的材质简化。\n衣物：衣服及蓝色装饰前襟保持源髋部权重，不额外跟随大腿。\n动作：绑定测试_挥手与步伐，1–96 帧，30 fps；56、72 帧加大跨步和反向摆臂。\n未拆分：手指骨骼、精细面部表情、IK 控制器。\n原始文件及上一版绑定文件均未覆盖。\n')

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
    'support_edges_subdivided': len(support_edges), 'old_oral_interior_vertices_removed': old_interior_vertices,
    'outer_skin_vertices_flattened': outer_skin_flattened,
    'oral_patch_vertices_rebuilt': inner_vertices_projected,
    'oral_patch_radial_rings': 3,
    'uv_layers': [layer.name for layer in obj.data.uv_layers],
    'unweighted_vertices': unweighted, 'invalid_weight_sums': invalid_weights,
    'bone_count': len(rig.pose.bones), 'action': action.name,
    'pants_vertices_reweighted': pants_vertices,
    'covered_pants_vertices_shrunk': covered_pants_vertices,
    'pants_uniform_material_faces': pants_material_faces,
    'pants_material_cleanup': '全部裤片统一为哑光深藏蓝材质，有意简化原裤片贴图，以彻底移除错误 UV 贴图岛造成的红棕色杂色；其他部件贴图与 UV 保留。',
    'robe_side_vertices_with_limited_thigh_follow': robe_side_vertices,
    'robe_side_thigh_follow_cap': 0.0,
    'mouth_face_counts': mouth_face_counts,
    'mouth_material_cleanup': '口腔内部统一为单一哑光珊瑚色，消除舌头与口腔的锯齿材质边界；主皮肤贴图和 UV 保留。',
    'oral_bowl_max_depth_m': 0.002,
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
