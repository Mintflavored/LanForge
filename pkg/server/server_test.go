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
	_, joined1, err := mgr.JoinRoom(client1, room.Code, "Dmitry", "", "", "")
	if err != nil {
		t.Fatalf("Failed to join room: %v", err)
	}

	if joined1.State.VirtualIP != "10.42.0.2" {
		t.Errorf("Expected client 1 IP to be 10.42.0.2, got %s", joined1.State.VirtualIP)
	}

	// Join client 2
	client2 := mgr.RegisterPeer(nil)
	_, joined2, err := mgr.JoinRoom(client2, room.Code, "Sergey", "", "", "")
	if err != nil {
		t.Fatalf("Failed to join room: %v", err)
	}

	if joined2.State.VirtualIP != "10.42.0.3" {
		t.Errorf("Expected client 2 IP to be 10.42.0.3, got %s", joined2.State.VirtualIP)
	}

	// Leave room
	mgr.LeaveRoom(client1)
	activeRoom := mgr.GetRoom(room.Code)
	if len(activeRoom.Peers) != 2 {
		t.Errorf("Expected 2 peers remaining, got %d", len(activeRoom.Peers))
	}
}

func TestHostReconnectPreservesRoleAndIP(t *testing.T) {
	mgr := NewRoomManager()

	// 1. Host creates room
	hostPeer := mgr.RegisterPeer(nil)
	originalHostID := hostPeer.ID
	token := hostPeer.SessionToken
	room, _, err := mgr.CreateRoom(hostPeer, "Steam Party", "steam_sdr", "", "HostUser", 8)
	if err != nil {
		t.Fatalf("Failed to create room: %v", err)
	}

	// 2. Guest joins room
	guestPeer := mgr.RegisterPeer(nil)
	_, guestJoined, err := mgr.JoinRoom(guestPeer, room.Code, "GuestUser", "", "", "")
	if err != nil {
		t.Fatalf("Guest failed to join: %v", err)
	}
	if guestJoined.State.VirtualIP != "10.42.0.2" {
		t.Fatalf("Expected guest IP 10.42.0.2, got %s", guestJoined.State.VirtualIP)
	}

	// 3. Host disconnects (temporary drop)
	mgr.HandlePeerDisconnect(hostPeer, nil, hostPeer.ConnGen)

	// Verify host is still in the room under grace period!
	roomObj := mgr.GetRoom(room.Code)
	if roomObj.HostID != originalHostID {
		t.Fatalf("Host should NOT be transferred during grace period! Got host %s", roomObj.HostID)
	}
	if _, inRoom := roomObj.Peers[originalHostID]; !inRoom {
		t.Fatalf("Host peer should remain in room during grace period")
	}

	// 4. Host reconnects via new websocket connection
	newConnPeer := mgr.RegisterPeer(nil)
	_, reconnectedPeer, err := mgr.JoinRoom(newConnPeer, room.Code, "HostUser", "", originalHostID, token)
	if err != nil {
		t.Fatalf("Host failed to re-sync room: %v", err)
	}

	// 5. Verify host retained ID, 10.42.0.1 IP, and IsHost status
	if reconnectedPeer.ID != originalHostID {
		t.Errorf("Expected peer ID %s, got %s", originalHostID, reconnectedPeer.ID)
	}
	if !reconnectedPeer.State.IsHost {
		t.Errorf("Expected reconnected peer to still be Host!")
	}
	if reconnectedPeer.State.VirtualIP != "10.42.0.1" {
		t.Errorf("Expected reconnected host IP 10.42.0.1, got %s", reconnectedPeer.State.VirtualIP)
	}
	if roomObj.HostID != originalHostID {
		t.Errorf("Room hostId should remain %s, got %s", originalHostID, roomObj.HostID)
	}

	// 6. Verify total peers is still exactly 2 (no duplicate peer created)
	if len(roomObj.Peers) != 2 {
		t.Errorf("Expected exactly 2 peers in room, got %d", len(roomObj.Peers))
	}
}

func TestDisconnectGracePeriodAndEviction(t *testing.T) {
	mgr := NewRoomManager()

	hostPeer := mgr.RegisterPeer(nil)
	room, _, err := mgr.CreateRoom(hostPeer, "Test Room", "", "", "Host", 4)
	if err != nil {
		t.Fatalf("Failed to create room: %v", err)
	}

	guestPeer := mgr.RegisterPeer(nil)
	_, guestJoined, err := mgr.JoinRoom(guestPeer, room.Code, "Guest", "", "", "")
	if err != nil {
		t.Fatalf("Failed to join guest: %v", err)
	}

	// Host disconnects
	mgr.HandlePeerDisconnect(hostPeer, nil, hostPeer.ConnGen)

	// Simulate grace period expiry by calling EvictPeer
	mgr.EvictPeer(hostPeer.ID)

	// Now host should be transferred to guest
	roomObj := mgr.GetRoom(room.Code)
	if roomObj.HostID != guestJoined.ID {
		t.Errorf("Expected host to be transferred to guest %s, got %s", guestJoined.ID, roomObj.HostID)
	}
	if guestJoined.State.VirtualIP != "10.42.0.1" {
		t.Errorf("Promoted guest should receive 10.42.0.1, got %s", guestJoined.State.VirtualIP)
	}
}
