package client

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/lanforge/lanforge/pkg/protocol"
)

// Client handles connection to the LANForge signaling and room server.
type Client struct {
	ServerURL   string
	Conn        *websocket.Conn
	Connected   bool
	You         protocol.PeerState
	Room        *protocol.RoomState
	Events      chan protocol.ServerMessage
	stopChan    chan struct{}
	mu          sync.RWMutex
	writeMu     sync.Mutex
	lastPingRTT int
}

// NewClient creates a new LANForge client.
func NewClient(serverURL string) *Client {
	if serverURL == "" {
		serverURL = "ws://localhost:8787"
	}
	return &Client{
		ServerURL: serverURL,
		Events:    make(chan protocol.ServerMessage, 50),
		stopChan:  make(chan struct{}),
	}
}

// Connect opens the WebSocket connection to the server.
func (c *Client) Connect() error {
	c.mu.Lock()
	if c.Connected {
		c.mu.Unlock()
		return nil
	}
	c.mu.Unlock()

	conn, _, err := websocket.DefaultDialer.Dial(c.ServerURL, nil)
	if err != nil {
		return fmt.Errorf("failed to connect to server %s: %w", c.ServerURL, err)
	}

	c.mu.Lock()
	c.Conn = conn
	c.Connected = true
	c.mu.Unlock()

	go c.readLoop()
	go c.pingLoop()

	return nil
}

// Disconnect closes the client connection.
func (c *Client) Disconnect() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.Connected {
		return
	}
	c.Connected = false
	if c.Conn != nil {
		_ = c.Conn.Close()
	}
}

func (c *Client) readLoop() {
	for {
		_, raw, err := c.Conn.ReadMessage()
		if err != nil {
			c.mu.Lock()
			c.Connected = false
			c.mu.Unlock()
			c.Events <- protocol.ServerMessage{
				Type:         "connection_lost",
				ErrorMessage: err.Error(),
			}
			break
		}

		var msg protocol.ServerMessage
		if err := json.Unmarshal(raw, &msg); err == nil {
			c.handleServerMessage(msg)
			c.Events <- msg
		}
	}
}

func (c *Client) handleServerMessage(msg protocol.ServerMessage) {
	c.mu.Lock()
	defer c.mu.Unlock()

	switch msg.Type {
	case "room_created", "room_joined":
		c.Room = msg.Room
		if msg.You != nil {
			c.You = *msg.You
		}

	case "peer_joined":
		if c.Room != nil && msg.Peer != nil {
			exists := false
			for i, p := range c.Room.Peers {
				if p.ID == msg.Peer.ID {
					c.Room.Peers[i] = *msg.Peer
					exists = true
					break
				}
			}
			if !exists {
				c.Room.Peers = append(c.Room.Peers, *msg.Peer)
			}
		}

	case "peer_left":
		if c.Room != nil {
			updated := make([]protocol.PeerState, 0, len(c.Room.Peers))
			for _, p := range c.Room.Peers {
				if p.ID != msg.PeerID {
					updated = append(updated, p)
				}
			}
			c.Room.Peers = updated
		}

	case "peer_updated":
		if c.Room != nil && msg.Peer != nil {
			for i, p := range c.Room.Peers {
				if p.ID == msg.Peer.ID {
					c.Room.Peers[i] = *msg.Peer
					break
				}
			}
			if c.You.ID == msg.Peer.ID {
				c.You = *msg.Peer
			}
		}

	case "host_transferred":
		if c.Room != nil {
			c.Room.HostID = msg.NewHostID
			if c.You.ID == msg.NewHostID {
				c.You.IsHost = true
			}
		}

	case "pong":
		rtt := int(time.Now().UnixMilli() - msg.ClientTimestamp)
		c.lastPingRTT = rtt
		c.You.PingMs = rtt
	}
}

func (c *Client) sendJSON(v interface{}) error {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if c.Conn == nil {
		return fmt.Errorf("not connected")
	}
	return c.Conn.WriteJSON(v)
}

// CreateRoom sends a create room request.
func (c *Client) CreateRoom(name, gamePreset, password, hostNick string) error {
	return c.sendJSON(protocol.ClientMessage{
		Type:       "create_room",
		Name:       name,
		GamePreset: gamePreset,
		Password:   password,
		HostNick:   hostNick,
	})
}

// JoinRoom sends a join room request.
func (c *Client) JoinRoom(code, nick, password string) error {
	return c.sendJSON(protocol.ClientMessage{
		Type:     "join_room",
		Code:     code,
		Nick:     nick,
		Password: password,
	})
}

// LeaveRoom leaves the active room.
func (c *Client) LeaveRoom() error {
	c.mu.Lock()
	c.Room = nil
	c.mu.Unlock()
	return c.sendJSON(protocol.ClientMessage{
		Type: "leave_room",
	})
}

// SendChat sends a chat message into the room.
func (c *Client) SendChat(text string) error {
	return c.sendJSON(protocol.ClientMessage{
		Type: "chat_message",
		Text: text,
	})
}

// PingRTT returns the last measured latency in milliseconds.
func (c *Client) PingRTT() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.lastPingRTT
}

func (c *Client) pingLoop() {
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.stopChan:
			return
		case <-ticker.C:
			c.mu.RLock()
			conn := c.Conn
			connected := c.Connected
			c.mu.RUnlock()

			if connected && conn != nil {
				_ = c.sendJSON(protocol.ClientMessage{
					Type:      "ping",
					Timestamp: time.Now().UnixMilli(),
				})
			}
		}
	}
}
