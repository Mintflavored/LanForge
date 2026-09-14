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
	rooms         map[string]*Room
	peers         map[string]*ConnectedPeer
	tunnelConns   map[string]*websocket.Conn
	userPresences map[string]*protocol.UserPresence
	userPeers     map[string]*ConnectedPeer
	userSubs      map[string]map[string]bool
	mu            sync.RWMutex
}

// NewRoomManager creates a new RoomManager.
func NewRoomManager() *RoomManager {
	return &RoomManager{
		rooms:         make(map[string]*Room),
		peers:         make(map[string]*ConnectedPeer),
		tunnelConns:   make(map[string]*websocket.Conn),
		userPresences: make(map[string]*protocol.UserPresence),
		userPeers:     make(map[string]*ConnectedPeer),
		userSubs:      make(map[string]map[string]bool),
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
		ID:           peerID,
		Conn:         conn,
		ConnGen:      1,
		SessionToken: generateID("tok"),
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

// RegisterTunnel registers a dedicated TCP-over-WebSocket tunnel connection.
func (m *RoomManager) RegisterTunnel(peerID string, conn *websocket.Conn) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.tunnelConns[peerID] = conn
}

// UnregisterTunnel removes a tunnel connection.
func (m *RoomManager) UnregisterTunnel(peerID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.tunnelConns, peerID)
}

// GetBinaryConn returns the active connection for binary multiplexing.
func (m *RoomManager) GetBinaryConn(targetID string) *websocket.Conn {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if conn, ok := m.tunnelConns[targetID]; ok && conn != nil {
		return conn
	}
	if p, ok := m.peers[targetID]; ok && p != nil {
		return p.Conn
	}
	return nil
}

// GetPeer retrieves a peer by ID.
func (m *RoomManager) GetPeer(peerID string) *ConnectedPeer {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.peers[peerID]
}

// RebindPeerID reassigns a peer's ID in the peers map.
func (m *RoomManager) RebindPeerID(peer *ConnectedPeer, newID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.peers, peer.ID)
	peer.ID = newID
	peer.State.ID = newID
	m.peers[newID] = peer
}

func (m *RoomManager) notifySubscribersLocked(presence *protocol.UserPresence) []*ConnectedPeer {
	if presence == nil || presence.UserID == "" {
		return nil
	}
	var subscribers []*ConnectedPeer
	if subs, ok := m.userSubs[presence.UserID]; ok {
		for subUID := range subs {
			if subPeer, found := m.userPeers[subUID]; found && subPeer != nil {
				subscribers = append(subscribers, subPeer)
			}
		}
	}
	return subscribers
}

// UnregisterPeer removes a peer upon disconnect and notifies presence subscribers.
func (m *RoomManager) UnregisterPeer(peerID string) {
	m.mu.Lock()
	peer, exists := m.peers[peerID]
	var subscribers []*ConnectedPeer
	var offlinePresence *protocol.UserPresence

	if exists {
		delete(m.peers, peerID)
		if peer.UserID != "" {
			if curr, ok := m.userPeers[peer.UserID]; ok && curr == peer {
				delete(m.userPeers, peer.UserID)
				if p, ok := m.userPresences[peer.UserID]; ok && p != nil {
					p.Status = "offline"
					p.LastSeen = time.Now().UnixMilli()
					offlinePresence = p
					subscribers = m.notifySubscribersLocked(p)
				}
			}
		}
	}
	m.mu.Unlock()

	if offlinePresence != nil && len(subscribers) > 0 {
		offlineMsg := protocol.ServerMessage{
			Type:     "presence_update",
			Presence: offlinePresence,
		}
		for _, sub := range subscribers {
			_ = sub.SendJSON(offlineMsg)
		}
	}

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

	peer.Mu.Lock()
	peer.State.Nick = hostNick
	peer.State.IsHost = true
	peer.State.VirtualIP = ip
	peer.State.CurrentGame = gamePreset
	peer.RoomCode = code
	if peer.SessionToken == "" {
		peer.SessionToken = generateID("tok")
	}
	peer.Mu.Unlock()

	room.Mu.Lock()
	room.Peers[peer.ID] = peer
	room.Mu.Unlock()

	m.mu.Lock()
	m.rooms[code] = room
	m.mu.Unlock()

	m.syncPresenceRoomStatus(peer, "in_game", code, gamePreset)

	return room.ToState(), peer.State, nil
}

func (m *RoomManager) findRoom(code string) (*Room, bool) {
	norm := strings.ToUpper(strings.TrimSpace(code))
	if r, ok := m.rooms[norm]; ok {
		return r, true
	}
	clean := strings.ReplaceAll(strings.ReplaceAll(norm, "-", ""), " ", "")
	for k, r := range m.rooms {
		kClean := strings.ReplaceAll(strings.ReplaceAll(k, "-", ""), " ", "")
		if kClean == clean {
			return r, true
		}
	}
	return nil, false
}

// JoinRoom adds a peer into an existing room or seamlessly resumes their session if peerID matches.
func (m *RoomManager) JoinRoom(peer *ConnectedPeer, code, nick, password, peerID, sessionToken string) (protocol.RoomState, *ConnectedPeer, error) {
	normCode := strings.ToUpper(strings.TrimSpace(code))

	m.mu.RLock()
	room, exists := m.findRoom(normCode)
	m.mu.RUnlock()

	if !exists {
		return protocol.RoomState{}, nil, fmt.Errorf("комната %s не найдена на этом сервере", normCode)
	}

	// 1. Проверка на возобновление существующей сессии (reconnection / session resumption)
	if peerID != "" {
		room.Mu.Lock()
		existingPeer, isReconnecting := room.Peers[peerID]
		room.Mu.Unlock()

		if isReconnecting {
			// Проверяем сессионный токен, если он был задан
			if existingPeer.SessionToken != "" && sessionToken != "" && existingPeer.SessionToken != sessionToken {
				return protocol.RoomState{}, nil, fmt.Errorf("недействительный сессионный токен")
			}

			// Возобновляем сессию
			existingPeer.Mu.Lock()
			if existingPeer.EvictTimer != nil {
				existingPeer.EvictTimer.Stop()
				existingPeer.EvictTimer = nil
			}
			existingPeer.ConnGen++
			if existingPeer.Conn != nil && existingPeer.Conn != peer.Conn {
				_ = existingPeer.Conn.Close()
			}
			existingPeer.Conn = peer.Conn
			existingPeer.DisconnectedAt = time.Time{}
			existingPeer.LastSeen = time.Now()
			if nick != "" {
				existingPeer.State.Nick = nick
			}
			existingPeer.Mu.Unlock()

			// Если временный peer имел другой ID, удаляем его из m.peers и привязываем existingPeer
			if peer.ID != existingPeer.ID {
				m.mu.Lock()
				delete(m.peers, peer.ID)
				m.peers[existingPeer.ID] = existingPeer
				m.mu.Unlock()
			}

			// Оповещаем комнату о возвращении участника
			room.Broadcast(protocol.ServerMessage{
				Type: "peer_updated",
				Peer: &existingPeer.State,
			}, "")

			m.syncPresenceRoomStatus(existingPeer, "in_game", room.Code, room.GamePreset)

			return room.ToState(), existingPeer, nil
		}
	}

	// 2. Вход нового участника в комнату
	if peer.RoomCode != "" {
		m.LeaveRoom(peer)
	}

	room.Mu.Lock()
	if len(room.Peers) >= room.MaxPeers {
		room.Mu.Unlock()
		return protocol.RoomState{}, nil, fmt.Errorf("комната заполнена")
	}

	if room.Password != "" && room.Password != strings.TrimSpace(password) {
		room.Mu.Unlock()
		return protocol.RoomState{}, nil, fmt.Errorf("неверный пароль комнаты")
	}
	room.Mu.Unlock()

	ip, err := room.AllocateVirtualIP(false)
	if err != nil {
		return protocol.RoomState{}, nil, err
	}

	if nick == "" {
		nick = fmt.Sprintf("Player_%s", peer.ID[len(peer.ID)-4:])
	}

	peer.Mu.Lock()
	peer.State.Nick = nick
	peer.State.IsHost = false
	peer.State.VirtualIP = ip
	peer.RoomCode = room.Code
	if peer.SessionToken == "" {
		peer.SessionToken = generateID("tok")
	}
	peer.Mu.Unlock()

	room.Mu.Lock()
	room.Peers[peer.ID] = peer
	room.Mu.Unlock()

	// Broadcast join event outside of mutex lock
	room.Broadcast(protocol.ServerMessage{
		Type: "peer_joined",
		Peer: &peer.State,
	}, peer.ID)

	m.syncPresenceRoomStatus(peer, "in_game", room.Code, room.GamePreset)

	return room.ToState(), peer, nil
}

// HandlePeerDisconnect handles socket disconnection with a 45-second grace period for room peers.
func (m *RoomManager) HandlePeerDisconnect(peer *ConnectedPeer, conn *websocket.Conn, connGen uint64) {
	if peer == nil {
		return
	}

	if peer.IsTunnel {
		m.UnregisterTunnel(peer.ID)
		return
	}

	peer.Mu.Lock()
	// Проверяем, не было ли соединение уже перехвачено новым сокетом
	if peer.Conn != conn || peer.ConnGen != connGen {
		peer.Mu.Unlock()
		return
	}

	peer.Conn = nil
	peer.DisconnectedAt = time.Now()
	roomCode := peer.RoomCode
	peerID := peer.ID
	peer.Mu.Unlock()

	// Если пир не находился в комнате, удаляем сразу
	if roomCode == "" {
		m.UnregisterPeer(peerID)
		return
	}

	// Запускаем 45-секундный льготный период (grace period) перед выселением
	peer.Mu.Lock()
	if peer.EvictTimer != nil {
		peer.EvictTimer.Stop()
	}
	peer.EvictTimer = time.AfterFunc(45*time.Second, func() {
		m.EvictPeer(peerID)
	})
	peer.Mu.Unlock()
}

// EvictPeer removes a peer after the disconnect grace period has expired.
func (m *RoomManager) EvictPeer(peerID string) {
	m.mu.RLock()
	peer := m.peers[peerID]
	m.mu.RUnlock()

	if peer == nil {
		return
	}

	peer.Mu.Lock()
	if peer.Conn != nil {
		// Пир успел переподключиться, отменяем выселение
		peer.Mu.Unlock()
		return
	}
	peer.Mu.Unlock()

	m.UnregisterPeer(peerID)
}

// LeaveRoom removes a peer from their current room immediately (intentional leave).
func (m *RoomManager) LeaveRoom(peer *ConnectedPeer) {
	if peer == nil || peer.RoomCode == "" {
		return
	}

	peer.Mu.Lock()
	if peer.EvictTimer != nil {
		peer.EvictTimer.Stop()
		peer.EvictTimer = nil
	}
	roomCode := peer.RoomCode
	peer.Mu.Unlock()

	m.mu.RLock()
	room, exists := m.findRoom(roomCode)
	m.mu.RUnlock()

	if !exists {
		peer.Mu.Lock()
		peer.RoomCode = ""
		peer.Mu.Unlock()
		return
	}

	room.Mu.Lock()
	delete(room.Peers, peer.ID)
	room.ReleaseVirtualIPLocked(peer.State.VirtualIP)
	wasHost := peer.State.IsHost
	remainingCount := len(room.Peers)

	var nextHost *ConnectedPeer
	if wasHost && remainingCount > 0 {
		for _, p := range room.Peers {
			nextHost = p
			nextHost.Mu.Lock()
			nextHost.State.IsHost = true
			room.HostID = nextHost.ID
			// Promote new host to 10.42.0.1
			room.ReleaseVirtualIPLocked(nextHost.State.VirtualIP)
			nextHost.State.VirtualIP = "10.42.0.1"
			room.AssignedIPs[1] = true
			nextHost.Mu.Unlock()
			break
		}
	}
	room.Mu.Unlock()

	peer.Mu.Lock()
	peer.RoomCode = ""
	peer.State.VirtualIP = ""
	peer.State.IsHost = false
	peer.Mu.Unlock()

	if remainingCount == 0 {
		// Keep the room alive for 2 minutes in case of client reconnects
		go func(rCode string) {
			time.Sleep(2 * time.Minute)
			m.mu.Lock()
			defer m.mu.Unlock()
			if r, ok := m.rooms[rCode]; ok {
				r.Mu.Lock()
				count := len(r.Peers)
				r.Mu.Unlock()
				if count == 0 {
					delete(m.rooms, rCode)
				}
			}
		}(room.Code)
	} else {
		// Broadcast outside of mutex lock (prevents deadlock)
		room.Broadcast(protocol.ServerMessage{
			Type:   "peer_left",
			PeerID: peer.ID,
			Reason: "left",
		}, "")

		if nextHost != nil {
			room.Broadcast(protocol.ServerMessage{
				Type:      "host_transferred",
				NewHostID: nextHost.ID,
			}, "")
			room.Broadcast(protocol.ServerMessage{
				Type: "peer_updated",
				Peer: &nextHost.State,
			}, "")
		}
	}
	m.syncPresenceRoomStatus(peer, "online", "", "")
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

// BroadcastAll sends a message to all connected peers.
func (m *RoomManager) BroadcastAll(msg protocol.ServerMessage) {
	m.mu.RLock()
	peers := make([]*ConnectedPeer, 0, len(m.peers))
	for _, p := range m.peers {
		peers = append(peers, p)
	}
	m.mu.RUnlock()

	for _, p := range peers {
		_ = p.SendJSON(msg)
	}
}

func (m *RoomManager) syncPresenceRoomStatus(peer *ConnectedPeer, status, roomCode, game string) {
	if peer == nil || peer.UserID == "" {
		return
	}
	m.mu.Lock()
	var subs []*ConnectedPeer
	var pCopy *protocol.UserPresence
	if p, ok := m.userPresences[peer.UserID]; ok && p != nil {
		p.Status = status
		p.RoomCode = roomCode
		if game != "" {
			p.Game = game
		}
		p.LastSeen = time.Now().UnixMilli()
		cp := *p
		pCopy = &cp
		subs = m.notifySubscribersLocked(&cp)
	}
	m.mu.Unlock()

	if pCopy != nil && len(subs) > 0 {
		updateMsg := protocol.ServerMessage{
			Type:     "presence_update",
			Presence: pCopy,
		}
		for _, sub := range subs {
			if sub != peer {
				_ = sub.SendJSON(updateMsg)
			}
		}
	}
}

// AnnouncePresence registers or updates the user's presence and subscriptions, returning the snapshot of online friends.
func (m *RoomManager) AnnouncePresence(peer *ConnectedPeer, presence protocol.UserPresence, friendIDs []string) []protocol.UserPresence {
	m.mu.Lock()
	if presence.UserID == "" {
		m.mu.Unlock()
		return nil
	}
	peer.UserID = presence.UserID
	presence.LastSeen = time.Now().UnixMilli()
	if presence.Status == "" {
		if peer.RoomCode != "" {
			presence.Status = "in_game"
			presence.RoomCode = peer.RoomCode
		} else {
			presence.Status = "online"
		}
	}

	pCopy := presence
	m.userPresences[presence.UserID] = &pCopy
	m.userPeers[presence.UserID] = peer

	// Update friend subscriptions
	for _, fID := range friendIDs {
		fID = strings.TrimSpace(fID)
		if fID == "" || fID == presence.UserID {
			continue
		}
		if m.userSubs[fID] == nil {
			m.userSubs[fID] = make(map[string]bool)
		}
		m.userSubs[fID][presence.UserID] = true
	}

	// Prepare snapshot of online friends
	var snapshot []protocol.UserPresence
	for _, fID := range friendIDs {
		fID = strings.TrimSpace(fID)
		if p, ok := m.userPresences[fID]; ok && p != nil && p.Status != "offline" {
			snapshot = append(snapshot, *p)
		}
	}

	subscribers := m.notifySubscribersLocked(&pCopy)
	m.mu.Unlock()

	// Notify subscribers
	updateMsg := protocol.ServerMessage{
		Type:     "presence_update",
		Presence: &pCopy,
	}
	for _, sub := range subscribers {
		if sub != peer {
			_ = sub.SendJSON(updateMsg)
		}
	}

	return snapshot
}

// SendFriendInvite sends a game invite directly to the target friend if they are currently online.
func (m *RoomManager) SendFriendInvite(fromPeer *ConnectedPeer, invite protocol.FriendInvite, targetUserID string) error {
	m.mu.RLock()
	targetPeer, ok := m.userPeers[targetUserID]
	m.mu.RUnlock()

	if !ok || targetPeer == nil {
		return fmt.Errorf("пользователь %s не в сети", targetUserID)
	}

	invite.Timestamp = time.Now().UnixMilli()
	msg := protocol.ServerMessage{
		Type:   "incoming_invite",
		Invite: &invite,
	}
	return targetPeer.SendJSON(msg)
}
