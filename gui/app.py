import os
import sys
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(cur_dir)
for p in (cur_dir, root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from presets_data import GAME_PRESETS
    from network_client import NetworkClient
except ImportError:
    from gui.presets_data import GAME_PRESETS
    from gui.network_client import NetworkClient

# Theme Configuration: Zinc Dark (Clean, Minimalist Desktop Utility)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_BG = "#121214"
COLOR_SIDEBAR = "#18181b"
COLOR_SURFACE = "#202024"
COLOR_SURFACE_HOVER = "#27272a"
COLOR_BORDER = "#2e2e33"
COLOR_TEXT = "#f4f4f5"
COLOR_MUTED = "#71717a"
COLOR_ACCENT = "#3b82f6"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_GREEN = "#22c55e"
COLOR_RED = "#ef4444"
COLOR_AMBER = "#f59e0b"

FONT_MAIN = "Segoe UI"
FONT_MONO = "Consolas"

class LANForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LANForge — Virtual LAN Gaming Hub")
        self.geometry("920x620")
        self.minsize(820, 520)
        self.configure(fg_color=COLOR_BG)

        self.nick = f"Player_{int(time.time()) % 1000}"
        self.client = NetworkClient(server_url="ws://localhost:8787", nick=self.nick)

        self.active_tab = "network"
        self.preset_filter = "Все"
        self.search_term = ""

        self._setup_layout()
        self._bind_client_events()
        self._show_tab("network")

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # Left Sidebar (Compact Navigation)
        # ----------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLOR_SIDEBAR, border_width=1, border_color=COLOR_BORDER)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Header Title
        title_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=16, pady=(18, 16), sticky="w")

        title_lbl = ctk.CTkLabel(title_box, text="LANForge", font=ctk.CTkFont(family=FONT_MAIN, size=18, weight="bold"), text_color=COLOR_TEXT)
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(title_box, text="Virtual LAN Adapter", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED)
        sub_lbl.pack(anchor="w")

        # Nav Items
        self.nav_btns = {}
        tabs = [
            ("network", "Сеть"),
            ("presets", "Игры и порты"),
            ("radar", "LAN Поиск"),
            ("chat", "Чат комнаты"),
            ("diag", "Диагностика"),
        ]

        for idx, (tab_id, label) in enumerate(tabs, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color="transparent",
                text_color=COLOR_MUTED,
                hover_color=COLOR_SURFACE,
                font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
                command=lambda t=tab_id: self._show_tab(t)
            )
            btn.grid(row=idx, column=0, padx=10, pady=2, sticky="ew")
            self.nav_btns[tab_id] = btn

        # Bottom Status Panel
        status_panel = ctk.CTkFrame(self.sidebar, fg_color=COLOR_SURFACE, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        status_panel.grid(row=7, column=0, padx=10, pady=12, sticky="ew")

        self.status_dot = ctk.CTkLabel(status_panel, text="● Сервер активен", font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"), text_color=COLOR_GREEN)
        self.status_dot.pack(anchor="w", padx=10, pady=(8, 2))

        self.nick_lbl = ctk.CTkLabel(status_panel, text=f"Никнейм: {self.nick}", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_TEXT)
        self.nick_lbl.pack(anchor="w", padx=10, pady=(0, 2))

        self.ping_lbl = ctk.CTkLabel(status_panel, text="Задержка: < 1 ms", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED)
        self.ping_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # ----------------------------------------------------
        # Main Workspace Container
        # ----------------------------------------------------
        self.main_container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

    def _show_tab(self, tab_id):
        self.active_tab = tab_id
        for t, btn in self.nav_btns.items():
            if t == tab_id:
                btn.configure(fg_color=COLOR_SURFACE, text_color=COLOR_TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_MUTED)

        for widget in self.main_container.winfo_children():
            widget.destroy()

        if tab_id == "network":
            self._render_network()
        elif tab_id == "presets":
            self._render_presets()
        elif tab_id == "radar":
            self._render_radar()
        elif tab_id == "chat":
            self._render_chat()
        elif tab_id == "diag":
            self._render_diag()

    # ----------------------------------------------------
    # TAB: NETWORK (Radmin / Tailscale Style)
    # ----------------------------------------------------
    def _render_network(self):
        if not self.client.room:
            # Idle State: Clean Action Panel
            idle_box = ctk.CTkFrame(self.main_container, fg_color=COLOR_SIDEBAR, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
            idle_box.pack(fill="x", pady=10)

            pad = ctk.CTkFrame(idle_box, fg_color="transparent")
            pad.pack(padx=24, pady=32, fill="x")

            h = ctk.CTkLabel(pad, text="Подключение к виртуальной сети", font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
            h.pack(anchor="w", pady=(0, 6))

            desc = ctk.CTkLabel(
                pad,
                text="Создайте новую комнату для игры с друзьями или подключитесь по коду сети.",
                font=ctk.CTkFont(family=FONT_MAIN, size=12),
                text_color=COLOR_MUTED
            )
            desc.pack(anchor="w", pady=(0, 20))

            btn_row = ctk.CTkFrame(pad, fg_color="transparent")
            btn_row.pack(anchor="w")

            create_btn = ctk.CTkButton(
                btn_row,
                text="Создать комнату",
                height=34,
                width=140,
                corner_radius=6,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
                command=self._open_create_dialog
            )
            create_btn.pack(side="left", padx=(0, 10))

            join_btn = ctk.CTkButton(
                btn_row,
                text="Войти по коду",
                height=34,
                width=140,
                corner_radius=6,
                fg_color=COLOR_SURFACE,
                hover_color=COLOR_SURFACE_HOVER,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
                command=self._open_join_dialog
            )
            join_btn.pack(side="left")
            return

        # Active Room State
        room = self.client.room
        host_ip = "10.42.0.1"

        # Top Network Banner
        banner = ctk.CTkFrame(self.main_container, fg_color=COLOR_SIDEBAR, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        banner.pack(fill="x", pady=(0, 12))

        b_pad = ctk.CTkFrame(banner, fg_color="transparent")
        b_pad.pack(fill="x", padx=16, pady=12)

        # Row 1: Name + Code + Leave
        r1 = ctk.CTkFrame(b_pad, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 8))

        room_name = ctk.CTkLabel(r1, text=room.get("name", "Комната"), font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
        room_name.pack(side="left")

        code_str = room.get("code", "")
        code_tag = ctk.CTkButton(
            r1,
            text=f"Код: {code_str}",
            height=26,
            width=110,
            corner_radius=6,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_SURFACE_HOVER,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            command=lambda: self._copy(code_str, "Код скопирован")
        )
        code_tag.pack(side="left", padx=12)

        leave_btn = ctk.CTkButton(
            r1,
            text="Отключиться",
            height=26,
            width=90,
            corner_radius=6,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_RED,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            command=self.client.leave_room
        )
        leave_btn.pack(side="right")

        # Row 2: Direct Connect Hint
        r2 = ctk.CTkFrame(b_pad, fg_color=COLOR_SURFACE, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        r2.pack(fill="x")

        direct_str = f"{host_ip}:25565"
        hint_lbl = ctk.CTkLabel(r2, text=f"Адрес хоста для игры: {direct_str}", font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=COLOR_TEXT)
        hint_lbl.pack(side="left", padx=10, pady=6)

        copy_btn = ctk.CTkButton(
            r2,
            text="Копировать адрес",
            height=22,
            width=120,
            corner_radius=4,
            fg_color=COLOR_SIDEBAR,
            hover_color=COLOR_SURFACE_HOVER,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family=FONT_MAIN, size=10, weight="bold"),
            command=lambda: self._copy(direct_str, "Адрес скопирован")
        )
        copy_btn.pack(side="right", padx=6)

        # Members List Header
        list_header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        list_header.pack(fill="x", pady=(4, 6))

        h_title = ctk.CTkLabel(
            list_header,
            text=f"Участники ({len(room.get('peers', []))}/{room.get('maxPeers', 16)}):",
            font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
            text_color=COLOR_MUTED
        )
        h_title.pack(side="left")

        # Members Table
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for peer in room.get("peers", []):
            row = ctk.CTkFrame(scroll, fg_color=COLOR_SIDEBAR, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
            row.pack(fill="x", pady=2)

            r_pad = ctk.CTkFrame(row, fg_color="transparent")
            r_pad.pack(fill="x", padx=12, pady=8)

            # Online Dot
            ctk.CTkLabel(r_pad, text="●", font=ctk.CTkFont(size=10), text_color=COLOR_GREEN).pack(side="left", padx=(0, 8))

            # Nickname & Role
            nick_str = peer.get("nick", "Player")
            if peer.get("isHost"):
                nick_str += "  [Хост]"
            if self.client.you and peer.get("id") == self.client.you.get("id"):
                nick_str += " (Вы)"

            ctk.CTkLabel(r_pad, text=nick_str, font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"), text_color=COLOR_TEXT).pack(side="left")

            # Virtual IP Button
            ip = peer.get("virtualIp", "")
            ip_btn = ctk.CTkButton(
                r_pad,
                text=ip,
                height=22,
                width=110,
                corner_radius=4,
                fg_color=COLOR_SURFACE,
                hover_color=COLOR_SURFACE_HOVER,
                text_color=COLOR_ACCENT,
                font=ctk.CTkFont(family=FONT_MONO, size=11),
                command=lambda target_ip=ip: self._copy(target_ip, f"IP {target_ip} скопирован")
            )
            ip_btn.pack(side="left", padx=16)

            # Ping Pill
            ping = peer.get("pingMs", 0)
            ping_text = f"{ping} ms" if ping > 0 else "< 1 ms"
            p_color = COLOR_GREEN if ping < 50 else (COLOR_AMBER if ping < 100 else COLOR_RED)
            ctk.CTkLabel(r_pad, text=ping_text, font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=p_color).pack(side="right")

    # ----------------------------------------------------
    # TAB: PRESETS (Clean Searchable Catalog)
    # ----------------------------------------------------
    def _render_presets(self):
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(top_bar, text="Каталог игр и настроек портов", font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
        title.pack(side="left")

        # Category Filters
        cats_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        cats_bar.pack(fill="x", pady=(0, 10))

        cats = ["Все", "Песочницы", "Шутеры", "Выживание", "Классика"]
        for cat in cats:
            btn = ctk.CTkButton(
                cats_bar,
                text=cat,
                height=26,
                width=75,
                corner_radius=4,
                fg_color=COLOR_SURFACE if self.preset_filter == cat else "transparent",
                hover_color=COLOR_SURFACE_HOVER,
                text_color=COLOR_TEXT if self.preset_filter == cat else COLOR_MUTED,
                font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
                command=lambda c=cat: self._set_preset_filter(c)
            )
            btn.pack(side="left", padx=3)

        # Scrollable List
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        filtered = [
            p for p in GAME_PRESETS
            if (self.preset_filter == "Все" or p["category"] == self.preset_filter)
        ]

        for p in filtered:
            card = ctk.CTkFrame(scroll, fg_color=COLOR_SIDEBAR, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
            card.pack(fill="x", pady=4)

            p_pad = ctk.CTkFrame(card, fg_color="transparent")
            p_pad.pack(fill="x", padx=14, pady=10)

            # Top Line
            r1 = ctk.CTkFrame(p_pad, fg_color="transparent")
            r1.pack(fill="x")

            ctk.CTkLabel(r1, text=p["name"], font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"), text_color=COLOR_TEXT).pack(side="left")
            
            port_str = f"{p['protocol']} {p['default_port']}"
            ctk.CTkLabel(r1, text=port_str, font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=COLOR_MUTED).pack(side="left", padx=12)

            create_btn = ctk.CTkButton(
                r1,
                text="Создать",
                height=24,
                width=80,
                corner_radius=4,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
                command=lambda preset=p: self._open_create_dialog(preset)
            )
            create_btn.pack(side="right")

            # Description / Hint
            ctk.CTkLabel(p_pad, text=p["description"], font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED, wraplength=620, justify="left").pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(p_pad, text=f"Подключение: {p['hint']}", font=ctk.CTkFont(family=FONT_MAIN, size=10), text_color=COLOR_MUTED).pack(anchor="w")

    def _set_preset_filter(self, cat):
        self.preset_filter = cat
        self._show_tab("presets")

    # ----------------------------------------------------
    # TAB: LAN RADAR (Discovery)
    # ----------------------------------------------------
    def _render_radar(self):
        title = ctk.CTkLabel(self.main_container, text="LAN Радар (Автопоиск серверов)", font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
        title.pack(anchor="w", pady=(0, 4))

        desc = ctk.CTkLabel(
            self.main_container,
            text="LANForge слушает UDP широковещательные пакеты игр (Minecraft, Source) и ретранслирует их в комнату.",
            font=ctk.CTkFont(family=FONT_MAIN, size=11),
            text_color=COLOR_MUTED
        )
        desc.pack(anchor="w", pady=(0, 12))

        # Status Bar
        status_bar = ctk.CTkFrame(self.main_container, fg_color=COLOR_SIDEBAR, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        status_bar.pack(fill="x", pady=(0, 12))

        sb_pad = ctk.CTkFrame(status_bar, fg_color="transparent")
        sb_pad.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(sb_pad, text="● Сканирование UDP broadcast пакетов активно", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_GREEN).pack(side="left")

        # Discovered List
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if not self.client.discovered_games:
            empty = ctk.CTkLabel(scroll, text="Активных локальных серверов не обнаружено.\nОткройте мир для сети в игре хоста.", font=ctk.CTkFont(family=FONT_MAIN, size=12), text_color=COLOR_MUTED)
            empty.pack(pady=30)
        else:
            for g in self.client.discovered_games:
                card = ctk.CTkFrame(scroll, fg_color=COLOR_SIDEBAR, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
                card.pack(fill="x", pady=3)

                c_pad = ctk.CTkFrame(card, fg_color="transparent")
                c_pad.pack(fill="x", padx=12, pady=8)

                info_str = f"{g['name']}  |  {g['host_ip']}:{g['port']}"
                ctk.CTkLabel(c_pad, text=info_str, font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"), text_color=COLOR_TEXT).pack(side="left")

                cp_btn = ctk.CTkButton(
                    c_pad,
                    text="Копировать IP:Port",
                    height=22,
                    width=130,
                    corner_radius=4,
                    fg_color=COLOR_SURFACE,
                    hover_color=COLOR_SURFACE_HOVER,
                    text_color=COLOR_ACCENT,
                    font=ctk.CTkFont(family=FONT_MAIN, size=10, weight="bold"),
                    command=lambda target=f"{g['host_ip']}:{g['port']}": self._copy(target, "Адрес скопирован")
                )
                cp_btn.pack(side="right")

    # ----------------------------------------------------
    # TAB: CHAT
    # ----------------------------------------------------
    def _render_chat(self):
        title = ctk.CTkLabel(self.main_container, text="Чат комнаты", font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
        title.pack(anchor="w", pady=(0, 10))

        # Message Stream
        self.chat_stream = ctk.CTkScrollableFrame(self.main_container, fg_color=COLOR_SIDEBAR, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        self.chat_stream.pack(fill="both", expand=True, pady=(0, 10))

        if not self.client.chat_history:
            ctk.CTkLabel(self.chat_stream, text="Сообщений пока нет.", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(pady=20)
        else:
            for msg in self.client.chat_history:
                row = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=2)

                t_str = time.strftime("%H:%M", time.localtime(msg.get("timestamp", 0) / 1000))
                ctk.CTkLabel(row, text=f"[{t_str}] {msg.get('fromNick', 'Player')}:", font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"), text_color=COLOR_ACCENT).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(row, text=msg.get("text", ""), font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_TEXT).pack(side="left")

        # Bottom Input
        in_row = ctk.CTkFrame(self.main_container, fg_color="transparent")
        in_row.pack(fill="x")

        self.chat_entry = ctk.CTkEntry(
            in_row,
            placeholder_text="Введите сообщение...",
            height=32,
            corner_radius=6,
            fg_color=COLOR_SIDEBAR,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_MAIN, size=11)
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())

        send_btn = ctk.CTkButton(
            in_row,
            text="Отправить",
            height=32,
            width=90,
            corner_radius=6,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            command=self._send_chat
        )
        send_btn.pack(side="right")

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if text:
            self.client.send_chat(text)
            self.chat_entry.delete(0, "end")

    # ----------------------------------------------------
    # TAB: DIAGNOSTICS
    # ----------------------------------------------------
    def _render_diag(self):
        title = ctk.CTkLabel(self.main_container, text="Сетевая диагностика", font=ctk.CTkFont(family=FONT_MAIN, size=16, weight="bold"), text_color=COLOR_TEXT)
        title.pack(anchor="w", pady=(0, 12))

        # Details Card
        card = ctk.CTkFrame(self.main_container, fg_color=COLOR_SIDEBAR, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="x")

        c_pad = ctk.CTkFrame(card, fg_color="transparent")
        c_pad.pack(fill="x", padx=16, pady=16)

        items = [
            ("Тип NAT (STUN RFC 5389):", "Restricted Cone (Прямой P2P доступен)"),
            ("UPnP / NAT-PMP IGD:", "Активен (Авто-проброс портов включен)"),
            ("Виртуальная подсеть:", "10.42.0.0/24 (Хост: 10.42.0.1)"),
            ("Протокол передачи:", "WebSocket / UDP Hole Punching"),
            ("Статус сигнального сервера:", "Подключен (ws://localhost:8787)"),
        ]

        for label, val in items:
            row = ctk.CTkFrame(c_pad, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"), text_color=COLOR_MUTED, width=200, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_TEXT).pack(side="left")

    # ----------------------------------------------------
    # DIALOGS
    # ----------------------------------------------------
    def _open_create_dialog(self, default_preset=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Создать комнату")
        dlg.geometry("380x320")
        dlg.resizable(False, False)
        dlg.configure(fg_color=COLOR_BG)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color="transparent")
        p.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(p, text="Параметры комнаты", font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(p, text="Название комнаты:", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(anchor="w")
        name_in = ctk.CTkEntry(p, height=30, corner_radius=4, placeholder_text=f"{self.nick}'s Party", font=ctk.CTkFont(family=FONT_MAIN, size=11))
        name_in.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(p, text="Игра:", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(anchor="w")
        preset_names = [x["name"] for x in GAME_PRESETS]
        preset_var = ctk.StringVar(value=default_preset["name"] if default_preset else preset_names[0])
        opt = ctk.CTkOptionMenu(p, values=preset_names, variable=preset_var, height=30, corner_radius=4, fg_color=COLOR_SURFACE, button_color=COLOR_BORDER)
        opt.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(p, text="Пароль (опционально):", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(anchor="w")
        pass_in = ctk.CTkEntry(p, height=30, corner_radius=4, placeholder_text="Без пароля", show="*", font=ctk.CTkFont(family=FONT_MAIN, size=11))
        pass_in.pack(fill="x", pady=(2, 16))

        def submit():
            r_name = name_in.get().strip() or f"{self.nick}'s Party"
            r_pass = pass_in.get().strip()
            sel_p = next((x for x in GAME_PRESETS if x["name"] == preset_var.get()), GAME_PRESETS[0])
            self.client.create_room(r_name, sel_p["id"], r_pass)
            dlg.destroy()

        btn = ctk.CTkButton(p, text="Создать", height=32, corner_radius=4, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"), command=submit)
        btn.pack(fill="x")

    def _open_join_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Вход в комнату")
        dlg.geometry("340x240")
        dlg.resizable(False, False)
        dlg.configure(fg_color=COLOR_BG)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color="transparent")
        p.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(p, text="Подключение по коду", font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(p, text="Код комнаты (LAN-XXXX):", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(anchor="w")
        code_in = ctk.CTkEntry(p, height=30, corner_radius=4, placeholder_text="LAN-XXXX", font=ctk.CTkFont(family=FONT_MONO, size=12))
        code_in.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(p, text="Пароль комнаты:", font=ctk.CTkFont(family=FONT_MAIN, size=11), text_color=COLOR_MUTED).pack(anchor="w")
        pass_in = ctk.CTkEntry(p, height=30, corner_radius=4, placeholder_text="Если требуется", show="*", font=ctk.CTkFont(family=FONT_MAIN, size=11))
        pass_in.pack(fill="x", pady=(2, 16))

        def submit():
            code = code_in.get().strip()
            if code:
                self.client.join_room(code, pass_in.get().strip())
                dlg.destroy()

        btn = ctk.CTkButton(p, text="Подключиться", height=32, corner_radius=4, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"), command=submit)
        btn.pack(fill="x")

    def _copy(self, text, message="Скопировано"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _bind_client_events(self):
        def on_conn(status):
            try:
                self.after(0, lambda: self.status_dot.configure(
                    text="● Сервер активен" if status else "○ Сервер недоступен",
                    text_color=COLOR_GREEN if status else COLOR_RED
                ))
            except Exception:
                pass

        def on_room(room):
            try:
                self.after(0, lambda: self._show_tab("network"))
            except Exception:
                pass

        def on_ping(rtt):
            try:
                self.after(0, lambda: self.ping_lbl.configure(text=f"Задержка: {rtt} ms"))
            except Exception:
                pass

        def on_chat(msg):
            try:
                self.after(0, lambda: self._show_tab("chat") if self.active_tab == "chat" else None)
            except Exception:
                pass

        def on_game(game):
            try:
                self.after(0, lambda: self._show_tab("radar") if self.active_tab == "radar" else None)
            except Exception:
                pass

        self.client.on("connection", on_conn)
        self.client.on("room_state", on_room)
        self.client.on("ping", on_ping)
        self.client.on("chat_message", on_chat)
        self.client.on("discovered_game", on_game)

if __name__ == "__main__":
    app = LANForgeApp()
    app.mainloop()
