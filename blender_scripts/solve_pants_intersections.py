from pathlib import Path
import bpy
import json
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨.blend'))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
components = obj.data.attributes['component_index'].data


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def reweight():
    hips = obj.vertex_groups['hips']
    for vertex in obj.data.vertices:
        if components[vertex.index].value != 6:
            continue
        side_blend = smoothstep((abs(vertex.co.x) - 0.015) / 0.07)
        down_blend = smoothstep((0.125 - vertex.co.z) / 0.035)
        thigh_weight = side_blend * down_blend
        thigh = obj.vertex_groups['thigh_L' if vertex.co.x > 0 else 'thigh_R']
        for group in list(obj.vertex_groups):
            group.remove([vertex.index])
        if thigh_weight < 0.999999:
            hips.add([vertex.index], 1.0 - thigh_weight, 'REPLACE')
        if thigh_weight > 0.000001:
            thigh.add([vertex.index], thigh_weight, 'REPLACE')


def overlap_counts():
    counts = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for frame in range(44, 89, 2):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        vertices = [vertex.co.copy() for vertex in mesh.vertices]
        polygons = {component: [] for component in (2, 6)}
        for polygon in mesh.polygons:
            component = int(components[polygon.vertices[0]].value)
            if component in polygons:
                polygons[component].append(tuple(polygon.vertices))
        trees = {
            component: BVHTree.FromPolygons(vertices, faces, all_triangles=False)
            for component, faces in polygons.items()
        }
        counts[frame] = len(trees[2].overlap(trees[6]))
        evaluated.to_mesh_clear()
    return counts


reweight()
results = {'baseline': overlap_counts()}
original_coordinates = [vertex.co.copy() for vertex in obj.data.vertices]
robe_weights = {
    vertex.index: {item.group: item.weight for item in vertex.groups}
    for vertex in obj.data.vertices if components[vertex.index].value == 2
}


def apply_robe_follow(max_follow):
    for index, original_weights in robe_weights.items():
        vertex = obj.data.vertices[index]
        for group in list(obj.vertex_groups):
            group.remove([index])
        side_blend = smoothstep((abs(vertex.co.x) - 0.04) / 0.10)
        down_blend = smoothstep((0.19 - vertex.co.z) / 0.085)
        follow = max_follow * side_blend * down_blend
        for group_index, weight in original_weights.items():
            obj.vertex_groups[group_index].add([index], weight * (1.0 - follow), 'REPLACE')
        if follow > 0.000001:
            thigh = obj.vertex_groups['thigh_L' if vertex.co.x > 0 else 'thigh_R']
            thigh.add([index], follow, 'REPLACE')


for y_factor, x_factor, robe_follow in (
    (0.55, 0.85, 0.0), (0.55, 0.85, 0.25), (0.40, 0.75, 0.25),
    (0.40, 0.75, 0.45), (0.28, 0.65, 0.30), (0.10, 0.40, 0.30),
):
    for vertex, original in zip(obj.data.vertices, original_coordinates):
        if components[vertex.index].value != 6:
            continue
        covered = smoothstep((original.z - 0.098) / 0.052)
        center_x = 0.09 if original.x > 0 else -0.09
        target_x = center_x + (original.x - center_x) * x_factor
        target_y = -0.055 + (original.y + 0.055) * y_factor
        vertex.co.x = original.x + (target_x - original.x) * covered
        vertex.co.y = original.y + (target_y - original.y) * covered
    apply_robe_follow(robe_follow)
    obj.data.update()
    bpy.context.view_layer.update()
    results[f'y={y_factor},x={x_factor},robe={robe_follow}'] = overlap_counts()

scene.frame_set(1)
print(json.dumps(results, ensure_ascii=False, indent=2))
(ROOT / 'review' / 'pants_intersection_trials.json').write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8'
)
