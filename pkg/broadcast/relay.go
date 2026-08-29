package broadcast

import (
	"fmt"
	"net"
	"strings"
	"sync"
	"time"
)

// DiscoveredGame represents a LAN game discovered through UDP broadcast.
type DiscoveredGame struct {
	ID         string `json:"id"`
	GameName   string `json:"gameName"`
	HostNick   string `json:"hostNick"`
	HostIP     string `json:"hostIp"`
	Port       int    `json:"port"`
	DetectedAt int64  `json:"detectedAt"`
	Motd       string `json:"motd"`
}

// RelayManager listens to LAN broadcast packets and notifies discovered games.
type RelayManager struct {
	listeners []chan DiscoveredGame
	running   bool
	mu        sync.Mutex
	stopChan  chan struct{}
}

// NewRelayManager creates a new RelayManager.
func NewRelayManager() *RelayManager {
	return &RelayManager{
		listeners: make([]chan DiscoveredGame, 0),
		stopChan:  make(chan struct{}),
	}
}

// Subscribe adds a channel to receive discovered LAN games.
func (r *RelayManager) Subscribe() chan DiscoveredGame {
	r.mu.Lock()
	defer r.mu.Unlock()
	ch := make(chan DiscoveredGame, 10)
	r.listeners = append(r.listeners, ch)
	return ch
}

// Start begins listening to UDP broadcast packets (port 4445 for Minecraft LAN, etc).
func (r *RelayManager) Start() {
	r.mu.Lock()
	if r.running {
		r.mu.Unlock()
		return
	}
	r.running = true
	r.mu.Unlock()

	go r.listenMinecraftBroadcast()
}

// Stop stops the broadcast listener.
func (r *RelayManager) Stop() {
	r.mu.Lock()
	defer r.mu.Unlock()
	if !r.running {
		return
	}
	r.running = false
	close(r.stopChan)
}

func (r *RelayManager) emit(game DiscoveredGame) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, ch := range r.listeners {
		select {
		case ch <- game:
		default:
		}
	}
}

func (r *RelayManager) listenMinecraftBroadcast() {
	addr, err := net.ResolveUDPAddr("udp4", "0.0.0.0:4445")
	if err != nil {
		return
	}

	conn, err := net.ListenUDP("udp4", addr)
	if err != nil {
		return
	}
	defer conn.Close()

	buf := make([]byte, 2048)
	for {
		select {
		case <-r.stopChan:
			return
		default:
		}

		_ = conn.SetReadDeadline(time.Now().Add(1 * time.Second))
		n, src, err := conn.ReadFrom(buf)
		if err != nil {
			continue
		}

		text := string(buf[:n])
		// Minecraft LAN format: [MOTD]World Name[/MOTD][AD]Port[/AD]
		if strings.Contains(text, "[MOTD]") && strings.Contains(text, "[/MOTD]") {
			motdStart := strings.Index(text, "[MOTD]") + 6
			motdEnd := strings.Index(text, "[/MOTD]")
			motd := "Minecraft LAN World"
			if motdEnd > motdStart {
				motd = text[motdStart:motdEnd]
			}

			port := 25565
			if strings.Contains(text, "[AD]") && strings.Contains(text, "[/AD]") {
				adStart := strings.Index(text, "[AD]") + 4
				adEnd := strings.Index(text, "[/AD]")
				if adEnd > adStart {
					_, _ = fmt.Sscanf(text[adStart:adEnd], "%d", &port)
				}
			}

			hostIP := "127.0.0.1"
			if udpAddr, ok := src.(*net.UDPAddr); ok {
				hostIP = udpAddr.IP.String()
			}

			r.emit(DiscoveredGame{
				ID:         fmt.Sprintf("mc_%d", port),
				GameName:   "Minecraft LAN World",
				HostNick:   "Local Host",
				HostIP:     hostIP,
				Port:       port,
				DetectedAt: time.Now().UnixMilli(),
				Motd:       motd,
			})
		}
	}
}
