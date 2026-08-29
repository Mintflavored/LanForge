"""
Top Navigation Component for LANForge (Zero-Interruption Clean Tab Switching)
"""

import customtkinter as ctk
from gui.theme import (
    BG_COLOR,
    BENTO_CARD,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    FONT_SANS,
)

class TopNavBar(ctk.CTkFrame):
    def __init__(self, parent, on_tab_selected, on_create_clicked, on_join_clicked):
        super().__init__(parent, height=54, fg_color=BG_COLOR, corner_radius=0)
        self.on_tab_selected = on_tab_selected
        self.on_create_clicked = on_create_clicked
        self.on_join_clicked = on_join_clicked

        self.tab_btns = {}
        self._setup_ui()

    def _setup_ui(self):
        # Brand / Logo
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
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
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        dot_lbl.pack(side="left")

        # Tab Selector Container
        self.tabs_bar = ctk.CTkFrame(self, height=36, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        self.tabs_bar.pack(side="left", padx=24)

        tabs = [
            ("overview", "Обзор", 82),
            ("games", "Игры", 80),
            ("radar", "LAN Радар", 102),
            ("chat", "Чат", 76),
            ("diag", "Диагностика", 110),
        ]

        for tab_id, label, width in tabs:
            btn = ctk.CTkButton(
                self.tabs_bar,
                text=label,
                height=28,
                width=width,
                corner_radius=6,
                fg_color="#202024" if tab_id == "overview" else "transparent",
                hover_color="#1a1a1f",
                text_color=TEXT_MAIN if tab_id == "overview" else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                command=lambda t=tab_id: self.on_tab_selected(t)
            )
            btn.pack(side="left", padx=2, pady=3)
            self.tab_btns[tab_id] = btn

        # Right Action Buttons
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(side="right")

        self.create_btn = ctk.CTkButton(
            actions_frame,
            text="+ Создать сеть",
            height=30,
            width=120,
            corner_radius=6,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color="#ffffff",
            command=self.on_create_clicked
        )
        self.create_btn.pack(side="left", padx=(0, 8))

        self.join_btn = ctk.CTkButton(
            actions_frame,
            text="Войти по коду",
            height=30,
            width=110,
            corner_radius=6,
            fg_color=BENTO_CARD,
            hover_color="#1f1f26",
            border_width=1,
            border_color=BENTO_BORDER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color=TEXT_MAIN,
            command=self.on_join_clicked
        )
        self.join_btn.pack(side="left")

    def set_active_tab(self, active_tab_id):
        for tab_id, btn in self.tab_btns.items():
            if tab_id == active_tab_id:
                btn.configure(fg_color="#202024", text_color=TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
