from pathlib import Path
from collections import Counter
import bpy
import json

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨_优化.blend'))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
records = []
for polygon in obj.data.polygons:
    center = polygon.center
    if not (abs(center.x) < 0.09 and 0.39 < center.z < 0.525 and -0.33 < center.y < -0.18):
        continue
    records.append({
        'index': polygon.index,
        'material': obj.data.materials[polygon.material_index].name,
        'center': [round(value, 7) for value in center],
        'normal': [round(value, 5) for value in polygon.normal],
        'vertices': list(polygon.vertices),
        'area': polygon.area,
    })
summary = {}
for material in sorted({row['material'] for row in records}):
    selected = [row for row in records if row['material'] == material]
    summary[material] = {
        'faces': len(selected),
        'normal_y_signs': dict(Counter('positive' if row['normal'][1] > 0.05 else 'negative' if row['normal'][1] < -0.05 else 'side' for row in selected)),
        'normal_z_signs': dict(Counter('positive' if row['normal'][2] > 0.05 else 'negative' if row['normal'][2] < -0.05 else 'side' for row in selected)),
        'y_range': [min(row['center'][1] for row in selected), max(row['center'][1] for row in selected)],
        'z_range': [min(row['center'][2] for row in selected), max(row['center'][2] for row in selected)],
    }
(ROOT / 'review' / 'mouth_material_region.json').write_text(json.dumps({'summary': summary, 'records': records}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
