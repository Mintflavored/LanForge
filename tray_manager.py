"""
Windows System Tray & Notification Manager for LANForge.
Runs in a background thread and interacts with the PyWebView desktop window.
"""

import threading
from PIL import Image
import pystray

class TrayManager:
    def __init__(self, icon_path, app_name="LANForge", on_show=None, on_quit=None):
        self.icon_path = icon_path
        self.app_name = app_name
        self.on_show = on_show
        self.on_quit = on_quit
        self.tray = None
        self.status_text = "Вне сети"
        self.my_ip = "10.42.0.1"
        self._thread = None

    def _create_menu(self):
        return pystray.Menu(
            pystray.MenuItem(f"{self.app_name} (v1.5.0)", None, enabled=False),
            pystray.MenuItem(lambda text: f"Статус: {self.status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Показать окно", self._action_show, default=True),
            pystray.MenuItem("Скопировать мой IP", self._action_copy_ip),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._action_quit)
        )

    def _action_show(self, icon, item):
        if self.on_show:
            self.on_show()

    def _action_copy_ip(self, icon, item):
        try:
            import subprocess
            subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{self.my_ip}'"], check=True, creationflags=0x08000000)
            self.notify("LANForge", f"IP {self.my_ip} скопирован в буфер обмена")
        except Exception:
            pass

    def _action_quit(self, icon, item):
        if self.tray:
            self.tray.stop()
        if self.on_quit:
            self.on_quit()

    def update_status(self, text, ip="10.42.0.1"):
        self.status_text = text
        self.my_ip = ip
        if self.tray:
            self.tray.update_menu()

    def notify(self, title, message):
        if self.tray:
            try:
                self.tray.notify(message, title)
            except Exception:
                pass

    def start(self):
        try:
            image = Image.open(self.icon_path)
        except Exception:
            image = Image.new("RGBA", (64, 64), color=(255, 85, 0, 255))

        self.tray = pystray.Icon(
            name="LANForge",
            icon=image,
            title=f"{self.app_name} — Virtual LAN",
            menu=self._create_menu()
        )
        try:
            self.tray.run_detached()
        except Exception as e:
            print(f"[Tray Start Error] {e}")

    def stop(self):
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
