"""
Discord Rich Presence (RPC) Client for LANForge.
Communicates directly with Discord desktop via Windows Named Pipe (\\.\\pipe\\discord-ipc-0).
Zero external dependencies, non-blocking background thread.
"""

import json
import os
import struct
import time
import uuid
import threading

DISCORD_CLIENT_ID = "1212891928472918273"

class DiscordRPC:
    def __init__(self, client_id=DISCORD_CLIENT_ID):
        self.client_id = client_id
        self.pipe = None
        self.connected = False
        self.start_time = int(time.time())
        self.last_activity = None
        self.lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _find_pipe(self):
        for i in range(10):
            pipe_path = rf"\\.\pipe\discord-ipc-{i}"
            try:
                # Open pipe with binary read/write
                pipe = open(pipe_path, "w+b", buffering=0)
                return pipe
            except Exception:
                continue
        return None

    def _send(self, opcode, payload):
        if not self.pipe:
            return False
        try:
            data = json.dumps(payload).encode("utf-8")
            header = struct.pack("<II", opcode, len(data))
            self.pipe.write(header + data)
            self.pipe.flush()
            return True
        except Exception:
            self.connected = False
            try:
                self.pipe.close()
            except Exception:
                pass
            self.pipe = None
            return False

    def _read_response(self):
        if not self.pipe:
            return None
        try:
            header = self.pipe.read(8)
            if len(header) < 8:
                return None
            opcode, length = struct.unpack("<II", header)
            data = self.pipe.read(length)
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def _connect(self):
        self.pipe = self._find_pipe()
        if not self.pipe:
            return False
        handshake = {"v": 1, "client_id": self.client_id}
        if self._send(0, handshake):
            resp = self._read_response()
            if resp and resp.get("cmd") == "DISPATCH" and resp.get("evt") == "READY":
                self.connected = True
                return True
        return False

    def set_activity(self, details="В главном меню", state="P2P Gaming Hub v1.5.0", party_size=None, party_max=16, room_code=None):
        with self.lock:
            activity = {
                "details": details,
                "state": state,
                "timestamps": {"start": self.start_time},
                "assets": {
                    "large_image": "lanforge_logo",
                    "large_text": "LANForge — P2P Virtual LAN"
                }
            }
            if party_size is not None and room_code:
                activity["party"] = {
                    "id": f"lanforge_{room_code}",
                    "size": [max(1, party_size), max(1, party_max)]
                }
            self.last_activity = activity
            if self.connected:
                payload = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": activity
                    },
                    "nonce": str(uuid.uuid4())
                }
                self._send(1, payload)

    def _worker_loop(self):
        while self._running:
            if not self.connected:
                if self._connect():
                    if self.last_activity:
                        self.set_activity()
            time.sleep(3.0)

    def close(self):
        self._running = False
        if self.pipe:
            try:
                self.pipe.close()
            except Exception:
                pass

# Global instance
discord = DiscordRPC()
