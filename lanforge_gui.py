"""
LANForge Desktop Launcher (v1.5.0)
- Discord Rich Presence (RPC) Integration
- Windows System Tray & Native Toast Notifications
- DirectX 11/12 GPU composition, zero-proxy loopback bypass, Clash Verge & VPN-safe
- Auto-manages Go backend server lifecycle with zero orphaned processes
"""

__version__ = "1.5.0"

import os
import sys
import time
import socket
import subprocess
import atexit
import threading

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
from discord_rpc import discord
from tray_manager import TrayManager

# Determine root directory (both in development and PyInstaller bundled mode)
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    base_dir = os.path.dirname(exe_dir) if os.path.basename(exe_dir).lower() == "bin" else exe_dir
    html_path = os.path.join(base_dir, "ui", "index.html")
    icon_path = os.path.join(base_dir, "app_icon.png")
    if not os.path.exists(html_path):
        html_path = os.path.join(sys._MEIPASS, "ui", "index.html")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(sys._MEIPASS, "app_icon.png")
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.path.join(base_dir, "bin")
    html_path = os.path.join(base_dir, "ui", "index.html")
    icon_path = os.path.join(base_dir, "app_icon.png")

server_proc = None
main_window = None
tray = None

def is_port_open(host="127.0.0.1", port=8787):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def start_backend_server():
    global server_proc
    try:
        if is_port_open("127.0.0.1", 8787):
            return  # Server already running

        candidates = [
            os.path.join(exe_dir, "lanforge-server.exe"),
            os.path.join(base_dir, "bin", "lanforge-server.exe"),
            os.path.join(base_dir, "lanforge-server.exe")
        ]
        server_bin = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                server_bin = cand
                break

        if server_bin:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            server_proc = subprocess.Popen(
                [server_bin, "-port", "8787"],
                cwd=os.path.dirname(server_bin),
                creationflags=creation_flags
            )
            for _ in range(25):
                time.sleep(0.1)
                if is_port_open("127.0.0.1", 8787):
                    break
    except Exception as e:
        print(f"[Backend Spawn Error] {e}")

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

class JsApi:
    """JS Bridge allowing UI to interact with Windows Native features."""

    def update_presence(self, details, state, party_size=None, party_max=16, room_code=None):
        try:
            discord.set_activity(
                details=details,
                state=state,
                party_size=party_size,
                party_max=party_max,
                room_code=room_code
            )
        except Exception as e:
            print(f"[Discord RPC Error] {e}")

    def update_tray(self, status_text, my_ip):
        if tray:
            tray.update_status(status_text, my_ip)

    def show_notification(self, title, message):
        if tray:
            tray.notify(title, message)

def on_show_window():
    global main_window
    if main_window:
        try:
            main_window.show()
            main_window.restore()
        except Exception:
            pass

def on_quit_app():
    global main_window
    stop_backend_server()
    if main_window:
        try:
            main_window.destroy()
        except Exception:
            pass
    sys.exit(0)

def main():
    global main_window, tray

    start_backend_server()

    # Initialize Windows System Tray
    tray = TrayManager(
        icon_path=icon_path,
        app_name="LANForge",
        on_show=on_show_window,
        on_quit=on_quit_app
    )
    tray.start()

    # Initial Discord RPC Status
    discord.set_activity("В главном меню", "P2P Virtual Gaming Hub v1.5.0")

    api = JsApi()

    main_window = webview.create_window(
        title="LANForge",
        url=html_path,
        js_api=api,
        width=980,
        height=640,
        min_size=(860, 540),
        background_color="#09090b",
        easy_drag=False
    )

    def on_closed():
        if tray:
            tray.stop()
        stop_backend_server()

    main_window.events.closed += on_closed

    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()
