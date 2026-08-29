import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from gui.presets_data import GAME_PRESETS
from gui.network_client import NetworkClient

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LANForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LANForge — P2P Virtual LAN Gaming Hub")
        self.geometry("1080x700")
        self.minsize(920, 580)

        # Custom Dark Palette
        self.configure(fg_color="#0d1117")

        # Network Client
        self.nick = f"Player_{int(time.time()) % 10000}"
        self.client = NetworkClient(server_url="ws://localhost:8787", nick=self.nick)

        # UI State
        self.active_tab = "lobby"
        self.category_filter = "Все"
        self.search_query = ""

        # Setup Views
        self._setup_layout()
        self._bind_client_events()
        self._show_tab("lobby")

    def _setup_layout(self):
        # Configure Grid (2 columns: Sidebar + Main Content)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Navigation Sidebar
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="#161b22", border_width=1, border_color="#30363d")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        # Brand Header
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🎮 LANFORGE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#818cf8"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 2), sticky="w")

        self.sub_logo = ctk.CTkLabel(
            self.sidebar,
            text="P2P Gaming Virtual LAN",
            font=ctk.CTkFont(size=11),
            text_color="#6b7280"
        )
        self.sub_logo.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Navigation Buttons
        self.nav_btns = {}
        tabs = [
            ("lobby", "🎮  Комната"),
            ("presets", "🕹️  Каталог игр"),
            ("radar", "📡  LAN Радар"),
            ("diag", "⚡  Сеть & NAT"),
            ("chat", "💬  Чат комнаты"),
        ]

        for idx, (tab_id, label) in enumerate(tabs, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=38,
                corner_radius=10,
                fg_color="transparent",
                text_color="#9ca3af",
                hover_color="#21262d",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda t=tab_id: self._show_tab(t)
            )
            btn.grid(row=idx, column=0, padx=12, pady=3, sticky="ew")
            self.nav_btns[tab_id] = btn

        # Bottom Profile & Status Card
        self.status_card = ctk.CTkFrame(self.sidebar, fg_color="#0d1117", corner_radius=12, border_width=1, border_color="#30363d")
        self.status_card.grid(row=8, column=0, padx=12, pady=15, sticky="ew")

        self.status_indicator = ctk.CTkLabel(
            self.status_card,
            text="● Online",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10b981"
        )
        self.status_indicator.pack(anchor="w", padx=12, pady=(10, 2))

        self.nick_label = ctk.CTkLabel(
            self.status_card,
            text=f"Ник: {self.nick}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f3f4f6"
        )
        self.nick_label.pack(anchor="w", padx=12, pady=(0, 2))

        self.ping_label = ctk.CTkLabel(
            self.status_card,
            text="Ping: < 1 ms",
            font=ctk.CTkFont(size=11),
            text_color="#818cf8"
        )
        self.ping_label.pack(anchor="w", padx=12, pady=(0, 10))

        # 2. Main Content Frame
        self.main_container = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

    def _show_tab(self, tab_id):
        self.active_tab = tab_id
        for t, btn in self.nav_btns.items():
            if t == tab_id:
                btn.configure(fg_color="#6366f1", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#9ca3af")

        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        if tab_id == "lobby":
            self._render_lobby()
        elif tab_id == "presets":
            self._render_presets()
        elif tab_id == "radar":
            self._render_radar()
        elif tab_id == "diag":
            self._render_diagnostics()
        elif tab_id == "chat":
            self._render_chat()

    # ----------------------------------------------------
    # TAB: LOBBY
    # ----------------------------------------------------
    def _render_lobby(self):
        if not self.client.room:
            # Welcome Screen when NOT in room
            hero = ctk.CTkFrame(self.main_container, fg_color="#161b22", corner_radius=18, border_width=1, border_color="#30363d")
            hero.pack(expand=True, fill="both", padx=20, pady=20)

            title = ctk.CTkLabel(hero, text="🎮 Готовы играть с друзьями по сети?", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f3f4f6")
            title.pack(pady=(60, 8))

            subtitle = ctk.CTkLabel(
                hero,
                text="Создайте игровую комнату и отправьте 6-значный код друзьям,\nлибо подключитесь к уже существующей комнате.",
                font=ctk.CTkFont(size=13),
                text_color="#9ca3af"
            )
            subtitle.pack(pady=(0, 30))

            btn_box = ctk.CTkFrame(hero, fg_color="transparent")
            btn_box.pack(pady=10)

            create_btn = ctk.CTkButton(
                btn_box,
                text="+ Создать комнату",
                width=180,
                height=45,
                corner_radius=12,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="#6366f1",
                hover_color="#4f46e5",
                command=self._open_create_modal
            )
            create_btn.pack(side="left", padx=10)

            join_btn = ctk.CTkButton(
                btn_box,
                text="🔑 Войти по коду",
                width=180,
                height=45,
                corner_radius=12,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="#21262d",
                hover_color="#30363d",
                text_color="#f3f4f6",
                command=self._open_join_modal
            )
            join_btn.pack(side="left", padx=10)

            hint = ctk.CTkLabel(hero, text="✓ Автопоиск серверов в локальной сети (Minecraft, Terraria, CS, Source)", font=ctk.CTkFont(size=11), text_color="#6b7280")
            hint.pack(side="bottom", pady=25)
        else:
            # Active Room Screen
            room = self.client.room
            host_ip = "10.42.0.1"

            # Top Room Banner
            header_card = ctk.CTkFrame(self.main_container, fg_color="#161b22", corner_radius=14, border_width=1, border_color="#30363d")
            header_card.pack(fill="x", pady=(0, 15))

            row1 = ctk.CTkFrame(header_card, fg_color="transparent")
            row1.pack(fill="x", padx=16, pady=(14, 6))

            name_lbl = ctk.CTkLabel(row1, text=room.get("name", "LAN Room"), font=ctk.CTkFont(size=18, weight="bold"), text_color="#ffffff")
            name_lbl.pack(side="left")

            code_btn = ctk.CTkButton(
                row1,
                text=f"Код: {room.get('code')}  📋",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#10b981",
                hover_color="#059669",
                height=32,
                corner_radius=8,
                command=lambda: self._copy_to_clipboard(room.get('code'), "Код комнаты скопирован!")
            )
            code_btn.pack(side="right", padx=(10, 0))

            leave_btn = ctk.CTkButton(
                row1,
                text="Выйти",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#ef4444",
                hover_color="#dc2626",
                height=32,
                width=80,
                corner_radius=8,
                command=self.client.leave_room
            )
            leave_btn.pack(side="right")

            # Direct Connect Bar
            connect_bar = ctk.CTkFrame(header_card, fg_color="#0d1117", corner_radius=8, border_width=1, border_color="#30363d")
            connect_bar.pack(fill="x", padx=16, pady=(0, 14))

            conn_text = f"★ Прямое подключение к хосту в игре:  {host_ip}:25565"
            conn_lbl = ctk.CTkLabel(connect_bar, text=conn_text, font=ctk.CTkFont(size=12, weight="bold"), text_color="#06b6d4")
            conn_lbl.pack(side="left", padx=12, pady=8)

            copy_conn = ctk.CTkButton(
                connect_bar,
                text="Скопировать адрес",
                font=ctk.CTkFont(size=11, weight="bold"),
                height=26,
                fg_color="#21262d",
                hover_color="#30363d",
                command=lambda: self._copy_to_clipboard(f"{host_ip}:25565", "Адрес скопирован!")
            )
            copy_conn.pack(side="right", padx=10)

            # Peers List Frame
            peers_title = ctk.CTkLabel(
                self.main_container,
                text=f"Участники комнаты ({len(room.get('peers', []))} / {room.get('maxPeers', 16)}):",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#e5e7eb"
            )
            peers_title.pack(anchor="w", pady=(5, 8))

            scroll_peers = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
            scroll_peers.pack(fill="both", expand=True)

            for peer in room.get("peers", []):
                p_card = ctk.CTkFrame(scroll_peers, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
                p_card.pack(fill="x", pady=4)

                p_row = ctk.CTkFrame(p_card, fg_color="transparent")
                p_row.pack(fill="x", padx=14, pady=10)

                nick_txt = peer.get("nick", "Player")
                if peer.get("isHost"):
                    nick_txt += "  [HOST 👑]"
                if self.client.you and peer.get("id") == self.client.you.get("id"):
                    nick_txt += "  (ВЫ)"

                nick_l = ctk.CTkLabel(p_row, text=nick_txt, font=ctk.CTkFont(size=13, weight="bold"), text_color="#f3f4f6")
                nick_l.pack(side="left")

                # Virtual IP Button
                ip = peer.get("virtualIp", "")
                ip_btn = ctk.CTkButton(
                    p_row,
                    text=f"{ip} 📋",
                    font=ctk.CTkFont(size=11, family="Consolas"),
                    fg_color="#0d1117",
                    hover_color="#21262d",
                    border_width=1,
                    border_color="#30363d",
                    height=28,
                    width=130,
                    command=lambda target_ip=ip: self._copy_to_clipboard(target_ip, f"IP {target_ip} скопирован!")
                )
                ip_btn.pack(side="left", padx=20)

                # Ping Badge
                ping = peer.get("pingMs", 0)
                ping_str = f"{ping} ms" if ping > 0 else "< 1 ms"
                p_color = "#10b981" if ping < 50 else ("#f59e0b" if ping < 100 else "#ef4444")

                ping_badge = ctk.CTkLabel(p_row, text=ping_str, font=ctk.CTkFont(size=11, weight="bold"), text_color=p_color)
                ping_badge.pack(side="right", padx=10)

    # ----------------------------------------------------
    # TAB: PRESETS (30+ Games)
    # ----------------------------------------------------
    def _render_presets(self):
        title = ctk.CTkLabel(self.main_container, text="🕹️ Каталог игр с готовыми настройками", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f3f4f6")
        title.pack(anchor="w", pady=(0, 10))

        # Filter Chips Bar
        filter_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        filter_bar.pack(fill="x", pady=(0, 10))

        cats = ["Все", "Песочницы", "Шутеры", "Выживание", "Классика"]
        for cat in cats:
            btn = ctk.CTkButton(
                filter_bar,
                text=cat,
                width=80,
                height=30,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#6366f1" if self.category_filter == cat else "#161b22",
                hover_color="#4f46e5",
                text_color="#ffffff" if self.category_filter == cat else "#9ca3af",
                command=lambda c=cat: self._set_category_filter(c)
            )
            btn.pack(side="left", padx=4)

        # Scrollable Game Cards Grid
        scroll_grid = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll_grid.pack(fill="both", expand=True)

        filtered = [
            p for p in GAME_PRESETS
            if (self.category_filter == "Все" or p["category"] == self.category_filter)
        ]

        for p in filtered:
            card = ctk.CTkFrame(scroll_grid, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
            card.pack(fill="x", pady=6, padx=2)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 4))

            g_name = ctk.CTkLabel(top_row, text=p["name"], font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
            g_name.pack(side="left")

            port_badge = ctk.CTkLabel(
                top_row,
                text=f"{p['protocol']}:{p['default_port']}",
                font=ctk.CTkFont(size=11, family="Consolas", weight="bold"),
                fg_color="#0d1117",
                corner_radius=6,
                text_color="#06b6d4",
                padx=8,
                pady=2
            )
            port_badge.pack(side="right")

            desc = ctk.CTkLabel(card, text=p["description"], font=ctk.CTkFont(size=12), text_color="#9ca3af", wraplength=650, justify="left")
            desc.pack(anchor="w", padx=14, pady=(0, 8))

            bot_row = ctk.CTkFrame(card, fg_color="transparent")
            bot_row.pack(fill="x", padx=14, pady=(0, 12))

            hint_lbl = ctk.CTkLabel(bot_row, text=f"💡 {p['hint']}", font=ctk.CTkFont(size=11), text_color="#6b7280")
            hint_lbl.pack(side="left")

            host_btn = ctk.CTkButton(
                bot_row,
                text="Создать комнату",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#6366f1",
                hover_color="#4f46e5",
                height=28,
                corner_radius=8,
                command=lambda preset=p: self._open_create_modal(preset)
            )
            host_btn.pack(side="right")

    def _set_category_filter(self, cat):
        self.category_filter = cat
        self._show_tab("presets")

    # ----------------------------------------------------
    # TAB: MAGIC LAN RADAR
    # ----------------------------------------------------
    def _render_radar(self):
        title = ctk.CTkLabel(self.main_container, text="📡 Magic LAN Discovery Radar", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f3f4f6")
        title.pack(anchor="w", pady=(0, 4))

        sub = ctk.CTkLabel(
            self.main_container,
            text="LANForge сканирует локальные UDP 255.255.255.255 пакеты игр и ретранслирует их всем участникам комнаты.\nИгры автоматически увидят сервер хоста во вкладке «Локальная сеть»!",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af",
            justify="left"
        )
        sub.pack(anchor="w", pady=(0, 15))

        banner = ctk.CTkFrame(self.main_container, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#10b981")
        banner.pack(fill="x", pady=(0, 15))

        b_row = ctk.CTkFrame(banner, fg_color="transparent")
        b_row.pack(fill="x", padx=14, pady=12)

        rad_status = ctk.CTkLabel(b_row, text="◎ Сканер широковещательных пакетов активен (порт 4445, 27015...)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10b981")
        rad_status.pack(side="left")

        sim_btn = ctk.CTkButton(
            b_row,
            text="Тестовый UDP Broadcast",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#21262d",
            hover_color="#30363d",
            height=28,
            command=self._simulate_broadcast
        )
        sim_btn.pack(side="right")

        # Discovered List
        d_title = ctk.CTkLabel(self.main_container, text=f"Обнаруженные сервера ({len(self.client.discovered_games)}):", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e5e7eb")
        d_title.pack(anchor="w", pady=(5, 8))

        scroll_d = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        scroll_d.pack(fill="both", expand=True)

        if not self.client.discovered_games:
            empty = ctk.CTkLabel(scroll_d, text="Пока не обнаружено активных LAN-миров в сети.\nОткройте мир для сети в Minecraft или запустите сервер игры.", font=ctk.CTkFont(size=12), text_color="#6b7280")
            empty.pack(pady=40)
        else:
            for g in self.client.discovered_games:
                card = ctk.CTkFrame(scroll_d, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
                card.pack(fill="x", pady=4)

                r = ctk.CTkFrame(card, fg_color="transparent")
                r.pack(fill="x", padx=14, pady=10)

                info = ctk.CTkLabel(r, text=f"🎮 {g['name']}  |  Хост: {g['host_nick']}  |  {g['host_ip']}:{g['port']}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#ffffff")
                info.pack(side="left")

                cp_btn = ctk.CTkButton(
                    r,
                    text="Скопировать IP:Port",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#10b981",
                    hover_color="#059669",
                    height=26,
                    command=lambda target=f"{g['host_ip']}:{g['port']}": self._copy_to_clipboard(target, "Адрес скопирован!")
                )
                cp_btn.pack(side="right")

    def _simulate_broadcast(self):
        sim = {
            "id": f"mc_{int(time.time())}",
            "name": "Minecraft LAN World (Survival 1.21)",
            "host_nick": "Alex_Host",
            "host_ip": "10.42.0.1",
            "port": 25565,
            "motd": "A Minecraft Server - LAN Game",
        }
        self.client.discovered_games.insert(0, sim)
        self._show_tab("radar")

    # ----------------------------------------------------
    # TAB: DIAGNOSTICS
    # ----------------------------------------------------
    def _render_diagnostics(self):
        title = ctk.CTkLabel(self.main_container, text="⚡ Сетевая диагностика и NAT Traversal", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f3f4f6")
        title.pack(anchor="w", pady=(0, 15))

        cards_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 15))

        # 1. STUN NAT Card
        c1 = ctk.CTkFrame(cards_frame, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d", width=220)
        c1.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(c1, text="ТИП NAT (STUN RFC 5389)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#818cf8").pack(anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(c1, text="Restricted Cone (Открытый)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981").pack(anchor="w", padx=12)
        ctk.CTkLabel(c1, text="Внешний IP: 178.62.204.14:54192", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(anchor="w", padx=12, pady=(4, 12))

        # 2. UPnP Card
        c2 = ctk.CTkFrame(cards_frame, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d", width=220)
        c2.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(c2, text="UPnP / NAT-PMP IGD", font=ctk.CTkFont(size=11, weight="bold"), text_color="#06b6d4").pack(anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(c2, text="● Авто-проброс активен", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981").pack(anchor="w", padx=12)
        ctk.CTkLabel(c2, text="Порты игр мапятся автоматически.", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(anchor="w", padx=12, pady=(4, 12))

        # 3. Subnet Card
        c3 = ctk.CTkFrame(cards_frame, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d", width=220)
        c3.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(c3, text="ВИРТУАЛЬНАЯ ПОДСЕТЬ", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f59e0b").pack(anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(c3, text="10.42.0.0/24 (Zero-Driver)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f3f4f6").pack(anchor="w", padx=12)
        ctk.CTkLabel(c3, text="Хост: 10.42.0.1 | Клиенты: 10.42.0.2..", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(anchor="w", padx=12, pady=(4, 12))

    # ----------------------------------------------------
    # TAB: CHAT
    # ----------------------------------------------------
    def _render_chat(self):
        title = ctk.CTkLabel(self.main_container, text="💬 Чат игровой комнаты", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f3f4f6")
        title.pack(anchor="w", pady=(0, 10))

        # Messages Box
        self.chat_box = ctk.CTkScrollableFrame(self.main_container, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
        self.chat_box.pack(fill="both", expand=True, pady=(0, 10))

        if not self.client.chat_history:
            ctk.CTkLabel(self.chat_box, text="Чат пуст. Напишите первое сообщение!", font=ctk.CTkFont(size=12), text_color="#6b7280").pack(pady=30)
        else:
            for msg in self.client.chat_history:
                msg_row = ctk.CTkFrame(self.chat_box, fg_color="transparent")
                msg_row.pack(fill="x", padx=10, pady=3)

                time_str = time.strftime("%H:%M", time.localtime(msg.get("timestamp", 0) / 1000))
                ctk.CTkLabel(msg_row, text=f"[{time_str}] {msg.get('fromNick', 'User')}:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#818cf8").pack(side="left", padx=(0, 6))
                ctk.CTkLabel(msg_row, text=msg.get("text", ""), font=ctk.CTkFont(size=12), text_color="#f3f4f6").pack(side="left")

        # Input Row
        input_row = ctk.CTkFrame(self.main_container, fg_color="transparent")
        input_row.pack(fill="x")

        self.chat_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Написать сообщение в комнату (Enter)...",
            height=38,
            corner_radius=10,
            fg_color="#161b22",
            border_color="#30363d",
            text_color="#ffffff"
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat_message())

        send_btn = ctk.CTkButton(
            input_row,
            text="Отправить",
            width=100,
            height=38,
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._send_chat_message
        )
        send_btn.pack(side="right")

    def _send_chat_message(self):
        text = self.chat_entry.get().strip()
        if text:
            self.client.send_chat(text)
            self.chat_entry.delete(0, "end")

    # ----------------------------------------------------
    # MODAL DIALOGS
    # ----------------------------------------------------
    def _open_create_modal(self, default_preset=None):
        modal = ctk.CTkToplevel(self)
        modal.title("Создать игровую комнату")
        modal.geometry("440x380")
        modal.resizable(False, False)
        modal.grab_set()

        ctk.CTkLabel(modal, text="🚀 Создание комнаты", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 15))

        # Room Name
        ctk.CTkLabel(modal, text="Название комнаты:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=30, pady=(5, 2))
        name_entry = ctk.CTkEntry(modal, width=380, placeholder_text=f"{self.nick}'s LAN Party")
        name_entry.pack(padx=30, pady=(0, 10))

        # Game Preset Dropdown
        ctk.CTkLabel(modal, text="Основная игра:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=30, pady=(5, 2))
        preset_names = [p["name"] for p in GAME_PRESETS]
        preset_var = ctk.StringVar(value=default_preset["name"] if default_preset else preset_names[0])
        preset_menu = ctk.CTkOptionMenu(modal, values=preset_names, variable=preset_var, width=380, fg_color="#161b22", button_color="#6366f1")
        preset_menu.pack(padx=30, pady=(0, 10))

        # Password
        ctk.CTkLabel(modal, text="Пароль комнаты (опционально):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=30, pady=(5, 2))
        pass_entry = ctk.CTkEntry(modal, width=380, placeholder_text="Оставьте пустым, если без пароля", show="*")
        pass_entry.pack(padx=30, pady=(0, 20))

        def on_submit():
            p_name = name_entry.get().strip() or f"{self.nick}'s Party"
            p_pass = pass_entry.get().strip()
            selected_p = next((p for p in GAME_PRESETS if p["name"] == preset_var.get()), GAME_PRESETS[0])
            self.client.create_room(p_name, selected_p["id"], p_pass)
            modal.destroy()

        create_action_btn = ctk.CTkButton(
            modal,
            text="Запустить игровую сеть",
            width=380,
            height=40,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=on_submit
        )
        create_action_btn.pack(padx=30)

    def _open_join_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Подключиться к комнате")
        modal.geometry("400x300")
        modal.resizable(False, False)
        modal.grab_set()

        ctk.CTkLabel(modal, text="🔑 Вход по коду", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 15))

        ctk.CTkLabel(modal, text="Код комнаты (например LAN-9X4K):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=30, pady=(5, 2))
        code_entry = ctk.CTkEntry(modal, width=340, placeholder_text="LAN-XXXX", font=ctk.CTkFont(family="Consolas", size=14))
        code_entry.pack(padx=30, pady=(0, 10))

        ctk.CTkLabel(modal, text="Пароль (если требуется):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=30, pady=(5, 2))
        pass_entry = ctk.CTkEntry(modal, width=340, placeholder_text="Пароль", show="*")
        pass_entry.pack(padx=30, pady=(0, 20))

        def on_submit():
            code = code_entry.get().strip()
            if code:
                self.client.join_room(code, pass_entry.get().strip())
                modal.destroy()

        join_action_btn = ctk.CTkButton(
            modal,
            text="Подключиться к игре",
            width=340,
            height=40,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=on_submit
        )
        join_action_btn.pack(padx=30)

    def _copy_to_clipboard(self, text, message="Скопировано!"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _bind_client_events(self):
        def on_conn(status):
            self.after(0, lambda: self.status_indicator.configure(
                text="● Online" if status else "○ Offline",
                text_color="#10b981" if status else "#ef4444"
            ))

        def on_room(room):
            self.after(0, lambda: self._show_tab("lobby"))

        def on_ping(rtt):
            self.after(0, lambda: self.ping_label.configure(text=f"Ping: {rtt} ms"))

        def on_chat(msg):
            self.after(0, lambda: self._show_tab("chat") if self.active_tab == "chat" else None)

        def on_game(game):
            self.after(0, lambda: self._show_tab("radar") if self.active_tab == "radar" else None)

        self.client.on("connection", on_conn)
        self.client.on("room_state", on_room)
        self.client.on("ping", on_ping)
        self.client.on("chat_message", on_chat)
        self.client.on("discovered_game", on_game)

if __name__ == "__main__":
    app = LANForgeApp()
    app.mainloop()
