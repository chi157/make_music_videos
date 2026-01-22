import os
from fontTools.ttLib import TTFont

input_font = "ChenYuluoyan-2.0-Thin.ttf"
output_font = "ChenYuluoyan-2.0-Thin_fixed.ttf"

search_paths = [
    os.path.join(os.getcwd(), input_font),
    os.path.join(r"C:\Windows\Fonts", input_font),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts", input_font),
    # Also check project dir explicitly
    os.path.join("e:\\My Project\\make_music_videos", input_font)
]

found_path = None
for p in search_paths:
    if os.path.exists(p):
        found_path = p
        break

if not found_path:
    print(f"Error: Could not find {input_font}")
    exit(1)

print(f"Processing: {found_path}")

try:
    font = TTFont(found_path)
    
    # Tables related to TrueType hinting/instructions
    # Removing these disables the bytecode instructions causing "too many function definitions"
    hinting_tables = ['fpgm', 'prep', 'cvt ', 'hdmx', 'LTSH', 'VDMX', 'gasp']
    
    removed_count = 0
    for tag in hinting_tables:
        if tag in font:
            del font[tag]
            removed_count += 1
            
    print(f"Removed {removed_count} hinting tables.")
    
    output_path = os.path.join(os.path.dirname(__file__), output_font)
    font.save(output_path)
    print(f"Saved optimized font to: {output_path}")

except Exception as e:
    print(f"Failed to fix font: {e}")
    exit(1)
