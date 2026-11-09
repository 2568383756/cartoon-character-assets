from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
frames = (1, 17, 33, 49)
views = ('front', 'three_quarter', 'side', 'back')
labels = {'front': '正面', 'three_quarter': '三分之四', 'side': '侧面', 'back': '背面'}
cell = 260
header = 34
sheet = Image.new('RGB', (cell * 4, (cell + header) * 4 + header), '#eef1f5')
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
except OSError:
    font = ImageFont.load_default()
for col, view in enumerate(views):
    draw.text((col * cell + 10, 7), labels[view], fill='#202733', font=font)
for row, frame in enumerate(frames):
    for col, view in enumerate(views):
        image = Image.open(root / f'carry_{view}_{frame:02d}.png').convert('RGB')
        image.thumbnail((cell, cell), Image.Resampling.LANCZOS)
        x = col * cell
        y = header + row * (cell + header)
        sheet.paste(image, (x, y))
        draw.text((x + 10, y + cell + 6), f'第 {frame} 帧', fill='#202733', font=font)
out = root / 'carry_contact_sheet.png'
sheet.save(out)
print(out)
