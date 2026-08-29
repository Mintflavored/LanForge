package server

import (
	"testing"
)

func TestRoomLifecycleAndIPAllocation(t *testing.T) {
	mgr := NewRoomManager()

	hostPeer := mgr.RegisterPeer(nil)
	room, hostState, err := mgr.CreateRoom(hostPeer, "Minecraft LAN", "minecraft_java", "", "Alex", 16)
	if err != nil {
		t.Fatalf("Failed to create room: %v", err)
	}

	if hostState.VirtualIP != "10.42.0.1" {
		t.Errorf("Expected host IP to be 10.42.0.1, got %s", hostState.VirtualIP)
	}

	if !hostState.IsHost {
		t.Errorf("Expected hostState.IsHost to be true")
	}

	// Join client 1
	client1 := mgr.RegisterPeer(nil)
	_, clientState1, err := mgr.JoinRoom(client1, room.Code, "Dmitry", "")
	if err != nil {
		t.Fatalf("Failed to join room: %v", err)
	}

	if clientState1.VirtualIP != "10.42.0.2" {
		t.Errorf("Expected client 1 IP to be 10.42.0.2, got %s", clientState1.VirtualIP)
	}

	// Join client 2
	client2 := mgr.RegisterPeer(nil)
	_, clientState2, err := mgr.JoinRoom(client2, room.Code, "Sergey", "")
	if err != nil {
		t.Fatalf("Failed to join room: %v", err)
	}

	if clientState2.VirtualIP != "10.42.0.3" {
		t.Errorf("Expected client 2 IP to be 10.42.0.3, got %s", clientState2.VirtualIP)
	}

	// Leave room
	mgr.LeaveRoom(client1)
	activeRoom := mgr.GetRoom(room.Code)
	if len(activeRoom.Peers) != 2 {
		t.Errorf("Expected 2 peers remaining, got %d", len(activeRoom.Peers))
	}
}
