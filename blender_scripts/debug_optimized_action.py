from pathlib import Path
import bpy
import json

ROOT = Path(__file__).resolve().parents[1]
results = {}

def snapshot(label, rig, action):
    rows = {}
    for frame in (1, 12, 24, 40, 54, 55, 56, 57, 70, 71, 72, 73, 95, 96):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        rows[str(frame)] = {
            name: {
                'head': [round(v, 6) for v in rig.pose.bones[name].head],
                'quaternion': [round(v, 6) for v in rig.pose.bones[name].rotation_quaternion],
            }
            for name in ('thigh_L', 'shin_L', 'thigh_R', 'shin_R', 'foot_L', 'foot_R')
        }
    results[label] = {
        'action_frame_range': list(action.frame_range),
        'slots': [slot.identifier for slot in action.slots],
        'active_slot': rig.animation_data.action_slot.identifier if rig.animation_data.action_slot else None,
        'nla': [
            {'name': strip.name, 'start': strip.frame_start, 'end': strip.frame_end, 'action': strip.action.name if strip.action else None}
            for track in rig.animation_data.nla_tracks for strip in track.strips
        ],
        'frames': rows,
    }

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨_优化.blend'))
rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
snapshot('native', rig, rig.animation_data.action)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'deliverables' / '卡通人物_已绑骨_优化.glb'))
rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
action = next(action for action in bpy.data.actions if '绑定测试' in action.name)
snapshot('glb_imported_default', rig, action)
rig.animation_data.action = action
snapshot('glb_imported_assigned', rig, action)
(ROOT / 'review' / 'optimized_action_debug.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
