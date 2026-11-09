from pathlib import Path
import bpy
import bmesh
import json

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨.blend'))
bpy.context.scene.frame_set(1)
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
mesh = obj.data

def inside(v):
    p = v.co
    return abs(p.x) < 0.15 and p.y < -0.18 and 0.385 < p.z < 0.522

vertices = []
selected = set()
for v in mesh.vertices:
    if inside(v):
        selected.add(v.index)
        vertices.append({
            'index': v.index,
            'co': [round(c, 7) for c in v.co],
            'degree': len(v.link_edges) if hasattr(v, 'link_edges') else None,
            'groups': {obj.vertex_groups[g.group].name: round(g.weight, 5) for g in v.groups},
        })
mesh.update()
bm = bmesh.new()
bm.from_mesh(mesh)
bm.normal_update()
edges = []
for edge in bm.edges:
    a, b = edge.verts
    if a.index not in selected and b.index not in selected:
        continue
    angle = None
    if len(edge.link_faces) == 2:
        angle = round(edge.calc_face_angle(), 5)
    if edge.is_boundary or (angle is not None and angle > 0.20) or (a.index in selected and b.index in selected):
        edges.append({
            'vertices': [a.index, b.index],
            'co': [[round(c, 6) for c in a.co], [round(c, 6) for c in b.co]],
            'boundary': edge.is_boundary,
            'angle': angle,
            'faces': [f.index for f in edge.link_faces],
        })
polygons = []
for polygon in mesh.polygons:
    if any(i in selected for i in polygon.vertices):
        polygons.append({
            'index': polygon.index,
            'vertices': list(polygon.vertices),
            'normal': [round(v, 4) for v in polygon.normal],
            'area': round(polygon.area, 9),
        })
bm.free()
report = {'vertices': vertices, 'edges': edges, 'polygons': polygons}
(ROOT / 'review' / 'mouth_topology.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('region vertices', len(vertices), 'edges', len(edges), 'polygons', len(polygons))
