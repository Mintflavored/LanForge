r"""
LANForge Desktop Launcher (v1.7.2)
- Discord Rich Presence (RPC) Integration
- Windows System Tray & Native Toast Notifications
- DirectX 11/12 GPU composition, zero-proxy loopback bypass, Clash Verge & VPN-safe
- Hybrid Cloud & Local Signaling support
- Unified Rotating File Logger (%APPDATA%\LANForge\lanforge.log)
- Zero-Driver P2P Game Data Tunnel with auto-reconnect & session recovery
"""

__version__ = "1.7.2"

import os
import sys
import json
import time
import socket
import logging
import platform
import subprocess
import atexit
import threading
from logging.handlers import RotatingFileHandler

# AppData configuration & logs directory
app_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LANForge")
os.makedirs(app_data_dir, exist_ok=True)
CONFIG_FILE = os.path.join(app_data_dir, "config.json")
LOG_FILE = os.path.join(app_data_dir, "lanforge.log")

# Setup Rotating File Logger
logger = logging.getLogger("LANForge")
logger.setLevel(logging.DEBUG)
log_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
formatter = logging.Formatter(
    "[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

logger.info(f"=== LANForge v{__version__} Starting ===")
logger.info(f"OS: {platform.platform()} ({platform.architecture()[0]})")
logger.info(f"Python: {sys.version.split()[0]} | Executable: {sys.executable}")
logger.info(f"AppData Directory: {app_data_dir}")

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
            logger.info("Local Go server already active on 127.0.0.1:8787")
            return

        candidates = []
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "lanforge-server.exe"))
            candidates.append(os.path.join(sys._MEIPASS, "bin", "lanforge-server.exe"))
        candidates.extend([
            os.path.join(exe_dir, "lanforge-server.exe"),
            os.path.join(exe_dir, "bin", "lanforge-server.exe"),
            os.path.join(base_dir, "bin", "lanforge-server.exe"),
            os.path.join(base_dir, "lanforge-server.exe")
        ])
        server_bin = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                server_bin = cand
                break

        if server_bin:
            logger.info(f"Spawning local Go server binary: {server_bin}")
            creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            server_proc = subprocess.Popen(
                [server_bin, "-port", "8787"],
                cwd=os.path.dirname(server_bin),
                creationflags=creation_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            def pipe_stream(stream, is_err=False):
                try:
                    for line in iter(stream.readline, b''):
                        msg = line.decode('utf-8', errors='ignore').strip()
                        if msg:
                            if is_err:
                                logger.error(f"[GoServer] {msg}")
                            else:
                                logger.info(f"[GoServer] {msg}")
                except Exception:
                    pass

            threading.Thread(target=pipe_stream, args=(server_proc.stdout, False), daemon=True).start()
            threading.Thread(target=pipe_stream, args=(server_proc.stderr, True), daemon=True).start()

            for _ in range(30):
                time.sleep(0.1)
                if is_port_open("127.0.0.1", 8787):
                    logger.info("Local Go server successfully listening on 127.0.0.1:8787")
                    break
        else:
            logger.warning("No local lanforge-server.exe binary found in candidates.")
    except Exception as e:
        logger.error(f"[Backend Spawn Error] {e}")

def stop_backend_server():
    global server_proc
    if server_proc:
        try:
            logger.info("Terminating local Go server...")
            server_proc.terminate()
            server_proc.wait(timeout=1.0)
        except Exception:
            try:
                server_proc.kill()
            except Exception:
                pass
        server_proc = None

atexit.register(stop_backend_server)

def load_user_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                logger.info(f"Loaded config: {cfg}")
                return cfg
    except Exception as e:
        logger.error(f"[Config Read Error] {e}")
    return {}

def save_user_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved config: {data}")
        return True
    except Exception as e:
        logger.error(f"[Config Write Error] {e}")
        return False

class JsApi:
    """JS Bridge allowing UI to interact with Windows Native features, persistent config & logs."""

    def log(self, level, tag, message):
        lvl = str(level).lower()
        text = f"[{tag}] {message}"
        if lvl == "error":
            logger.error(text)
        elif lvl in ("warn", "warning"):
            logger.warning(text)
        elif lvl == "debug":
            logger.debug(text)
        else:
            logger.info(text)

    def open_log_dir(self):
        try:
            os.startfile(app_data_dir)
            logger.info(f"Opened log directory: {app_data_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to open log dir: {e}")
            return False

    def get_log_content(self, max_lines=250):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    return "".join(lines[-max_lines:])
        except Exception as e:
            return f"Error reading log file: {e}"
        return "Лог-файл пуст."

    def get_config(self):
        return load_user_config()

    def save_config(self, cfg_data):
        if isinstance(cfg_data, str):
            try:
                cfg_data = json.loads(cfg_data)
            except Exception:
                pass
        return save_user_config(cfg_data)

    def update_presence(self, details, state, party_size=None, party_max=16, room_code=None, game_preset=None):
        try:
            discord.set_activity(
                details=details,
                state=state,
                party_size=party_size,
                party_max=party_max,
                room_code=room_code,
                game_preset=game_preset
            )
        except Exception as e:
            logger.warning(f"[Discord RPC Error] {e}")

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
    logger.info("Application quitting requested.")
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
    discord.set_activity("В главном меню", f"P2P Virtual Gaming Hub v{__version__}")

    api = JsApi()

    main_window = webview.create_window(
        title="LANForge",
        url=html_path,
        js_api=api,
        width=1040,
        height=660,
        min_size=(1040, 660),
        resizable=True,
        background_color="#09090b",
        easy_drag=False
    )

    def on_closed():
        logger.info("Main window closed event triggered.")
        if tray:
            tray.stop()
        stop_backend_server()

    main_window.events.closed += on_closed

    webview.start(gui="edgechromium", debug=False, storage_path=app_data_dir)

if __name__ == "__main__":
    main()
