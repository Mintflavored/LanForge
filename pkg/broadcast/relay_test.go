package broadcast

import (
	"net"
	"testing"
	"time"
)

func TestMinecraftPacketParsing(t *testing.T) {
	mgr := NewRelayManager()
	ch := mgr.Subscribe()
	defer mgr.Unsubscribe(ch)

	samplePacket := []byte("[MOTD]Test Survival World[/MOTD][AD]25565[/AD]")
	dummyAddr := &net.UDPAddr{
		IP:   net.ParseIP("192.168.1.105"),
		Port: 4445,
	}

	mgr.parsePacket(samplePacket, dummyAddr)

	select {
	case game := <-ch:
		if game.Port != 25565 {
			t.Fatalf("expected port 25565, got %d", game.Port)
		}
		if game.Motd != "Test Survival World" {
			t.Fatalf("expected motd 'Test Survival World', got '%s'", game.Motd)
		}
		if game.HostIP != "192.168.1.105" {
			t.Fatalf("expected host IP '192.168.1.105', got '%s'", game.HostIP)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("timed out waiting for discovered game emit")
	}

	active := mgr.GetActiveGames()
	if len(active) != 1 {
		t.Fatalf("expected 1 active game, got %d", len(active))
	}
}

func TestRelayManagerSubscribeUnsubscribe(t *testing.T) {
	mgr := NewRelayManager()
	ch1 := mgr.Subscribe()
	_ = mgr.Subscribe()

	if len(mgr.listeners) != 2 {
		t.Fatalf("expected 2 listeners, got %d", len(mgr.listeners))
	}

	mgr.Unsubscribe(ch1)
	if len(mgr.listeners) != 1 {
		t.Fatalf("expected 1 listener after unsubscribe, got %d", len(mgr.listeners))
	}

	mgr.Stop()
	if mgr.running {
		t.Fatal("expected running to be false after Stop")
	}
	if len(mgr.listeners) != 0 {
		t.Fatalf("expected 0 listeners after Stop, got %d", len(mgr.listeners))
	}
}
