from pathlib import Path
from PIL import Image, ImageDraw
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review'
data = (ROOT / 'deliverables' / '卡通人物_已绑骨_优化.glb').read_bytes()
chunk_length, chunk_type = struct.unpack_from('<I4s', data, 12)
gltf = json.loads(data[20:20 + chunk_length].decode('utf-8'))
bin_start = 20 + chunk_length + 8
for index, image in enumerate(gltf.get('images', [])):
    view = gltf['bufferViews'][image['bufferView']]
    start = bin_start + view.get('byteOffset', 0)
    payload = data[start:start + view['byteLength']]
    suffix = '.png' if image.get('mimeType') == 'image/png' else '.jpg'
    (REVIEW / f'extracted_texture_{index}{suffix}').write_bytes(payload)

frames = [44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88]
thumb_w, thumb_h = 350, 300
sheet = Image.new('RGB', (thumb_w * 4, (thumb_h + 28) * 3), 'white')
draw = ImageDraw.Draw(sheet)
for i, frame in enumerate(frames):
    image = Image.open(REVIEW / f'walk_check_{frame:02d}.png').convert('RGB')
    image.thumbnail((thumb_w, thumb_h))
    x, y = (i % 4) * thumb_w, (i // 4) * (thumb_h + 28)
    sheet.paste(image, (x, y + 28))
    draw.text((x + 10, y + 7), f'Frame {frame}', fill='black')
sheet.save(REVIEW / 'walk_contact_sheet.png')
print(json.dumps({'textures': gltf.get('images', []), 'sheet': str(REVIEW / 'walk_contact_sheet.png')}, ensure_ascii=False))
