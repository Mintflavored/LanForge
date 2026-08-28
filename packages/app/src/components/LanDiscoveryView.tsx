import React, { useState } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { Radio, Sparkles, Copy, Check, Gamepad2 } from "lucide-react";

export const LanDiscoveryView: React.FC = () => {
  const { discoveredGames, addDiscoveredGame, addToast } = useAppStore();
  const [copiedIp, setCopiedIp] = useState<string | null>(null);

  const handleCopy = (ipPort: string) => {
    navigator.clipboard.writeText(ipPort);
    setCopiedIp(ipPort);
    addToast(`Адрес ${ipPort} скопирован!`, "success");
    setTimeout(() => setCopiedIp(null), 2000);
  };

  const handleSimulateGame = () => {
    addDiscoveredGame({
      id: "game_" + Date.now(),
      gameName: "Minecraft World (Survival 1.21)",
      hostNick: "Alex_Host",
      hostIp: "10.42.0.1",
      port: 25565,
      detectedAt: Date.now(),
      motd: "A Minecraft Server - LAN Game",
    });
  };

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-140px)] overflow-y-auto pr-1">
      {/* Radar banner */}
      <div className="p-6 rounded-2xl bg-surface border border-border shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow glow-emerald">
              <Radio className="w-7 h-7 animate-pulse" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Magic LAN Discovery Scanner</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  Активно
                </span>
              </h2>
              <p className="text-xs text-gray-400 mt-1 max-w-xl">
                LANForge автоматически перехватывает широковещательные UDP-пакеты (Broadcast / Multicast)
                ваших игр и ретранслирует их всем участникам комнаты. Игры видят хост во вкладке «Локальная сеть» без ручного ввода IP.
              </p>
            </div>
          </div>

          <button
            onClick={handleSimulateGame}
            className="px-4 py-2 rounded-xl bg-surface-hover hover:bg-border text-xs font-semibold text-gray-200 border border-border flex items-center gap-2 transition"
          >
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Эмулировать UDP Broadcast
          </button>
        </div>
      </div>

      {/* Discovered games list */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-bold text-gray-300 flex items-center gap-2">
            <Gamepad2 className="w-4 h-4 text-emerald-400" />
            <span>Обнаруженные сервера в виртуальной сети ({discoveredGames.length})</span>
          </h3>
        </div>

        {discoveredGames.length === 0 ? (
          <div className="p-12 rounded-2xl bg-surface border border-border flex flex-col items-center justify-center text-center shadow-lg">
            <div className="w-16 h-16 rounded-full bg-background border border-border flex items-center justify-center mb-3">
              <Radio className="w-8 h-8 text-gray-600 animate-ping-slow" />
            </div>
            <h4 className="font-bold text-gray-300 text-sm">Ожидание широковещательных пакетов игр...</h4>
            <p className="text-xs text-gray-500 max-w-md mt-1">
              Когда хост в комнате откроет мир для сети в Minecraft, запустит сервер CS или Terraria — он моментально появится здесь.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {discoveredGames.map((game) => (
              <div
                key={game.id}
                className="p-5 rounded-2xl bg-surface border border-emerald-500/30 shadow-lg relative overflow-hidden"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-md uppercase">
                      Обнаружено по LAN
                    </span>
                    <h4 className="font-bold text-white text-base mt-1.5">{game.gameName}</h4>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Хост: <span className="text-gray-200 font-semibold">{game.hostNick}</span>
                    </p>
                    {game.motd && (
                      <p className="text-xs text-gray-500 italic mt-1">{game.motd}</p>
                    )}
                  </div>

                  <button
                    onClick={() => handleCopy(`${game.hostIp}:${game.port}`)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-background border border-border hover:border-emerald-400 text-xs font-mono font-bold text-gray-200 hover:text-white transition shadow"
                  >
                    <span>{game.hostIp}:{game.port}</span>
                    {copiedIp === `${game.hostIp}:${game.port}` ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
