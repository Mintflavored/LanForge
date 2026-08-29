"""
Top Navigation Component for LANForge (Animated Sliding Tab Indicator, Logo, Quick Actions)
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
from gui.anim import PulseDotController, SlidingTabIndicator

class TopNavBar(ctk.CTkFrame):
    def __init__(self, parent, on_tab_selected, on_create_clicked, on_join_clicked):
        super().__init__(parent, height=54, fg_color=BG_COLOR, corner_radius=0)
        self.on_tab_selected = on_tab_selected
        self.on_create_clicked = on_create_clicked
        self.on_join_clicked = on_join_clicked

        self.tab_btns = {}
        self.tab_positions = {
            "overview": (4, 82),
            "games": (88, 80),
            "radar": (170, 102),
            "chat": (274, 76),
            "diag": (352, 110),
        }
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

        # Pulse on brand dot
        self.pulse_ctrl = PulseDotController(dot_lbl, color_on=ACCENT_ORANGE, color_off="#662200", interval_ms=70)

        # Tab Selector Container
        self.tabs_bar = ctk.CTkFrame(self, width=470, height=36, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        self.tabs_bar.pack(side="left", padx=24)
        self.tabs_bar.pack_propagate(False)

        # Sliding Animated Highlight Pill (width & height passed to constructor)
        self.pill = ctk.CTkFrame(self.tabs_bar, width=82, height=28, fg_color="#242429", corner_radius=6, border_width=1, border_color="#3f3f46")
        self.pill.place(x=4, y=4)
        self.slider = SlidingTabIndicator(self.tabs_bar, self.pill)

        # Tabs Layout
        tabs = [
            ("overview", "Обзор", 82),
            ("games", "Игры", 80),
            ("radar", "LAN Радар", 102),
            ("chat", "Чат", 76),
            ("diag", "Диагностика", 110),
        ]

        curr_x = 4
        for tab_id, label, width in tabs:
            btn = ctk.CTkButton(
                self.tabs_bar,
                text=label,
                height=28,
                width=width,
                corner_radius=6,
                fg_color="transparent",
                hover_color="#1a1a1f",
                text_color=TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
                command=lambda t=tab_id: self.on_tab_selected(t)
            )
            btn.place(x=curr_x, y=4)
            self.tab_btns[tab_id] = btn
            self.tab_positions[tab_id] = (curr_x, width)
            curr_x += width + 2

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
        if active_tab_id in self.tab_positions:
            target_x, target_w = self.tab_positions[active_tab_id]
            self.slider.slide_to(target_x, target_w)

        for tab_id, btn in self.tab_btns.items():
            if tab_id == active_tab_id:
                btn.configure(text_color=TEXT_MAIN)
            else:
                btn.configure(text_color=TEXT_MUTED)
