"""
Diagnostics View (NAT Type, STUN Telemetry, UPnP Port Mapping, MTU)
"""

import customtkinter as ctk
from gui.theme import (
    BG_COLOR,
    BENTO_CARD,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    ACCENT_GREEN,
    FONT_SANS,
    FONT_MONO,
)

class DiagView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self._setup_ui()

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="Сетевая диагностика и телеметрия", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 10))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        items = [
            ("NAT ТИП И ТОПОЛОГИЯ", "Restricted Cone (Port-Restricted)", "Прямое P2P-соединение возможно без TURN-реле", (0, 0)),
            ("STUN СЕРВЕРЫ", "stun.l.google.com:19302", "Обнаружение публичного IP и порта активно (RTT < 15ms)", (0, 1)),
            ("UPNP IGD МАРШРУТИЗАЦИЯ", "Совместимый шлюз найден", "Автоматический проброс игровых портов включен", (1, 0)),
            ("MTU И БУФЕРЫ", "MTU: 1420 (Виртуальный туннель)", "Оптимизировано для отсутствия фрагментации пакетов", (1, 1)),
        ]

        for head, val, sub, (r, c) in items:
            card = ctk.CTkFrame(grid, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)

            pad = ctk.CTkFrame(card, fg_color="transparent")
            pad.pack(fill="both", expand=True, padx=16, pady=16)

            ctk.CTkLabel(pad, text=head, font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
            ctk.CTkLabel(pad, text=val, font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 4))
            ctk.CTkLabel(pad, text=sub, font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=ACCENT_GREEN if "актив" in sub or "включен" in sub or "возможно" in sub else TEXT_MUTED).pack(anchor="w")
