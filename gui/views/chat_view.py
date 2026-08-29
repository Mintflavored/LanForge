"""
Room Chat View (Teletype Messaging Stream)
"""

import time
import customtkinter as ctk
from gui.theme import (
    BENTO_CARD,
    BENTO_BORDER,
    TEXT_MAIN,
    TEXT_MUTED,
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    FONT_SANS,
)

class ChatView(ctk.CTkFrame):
    def __init__(self, parent, client):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.client = client
        self.rendered_count = 0

        self._setup_ui()

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="Чат комнаты", font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"), text_color=TEXT_MAIN)
        title.pack(anchor="w", pady=(0, 10))

        self.chat_feed = ctk.CTkScrollableFrame(self, fg_color=BENTO_CARD, corner_radius=10, border_width=1, border_color=BENTO_BORDER)
        self.chat_feed.pack(fill="both", expand=True, pady=(0, 10))

        self.empty_lbl = ctk.CTkLabel(self.chat_feed, text="Сообщений пока нет.", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED)
        self.empty_lbl.pack(pady=25)

        in_row = ctk.CTkFrame(self, fg_color="transparent")
        in_row.pack(fill="x")

        self.chat_entry = ctk.CTkEntry(
            in_row,
            placeholder_text="Введите сообщение...",
            height=34,
            corner_radius=8,
            fg_color=BENTO_CARD,
            border_color=BENTO_BORDER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_SANS, size=11)
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())

        send_btn = ctk.CTkButton(
            in_row,
            text="Отправить",
            height=34,
            width=90,
            corner_radius=8,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
            command=self._send_chat
        )
        send_btn.pack(side="right")

    def reset_chat(self):
        self.rendered_count = 0
        for w in self.chat_feed.winfo_children():
            w.destroy()
        self.empty_lbl = ctk.CTkLabel(self.chat_feed, text="Сообщений пока нет.", font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MUTED)
        self.empty_lbl.pack(pady=25)

    def append_message(self, msg):
        if self.rendered_count == 0 and self.empty_lbl.winfo_exists():
            self.empty_lbl.pack_forget()

        row = ctk.CTkFrame(self.chat_feed, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        t_str = time.strftime("%H:%M", time.localtime(msg.get("timestamp", 0) / 1000))
        ctk.CTkLabel(row, text=f"[{t_str}] {msg.get('fromNick', 'User')}:", font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"), text_color=ACCENT_ORANGE).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(row, text=msg.get("text", ""), font=ctk.CTkFont(family=FONT_SANS, size=11), text_color=TEXT_MAIN).pack(side="left")

        self.rendered_count += 1

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if text:
            self.client.send_chat(text)
            self.chat_entry.delete(0, "end")
