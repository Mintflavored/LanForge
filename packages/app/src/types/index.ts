export interface PeerState {
  id: string;
  nick: string;
  virtualIp: string;
  isHost: boolean;
  isReady: boolean;
  currentGame?: string;
  pingMs?: number;
  joinedAt: number;
}

export interface RoomState {
  code: string;
  name: string;
  gamePreset?: string;
  hostId: string;
  hasPassword: boolean;
  peers: PeerState[];
  createdAt: number;
  maxPeers: number;
}

export interface ChatMessage {
  id: string;
  fromPeerId: string;
  fromNick: string;
  text: string;
  timestamp: number;
}

export interface NatDiagnostics {
  publicIp?: string;
  publicPort?: number;
  natType: "FullCone" | "RestrictedCone" | "PortRestricted" | "Symmetric" | "Unknown" | "Testing";
  upnpStatus: "Enabled" | "Disabled" | "NotFound" | "Testing";
  activeTunnels: number;
  bytesReceived: number;
  bytesSent: number;
}

export interface DiscoveredLanGame {
  id: string;
  gameName: string;
  hostNick: string;
  hostIp: string;
  port: number;
  detectedAt: number;
  motd?: string;
}

export interface AppSettings {
  nick: string;
  serverUrl: string;
  networkMode: "wintun" | "zero_driver";
  autoUpnp: boolean;
  broadcastRelay: boolean;
  virtualSubnet: string;
}
