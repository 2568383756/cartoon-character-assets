from pathlib import Path
import bpy
import json
import struct
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "deliverables" / "卡通人物_已绑骨.glb"
REVIEW = ROOT / "review"
data = GLB.read_bytes()
magic, version, total_length = struct.unpack_from("<4sII", data, 0)
chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
assert magic == b"glTF" and version == 2 and chunk_type == b"JSON"
gltf = json.loads(data[20:20 + chunk_length].decode("utf-8"))
structure = {
    "byte_length": total_length,
    "nodes": len(gltf.get("nodes", [])),
    "meshes": len(gltf.get("meshes", [])),
    "skins": [
        {"joint_count": len(skin.get("joints", [])), "skeleton": skin.get("skeleton")}
        for skin in gltf.get("skins", [])
    ],
    "animations": [
        {
            "name": animation.get("name"),
            "channels": len(animation.get("channels", [])),
            "samplers": len(animation.get("samplers", [])),
        }
        for animation in gltf.get("animations", [])
    ],
    "materials": [material.get("name") for material in gltf.get("materials", [])],
    "images": len(gltf.get("images", [])),
    "extensions_used": gltf.get("extensionsUsed", []),
}
(REVIEW / "glb_structure.json").write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(GLB))
armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if len(armatures) != 1 or not meshes:
    raise RuntimeError("GLB 回导后骨架或网格缺失")
rig = armatures[0]
rig.name = "GLB回导骨架"
for action in bpy.data.actions:
    if "绑定测试" in action.name:
        rig.animation_data_create()
        rig.animation_data.action = action
        break
scene = bpy.context.scene
scene.render.fps = 30
scene.frame_set(12)
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
material = bpy.data.materials.new("检查用地面材质")
material.diffuse_color = (0.32, 0.36, 0.42, 1)
plane.data.materials.append(material)

def add_area(name, location, energy, size, color):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_data.color = color
    light = bpy.data.objects.new(name, light_data)
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
camera.location = (0, -3.5, 0.75)
camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(REVIEW / "glb_roundtrip_wave.png")
bpy.ops.render.render(write_still=True)
roundtrip = {
    "armature_bones": len(rig.data.bones),
    "bone_names": [bone.name for bone in rig.data.bones],
    "mesh_vertices": sum(len(obj.data.vertices) for obj in meshes),
    "mesh_polygons": sum(len(obj.data.polygons) for obj in meshes),
    "actions": [action.name for action in bpy.data.actions],
    "materials": [material.name for material in bpy.data.materials if material.users],
    "posed_bone_head": list(rig.pose.bones["hand_L"].head) if "hand_L" in rig.pose.bones else None,
}
(REVIEW / "glb_roundtrip_report.json").write_text(json.dumps(roundtrip, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"structure": structure, "roundtrip": roundtrip}, ensure_ascii=False, indent=2))
