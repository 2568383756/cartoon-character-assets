from pathlib import Path
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OBJ = ROOT / "source_model" / "3d_卡通人物模型.obj"
WORK = ROOT / "working"
REVIEW = ROOT / "review"
WORK.mkdir(exist_ok=True)
REVIEW.mkdir(exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for data in list(bpy.data.meshes):
    if data.users == 0:
        bpy.data.meshes.remove(data)

bpy.ops.wm.obj_import(filepath=str(OBJ), forward_axis="NEGATIVE_Z", up_axis="Y")
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("OBJ 导入后没有网格")

bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = "卡通人物"
obj.data.name = "卡通人物_清理网格"
obj.rotation_euler.z = -math.pi / 2
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
for polygon in obj.data.polygons:
    polygon.use_smooth = True

remaining = set(range(len(obj.data.vertices)))
components = []
while remaining:
    seed = remaining.pop()
    stack = [seed]
    indices = [seed]
    while stack:
        current = stack.pop()
        vertex = obj.data.vertices[current]
        for edge in obj.data.edges:
            if edge.vertices[0] == current:
                neighbor = edge.vertices[1]
            elif edge.vertices[1] == current:
                neighbor = edge.vertices[0]
            else:
                continue
            if neighbor in remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
                indices.append(neighbor)
    components.append(indices)
components.sort(key=len, reverse=True)

attribute = obj.data.attributes.get("component_index") or obj.data.attributes.new("component_index", "INT", "POINT")
records = []
for component_index, indices in enumerate(components):
    group = obj.vertex_groups.new(name=f"part_{component_index:02d}")
    group.add(indices, 1.0, "REPLACE")
    points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    center = [sum(point[axis] for point in points) / len(points) for axis in range(3)]
    for index in indices:
        attribute.data[index].value = component_index
    records.append({
        "component": component_index,
        "vertices": len(indices),
        "bounds_min": minimum,
        "bounds_max": maximum,
        "center": center,
    })

for material in obj.data.materials:
    if material:
        material.name = "卡通人物 · 主贴图"
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        try:
            image.pack()
        except RuntimeError:
            pass

report = {
    "blender_version": bpy.app.version_string,
    "mesh": obj.name,
    "vertices": len(obj.data.vertices),
    "edges": len(obj.data.edges),
    "polygons": len(obj.data.polygons),
    "components": records,
    "materials": [material.name for material in obj.data.materials if material],
    "packed_images": [image.name for image in bpy.data.images if image.packed_file],
}
(REVIEW / "clean_model_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "model_clean.blend"))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
background.inputs["Strength"].default_value = 0.45

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
views = {
    "front": (0, -3.5, 0.75),
    "side": (3.5, 0, 0.75),
    "back": (0, 3.5, 0.75),
    "three_quarter": (2.4, -3.2, 1.6),
}
for name, location in views.items():
    camera.location = location
    target = Vector((0, 0, 0.5))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"original_{name}.png")
    bpy.ops.render.render(write_still=True)

print(json.dumps(report, ensure_ascii=False, indent=2))
