import React, { useState } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { GAME_PRESETS } from "../services/gamePresets.js";
import { RoomChat } from "./RoomChat.js";
import {
  Copy,
  Check,
  Users,
  Shield,
  LogOut,
  UserX,
  Gamepad2,
  Lock,
  Wifi,
  Sparkles,
} from "lucide-react";

export const RoomLobby: React.FC = () => {
  const { room, you, leaveRoom, kickPeer, addToast } = useAppStore();
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedIp, setCopiedIp] = useState<string | null>(null);

  if (!room || !you) return null;

  const currentPreset = GAME_PRESETS.find((p) => p.id === room.gamePreset);
  const hostPeer = room.peers.find((p) => p.id === room.hostId);
  const hostIp = hostPeer?.virtualIp || "10.42.0.1";

  const handleCopyCode = () => {
    navigator.clipboard.writeText(room.code);
    setCopiedCode(true);
    addToast(`Код комнаты ${room.code} скопирован в буфер!`, "success");
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleCopyIp = (ip: string) => {
    navigator.clipboard.writeText(ip);
    setCopiedIp(ip);
    addToast(`Виртуальный IP ${ip} скопирован!`, "success");
    setTimeout(() => setCopiedIp(null), 2000);
  };

  const getPingColor = (ping?: number) => {
    if (ping === undefined) return "text-gray-500 bg-gray-500/10";
    if (ping < 45) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
    if (ping < 95) return "text-amber-400 bg-amber-500/10 border-amber-500/30";
    return "text-rose-400 bg-rose-500/10 border-rose-500/30";
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
      {/* Left Column: Room info & Peers list */}
      <div className="lg:col-span-2 flex flex-col gap-5 overflow-y-auto pr-1">
        {/* Room Header Card */}
        <div className="p-5 rounded-2xl bg-surface border border-border relative overflow-hidden shadow-xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  Сеть активна
                </span>
                {room.hasPassword && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400">
                    <Lock className="w-3 h-3" /> Пароль
                  </span>
                )}
                {currentPreset && (
                  <span
                    className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
                    style={{ backgroundColor: `${currentPreset.color}25`, color: currentPreset.color }}
                  >
                    <Gamepad2 className="w-3 h-3" /> {currentPreset.name}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-white tracking-wide">{room.name}</h2>
            </div>

            <div className="flex items-center gap-2">
              {/* Room Code Share Button */}
              <button
                onClick={handleCopyCode}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-background border border-primary/40 text-primary hover:bg-primary/10 transition font-mono font-bold text-sm shadow-md"
              >
                {copiedCode ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                <span>{room.code}</span>
              </button>

              <button
                onClick={leaveRoom}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition text-sm font-medium"
              >
                <LogOut className="w-4 h-4" />
                Выйти
              </button>
            </div>
          </div>

          {/* Quick Connect Hint Bar */}
          {currentPreset && (
            <div className="mt-4 p-3 rounded-xl bg-background/80 border border-border/70 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-gray-300">
                <Sparkles className="w-4 h-4 text-primary shrink-0" />
                <span>
                  <strong>Прямое подключение к хосту:</strong>{" "}
                  <code className="px-2 py-0.5 bg-surface rounded text-primary font-mono font-bold">
                    {hostIp}:{currentPreset.defaultPort}
                  </code>
                </span>
              </div>
              <button
                onClick={() => handleCopyIp(`${hostIp}:${currentPreset.defaultPort}`)}
                className="px-2.5 py-1 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary font-medium transition"
              >
                Скопировать адрес для игры
              </button>
            </div>
          )}
        </div>

        {/* Peers List */}
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2 text-sm font-bold text-gray-300">
              <Users className="w-4 h-4 text-primary" />
              <span>Участники сети ({room.peers.length} / {room.maxPeers})</span>
            </div>
            <span className="text-xs text-gray-500">
              Подсеть: <code>10.42.0.0/24</code>
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {room.peers.map((peer) => {
              const isMe = peer.id === you.id;
              const isHost = peer.id === room.hostId;

              return (
                <div
                  key={peer.id}
                  className={`p-4 rounded-2xl bg-surface border transition-all duration-200 shadow-md ${
                    isMe
                      ? "border-primary/50 ring-1 ring-primary/30"
                      : "border-border hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-700 flex items-center justify-center font-bold text-white shadow">
                        {peer.nick.substring(0, 2).toUpperCase()}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-white">{peer.nick}</span>
                          {isMe && (
                            <span className="text-[10px] px-1.5 py-0.2 bg-primary/20 text-primary font-semibold rounded">
                              ВЫ
                            </span>
                          )}
                          {isHost && (
                            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.2 bg-amber-500/20 text-amber-400 font-semibold rounded border border-amber-500/30">
                              <Shield className="w-2.5 h-2.5" />
                              HOST
                            </span>
                          )}
                        </div>

                        {/* Virtual IP with 1-click copy */}
                        <button
                          onClick={() => handleCopyIp(peer.virtualIp)}
                          className="flex items-center gap-1.5 mt-1 text-xs font-mono text-gray-400 hover:text-white transition group"
                        >
                          <span>{peer.virtualIp}</span>
                          {copiedIp === peer.virtualIp ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Ping / Kick */}
                    <div className="flex flex-col items-end gap-1.5">
                      <div
                        className={`flex items-center gap-1 px-2 py-0.5 rounded-lg border text-[11px] font-mono font-semibold ${getPingColor(
                          peer.pingMs
                        )}`}
                      >
                        <Wifi className="w-3 h-3" />
                        <span>{peer.pingMs !== undefined ? `${peer.pingMs} ms` : "< 1 ms"}</span>
                      </div>

                      {you.isHost && !isMe && (
                        <button
                          onClick={() => kickPeer(peer.id)}
                          title="Исключить из комнаты"
                          className="p-1 rounded-lg text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
                        >
                          <UserX className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Right Column: Room Chat */}
      <div className="lg:col-span-1 h-full">
        <RoomChat />
      </div>
    </div>
  );
};
