package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
	"github.com/lanforge/lanforge/pkg/protocol"
	"github.com/lanforge/lanforge/pkg/stun"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow LAN and web clients
	},
}

// Server encapsulates the HTTP and WebSocket signaling listener.
type Server struct {
	Manager *RoomManager
	Port    int
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
		_, raw, err := conn.ReadMessage()
		if err != nil {
			break
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
