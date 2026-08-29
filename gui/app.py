"""
LANForge Desktop Application Entrypoint (With Pre-Warming & Win32 Render Profiler)
"""

import os
import sys
import time
import ctypes
import customtkinter as ctk
from tkinter import messagebox

# Win32 GDI Repaint Control
user32 = ctypes.windll.user32
WM_SETREDRAW = 0x000B
RDW_INVALIDATE = 0x0001
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
RDW_ERASE = 0x0004
REDRAW_FLAGS = RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW | RDW_ERASE

# Determine true workspace directory (even when packed in PyInstaller Temp dir)
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    workspace_dir = os.path.dirname(exe_dir) if os.path.basename(exe_dir).lower() == "bin" else exe_dir
else:
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

cur_dir = os.path.dirname(os.path.abspath(__file__))
for p in (cur_dir, workspace_dir):
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

class RenderProfiler:
    """High-precision render and frame timing telemetry."""
    def __init__(self, log_path=None):
        self.log_path = log_path or os.path.join(workspace_dir, "render_metrics.log")
        self.records = []
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write(f"=== LANForge Render Telemetry Log ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        except Exception:
            pass

    def record_switch(self, from_tab, to_tab, t_freeze_ms, t_swap_ms, t_idle_ms, t_redraw_ms, total_ms):
        record = {
            "from_tab": from_tab,
            "to_tab": to_tab,
            "freeze_lock_ms": round(t_freeze_ms, 3),
            "view_swap_ms": round(t_swap_ms, 3),
            "idle_layout_ms": round(t_idle_ms, 3),
            "gdi_redraw_ms": round(t_redraw_ms, 3),
            "total_latency_ms": round(total_ms, 3),
            "timestamp": time.time()
        }
        self.records.append(record)
        log_line = (
            f"[{time.strftime('%H:%M:%S')}] Tab Switch '{from_tab}' -> '{to_tab}': "
            f"Total={record['total_latency_ms']}ms "
            f"(Freeze={record['freeze_lock_ms']}ms, Swap={record['view_swap_ms']}ms, "
            f"Layout={record['idle_layout_ms']}ms, Redraw={record['gdi_redraw_ms']}ms)\n"
        )
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    def save_summary(self):
        if not self.records:
            return
        avg_total = sum(r["total_latency_ms"] for r in self.records) / len(self.records)
        max_total = max(r["total_latency_ms"] for r in self.records)
        min_total = min(r["total_latency_ms"] for r in self.records)

        summary = (
            f"\n--- BENCHMARK SUMMARY ({len(self.records)} switches) ---\n"
            f"Average Switch Latency: {avg_total:.2f} ms\n"
            f"Min Switch Latency:     {min_total:.2f} ms\n"
            f"Max Switch Latency:     {max_total:.2f} ms\n"
            f"Status: {'PERFECT (Sub-16ms V-Sync Frame)' if max_total < 16.6 else ('Smooth' if max_total < 35 else 'Solid')}\n"
        )
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(summary)
        except Exception:
            pass


class LANForgeApp(ctk.CTk):
    def __init__(self, benchmark_mode=False):
        super().__init__()

        self.title("LANForge — P2P Virtual Network")
        self.geometry("980x640")
        self.minsize(860, 540)
        self.configure(fg_color=BG_COLOR)

        self.benchmark_mode = benchmark_mode
        self.profiler = RenderProfiler(log_path=os.path.join(workspace_dir, "render_metrics.log"))

        self.nick = f"User_{int(time.time()) % 1000}"
        self.client = NetworkClient(server_url="ws://localhost:8787", nick=self.nick)

        self.active_tab = "overview"
        self.known_peer_ids = set()

        self._setup_layout()
        self._prewarm_all_views()
        self._bind_client_events()
        self._show_tab("overview")

        if self.benchmark_mode:
            self.after(200, self._run_benchmark_cycle)

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top Navigation Bar Component
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

        # Instantiate View Components
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

    def _prewarm_all_views(self):
        """Pre-warms all view layouts into GDI device context during startup to eliminate first-switch latency."""
        hwnd = self.winfo_id()
        user32.SendMessageW(hwnd, WM_SETREDRAW, 0, 0)
        for name, view in self.views.items():
            view.grid(row=0, column=0, sticky="nsew")
            self.update_idletasks()
            view.grid_remove()
        user32.SendMessageW(hwnd, WM_SETREDRAW, 1, 0)

    def _show_tab(self, tab_id):
        old_tab = self.active_tab
        self.active_tab = tab_id
        self.nav_bar.set_active_tab(tab_id)

        t0 = time.perf_counter_ns()
        hwnd = self.winfo_id()

        # Step 1: Win32 Freeze
        t_before_freeze = time.perf_counter_ns()
        user32.SendMessageW(hwnd, WM_SETREDRAW, 0, 0)
        t_after_freeze = time.perf_counter_ns()

        # Step 2: Swap Views in Grid
        t_before_swap = time.perf_counter_ns()
        for name, view in self.views.items():
            if name == tab_id:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_remove()
        t_after_swap = time.perf_counter_ns()

        # Step 3: Layout calculation
        t_before_idle = time.perf_counter_ns()
        self.update_idletasks()
        t_after_idle = time.perf_counter_ns()

        # Step 4: Win32 Unfreeze & Atomic Paint
        t_before_redraw = time.perf_counter_ns()
        user32.SendMessageW(hwnd, WM_SETREDRAW, 1, 0)
        user32.RedrawWindow(hwnd, None, None, REDRAW_FLAGS)
        t_after_redraw = time.perf_counter_ns()

        t_end = time.perf_counter_ns()

        freeze_ms = (t_after_freeze - t_before_freeze) / 1_000_000
        swap_ms = (t_after_swap - t_before_swap) / 1_000_000
        idle_ms = (t_after_idle - t_before_idle) / 1_000_000
        redraw_ms = (t_after_redraw - t_before_redraw) / 1_000_000
        total_ms = (t_end - t0) / 1_000_000

        self.profiler.record_switch(old_tab, tab_id, freeze_ms, swap_ms, idle_ms, redraw_ms, total_ms)

    def _run_benchmark_cycle(self):
        """Automated test sequence cycling through all tabs."""
        sequence = [
            "games", "overview", "radar", "games", "chat",
            "diag", "games", "overview", "chat", "radar", "games"
        ]
        
        def _step(idx):
            if idx < len(sequence):
                tab = sequence[idx]
                self._show_tab(tab)
                self.after(120, lambda: _step(idx + 1))
            else:
                self.profiler.save_summary()
                self.after(200, self.destroy)

        _step(0)

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
    benchmark = "--benchmark" in sys.argv or "--autotest" in sys.argv
    app = LANForgeApp(benchmark_mode=benchmark)
    app.mainloop()
