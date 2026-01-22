import os
from PIL import ImageFont, ImageDraw, Image

# Hardcoded font name from user request
font_name = "ChenYuluoyan-2.0-Thin.ttf"
search_paths = [
    os.path.join(os.getcwd(), font_name),
    os.path.join(r"C:\Windows\Fonts", font_name),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts", font_name),
    # Also check without current working directory just in case it's in the root of workspace
    os.path.join("e:\\My Project\\make_music_videos", font_name)
]

found_path = None
for p in search_paths:
    if os.path.exists(p):
        found_path = p
        break

print(f"Font Path Found: {found_path}")

if not found_path:
    print("Could not find font file.")
    exit(1)

def test_load(engine_name, engine_val):
    print(f"\n--- Testing {engine_name} ---")
    try:
        kwargs = {}
        if engine_val is not None:
            kwargs['layout_engine'] = engine_val
        
        font = ImageFont.truetype(found_path, 40, **kwargs)
        print(f"Load Success: {font}")
        
        # Test Render
        img = Image.new("RGB", (100, 100))
        draw = ImageDraw.Draw(img)
        draw.text((0,0), "Test", font=font)
        print("Render Success")
    except Exception as e:
        print(f"FAIL: {e}")

# Test Default
test_load("Default", None)

# Test Basic
# Check if Layout exists
if hasattr(ImageFont, 'Layout'):
    test_load("BASIC (0)", ImageFont.Layout.BASIC)
    if hasattr(ImageFont.Layout, 'RAQM'):
         test_load("RAQM", ImageFont.Layout.RAQM)
else:
    print("ImageFont.Layout not available")
