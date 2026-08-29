"""
Generate Discord Cover Banner and RPC Art Assets for LANForge.
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

def create_banner():
    width, height = 1920, 1080
    img = Image.new("RGBA", (width, height), (9, 9, 11, 255))
    draw = ImageDraw.Draw(img)

    # 1. Dark glowing ambient radial gradients
    # Center-left glow (Orange #ff5500)
    cx, cy = 540, 540
    for r in range(450, 0, -4):
        alpha = int(45 * (1 - r / 450)**2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 85, 0, alpha))

    # Center-right glow (Red #ef4444)
    cx2, cy2 = 1380, 540
    for r in range(400, 0, -4):
        alpha = int(35 * (1 - r / 400)**2)
        draw.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r], fill=(239, 68, 68, alpha))

    # 2. Cyber-grid pattern in background
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(39, 39, 42, 40), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(39, 39, 42, 40), width=1)

    # 3. Load or Draw Glowing Isometric Cube in center-left
    icon_path = "app_icon.png"
    if os.path.exists(icon_path):
        icon = Image.open(icon_path).convert("RGBA")
        icon_resized = icon.resize((480, 480), Image.Resampling.LANCZOS)
        img.paste(icon_resized, (240, 300), icon_resized)

    # 4. Text & Branding on the right
    # Title: LANFORGE
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 110)
        font_sub = ImageFont.truetype("arial.ttf", 36)
        font_mono = ImageFont.truetype("consola.ttf", 26)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    tx = 820
    ty = 360
    # Glow behind text
    draw.text((tx, ty), "LANFORGE", font=font_large, fill=(255, 85, 0, 255))
    draw.text((tx + 690, ty), ".", font=font_large, fill=(239, 68, 68, 255))

    # Subtitle
    draw.text((tx + 6, ty + 140), "NEXT-GEN P2P VIRTUAL GAMING HUB", font=font_sub, fill=(255, 255, 255, 240))

    # Feature badges row
    badges = ["DIRECT UDP P2P", "ZERO LATENCY", "VPN & PROXY SAFE", "BY NERVS"]
    bx = tx + 6
    by = ty + 220
    for b in badges:
        col = (255, 85, 0, 255) if b == "BY NERVS" else (161, 161, 170, 255)
        # pill background
        draw.rounded_rectangle([bx, by, bx + len(b) * 16 + 24, by + 38], radius=6, fill=(24, 24, 28, 200), outline=(39, 39, 42, 255))
        draw.text((bx + 12, by + 7), b, font=font_mono, fill=col)
        bx += len(b) * 16 + 36

    img.save("discord_banner.png", "PNG")
    print("Created discord_banner.png (1920x1080)")

if __name__ == "__main__":
    create_banner()
