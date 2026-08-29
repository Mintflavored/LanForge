"""
Generate high-resolution Windows .ico and .png application icons for LANForge.
"""

import os
from PIL import Image, ImageDraw

def create_lanforge_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base coordinates for Isometric Network Cube
    cx, cy = 128, 128
    r = 96

    # Gradient-like glowing polygonal structure
    # Top face
    p_top = [(cx, cy - r), (cx + r * 0.866, cy - r * 0.5), (cx, cy), (cx - r * 0.866, cy - r * 0.5)]
    # Left face
    p_left = [(cx - r * 0.866, cy - r * 0.5), (cx, cy), (cx, cy + r), (cx - r * 0.866, cy + r * 0.5)]
    # Right face
    p_right = [(cx, cy), (cx + r * 0.866, cy - r * 0.5), (cx + r * 0.866, cy + r * 0.5), (cx, cy + r)]

    # Draw dark translucent inner faces
    draw.polygon(p_top, fill=(24, 24, 28, 220))
    draw.polygon(p_left, fill=(18, 18, 22, 240))
    draw.polygon(p_right, fill=(14, 14, 18, 255))

    # Outer and inner border lines (Orange to Red Neon Glow)
    accent_orange = (255, 85, 0, 255)
    accent_red = (239, 68, 68, 255)

    # Draw strokes
    draw.line([(cx, cy - r), (cx + r * 0.866, cy - r * 0.5)], fill=accent_orange, width=7)
    draw.line([(cx + r * 0.866, cy - r * 0.5), (cx + r * 0.866, cy + r * 0.5)], fill=accent_red, width=7)
    draw.line([(cx + r * 0.866, cy + r * 0.5), (cx, cy + r)], fill=accent_red, width=7)
    draw.line([(cx, cy + r), (cx - r * 0.866, cy + r * 0.5)], fill=accent_orange, width=7)
    draw.line([(cx - r * 0.866, cy + r * 0.5), (cx - r * 0.866, cy - r * 0.5)], fill=accent_orange, width=7)
    draw.line([(cx - r * 0.866, cy - r * 0.5), (cx, cy - r)], fill=accent_orange, width=7)

    # Inner Y-axis lines
    draw.line([(cx, cy), (cx, cy - r)], fill=accent_orange, width=6)
    draw.line([(cx, cy), (cx - r * 0.866, cy + r * 0.5)], fill=accent_orange, width=6)
    draw.line([(cx, cy), (cx + r * 0.866, cy + r * 0.5)], fill=accent_red, width=6)

    # Glowing Core Node in center
    node_r = 18
    draw.ellipse([cx - node_r, cy - node_r, cx + node_r, cy + node_r], fill=accent_orange, outline=accent_red, width=3)
    core_r = 8
    draw.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(255, 255, 255, 255))

    # Save PNG and multi-resolution ICO
    img.save("app_icon.png")
    img.save(
        "app.ico",
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    print("app.ico and app_icon.png created successfully!")

if __name__ == "__main__":
    create_lanforge_icon()
