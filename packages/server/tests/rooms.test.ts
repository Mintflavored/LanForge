import { describe, it, expect, beforeEach } from "vitest";
import { RoomManager, ConnectedPeer } from "../src/rooms.js";
import { WebSocket } from "ws";

describe("RoomManager and Virtual IP Allocation", () => {
  let manager: RoomManager;

  const mockWs = {
    readyState: WebSocket.OPEN,
    send: () => {},
  } as unknown as WebSocket;

  beforeEach(() => {
    manager = new RoomManager();
  });

  it("registers peers and generates unique IDs", () => {
    const peer1 = manager.registerPeer(mockWs);
    const peer2 = manager.registerPeer(mockWs);
    expect(peer1.id).toBeDefined();
    expect(peer2.id).toBeDefined();
    expect(peer1.id).not.toBe(peer2.id);
  });

  it("creates a room, assigns host IP (10.42.0.1) and code", () => {
    const host = manager.registerPeer(mockWs);
    const { room, peerState } = manager.createRoom(host, {
      name: "Minecraft Night",
      hostNick: "Alex",
      gamePreset: "minecraft",
    });

    expect(room.code).toBeDefined();
    expect(room.name).toBe("Minecraft Night");
    expect(room.hostId).toBe(host.id);
    expect(peerState.virtualIp).toBe("10.42.0.1");
    expect(peerState.isHost).toBe(true);
  });

  it("allows peer to join room with consecutive virtual IP (10.42.0.2)", () => {
    const host = manager.registerPeer(mockWs);
    const { room } = manager.createRoom(host, {
      name: "LAN Party",
      hostNick: "Alex",
    });

    const client1 = manager.registerPeer(mockWs);
    const { peerState: clientState1 } = manager.joinRoom(client1, room.code, {
      nick: "Dmitry",
    });

    expect(clientState1.virtualIp).toBe("10.42.0.2");
    expect(clientState1.isHost).toBe(false);

    const client2 = manager.registerPeer(mockWs);
    const { peerState: clientState2 } = manager.joinRoom(client2, room.code, {
      nick: "Sergey",
    });

    expect(clientState2.virtualIp).toBe("10.42.0.3");
  });

  it("rejects joining with invalid password", () => {
    const host = manager.registerPeer(mockWs);
    const { room } = manager.createRoom(host, {
      name: "Secret LAN",
      hostNick: "Alex",
      password: "secret_password",
    });

    const client = manager.registerPeer(mockWs);
    expect(() => {
      manager.joinRoom(client, room.code, {
        nick: "Dmitry",
        password: "wrong_password",
      });
    }).toThrowError("Неверный пароль комнаты");
  });

  it("releases virtual IP when peer leaves and cleans empty room", () => {
    const host = manager.registerPeer(mockWs);
    const { room } = manager.createRoom(host, {
      name: "Test Room",
      hostNick: "Alex",
    });

    const client = manager.registerPeer(mockWs);
    manager.joinRoom(client, room.code, { nick: "Guest" });

    expect(manager.getRoom(room.code)?.peers.size).toBe(2);

    manager.leaveRoom(client);
    expect(manager.getRoom(room.code)?.peers.size).toBe(1);

    manager.leaveRoom(host);
    expect(manager.getRoom(room.code)).toBeUndefined();
  });
});
