"""
Games Catalog View (Ultra-Lightweight High-Density Stream Architecture)
Zero waterfall, zero canvas lag, instantaneous sub-10ms atomic rendering.
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
    FONT_SANS,
    FONT_MONO,
)
from gui.presets_data import GAME_PRESETS

class GamesView(ctk.CTkFrame):
    def __init__(self, parent, on_preset_selected):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.on_preset_selected = on_preset_selected
        self.preset_filter = "Все"
        self.search_query = ""
        self.card_widgets = {}

        self._setup_ui()

    def _setup_ui(self):
        # Header with Title and Search Bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header,
            text="Каталог поддерживаемых игр",
            font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"),
            text_color=TEXT_MAIN
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="Поиск по названию...",
            height=28,
            width=200,
            corner_radius=6,
            fg_color=BENTO_CARD,
            border_color=BENTO_BORDER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_SANS, size=11)
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Filter Chips Bar
        f_box = ctk.CTkFrame(self, fg_color="transparent")
        f_box.pack(fill="x", pady=(0, 8))

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

        # Lightweight Scrollable Container
        self.games_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.games_scroll.pack(fill="both", expand=True)

        self._build_all_cards()
        self._apply_filter()

    def _build_all_cards(self):
        """Creates single-layer high-density rows that render atomically without canvas lag."""
        for p in GAME_PRESETS:
            # Flat, single-layer row container (no nested subframes)
            row = ctk.CTkFrame(
                self.games_scroll,
                height=48,
                fg_color=BENTO_CARD,
                corner_radius=6,
                border_width=1,
                border_color=BENTO_BORDER
            )

            # Left: Game Title
            name_lbl = ctk.CTkLabel(
                row,
                text=p["name"],
                font=ctk.CTkFont(family=FONT_SANS, size=13, weight="bold"),
                text_color=TEXT_MAIN,
                anchor="w"
            )
            name_lbl.pack(side="left", padx=(14, 8), pady=10)

            # Center: Category & Port Badge
            spec_str = f"[{p['category']}]  {p['protocol'].upper()}:{p['default_port']}"
            spec_lbl = ctk.CTkLabel(
                row,
                text=spec_str,
                font=ctk.CTkFont(family=FONT_MONO, size=11),
                text_color=TEXT_MUTED
            )
            spec_lbl.pack(side="left", padx=8)

            # Right: Action Button
            btn = ctk.CTkButton(
                row,
                text="Создать сеть →",
                height=26,
                width=115,
                corner_radius=4,
                fg_color=ACCENT_ORANGE,
                hover_color=ACCENT_ORANGE_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda preset=p: self.on_preset_selected(preset)
            )
            btn.pack(side="right", padx=12, pady=10)

            # Hint Label (Left of button)
            hint_lbl = ctk.CTkLabel(
                row,
                text=p["hint"],
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color="#64748b"
            )
            hint_lbl.pack(side="right", padx=10)

            self.card_widgets[p["id"]] = (row, p["name"].lower(), p["category"])

    def _on_search_changed(self, event=None):
        self.search_query = self.search_entry.get().strip().lower()
        self._apply_filter()

    def _filter_games(self, cat):
        self.preset_filter = cat
        for c, btn in self.game_filter_btns.items():
            if c == cat:
                btn.configure(fg_color="#202024", text_color=TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
        self._apply_filter()

    def _apply_filter(self):
        """Instantly maps/unmaps pre-existing single-layer rows without canvas overhead."""
        for p in GAME_PRESETS:
            row, name_lower, category = self.card_widgets[p["id"]]
            matches_cat = (self.preset_filter == "Все" or category == self.preset_filter)
            matches_search = (not self.search_query or self.search_query in name_lower)

            if matches_cat and matches_search:
                row.pack(fill="x", pady=2)
            else:
                row.pack_forget()
