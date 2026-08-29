"""
Threaded WebSocket Network Client with Reconnection and Event Bus
"""

import asyncio
import json
import socket
import threading
import time
import websockets

try:
    from gui.events import NetworkEvents
except ImportError:
    from events import NetworkEvents

class NetworkClient:
    def __init__(self, server_url="ws://localhost:8787", nick="Player"):
        self.server_url = server_url
        self.nick = nick
        self.ws = None
        self.loop = None
        self.connected = False
        self.room = None
        self.you = None
        self.chat_history = []
        self.discovered_games = []
        self.last_ping_rtt = 0
        self.callbacks = {}
        self.running = True

        # Dedicated background async event loop
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

        # Dedicated UDP LAN broadcast sniffer
        self.discovery_thread = threading.Thread(target=self._listen_broadcast, daemon=True)
        self.discovery_thread.start()

    def on(self, event_name, callback):
        self.callbacks[event_name] = callback

    def _emit(self, event_name, data):
        if event_name in self.callbacks:
            try:
                self.callbacks[event_name](data)
            except Exception:
                pass

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        while self.running:
            try:
                async with websockets.connect(self.server_url, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    self.connected = True
                    self._emit(NetworkEvents.CONNECTION, True)

                    ping_task = asyncio.create_task(self._ping_loop())
                    try:
                        async for message in ws:
                            data = json.loads(message)
                            self._handle_server_message(data)
                    finally:
                        ping_task.cancel()
            except Exception:
                self.connected = False
                self.ws = None
                self._emit(NetworkEvents.CONNECTION, False)
                await asyncio.sleep(2)

    def _handle_server_message(self, msg):
        msg_type = msg.get("type")
        if msg_type in ("room_created", "room_joined"):
            self.room = msg.get("room")
            self.you = msg.get("you")
            self.chat_history.clear()
            self._emit(NetworkEvents.ROOM_STATE, self.room)
        elif msg_type == "peer_joined":
            if self.room and msg.get("peer"):
                peer = msg["peer"]
                peers = [p for p in self.room["peers"] if p["id"] != peer["id"]]
                peers.append(peer)
                self.room["peers"] = peers
                self._emit(NetworkEvents.ROOM_STATE, self.room)
        elif msg_type == "peer_left":
            if self.room:
                peer_id = msg.get("peerId")
                self.room["peers"] = [p for p in self.room["peers"] if p["id"] != peer_id]
                self._emit(NetworkEvents.ROOM_STATE, self.room)
        elif msg_type == "peer_updated":
            if self.room and msg.get("peer"):
                peer = msg["peer"]
                self.room["peers"] = [p if p["id"] != peer["id"] else peer for p in self.room["peers"]]
                if self.you and self.you["id"] == peer["id"]:
                    self.you = peer
                self._emit(NetworkEvents.ROOM_STATE, self.room)
        elif msg_type == "chat_broadcast":
            if msg.get("message"):
                self.chat_history.append(msg["message"])
                self._emit(NetworkEvents.CHAT_MESSAGE, msg["message"])
        elif msg_type == "pong":
            client_ts = msg.get("clientTimestamp", 0)
            self.last_ping_rtt = int((time.time() * 1000) - client_ts)
            self._emit(NetworkEvents.PING, self.last_ping_rtt)
        elif msg_type == "error":
            self._emit(NetworkEvents.ERROR, msg.get("errorMessage", "Error"))

    async def _ping_loop(self):
        while self.connected and self.ws:
            try:
                payload = json.dumps({"type": "ping", "timestamp": int(time.time() * 1000)})
                await self.ws.send(payload)
            except Exception:
                break
            await asyncio.sleep(4)

    def send_json(self, payload):
        if self.loop and self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(payload)), self.loop)

    def create_room(self, name, preset_id="minecraft_java", password=""):
        self.send_json({
            "type": "create_room",
            "name": name,
            "gamePreset": preset_id,
            "password": password,
            "hostNick": self.nick,
        })

    def join_room(self, code, password=""):
        self.send_json({
            "type": "join_room",
            "code": code.strip().upper(),
            "nick": self.nick,
            "password": password,
        })

    def leave_room(self):
        self.send_json({"type": "leave_room"})
        self.room = None
        self.you = None
        self._emit(NetworkEvents.ROOM_STATE, None)

    def send_chat(self, text):
        if text.strip():
            self.send_json({"type": "chat_message", "text": text.strip()})

    def _listen_broadcast(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("0.0.0.0", 4445))
            sock.settimeout(0.5)

            while self.running:
                try:
                    data, addr = sock.recvfrom(2048)
                    text = data.decode("utf-8", errors="ignore")
                    if "[MOTD]" in text and "[/MOTD]" in text:
                        motd = text.split("[MOTD]")[1].split("[/MOTD]")[0]
                        port = 25565
                        if "[AD]" in text and "[/AD]" in text:
                            try:
                                port = int(text.split("[AD]")[1].split("[/AD]")[0])
                            except Exception:
                                pass

                        game = {
                            "id": f"mc_{port}",
                            "name": "Minecraft LAN World",
                            "host_nick": "Local Host",
                            "host_ip": addr[0],
                            "port": port,
                            "motd": motd,
                        }
                        if not any(g["id"] == game["id"] for g in self.discovered_games):
                            self.discovered_games.insert(0, game)
                            self._emit(NetworkEvents.DISCOVERED_GAME, game)
                except socket.timeout:
                    continue
                except Exception:
                    time.sleep(1)
        except Exception:
            pass
