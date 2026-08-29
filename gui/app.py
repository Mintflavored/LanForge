"""
LANForge Desktop Application Entrypoint (Ultra-Fast Opaque View Switching)
"""

import os
import sys
import time
import customtkinter as ctk
from tkinter import messagebox

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(cur_dir)
for p in (cur_dir, root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from gui.theme import BG_COLOR
from gui.events import NetworkEvents
from gui.network_client import NetworkClient
from gui.anim import ToastNotification
from gui.components import TopNavBar, CreateRoomDialog, JoinRoomDialog
from gui.views import OverviewView, GamesView, RadarView, ChatView, DiagView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LANForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LANForge — P2P Virtual Network")
        self.geometry("980x640")
        self.minsize(860, 540)
        self.configure(fg_color=BG_COLOR)

        self.nick = f"User_{int(time.time()) % 1000}"
        self.client = NetworkClient(server_url="ws://localhost:8787", nick=self.nick)

        self.active_tab = "overview"
        self.known_peer_ids = set()

        self._setup_layout()
        self._bind_client_events()
        self._show_tab("overview")

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top Navigation Bar Component (with animated sliding pill)
        self.nav_bar = TopNavBar(
            self,
            on_tab_selected=self._show_tab,
            on_create_clicked=self._open_create_dialog,
            on_join_clicked=self._open_join_dialog
        )
        self.nav_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 6))

        # Main Views Container (Dedicated Grid Cell)
        self.main_container = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(4, 16))
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Instantiate View Components into the exact same grid cell
        self.views = {
            "overview": OverviewView(
                self.main_container,
                client=self.client,
                on_create_requested=self._open_create_dialog,
                on_join_requested=self._open_join_dialog,
                copy_helper=self._copy_with_feedback
            ),
            "games": GamesView(
                self.main_container,
                on_preset_selected=self._open_create_dialog
            ),
            "radar": RadarView(
                self.main_container,
                client=self.client,
                copy_helper=self._copy_with_feedback
            ),
            "chat": ChatView(
                self.main_container,
                client=self.client
            ),
            "diag": DiagView(self.main_container),
        }

    def _show_tab(self, tab_id):
        self.active_tab = tab_id
        self.nav_bar.set_active_tab(tab_id)

        # Atomic 0ms switch: map active view, remove others from paint tree
        for name, view in self.views.items():
            if name == tab_id:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_remove()

    def show_toast(self, text, toast_type="orange"):
        """Displays floating animated toast notification."""
        try:
            ToastNotification(self, text=text, toast_type=toast_type)
        except Exception:
            pass

    def _open_create_dialog(self, default_preset=None):
        CreateRoomDialog(self, client=self.client, default_preset=default_preset)

    def _open_join_dialog(self):
        JoinRoomDialog(self, client=self.client)

    def _copy_with_feedback(self, button, original_text, text_to_copy):
        try:
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            self.update()
            button.configure(text="✓ Скопировано")
            self.show_toast(f"Скопировано: {text_to_copy}", toast_type="green")
            self.after(1200, lambda: button.configure(text=original_text))
        except Exception:
            pass

    def _bind_client_events(self):
        def on_room(room):
            try:
                if room:
                    current_peer_ids = {p["id"] for p in room.get("peers", [])}
                    new_peers = [p for p in room.get("peers", []) if p["id"] not in self.known_peer_ids and (not self.client.you or p["id"] != self.client.you.get("id"))]
                    if new_peers and len(self.known_peer_ids) > 0:
                        for np in new_peers:
                            self.show_toast(f"Игрок {np.get('nick')} подключился к сети", toast_type="green")
                    self.known_peer_ids = current_peer_ids
                else:
                    self.known_peer_ids.clear()

                self.after(0, lambda: self.views["overview"].update_state(room, self.client.you))
                if not room:
                    self.after(0, self.views["chat"].reset_chat)
            except Exception:
                pass

        def on_ping(rtt):
            try:
                self.after(0, lambda: self.views["overview"].update_ping(rtt))
            except Exception:
                pass

        def on_chat(msg):
            try:
                self.after(0, lambda: self.views["chat"].append_message(msg))
                if self.active_tab != "chat":
                    self.show_toast(f"{msg.get('fromNick')}: {msg.get('text')}", toast_type="orange")
            except Exception:
                pass

        def on_game(game):
            try:
                self.after(0, self.views["radar"].update_radar)
                self.show_toast(f"Обнаружен LAN-мир: {game.get('name')}", toast_type="green")
            except Exception:
                pass

        def on_error(err_msg):
            try:
                self.after(0, lambda: messagebox.showwarning("Ошибка LANForge", err_msg))
            except Exception:
                pass

        self.client.on(NetworkEvents.ROOM_STATE, on_room)
        self.client.on(NetworkEvents.PING, on_ping)
        self.client.on(NetworkEvents.CHAT_MESSAGE, on_chat)
        self.client.on(NetworkEvents.DISCOVERED_GAME, on_game)
        self.client.on(NetworkEvents.ERROR, on_error)

if __name__ == "__main__":
    app = LANForgeApp()
    app.mainloop()
