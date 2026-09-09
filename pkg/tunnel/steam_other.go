//go:build !windows
// +build !windows

package tunnel

import "errors"

type SteamFriend struct {
	SteamID  string `json:"steam_id"`
	Name     string `json:"name"`
	Online   bool   `json:"online"`
	InGame   bool   `json:"in_game"`
	InTunnel bool   `json:"in_tunnel"`
}

type SteamSelfInfo struct {
	SteamID string `json:"steam_id"`
	Name    string `json:"name"`
}

type SteamStatus struct {
	SteamRunning bool          `json:"steamRunning"`
	Initialized  bool          `json:"initialized"`
	SelfInfo     SteamSelfInfo `json:"self_info"`
	Friends      []SteamFriend `json:"friends"`
	Hosting      bool          `json:"hosting"`
	HostPort     int           `json:"hostPort"`
	ClientActive bool          `json:"clientActive"`
	ClientPort   int           `json:"clientPort"`
	TargetHostID string        `json:"targetHostId"`
	Ping         int           `json:"ping"`
	BytesUp      uint64        `json:"bytesUp"`
	BytesDown    uint64        `json:"bytesDown"`
}

type SteamManager struct{}

func GetSteamManager() *SteamManager {
	return &SteamManager{}
}

func (m *SteamManager) IsSteamRunning() bool { return false }
func (m *SteamManager) Init() error         { return errors.New("steamworks is only supported on Windows") }
func (m *SteamManager) StartHost(gamePort int) error {
	return errors.New("steamworks is only supported on Windows")
}
func (m *SteamManager) StartClient(hostSteamID uint64, localPort int) (int, error) {
	return 0, errors.New("steamworks is only supported on Windows")
}
func (m *SteamManager) Stop() {}
func (m *SteamManager) GetStatus() SteamStatus {
	return SteamStatus{}
}
func (m *SteamManager) InviteFriend(targetSteamID uint64, connectString string) bool {
	return false
}
