from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "working" / "model_clean.blend"))
obj = bpy.data.objects["卡通人物"]
attribute = obj.data.attributes["component_index"]
palette = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33",
    "#a65628", "#f781bf", "#999999", "#66c2a5", "#fc8d62", "#8da0cb",
    "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#1b9e77", "#d95f02",
    "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d",
]

def rgba(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[i:i+2], 16) / 255 for i in (0, 2, 4)) + (1,)

materials = []
for index, color in enumerate(palette):
    material = bpy.data.materials.new(f"部件_{index:02d}")
    material.diffuse_color = rgba(color)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba(color)
    principled.inputs["Roughness"].default_value = 0.65
    materials.append(material)
for material in materials:
    obj.data.materials.append(material)
material_offset = len(obj.data.materials) - len(materials)
for polygon in obj.data.polygons:
    component = attribute.data[polygon.vertices[0]].value
    polygon.material_index = material_offset + component
    polygon.use_smooth = True

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
views = {"front": (0, -3.5, 0.75), "side": (3.5, 0, 0.75), "back": (0, 3.5, 0.75)}
for name, location in views.items():
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"components_{name}.png")
    bpy.ops.render.render(write_still=True)
(REVIEW / "component_colors.json").write_text(json.dumps({str(i): color for i, color in enumerate(palette)}, indent=2), encoding="utf-8")
