import React, { useState } from "react";
import { useAppStore } from "../stores/useAppStore.js";
import { Settings, X, Save, Server, User, Shield } from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { settings, updateSettings, addToast } = useAppStore();
  const [nick, setNick] = useState(settings.nick);
  const [serverUrl, setServerUrl] = useState(settings.serverUrl);
  const [networkMode, setNetworkMode] = useState(settings.networkMode);
  const [autoUpnp, setAutoUpnp] = useState(settings.autoUpnp);
  const [broadcastRelay, setBroadcastRelay] = useState(settings.broadcastRelay);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateSettings({
      nick: nick.trim() || "Player",
      serverUrl: serverUrl.trim() || "ws://localhost:8787",
      networkMode,
      autoUpnp,
      broadcastRelay,
    });
    addToast("Настройки успешно сохранены!", "success");
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

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-primary/20 text-primary border border-primary/30">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Параметры LANForge</h2>
            <p className="text-xs text-gray-400">Настройки игрового профиля и сетевого адаптера</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          {/* Nickname */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-primary" />
              Игровой никнейм
            </label>
            <input
              type="text"
              value={nick}
              onChange={(e) => setNick(e.target.value)}
              placeholder="Ваш ник"
              className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-white text-sm focus:outline-none focus:border-primary transition"
              required
            />
          </div>

          {/* Server URL */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-primary" />
              Адрес сигнального сервера
            </label>
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="ws://localhost:8787"
              className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-white text-xs font-mono focus:outline-none focus:border-primary transition"
              required
            />
            <p className="text-[11px] text-gray-500 mt-1">
              Можно указать свой VPS с развернутым LANForge Signaling сервером.
            </p>
          </div>

          {/* Network Mode */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-primary" />
              Режим сетевого драйвера
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setNetworkMode("wintun")}
                className={`p-3 rounded-xl border text-left transition ${
                  networkMode === "wintun"
                    ? "border-primary bg-primary/10 text-white"
                    : "border-border bg-background text-gray-400 hover:text-white"
                }`}
              >
                <div className="font-semibold text-xs text-white">Wintun Adapter</div>
                <div className="text-[10px] text-gray-400 mt-0.5">Полная L3 виртуальная подсеть</div>
              </button>

              <button
                type="button"
                onClick={() => setNetworkMode("zero_driver")}
                className={`p-3 rounded-xl border text-left transition ${
                  networkMode === "zero_driver"
                    ? "border-primary bg-primary/10 text-white"
                    : "border-border bg-background text-gray-400 hover:text-white"
                }`}
              >
                <div className="font-semibold text-xs text-white">Zero-Driver Mode</div>
                <div className="text-[10px] text-gray-400 mt-0.5">Без прав админа / Прокси</div>
              </button>
            </div>
          </div>

          {/* Toggles */}
          <div className="space-y-2 pt-1">
            <label className="flex items-center justify-between p-3 rounded-xl bg-background border border-border cursor-pointer">
              <span className="text-xs text-gray-300 font-medium">
                Автоматический проброс UPnP на роутере
              </span>
              <input
                type="checkbox"
                checked={autoUpnp}
                onChange={(e) => setAutoUpnp(e.target.checked)}
                className="w-4 h-4 rounded border-border bg-surface text-primary focus:ring-primary"
              />
            </label>

            <label className="flex items-center justify-between p-3 rounded-xl bg-background border border-border cursor-pointer">
              <span className="text-xs text-gray-300 font-medium">
                Magic LAN Discovery (UDP Broadcast Relay)
              </span>
              <input
                type="checkbox"
                checked={broadcastRelay}
                onChange={(e) => setBroadcastRelay(e.target.checked)}
                className="w-4 h-4 rounded border-border bg-surface text-primary focus:ring-primary"
              />
            </label>
          </div>

          {/* Actions */}
          <div className="pt-4 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold text-gray-400 hover:text-white transition"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-semibold flex items-center gap-2 transition shadow glow-primary"
            >
              <Save className="w-4 h-4" />
              Сохранить изменения
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
