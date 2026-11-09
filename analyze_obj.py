from pathlib import Path
import json
import numpy as np

root = Path(__file__).resolve().parent
obj_path = root / "source_model" / "3d_卡通人物模型.obj"
vertices = []
faces = []
objects = []
groups = []
materials = []
current_object = None
current_group = None
current_material = None
face_materials = []

with obj_path.open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if line.startswith("v "):
            vertices.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            indices = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            faces.append(indices)
            face_materials.append(current_material)
        elif line.startswith("o "):
            current_object = line[2:].strip()
            objects.append(current_object)
        elif line.startswith("g "):
            current_group = line[2:].strip()
            groups.append(current_group)
        elif line.startswith("usemtl "):
            current_material = line[7:].strip()
            materials.append(current_material)

v = np.asarray(vertices, dtype=np.float64)
position_to_unique = {}
unique_positions = []
vertex_to_unique = np.empty(len(v), dtype=np.int32)
for index, position in enumerate(v):
    key = tuple(position)
    unique_index = position_to_unique.get(key)
    if unique_index is None:
        unique_index = len(unique_positions)
        position_to_unique[key] = unique_index
        unique_positions.append(key)
    vertex_to_unique[index] = unique_index

parent = np.arange(len(unique_positions), dtype=np.int32)
size = np.ones(len(unique_positions), dtype=np.int32)

def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return int(a)

def union(a, b):
    a, b = find(a), find(b)
    if a == b:
        return
    if size[a] < size[b]:
        a, b = b, a
    parent[b] = a
    size[a] += size[b]

for face in faces:
    root_index = vertex_to_unique[face[0]]
    for index in face[1:]:
        union(root_index, vertex_to_unique[index])

components = {}
for unique_index in range(len(unique_positions)):
    components.setdefault(find(unique_index), []).append(unique_index)
unique_v = np.asarray(unique_positions, dtype=np.float64)
component_records = []
for component_indices in components.values():
    points = unique_v[component_indices]
    component_records.append({
        "vertices": len(component_indices),
        "bounds_min": points.min(axis=0).tolist(),
        "bounds_max": points.max(axis=0).tolist(),
        "center": points.mean(axis=0).tolist(),
    })
component_records.sort(key=lambda item: item["vertices"], reverse=True)

material_counts = {}
for material in face_materials:
    material_counts[material] = material_counts.get(material, 0) + 1

report = {
    "file": obj_path.name,
    "vertex_positions": len(vertices),
    "unique_vertex_positions": len(unique_positions),
    "faces": len(faces),
    "triangle_faces": sum(len(face) == 3 for face in faces),
    "quad_faces": sum(len(face) == 4 for face in faces),
    "objects": objects,
    "groups": groups,
    "materials": materials,
    "material_face_counts": material_counts,
    "bounds_min": v.min(axis=0).tolist(),
    "bounds_max": v.max(axis=0).tolist(),
    "dimensions_xyz": (v.max(axis=0) - v.min(axis=0)).tolist(),
    "center_xyz": ((v.max(axis=0) + v.min(axis=0)) / 2).tolist(),
    "connected_components": len(component_records),
    "largest_components": component_records[:30],
}
output = root / "model_analysis.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
