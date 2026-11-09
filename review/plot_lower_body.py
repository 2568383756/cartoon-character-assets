from pathlib import Path
from PIL import Image, ImageDraw
import json

ROOT = Path(__file__).resolve().parents[1]
records = json.loads((ROOT / 'review' / 'lower_body_uv_colors.json').read_text())
sheet = Image.new('RGB', (1200, 650), 'white')
draw = ImageDraw.Draw(sheet)
red_candidates = []
for panel, component in enumerate((2, 6)):
    ox = panel * 600
    draw.text((ox + 20, 15), f'Component {component}: x/z colored by sampled texture', fill='black')
    for item in records:
        if item['component'] != component or not item['samples']:
            continue
        x, y, z = item['co']
        rgba = item['samples'][0]['rgba']
        rgb = tuple(max(0, min(255, int(c * 255))) for c in rgba[:3])
        px = ox + 300 + x / 0.42 * 560
        py = 610 - (z - 0.04) / 0.19 * 560
        radius = 6 if component == 2 else 4
        draw.ellipse((px-radius, py-radius, px+radius, py+radius), fill=rgb, outline='black')
        r, g, b = rgba[:3]
        if component == 2 and r > g * 1.30 and r > b * 1.30 and r > 0.25:
            red_candidates.append({'index': item['index'], 'co': item['co'], 'rgb': rgba[:3]})
            draw.text((px + 7, py - 6), str(item['index']), fill='black')
sheet.save(ROOT / 'review' / 'lower_body_color_map.png')
(ROOT / 'review' / 'lower_body_red_candidates.json').write_text(json.dumps(red_candidates, indent=2))
print({'red_candidates': len(red_candidates), 'indices': [x['index'] for x in red_candidates]})
