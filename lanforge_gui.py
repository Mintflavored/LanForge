"""
LANForge Desktop Launcher (GPU-Accelerated & Proxy/VPN Resilient)
DirectX 11/12 GPU composition, zero-proxy loopback bypass, Clash Verge & VPN-safe.
"""

__version__ = "1.3.0"

import os
import sys

# Ensure local loopback connections completely bypass system proxies & Clash Verge
PROXY_BYPASS = "localhost,127.0.0.1,::1,10.0.0.0/8,192.168.0.0/16,172.16.0.0/12,*.local,10.42.*"
os.environ["NO_PROXY"] = PROXY_BYPASS
os.environ["no_proxy"] = PROXY_BYPASS

# Edge WebView2 Chromium flags for proxy bypass and high performance
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    f"--proxy-bypass-list={PROXY_BYPASS} "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--disable-features=OutOfProcessOpengl"
)

import webview

# Determine root directory (both in development and PyInstaller bundled mode)
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    base_dir = os.path.dirname(exe_dir) if os.path.basename(exe_dir).lower() == "bin" else exe_dir
    html_path = os.path.join(base_dir, "ui", "index.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(sys._MEIPASS, "ui", "index.html")
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "ui", "index.html")

def main():
    window = webview.create_window(
        title="LANForge",
        url=html_path,
        width=980,
        height=640,
        min_size=(860, 540),
        background_color="#09090b",
        easy_drag=False
    )
    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()
