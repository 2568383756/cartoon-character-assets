from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "working" / "character_02"
REVIEW = ROOT / "review" / "character_02"
REVIEW.mkdir(parents=True, exist_ok=True)
FBX = next(SOURCE_DIR.glob("*.fbx"))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX), use_anim=True)
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("FBX 中没有网格")

report = {
    "source": str(FBX),
    "objects": [],
    "images": [],
    "armatures": [],
    "actions": [action.name for action in bpy.data.actions],
}
for image in bpy.data.images:
    report["images"].append({
        "name": image.name,
        "filepath": image.filepath,
        "size": list(image.size),
        "packed": bool(image.packed_file),
    })
for arm in [obj for obj in scene.objects if obj.type == "ARMATURE"]:
    report["armatures"].append({"name": arm.name, "bones": [bone.name for bone in arm.data.bones]})

all_world_points = []
for obj in meshes:
    world_points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    all_world_points.extend(world_points)
    adjacency = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    remaining = set(range(len(obj.data.vertices)))
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
        points = [obj.data.vertices[index].co for index in indices]
        low = [min(point[axis] for point in points) for axis in range(3)]
        high = [max(point[axis] for point in points) for axis in range(3)]
        center = [(low[axis] + high[axis]) * 0.5 for axis in range(3)]
        components.append({
            "index": len(components),
            "vertices": len(indices),
            "bbox_min_local": low,
            "bbox_max_local": high,
            "bbox_center_local": center,
        })
    components.sort(key=lambda item: item["vertices"], reverse=True)
    for index, component in enumerate(components):
        component["index"] = index
    materials = []
    for material in obj.data.materials:
        if material is None:
            materials.append(None)
            continue
        textures = []
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    textures.append({"node": node.name, "image": node.image.name})
        materials.append({"name": material.name, "textures": textures})
    report["objects"].append({
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
        "uv_layers": [layer.name for layer in obj.data.uv_layers],
        "vertex_groups": [group.name for group in obj.vertex_groups],
        "modifiers": [{"name": mod.name, "type": mod.type} for mod in obj.modifiers],
        "materials": materials,
        "components": components,
    })

low = Vector([min(point[axis] for point in all_world_points) for axis in range(3)])
high = Vector([max(point[axis] for point in all_world_points) for axis in range(3)])
center = (low + high) * 0.5
size = max(high - low)
report["world_bbox"] = {"min": list(low), "max": list(high), "center": list(center), "dimensions": list(high - low)}
(REVIEW / "import_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "working" / "character_02_import.blend"))

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 850
scene.render.resolution_y = 850
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("新角色检查环境")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
background.inputs["Strength"].default_value = 0.6

bpy.ops.mesh.primitive_plane_add(size=size * 20, location=(center.x, center.y, low.z - size * 0.004))
plane = bpy.context.object
plane.name = "检查用地面"
material = bpy.data.materials.new("检查用地面材质")
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)


def area(name, offset, energy, light_size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy * size * size
    data.shape = "DISK"
    data.size = light_size * size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = center + Vector(offset) * size
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()


area("检查主光", (1.5, -2.5, 2.5), 350, 2.5, (1.0, 0.88, 0.76))
area("检查补光", (-2.0, -1.0, 1.5), 260, 2.0, (0.74, 0.85, 1.0))
area("检查轮廓光", (0.5, 2.0, 2.0), 400, 2.0, (0.86, 0.92, 1.0))
camera_data = bpy.data.cameras.new("检查相机")
camera = bpy.data.objects.new("检查相机", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = size * 1.30
camera_data.clip_start = size * 0.001
camera_data.clip_end = size * 100
views = [
    ("negative_y", Vector((0, -4.0, 0.45))),
    ("three_quarter", Vector((3.0, -4.0, 1.1))),
    ("positive_x", Vector((4.0, 0, 0.45))),
    ("positive_y", Vector((0, 4.0, 0.45))),
    ("negative_x", Vector((-4.0, 0, 0.45))),
]
for label, offset in views:
    camera.location = center + offset * size
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(REVIEW / f"import_{label}.png")
    bpy.ops.render.render(write_still=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
