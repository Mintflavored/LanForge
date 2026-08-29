"""
Diagnostics & Telemetry View (NAT type, UPnP, Subnet, MTU)
"""

import customtkinter as ctk
from gui.theme import (
    BENTO_CARD,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    FONT_SANS,
)

class DiagView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self._setup_ui()

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="Сетевая диагностика", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 12))

        box = ctk.CTkFrame(self, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
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
