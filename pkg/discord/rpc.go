package discord

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"
)

const defaultClientID = "1543141438970396702"

// Activity represents the Discord Rich Presence activity structure.
type Activity struct {
	Details    string `json:"details,omitempty"`
	State      string `json:"state,omitempty"`
	Timestamps struct {
		Start int64 `json:"start,omitempty"`
	} `json:"timestamps,omitempty"`
	Assets struct {
		LargeImage string `json:"large_image,omitempty"`
		LargeText  string `json:"large_text,omitempty"`
		SmallImage string `json:"small_image,omitempty"`
		SmallText  string `json:"small_text,omitempty"`
	} `json:"assets,omitempty"`
	Party *Party `json:"party,omitempty"`
}

// Party represents a multiplayer party.
type Party struct {
	ID   string `json:"id,omitempty"`
	Size [2]int `json:"size,omitempty"`
}

// Client manages Discord RPC communication over Windows Named Pipe.
type Client struct {
	clientID     string
	pipe         *os.File
	connected    bool
	startTime    int64
	lastActivity *Activity
	mu           sync.Mutex
	stopChan     chan struct{}
}

// NewClient initializes a new Discord RPC client.
func NewClient(clientID ...string) *Client {
	cid := defaultClientID
	if len(clientID) > 0 && clientID[0] != "" {
		cid = clientID[0]
	}
	c := &Client{
		clientID:  cid,
		startTime: time.Now().Unix(),
		stopChan:  make(chan struct{}),
	}
	go c.workerLoop()
	return c
}

func (c *Client) workerLoop() {
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	// Initial connection attempt
	c.mu.Lock()
	c.connect()
	c.mu.Unlock()

	for {
		select {
		case <-c.stopChan:
			c.mu.Lock()
			if c.pipe != nil {
				_ = c.pipe.Close()
				c.pipe = nil
			}
			c.connected = false
			c.mu.Unlock()
			return
		case <-ticker.C:
			c.mu.Lock()
			if !c.connected {
				if c.connect() && c.lastActivity != nil {
					_ = c.sendActivity(c.lastActivity)
				}
			}
			c.mu.Unlock()
		}
	}
}

func (c *Client) connect() bool {
	for i := 0; i < 10; i++ {
		pipePath := fmt.Sprintf(`\\.\pipe\discord-ipc-%d`, i)
		f, err := os.OpenFile(pipePath, os.O_RDWR, 0)
		if err != nil {
			continue
		}

		c.pipe = f
		handshake := map[string]interface{}{
			"v":         1,
			"client_id": c.clientID,
		}
		if err := c.send(0, handshake); err != nil {
			_ = f.Close()
			c.pipe = nil
			continue
		}

		// Read handshake response
		var header [8]byte
		_ = f.SetReadDeadline(time.Now().Add(1 * time.Second))
		if _, err := f.Read(header[:]); err != nil {
			_ = f.Close()
			c.pipe = nil
			continue
		}

		length := binary.LittleEndian.Uint32(header[4:8])
		buf := make([]byte, length)
		if _, err := f.Read(buf); err != nil {
			_ = f.Close()
			c.pipe = nil
			continue
		}

		var resp map[string]interface{}
		if json.Unmarshal(buf, &resp) == nil && resp["cmd"] == "DISPATCH" && resp["evt"] == "READY" {
			c.connected = true
			_ = f.SetReadDeadline(time.Time{})
			return true
		}

		_ = f.Close()
		c.pipe = nil
	}
	return false
}

func (c *Client) send(opcode uint32, payload interface{}) error {
	if c.pipe == nil {
		return fmt.Errorf("pipe disconnected")
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	header := make([]byte, 8)
	binary.LittleEndian.PutUint32(header[0:4], opcode)
	binary.LittleEndian.PutUint32(header[4:8], uint32(len(data)))

	if _, err := c.pipe.Write(append(header, data...)); err != nil {
		c.connected = false
		_ = c.pipe.Close()
		c.pipe = nil
		return err
	}
	return nil
}

func (c *Client) sendActivity(a *Activity) error {
	payload := map[string]interface{}{
		"cmd": "SET_ACTIVITY",
		"args": map[string]interface{}{
			"pid":      os.Getpid(),
			"activity": a,
		},
		"nonce": fmt.Sprintf("%d", time.Now().UnixNano()),
	}
	return c.send(1, payload)
}

// SetActivity updates Discord presence.
func (c *Client) SetActivity(details, state string, partySize, partyMax int, roomCode, gamePreset string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	largeKey := "app_icon"
	if gamePreset != "" {
		largeKey = gamePreset
	}

	act := &Activity{
		Details: details,
		State:   state,
	}
	act.Timestamps.Start = c.startTime
	act.Assets.LargeImage = largeKey
	act.Assets.LargeText = "LANForge — Virtual LAN Hub"
	act.Assets.SmallImage = "app_icon"
	act.Assets.SmallText = "P2P Virtual Network"

	if partySize > 0 && roomCode != "" {
		if partyMax <= 0 {
			partyMax = 16
		}
		act.Party = &Party{
			ID:   fmt.Sprintf("lanforge_%s", roomCode),
			Size: [2]int{partySize, partyMax},
		}
	}

	c.lastActivity = act
	if c.connected {
		_ = c.sendActivity(act)
	}
}

// Close disconnects from Discord.
func (c *Client) Close() {
	close(c.stopChan)
}
