package protocol

import (
	"encoding/json"
	"testing"
)

func TestClientMessageSerialization(t *testing.T) {
	msg := ClientMessage{
		Type:       "create_room",
		Name:       "Test Party",
		GamePreset: "minecraft_java",
		HostNick:   "Gamer",
		MaxPeers:   16,
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("failed to marshal ClientMessage: %v", err)
	}

	var decoded ClientMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal ClientMessage: %v", err)
	}

	if decoded.Type != msg.Type || decoded.Name != msg.Name || decoded.GamePreset != msg.GamePreset {
		t.Errorf("decoded message mismatch: got %+v, want %+v", decoded, msg)
	}
}

func TestServerMessageSerialization(t *testing.T) {
	msg := ServerMessage{
		Type: "room_created",
		Room: &RoomState{
			Code:        "LAN-9X4K",
			Name:        "Test Room",
			HostID:      "peer_1",
			HasPassword: false,
			MaxPeers:    16,
		},
		You: &PeerState{
			ID:        "peer_1",
			Nick:      "HostPlayer",
			VirtualIP: "10.42.0.1",
			IsHost:    true,
		},
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("failed to marshal ServerMessage: %v", err)
	}

	var decoded ServerMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal ServerMessage: %v", err)
	}

	if decoded.Type != "room_created" || decoded.Room.Code != "LAN-9X4K" || decoded.You.VirtualIP != "10.42.0.1" {
		t.Errorf("decoded message mismatch: got %+v", decoded)
	}
}
