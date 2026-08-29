package server

import (
	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/lanforge/lanforge/pkg/protocol"
)

// ConnectedPeer represents an active WebSocket connection of a player.
type ConnectedPeer struct {
	ID       string
	Conn     *websocket.Conn
	State    protocol.PeerState
	RoomCode string
	LastSeen time.Time
	Mu       sync.Mutex
}

// SendJSON sends a thread-safe JSON message to this peer.
func (p *ConnectedPeer) SendJSON(v interface{}) error {
	p.Mu.Lock()
	defer p.Mu.Unlock()
	if p.Conn == nil {
		return fmt.Errorf("connection closed")
	}
	return p.Conn.WriteJSON(v)
}

// Room represents a virtual LAN party room.
type Room struct {
	Code        string
	Name        string
	GamePreset  string
	HostID      string
	Password    string
	CreatedAt   int64
	MaxPeers    int
	AssignedIPs map[int]bool
	Peers       map[string]*ConnectedPeer
	Mu          sync.RWMutex
}

// NewRoom constructs a new gaming room.
func NewRoom(code, name, hostID, gamePreset, password string, maxPeers int) *Room {
	if maxPeers <= 0 {
		maxPeers = 16
	}
	return &Room{
		Code:        code,
		Name:        name,
		GamePreset:  gamePreset,
		HostID:      hostID,
		Password:    password,
		CreatedAt:   time.Now().UnixMilli(),
		MaxPeers:    maxPeers,
		AssignedIPs: make(map[int]bool),
		Peers:       make(map[string]*ConnectedPeer),
	}
}

// AllocateVirtualIP assigns an IP from 10.42.0.x subnet.
func (r *Room) AllocateVirtualIP(isHost bool) (string, error) {
	r.Mu.Lock()
	defer r.Mu.Unlock()

	if isHost {
		r.AssignedIPs[1] = true
		return "10.42.0.1", nil
	}

	for i := 2; i <= 254; i++ {
		if !r.AssignedIPs[i] {
			r.AssignedIPs[i] = true
			return fmt.Sprintf("10.42.0.%d", i), nil
		}
	}
	return "", fmt.Errorf("no virtual IPs available in room subnet")
}

// ReleaseVirtualIPLocked frees the virtual IP while caller holds r.Mu.
func (r *Room) ReleaseVirtualIPLocked(ip string) {
	var octet int
	if n, _ := fmt.Sscanf(ip, "10.42.0.%d", &octet); n == 1 {
		delete(r.AssignedIPs, octet)
	}
}

// ReleaseVirtualIP frees the virtual IP in the room pool.
func (r *Room) ReleaseVirtualIP(ip string) {
	r.Mu.Lock()
	defer r.Mu.Unlock()
	r.ReleaseVirtualIPLocked(ip)
}

// ToState converts the internal room to protocol RoomState.
func (r *Room) ToState() protocol.RoomState {
	r.Mu.RLock()
	defer r.Mu.RUnlock()

	peerStates := make([]protocol.PeerState, 0, len(r.Peers))
	for _, p := range r.Peers {
		peerStates = append(peerStates, p.State)
	}

	return protocol.RoomState{
		Code:        r.Code,
		Name:        r.Name,
		GamePreset:  r.GamePreset,
		HostID:      r.HostID,
		HasPassword: r.Password != "",
		Peers:       peerStates,
		CreatedAt:   r.CreatedAt,
		MaxPeers:    r.MaxPeers,
	}
}

// Broadcast sends a server message to all peers in the room except excludePeerID.
func (r *Room) Broadcast(msg protocol.ServerMessage, excludePeerID string) {
	r.Mu.RLock()
	peersCopy := make([]*ConnectedPeer, 0, len(r.Peers))
	for id, p := range r.Peers {
		if id != excludePeerID {
			peersCopy = append(peersCopy, p)
		}
	}
	r.Mu.RUnlock()

	for _, p := range peersCopy {
		_ = p.SendJSON(msg)
	}
}

// SendTo sends a server message to a specific peer.
func (r *Room) SendTo(targetID string, msg protocol.ServerMessage) bool {
	r.Mu.RLock()
	target, exists := r.Peers[targetID]
	r.Mu.RUnlock()

	if exists {
		_ = target.SendJSON(msg)
		return true
	}
	return false
}
