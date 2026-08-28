import { WebSocket } from "ws";
import { PeerState, RoomState, ChatMessage, ServerMessage } from "./types.js";
import { randomBytes } from "crypto";

export interface ConnectedPeer {
  id: string;
  ws: WebSocket;
  state: PeerState;
  roomCode?: string;
  lastSeen: number;
}

export class Room {
  public readonly code: string;
  public name: string;
  public gamePreset?: string;
  public hostId: string;
  public password?: string;
  public createdAt: number;
  public maxPeers: number;

  private assignedIps = new Set<number>();
  public peers = new Map<string, ConnectedPeer>();

  constructor(options: {
    code: string;
    name: string;
    hostId: string;
    gamePreset?: string;
    password?: string;
    maxPeers?: number;
  }) {
    this.code = options.code;
    this.name = options.name;
    this.hostId = options.hostId;
    this.gamePreset = options.gamePreset;
    this.password = options.password;
    this.createdAt = Date.now();
    this.maxPeers = options.maxPeers ?? 16;
  }

  public allocateVirtualIp(isHost: boolean): string {
    if (isHost) {
      this.assignedIps.add(1);
      return "10.42.0.1";
    }

    for (let i = 2; i <= 254; i++) {
      if (!this.assignedIps.has(i)) {
        this.assignedIps.add(i);
        return `10.42.0.${i}`;
      }
    }
    throw new Error("No virtual IP addresses available in room subnet");
  }

  public releaseVirtualIp(ip: string): void {
    const parts = ip.split(".");
    if (parts.length === 4) {
      const lastOctet = parseInt(parts[3], 10);
      if (!isNaN(lastOctet)) {
        this.assignedIps.delete(lastOctet);
      }
    }
  }

  public toState(): RoomState {
    return {
      code: this.code,
      name: this.name,
      gamePreset: this.gamePreset,
      hostId: this.hostId,
      hasPassword: Boolean(this.password),
      peers: Array.from(this.peers.values()).map((p) => p.state),
      createdAt: this.createdAt,
      maxPeers: this.maxPeers,
    };
  }

  public broadcast(message: ServerMessage, excludePeerId?: string): void {
    const payload = JSON.stringify(message);
    for (const [id, peer] of this.peers.entries()) {
      if (id !== excludePeerId && peer.ws.readyState === WebSocket.OPEN) {
        peer.ws.send(payload);
      }
    }
  }

  public sendTo(targetPeerId: string, message: ServerMessage): boolean {
    const target = this.peers.get(targetPeerId);
    if (target && target.ws.readyState === WebSocket.OPEN) {
      target.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }
}

export class RoomManager {
  private rooms = new Map<string, Room>();
  private peers = new Map<string, ConnectedPeer>();

  public generatePeerId(): string {
    return "peer_" + randomBytes(6).toString("hex");
  }

  public generateRoomCode(): string {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    let code: string;
    let attempts = 0;
    do {
      let part1 = "";
      let part2 = "";
      for (let i = 0; i < 3; i++) {
        part1 += chars.charAt(Math.floor(Math.random() * chars.length));
        part2 += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      code = `${part1}-${part2}`;
      attempts++;
      if (attempts > 100) break;
    } while (this.rooms.has(code));
    return code;
  }

  public registerPeer(ws: WebSocket): ConnectedPeer {
    const peerId = this.generatePeerId();
    const peer: ConnectedPeer = {
      id: peerId,
      ws,
      state: {
        id: peerId,
        nick: "Player",
        virtualIp: "",
        isHost: false,
        isReady: false,
        joinedAt: Date.now(),
      },
      lastSeen: Date.now(),
    };
    this.peers.set(peerId, peer);
    return peer;
  }

  public getPeer(peerId: string): ConnectedPeer | undefined {
    return this.peers.get(peerId);
  }

  public unregisterPeer(peerId: string): void {
    const peer = this.peers.get(peerId);
    if (peer) {
      if (peer.roomCode) {
        this.leaveRoom(peer);
      }
      this.peers.delete(peerId);
    }
  }

  public createRoom(
    peer: ConnectedPeer,
    options: {
      name: string;
      hostNick: string;
      gamePreset?: string;
      password?: string;
      maxPeers?: number;
    }
  ): { room: RoomState; peerState: PeerState } {
    if (peer.roomCode) {
      this.leaveRoom(peer);
    }

    const code = this.generateRoomCode();
    const room = new Room({
      code,
      name: options.name || `${options.hostNick}'s LAN Party`,
      hostId: peer.id,
      gamePreset: options.gamePreset,
      password: options.password,
      maxPeers: options.maxPeers || 16,
    });

    peer.state.nick = options.hostNick || "Host";
    peer.state.isHost = true;
    peer.state.virtualIp = room.allocateVirtualIp(true);
    peer.state.currentGame = options.gamePreset;
    peer.roomCode = code;

    room.peers.set(peer.id, peer);
    this.rooms.set(code, room);

    return {
      room: room.toState(),
      peerState: peer.state,
    };
  }

  public joinRoom(
    peer: ConnectedPeer,
    code: string,
    options: { nick: string; password?: string }
  ): { room: RoomState; peerState: PeerState } {
    if (peer.roomCode) {
      this.leaveRoom(peer);
    }

    const normalizedCode = code.trim().toUpperCase();
    const room = this.rooms.get(normalizedCode);
    if (!room) {
      throw new Error(`Комната "${normalizedCode}" не найдена`);
    }

    if (room.peers.size >= room.maxPeers) {
      throw new Error("Комната заполнена");
    }

    if (room.password && room.password !== options.password) {
      throw new Error("Неверный пароль комнаты");
    }

    peer.state.nick = options.nick || `Player_${peer.id.slice(5, 9)}`;
    peer.state.isHost = false;
    peer.state.virtualIp = room.allocateVirtualIp(false);
    peer.roomCode = normalizedCode;

    room.peers.set(peer.id, peer);

    // Notify other peers in room
    room.broadcast({ type: "peer_joined", peer: peer.state }, peer.id);

    return {
      room: room.toState(),
      peerState: peer.state,
    };
  }

  public leaveRoom(peer: ConnectedPeer): void {
    if (!peer.roomCode) return;

    const room = this.rooms.get(peer.roomCode);
    if (!room) {
      peer.roomCode = undefined;
      return;
    }

    room.peers.delete(peer.id);
    room.releaseVirtualIp(peer.state.virtualIp);
    const wasHost = peer.state.isHost;

    peer.roomCode = undefined;
    peer.state.virtualIp = "";
    peer.state.isHost = false;

    if (room.peers.size === 0) {
      // Clean up empty room
      this.rooms.delete(room.code);
    } else {
      // Notify remaining peers
      room.broadcast({ type: "peer_left", peerId: peer.id, reason: "left" });

      // Transfer host if host left
      if (wasHost) {
        const nextHost = room.peers.values().next().value;
        if (nextHost) {
          nextHost.state.isHost = true;
          room.hostId = nextHost.id;
          room.broadcast({ type: "host_transferred", newHostId: nextHost.id });
          room.broadcast({ type: "peer_updated", peer: nextHost.state });
        }
      }
    }
  }

  public kickPeer(hostPeer: ConnectedPeer, targetPeerId: string): void {
    if (!hostPeer.roomCode) {
      throw new Error("Вы не находитесь в комнате");
    }
    const room = this.rooms.get(hostPeer.roomCode);
    if (!room || room.hostId !== hostPeer.id) {
      throw new Error("Только создатель комнаты может исключать участников");
    }

    const targetPeer = room.peers.get(targetPeerId);
    if (!targetPeer) {
      throw new Error("Участник не найден в комнате");
    }

    targetPeer.ws.send(JSON.stringify({ type: "kicked", reason: "Исключен создателем комнаты" }));
    this.leaveRoom(targetPeer);
  }

  public getRoom(code: string): Room | undefined {
    return this.rooms.get(code.trim().toUpperCase());
  }

  public getRoomCount(): number {
    return this.rooms.size;
  }

  public getPeerCount(): number {
    return this.peers.size;
  }
}
