type EventCallback<T = any> = (data: T) => void;

export class SignalingClient {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners = new Map<string, Set<EventCallback>>();
  private pingInterval: any = null;
  public isConnected = false;

  constructor(url = "ws://localhost:8787") {
    this.url = url;
  }

  public setUrl(newUrl: string) {
    if (this.url !== newUrl) {
      this.url = newUrl;
      if (this.isConnected) {
        this.disconnect();
        this.connect();
      }
    }
  }

  public connect(): Promise<void> {
    return new Promise((resolve) => {
      if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
        return resolve();
      }

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.isConnected = true;
          this.emit("connection_status", { status: "connected" });
          this.startPingLoop();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
          } catch (err) {
            console.error("[Signaling] Parse error:", err);
          }
        };

        this.ws.onclose = () => {
          this.isConnected = false;
          this.emit("connection_status", { status: "disconnected" });
          this.stopPingLoop();
        };

        this.ws.onerror = () => {
          this.emit("connection_status", { status: "error" });
        };
      } catch {
        this.emit("connection_status", { status: "error" });
        resolve();
      }
    });
  }

  public disconnect() {
    this.stopPingLoop();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  public on(event: string, callback: EventCallback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  private emit(event: string, data: any) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      for (const cb of handlers) {
        cb(data);
      }
    }
  }

  private send(payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  public createRoom(options: {
    name: string;
    hostNick: string;
    gamePreset?: string;
    password?: string;
    maxPeers?: number;
  }) {
    this.send({
      type: "create_room",
      name: options.name,
      hostNick: options.hostNick,
      gamePreset: options.gamePreset,
      password: options.password,
      maxPeers: options.maxPeers,
    });
  }

  public joinRoom(options: { code: string; nick: string; password?: string }) {
    this.send({
      type: "join_room",
      code: options.code,
      nick: options.nick,
      password: options.password,
    });
  }

  public leaveRoom() {
    this.send({ type: "leave_room" });
  }

  public sendChatMessage(text: string) {
    this.send({ type: "chat_message", text });
  }

  public updateStatus(status: { currentGame?: string; isReady?: boolean; pingMs?: number }) {
    this.send({ type: "update_status", ...status });
  }

  public kickPeer(targetPeerId: string) {
    this.send({ type: "kick_peer", targetPeerId });
  }

  private startPingLoop() {
    this.stopPingLoop();
    this.pingInterval = setInterval(() => {
      this.send({ type: "ping", timestamp: Date.now() });
    }, 4000);
  }

  private stopPingLoop() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private handleServerMessage(msg: any) {
    switch (msg.type) {
      case "room_created":
      case "room_joined":
        this.emit("room_state", { room: msg.room, you: msg.you });
        break;
      case "peer_joined":
        this.emit("peer_joined", msg.peer);
        break;
      case "peer_left":
        this.emit("peer_left", { peerId: msg.peerId, reason: msg.reason });
        break;
      case "peer_updated":
        this.emit("peer_updated", msg.peer);
        break;
      case "host_transferred":
        this.emit("host_transferred", msg.newHostId);
        break;
      case "chat_broadcast":
        this.emit("chat_message", msg.message);
        break;
      case "kicked":
        this.emit("kicked", msg.reason);
        break;
      case "error":
        this.emit("error", { code: msg.code, message: msg.message });
        break;
      case "pong": {
        const rtt = Date.now() - msg.clientTimestamp;
        this.emit("pong", { rtt });
        // Report RTT back to room so peers see live ping
        this.updateStatus({ pingMs: rtt });
        break;
      }
    }
  }
}

export const signalingClient = new SignalingClient();
