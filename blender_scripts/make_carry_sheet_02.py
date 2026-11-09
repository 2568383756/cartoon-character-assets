from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r"E:\KimiData\kimi\tasks\2026-11-07\16-16-56-5e24d110")
folder = root / "review" / "character_02"
frames = (1, 17, 33, 49)
views = ("front", "three_quarter", "side", "back")
labels = {"front": "Front", "three_quarter": "Three-quarter", "side": "Side", "back": "Back"}
font = ImageFont.load_default(size=20)
sheet = Image.new("RGB", (1400, 1480), "#e8edf2")
draw = ImageDraw.Draw(sheet)
for row, frame in enumerate(frames):
    for column, view in enumerate(views):
        x = column * 350
        y = row * 370
        image = Image.open(folder / f"carry02_{view}_{frame:02d}.png").convert("RGB").resize((350, 350), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))
        draw.text((x + 10, y + 348), f"Frame {frame:02d} | {labels[view]}", fill="#17202b", font=font)
path = folder / "carry02_contact_sheet.jpg"
sheet.save(path, quality=92)
print(path)
