"""
Games Catalog View (High-Performance Pre-Cached Cards Architecture)
Zero pop-in, zero waterfall redraws, pre-instantiated widgets.
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
        self.card_widgets = {}

        self._setup_ui()

    def _setup_ui(self):
        # Header title
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header,
            text="Каталог игр",
            font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"),
            text_color=TEXT_MAIN
        ).pack(side="left")

        # Category filter chips
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

        # Scrollable container for game cards
        self.games_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.games_scroll.pack(fill="both", expand=True)

        # Pre-instantiate all game cards ONCE into memory (Flat 1-layer geometry)
        self._build_all_cards()
        self._apply_filter()

    def _build_all_cards(self):
        """Creates lightweight, flattened card widgets once to eliminate pop-in loading."""
        for p in GAME_PRESETS:
            # Single lightweight card frame
            card = ctk.CTkFrame(
                self.games_scroll,
                fg_color=BENTO_CARD,
                corner_radius=8,
                border_width=1,
                border_color=BENTO_BORDER
            )

            # Row 1: Title, Port Pill, Create Button
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(10, 2))

            ctk.CTkLabel(
                top_row,
                text=p["name"],
                font=ctk.CTkFont(family=FONT_SANS, size=13, weight="bold"),
                text_color=TEXT_MAIN
            ).pack(side="left")

            port_pill = f"[{p['protocol'].upper()} {p['default_port']}]"
            ctk.CTkLabel(
                top_row,
                text=port_pill,
                font=ctk.CTkFont(family=FONT_MONO, size=11),
                text_color=TEXT_MUTED
            ).pack(side="left", padx=10)

            ctk.CTkButton(
                top_row,
                text="Создать комнату",
                height=26,
                width=120,
                corner_radius=6,
                fg_color=ACCENT_ORANGE,
                hover_color=ACCENT_ORANGE_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda preset=p: self.on_preset_selected(preset)
            ).pack(side="right")

            # Row 2: Description
            ctk.CTkLabel(
                card,
                text=p["description"],
                font=ctk.CTkFont(family=FONT_SANS, size=11),
                text_color=TEXT_MUTED,
                wraplength=640,
                justify="left"
            ).pack(anchor="w", padx=14, pady=(2, 2))

            # Row 3: Connection hint
            ctk.CTkLabel(
                card,
                text=f"Инструкция: {p['hint']}",
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color="#71717a"
            ).pack(anchor="w", padx=14, pady=(0, 10))

            self.card_widgets[p["id"]] = (card, p["category"])

    def _filter_games(self, cat):
        self.preset_filter = cat
        for c, btn in self.game_filter_btns.items():
            if c == cat:
                btn.configure(fg_color="#202024", text_color=TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
        self._apply_filter()

    def _apply_filter(self):
        """Instantly packs/unpacks already pre-rendered cards without recreating widgets."""
        for p in GAME_PRESETS:
            card, category = self.card_widgets[p["id"]]
            if self.preset_filter == "Все" or category == self.preset_filter:
                card.pack(fill="x", pady=4)
            else:
                card.pack_forget()
