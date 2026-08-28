import { create } from "zustand";
import { RoomState, PeerState, ChatMessage, NatDiagnostics, DiscoveredLanGame, AppSettings } from "../types/index.js";
import { signalingClient } from "../services/signalingClient.js";
import { nativeBridge } from "../services/nativeBridge.js";

interface Toast {
  id: string;
  type: "info" | "success" | "error" | "warning";
  message: string;
}

interface AppStore {
  // Connection & Room
  isConnected: boolean;
  room: RoomState | null;
  you: PeerState | null;
  chatMessages: ChatMessage[];
  unreadChatCount: number;

  // Active View Tab
  activeTab: "lobby" | "presets" | "lan_discovery" | "diagnostics";
  setActiveTab: (tab: "lobby" | "presets" | "lan_discovery" | "diagnostics") => void;

  // LAN Discovery & Diagnostics
  discoveredGames: DiscoveredLanGame[];
  natDiagnostics: NatDiagnostics;
  isTestingNat: boolean;

  // Settings
  settings: AppSettings;
  updateSettings: (partial: Partial<AppSettings>) => void;

  // Toasts
  toasts: Toast[];
  addToast: (message: string, type?: Toast["type"]) => void;
  removeToast: (id: string) => void;

  // Actions
  init: () => void;
  createRoom: (name: string, gamePreset?: string, password?: string) => void;
  joinRoom: (code: string, password?: string) => void;
  leaveRoom: () => void;
  sendChat: (text: string) => void;
  kickPeer: (peerId: string) => void;
  testNatAndUpnp: () => Promise<void>;
  addDiscoveredGame: (game: DiscoveredLanGame) => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  isConnected: false,
  room: null,
  you: null,
  chatMessages: [],
  unreadChatCount: 0,
  activeTab: "lobby",

  discoveredGames: [],
  natDiagnostics: {
    natType: "Testing",
    upnpStatus: "Testing",
    activeTunnels: 0,
    bytesReceived: 0,
    bytesSent: 0,
  },
  isTestingNat: false,

  settings: {
    nick: "Player_" + Math.floor(1000 + Math.random() * 9000),
    serverUrl: "ws://localhost:8787",
    networkMode: "wintun",
    autoUpnp: true,
    broadcastRelay: true,
    virtualSubnet: "10.42.0.0/24",
  },

  toasts: [],

  setActiveTab: (tab) => {
    set({ activeTab: tab });
    if (tab === "lobby") {
      set({ unreadChatCount: 0 });
    }
  },

  updateSettings: (partial) => {
    set((state) => {
      const next = { ...state.settings, ...partial };
      if (partial.serverUrl) {
        signalingClient.setUrl(partial.serverUrl);
      }
      return { settings: next };
    });
  },

  addToast: (message, type = "info") => {
    const id = "toast_" + Math.random().toString(36).substring(2, 9);
    set((state) => ({ toasts: [...state.toasts, { id, type, message }] }));
    setTimeout(() => {
      get().removeToast(id);
    }, 4000);
  },

  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  init: () => {
    const { settings } = get();
    signalingClient.setUrl(settings.serverUrl);

    signalingClient.on("connection_status", ({ status }) => {
      set({ isConnected: status === "connected" });
    });

    signalingClient.on("room_state", ({ room, you }) => {
      set({ room, you, chatMessages: [] });
      get().addToast(`Вы вошли в комнату "${room.name}" [${room.code}]`, "success");
    });

    signalingClient.on("peer_joined", (peer: PeerState) => {
      set((state) => {
        if (!state.room) return state;
        const exists = state.room.peers.some((p) => p.id === peer.id);
        const peers = exists
          ? state.room.peers.map((p) => (p.id === peer.id ? peer : p))
          : [...state.room.peers, peer];
        return { room: { ...state.room, peers } };
      });
      get().addToast(`${peer.nick} присоединился к комнате`, "info");
    });

    signalingClient.on("peer_left", ({ peerId }) => {
      set((state) => {
        if (!state.room) return state;
        return {
          room: {
            ...state.room,
            peers: state.room.peers.filter((p) => p.id !== peerId),
          },
        };
      });
      get().addToast(`Игрок покинул комнату`, "warning");
    });

    signalingClient.on("peer_updated", (peer: PeerState) => {
      set((state) => {
        if (!state.room) return state;
        const peers = state.room.peers.map((p) => (p.id === peer.id ? peer : p));
        const you = state.you?.id === peer.id ? peer : state.you;
        return { room: { ...state.room, peers }, you };
      });
    });

    signalingClient.on("host_transferred", (newHostId: string) => {
      set((state) => {
        if (!state.room) return state;
        return { room: { ...state.room, hostId: newHostId } };
      });
      get().addToast("Права хоста были переданы новому игроку", "info");
    });

    signalingClient.on("chat_message", (message: ChatMessage) => {
      set((state) => ({
        chatMessages: [...state.chatMessages, message],
        unreadChatCount: state.activeTab !== "lobby" ? state.unreadChatCount + 1 : 0,
      }));
    });

    signalingClient.on("kicked", (reason?: string) => {
      set({ room: null, you: null, chatMessages: [] });
      get().addToast(reason || "Вы были исключены из комнаты", "error");
    });

    signalingClient.on("error", ({ message }) => {
      get().addToast(message, "error");
    });

    // Start WebSocket connection
    signalingClient.connect();

    // Start LAN Broadcast listener
    nativeBridge.startLanBroadcast((game) => {
      get().addDiscoveredGame(game);
    });

    // Initial NAT check
    get().testNatAndUpnp();
  },

  createRoom: (name, gamePreset, password) => {
    const { settings } = get();
    signalingClient.createRoom({
      name,
      hostNick: settings.nick,
      gamePreset,
      password: password || undefined,
    });
  },

  joinRoom: (code, password) => {
    const { settings } = get();
    signalingClient.joinRoom({
      code,
      nick: settings.nick,
      password: password || undefined,
    });
  },

  leaveRoom: () => {
    signalingClient.leaveRoom();
    set({ room: null, you: null, chatMessages: [] });
    get().addToast("Вы вышли из комнаты", "info");
  },

  sendChat: (text) => {
    if (!text.trim()) return;
    signalingClient.sendChatMessage(text);
  },

  kickPeer: (peerId) => {
    signalingClient.kickPeer(peerId);
  },

  testNatAndUpnp: async () => {
    set({ isTestingNat: true });
    try {
      const diag = await nativeBridge.detectNat();
      set({ natDiagnostics: diag, isTestingNat: false });
    } catch {
      set({ isTestingNat: false });
    }
  },

  addDiscoveredGame: (game) => {
    set((state) => {
      const filtered = state.discoveredGames.filter((g) => g.id !== game.id);
      return { discoveredGames: [game, ...filtered].slice(0, 10) };
    });
    get().addToast(`Найдена LAN игра: ${game.gameName} (${game.hostNick})`, "success");
  },
}));
