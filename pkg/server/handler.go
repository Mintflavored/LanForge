package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/lanforge/lanforge/pkg/protocol"
	"github.com/lanforge/lanforge/pkg/stun"
	"github.com/lanforge/lanforge/pkg/tunnel"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow LAN and web clients
	},
}

// Server encapsulates the HTTP and WebSocket signaling listener.
type Server struct {
	Manager      *RoomManager
	Port         int
	activeTunnel *tunnel.TunnelEngine
	tunnelMu     sync.Mutex
}

// NewServer creates a new signaling server.
func NewServer(port int) *Server {
	return &Server{
		Manager: NewRoomManager(),
		Port:    port,
	}
}

// Handler returns the http.Handler for the signaling server.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status":    "ok",
			"timestamp": time.Now().UnixMilli(),
		})
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"activeRooms":    s.Manager.ActiveRoomsCount(),
			"connectedPeers": s.Manager.ActivePeersCount(),
		})
	})

	mux.HandleFunc("/api/probe-stun", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		probes := stun.ProbeAllStunServers()
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status":     "ok",
			"stunProbes": probes,
		})
	})

	mux.HandleFunc("/api/tunnel/start", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		var req struct {
			HubURL       string `json:"hubUrl"`
			RoomCode     string `json:"roomCode"`
			IsHost       bool   `json:"isHost"`
			PeerID       string `json:"peerId"`
			TargetPeerID string `json:"targetPeerId"`
			GamePort     int    `json:"gamePort"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		s.tunnelMu.Lock()
		if s.activeTunnel != nil {
			s.activeTunnel.Stop()
			s.activeTunnel = nil
		}

		eng := tunnel.NewTunnelEngine(tunnel.EngineConfig{
			HubURL:       req.HubURL,
			RoomCode:     req.RoomCode,
			IsHost:       req.IsHost,
			MyPeerID:     req.PeerID,
			TargetPeerID: req.TargetPeerID,
			GamePort:     req.GamePort,
		})
		if err := eng.Start(); err != nil {
			s.tunnelMu.Unlock()
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		s.activeTunnel = eng
		listenPort := eng.GetListenPort()
		s.tunnelMu.Unlock()

		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status":     "ok",
			"listenPort": listenPort,
		})
	})

	mux.HandleFunc("/api/tunnel/stop", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		s.tunnelMu.Lock()
		if s.activeTunnel != nil {
			s.activeTunnel.Stop()
			s.activeTunnel = nil
		}
		s.tunnelMu.Unlock()

		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "ok",
		})
	})

	mux.HandleFunc("/api/tunnel/status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		s.tunnelMu.Lock()
		defer s.tunnelMu.Unlock()

		if s.activeTunnel == nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"running": false,
			})
			return
		}

		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"running":    true,
			"listenPort": s.activeTunnel.GetListenPort(),
			"bytesUp":    s.activeTunnel.BytesUp.Load(),
			"bytesDown":  s.activeTunnel.BytesDown.Load(),
		})
	})

	// Native Steam P2P (Valve SDR) API Endpoints
	mux.HandleFunc("/api/steam/status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		mgr := tunnel.GetSteamManager()
		st := mgr.GetStatus()
		_ = json.NewEncoder(w).Encode(st)
	})

	mux.HandleFunc("/api/steam/start", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		mgr := tunnel.GetSteamManager()
		if err := mgr.Init(); err != nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"ok": true,
		})
	})

	mux.HandleFunc("/api/steam/host", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		var req struct {
			Port int `json:"port"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if req.Port <= 0 {
			req.Port = 25565
		}

		mgr := tunnel.GetSteamManager()
		if err := mgr.StartHost(req.Port); err != nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}

		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"ok":   true,
			"port": req.Port,
		})
	})

	mux.HandleFunc("/api/steam/connect", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		var req struct {
			HostSteamID string `json:"hostSteamId"`
			Peer        string `json:"peer"`
			LocalPort   int    `json:"localPort"`
			RemotePort  int    `json:"remote_port"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		targetIDStr := req.HostSteamID
		if targetIDStr == "" {
			targetIDStr = req.Peer
		}
		targetID, err := strconv.ParseUint(targetIDStr, 10, 64)
		if err != nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": "invalid steam ID",
			})
			return
		}

		localPort := req.LocalPort
		if localPort <= 0 {
			localPort = req.RemotePort
		}
		if localPort <= 0 {
			localPort = 25565
		}

		mgr := tunnel.GetSteamManager()
		actualPort, err := mgr.StartClient(targetID, localPort)
		if err != nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}

		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"ok":           true,
			"listenPort":   actualPort,
			"targetHostId": targetIDStr,
		})
	})

	mux.HandleFunc("/api/steam/stop", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		mgr := tunnel.GetSteamManager()
		mgr.Stop()
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"ok": true,
		})
	})

	mux.HandleFunc("/api/steam/invite", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			return
		}

		var req struct {
			SteamID string `json:"steamId"`
			Peer    string `json:"peer"`
			Port    int    `json:"port"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		idStr := req.SteamID
		if idStr == "" {
			idStr = req.Peer
		}
		targetID, err := strconv.ParseUint(idStr, 10, 64)
		if err != nil {
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": "invalid steam ID",
			})
			return
		}

		port := req.Port
		if port <= 0 {
			port = 25565
		}

		mgr := tunnel.GetSteamManager()
		ok := mgr.InviteFriend(targetID, fmt.Sprintf("+connect_port %d", port))
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"ok": ok,
		})
	})

	mux.HandleFunc("/ws", s.handleWebSocket)
	mux.HandleFunc("/", s.handleWebSocket)

	return mux
}

// Start runs the signaling server.
func (s *Server) Start() error {
	addr := fmt.Sprintf("0.0.0.0:%d", s.Port)
	fmt.Printf("[LANForge Server] Listening on ws://%s\n", addr)
	return http.ListenAndServe(addr, s.Handler())
}

func (s *Server) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	peer := s.Manager.RegisterPeer(conn)
	defer s.Manager.UnregisterPeer(peer.ID)

	for {
		msgType, raw, err := conn.ReadMessage()
		if err != nil {
			break
		}

		if msgType == websocket.BinaryMessage {
			if len(raw) > 1 {
				targetLen := int(raw[0])
				if len(raw) >= 1+targetLen {
					targetID := string(raw[1 : 1+targetLen])
					payload := raw[1+targetLen:]
					targetPeer := s.Manager.GetPeer(targetID)
					if targetPeer != nil && targetPeer.Conn != nil {
						_ = targetPeer.Conn.WriteMessage(websocket.BinaryMessage, payload)
					}
				}
			}
			continue
		}

		var msg protocol.ClientMessage
		if err := json.Unmarshal(raw, &msg); err != nil {
			_ = peer.SendJSON(protocol.ServerMessage{
				Type:         "error",
				Code:         "BAD_REQUEST",
				ErrorMessage: "Invalid message payload",
			})
			continue
		}

		s.handleClientMessage(peer, msg)
	}
}

func (s *Server) handleClientMessage(peer *ConnectedPeer, msg protocol.ClientMessage) {
	peer.LastSeen = time.Now()

	switch msg.Type {
	case "tunnel_register":
		if msg.PeerID != "" {
			s.Manager.RebindPeerID(peer, msg.PeerID)
		}
		if msg.Code != "" {
			peer.RoomCode = msg.Code
		}

	case "create_room":
		room, you, err := s.Manager.CreateRoom(peer, msg.Name, msg.GamePreset, msg.Password, msg.HostNick, msg.MaxPeers)
		if err != nil {
			_ = peer.SendJSON(protocol.ServerMessage{
				Type:         "error",
				Code:         "CREATE_ROOM_FAILED",
				ErrorMessage: err.Error(),
			})
			return
		}
		_ = peer.SendJSON(protocol.ServerMessage{
			Type: "room_created",
			Room: &room,
			You:  &you,
		})

	case "join_room":
		room, you, err := s.Manager.JoinRoom(peer, msg.Code, msg.Nick, msg.Password)
		if err != nil {
			_ = peer.SendJSON(protocol.ServerMessage{
				Type:         "error",
				Code:         "JOIN_ROOM_FAILED",
				ErrorMessage: err.Error(),
			})
			return
		}
		_ = peer.SendJSON(protocol.ServerMessage{
			Type: "room_joined",
			Room: &room,
			You:  &you,
		})

	case "leave_room":
		s.Manager.LeaveRoom(peer)

	case "signal":
		if peer.RoomCode == "" {
			return
		}
		room := s.Manager.GetRoom(peer.RoomCode)
		if room == nil {
			return
		}
		room.SendTo(msg.TargetPeerID, protocol.ServerMessage{
			Type:       "signal_forward",
			FromPeerID: peer.ID,
			SignalType: msg.SignalType,
			Data:       msg.Data,
		})

	case "chat_message":
		if peer.RoomCode == "" {
			return
		}
		room := s.Manager.GetRoom(peer.RoomCode)
		if room == nil {
			return
		}
		chat := &protocol.ChatMessage{
			ID:         generateID("msg"),
			FromPeerID: peer.ID,
			FromNick:   peer.State.Nick,
			Text:       msg.Text,
			Timestamp:  time.Now().UnixMilli(),
		}
		room.Broadcast(protocol.ServerMessage{
			Type:    "chat_broadcast",
			Message: chat,
		}, "")

	case "update_room_port":
		if peer.RoomCode == "" || msg.Port <= 0 {
			return
		}
		room := s.Manager.GetRoom(peer.RoomCode)
		if room != nil {
			room.Broadcast(protocol.ServerMessage{
				Type: "room_port_updated",
				Port: msg.Port,
			}, "")
		}

	case "update_status":
		if peer.RoomCode == "" {
			return
		}
		room := s.Manager.GetRoom(peer.RoomCode)
		if room == nil {
			return
		}
		if msg.CurrentGame != "" {
			peer.State.CurrentGame = msg.CurrentGame
		}
		if msg.IsReady != nil {
			peer.State.IsReady = *msg.IsReady
		}
		if msg.PingMs != nil {
			peer.State.PingMs = *msg.PingMs
		}
		if msg.JitterMs != nil {
			peer.State.JitterMs = *msg.JitterMs
		}
		if msg.PacketLoss != nil {
			peer.State.PacketLoss = *msg.PacketLoss
		}
		if msg.ConnectionType != "" {
			peer.State.ConnectionType = msg.ConnectionType
		}
		room.Broadcast(protocol.ServerMessage{
			Type: "peer_updated",
			Peer: &peer.State,
		}, "")

	case "probe_stun":
		go func() {
			probes := stun.ProbeAllStunServers()
			_ = peer.SendJSON(protocol.ServerMessage{
				Type:       "stun_probes_result",
				StunProbes: probes,
			})
		}()

	case "ping":
		_ = peer.SendJSON(protocol.ServerMessage{
			Type:            "pong",
			ClientTimestamp: msg.Timestamp,
			ServerTimestamp: time.Now().UnixMilli(),
		})
	}
}
