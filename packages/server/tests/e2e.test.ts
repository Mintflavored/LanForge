import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { createLanForgeServer } from "../src/server.js";
import { WebSocket } from "ws";

describe("LANForge End-to-End WebSocket Flow", () => {
  const TEST_PORT = 9876;
  const server = createLanForgeServer(TEST_PORT);

  beforeAll(async () => {
    await server.start();
  });

  afterAll(async () => {
    await server.stop();
  });

  it("performs full room creation, joining, virtual IP allocation, chat, and leaving", async () => {
    const wsHost = new WebSocket(`ws://localhost:${TEST_PORT}`);
    const wsClient = new WebSocket(`ws://localhost:${TEST_PORT}`);

    await Promise.all([
      new Promise<void>((resolve) => wsHost.on("open", resolve)),
      new Promise<void>((resolve) => wsClient.on("open", resolve)),
    ]);

    let roomCode = "";

    // 1. Host creates room
    const hostCreatedPromise = new Promise<any>((resolve) => {
      wsHost.on("message", (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "room_created") {
          resolve(msg);
        }
      });
    });

    wsHost.send(
      JSON.stringify({
        type: "create_room",
        name: "Test LAN Room",
        hostNick: "SuperHost",
        gamePreset: "minecraft_java",
      })
    );

    const hostCreated = await hostCreatedPromise;
    expect(hostCreated.room.code).toBeDefined();
    expect(hostCreated.you.virtualIp).toBe("10.42.0.1");
    expect(hostCreated.you.isHost).toBe(true);
    roomCode = hostCreated.room.code;

    // 2. Client joins room
    const clientJoinedPromise = new Promise<any>((resolve) => {
      wsClient.on("message", (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "room_joined") {
          resolve(msg);
        }
      });
    });

    wsClient.send(
      JSON.stringify({
        type: "join_room",
        code: roomCode,
        nick: "GamerFriend",
      })
    );

    const clientJoined = await clientJoinedPromise;
    expect(clientJoined.room.code).toBe(roomCode);
    expect(clientJoined.you.virtualIp).toBe("10.42.0.2");
    expect(clientJoined.you.isHost).toBe(false);

    // 3. Test Room Chat
    const chatPromise = new Promise<any>((resolve) => {
      wsClient.on("message", (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "chat_broadcast") {
          resolve(msg.message);
        }
      });
    });

    wsHost.send(
      JSON.stringify({
        type: "chat_message",
        text: "Заходи на сервер 10.42.0.1:25565!",
      })
    );

    const chatMsg = await chatPromise;
    expect(chatMsg.text).toBe("Заходи на сервер 10.42.0.1:25565!");
    expect(chatMsg.fromNick).toBe("SuperHost");

    // Cleanup
    wsHost.close();
    wsClient.close();
  });
});
