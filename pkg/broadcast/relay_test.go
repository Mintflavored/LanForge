package broadcast

import (
	"net"
	"strings"
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

func TestAnimeFightingPacketParsing(t *testing.T) {
	mgr := NewRelayManager()
	ch := mgr.Subscribe()
	defer mgr.Unsubscribe(ch)

	samplePacket := []byte("ANIME_FIGHT_ROOM_READY_V1")
	dummyAddr := &net.UDPAddr{
		IP:   net.ParseIP("192.168.1.120"),
		Port: 27846,
	}

	mgr.parsePacket(samplePacket, dummyAddr)

	select {
	case game := <-ch:
		if game.Port != 27845 {
			t.Fatalf("expected port 27845, got %d", game.Port)
		}
		if game.GameName != "Anime Fighting: Multiverse" {
			t.Fatalf("expected gameName 'Anime Fighting: Multiverse', got '%s'", game.GameName)
		}
		if game.HostIP != "192.168.1.120" {
			t.Fatalf("expected host IP '192.168.1.120', got '%s'", game.HostIP)
		}
		if game.Protocol != "UDP" {
			t.Fatalf("expected protocol UDP, got %s", game.Protocol)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("timed out waiting for discovered game emit")
	}

	active := mgr.GetActiveGames()
	if len(active) != 1 {
		t.Fatalf("expected 1 active game, got %d", len(active))
	}
	if active[0].Motd != "Комната готова к бою" {
		t.Fatalf("expected Motd 'Комната готова к бою', got '%s'", active[0].Motd)
	}

	// Test duration-annotated packet (e.g. 180 sec)
	samplePacketWithDuration := []byte("ANIME_FIGHT_ROOM_READY_V1|180")
	mgr.parsePacket(samplePacketWithDuration, dummyAddr)

	select {
	case game := <-ch:
		if game.Motd != "1 на 1 · Время боя: 180 сек" {
			t.Fatalf("expected Motd '1 на 1 · Время боя: 180 сек', got '%s'", game.Motd)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("timed out waiting for duration-annotated game emit")
	}

	// Test unlimited time packet (0 sec)
	samplePacketUnlimited := []byte("ANIME_FIGHT_ROOM_READY_V1|0")
	mgr.parsePacket(samplePacketUnlimited, dummyAddr)

	select {
	case game := <-ch:
		if game.Motd != "1 на 1 · Без лимита" {
			t.Fatalf("expected Motd '1 на 1 · Без лимита', got '%s'", game.Motd)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("timed out waiting for unlimited game emit")
	}

	// Test 2v2 team battle packet
	samplePacketTeam := []byte("ANIME_FIGHT_ROOM_READY_V1|180|2v2")
	mgr.parsePacket(samplePacketTeam, dummyAddr)

	select {
	case game := <-ch:
		if game.Motd != "2 на 2 · Время боя: 180 сек" {
			t.Fatalf("expected Motd '2 на 2 · Время боя: 180 сек', got '%s'", game.Motd)
		}
		if game.Name != "Anime Fighting: Multiverse (2 на 2)" {
			t.Fatalf("expected room name 'Anime Fighting: Multiverse (2 на 2)', got '%s'", game.Name)
		}
		if !strings.Contains(game.Extra, "2 на 2") {
			t.Fatalf("expected Extra to contain '2 на 2', got '%s'", game.Extra)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("timed out waiting for 2v2 team game emit")
	}
}
