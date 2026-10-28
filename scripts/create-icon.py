"""Generate the application icon from simple geometric shapes (requires Pillow)."""
from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "desktop/src-tauri/icons"
root.mkdir(parents=True, exist_ok=True)
icon = Image.new("RGBA", (256, 256), (17, 19, 25, 255))
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle((36, 58, 220, 204), radius=38, fill="#8b80f9")
draw.rounded_rectangle((59, 83, 197, 177), radius=24, fill="#171925")
draw.ellipse((79, 113, 103, 137), fill="#e9e5ff")
draw.ellipse((153, 113, 177, 137), fill="#e9e5ff")
draw.line((128, 58, 128, 34), fill="#8b80f9", width=12)
draw.ellipse((118, 24, 138, 44), fill="#8b80f9")
icon.save(root / "icon.png")
icon.save(root / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
