import os
import sys
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

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

# Swiss Brutalism & Bento Grid Palette (Linear / Raycast / Nothing OS Style)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_COLOR = "#09090b"            # Deep pure obsidian
BENTO_CARD = "#121215"          # Bento block surface
BENTO_HOVER = "#1a1a1f"         # Bento hover surface
BENTO_BORDER = "#27272a"        # 1px crisp structural border
BENTO_BORDER_FOCUS = "#3f3f46"  # Highlighted border

TEXT_MAIN = "#ffffff"           # Stark white
TEXT_SECONDARY = "#a1a1aa"      # Neutral secondary
TEXT_MUTED = "#52525b"          # Low-contrast metadata

# Accent: Safety Orange & Emerald
ACCENT_ORANGE = "#ff5500"
ACCENT_ORANGE_HOVER = "#e04b00"
ACCENT_GREEN = "#22c55e"
ACCENT_RED = "#ef4444"

FONT_SANS = "Segoe UI"
FONT_MONO = "Consolas"

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
        self.preset_filter = "Все"

        self._setup_layout()
        self._bind_client_events()
        self._show_tab("overview")

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ----------------------------------------------------
        # TOP NAVIGATION BAR (Linear / Raycast Style)
        # ----------------------------------------------------
        self.top_bar = ctk.CTkFrame(self, height=54, fg_color=BG_COLOR, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 6))

        # Brand / Logo
        brand_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        brand_frame.pack(side="left")

        logo_lbl = ctk.CTkLabel(
            brand_frame,
            text="LANFORGE",
            font=ctk.CTkFont(family=FONT_SANS, size=16, weight="bold"),
            text_color=TEXT_MAIN
        )
        logo_lbl.pack(side="left")

        dot_lbl = ctk.CTkLabel(
            brand_frame,
            text=".",
            font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        dot_lbl.pack(side="left")

        # Tab Selector Pills
        self.tabs_bar = ctk.CTkFrame(self.top_bar, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        self.tabs_bar.pack(side="left", padx=24)

        self.tab_btns = {}
        tabs = [
            ("overview", "Обзор"),
            ("games", "Игры"),
            ("radar", "LAN Радар"),
            ("chat", "Чат"),
            ("diag", "Диагностика"),
        ]

        for tab_id, label in tabs:
            btn = ctk.CTkButton(
                self.tabs_bar,
                text=label,
                height=28,
                width=80,
                corner_radius=6,
                fg_color="transparent",
                hover_color=BENTO_HOVER,
                text_color=TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                command=lambda t=tab_id: self._show_tab(t)
            )
            btn.pack(side="left", padx=2, pady=2)
            self.tab_btns[tab_id] = btn

        # Right Action Buttons
        actions_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        actions_frame.pack(side="right")

        self.create_top_btn = ctk.CTkButton(
            actions_frame,
            text="+ Создать сеть",
            height=30,
            width=120,
            corner_radius=6,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color="#ffffff",
            command=self._open_create_dialog
        )
        self.create_top_btn.pack(side="left", padx=(0, 8))

        self.join_top_btn = ctk.CTkButton(
            actions_frame,
            text="Войти по коду",
            height=30,
            width=110,
            corner_radius=6,
            fg_color=BENTO_CARD,
            hover_color=BENTO_HOVER,
            border_width=1,
            border_color=BENTO_BORDER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color=TEXT_MAIN,
            command=self._open_join_dialog
        )
        self.join_top_btn.pack(side="left")

        # ----------------------------------------------------
        # MAIN WORKSPACE CONTAINER
        # ----------------------------------------------------
        self.main_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(4, 16))

    def _show_tab(self, tab_id):
        self.active_tab = tab_id
        for t, btn in self.tab_btns.items():
            if t == tab_id:
                btn.configure(fg_color="#202024", text_color=TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)

        for widget in self.main_container.winfo_children():
            widget.destroy()

        if tab_id == "overview":
            self._render_overview()
        elif tab_id == "games":
            self._render_games()
        elif tab_id == "radar":
            self._render_radar()
        elif tab_id == "chat":
            self._render_chat()
        elif tab_id == "diag":
            self._render_diag()

    # ----------------------------------------------------
    # TAB: OVERVIEW (Bento Grid Architecture)
    # ----------------------------------------------------
    def _render_overview(self):
        # 2-Column Bento Grid
        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_rowconfigure(0, weight=1)

        # -----------------
        # LEFT BENTO: Main Network Room Tile
        # -----------------
        left_bento = ctk.CTkFrame(self.main_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        left_bento.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        lb_pad = ctk.CTkFrame(left_bento, fg_color="transparent")
        lb_pad.pack(fill="both", expand=True, padx=20, pady=20)

        if not self.client.room:
            # Empty / Standby State
            ctk.CTkLabel(lb_pad, text="ВИРТУАЛЬНАЯ СЕТЬ", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
            ctk.CTkLabel(lb_pad, text="Сеть не подключена", font=ctk.CTkFont(family=FONT_SANS, size=24, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 8))
            ctk.CTkLabel(
                lb_pad,
                text="Создайте комнату для совместной игры или введите 6-значный код комнаты хоста для подключения.",
                font=ctk.CTkFont(family=FONT_SANS, size=12),
                text_color=TEXT_SECONDARY,
                wraplength=420,
                justify="left"
            ).pack(anchor="w", pady=(0, 24))

            actions_box = ctk.CTkFrame(lb_pad, fg_color="transparent")
            actions_box.pack(anchor="w")

            ctk.CTkButton(
                actions_box,
                text="Создать комнату",
                height=36,
                width=150,
                corner_radius=8,
                fg_color=ACCENT_ORANGE,
                hover_color=ACCENT_ORANGE_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                command=self._open_create_dialog
            ).pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                actions_box,
                text="Войти по коду",
                height=36,
                width=140,
                corner_radius=8,
                fg_color="#1e1e24",
                hover_color="#27272e",
                border_width=1,
                border_color=BENTO_BORDER,
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                text_color=TEXT_MAIN,
                command=self._open_join_dialog
            ).pack(side="left")
        else:
            # Active Room State
            room = self.client.room
            host_ip = "10.42.0.1"

            # Header info
            top_meta = ctk.CTkFrame(lb_pad, fg_color="transparent")
            top_meta.pack(fill="x", pady=(0, 6))

            ctk.CTkLabel(top_meta, text="АКТИВНАЯ СЕТЬ", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=TEXT_MUTED).pack(side="left")

            ctk.CTkButton(
                top_meta,
                text="Отключиться",
                height=22,
                width=90,
                corner_radius=4,
                fg_color="#27272a",
                hover_color=ACCENT_RED,
                font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
                text_color=TEXT_MAIN,
                command=self.client.leave_room
            ).pack(side="right")

            # Room Title + Code Pill
            title_row = ctk.CTkFrame(lb_pad, fg_color="transparent")
            title_row.pack(fill="x", pady=(0, 12))

            ctk.CTkLabel(title_row, text=room.get("name", "Комната"), font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

            code_str = room.get("code", "LAN-XXXX")
            ctk.CTkButton(
                title_row,
                text=f"{code_str} 📋",
                height=26,
                width=100,
                corner_radius=6,
                fg_color="#1e1e24",
                hover_color="#27272e",
                border_width=1,
                border_color=BENTO_BORDER,
                font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                text_color=ACCENT_ORANGE,
                command=lambda: self._copy(code_str, "Код скопирован")
            ).pack(side="left", padx=12)

            # Direct Connect String Block
            connect_box = ctk.CTkFrame(lb_pad, fg_color="#18181c", corner_radius=8, border_width=1, border_color=BENTO_BORDER)
            connect_box.pack(fill="x", pady=(0, 14))

            cb_pad = ctk.CTkFrame(connect_box, fg_color="transparent")
            cb_pad.pack(fill="x", padx=12, pady=8)

            direct_addr = f"{host_ip}:25565"
            ctk.CTkLabel(cb_pad, text=f"Адрес хоста в игре:  {direct_addr}", font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

            ctk.CTkButton(
                cb_pad,
                text="Копировать адрес",
                height=24,
                width=130,
                corner_radius=4,
                fg_color="#27272a",
                hover_color=BENTO_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                text_color=TEXT_MAIN,
                command=lambda: self._copy(direct_addr, "Адрес скопирован")
            ).pack(side="right")

            # Peers List Header
            ctk.CTkLabel(
                lb_pad,
                text=f"Участники ({len(room.get('peers', []))}/{room.get('maxPeers', 16)}):",
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                text_color=TEXT_MUTED
            ).pack(anchor="w", pady=(0, 6))

            # Scrollable Peers
            scroll_peers = ctk.CTkScrollableFrame(lb_pad, fg_color="transparent")
            scroll_peers.pack(fill="both", expand=True)

            for peer in room.get("peers", []):
                p_row = ctk.CTkFrame(scroll_peers, fg_color="#18181c", corner_radius=6, border_width=1, border_color=BENTO_BORDER)
                p_row.pack(fill="x", pady=2)

                pr_pad = ctk.CTkFrame(p_row, fg_color="transparent")
                pr_pad.pack(fill="x", padx=10, pady=6)

                # Online Indicator
                ctk.CTkLabel(pr_pad, text="●", font=ctk.CTkFont(size=9), text_color=ACCENT_GREEN).pack(side="left", padx=(0, 6))

                nick_txt = peer.get("nick", "User")
                if peer.get("isHost"):
                    nick_txt += " (Хост)"
                if self.client.you and peer.get("id") == self.client.you.get("id"):
                    nick_txt += " (Вы)"

                ctk.CTkLabel(pr_pad, text=nick_txt, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

                # IP Tag Button
                v_ip = peer.get("virtualIp", "")
                ctk.CTkButton(
                    pr_pad,
                    text=f"{v_ip} 📋",
                    height=20,
                    width=100,
                    corner_radius=4,
                    fg_color="#202024",
                    hover_color=BENTO_HOVER,
                    font=ctk.CTkFont(family=FONT_MONO, size=10),
                    text_color=TEXT_SECONDARY,
                    command=lambda target_ip=v_ip: self._copy(target_ip, f"IP {target_ip} скопирован")
                ).pack(side="left", padx=12)

                # Latency Badge
                ping = peer.get("pingMs", 0)
                p_str = f"{ping} ms" if ping > 0 else "< 1 ms"
                p_col = ACCENT_GREEN if ping < 50 else (ACCENT_ORANGE if ping < 100 else ACCENT_RED)
                ctk.CTkLabel(pr_pad, text=p_str, font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=p_col).pack(side="right")

        # -----------------
        # RIGHT BENTO TILES (Sidebar Metrics)
        # -----------------
        right_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_rowconfigure(2, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        # Tile 1: Your Virtual IP
        t1 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t1.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        t1_pad = ctk.CTkFrame(t1, fg_color="transparent")
        t1_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t1_pad, text="ВАШ ВИРТУАЛЬНЫЙ IP", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        
        my_ip = self.client.you.get("virtualIp", "10.42.0.1") if (self.client.room and self.client.you) else "10.42.0.X"
        ip_display = ctk.CTkLabel(t1_pad, text=my_ip, font=ctk.CTkFont(family=FONT_MONO, size=22, weight="bold"), text_color=TEXT_MAIN)
        ip_display.pack(anchor="w", pady=(2, 4))

        ctk.CTkButton(
            t1_pad,
            text="Копировать IP",
            height=22,
            width=110,
            corner_radius=4,
            fg_color="#1e1e24",
            hover_color=BENTO_HOVER,
            border_width=1,
            border_color=BENTO_BORDER,
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
            command=lambda: self._copy(my_ip, "IP скопирован")
        ).pack(anchor="w")

        # Tile 2: Latency & Link Quality
        t2 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t2.grid(row=1, column=0, sticky="nsew", pady=4)

        t2_pad = ctk.CTkFrame(t2, fg_color="transparent")
        t2_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t2_pad, text="ЗАДЕРЖКА СЕТИ (RTT)", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        
        ping_val = self.client.last_ping_rtt
        ping_display_str = f"{ping_val} ms" if ping_val > 0 else "< 1 ms"
        ctk.CTkLabel(t2_pad, text=ping_display_str, font=ctk.CTkFont(family=FONT_MONO, size=22, weight="bold"), text_color=ACCENT_GREEN if ping_val < 50 else ACCENT_ORANGE).pack(anchor="w", pady=(2, 2))

        ctk.CTkLabel(t2_pad, text="● Прямой P2P туннель активен", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")

        # Tile 3: Router & NAT Info
        t3 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t3.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

        t3_pad = ctk.CTkFrame(t3, fg_color="transparent")
        t3_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t3_pad, text="ШЛЮЗ И UPNP МАРШРУТИЗАЦИЯ", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkLabel(t3_pad, text="Restricted Cone NAT", font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(t3_pad, text="UPnP IGD авто-проброс портов включен", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")

    # ----------------------------------------------------
    # TAB: GAMES (Bento Game Catalog)
    # ----------------------------------------------------
    def _render_games(self):
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header, text="Каталог игр", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

        # Filter Chips
        f_box = ctk.CTkFrame(self.main_container, fg_color="transparent")
        f_box.pack(fill="x", pady=(0, 12))

        cats = ["Все", "Песочницы", "Шутеры", "Выживание", "Классика"]
        for cat in cats:
            btn = ctk.CTkButton(
                f_box,
                text=cat,
                height=26,
                width=80,
                corner_radius=6,
                fg_color="#202024" if self.preset_filter == cat else "transparent",
                hover_color=BENTO_HOVER,
                text_color=TEXT_MAIN if self.preset_filter == cat else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda c=cat: self._set_preset_filter(c)
            )
            btn.pack(side="left", padx=2)

        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        filtered = [
            p for p in GAME_PRESETS
            if (self.preset_filter == "Все" or p["category"] == self.preset_filter)
        ]

        for p in filtered:
            card = ctk.CTkFrame(scroll, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
            card.pack(fill="x", pady=4)

            c_pad = ctk.CTkFrame(card, fg_color="transparent")
            c_pad.pack(fill="x", padx=14, pady=10)

            # Top Line
            r1 = ctk.CTkFrame(c_pad, fg_color="transparent")
            r1.pack(fill="x")

            ctk.CTkLabel(r1, text=p["name"], font=ctk.CTkFont(family=FONT_SANS, size=13, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

            port_pill = f"{p['protocol']} {p['default_port']}"
            ctk.CTkLabel(r1, text=port_pill, font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=TEXT_MUTED).pack(side="left", padx=12)

            ctk.CTkButton(
                r1,
                text="Создать комнату",
                height=26,
                width=120,
                corner_radius=6,
                fg_color=ACCENT_ORANGE,
                hover_color=ACCENT_ORANGE_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda preset=p: self._open_create_dialog(preset)
            ).pack(side="right")

            # Description
            ctk.CTkLabel(c_pad, text=p["description"], font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(c_pad, text=f"Инструкция: {p['hint']}", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")

    def _set_preset_filter(self, cat):
        self.preset_filter = cat
        self._show_tab("games")

    # ----------------------------------------------------
    # TAB: RADAR (LAN Discovery)
    # ----------------------------------------------------
    def _render_radar(self):
        title = ctk.CTkLabel(self.main_container, text="LAN Радар (Автопоиск серверов)", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 4))

        desc = ctk.CTkLabel(
            self.main_container,
            text="LANForge перехватывает широковещательные UDP-пакеты игр (Minecraft, Source) и ретранслирует их всем участникам комнаты.",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_MUTED
        )
        desc.pack(anchor="w", pady=(0, 12))

        # Status Strip
        sb = ctk.CTkFrame(self.main_container, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        sb.pack(fill="x", pady=(0, 12))

        sb_pad = ctk.CTkFrame(sb, fg_color="transparent")
        sb_pad.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(sb_pad, text="● Сканирование широковещательных пакетов активно", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=ACCENT_GREEN).pack(side="left")

        # Discovered List
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if not self.client.discovered_games:
            ctk.CTkLabel(scroll, text="Активных LAN-миров в сети пока не обнаружено.\nОткройте мир для сети в Minecraft или запустите локальный сервер.", font=ctk.CTkFont(family=FONT_SANS, size=12), text_color=TEXT_MUTED).pack(pady=30)
        else:
            for g in self.client.discovered_games:
                card = ctk.CTkFrame(scroll, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
                card.pack(fill="x", pady=3)

                c_pad = ctk.CTkFrame(card, fg_color="transparent")
                c_pad.pack(fill="x", padx=12, pady=8)

                info_str = f"{g['name']}  |  {g['host_ip']}:{g['port']}"
                ctk.CTkLabel(c_pad, text=info_str, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

                ctk.CTkButton(
                    c_pad,
                    text="Копировать адрес",
                    height=22,
                    width=130,
                    corner_radius=4,
                    fg_color="#1e1e24",
                    hover_color=BENTO_HOVER,
                    font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
                    command=lambda target=f"{g['host_ip']}:{g['port']}": self._copy(target, "Адрес скопирован")
                ).pack(side="right")

    # ----------------------------------------------------
    # TAB: CHAT (Linear / Raycast Style)
    # ----------------------------------------------------
    def _render_chat(self):
        title = ctk.CTkLabel(self.main_container, text="Чат комнаты", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 10))

        # Message Feed
        self.chat_feed = ctk.CTkScrollableFrame(self.main_container, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        self.chat_feed.pack(fill="both", expand=True, pady=(0, 10))

        if not self.client.chat_history:
            ctk.CTkLabel(self.chat_feed, text="Сообщений пока нет.", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(pady=25)
        else:
            for msg in self.client.chat_history:
                row = ctk.CTkFrame(self.chat_feed, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=2)

                t_str = time.strftime("%H:%M", time.localtime(msg.get("timestamp", 0) / 1000))
                ctk.CTkLabel(row, text=f"[{t_str}] {msg.get('fromNick', 'User')}:", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=ACCENT_ORANGE).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(row, text=msg.get("text", ""), font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MAIN).pack(side="left")

        # Input Row
        in_row = ctk.CTkFrame(self.main_container, fg_color="transparent")
        in_row.pack(fill="x")

        self.chat_entry = ctk.CTkEntry(
            in_row,
            placeholder_text="Введите сообщение...",
            height=34,
            corner_radius=8,
            fg_color=BENTO_CARD,
            border_color=BENTO_BORDER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_SANS, size=11)
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())

        send_btn = ctk.CTkButton(
            in_row,
            text="Отправить",
            height=34,
            width=90,
            corner_radius=8,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
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
        title = ctk.CTkLabel(self.main_container, text="Сетевая диагностика", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 12))

        box = ctk.CTkFrame(self.main_container, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        box.pack(fill="x")

        b_pad = ctk.CTkFrame(box, fg_color="transparent")
        b_pad.pack(fill="x", padx=18, pady=16)

        diag_items = [
            ("Тип NAT (STUN RFC 5389)", "Restricted Cone (Прямой P2P доступен)"),
            ("UPnP / NAT-PMP IGD", "● Активен (Авто-проброс портов включен)"),
            ("Виртуальная подсеть", "10.42.0.0/24 (Хост: 10.42.0.1)"),
            ("Транспортный стек", "WebSocket / UDP Hole Punching Forwarder"),
            ("Сигнальный сервер", "ws://localhost:8787"),
        ]

        for label, val in diag_items:
            r = ctk.CTkFrame(b_pad, fg_color="transparent")
            r.pack(fill="x", pady=4)
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=TEXT_MUTED, width=220, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=val, font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MAIN).pack(side="left")

    # ----------------------------------------------------
    # DIALOGS
    # ----------------------------------------------------
    def _open_create_dialog(self, default_preset=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Создать комнату")
        dlg.geometry("380x320")
        dlg.resizable(False, False)
        dlg.configure(fg_color=BG_COLOR)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(p, text="Параметры комнаты", font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=14, pady=(12, 10))

        ctk.CTkLabel(p, text="Название комнаты:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        name_in = ctk.CTkEntry(p, height=30, corner_radius=6, placeholder_text=f"{self.nick}'s Party", font=ctk.CTkFont(family=FONT_SANS, size=11), fg_color="#18181c", border_color=BENTO_BORDER)
        name_in.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Игра:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        preset_names = [x["name"] for x in GAME_PRESETS]
        preset_var = ctk.StringVar(value=default_preset["name"] if default_preset else preset_names[0])
        opt = ctk.CTkOptionMenu(p, values=preset_names, variable=preset_var, height=30, corner_radius=6, fg_color="#18181c", button_color=BENTO_BORDER, font=ctk.CTkFont(family=FONT_SANS, size=11))
        opt.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Пароль (опционально):", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        pass_in = ctk.CTkEntry(p, height=30, corner_radius=6, placeholder_text="Без пароля", show="*", font=ctk.CTkFont(family=FONT_SANS, size=11), fg_color="#18181c", border_color=BENTO_BORDER)
        pass_in.pack(fill="x", padx=14, pady=(2, 14))

        def submit():
            r_name = name_in.get().strip() or f"{self.nick}'s Party"
            r_pass = pass_in.get().strip()
            sel_p = next((x for x in GAME_PRESETS if x["name"] == preset_var.get()), GAME_PRESETS[0])
            self.client.create_room(r_name, sel_p["id"], r_pass)
            dlg.destroy()

        ctk.CTkButton(p, text="Создать сеть", height=32, corner_radius=6, fg_color=ACCENT_ORANGE, hover_color=ACCENT_ORANGE_HOVER, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), command=submit).pack(fill="x", padx=14)

    def _open_join_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Вход в комнату")
        dlg.geometry("360x240")
        dlg.resizable(False, False)
        dlg.configure(fg_color=BG_COLOR)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(p, text="Подключение по коду", font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=14, pady=(12, 10))

        ctk.CTkLabel(p, text="Код комнаты (LAN-XXXX):", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        code_in = ctk.CTkEntry(p, height=30, corner_radius=6, placeholder_text="LAN-XXXX", font=ctk.CTkFont(family=FONT_MONO, size=12), fg_color="#18181c", border_color=BENTO_BORDER)
        code_in.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Пароль:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        pass_in = ctk.CTkEntry(p, height=30, corner_radius=6, placeholder_text="Если требуется", show="*", font=ctk.CTkFont(family=FONT_SANS, size=11), fg_color="#18181c", border_color=BENTO_BORDER)
        pass_in.pack(fill="x", padx=14, pady=(2, 14))

        def submit():
            code = code_in.get().strip()
            if code:
                self.client.join_room(code, pass_in.get().strip())
                dlg.destroy()

        ctk.CTkButton(p, text="Подключиться", height=32, corner_radius=6, fg_color=ACCENT_ORANGE, hover_color=ACCENT_ORANGE_HOVER, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), command=submit).pack(fill="x", padx=14)

    def _copy(self, text, message="Скопировано"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _bind_client_events(self):
        def on_conn(status):
            pass

        def on_room(room):
            try:
                self.after(0, lambda: self._show_tab("overview"))
            except Exception:
                pass

        def on_ping(rtt):
            try:
                if self.active_tab == "overview":
                    self.after(0, lambda: self._show_tab("overview"))
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
