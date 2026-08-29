"""
LANForge Desktop Launcher (GPU-Accelerated & Proxy/VPN Resilient)
DirectX 11/12 GPU composition, zero-proxy loopback bypass, Clash Verge & VPN-safe.
Auto-manages Go backend server lifecycle with zero orphaned processes.
"""

__version__ = "1.4.0"

import os
import sys
import time
import socket
import subprocess
import atexit

# Ensure local loopback connections completely bypass system proxies & Clash Verge
PROXY_BYPASS = "localhost,127.0.0.1,::1,10.0.0.0/8,192.168.0.0/16,172.16.0.0/12,*.local,10.42.*"
os.environ["NO_PROXY"] = PROXY_BYPASS
os.environ["no_proxy"] = PROXY_BYPASS

# Edge WebView2 Chromium flags for proxy bypass, zero-CORS file restrictions, and hardware GPU acceleration
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    f"--proxy-bypass-list={PROXY_BYPASS} "
    "--disable-web-security "
    "--allow-file-access-from-files "
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

server_proc = None

def is_port_open(host="127.0.0.1", port=8787):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def start_backend_server():
    global server_proc
    if is_port_open("127.0.0.1", 8787):
        return  # Server already running

    server_bin = os.path.join(base_dir, "bin", "lanforge-server.exe")
    if not os.path.exists(server_bin):
        server_bin = os.path.join(base_dir, "lanforge-server.exe")

    if os.path.exists(server_bin):
        creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        server_proc = subprocess.Popen(
            [server_bin, "-port", "8787"],
            creationflags=creation_flags
        )
        # Wait up to 1.5s for port to become active
        for _ in range(15):
            time.sleep(0.1)
            if is_port_open("127.0.0.1", 8787):
                break

def stop_backend_server():
    global server_proc
    if server_proc:
        try:
            server_proc.terminate()
            server_proc.wait(timeout=1.0)
        except Exception:
            try:
                server_proc.kill()
            except Exception:
                pass
        server_proc = None

atexit.register(stop_backend_server)

def main():
    start_backend_server()

    window = webview.create_window(
        title="LANForge",
        url=html_path,
        width=980,
        height=640,
        min_size=(860, 540),
        background_color="#09090b",
        easy_drag=False
    )
    window.events.closed += stop_backend_server

    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()
