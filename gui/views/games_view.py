"""
Games Catalog View (Bento Grid Architecture — 2-Column High-Speed Layout)
Opaque background, zero scrollbar canvas overhead, zero waterfall redraws.
"""

import customtkinter as ctk
from gui.theme import (
    BG_COLOR,
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
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
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
            width=220,
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
        f_box.pack(fill="x", pady=(0, 12))

        self.game_filter_btns = {}
        cats = ["Все", "Песочницы", "Шутеры", "Выживание", "Классика"]
        for cat in cats:
            btn = ctk.CTkButton(
                f_box,
                text=cat,
                height=26,
                width=85,
                corner_radius=6,
                fg_color="#202024" if self.preset_filter == cat else "transparent",
                hover_color=BENTO_HOVER,
                text_color=TEXT_MAIN if self.preset_filter == cat else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda c=cat: self._filter_games(c)
            )
            btn.pack(side="left", padx=2)
            self.game_filter_btns[cat] = btn

        # 2-Column Bento Grid Container (Direct CTkFrame, zero Canvas scroll jitter)
        self.grid_container = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_columnconfigure(1, weight=1)

        self._build_all_cards()
        self._apply_filter()

    def _build_all_cards(self):
        """Creates pre-rendered Bento Cards for each game preset."""
        for p in GAME_PRESETS:
            card = ctk.CTkFrame(
                self.grid_container,
                height=68,
                fg_color=BENTO_CARD,
                corner_radius=8,
                border_width=1,
                border_color=BENTO_BORDER
            )

            # Left side content
            info_box = ctk.CTkFrame(card, fg_color="transparent")
            info_box.pack(side="left", fill="both", expand=True, padx=14, pady=8)

            title_row = ctk.CTkFrame(info_box, fg_color="transparent")
            title_row.pack(anchor="w")

            ctk.CTkLabel(
                title_row,
                text=p["name"],
                font=ctk.CTkFont(family=FONT_SANS, size=13, weight="bold"),
                text_color=TEXT_MAIN
            ).pack(side="left")

            port_badge = f"[{p['protocol'].upper()}:{p['default_port']}]"
            ctk.CTkLabel(
                title_row,
                text=port_badge,
                font=ctk.CTkFont(family=FONT_MONO, size=10),
                text_color=TEXT_MUTED
            ).pack(side="left", padx=8)

            ctk.CTkLabel(
                info_box,
                text=p["hint"],
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color="#71717a"
            ).pack(anchor="w", pady=(2, 0))

            # Right side action button
            btn = ctk.CTkButton(
                card,
                text="Создать",
                height=26,
                width=80,
                corner_radius=6,
                fg_color=ACCENT_ORANGE,
                hover_color=ACCENT_ORANGE_HOVER,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                command=lambda preset=p: self.on_preset_selected(preset)
            )
            btn.pack(side="right", padx=12, pady=12)

            self.card_widgets[p["id"]] = (card, p["name"].lower(), p["category"])

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
        """Arranges matching cards into a 2-column Bento Grid instantly."""
        for p in GAME_PRESETS:
            card, _, _ = self.card_widgets[p["id"]]
            card.grid_forget()

        matching = []
        for p in GAME_PRESETS:
            card, name_lower, category = self.card_widgets[p["id"]]
            matches_cat = (self.preset_filter == "Все" or category == self.preset_filter)
            matches_search = (not self.search_query or self.search_query in name_lower)
            if matches_cat and matches_search:
                matching.append(card)

        for idx, card in enumerate(matching):
            row_idx = idx // 2
            col_idx = idx % 2
            padx = (0, 6) if col_idx == 0 else (6, 0)
            card.grid(row=row_idx, column=col_idx, sticky="ew", padx=padx, pady=4)
