package server

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"math/big"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/lanforge/lanforge/pkg/protocol"
)

// RoomManager manages all active rooms and connected peers.
type RoomManager struct {
	rooms map[string]*Room
	peers map[string]*ConnectedPeer
	mu    sync.RWMutex
}

// NewRoomManager creates a new RoomManager.
func NewRoomManager() *RoomManager {
	return &RoomManager{
		rooms: make(map[string]*Room),
		peers: make(map[string]*ConnectedPeer),
	}
}

func generateID(prefix string) string {
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return fmt.Sprintf("%s_%s", prefix, hex.EncodeToString(b))
}

// GenerateRoomCode creates a clean 6-character room code (e.g. LAN-9X4K).
func (m *RoomManager) GenerateRoomCode() string {
	const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	for {
		part1 := make([]byte, 3)
		part2 := make([]byte, 3)
		for i := 0; i < 3; i++ {
			n1, _ := rand.Int(rand.Reader, big.NewInt(int64(len(chars))))
			n2, _ := rand.Int(rand.Reader, big.NewInt(int64(len(chars))))
			part1[i] = chars[n1.Int64()]
			part2[i] = chars[n2.Int64()]
		}
		code := fmt.Sprintf("%s-%s", string(part1), string(part2))

		m.mu.RLock()
		_, exists := m.rooms[code]
		m.mu.RUnlock()
		if !exists {
			return code
		}
	}
}

// RegisterPeer registers a new incoming WebSocket connection.
func (m *RoomManager) RegisterPeer(conn *websocket.Conn) *ConnectedPeer {
	peerID := generateID("peer")
	peer := &ConnectedPeer{
		ID:   peerID,
		Conn: conn,
		State: protocol.PeerState{
			ID:       peerID,
			Nick:     "Player",
			JoinedAt: time.Now().UnixMilli(),
		},
		LastSeen: time.Now(),
	}

	m.mu.Lock()
	m.peers[peerID] = peer
	m.mu.Unlock()

	return peer
}

// UnregisterPeer removes a peer upon disconnect.
func (m *RoomManager) UnregisterPeer(peerID string) {
	m.mu.Lock()
	peer, exists := m.peers[peerID]
	if exists {
		delete(m.peers, peerID)
	}
	m.mu.Unlock()

	if exists && peer.RoomCode != "" {
		m.LeaveRoom(peer)
	}
}

// CreateRoom creates a new gaming room with the peer as host.
func (m *RoomManager) CreateRoom(peer *ConnectedPeer, name, gamePreset, password, hostNick string, maxPeers int) (protocol.RoomState, protocol.PeerState, error) {
	if peer.RoomCode != "" {
		m.LeaveRoom(peer)
	}

	code := m.GenerateRoomCode()
	if name == "" {
		if hostNick == "" {
			hostNick = "Host"
		}
		name = fmt.Sprintf("%s's LAN Party", hostNick)
	}
	if hostNick == "" {
		hostNick = "Host"
	}

	room := NewRoom(code, name, peer.ID, gamePreset, password, maxPeers)
	ip, err := room.AllocateVirtualIP(true)
	if err != nil {
		return protocol.RoomState{}, protocol.PeerState{}, err
	}

	peer.State.Nick = hostNick
	peer.State.IsHost = true
	peer.State.VirtualIP = ip
	peer.State.CurrentGame = gamePreset
	peer.RoomCode = code

	room.Peers[peer.ID] = peer

	m.mu.Lock()
	m.rooms[code] = room
	m.mu.Unlock()

	return room.ToState(), peer.State, nil
}

// JoinRoom adds a peer into an existing room.
func (m *RoomManager) JoinRoom(peer *ConnectedPeer, code, nick, password string) (protocol.RoomState, protocol.PeerState, error) {
	if peer.RoomCode != "" {
		m.LeaveRoom(peer)
	}

	normCode := strings.ToUpper(strings.TrimSpace(code))

	m.mu.RLock()
	room, exists := m.rooms[normCode]
	m.mu.RUnlock()

	if !exists {
		return protocol.RoomState{}, protocol.PeerState{}, fmt.Errorf("комната %s не найдена", normCode)
	}

	room.Mu.Lock()
	if len(room.Peers) >= room.MaxPeers {
		room.Mu.Unlock()
		return protocol.RoomState{}, protocol.PeerState{}, fmt.Errorf("комната заполнена")
	}

	if room.Password != "" && room.Password != strings.TrimSpace(password) {
		room.Mu.Unlock()
		return protocol.RoomState{}, protocol.PeerState{}, fmt.Errorf("неверный пароль комнаты")
	}
	room.Mu.Unlock()

	ip, err := room.AllocateVirtualIP(false)
	if err != nil {
		return protocol.RoomState{}, protocol.PeerState{}, err
	}

	if nick == "" {
		nick = fmt.Sprintf("Player_%s", peer.ID[len(peer.ID)-4:])
	}

	peer.State.Nick = nick
	peer.State.IsHost = false
	peer.State.VirtualIP = ip
	peer.RoomCode = normCode

	room.Mu.Lock()
	room.Peers[peer.ID] = peer
	room.Mu.Unlock()

	// Broadcast join event
	room.Broadcast(protocol.ServerMessage{
		Type: "peer_joined",
		Peer: &peer.State,
	}, peer.ID)

	return room.ToState(), peer.State, nil
}

// LeaveRoom removes a peer from their current room.
func (m *RoomManager) LeaveRoom(peer *ConnectedPeer) {
	if peer.RoomCode == "" {
		return
	}

	m.mu.RLock()
	room, exists := m.rooms[peer.RoomCode]
	m.mu.RUnlock()

	if !exists {
		peer.RoomCode = ""
		return
	}

	room.Mu.Lock()
	delete(room.Peers, peer.ID)
	room.ReleaseVirtualIPLocked(peer.State.VirtualIP)
	wasHost := peer.State.IsHost
	remainingCount := len(room.Peers)
	room.Mu.Unlock()

	peer.RoomCode = ""
	peer.State.VirtualIP = ""
	peer.State.IsHost = false

	if remainingCount == 0 {
		m.mu.Lock()
		delete(m.rooms, room.Code)
		m.mu.Unlock()
	} else {
		room.Broadcast(protocol.ServerMessage{
			Type:   "peer_left",
			PeerID: peer.ID,
			Reason: "left",
		}, "")

		// Host migration
		if wasHost {
			room.Mu.Lock()
			for _, nextHost := range room.Peers {
				nextHost.State.IsHost = true
				room.HostID = nextHost.ID
				room.Broadcast(protocol.ServerMessage{
					Type:      "host_transferred",
					NewHostID: nextHost.ID,
				}, "")
				room.Broadcast(protocol.ServerMessage{
					Type: "peer_updated",
					Peer: &nextHost.State,
				}, "")
				break
			}
			room.Mu.Unlock()
		}
	}
}

// GetRoom retrieves a room by code.
func (m *RoomManager) GetRoom(code string) *Room {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.rooms[strings.ToUpper(strings.TrimSpace(code))]
}

// ActiveRoomsCount returns total active rooms.
func (m *RoomManager) ActiveRoomsCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.rooms)
}

// ActivePeersCount returns total connected peers.
func (m *RoomManager) ActivePeersCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.peers)
}
