from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
FBX = ROOT / "source_model" / "fbx_version" / "tripo_convert_32b70fc4-da7d-4934-88d9-d7d9b5a1acab.fbx"
REVIEW = ROOT / "review"
WORK = ROOT / "working"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(FBX))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("FBX 导入后没有网格")

points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
center = (minimum + maximum) / 2
size = maximum - minimum
report = {
    "blender_version": bpy.app.version_string,
    "objects": [
        {
            "name": obj.name,
            "type": obj.type,
            "vertices": len(obj.data.vertices) if obj.type == "MESH" else None,
            "polygons": len(obj.data.polygons) if obj.type == "MESH" else None,
            "vertex_groups": [group.name for group in obj.vertex_groups],
            "uv_layers": [layer.name for layer in obj.data.uv_layers] if obj.type == "MESH" else [],
            "materials": [material.name for material in obj.data.materials if material] if obj.type == "MESH" else [],
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "dimensions": list(obj.dimensions),
        }
        for obj in bpy.context.scene.objects
    ],
    "bounds_min": list(minimum),
    "bounds_max": list(maximum),
    "dimensions": list(size),
    "armatures": [obj.name for obj in bpy.context.scene.objects if obj.type == "ARMATURE"],
    "images": [image.name for image in bpy.data.images],
}
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        try:
            image.pack()
        except RuntimeError:
            pass
report["packed_images"] = [image.name for image in bpy.data.images if image.packed_file]
(REVIEW / "fbx_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "model_fbx.blend"))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
background.inputs["Strength"].default_value = 0.5

def add_area(name, location, energy, size_value, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size_value
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()

scale = max(size)
add_area("主光", center + Vector((1.5, -2.5, 2.5)) * scale, 350 * scale * scale, 2.5 * scale, (1.0, 0.86, 0.72))
add_area("补光", center + Vector((-2.0, -1.0, 1.3)) * scale, 230 * scale * scale, 2.0 * scale, (0.72, 0.84, 1.0))
add_area("轮廓光", center + Vector((0.5, 2.0, 2.0)) * scale, 400 * scale * scale, 2.0 * scale, (0.85, 0.92, 1.0))
camera_data = bpy.data.cameras.new("检查相机")
camera = bpy.data.objects.new("检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = scale * 1.28
views = {"front": (0, -3.5, 0.25), "side": (3.5, 0, 0.25), "back": (0, 3.5, 0.25)}
for name, offset in views.items():
    camera.location = center + Vector(offset) * scale
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"fbx_{name}.png")
    bpy.ops.render.render(write_still=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
