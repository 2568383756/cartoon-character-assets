from pathlib import Path
import json
import shutil
import zipfile

root = Path(r"E:\KimiData\kimi\tasks\2026-11-07\16-16-56-5e24d110")
archive = root / "working" / "character_02_source.zip"
out_dir = root / "working" / "character_02"
out_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(archive) as zf:
    members = []
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"Unsafe archive member: {name}")
        members.append({
            "name": name,
            "size": info.file_size,
            "compressed_size": info.compress_size,
            "is_directory": info.is_dir(),
        })
    zf.extractall(out_dir)

files = []
for path in sorted(out_dir.rglob("*")):
    if path.is_file():
        files.append({
            "path": str(path.relative_to(out_dir)),
            "size": path.stat().st_size,
        })

report = {"archive": str(archive), "members": members, "files": files}
(root / "working" / "character_02_inventory.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
