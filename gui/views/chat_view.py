"""
Chat View (Room Messaging Feed with Timestamping)
"""

import time
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

class ChatView(ctk.CTkFrame):
    def __init__(self, parent, client):
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.client = client
        self._setup_ui()

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="Чат комнаты", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 10))

        self.chat_scroll = ctk.CTkScrollableFrame(self, fg_color=BENTO_CARD, corner_radius=8, border_width=1, border_color=BENTO_BORDER)
        self.chat_scroll.pack(fill="both", expand=True, pady=(0, 10))

        input_box = ctk.CTkFrame(self, fg_color="transparent")
        input_box.pack(fill="x")

        self.chat_input = ctk.CTkEntry(
            input_box,
            placeholder_text="Напишите сообщение...",
            height=34,
            corner_radius=6,
            fg_color=BENTO_CARD,
            border_color=BENTO_BORDER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_SANS, size=12)
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())

        ctk.CTkButton(
            input_box,
            text="Отправить",
            height=34,
            width=100,
            corner_radius=6,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            command=self._send_chat
        ).pack(side="right")

    def append_message(self, msg):
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=6)

        t_str = time.strftime("%H:%M", time.localtime(msg.get("timestamp", time.time())))
        nick_str = msg.get("fromNick", "User")
        text_str = msg.get("text", "")

        is_me = self.client.you and msg.get("fromId") == self.client.you.get("id")
        nick_col = ACCENT_ORANGE if is_me else "#3b82f6"

        ctk.CTkLabel(row, text=f"[{t_str}]", font=ctk.CTkFont(family=FONT_MONO, size=10), text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(row, text=f"{nick_str}:", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=nick_col).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(row, text=text_str, font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MAIN, wraplength=700, justify="left").pack(side="left")

    def reset_chat(self):
        for w in self.chat_scroll.winfo_children():
            w.destroy()

    def _send_chat(self):
        text = self.chat_input.get().strip()
        if text:
            self.client.send_chat(text)
            self.chat_input.delete(0, "end")
