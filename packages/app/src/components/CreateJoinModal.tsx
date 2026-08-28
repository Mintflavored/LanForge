import React, { useState } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { GAME_PRESETS } from "../services/gamePresets.js";
import { PlusCircle, LogIn, Lock, X, Sparkles } from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: "create" | "join";
  preselectedGame?: string;
}

export const CreateJoinModal: React.FC<Props> = ({
  isOpen,
  onClose,
  initialMode = "create",
  preselectedGame,
}) => {
  const [mode, setMode] = useState<"create" | "join">(initialMode);
  const [roomName, setRoomName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [selectedGame, setSelectedGame] = useState(preselectedGame || "minecraft_java");
  const [password, setPassword] = useState("");
  const [hasPass, setHasPass] = useState(false);

  const { createRoom, joinRoom, settings } = useAppStore();

  if (!isOpen) return null;

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createRoom(roomName, selectedGame, hasPass ? password : undefined);
    onClose();
  };

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    joinRoom(joinCode.trim(), password || undefined);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg bg-surface border border-border rounded-2xl p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-gray-400 hover:text-white hover:bg-surface-hover transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Tab switcher */}
        <div className="flex bg-background p-1 rounded-xl mb-6 border border-border/50">
          <button
            onClick={() => setMode("create")}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition ${
              mode === "create"
                ? "bg-primary text-white shadow-lg glow-primary"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <PlusCircle className="w-4 h-4" />
            Создать комнату
          </button>
          <button
            onClick={() => setMode("join")}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition ${
              mode === "join"
                ? "bg-primary text-white shadow-lg glow-primary"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <LogIn className="w-4 h-4" />
            Подключиться по коду
          </button>
        </div>

        {mode === "create" ? (
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Название комнаты
              </label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder={`${settings.nick}'s LAN Room`}
                className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-white placeholder-gray-500 focus:outline-none focus:border-primary transition text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Основная игра
              </label>
              <select
                value={selectedGame}
                onChange={(e) => setSelectedGame(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-white focus:outline-none focus:border-primary transition text-sm"
              >
                {GAME_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name} ({preset.protocol.toUpperCase()}:{preset.defaultPort})
                  </option>
                ))}
              </select>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasPass}
                  onChange={(e) => setHasPass(e.target.checked)}
                  className="rounded border-border bg-background text-primary focus:ring-primary w-4 h-4"
                />
                <span>Защитить комнату паролем</span>
              </label>
              {hasPass && (
                <div className="mt-2 relative">
                  <Lock className="w-4 h-4 text-gray-500 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Введите пароль комнаты"
                    className="w-full pl-10 pr-4 py-2 rounded-xl bg-background border border-border text-white placeholder-gray-500 focus:outline-none focus:border-primary text-sm"
                  />
                </div>
              )}
            </div>

            <div className="pt-4">
              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold flex items-center justify-center gap-2 transition shadow-lg glow-primary"
              >
                <Sparkles className="w-5 h-5" />
                Запустить игровую сеть
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleJoin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Код комнаты (6 знаков)
              </label>
              <input
                type="text"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                placeholder="например: ABC-XYZ или 748-912"
                maxLength={8}
                className="w-full px-4 py-3 rounded-xl bg-background border border-border text-white text-center tracking-widest text-lg font-mono placeholder-gray-600 focus:outline-none focus:border-primary transition"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Пароль (если требуется)
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-500 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Пароль от хоста"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-background border border-border text-white placeholder-gray-500 focus:outline-none focus:border-primary text-sm"
                />
              </div>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={!joinCode.trim()}
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold flex items-center justify-center gap-2 transition shadow-lg glow-primary"
              >
                <LogIn className="w-5 h-5" />
                Войти в комнату
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
