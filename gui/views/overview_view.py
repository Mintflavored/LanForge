"""
Overview View (Bento Grid Dashboard with Room Card, Virtual IP, Latency and NAT)
"""

import customtkinter as ctk
from gui.theme import (
    BENTO_CARD,
    BENTO_HOVER,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    ACCENT_GREEN,
    ACCENT_RED,
    FONT_SANS,
    FONT_MONO,
)
from gui.presets_data import GAME_PRESETS

class OverviewView(ctk.CTkFrame):
    def __init__(self, parent, client, on_create_requested, on_join_requested, copy_helper):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.client = client
        self.on_create_requested = on_create_requested
        self.on_join_requested = on_join_requested
        self.copy_helper = copy_helper

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # LEFT BENTO: Room Card
        self.left_bento = ctk.CTkFrame(self, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        self.left_bento.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.lb_pad = ctk.CTkFrame(self.left_bento, fg_color="transparent")
        self.lb_pad.pack(fill="both", expand=True, padx=20, pady=20)

        # Standby View Elements
        self.standby_frame = ctk.CTkFrame(self.lb_pad, fg_color="transparent")
        self.standby_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(self.standby_frame, text="ВИРТУАЛЬНАЯ СЕТЬ", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkLabel(self.standby_frame, text="Сеть не подключена", font=ctk.CTkFont(family=FONT_SANS, size=24, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 8))
        ctk.CTkLabel(
            self.standby_frame,
            text="Создайте комнату для совместной игры или введите 6-значный код комнаты хоста для подключения.",
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            text_color=TEXT_SECONDARY,
            wraplength=420,
            justify="left"
        ).pack(anchor="w", pady=(0, 24))

        standby_btns = ctk.CTkFrame(self.standby_frame, fg_color="transparent")
        standby_btns.pack(anchor="w")

        ctk.CTkButton(
            standby_btns,
            text="Создать комнату",
            height=36,
            width=150,
            corner_radius=8,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            command=self.on_create_requested
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            standby_btns,
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
            command=self.on_join_requested
        ).pack(side="left")

        # Active Room View Elements
        self.active_frame = ctk.CTkFrame(self.lb_pad, fg_color="transparent")

        top_meta = ctk.CTkFrame(self.active_frame, fg_color="transparent")
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

        title_row = ctk.CTkFrame(self.active_frame, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 10))

        self.room_title = ctk.CTkLabel(title_row, text="Комната", font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"), text_color=TEXT_MAIN)
        self.room_title.pack(side="left")

        self.code_btn = ctk.CTkButton(
            title_row,
            text="LAN-XXXX 📋",
            height=26,
            width=100,
            corner_radius=6,
            fg_color="#1e1e24",
            hover_color="#27272e",
            border_width=1,
            border_color=BENTO_BORDER,
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        self.code_btn.pack(side="left", padx=12)

        # Direct Connect String Block
        connect_box = ctk.CTkFrame(self.active_frame, fg_color="#18181c", corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        connect_box.pack(fill="x", pady=(0, 12))

        cb_pad = ctk.CTkFrame(connect_box, fg_color="transparent")
        cb_pad.pack(fill="x", padx=12, pady=8)

        self.direct_lbl = ctk.CTkLabel(cb_pad, text="Адрес хоста в игре:  10.42.0.1:25565", font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"), text_color=TEXT_MAIN)
        self.direct_lbl.pack(side="left")

        self.direct_btn = ctk.CTkButton(
            cb_pad,
            text="Копировать адрес",
            height=24,
            width=130,
            corner_radius=4,
            fg_color="#27272a",
            hover_color=BENTO_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
            text_color=TEXT_MAIN
        )
        self.direct_btn.pack(side="right")

        self.peers_header = ctk.CTkLabel(self.active_frame, text="Участники (0/16):", font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), text_color=TEXT_MUTED)
        self.peers_header.pack(anchor="w", pady=(0, 6))

        self.peers_scroll = ctk.CTkScrollableFrame(self.active_frame, fg_color="transparent")
        self.peers_scroll.pack(fill="both", expand=True)

        # RIGHT BENTO TILES
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_rowconfigure(2, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        # Tile 1: IP Display
        t1 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t1.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        t1_pad = ctk.CTkFrame(t1, fg_color="transparent")
        t1_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t1_pad, text="ВАШ ВИРТУАЛЬНЫЙ IP", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.ip_val = ctk.CTkLabel(t1_pad, text="10.42.0.X", font=ctk.CTkFont(family=FONT_MONO, size=22, weight="bold"), text_color=TEXT_MAIN)
        self.ip_val.pack(anchor="w", pady=(2, 4))

        self.ip_btn = ctk.CTkButton(
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
            command=self._copy_my_ip
        )
        self.ip_btn.pack(anchor="w")

        # Tile 2: Ping Display
        t2 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t2.grid(row=1, column=0, sticky="nsew", pady=4)

        t2_pad = ctk.CTkFrame(t2, fg_color="transparent")
        t2_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t2_pad, text="ЗАДЕРЖКА СЕТИ (RTT)", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.ping_val = ctk.CTkLabel(t2_pad, text="< 1 ms", font=ctk.CTkFont(family=FONT_MONO, size=22, weight="bold"), text_color=ACCENT_GREEN)
        self.ping_val.pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(t2_pad, text="● Прямой P2P туннель активен", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")

        # Tile 3: NAT Display
        t3 = ctk.CTkFrame(right_container, fg_color=BENTO_CARD, corner_radius=12, border_width=1, border_color=BENTO_BORDER)
        t3.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

        t3_pad = ctk.CTkFrame(t3, fg_color="transparent")
        t3_pad.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(t3_pad, text="ШЛЮЗ И UPNP МАРШРУТИЗАЦИЯ", font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkLabel(t3_pad, text="Restricted Cone NAT", font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(t3_pad, text="UPnP IGD авто-проброс портов включен", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")

    def _copy_my_ip(self):
        val = self.ip_val.cget("text")
        if val and val != "10.42.0.X":
            self.copy_helper(self.ip_btn, "Копировать IP", val)

    def update_state(self, room, you):
        if not room:
            self.active_frame.pack_forget()
            self.standby_frame.pack(fill="both", expand=True)
            self.ip_val.configure(text="10.42.0.X")
            return

        self.standby_frame.pack_forget()
        self.active_frame.pack(fill="both", expand=True)

        code_str = room.get("code", "LAN-XXXX")
        self.room_title.configure(text=room.get("name", "Комната"))
        self.code_btn.configure(
            text=f"{code_str} 📋",
            command=lambda: self.copy_helper(self.code_btn, f"{code_str} 📋", code_str)
        )

        my_ip = you.get("virtualIp", "10.42.0.1") if you else "10.42.0.1"
        self.ip_val.configure(text=my_ip)

        # Dynamic Game Preset Port Resolution
        preset_id = room.get("gamePreset", "minecraft_java")
        preset = next((p for p in GAME_PRESETS if p["id"] == preset_id), None)
        port = preset["default_port"] if preset else 25565
        host_ip = "10.42.0.1"
        direct_addr = f"{host_ip}:{port}"

        self.direct_lbl.configure(text=f"Адрес хоста в игре:  {direct_addr}")
        self.direct_btn.configure(
            text="Копировать адрес",
            command=lambda: self.copy_helper(self.direct_btn, "Копировать адрес", direct_addr)
        )

        peers = room.get("peers", [])
        self.peers_header.configure(text=f"Участники ({len(peers)}/{room.get('maxPeers', 16)}):")

        for w in self.peers_scroll.winfo_children():
            w.destroy()

        for peer in peers:
            p_row = ctk.CTkFrame(self.peers_scroll, fg_color="#18181c", corner_radius=6, border_width=1, border_color=BENTO_BORDER)
            p_row.pack(fill="x", pady=2)

            pr_pad = ctk.CTkFrame(p_row, fg_color="transparent")
            pr_pad.pack(fill="x", padx=10, pady=6)

            ctk.CTkLabel(pr_pad, text="●", font=ctk.CTkFont(size=9), text_color=ACCENT_GREEN).pack(side="left", padx=(0, 6))

            nick_txt = peer.get("nick", "User")
            if peer.get("isHost"):
                nick_txt += " (Хост)"
            if you and peer.get("id") == you.get("id"):
                nick_txt += " (Вы)"

            ctk.CTkLabel(pr_pad, text=nick_txt, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

            v_ip = peer.get("virtualIp", "")
            ip_btn = ctk.CTkButton(
                pr_pad,
                text=f"{v_ip} 📋",
                height=20,
                width=100,
                corner_radius=4,
                fg_color="#202024",
                hover_color=BENTO_HOVER,
                font=ctk.CTkFont(family=FONT_MONO, size=10),
                text_color=TEXT_SECONDARY
            )
            ip_btn.configure(command=lambda b=ip_btn, target=v_ip: self.copy_helper(b, f"{target} 📋", target))
            ip_btn.pack(side="left", padx=12)

            ping = peer.get("pingMs", 0)
            p_str = f"{ping} ms" if ping > 0 else "< 1 ms"
            p_col = ACCENT_GREEN if ping < 50 else (ACCENT_ORANGE if ping < 100 else ACCENT_RED)
            ctk.CTkLabel(pr_pad, text=p_str, font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=p_col).pack(side="right")

    def update_ping(self, rtt):
        p_str = f"{rtt} ms" if rtt > 0 else "< 1 ms"
        p_col = ACCENT_GREEN if rtt < 50 else (ACCENT_ORANGE if rtt < 100 else ACCENT_RED)
        self.ping_val.configure(text=p_str, text_color=p_col)
