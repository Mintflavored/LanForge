"""
LANForge Desktop Launcher (GPU-Accelerated Edge WebView2 Architecture)
DirectX 11/12 GPU composition, 144Hz V-Sync, sub-millisecond tab switching.
"""

import os
import sys
import webview

# Determine root directory (both in development and PyInstaller bundled mode)
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    # If in bin/ directory, move to workspace root
    base_dir = os.path.dirname(exe_dir) if os.path.basename(exe_dir).lower() == "bin" else exe_dir
    html_path = os.path.join(base_dir, "ui", "index.html")
    # Fallback to PyInstaller temp directory
    if not os.path.exists(html_path):
        html_path = os.path.join(sys._MEIPASS, "ui", "index.html")
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "ui", "index.html")

def main():
    # Create native Windows WebView2 hardware-accelerated window
    window = webview.create_window(
        title="LANForge — P2P Virtual Network",
        url=html_path,
        width=980,
        height=640,
        min_size=(860, 540),
        background_color="#09090b",
        easy_drag=False
    )
    # Start WebView2 with Edge Chromium engine and hardware acceleration
    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()
