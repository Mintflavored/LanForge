"""
Modal Dialogs for LANForge (Create Room, Join by Code)
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
    FONT_MONO,
)
from gui.presets_data import GAME_PRESETS

class CreateRoomDialog(ctk.CTkToplevel):
    def __init__(self, parent, client, default_preset=None):
        super().__init__(parent)
        self.client = client

        self.title("Создать комнату")
        self.geometry("380x320")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

        self._setup_ui(default_preset)

    def _setup_ui(self, default_preset):
        p = ctk.CTkFrame(self, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(
            p,
            text="Параметры комнаты",
            font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"),
            text_color=TEXT_MAIN
        ).pack(anchor="w", padx=14, pady=(12, 10))

        ctk.CTkLabel(p, text="Название комнаты:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        self.name_in = ctk.CTkEntry(
            p,
            height=30,
            corner_radius=6,
            placeholder_text=f"{self.client.nick}'s Party",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            fg_color="#18181c",
            border_color=BENTO_BORDER
        )
        self.name_in.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Игра:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        preset_names = [x["name"] for x in GAME_PRESETS]
        self.preset_var = ctk.StringVar(value=default_preset["name"] if default_preset else preset_names[0])
        opt = ctk.CTkOptionMenu(
            p,
            values=preset_names,
            variable=self.preset_var,
            height=30,
            corner_radius=6,
            fg_color="#18181c",
            button_color=BENTO_BORDER,
            font=ctk.CTkFont(family=FONT_SANS, size=11)
        )
        opt.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Пароль (опционально):", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        self.pass_in = ctk.CTkEntry(
            p,
            height=30,
            corner_radius=6,
            placeholder_text="Без пароля",
            show="*",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            fg_color="#18181c",
            border_color=BENTO_BORDER
        )
        self.pass_in.pack(fill="x", padx=14, pady=(2, 14))

        ctk.CTkButton(
            p,
            text="Создать сеть",
            height=32,
            corner_radius=6,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            command=self._submit
        ).pack(fill="x", padx=14)

    def _submit(self):
        r_name = self.name_in.get().strip() or f"{self.client.nick}'s Party"
        r_pass = self.pass_in.get().strip()
        sel_p = next((x for x in GAME_PRESETS if x["name"] == self.preset_var.get()), GAME_PRESETS[0])
        self.client.create_room(r_name, sel_p["id"], r_pass)
        self.destroy()


class JoinRoomDialog(ctk.CTkToplevel):
    def __init__(self, parent, client):
        super().__init__(parent)
        self.client = client

        self.title("Вход в комнату")
        self.geometry("360x240")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        p = ctk.CTkFrame(self, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        p.pack(padx=16, pady=16, fill="both", expand=True)

        ctk.CTkLabel(
            p,
            text="Подключение по коду",
            font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"),
            text_color=TEXT_MAIN
        ).pack(anchor="w", padx=14, pady=(12, 10))

        ctk.CTkLabel(p, text="Код комнаты (LAN-XXXX):", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        self.code_in = ctk.CTkEntry(
            p,
            height=30,
            corner_radius=6,
            placeholder_text="LAN-XXXX",
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            fg_color="#18181c",
            border_color=BENTO_BORDER
        )
        self.code_in.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(p, text="Пароль:", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=14)
        self.pass_in = ctk.CTkEntry(
            p,
            height=30,
            corner_radius=6,
            placeholder_text="Если требуется",
            show="*",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            fg_color="#18181c",
            border_color=BENTO_BORDER
        )
        self.pass_in.pack(fill="x", padx=14, pady=(2, 14))

        ctk.CTkButton(
            p,
            text="Подключиться",
            height=32,
            corner_radius=6,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            command=self._submit
        ).pack(fill="x", padx=14)

    def _submit(self):
        code = self.code_in.get().strip()
        if code:
            self.client.join_room(code, self.pass_in.get().strip())
            self.destroy()
