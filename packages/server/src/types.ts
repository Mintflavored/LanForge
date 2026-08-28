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

// Client -> Server Events
export type ClientMessage =
  | { type: 'create_room'; name: string; gamePreset?: string; password?: string; hostNick: string; maxPeers?: number }
  | { type: 'join_room'; code: string; password?: string; nick: string }
  | { type: 'leave_room' }
  | { type: 'signal'; targetPeerId: string; signalType: 'offer' | 'answer' | 'candidate'; data: unknown }
  | { type: 'chat_message'; text: string }
  | { type: 'relay_packet'; targetPeerId: string; data: string }
  | { type: 'update_status'; currentGame?: string; isReady?: boolean; pingMs?: number }
  | { type: 'kick_peer'; targetPeerId: string }
  | { type: 'ping'; timestamp: number };

// Server -> Client Events
export type ServerMessage =
  | { type: 'room_created'; room: RoomState; you: PeerState }
  | { type: 'room_joined'; room: RoomState; you: PeerState }
  | { type: 'peer_joined'; peer: PeerState }
  | { type: 'peer_left'; peerId: string; reason?: string }
  | { type: 'peer_updated'; peer: PeerState }
  | { type: 'host_transferred'; newHostId: string }
  | { type: 'signal_forward'; fromPeerId: string; signalType: 'offer' | 'answer' | 'candidate'; data: unknown }
  | { type: 'chat_broadcast'; message: ChatMessage }
  | { type: 'relay_packet_forward'; fromPeerId: string; data: string }
  | { type: 'kicked'; reason?: string }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong'; clientTimestamp: number; serverTimestamp: number };
