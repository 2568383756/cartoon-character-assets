from pathlib import Path
import bpy
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨.blend'))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
image = next(i for i in bpy.data.images if i.type == 'IMAGE')
w, h = image.size
pixels = np.empty(w * h * 4, dtype=np.float32)
image.pixels.foreach_get(pixels)
pixels = pixels.reshape(h, w, 4)
uv_layer = obj.data.uv_layers.active
components = obj.data.attributes['component_index'].data
records = []
for vertex in obj.data.vertices:
    component = int(components[vertex.index].value)
    if component not in (2, 6) or vertex.co.z > 0.215:
        continue
    uvs = []
    for polygon in obj.data.polygons:
        if vertex.index not in polygon.vertices:
            continue
        for loop_index in polygon.loop_indices:
            if obj.data.loops[loop_index].vertex_index == vertex.index:
                uvs.append(list(uv_layer.data[loop_index].uv))
    samples = []
    for u, v in uvs:
        x = max(0, min(w - 1, int(u * w)))
        y = max(0, min(h - 1, int(v * h)))
        samples.append({'uv': [u, v], 'rgba': pixels[y, x].tolist()})
    records.append({'index': vertex.index, 'component': component, 'co': list(vertex.co), 'samples': samples})
(ROOT / 'review' / 'lower_body_uv_colors.json').write_text(json.dumps(records), encoding='utf-8')
print({'image': image.name, 'size': [w, h], 'records': len(records)})
