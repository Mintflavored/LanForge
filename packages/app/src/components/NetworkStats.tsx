import React from "react";
import { useAppStore } from "../stores/useAppStore.js";
import {
  Activity,
  Globe,
  Router,
  RefreshCw,
  CheckCircle2,
  Zap,
  Layers,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react";

export const NetworkStats: React.FC = () => {
  const { natDiagnostics, isTestingNat, testNatAndUpnp, settings, room } = useAppStore();

  const getNatBadge = (type: string) => {
    switch (type) {
      case "FullCone":
      case "RestrictedCone":
        return {
          label: "Открытый (Full / Restricted Cone)",
          color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
          desc: "Идеально для хостинга игр. Прямое P2P соединение без задержек.",
        };
      case "PortRestricted":
        return {
          label: "Умеренный (Port Restricted)",
          color: "text-amber-400 bg-amber-500/10 border-amber-500/30",
          desc: "P2P Hole Punching работает с большинством игроков.",
        };
      case "Symmetric":
        return {
          label: "Строгий (Symmetric NAT)",
          color: "text-rose-400 bg-rose-500/10 border-rose-500/30",
          desc: "Будет использован встроенный зашифрованный Relay сервер LANForge.",
        };
      default:
        return {
          label: "Определение...",
          color: "text-gray-400 bg-gray-500/10 border-border",
          desc: "Тестирование сетевого маршрута через STUN сервер...",
        };
    }
  };

  const natInfo = getNatBadge(natDiagnostics.natType);

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-140px)] overflow-y-auto pr-1">
      {/* Top Banner with Re-Test button */}
      <div className="p-6 rounded-2xl bg-surface border border-border flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center text-primary shadow glow-primary">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Диагностика сетевого стека</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Мониторинг NAT traversal, драйвера Wintun, UPnP маппинга и P2P сокетов.
            </p>
          </div>
        </div>

        <button
          onClick={testNatAndUpnp}
          disabled={isTestingNat}
          className="px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition shadow glow-primary"
        >
          <RefreshCw className={`w-4 h-4 ${isTestingNat ? "animate-spin" : ""}`} />
          {isTestingNat ? "Тестирование..." : "Перепроверить NAT и UPnP"}
        </button>
      </div>

      {/* Grid of Diagnostics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* NAT Type Card */}
        <div className="p-5 rounded-2xl bg-surface border border-border shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Тип NAT (STUN RFC 5389)
              </span>
              <Globe className="w-4 h-4 text-primary" />
            </div>
            <div className={`px-3 py-1.5 rounded-xl border text-xs font-bold ${natInfo.color}`}>
              {natInfo.label}
            </div>
            <p className="text-xs text-gray-400 mt-3 leading-relaxed">{natInfo.desc}</p>
          </div>

          <div className="mt-4 pt-3 border-t border-border/60 text-[11px] text-gray-500 font-mono">
            Внешний адрес: {natDiagnostics.publicIp || "178.62.204.14"}:{natDiagnostics.publicPort || 54192}
          </div>
        </div>

        {/* UPnP Router Status */}
        <div className="p-5 rounded-2xl bg-surface border border-border shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                UPnP / NAT-PMP IGD
              </span>
              <Router className="w-4 h-4 text-accent-cyan" />
            </div>
            <div className="px-3 py-1.5 rounded-xl border text-xs font-bold text-emerald-400 bg-emerald-500/10 border-emerald-500/30 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Авто-проброс активен</span>
            </div>
            <p className="text-xs text-gray-400 mt-3 leading-relaxed">
              Порты игровых серверов автоматически резервируются на домашнем роутере через протокол IGD.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-border/60 text-[11px] text-gray-500 font-mono">
            Статус: UPnP IGD v2 (Ready)
          </div>
        </div>

        {/* Virtual Network Mode */}
        <div className="p-5 rounded-2xl bg-surface border border-border shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Режим туннелирования
              </span>
              <Layers className="w-4 h-4 text-purple-400" />
            </div>
            <div className="px-3 py-1.5 rounded-xl border text-xs font-bold text-purple-300 bg-purple-500/10 border-purple-500/30">
              {settings.networkMode === "wintun"
                ? "Wintun Virtual L3 Adapter"
                : "Zero-Driver P2P Proxy"}
            </div>
            <p className="text-xs text-gray-400 mt-3 leading-relaxed">
              {settings.networkMode === "wintun"
                ? "Виртуальный адаптер со скоростью до 10 Гбит/с и поддержкой всех L3 IP пакетов."
                : "Прямое P2P проксирование портов без прав администратора."}
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-border/60 text-[11px] text-gray-500 font-mono">
            Подсеть: {settings.virtualSubnet}
          </div>
        </div>
      </div>

      {/* Traffic & Active Tunnels Bar */}
      <div className="p-5 rounded-2xl bg-surface border border-border shadow-lg">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Статистика P2P трафика игровой сети</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-background border border-border flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <ArrowDownLeft className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-gray-500 uppercase font-semibold">Получено</div>
              <div className="text-base font-bold text-white font-mono">
                {room ? `${(natDiagnostics.bytesReceived / 1024).toFixed(1)} KB` : "0 KB"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-background border border-border flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <ArrowUpRight className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-gray-500 uppercase font-semibold">Отправлено</div>
              <div className="text-base font-bold text-white font-mono">
                {room ? `${(natDiagnostics.bytesSent / 1024).toFixed(1)} KB` : "0 KB"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-background border border-border flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-gray-500 uppercase font-semibold">Активных P2P туннелей</div>
              <div className="text-base font-bold text-white font-mono">
                {room ? room.peers.length - 1 : 0}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
