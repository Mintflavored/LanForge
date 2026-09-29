package tunnel

import (
	"encoding/binary"
	"fmt"
	"log"
	"net"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

const (
	FrameOpen    byte = 0x01
	FrameData    byte = 0x02
	FrameClose   byte = 0x03
	FrameUDPData byte = 0x04
)

// EngineConfig configures a game tunnel instance.
type EngineConfig struct {
	HubURL        string // e.g. "wss://lanforge.onrender.com" or "ws://127.0.0.1:8787"
	RoomCode      string // e.g. "SEN-LFZ"
	IsHost        bool   // true if this peer is the host
	MyPeerID      string // Client's signaling peer ID
	TargetPeerID  string // Host's peer ID (if client)
	GamePort      int    // Host: local game port (e.g. 5000); Client: local listen port (e.g. 25565)
	DiscoveryPort int    // Optional LAN discovery port (e.g. 27846 for Anime Fighting)
}

// TunnelEngine manages TCP listening/dialing and multiplexing over a resilient WebSocket tunnel.
type TunnelEngine struct {
	cfg         EngineConfig
	wsConn      *websocket.Conn
	wsWriteMu   sync.Mutex
	listener    net.Listener
	streams     map[uint32]net.Conn
	streamPeers map[uint32]string // streamID -> sender PeerID
	streamsMu   sync.RWMutex
	nextStream  uint32
	running     atomic.Bool
	stopChan    chan struct{}
	BytesUp     atomic.Uint64
	BytesDown   atomic.Uint64

	// UDP proxying fields
	udpListener          *net.UDPConn
	udpDiscoveryListener *net.UDPConn
	udpMu                sync.RWMutex
	clientUDPSessions    map[string]uint32       // "ip:port" -> streamID
	clientUDPSrcAddrs    map[uint32]*net.UDPAddr // streamID -> srcAddr
	hostUDPSessions      map[string]*net.UDPConn // "senderID:streamID" -> dial conn to local game
}

// NewTunnelEngine creates a new game tunnel engine.
func NewTunnelEngine(cfg EngineConfig) *TunnelEngine {
	return &TunnelEngine{
		cfg:               cfg,
		streams:           make(map[uint32]net.Conn),
		streamPeers:       make(map[uint32]string),
		stopChan:          make(chan struct{}),
		clientUDPSessions: make(map[string]uint32),
		clientUDPSrcAddrs: make(map[uint32]*net.UDPAddr),
		hostUDPSessions:   make(map[string]*net.UDPConn),
	}
}

// Start launches the tunnel engine with background auto-reconnect.
func (e *TunnelEngine) Start() error {
	if !e.running.CompareAndSwap(false, true) {
		return fmt.Errorf("tunnel already running")
	}

	// 1. Verify hub URL
	u, err := url.Parse(e.cfg.HubURL)
	if err != nil {
		e.running.Store(false)
		return fmt.Errorf("invalid hub url: %w", err)
	}

	wsScheme := "ws"
	if u.Scheme == "https" || u.Scheme == "wss" {
		wsScheme = "wss"
	}
	wsURL := fmt.Sprintf("%s://%s/ws", wsScheme, u.Host)

	// 2. Initial connection check
	initialConn, err := e.dialAndRegister(wsURL)
	if err != nil {
		e.running.Store(false)
		return fmt.Errorf("failed to dial hub websocket: %w", err)
	}
	e.wsConn = initialConn

	// 3. Start connection manager with auto-reconnect
	go e.manageWsConnection(wsURL, initialConn)

	// 4. Start persistent Ping-Heartbeat loop
	go e.pingLoop()

	// 5. If Client (Friend), start local TCP listener and UDP listener
	if !e.cfg.IsHost {
		listenAddr := fmt.Sprintf("127.0.0.1:%d", e.cfg.GamePort)
		l, err := net.Listen("tcp", listenAddr)
		if err != nil {
			listenAddr = "127.0.0.1:0"
			l, err = net.Listen("tcp", listenAddr)
			if err != nil {
				e.Stop()
				return fmt.Errorf("failed to listen for game clients: %w", err)
			}
		}
		e.listener = l
		actualPort := l.Addr().(*net.TCPAddr).Port
		e.cfg.GamePort = actualPort
		log.Printf("[Tunnel Client] Listening for TCP game clients on %s -> forwarding to host %s", l.Addr().String(), e.cfg.TargetPeerID)
		go e.acceptGameClients()

		// Start local UDP listener on the same port
		udpAddr, err := net.ResolveUDPAddr("udp4", fmt.Sprintf("127.0.0.1:%d", actualPort))
		if err == nil {
			uconn, err := net.ListenUDP("udp4", udpAddr)
			if err != nil {
				uconn, _ = net.ListenUDP("udp4", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
			}
			if uconn != nil {
				e.udpListener = uconn
				log.Printf("[Tunnel Client] Listening for UDP game packets on %s -> forwarding to host %s", uconn.LocalAddr().String(), e.cfg.TargetPeerID)
				go e.readClientUDPLoop()
			}
		}

		// If DiscoveryPort is configured (e.g. 27846 for Anime Fighting), start local discovery beacon and responder
		if e.cfg.DiscoveryPort > 0 {
			// 1. Periodically broadcast ANIME_FIGHT_ROOM_READY_V1 to local game client on port 27846
			go e.startDiscoveryBeacon(e.cfg.DiscoveryPort)

			// 2. Also listen for active discovery search queries if port is free
			discAddr, err := net.ResolveUDPAddr("udp4", fmt.Sprintf("127.0.0.1:%d", e.cfg.DiscoveryPort))
			if err == nil {
				discConn, err := net.ListenUDP("udp4", discAddr)
				if err == nil {
					e.udpDiscoveryListener = discConn
					log.Printf("[Tunnel Client] Listening for LAN discovery queries on %s", discConn.LocalAddr().String())
					go e.readDiscoveryLoop()
				}
			}
		}
	} else {
		log.Printf("[Tunnel Host] Ready to pipe incoming streams/packets to local game port 127.0.0.1:%d", e.cfg.GamePort)
	}

	return nil
}

func (e *TunnelEngine) dialAndRegister(wsURL string) (*websocket.Conn, error) {
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		return nil, err
	}

	regMsg := map[string]interface{}{
		"type":         "tunnel_register",
		"code":         e.cfg.RoomCode,
		"peerId":       e.cfg.MyPeerID,
		"isHost":       e.cfg.IsHost,
		"targetPeerId": e.cfg.TargetPeerID,
	}
	if err := conn.WriteJSON(regMsg); err != nil {
		_ = conn.Close()
		return nil, err
	}

	return conn, nil
}

// manageWsConnection monitors the WebSocket and auto-reconnects with session preservation
func (e *TunnelEngine) manageWsConnection(wsURL string, activeConn *websocket.Conn) {
	conn := activeConn

	for {
		if !e.running.Load() {
			return
		}

		if conn == nil {
			log.Printf("[Tunnel] Auto-reconnecting to hub at %s (room %s)...", wsURL, e.cfg.RoomCode)
			newConn, err := e.dialAndRegister(wsURL)
			if err != nil {
				select {
				case <-e.stopChan:
					return
				case <-time.After(1500 * time.Millisecond):
					continue
				}
			}
			e.wsWriteMu.Lock()
			e.wsConn = newConn
			conn = newConn
			e.wsWriteMu.Unlock()
			log.Printf("[Tunnel] Hub connection restored and re-registered successfully!")
		}

		// Read frames until connection breaks
		e.readWsLoop(conn)

		// Disconnected: clean up this socket and loop back to reconnect
		e.wsWriteMu.Lock()
		if e.wsConn == conn {
			_ = conn.Close()
			e.wsConn = nil
		}
		conn = nil
		e.wsWriteMu.Unlock()

		select {
		case <-e.stopChan:
			return
		case <-time.After(500 * time.Millisecond):
			// Immediate reconnect attempt
		}
	}
}

// readWsLoop reads binary frames from the active connection until EOF or error
func (e *TunnelEngine) readWsLoop(conn *websocket.Conn) {
	for {
		msgType, raw, err := conn.ReadMessage()
		if err != nil {
			select {
			case <-e.stopChan:
				return
			default:
				log.Printf("[Tunnel] Hub connection lost: %v (auto-reconnecting...)", err)
				return
			}
		}

		if msgType == websocket.BinaryMessage {
			e.handleBinaryFrame(raw)
		}
	}
}

// pingLoop sends regular ping frames every 12s to keep cloud proxies alive
func (e *TunnelEngine) pingLoop() {
	ticker := time.NewTicker(12 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-e.stopChan:
			return
		case <-ticker.C:
			e.wsWriteMu.Lock()
			if e.wsConn != nil {
				_ = e.wsConn.WriteControl(websocket.PingMessage, []byte("keepalive"), time.Now().Add(5*time.Second))
			}
			e.wsWriteMu.Unlock()
		}
	}
}

// GetListenPort returns the local TCP/UDP port this client is listening on.
func (e *TunnelEngine) GetListenPort() int {
	return e.cfg.GamePort
}

// GetUDPListenPort returns the local UDP port this client is listening on.
func (e *TunnelEngine) GetUDPListenPort() int {
	if e.udpListener != nil {
		if addr, ok := e.udpListener.LocalAddr().(*net.UDPAddr); ok {
			return addr.Port
		}
	}
	return e.cfg.GamePort
}

// Stop terminates all listeners, connections and streams.
func (e *TunnelEngine) Stop() {
	if !e.running.CompareAndSwap(true, false) {
		return
	}

	close(e.stopChan)

	if e.listener != nil {
		_ = e.listener.Close()
	}

	if e.udpListener != nil {
		_ = e.udpListener.Close()
	}

	if e.udpDiscoveryListener != nil {
		_ = e.udpDiscoveryListener.Close()
	}

	e.udpMu.Lock()
	for key, conn := range e.hostUDPSessions {
		_ = conn.Close()
		delete(e.hostUDPSessions, key)
	}
	e.clientUDPSessions = make(map[string]uint32)
	e.clientUDPSrcAddrs = make(map[uint32]*net.UDPAddr)
	e.udpMu.Unlock()

	e.streamsMu.Lock()
	for id, conn := range e.streams {
		_ = conn.Close()
		delete(e.streams, id)
		delete(e.streamPeers, id)
	}
	e.streamsMu.Unlock()

	e.wsWriteMu.Lock()
	if e.wsConn != nil {
		_ = e.wsConn.Close()
		e.wsConn = nil
	}
	e.wsWriteMu.Unlock()

	log.Printf("[Tunnel] Engine stopped cleanly.")
}

// sendFrameTo sends:
// [targetLen:1B][targetPeerID:NB][senderLen:1B][senderPeerID:NB][frameType:1B][streamId:4B][payload...]
// If the tunnel is momentarily reconnecting, it waits up to 3s before failing.
func (e *TunnelEngine) sendFrameTo(targetPeerID string, frameType byte, streamID uint32, payload []byte) error {
	// Wait briefly if connection is in middle of 1s auto-reconnect
	var activeConn *websocket.Conn
	for i := 0; i < 30; i++ {
		e.wsWriteMu.Lock()
		activeConn = e.wsConn
		e.wsWriteMu.Unlock()
		if activeConn != nil || !e.running.Load() {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}

	e.wsWriteMu.Lock()
	defer e.wsWriteMu.Unlock()

	if e.wsConn == nil {
		return fmt.Errorf("websocket currently reconnecting")
	}

	targetBytes := []byte(targetPeerID)
	targetLen := byte(len(targetBytes))

	myBytes := []byte(e.cfg.MyPeerID)
	myLen := byte(len(myBytes))

	totalLen := 1 + int(targetLen) + 1 + int(myLen) + 1 + 4 + len(payload)
	buf := make([]byte, totalLen)

	buf[0] = targetLen
	copy(buf[1:1+targetLen], targetBytes)

	offset := 1 + int(targetLen)
	buf[offset] = myLen
	copy(buf[offset+1:offset+1+int(myLen)], myBytes)

	offset += 1 + int(myLen)
	buf[offset] = frameType
	binary.BigEndian.PutUint32(buf[offset+1:offset+5], streamID)

	if len(payload) > 0 {
		copy(buf[offset+5:], payload)
	}

	e.BytesUp.Add(uint64(len(payload)))
	return e.wsConn.WriteMessage(websocket.BinaryMessage, buf)
}

// acceptGameClients listens for local Minecraft connections (on friend's PC)
func (e *TunnelEngine) acceptGameClients() {
	for {
		conn, err := e.listener.Accept()
		if err != nil {
			select {
			case <-e.stopChan:
				return
			default:
				log.Printf("[Tunnel Client] Accept error: %v", err)
				return
			}
		}

		streamID := atomic.AddUint32(&e.nextStream, 1)
		target := e.cfg.TargetPeerID
		log.Printf("[Tunnel Client] New game connection accepted from %s (Stream #%d -> Host %s)", conn.RemoteAddr(), streamID, target)

		e.streamsMu.Lock()
		e.streams[streamID] = conn
		e.streamsMu.Unlock()

		// Send OPEN frame to Host
		_ = e.sendFrameTo(target, FrameOpen, streamID, nil)

		// Pipe TCP socket -> WebSocket
		go func(id uint32, targetHost string, c net.Conn) {
			defer func() {
				e.streamsMu.Lock()
				delete(e.streams, id)
				e.streamsMu.Unlock()
				_ = c.Close()
				_ = e.sendFrameTo(targetHost, FrameClose, id, nil)
				log.Printf("[Tunnel Client] Stream #%d closed", id)
			}()

			buf := make([]byte, 16384)
			for {
				n, err := c.Read(buf)
				if n > 0 {
					if err := e.sendFrameTo(targetHost, FrameData, id, buf[:n]); err != nil {
						// Transient send error during reconnection: continue attempting
						time.Sleep(50 * time.Millisecond)
						continue
					}
				}
				if err != nil {
					return
				}
			}
		}(streamID, target, conn)
	}
}

// readClientUDPLoop listens for incoming UDP game datagrams and multiplexes them over WebSocket
func (e *TunnelEngine) readClientUDPLoop() {
	buf := make([]byte, 65535)
	for {
		select {
		case <-e.stopChan:
			return
		default:
		}

		_ = e.udpListener.SetReadDeadline(time.Now().Add(1 * time.Second))
		n, srcAddr, err := e.udpListener.ReadFromUDP(buf)
		if err != nil {
			continue
		}

		addrKey := srcAddr.String()
		e.udpMu.Lock()
		streamID, exists := e.clientUDPSessions[addrKey]
		if !exists {
			streamID = atomic.AddUint32(&e.nextStream, 1)
			e.clientUDPSessions[addrKey] = streamID
			e.clientUDPSrcAddrs[streamID] = srcAddr
			log.Printf("[Tunnel Client] New UDP game session stream #%d from %s", streamID, addrKey)
		}
		e.udpMu.Unlock()

		target := e.cfg.TargetPeerID
		_ = e.sendFrameTo(target, FrameUDPData, streamID, buf[:n])
	}
}

// startDiscoveryBeacon broadcasts periodic LAN room announcements to local game clients (e.g. Anime Fighting)
func (e *TunnelEngine) startDiscoveryBeacon(port int) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	unicastAddr, err := net.ResolveUDPAddr("udp4", fmt.Sprintf("127.0.0.1:%d", port))
	if err != nil {
		return
	}
	broadcastAddr, _ := net.ResolveUDPAddr("udp4", fmt.Sprintf("255.255.255.255:%d", port))

	conn, err := net.ListenUDP("udp4", &net.UDPAddr{IP: net.ParseIP("0.0.0.0"), Port: 0})
	if err != nil {
		return
	}
	defer conn.Close()

	beaconMsg := []byte("ANIME_FIGHT_ROOM_READY_V1")

	for {
		select {
		case <-e.stopChan:
			return
		case <-ticker.C:
			if !e.running.Load() {
				return
			}
			_, _ = conn.WriteToUDP(beaconMsg, unicastAddr)
			if broadcastAddr != nil {
				_, _ = conn.WriteToUDP(beaconMsg, broadcastAddr)
			}
		}
	}
}

// readDiscoveryLoop answers LAN discovery queries for games like Anime Fighting
func (e *TunnelEngine) readDiscoveryLoop() {
	buf := make([]byte, 2048)
	for {
		select {
		case <-e.stopChan:
			return
		default:
		}

		_ = e.udpDiscoveryListener.SetReadDeadline(time.Now().Add(1 * time.Second))
		n, remoteAddr, err := e.udpDiscoveryListener.ReadFromUDP(buf)
		if err != nil {
			continue
		}

		reqStr := string(buf[:n])
		// Anime Fighting discovery query
		if strings.Contains(reqStr, "ANIME_FIGHT_ROOM_SEARCH_V1") {
			reply := []byte("ANIME_FIGHT_ROOM_READY_V1")
			_, _ = e.udpDiscoveryListener.WriteToUDP(reply, remoteAddr)
			log.Printf("[Tunnel Discovery] Responded to Anime Fighting discovery query from %s", remoteAddr.String())
		}
	}
}

// handleBinaryFrame decodes [senderLen:1B][senderPeerID:NB][frameType:1B][streamId:4B][payload]
func (e *TunnelEngine) handleBinaryFrame(raw []byte) {
	if len(raw) < 7 {
		return
	}

	senderLen := int(raw[0])
	if len(raw) < 1+senderLen+5 {
		return
	}
	senderID := string(raw[1 : 1+senderLen])

	offset := 1 + senderLen
	frameType := raw[offset]
	streamID := binary.BigEndian.Uint32(raw[offset+1 : offset+5])
	payload := raw[offset+5:]
	e.BytesDown.Add(uint64(len(payload)))

	switch frameType {
	case FrameOpen:
		// Host receives FrameOpen: connect to local Minecraft server
		if e.cfg.IsHost {
			e.streamsMu.Lock()
			e.streamPeers[streamID] = senderID
			e.streamsMu.Unlock()

			gameAddr := fmt.Sprintf("127.0.0.1:%d", e.cfg.GamePort)
			log.Printf("[Tunnel Host] Connecting stream #%d for peer %s to local Minecraft at %s...", streamID, senderID, gameAddr)
			gameConn, err := net.DialTimeout("tcp", gameAddr, 2*time.Second)
			if err != nil {
				log.Printf("[Tunnel Host] Failed to dial local game at %s: %v", gameAddr, err)
				_ = e.sendFrameTo(senderID, FrameClose, streamID, nil)
				return
			}

			e.streamsMu.Lock()
			e.streams[streamID] = gameConn
			e.streamsMu.Unlock()

			// Pipe gameConn -> WebSocket
			go func(id uint32, targetClient string, c net.Conn) {
				defer func() {
					e.streamsMu.Lock()
					delete(e.streams, id)
					delete(e.streamPeers, id)
					e.streamsMu.Unlock()
					_ = c.Close()
					_ = e.sendFrameTo(targetClient, FrameClose, id, nil)
					log.Printf("[Tunnel Host] Stream #%d to local game closed", id)
				}()

				buf := make([]byte, 16384)
				for {
					n, err := c.Read(buf)
					if n > 0 {
						if err := e.sendFrameTo(targetClient, FrameData, id, buf[:n]); err != nil {
							time.Sleep(50 * time.Millisecond)
							continue
						}
					}
					if err != nil {
						return
					}
				}
			}(streamID, senderID, gameConn)
		}

	case FrameData:
		e.streamsMu.RLock()
		conn, exists := e.streams[streamID]
		e.streamsMu.RUnlock()
		if exists && len(payload) > 0 {
			_, _ = conn.Write(payload)
		}

	case FrameUDPData:
		if e.cfg.IsHost {
			sessKey := fmt.Sprintf("%s:%d", senderID, streamID)
			e.udpMu.Lock()
			gameConn, exists := e.hostUDPSessions[sessKey]
			if !exists {
				gameAddr, err := net.ResolveUDPAddr("udp4", fmt.Sprintf("127.0.0.1:%d", e.cfg.GamePort))
				if err == nil {
					conn, err := net.DialUDP("udp4", nil, gameAddr)
					if err == nil {
						gameConn = conn
						e.hostUDPSessions[sessKey] = conn
						log.Printf("[Tunnel Host] Created UDP forwarder for peer %s stream #%d -> local game 127.0.0.1:%d", senderID, streamID, e.cfg.GamePort)

						go func(key string, targetClient string, sID uint32, c *net.UDPConn) {
							defer func() {
								e.udpMu.Lock()
								delete(e.hostUDPSessions, key)
								e.udpMu.Unlock()
								_ = c.Close()
								log.Printf("[Tunnel Host] UDP forwarder closed for %s", key)
							}()

							replyBuf := make([]byte, 65535)
							for {
								if !e.running.Load() {
									return
								}
								_ = c.SetReadDeadline(time.Now().Add(60 * time.Second))
								rn, rerr := c.Read(replyBuf)
								if rn > 0 {
									_ = e.sendFrameTo(targetClient, FrameUDPData, sID, replyBuf[:rn])
								}
								if rerr != nil {
									return
								}
							}
						}(sessKey, senderID, streamID, conn)
					}
				}
			}
			e.udpMu.Unlock()

			if gameConn != nil && len(payload) > 0 {
				_, _ = gameConn.Write(payload)
			}
		} else {
			e.udpMu.RLock()
			srcAddr, exists := e.clientUDPSrcAddrs[streamID]
			e.udpMu.RUnlock()

			if exists && e.udpListener != nil && len(payload) > 0 {
				_, _ = e.udpListener.WriteToUDP(payload, srcAddr)
			}
		}

	case FrameClose:
		e.streamsMu.Lock()
		conn, exists := e.streams[streamID]
		if exists {
			delete(e.streams, streamID)
			delete(e.streamPeers, streamID)
			_ = conn.Close()
		}
		e.streamsMu.Unlock()
	}
}
