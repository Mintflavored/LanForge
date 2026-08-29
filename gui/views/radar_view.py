"""
LAN Radar View (Automatic Broadcast Sniffer and Discovery)
"""

import customtkinter as ctk
from gui.theme import (
    BENTO_CARD,
    BENTO_HOVER,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    ACCENT_GREEN,
    FONT_SANS,
)

class RadarView(ctk.CTkFrame):
    def __init__(self, parent, client, copy_helper):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.client = client
        self.copy_helper = copy_helper
        self.rendered_count = 0

        self._setup_ui()

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="LAN Радар (Автопоиск серверов)", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 4))

        desc = ctk.CTkLabel(
            self,
            text="LANForge перехватывает широковещательные UDP-пакеты игр (Minecraft, Source) и ретранслирует их всем участникам комнаты.",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_MUTED
        )
        desc.pack(anchor="w", pady=(0, 12))

        sb = ctk.CTkFrame(self, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        sb.pack(fill="x", pady=(0, 12))

        sb_pad = ctk.CTkFrame(sb, fg_color="transparent")
        sb_pad.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(sb_pad, text="● Сканирование широковещательных пакетов активно", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=ACCENT_GREEN).pack(side="left")

        self.radar_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.radar_scroll.pack(fill="both", expand=True)

        self.update_radar()

    def update_radar(self):
        if not self.client.discovered_games:
            for w in self.radar_scroll.winfo_children():
                w.destroy()
            self.rendered_count = 0
            ctk.CTkLabel(self.radar_scroll, text="Активных LAN-миров в сети пока не обнаружено.\nОткройте мир для сети в Minecraft или запустите локальный сервер.", font=ctk.CTkFont(family=FONT_SANS, size=12), text_color=TEXT_MUTED).pack(pady=30)
            return

        if len(self.client.discovered_games) != self.rendered_count:
            self.rendered_count = len(self.client.discovered_games)
            for w in self.radar_scroll.winfo_children():
                w.destroy()

            for g in self.client.discovered_games:
                card = ctk.CTkFrame(self.radar_scroll, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
                card.pack(fill="x", pady=3)

                c_pad = ctk.CTkFrame(card, fg_color="transparent")
                c_pad.pack(fill="x", padx=12, pady=8)

                info_str = f"{g['name']}  |  {g['host_ip']}:{g['port']}"
                ctk.CTkLabel(c_pad, text=info_str, font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

                copy_btn = ctk.CTkButton(
                    c_pad,
                    text="Копировать адрес",
                    height=22,
                    width=130,
                    corner_radius=4,
                    fg_color="#1e1e24",
                    hover_color=BENTO_HOVER,
                    font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold")
                )
                target_str = f"{g['host_ip']}:{g['port']}"
                copy_btn.configure(command=lambda b=copy_btn, t=target_str: self.copy_helper(b, "Копировать адрес", t))
                copy_btn.pack(side="right")
