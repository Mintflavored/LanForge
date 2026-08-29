"""
Generate ultra-clean, professional Discord Cover Banner for LANForge without banding/circles.
Uses smooth Gaussian ambient glow, subtle cyber-grid, and high-res isometric branding.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os

def create_smooth_banner():
    width, height = 1920, 1080

    # 1. Base dark background
    base = Image.new("RGBA", (width, height), (9, 9, 11, 255))

    # 2. Smooth ambient glow layer (no stepped circles!)
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # Soft ambient orange glow on the left behind the cube
    glow_draw.ellipse([150, 150, 750, 850], fill=(255, 85, 0, 180))
    # Soft ambient red/crimson glow on the right
    glow_draw.ellipse([1100, 200, 1700, 800], fill=(239, 68, 68, 120))

    # Heavy Gaussian blur to create a seamless, buttery smooth diffuse lighting
    glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=160))
    base = Image.alpha_composite(base, glow_blurred)

    # 3. Precise cyber-mesh overlay
    grid_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_layer)

    for x in range(0, width, 48):
        grid_draw.line([(x, 0), (x, height)], fill=(39, 39, 42, 35), width=1)
    for y in range(0, height, 48):
        grid_draw.line([(0, y), (width, y)], fill=(39, 39, 42, 35), width=1)

    # Subtle diagonal connection ray
    grid_draw.line([(0, height), (width, 0)], fill=(255, 85, 0, 15), width=2)
    grid_draw.line([(0, height - 300), (width - 300, 0)], fill=(239, 68, 68, 12), width=1)

    base = Image.alpha_composite(base, grid_layer)

    # 4. Paste high-res glowing 3D Forge Cube
    icon_path = "app_icon.png"
    if os.path.exists(icon_path):
        icon = Image.open(icon_path).convert("RGBA")
        icon_resized = icon.resize((500, 500), Image.Resampling.LANCZOS)
        # Drop shadow behind cube
        shadow = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse([40, 40, 480, 480], fill=(0, 0, 0, 140))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=40))
        base.paste(shadow, (220, 290), shadow)
        base.paste(icon_resized, (230, 280), icon_resized)

    # 5. Crisp typography
    draw = ImageDraw.Draw(base)

    try:
        font_large = ImageFont.truetype("arialbd.ttf", 108)
        font_sub = ImageFont.truetype("arialbd.ttf", 34)
        font_mono = ImageFont.truetype("consola.ttf", 22)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    tx = 800
    ty = 370

    # Title: LANFORGE.
    draw.text((tx, ty), "LANFORGE", font=font_large, fill=(255, 255, 255, 255))
    draw.text((tx + 665, ty), ".", font=font_large, fill=(255, 85, 0, 255))

    # Subtitle
    draw.text((tx + 4, ty + 135), "NEXT-GEN P2P VIRTUAL GAMING HUB", font=font_sub, fill=(161, 161, 170, 255))

    # Feature badges
    badges = [
        ("DIRECT P2P", (34, 197, 94, 255)),
        ("ZERO-CONFIG NAT", (255, 85, 0, 255)),
        ("PROMETHEUS ENGINE", (161, 161, 170, 255)),
        ("BY NERVS", (239, 68, 68, 255))
    ]

    bx = tx + 4
    by = ty + 210
    for label, col in badges:
        text_w = len(label) * 13 + 28
        draw.rounded_rectangle([bx, by, bx + text_w, by + 36], radius=6, fill=(24, 24, 28, 220), outline=(39, 39, 42, 255))
        draw.text((bx + 14, by + 7), label, font=font_mono, fill=col)
        bx += text_w + 12

    base.save("discord_banner.png", "PNG")
    print("[SUCCESS] Re-generated smooth studio-grade discord_banner.png (1920x1080)")

if __name__ == "__main__":
    create_smooth_banner()
