package tunnel

import (
	"encoding/binary"
	"fmt"
	"log"
	"net"
	"net/url"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

const (
	FrameOpen  byte = 0x01
	FrameData  byte = 0x02
	FrameClose byte = 0x03
)

// EngineConfig configures a game tunnel instance.
type EngineConfig struct {
	HubURL       string // e.g. "wss://lanforge.onrender.com" or "ws://127.0.0.1:8787"
	RoomCode     string // e.g. "SEN-LFZ"
	IsHost       bool   // true if this peer is the host
	MyPeerID     string // Client's signaling peer ID
	TargetPeerID string // Host's peer ID (if client)
	GamePort     int    // Host: local game port (e.g. 5000); Client: local listen port (e.g. 25565)
}

// TunnelEngine manages TCP listening/dialing and multiplexing over a WebSocket tunnel.
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
}

// NewTunnelEngine creates a new game tunnel engine.
func NewTunnelEngine(cfg EngineConfig) *TunnelEngine {
	return &TunnelEngine{
		cfg:         cfg,
		streams:     make(map[uint32]net.Conn),
		streamPeers: make(map[uint32]string),
		stopChan:    make(chan struct{}),
	}
}

// Start launches the tunnel engine.
func (e *TunnelEngine) Start() error {
	if !e.running.CompareAndSwap(false, true) {
		return fmt.Errorf("tunnel already running")
	}

	// 1. Establish WebSocket tunnel connection to signaling hub
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

	log.Printf("[Tunnel] Connecting to hub at %s for room %s (host=%v, myPeer=%s)...", wsURL, e.cfg.RoomCode, e.cfg.IsHost, e.cfg.MyPeerID)
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		e.running.Store(false)
		return fmt.Errorf("failed to dial hub websocket: %w", err)
	}
	e.wsConn = conn

	// Register tunnel role with the hub
	regMsg := map[string]interface{}{
		"type":         "tunnel_register",
		"code":         e.cfg.RoomCode,
		"peerId":       e.cfg.MyPeerID,
		"isHost":       e.cfg.IsHost,
		"targetPeerId": e.cfg.TargetPeerID,
	}
	if err := e.sendJSON(regMsg); err != nil {
		e.Stop()
		return fmt.Errorf("failed to register tunnel session: %w", err)
	}

	// 2. Start reader loop from WebSocket
	go e.readWsLoop()

	// 3. Start persistent Ping-Heartbeat loop (prevents Render 60s idle disconnect)
	go e.pingLoop()

	// 4. If Client (Friend), start local TCP listener for Minecraft
	if !e.cfg.IsHost {
		listenAddr := fmt.Sprintf("127.0.0.1:%d", e.cfg.GamePort)
		l, err := net.Listen("tcp", listenAddr)
		if err != nil {
			// If preferred port is busy, fallback to dynamic port
			listenAddr = "127.0.0.1:0"
			l, err = net.Listen("tcp", listenAddr)
			if err != nil {
				e.Stop()
				return fmt.Errorf("failed to listen for game clients: %w", err)
			}
		}
		e.listener = l
		e.cfg.GamePort = l.Addr().(*net.TCPAddr).Port
		log.Printf("[Tunnel Client] Listening for Minecraft on %s -> forwarding to host %s", l.Addr().String(), e.cfg.TargetPeerID)
		go e.acceptGameClients()
	} else {
		log.Printf("[Tunnel Host] Ready to pipe incoming streams to local game port 127.0.0.1:%d", e.cfg.GamePort)
	}

	return nil
}

// pingLoop sends regular ping frames every 15s to keep the Render cloud connection alive
func (e *TunnelEngine) pingLoop() {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-e.stopChan:
			return
		case <-ticker.C:
			e.wsWriteMu.Lock()
			if e.wsConn != nil {
				_ = e.wsConn.WriteControl(websocket.PingMessage, []byte("heartbeat"), time.Now().Add(5*time.Second))
			}
			e.wsWriteMu.Unlock()
		}
	}
}

// GetListenPort returns the local TCP port this client is listening on.
func (e *TunnelEngine) GetListenPort() int {
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

	e.streamsMu.Lock()
	for id, conn := range e.streams {
		_ = conn.Close()
		delete(e.streams, id)
		delete(e.streamPeers, id)
	}
	e.streamsMu.Unlock()

	if e.wsConn != nil {
		_ = e.wsConn.Close()
	}
	log.Printf("[Tunnel] Engine stopped.")
}

func (e *TunnelEngine) sendJSON(v interface{}) error {
	e.wsWriteMu.Lock()
	defer e.wsWriteMu.Unlock()
	if e.wsConn == nil {
		return fmt.Errorf("websocket closed")
	}
	return e.wsConn.WriteJSON(v)
}

// sendFrameTo sends:
// [targetLen:1B][targetPeerID:NB][senderLen:1B][senderPeerID:NB][frameType:1B][streamId:4B][payload...]
func (e *TunnelEngine) sendFrameTo(targetPeerID string, frameType byte, streamID uint32, payload []byte) error {
	e.wsWriteMu.Lock()
	defer e.wsWriteMu.Unlock()
	if e.wsConn == nil {
		return fmt.Errorf("websocket closed")
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
						return
					}
				}
				if err != nil {
					return
				}
			}
		}(streamID, target, conn)
	}
}

// readWsLoop handles incoming binary tunnel frames from the hub
func (e *TunnelEngine) readWsLoop() {
	defer e.Stop()

	for {
		msgType, raw, err := e.wsConn.ReadMessage()
		if err != nil {
			select {
			case <-e.stopChan:
				return
			default:
				log.Printf("[Tunnel] Hub connection lost: %v", err)
				return
			}
		}

		if msgType == websocket.BinaryMessage {
			e.handleBinaryFrame(raw)
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
							return
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
