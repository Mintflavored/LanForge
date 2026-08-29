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

# Hardware Rack Color Scheme (Gunmetal, Anodized Steel, LED Indicators)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CHASSIS_BG = "#0f1013"        # Deep rack background
RACK_FACE = "#181a1f"         # Brushed gunmetal steel
BAY_BG = "#1f2229"            # Module bay background
BAY_HOVER = "#272a33"         # Hover state
BORDER_METAL = "#333742"      # Machine screws and rack borders
BORDER_LIGHT = "#444957"
TEXT_ETCHED = "#9ba1b0"       # Laser-etched metallic label
TEXT_BRIGHT = "#f3f5f8"       # White indicators
TEXT_MONO = "#a0aec0"

# LED Colors
LED_GREEN_ON = "#22c55e"
LED_GREEN_OFF = "#13331f"
LED_AMBER_ON = "#f59e0b"
LED_RED_ON = "#ef4444"
LED_CYAN_ON = "#06b6d4"

# LCD Display Colors
LCD_BG = "#0a1318"
LCD_BORDER = "#15333f"
LCD_TEXT = "#38bdf8"
LCD_SUB = "#0284c7"

FONT_MAIN = "Segoe UI"
FONT_MONO = "Consolas"

class LANForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LANFORGE // VIRTUAL NETWORK RACK SWITCH UNIT-24")
        self.geometry("980x660")
        self.minsize(880, 560)
        self.configure(fg_color=CHASSIS_BG)

        self.nick = f"UNIT_{int(time.time()) % 1000}"
        self.client = NetworkClient(server_url="ws://localhost:8787", nick=self.nick)

        self.active_module = "patchbay"
        self.preset_filter = "Все"
        self.led_state = True

        self._setup_rack_chassis()
        self._bind_client_events()
        self._show_module("patchbay")
        self._start_led_pulse()

    def _setup_rack_chassis(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ----------------------------------------------------
        # TOP RACK HEADER (Master Switch, LCD Screen, Screw Heads)
        # ----------------------------------------------------
        self.header_panel = ctk.CTkFrame(self, fg_color=RACK_FACE, corner_radius=0, border_width=1, border_color=BORDER_METAL)
        self.header_panel.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        h_inner = ctk.CTkFrame(self.header_panel, fg_color="transparent")
        h_inner.pack(fill="x", padx=16, pady=10)

        # Left: Rack Model Label + Screws
        brand_box = ctk.CTkFrame(h_inner, fg_color="transparent")
        brand_box.pack(side="left")

        lbl_unit = ctk.CTkLabel(
            brand_box,
            text="⊕ LANFORGE  //  SWITCH-24 MESH",
            font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        lbl_unit.pack(anchor="w")

        lbl_spec = ctk.CTkLabel(
            brand_box,
            text="IEEE 802.3 VIR-LAN  |  SUBNET: 10.42.0.0/24  |  MTU: 1420",
            font=ctk.CTkFont(family=FONT_MONO, size=10),
            text_color=TEXT_ETCHED
        )
        lbl_spec.pack(anchor="w")

        # Center: Master LCD Telemetry Screen
        self.lcd_screen = ctk.CTkFrame(h_inner, fg_color=LCD_BG, corner_radius=6, border_width=1, border_color=LCD_BORDER)
        self.lcd_screen.pack(side="left", padx=24, fill="y")

        self.lcd_label_1 = ctk.CTkLabel(
            self.lcd_screen,
            text="[SYS: READY]  LINK: ONLINE  |  PEERS: 0/16",
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=LCD_TEXT
        )
        self.lcd_label_1.pack(padx=14, pady=(4, 0), anchor="w")

        self.lcd_label_2 = ctk.CTkLabel(
            self.lcd_screen,
            text="ROOM: DISCONNECTED  |  DIRECT: STANDBY",
            font=ctk.CTkFont(family=FONT_MONO, size=10),
            text_color=LCD_SUB
        )
        self.lcd_label_2.pack(padx=14, pady=(0, 4), anchor="w")

        # Right: Master Hardware Actions
        actions_box = ctk.CTkFrame(h_inner, fg_color="transparent")
        actions_box.pack(side="right")

        self.pwr_btn = ctk.CTkButton(
            actions_box,
            text="⊕ СОЗДАТЬ СЕТЬ",
            height=30,
            width=130,
            corner_radius=4,
            fg_color="#1e3a5f",
            hover_color="#2563eb",
            border_width=1,
            border_color="#3b82f6",
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color="#ffffff",
            command=self._open_create_dialog
        )
        self.pwr_btn.pack(side="left", padx=4)

        self.join_btn = ctk.CTkButton(
            actions_box,
            text="⤹ ВХОД ПО КОДУ",
            height=30,
            width=120,
            corner_radius=4,
            fg_color=BAY_BG,
            hover_color=BAY_HOVER,
            border_width=1,
            border_color=BORDER_METAL,
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=TEXT_BRIGHT,
            command=self._open_join_dialog
        )
        self.join_btn.pack(side="left", padx=4)

        # ----------------------------------------------------
        # MODULE SWITCHER BAR (Rack Channel Selector)
        # ----------------------------------------------------
        self.module_bar = ctk.CTkFrame(self, height=36, fg_color=CHASSIS_BG, corner_radius=0, border_width=1, border_color=BORDER_METAL)
        self.module_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 0))

        self.module_btns = {}
        mods = [
            ("patchbay", "MOD 01: ПАТЧ-ПАНЕЛЬ (СЕТЬ)"),
            ("presets", "MOD 02: ИГРОВЫЕ ПОРТЫ"),
            ("radar", "MOD 03: ПАКЕТНЫЙ СНИФФЕР (РАДАР)"),
            ("chat", "MOD 04: ТЕЛЕТАЙП (ЧАТ)"),
            ("diag", "MOD 05: ТЕЛЕМЕТРИЯ NAT/UPNP"),
        ]

        for mod_id, title in mods:
            btn = ctk.CTkButton(
                self.module_bar,
                text=title,
                height=28,
                corner_radius=4,
                fg_color="transparent",
                hover_color=BAY_BG,
                text_color=TEXT_ETCHED,
                font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                command=lambda m=mod_id: self._show_module(m)
            )
            btn.pack(side="left", padx=3, pady=3)
            self.module_btns[mod_id] = btn

        # ----------------------------------------------------
        # MAIN RACK BAY WORKSPACE
        # ----------------------------------------------------
        self.main_bay = ctk.CTkFrame(self, fg_color=BAY_BG, corner_radius=6, border_width=1, border_color=BORDER_METAL)
        self.main_bay.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 12))

    def _show_module(self, mod_id):
        self.active_module = mod_id
        for m, btn in self.module_btns.items():
            if m == mod_id:
                btn.configure(fg_color=BAY_BG, text_color=TEXT_BRIGHT, border_width=1, border_color=BORDER_LIGHT)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_ETCHED, border_width=0)

        for widget in self.main_bay.winfo_children():
            widget.destroy()

        if mod_id == "patchbay":
            self._render_patchbay()
        elif mod_id == "presets":
            self._render_presets()
        elif mod_id == "radar":
            self._render_radar()
        elif mod_id == "chat":
            self._render_chat()
        elif mod_id == "diag":
            self._render_diag()

    # ----------------------------------------------------
    # MODULE 1: ETHERNET PATCH BAY (PHYSICAL PORTS)
    # ----------------------------------------------------
    def _render_patchbay(self):
        if not self.client.room:
            standby = ctk.CTkFrame(self.main_bay, fg_color="transparent")
            standby.pack(expand=True, fill="both", padx=30, pady=30)

            ctk.CTkLabel(
                standby,
                text="[ СЕТЕВОЙ МОДУЛЬ В РЕЖИМЕ ОЖИДАНИЯ ]",
                font=ctk.CTkFont(family=FONT_MONO, size=15, weight="bold"),
                text_color=TEXT_ETCHED
            ).pack(pady=(40, 8))

            ctk.CTkLabel(
                standby,
                text="Нет активного виртуального канала. Создайте комнату на панели или введите 6-значный код хоста.",
                font=ctk.CTkFont(family=FONT_MAIN, size=12),
                text_color=TEXT_MONO
            ).pack(pady=(0, 24))

            btn_box = ctk.CTkFrame(standby, fg_color="transparent")
            btn_box.pack()

            ctk.CTkButton(
                btn_box,
                text="⊕ ИНИЦИАЛИЗИРОВАТЬ СЕТЬ (ХОСТ)",
                width=240,
                height=38,
                corner_radius=4,
                fg_color="#1e3a5f",
                hover_color="#2563eb",
                font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
                command=self._open_create_dialog
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                btn_box,
                text="⤹ ПОДКЛЮЧИТЬ ПОРТ К СЕТИ",
                width=220,
                height=38,
                corner_radius=4,
                fg_color=RACK_FACE,
                hover_color=BAY_HOVER,
                border_width=1,
                border_color=BORDER_METAL,
                font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
                command=self._open_join_dialog
            ).pack(side="left", padx=8)
            return

        room = self.client.room
        host_ip = "10.42.0.1"

        # Active Patch Panel Banner
        p_top = ctk.CTkFrame(self.main_bay, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
        p_top.pack(fill="x", padx=10, pady=10)

        pt_pad = ctk.CTkFrame(p_top, fg_color="transparent")
        pt_pad.pack(fill="x", padx=12, pady=8)

        room_title = f"КАНАЛ: {room.get('name')}  |  КОД: {room.get('code')}"
        ctk.CTkLabel(pt_pad, text=room_title, font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"), text_color=TEXT_BRIGHT).pack(side="left")

        ctk.CTkButton(
            pt_pad,
            text="📋 КОПИРОВАТЬ КОД",
            height=24,
            width=130,
            corner_radius=3,
            fg_color="#1e3a5f",
            hover_color="#2563eb",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            command=lambda: self._copy(room.get('code'), "Код скопирован")
        ).pack(side="left", padx=12)

        ctk.CTkButton(
            pt_pad,
            text="ОТКЛЮЧИТЬ КАНАЛ",
            height=24,
            width=120,
            corner_radius=3,
            fg_color="#451a1a",
            hover_color="#dc2626",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            command=self.client.leave_room
        ).pack(side="right")

        # Direct Host IP Bar
        host_bar = ctk.CTkFrame(self.main_bay, fg_color=LCD_BG, corner_radius=4, border_width=1, border_color=LCD_BORDER)
        host_bar.pack(fill="x", padx=10, pady=(0, 10))

        hb_pad = ctk.CTkFrame(host_bar, fg_color="transparent")
        hb_pad.pack(fill="x", padx=12, pady=6)

        direct_connect_str = f"{host_ip}:25565"
        ctk.CTkLabel(
            hb_pad,
            text=f"★ СЕТЕВОЙ АДРЕС ДЛЯ ПОДКЛЮЧЕНИЯ В ИГРЕ:  {direct_connect_str}",
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=LCD_TEXT
        ).pack(side="left")

        ctk.CTkButton(
            hb_pad,
            text="КОПИРОВАТЬ АДРЕС",
            height=20,
            width=130,
            corner_radius=2,
            fg_color="#15333f",
            hover_color="#0284c7",
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            command=lambda: self._copy(direct_connect_str, "Адрес скопирован")
        ).pack(side="right")

        # Physical Ports Bay Header
        ctk.CTkLabel(
            self.main_bay,
            text="ПАТЧ-ПАНЕЛЬ СЛОТОВ // RJ-45 VIRTUAL PORTS:",
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=TEXT_ETCHED
        ).pack(anchor="w", padx=12, pady=(2, 4))

        # Ports Grid Container
        scroll_ports = ctk.CTkScrollableFrame(self.main_bay, fg_color="transparent")
        scroll_ports.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        peers = room.get("peers", [])
        total_slots = max(len(peers) + 2, 8)

        for slot_idx in range(total_slots):
            is_active = slot_idx < len(peers)
            peer = peers[slot_idx] if is_active else None

            port_card = ctk.CTkFrame(scroll_ports, fg_color=RACK_FACE if is_active else "#14161a", corner_radius=4, border_width=1, border_color=BORDER_METAL if is_active else "#20232a")
            port_card.pack(fill="x", pady=2)

            pc_pad = ctk.CTkFrame(port_card, fg_color="transparent")
            pc_pad.pack(fill="x", padx=10, pady=6)

            # Port Number Tag
            port_num_str = f"PORT {slot_idx+1:02d}"
            ctk.CTkLabel(
                pc_pad,
                text=port_num_str,
                font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                text_color=TEXT_BRIGHT if is_active else TEXT_ETCHED,
                width=65,
                anchor="w"
            ).pack(side="left")

            if is_active:
                led_link = "● LNK"
                led_act = "● ACT" if self.led_state else "○ ACT"

                ctk.CTkLabel(pc_pad, text=led_link, font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=LED_GREEN_ON).pack(side="left", padx=4)
                ctk.CTkLabel(pc_pad, text=led_act, font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=LED_AMBER_ON).pack(side="left", padx=4)

                nick_title = peer.get("nick", "UNIT")
                if peer.get("isHost"):
                    nick_title += " [HOST / MESH CONTROLLER]"
                if self.client.you and peer.get("id") == self.client.you.get("id"):
                    nick_title += " (YOU)"

                ctk.CTkLabel(
                    pc_pad,
                    text=nick_title,
                    font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                    text_color=TEXT_BRIGHT
                ).pack(side="left", padx=12)

                v_ip = peer.get("virtualIp", "10.42.0.X")
                ctk.CTkButton(
                    pc_pad,
                    text=f"{v_ip} 📋",
                    height=22,
                    width=120,
                    corner_radius=3,
                    fg_color=BAY_BG,
                    hover_color=BAY_HOVER,
                    border_width=1,
                    border_color=BORDER_METAL,
                    text_color=LCD_TEXT,
                    font=ctk.CTkFont(family=FONT_MONO, size=11),
                    command=lambda target_ip=v_ip: self._copy(target_ip, f"IP {target_ip} скопирован")
                ).pack(side="left", padx=10)

                ping = peer.get("pingMs", 0)
                vu_str, vu_col = self._get_vu_meter(ping)
                ctk.CTkLabel(
                    pc_pad,
                    text=vu_str,
                    font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
                    text_color=vu_col
                ).pack(side="right")
            else:
                ctk.CTkLabel(
                    pc_pad,
                    text="○ LNK  ○ ACT  //  СВОБОДНЫЙ ПОРТ ДЛЯ ИГРОКА (STANDBY)",
                    font=ctk.CTkFont(family=FONT_MONO, size=10),
                    text_color="#474d5b"
                ).pack(side="left", padx=6)

    def _get_vu_meter(self, ping):
        if ping <= 0:
            return "[■■■■■] <1ms", LED_GREEN_ON
        elif ping < 35:
            return f"[■■■■□] {ping}ms", LED_GREEN_ON
        elif ping < 80:
            return f"[■■■□□] {ping}ms", LED_AMBER_ON
        else:
            return f"[■□□□□] {ping}ms", LED_RED_ON

    # ----------------------------------------------------
    # MODULE 2: GAME PRESET SELECTOR (CHANNELS)
    # ----------------------------------------------------
    def _render_presets(self):
        title_box = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        title_box.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            title_box,
            text="ИГРОВЫЕ КАНАЛЫ И ПРЕСЕТЫ ПОРТОВ // RACK CHANNELS:",
            font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left")

        f_bar = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        f_bar.pack(fill="x", padx=12, pady=(0, 8))

        cats = ["Все", "Песочницы", "Шутеры", "Выживание", "Классика"]
        for cat in cats:
            btn = ctk.CTkButton(
                f_bar,
                text=cat,
                height=24,
                width=80,
                corner_radius=3,
                fg_color=RACK_FACE if self.preset_filter == cat else "transparent",
                hover_color=BAY_HOVER,
                border_width=1 if self.preset_filter == cat else 0,
                border_color=BORDER_METAL,
                text_color=TEXT_BRIGHT if self.preset_filter == cat else TEXT_ETCHED,
                font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
                command=lambda c=cat: self._set_preset_filter(c)
            )
            btn.pack(side="left", padx=2)

        scroll = ctk.CTkScrollableFrame(self.main_bay, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        filtered = [
            p for p in GAME_PRESETS
            if (self.preset_filter == "Все" or p["category"] == self.preset_filter)
        ]

        for idx, p in enumerate(filtered, start=1):
            row = ctk.CTkFrame(scroll, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
            row.pack(fill="x", pady=2)

            r_pad = ctk.CTkFrame(row, fg_color="transparent")
            r_pad.pack(fill="x", padx=10, pady=6)

            ch_str = f"CH {idx:02d}"
            ctk.CTkLabel(r_pad, text=ch_str, font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), text_color=LCD_TEXT, width=45, anchor="w").pack(side="left")

            ctk.CTkLabel(r_pad, text=p["name"], font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), text_color=TEXT_BRIGHT).pack(side="left")

            port_label = f"[{p['protocol']} {p['default_port']}]"
            ctk.CTkLabel(r_pad, text=port_label, font=ctk.CTkFont(family=FONT_MONO, size=10), text_color=TEXT_ETCHED).pack(side="left", padx=10)

            ctk.CTkButton(
                r_pad,
                text="ПРИВЯЗАТЬ СЕТЬ",
                height=22,
                width=120,
                corner_radius=3,
                fg_color="#1e3a5f",
                hover_color="#2563eb",
                font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
                command=lambda preset=p: self._open_create_dialog(preset)
            ).pack(side="right")

            ctk.CTkLabel(r_pad, text=p["hint"], font=ctk.CTkFont(family=FONT_MONO, size=10), text_color="#64748b").pack(side="right", padx=10)

    def _set_preset_filter(self, cat):
        self.preset_filter = cat
        self._show_module("presets")

    # ----------------------------------------------------
    # MODULE 3: PACKET SNIFFER (LAN RADAR)
    # ----------------------------------------------------
    def _render_radar(self):
        title_box = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        title_box.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            title_box,
            text="ПАКЕТНЫЙ СНИФФЕР // UDP 255.255.255.255 DISCOVERY MONITOR:",
            font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left")

        sb = ctk.CTkFrame(self.main_bay, fg_color=LCD_BG, corner_radius=4, border_width=1, border_color=LCD_BORDER)
        sb.pack(fill="x", padx=12, pady=(0, 10))

        sb_pad = ctk.CTkFrame(sb, fg_color="transparent")
        sb_pad.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            sb_pad,
            text="[LISTENER: SOCKET OPEN 0.0.0.0:4445]  |  REPEATER: BROADCAST MESH ACTIVE",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            text_color=LED_GREEN_ON
        ).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self.main_bay, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        if not self.client.discovered_games:
            ctk.CTkLabel(
                scroll,
                text="[ ПАКЕТОВ LAN-СЕРВЕРОВ НЕ ЗАФИКСИРОВАНО ]\nОткройте мир для сети в игре хоста (Minecraft/Source) — пакеты захватятся автоматически.",
                font=ctk.CTkFont(family=FONT_MONO, size=11),
                text_color=TEXT_ETCHED
            ).pack(pady=35)
        else:
            for g in self.client.discovered_games:
                card = ctk.CTkFrame(scroll, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
                card.pack(fill="x", pady=2)

                c_pad = ctk.CTkFrame(card, fg_color="transparent")
                c_pad.pack(fill="x", padx=10, pady=6)

                info_str = f"CAPTURED: {g['name']}  |  SRC: {g['host_ip']}:{g['port']}"
                ctk.CTkLabel(c_pad, text=info_str, font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), text_color=LCD_TEXT).pack(side="left")

                ctk.CTkButton(
                    c_pad,
                    text="КОПИРОВАТЬ IP:PORT",
                    height=20,
                    width=130,
                    corner_radius=2,
                    fg_color="#1e3a5f",
                    hover_color="#2563eb",
                    font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
                    command=lambda target=f"{g['host_ip']}:{g['port']}": self._copy(target, "Адрес скопирован")
                ).pack(side="right")

    # ----------------------------------------------------
    # MODULE 4: TELETYPE COMM (ROOM CHAT)
    # ----------------------------------------------------
    def _render_chat(self):
        title_box = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        title_box.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            title_box,
            text="ТЕЛЕТАЙП КАНАЛА СВЯЗИ // COMM LINK TELETYPE:",
            font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left")

        self.chat_feed = ctk.CTkScrollableFrame(self.main_bay, fg_color=LCD_BG, corner_radius=4, border_width=1, border_color=LCD_BORDER)
        self.chat_feed.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        if not self.client.chat_history:
            ctk.CTkLabel(self.chat_feed, text="[ ТЕЛЕТАЙП ЧИСТ // ЖДУ СООБЩЕНИЙ В КАНАЛ ]", font=ctk.CTkFont(family=FONT_MONO, size=10), text_color="#1e4e63").pack(pady=25)
        else:
            for msg in self.client.chat_history:
                row = ctk.CTkFrame(self.chat_feed, fg_color="transparent")
                row.pack(fill="x", padx=6, pady=1)

                t_str = time.strftime("%H:%M:%S", time.localtime(msg.get("timestamp", 0) / 1000))
                ctk.CTkLabel(row, text=f"[{t_str}] <{msg.get('fromNick', 'UNIT')}>", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=LCD_TEXT).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(row, text=msg.get("text", ""), font=ctk.CTkFont(family=FONT_MONO, size=10), text_color=TEXT_BRIGHT).pack(side="left")

        in_row = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        in_row.pack(fill="x", padx=12, pady=(0, 10))

        self.chat_entry = ctk.CTkEntry(
            in_row,
            placeholder_text="> Введите сообщение в канал связи...",
            height=30,
            corner_radius=3,
            fg_color=RACK_FACE,
            border_color=BORDER_METAL,
            text_color=TEXT_BRIGHT,
            font=ctk.CTkFont(family=FONT_MONO, size=11)
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())

        send_btn = ctk.CTkButton(
            in_row,
            text="ОТПРАВИТЬ",
            height=30,
            width=100,
            corner_radius=3,
            fg_color="#1e3a5f",
            hover_color="#2563eb",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            command=self._send_chat
        )
        send_btn.pack(side="right")

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if text:
            self.client.send_chat(text)
            self.chat_entry.delete(0, "end")

    # ----------------------------------------------------
    # MODULE 5: TELEMETRY (DIAGNOSTICS)
    # ----------------------------------------------------
    def _render_diag(self):
        title_box = ctk.CTkFrame(self.main_bay, fg_color="transparent")
        title_box.pack(fill="x", padx=12, pady=(10, 8))

        ctk.CTkLabel(
            title_box,
            text="СЕТЕВАЯ ТЕЛЕМЕТРИЯ // NAT TRAVERSAL & HARDWARE GAUGES:",
            font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left")

        t_box = ctk.CTkFrame(self.main_bay, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
        t_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        tb_pad = ctk.CTkFrame(t_box, fg_color="transparent")
        tb_pad.pack(fill="both", expand=True, padx=16, pady=12)

        telemetry_rows = [
            ("STUN NAT CLASSIFICATION (RFC 5389)", "Restricted Cone (Прямой P2P проброс активен)"),
            ("UPnP / NAT-PMP IGD STATUS", "● ENABLED (Авто-проброс портов на шлюзе активен)"),
            ("VIRTUAL ADAPTER SUBNET", "10.42.0.0/24 (Host IP: 10.42.0.1, Clients: 10.42.0.2..254)"),
            ("SOCKET TRANSPORT ENGINE", "WebSocket Wire / UDP Hole Punching Forwarder"),
            ("SIGNALING CONTROL SOCKET", "ws://localhost:8787 (Синхронизация комнат активна)"),
            ("PACKET MTU / MSS", "1420 BYTES / 1380 BYTES"),
        ]

        for label, val in telemetry_rows:
            r = ctk.CTkFrame(tb_pad, fg_color="transparent")
            r.pack(fill="x", pady=4)

            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), text_color=TEXT_ETCHED, width=280, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=val, font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=LCD_TEXT).pack(side="left")

    # ----------------------------------------------------
    # HARDWARE DIALOGS
    # ----------------------------------------------------
    def _open_create_dialog(self, default_preset=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("ИНИЦИАЛИЗАЦИЯ СЕТЕВОГО КАНАЛА")
        dlg.geometry("400x330")
        dlg.resizable(False, False)
        dlg.configure(fg_color=CHASSIS_BG)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(p, text="⊕ ПАРАМЕТРЫ СЕТЕВОГО КАНАЛА", font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"), text_color=TEXT_BRIGHT).pack(anchor="w", padx=12, pady=(12, 10))

        ctk.CTkLabel(p, text="ИМЯ КАНАЛА:", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=TEXT_ETCHED).pack(anchor="w", padx=12)
        name_in = ctk.CTkEntry(p, height=28, corner_radius=3, placeholder_text=f"{self.nick}'s Switch", font=ctk.CTkFont(family=FONT_MONO, size=11), fg_color=BAY_BG, border_color=BORDER_METAL)
        name_in.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(p, text="ИГРОВОЙ ПРЕСЕТ:", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=TEXT_ETCHED).pack(anchor="w", padx=12)
        preset_names = [x["name"] for x in GAME_PRESETS]
        preset_var = ctk.StringVar(value=default_preset["name"] if default_preset else preset_names[0])
        opt = ctk.CTkOptionMenu(p, values=preset_names, variable=preset_var, height=28, corner_radius=3, fg_color=BAY_BG, button_color=BORDER_METAL, font=ctk.CTkFont(family=FONT_MONO, size=11))
        opt.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(p, text="КЛЮЧ ДОСТУПА (ПАРОЛЬ):", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=TEXT_ETCHED).pack(anchor="w", padx=12)
        pass_in = ctk.CTkEntry(p, height=28, corner_radius=3, placeholder_text="БЕЗ ПАРОЛЯ", show="*", font=ctk.CTkFont(family=FONT_MONO, size=11), fg_color=BAY_BG, border_color=BORDER_METAL)
        pass_in.pack(fill="x", padx=12, pady=(2, 14))

        def submit():
            r_name = name_in.get().strip() or f"{self.nick}'s Switch"
            r_pass = pass_in.get().strip()
            sel_p = next((x for x in GAME_PRESETS if x["name"] == preset_var.get()), GAME_PRESETS[0])
            self.client.create_room(r_name, sel_p["id"], r_pass)
            dlg.destroy()

        ctk.CTkButton(p, text="ЗАПУСТИТЬ КАНАЛ", height=32, corner_radius=3, fg_color="#1e3a5f", hover_color="#2563eb", font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), command=submit).pack(fill="x", padx=12)

    def _open_join_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("ПОДКЛЮЧЕНИЕ К КАНАЛУ")
        dlg.geometry("360x250")
        dlg.resizable(False, False)
        dlg.configure(fg_color=CHASSIS_BG)
        dlg.grab_set()

        p = ctk.CTkFrame(dlg, fg_color=RACK_FACE, corner_radius=4, border_width=1, border_color=BORDER_METAL)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(p, text="⤹ ВХОД В СЕТЕВОЙ КАНАЛ", font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"), text_color=TEXT_BRIGHT).pack(anchor="w", padx=12, pady=(12, 10))

        ctk.CTkLabel(p, text="КОД СЕТИ (LAN-XXXX):", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=TEXT_ETCHED).pack(anchor="w", padx=12)
        code_in = ctk.CTkEntry(p, height=28, corner_radius=3, placeholder_text="LAN-XXXX", font=ctk.CTkFont(family=FONT_MONO, size=12), fg_color=BAY_BG, border_color=BORDER_METAL)
        code_in.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(p, text="ПАРОЛЬ (ЕСЛИ ТРЕБУЕТСЯ):", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"), text_color=TEXT_ETCHED).pack(anchor="w", padx=12)
        pass_in = ctk.CTkEntry(p, height=28, corner_radius=3, placeholder_text="ПАРОЛЬ", show="*", font=ctk.CTkFont(family=FONT_MONO, size=11), fg_color=BAY_BG, border_color=BORDER_METAL)
        pass_in.pack(fill="x", padx=12, pady=(2, 14))

        def submit():
            code = code_in.get().strip()
            if code:
                self.client.join_room(code, pass_in.get().strip())
                dlg.destroy()

        ctk.CTkButton(p, text="ПОДКЛЮЧИТЬ ПОРТ", height=32, corner_radius=3, fg_color="#1e3a5f", hover_color="#2563eb", font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"), command=submit).pack(fill="x", padx=12)

    def _copy(self, text, message="Скопировано"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _start_led_pulse(self):
        self.led_state = not self.led_state
        if self.active_module == "patchbay" and self.client.room:
            self._show_module("patchbay")
        self.after(1000, self._start_led_pulse)

    def _bind_client_events(self):
        def on_conn(status):
            try:
                self.after(0, lambda: self.lcd_label_1.configure(
                    text="[SYS: ONLINE]  LINK: READY" if status else "[SYS: ERROR]  LINK: OFFLINE",
                    text_color=LCD_TEXT if status else LED_RED_ON
                ))
            except Exception:
                pass

        def on_room(room):
            try:
                if room:
                    self.after(0, lambda: self.lcd_label_2.configure(
                        text=f"ROOM: {room.get('code')}  |  HOST: 10.42.0.1"
                    ))
                else:
                    self.after(0, lambda: self.lcd_label_2.configure(
                        text="ROOM: DISCONNECTED  |  DIRECT: STANDBY"
                    ))
                self.after(0, lambda: self._show_module("patchbay"))
            except Exception:
                pass

        def on_ping(rtt):
            try:
                self.after(0, lambda: self.lcd_label_1.configure(
                    text=f"[SYS: ONLINE]  RTT: {rtt}ms  |  PEERS: {len(self.client.room.get('peers', [])) if self.client.room else 0}/16"
                ))
            except Exception:
                pass

        def on_chat(msg):
            try:
                self.after(0, lambda: self._show_module("chat") if self.active_module == "chat" else None)
            except Exception:
                pass

        def on_game(game):
            try:
                self.after(0, lambda: self._show_module("radar") if self.active_module == "radar" else None)
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
