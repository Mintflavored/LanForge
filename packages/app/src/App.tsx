import React, { useEffect, useState } from "react";
import { useAppStore } from "./stores/useAppStore.js";
import { RoomLobby } from "./components/RoomLobby.js";
import { GamePresets } from "./components/GamePresets.js";
import { LanDiscoveryView } from "./components/LanDiscoveryView.js";
import { NetworkStats } from "./components/NetworkStats.js";
import { CreateJoinModal } from "./components/CreateJoinModal.js";
import { SettingsModal } from "./components/SettingsModal.js";
import { ToastContainer } from "./components/Toast.js";
import {
  Gamepad2,
  Users,
  Radio,
  Activity,
  Settings,
  PlusCircle,
  LogIn,
  WifiOff,
} from "lucide-react";

export const App: React.FC = () => {
  const {
    init,
    isConnected,
    room,
    activeTab,
    setActiveTab,
    unreadChatCount,
    settings,
    discoveredGames,
  } = useAppStore();

  const [isCreateJoinOpen, setIsCreateJoinOpen] = useState(false);
  const [createJoinMode, setCreateJoinMode] = useState<"create" | "join">("create");
  const [preselectedGame, setPreselectedGame] = useState<string | undefined>(undefined);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    init();
  }, [init]);

  const handleOpenCreate = (gamePresetId?: string) => {
    setCreateJoinMode("create");
    setPreselectedGame(gamePresetId);
    setIsCreateJoinOpen(true);
  };

  const handleOpenJoin = () => {
    setCreateJoinMode("join");
    setPreselectedGame(undefined);
    setIsCreateJoinOpen(true);
  };

  return (
    <div className="flex flex-col h-screen bg-background text-gray-100 font-sans select-none overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="h-16 px-6 border-b border-border bg-surface/80 backdrop-blur-md flex items-center justify-between shrink-0 z-30">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-indigo-500 flex items-center justify-center text-white shadow-lg glow-primary">
            <Gamepad2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-wider bg-gradient-to-r from-white via-gray-200 to-primary bg-clip-text text-transparent">
                LANFORGE
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">
                v1.0
              </span>
            </div>
            <span className="text-[11px] text-gray-400 block -mt-0.5">
              P2P Gaming Virtual LAN Mesh
            </span>
          </div>
        </div>

        {/* Center Tabs */}
        <nav className="flex items-center gap-1 bg-background/80 p-1 rounded-xl border border-border/80">
          <button
            onClick={() => setActiveTab("lobby")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "lobby"
                ? "bg-surface text-white shadow-sm border border-border"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Users className="w-4 h-4 text-primary" />
            <span>Комната</span>
            {room && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            )}
            {unreadChatCount > 0 && (
              <span className="px-1.5 py-0.2 bg-primary text-white text-[10px] rounded-full font-bold">
                {unreadChatCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("presets")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "presets"
                ? "bg-surface text-white shadow-sm border border-border"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Gamepad2 className="w-4 h-4 text-accent-amber" />
            <span>Каталог игр</span>
          </button>

          <button
            onClick={() => setActiveTab("lan_discovery")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "lan_discovery"
                ? "bg-surface text-white shadow-sm border border-border"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Radio className="w-4 h-4 text-emerald-400" />
            <span>LAN Radar</span>
            {discoveredGames.length > 0 && (
              <span className="px-1.5 py-0.2 bg-emerald-500/20 text-emerald-400 text-[10px] rounded-full font-bold border border-emerald-500/30">
                {discoveredGames.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("diagnostics")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "diagnostics"
                ? "bg-surface text-white shadow-sm border border-border"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Activity className="w-4 h-4 text-accent-cyan" />
            <span>Сеть & NAT</span>
          </button>
        </nav>

        {/* Right Info & Actions */}
        <div className="flex items-center gap-3">
          {/* Server Connection Status */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-semibold ${
              isConnected
                ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                : "text-rose-400 bg-rose-500/10 border-rose-500/30"
            }`}
          >
            {isConnected ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Online</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span>Offline</span>
              </>
            )}
          </div>

          {/* User Nick & Settings button */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface hover:bg-surface-hover border border-border text-xs font-medium text-gray-200 transition"
          >
            <div className="w-5 h-5 rounded-full bg-primary/30 text-primary flex items-center justify-center font-bold text-[10px]">
              {settings.nick.substring(0, 1).toUpperCase()}
            </div>
            <span>{settings.nick}</span>
            <Settings className="w-3.5 h-3.5 text-gray-400 ml-0.5" />
          </button>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="flex-1 p-6 overflow-hidden">
        {activeTab === "lobby" && (
          <>
            {room ? (
              <RoomLobby />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-primary/20 to-indigo-500/20 border border-primary/30 flex items-center justify-center mb-6 shadow-2xl glow-primary">
                  <Gamepad2 className="w-10 h-10 text-primary" />
                </div>
                <h2 className="text-2xl font-extrabold text-white tracking-wide">
                  Готовы играть с друзьями?
                </h2>
                <p className="text-sm text-gray-400 mt-2 leading-relaxed">
                  Создайте новую игровую комнату и отправьте 6-значный код друзьям, либо
                  введите код уже существующей комнаты для мгновенного P2P соединения.
                </p>

                <div className="grid grid-cols-2 gap-4 w-full mt-8">
                  <button
                    onClick={() => handleOpenCreate()}
                    className="py-3.5 px-4 rounded-2xl bg-primary hover:bg-primary-hover text-white font-bold text-sm flex items-center justify-center gap-2 transition shadow-xl glow-primary"
                  >
                    <PlusCircle className="w-5 h-5" />
                    Создать комнату
                  </button>
                  <button
                    onClick={handleOpenJoin}
                    className="py-3.5 px-4 rounded-2xl bg-surface hover:bg-surface-hover border border-border hover:border-primary text-gray-200 font-bold text-sm flex items-center justify-center gap-2 transition shadow-md"
                  >
                    <LogIn className="w-5 h-5" />
                    Ввести код
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === "presets" && <GamePresets onHostGame={handleOpenCreate} />}
        {activeTab === "lan_discovery" && <LanDiscoveryView />}
        {activeTab === "diagnostics" && <NetworkStats />}
      </main>

      {/* Modals & Overlays */}
      <CreateJoinModal
        isOpen={isCreateJoinOpen}
        onClose={() => setIsCreateJoinOpen(false)}
        initialMode={createJoinMode}
        preselectedGame={preselectedGame}
      />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
      <ToastContainer />
    </div>
  );
};
