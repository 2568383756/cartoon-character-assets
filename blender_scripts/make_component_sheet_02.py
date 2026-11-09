from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

root = Path(r"E:\KimiData\kimi\tasks\2026-11-07\16-16-56-5e24d110")
folder = root / "review" / "character_02" / "components"
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
font = ImageFont.load_default(size=22)
for start, end in ((0, 20), (20, 39)):
    items = manifest[start:end]
    columns = 5
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 300, rows * 340), "#e8edf2")
    draw = ImageDraw.Draw(sheet)
    for position, item in enumerate(items):
        x = (position % columns) * 300
        y = (position // columns) * 340
        image = Image.open(folder / item["image"]).convert("RGB")
        sheet.paste(image, (x, y))
        draw.text((x + 10, y + 306), f"{item['component']:02d}  |  {item['vertices']} vertices", fill="#17202b", font=font)
    path = folder / f"sheet_{start:02d}_{end - 1:02d}.jpg"
    sheet.save(path, quality=90)
    print(path)
