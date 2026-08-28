import React, { useState } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { GAME_PRESETS } from "../services/gamePresets.js";
import {
  Radio,
  Copy,
  Check,
  Search,
  PlusCircle,
} from "lucide-react";

interface Props {
  onHostGame: (presetId: string) => void;
}

export const GamePresets: React.FC<Props> = ({ onHostGame }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedPort, setCopiedPort] = useState<number | null>(null);
  const { addToast } = useAppStore();

  const categories = [
    { id: "all", label: "Все игры" },
    { id: "sandbox", label: "Песочницы" },
    { id: "survival", label: "Выживание" },
    { id: "fps", label: "Шутеры / FPS" },
    { id: "classic", label: "Классика" },
  ];

  const filteredPresets = GAME_PRESETS.filter((p) => {
    const matchesCat = selectedCategory === "all" || p.category === selectedCategory;
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const handleCopyPort = (port: number) => {
    navigator.clipboard.writeText(port.toString());
    setCopiedPort(port);
    addToast(`Порт ${port} скопирован в буфер`, "success");
    setTimeout(() => setCopiedPort(null), 2000);
  };

  return (
    <div className="flex flex-col gap-5 h-[calc(100vh-140px)] overflow-y-auto pr-1">
      {/* Search & Filter Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-surface border border-border">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? "bg-primary text-white shadow glow-primary"
                  : "bg-background text-gray-400 hover:text-white border border-border"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Поиск игры по названию..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-background border border-border text-white text-xs placeholder-gray-500 focus:outline-none focus:border-primary transition"
          />
        </div>
      </div>

      {/* Preset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-6">
        {filteredPresets.map((preset) => (
          <div
            key={preset.id}
            className="p-5 rounded-2xl bg-surface border border-border hover:border-gray-600 transition-all flex flex-col justify-between shadow-lg group relative overflow-hidden"
          >
            <div
              className="absolute top-0 right-0 w-32 h-32 rounded-full blur-2xl opacity-10 pointer-events-none transition-all group-hover:opacity-20"
              style={{ backgroundColor: preset.color }}
            />

            <div>
              {/* Top badges */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: preset.color }}
                  />
                  <h3 className="font-bold text-sm text-white group-hover:text-primary transition">
                    {preset.name}
                  </h3>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleCopyPort(preset.defaultPort)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-background border border-border text-[11px] font-mono text-gray-300 hover:text-white hover:border-primary transition"
                    title="Скопировать порт"
                  >
                    <span>{preset.protocol.toUpperCase()}:{preset.defaultPort}</span>
                    {copiedPort === preset.defaultPort ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3 opacity-60" />
                    )}
                  </button>
                </div>
              </div>

              <p className="text-xs text-gray-400 leading-relaxed mb-3">
                {preset.description}
              </p>

              {/* Discovery & Info */}
              <div className="flex items-center gap-2 mb-4">
                {preset.lanDiscoverySupported ? (
                  <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    <Radio className="w-3 h-3 animate-pulse" />
                    Автопоиск LAN (Broadcast)
                  </span>
                ) : (
                  <span className="text-[10px] text-gray-500 font-medium px-2 py-0.5 rounded-md bg-background border border-border">
                    Прямое подключение по IP
                  </span>
                )}
              </div>

              {/* Hint */}
              <div className="p-2.5 rounded-xl bg-background/60 border border-border/60 text-[11px] text-gray-400 font-mono">
                {preset.connectHint}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 mt-2">
              <button
                onClick={() => onHostGame(preset.id)}
                className="w-full py-2.5 rounded-xl bg-primary/20 hover:bg-primary text-primary hover:text-white font-semibold text-xs flex items-center justify-center gap-2 transition duration-200 border border-primary/40 hover:shadow-lg hover:glow-primary"
              >
                <PlusCircle className="w-4 h-4" />
                Создать комнату под эту игру
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
