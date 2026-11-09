from pathlib import Path
import bpy
import bmesh
import json
import math
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "character_02" / "components"
REVIEW.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "working" / "character_02_import.blend"))
scene = bpy.context.scene
source = next(obj for obj in scene.objects if obj.type == "MESH")
source.name = "新卡通人物"
source.rotation_euler.z = -math.pi / 2
bpy.ops.object.select_all(action="DESELECT")
source.select_set(True)
bpy.context.view_layer.objects.active = source
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

adjacency = [[] for _ in source.data.vertices]
for edge in source.data.edges:
    a, b = edge.vertices
    adjacency[a].append(b)
    adjacency[b].append(a)
remaining = set(range(len(source.data.vertices)))
components = []
while remaining:
    seed = remaining.pop()
    stack = [seed]
    indices = []
    while stack:
        current = stack.pop()
        indices.append(current)
        for neighbor in adjacency[current]:
            if neighbor in remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
    components.append(indices)
components.sort(key=len, reverse=True)
component_of = {}
for component, indices in enumerate(components):
    for index in indices:
        component_of[index] = component

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "working" / "character_02_aligned.blend"))

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 300
scene.render.resolution_y = 300
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("部件检查环境")
scene.world.color = (0.78, 0.82, 0.88)
scene.world.use_nodes = True
if scene.world.node_tree:
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
        background.inputs["Strength"].default_value = 0.7


def area(name, location, energy, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 0.5)) - light.location).to_track_quat("-Z", "Y").to_euler()


area("部件主光", (1.5, -2.5, 3.0), 350, 2.5)
area("部件补光", (-2.0, -1.0, 1.8), 230, 2.0)
area("部件轮廓光", (0.5, 2.0, 2.5), 400, 2.0)
camera_data = bpy.data.cameras.new("部件检查相机")
camera = bpy.data.objects.new("部件检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"

source.hide_render = True
manifest = []
for component, indices in enumerate(components):
    index_set = set(indices)
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = f"部件_{component:02d}"
    obj.hide_render = False
    scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    delete = [vert for vert in bm.verts if vert.index not in index_set]
    bmesh.ops.delete(bm, geom=delete, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    points = [vert.co for vert in obj.data.vertices]
    low = Vector([min(point[axis] for point in points) for axis in range(3)])
    high = Vector([max(point[axis] for point in points) for axis in range(3)])
    center = (low + high) * 0.5
    size = max(high - low)
    camera.location = center + Vector((2.2, -3.2, 1.2)) * max(size, 0.03)
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = max(size * 1.28, 0.05)
    camera_data.clip_start = 0.0001
    camera_data.clip_end = 100
    scene.render.filepath = str(REVIEW / f"component_{component:02d}.png")
    bpy.ops.render.render(write_still=True)
    manifest.append({
        "component": component,
        "vertices": len(indices),
        "bbox_min": list(low),
        "bbox_max": list(high),
        "bbox_center": list(center),
        "image": f"component_{component:02d}.png",
    })
    bpy.data.objects.remove(obj, do_unlink=True)

(REVIEW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False, indent=2))
