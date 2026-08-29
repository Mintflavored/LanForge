package presets

import (
	"testing"
)

func TestPresetsIntegrity(t *testing.T) {
	if len(AllPresets) < 10 {
		t.Fatalf("expected at least 10 presets, got %d", len(AllPresets))
	}

	for _, p := range AllPresets {
		if p.ID == "" {
			t.Errorf("preset missing ID: %+v", p)
		}
		if p.Name == "" {
			t.Errorf("preset %s missing Name", p.ID)
		}
		if p.DefaultPort <= 0 || p.DefaultPort > 65535 {
			t.Errorf("preset %s has invalid DefaultPort: %d", p.ID, p.DefaultPort)
		}
		if p.Protocol != "tcp" && p.Protocol != "udp" && p.Protocol != "both" {
			t.Errorf("preset %s has invalid Protocol: %s", p.ID, p.Protocol)
		}
	}
}

func TestFindPreset(t *testing.T) {
	mc := FindPreset("minecraft_java")
	if mc == nil {
		t.Fatal("expected to find minecraft_java preset")
	}
	if mc.DefaultPort != 25565 {
		t.Errorf("expected port 25565 for minecraft_java, got %d", mc.DefaultPort)
	}

	notFound := FindPreset("non_existent_game_xyz")
	if notFound != nil {
		t.Error("expected non_existent_game_xyz to be nil")
	}
}
