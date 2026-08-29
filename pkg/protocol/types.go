package protocol

import "encoding/json"

// PeerState represents the state of a single peer inside a room.
type PeerState struct {
	ID             string  `json:"id"`
	Nick           string  `json:"nick"`
	VirtualIP      string  `json:"virtualIp"`
	IsHost         bool    `json:"isHost"`
	IsReady        bool    `json:"isReady"`
	CurrentGame    string  `json:"currentGame,omitempty"`
	PingMs         int     `json:"pingMs,omitempty"`
	JitterMs       float64 `json:"jitterMs,omitempty"`
	PacketLoss     float64 `json:"packetLoss,omitempty"`
	ConnectionType string  `json:"connectionType,omitempty"` // "p2p" or "relay"
	JoinedAt       int64   `json:"joinedAt"`
}

// StunProbeResult holds latency metrics to a specific STUN endpoint.
type StunProbeResult struct {
	Server   string `json:"server"`
	RTTMs    int    `json:"rttMs"`
	Status   string `json:"status"` // "ok", "timeout", "blocked"
	PublicIP string `json:"publicIp,omitempty"`
}

// RoomState represents the full snapshot of a gaming room.
type RoomState struct {
	Code        string      `json:"code"`
	Name        string      `json:"name"`
	GamePreset  string      `json:"gamePreset,omitempty"`
	HostID      string      `json:"hostId"`
	HasPassword bool        `json:"hasPassword"`
	Peers       []PeerState `json:"peers"`
	CreatedAt   int64       `json:"createdAt"`
	MaxPeers    int         `json:"maxPeers"`
}

// ChatMessage represents a room text message.
type ChatMessage struct {
	ID         string `json:"id"`
	FromPeerID string `json:"fromPeerId"`
	FromNick   string `json:"fromNick"`
	Text       string `json:"text"`
	Timestamp  int64  `json:"timestamp"`
}

// ClientMessage is sent from Client to Server.
type ClientMessage struct {
	Type           string          `json:"type"`
	Name           string          `json:"name,omitempty"`
	GamePreset     string          `json:"gamePreset,omitempty"`
	Password       string          `json:"password,omitempty"`
	HostNick       string          `json:"hostNick,omitempty"`
	MaxPeers       int             `json:"maxPeers,omitempty"`
	Code           string          `json:"code,omitempty"`
	Nick           string          `json:"nick,omitempty"`
	TargetPeerID   string          `json:"targetPeerId,omitempty"`
	SignalType     string          `json:"signalType,omitempty"`
	Data           json.RawMessage `json:"data,omitempty"`
	Text           string          `json:"text,omitempty"`
	CurrentGame    string          `json:"currentGame,omitempty"`
	IsReady        *bool           `json:"isReady,omitempty"`
	PingMs         *int            `json:"pingMs,omitempty"`
	JitterMs       *float64        `json:"jitterMs,omitempty"`
	PacketLoss     *float64        `json:"packetLoss,omitempty"`
	ConnectionType string          `json:"connectionType,omitempty"`
	Timestamp      int64           `json:"timestamp,omitempty"`
}

// ServerMessage is sent from Server to Client.
type ServerMessage struct {
	Type            string            `json:"type"`
	Room            *RoomState        `json:"room,omitempty"`
	You             *PeerState        `json:"you,omitempty"`
	Peer            *PeerState        `json:"peer,omitempty"`
	PeerID          string            `json:"peerId,omitempty"`
	Reason          string            `json:"reason,omitempty"`
	NewHostID       string            `json:"newHostId,omitempty"`
	FromPeerID      string            `json:"fromPeerId,omitempty"`
	SignalType      string            `json:"signalType,omitempty"`
	Data            json.RawMessage   `json:"data,omitempty"`
	Message         *ChatMessage      `json:"message,omitempty"`
	Code            string            `json:"code,omitempty"`
	ErrorMessage    string            `json:"errorMessage,omitempty"`
	ClientTimestamp int64             `json:"clientTimestamp,omitempty"`
	ServerTimestamp int64             `json:"serverTimestamp,omitempty"`
	StunProbes      []StunProbeResult `json:"stunProbes,omitempty"`
}
