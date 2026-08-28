import React, { useState, useRef, useEffect } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { Send, MessageSquare, Shield } from "lucide-react";

export const RoomChat: React.FC = () => {
  const { chatMessages, sendChat, you, room } = useAppStore();
  const [inputText, setInputText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendChat(inputText.trim());
    setInputText("");
  };

  return (
    <div className="flex flex-col h-full bg-surface border border-border rounded-2xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-background/50">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-200">
          <MessageSquare className="w-4 h-4 text-primary" />
          <span>Чат комнаты</span>
        </div>
        <span className="text-xs text-gray-500 font-mono">
          {chatMessages.length} сообщ.
        </span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-3">
        {chatMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 text-xs">
            <MessageSquare className="w-8 h-8 mb-2 opacity-30" />
            <p>Чат комнаты пуст</p>
            <p className="text-[11px] text-gray-600 mt-0.5">
              Скидывайте сюда IP, порты или сообщения
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => {
            const isMe = msg.fromPeerId === you?.id;
            const isHost = room?.hostId === msg.fromPeerId;

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}
              >
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <span
                    className={`text-[11px] font-semibold ${
                      isMe ? "text-primary" : "text-gray-400"
                    }`}
                  >
                    {isMe ? "Вы" : msg.fromNick}
                  </span>
                  {isHost && (
                    <span className="flex items-center gap-0.5 text-[9px] px-1 py-0.2 bg-amber-500/20 text-amber-400 rounded">
                      <Shield className="w-2.5 h-2.5" />
                      Host
                    </span>
                  )}
                  <span className="text-[10px] text-gray-600">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <div
                  className={`max-w-[85%] px-3.5 py-2 rounded-2xl text-xs break-words shadow-sm ${
                    isMe
                      ? "bg-primary text-white rounded-br-none"
                      : "bg-surface-hover text-gray-200 rounded-bl-none border border-border/50"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 border-t border-border bg-background/50">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Написать сообщение в комнату..."
            className="flex-1 px-3.5 py-2 rounded-xl bg-background border border-border text-white placeholder-gray-500 focus:outline-none focus:border-primary text-xs"
          />
          <button
            type="submit"
            disabled={!inputText.trim()}
            className="p-2 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-white transition shadow"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
