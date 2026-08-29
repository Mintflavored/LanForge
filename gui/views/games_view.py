"""
Games Catalog View (Filter Chips, Preset Cards, 1-Click Room Creation)
"""

import customtkinter as ctk
from gui.theme import (
    BENTO_CARD,
    BENTO_HOVER,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    FONT_SANS,
    FONT_MONO,
)
from gui.presets_data import GAME_PRESETS

class GamesView(ctk.CTkFrame):
    def __init__(self, parent, on_preset_selected):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.on_preset_selected = on_preset_selected
        self.preset_filter = "Все"

        self._setup_ui()

    def _setup_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header, text="Каталог игр", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

        # Category chips
        f_box = ctk.CTkFrame(self, fg_color="transparent")
        f_box.pack(fill="x", pady=(0, 10))

        self.game_filter_btns = {}
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
                command=lambda c=cat: self._filter_games(c)
            )
            btn.pack(side="left", padx=2)
            self.game_filter_btns[cat] = btn

        self.games_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.games_scroll.pack(fill="both", expand=True)

        self._render_game_cards()

    def _filter_games(self, cat):
        self.preset_filter = cat
        for c, btn in self.game_filter_btns.items():
            if c == cat:
                btn.configure(fg_color="#202024", text_color=TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
        self._render_game_cards()

    def _render_game_cards(self):
        for w in self.games_scroll.winfo_children():
            w.destroy()

        filtered = [
            p for p in GAME_PRESETS
            if (self.preset_filter == "Все" or p["category"] == self.preset_filter)
        ]

        for p in filtered:
            card = ctk.CTkFrame(self.games_scroll, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
            card.pack(fill="x", pady=4)

            c_pad = ctk.CTkFrame(card, fg_color="transparent")
            c_pad.pack(fill="x", padx=14, pady=10)

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
                command=lambda preset=p: self.on_preset_selected(preset)
            ).pack(side="right")

            ctk.CTkLabel(c_pad, text=p["description"], font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(c_pad, text=f"Инструкция: {p['hint']}", font=ctk.CTkFont(family=FONT_SANS, size=10), text_color=TEXT_MUTED).pack(anchor="w")
