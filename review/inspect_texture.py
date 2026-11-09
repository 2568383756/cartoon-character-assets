from pathlib import Path
from PIL import Image, ImageDraw
import json

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review'
image = Image.open(REVIEW / 'extracted_texture_0.jpg').convert('RGB')
preview = image.copy()
preview.thumbnail((1600, 1600))
preview.save(REVIEW / 'texture_preview.jpg', quality=88)
w, h = image.size
regions = {
    'mouth_texture_main': (0.20, 0.40, 0.36, 0.64),
    'mouth_texture_secondary': (0.59, 0.88, 0.71, 1.00),
}
uv_data = json.loads((REVIEW / 'mouth_uv_texture.json').read_text(encoding='utf-8'))['mouth_uv']
for name, (u0, v0, u1, v1) in regions.items():
    box = (int(u0 * w), int((1 - v1) * h), int(u1 * w), int((1 - v0) * h))
    crop = image.crop(box)
    draw = ImageDraw.Draw(crop)
    for item in uv_data:
        for u, v in item['uv']:
            if u0 <= u <= u1 and v0 <= v <= v1:
                x, y = (u - u0) / (u1 - u0) * crop.width, (v1 - v) / (v1 - v0) * crop.height
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline='cyan', width=2)
    crop.save(REVIEW / f'{name}.png')
print({'size': image.size, 'preview': str(REVIEW / 'texture_preview.jpg')})
