import { createServer, IncomingMessage, ServerResponse } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { RoomManager, ConnectedPeer } from "./rooms.js";
import { ClientMessage, ServerMessage, ChatMessage } from "./types.js";
import { randomBytes } from "crypto";

export function createLanForgeServer(port = 8787) {
  const roomManager = new RoomManager();

  const httpServer = createServer((req: IncomingMessage, res: ServerResponse) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
      res.writeHead(200);
      res.end();
      return;
    }

    if (req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", timestamp: Date.now() }));
      return;
    }

    if (req.url === "/stats") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          activeRooms: roomManager.getRoomCount(),
          connectedPeers: roomManager.getPeerCount(),
          uptimeSec: Math.floor(process.uptime()),
        })
      );
      return;
    }

    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("LANForge Signaling & Relay Server");
  });

  const wss = new WebSocketServer({ server: httpServer });

  wss.on("connection", (ws: WebSocket) => {
    const peer = roomManager.registerPeer(ws);

    ws.on("message", (raw: Buffer | string) => {
      try {
        const msg = JSON.parse(raw.toString()) as ClientMessage;
        handleClientMessage(peer, msg, roomManager);
      } catch (err: any) {
        sendError(ws, "BAD_REQUEST", err.message || "Invalid JSON payload");
      }
    });

    ws.on("close", () => {
      roomManager.unregisterPeer(peer.id);
    });

    ws.on("error", () => {
      roomManager.unregisterPeer(peer.id);
    });
  });

  return {
    httpServer,
    wss,
    roomManager,
    start: () =>
      new Promise<void>((resolve) => {
        httpServer.listen(port, () => {
          console.log(`[LANForge Server] Listening on http://localhost:${port}`);
          resolve();
        });
      }),
    stop: () =>
      new Promise<void>((resolve) => {
        wss.close(() => {
          httpServer.close(() => resolve());
        });
      }),
  };
}

function handleClientMessage(
  peer: ConnectedPeer,
  msg: ClientMessage,
  roomManager: RoomManager
): void {
  peer.lastSeen = Date.now();

  switch (msg.type) {
    case "create_room": {
      try {
        const { room, peerState } = roomManager.createRoom(peer, {
          name: msg.name,
          hostNick: msg.hostNick,
          gamePreset: msg.gamePreset,
          password: msg.password,
          maxPeers: msg.maxPeers,
        });
        sendJson(peer.ws, {
          type: "room_created",
          room,
          you: peerState,
        });
      } catch (err: any) {
        sendError(peer.ws, "CREATE_ROOM_FAILED", err.message);
      }
      break;
    }

    case "join_room": {
      try {
        const { room, peerState } = roomManager.joinRoom(peer, msg.code, {
          nick: msg.nick,
          password: msg.password,
        });
        sendJson(peer.ws, {
          type: "room_joined",
          room,
          you: peerState,
        });
      } catch (err: any) {
        sendError(peer.ws, "JOIN_ROOM_FAILED", err.message);
      }
      break;
    }

    case "leave_room": {
      roomManager.leaveRoom(peer);
      break;
    }

    case "signal": {
      if (!peer.roomCode) {
        return sendError(peer.ws, "NOT_IN_ROOM", "You must join a room first");
      }
      const room = roomManager.getRoom(peer.roomCode);
      if (!room) return;

      const target = room.peers.get(msg.targetPeerId);
      if (target && target.ws.readyState === WebSocket.OPEN) {
        sendJson(target.ws, {
          type: "signal_forward",
          fromPeerId: peer.id,
          signalType: msg.signalType,
          data: msg.data,
        });
      }
      break;
    }

    case "chat_message": {
      if (!peer.roomCode) return;
      const room = roomManager.getRoom(peer.roomCode);
      if (!room) return;

      const chatMsg: ChatMessage = {
        id: "msg_" + randomBytes(4).toString("hex"),
        fromPeerId: peer.id,
        fromNick: peer.state.nick,
        text: msg.text.slice(0, 1000),
        timestamp: Date.now(),
      };

      room.broadcast({ type: "chat_broadcast", message: chatMsg });
      break;
    }

    case "relay_packet": {
      if (!peer.roomCode) return;
      const room = roomManager.getRoom(peer.roomCode);
      if (!room) return;

      const target = room.peers.get(msg.targetPeerId);
      if (target && target.ws.readyState === WebSocket.OPEN) {
        sendJson(target.ws, {
          type: "relay_packet_forward",
          fromPeerId: peer.id,
          data: msg.data,
        });
      }
      break;
    }

    case "update_status": {
      if (!peer.roomCode) return;
      const room = roomManager.getRoom(peer.roomCode);
      if (!room) return;

      if (msg.currentGame !== undefined) peer.state.currentGame = msg.currentGame;
      if (msg.isReady !== undefined) peer.state.isReady = msg.isReady;
      if (msg.pingMs !== undefined) peer.state.pingMs = msg.pingMs;

      room.broadcast({ type: "peer_updated", peer: peer.state });
      break;
    }

    case "kick_peer": {
      try {
        roomManager.kickPeer(peer, msg.targetPeerId);
      } catch (err: any) {
        sendError(peer.ws, "KICK_FAILED", err.message);
      }
      break;
    }

    case "ping": {
      sendJson(peer.ws, {
        type: "pong",
        clientTimestamp: msg.timestamp,
        serverTimestamp: Date.now(),
      });
      break;
    }
  }
}

function sendJson(ws: WebSocket, payload: ServerMessage): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}

function sendError(ws: WebSocket, code: string, message: string): void {
  sendJson(ws, { type: "error", code, message });
}
