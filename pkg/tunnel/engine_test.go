package tunnel

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestTunnelEngineEndToEnd(t *testing.T) {
	// 1. Mock Minecraft Echo Server on random port
	echoListener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("Failed to create echo listener: %v", err)
	}
	defer echoListener.Close()
	echoPort := echoListener.Addr().(*net.TCPAddr).Port

	go func() {
		for {
			conn, err := echoListener.Accept()
			if err != nil {
				return
			}
			go func(c net.Conn) {
				defer c.Close()
				_, _ = io.Copy(c, c) // Echo back everything
			}(conn)
		}
	}()

	// 2. Mock WebSocket Hub that routes binary messages between peers
	var upgrader = websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	var hubMu sync.Mutex
	hubConns := make(map[string]*websocket.Conn)

	hubServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ws, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer ws.Close()

		var peerID string
		for {
			msgType, data, err := ws.ReadMessage()
			if err != nil {
				break
			}
			if msgType == websocket.TextMessage {
				// Registration
				if strings.Contains(string(data), "peer_host") {
					peerID = "peer_host"
				} else {
					peerID = "peer_client"
				}
				hubMu.Lock()
				hubConns[peerID] = ws
				hubMu.Unlock()
			} else if msgType == websocket.BinaryMessage && len(data) > 0 {
				// Route to target peer
				targetLen := int(data[0])
				if len(data) >= 1+targetLen {
					targetID := string(data[1 : 1+targetLen])
					payload := data[1+targetLen:] // [frameType][streamId][payload]
					hubMu.Lock()
					targetConn := hubConns[targetID]
					hubMu.Unlock()
					if targetConn != nil {
						_ = targetConn.WriteMessage(websocket.BinaryMessage, payload)
					}
				}
			}
		}
		hubMu.Lock()
		delete(hubConns, peerID)
		hubMu.Unlock()
	}))
	defer hubServer.Close()

	hubURL := strings.Replace(hubServer.URL, "http://", "ws://", 1)

	// 3. Start Host Tunnel Engine
	hostEngine := NewTunnelEngine(EngineConfig{
		HubURL:       hubURL,
		RoomCode:     "TEST-123",
		IsHost:       true,
		MyPeerID:     "peer_host",
		TargetPeerID: "peer_client",
		GamePort:     echoPort,
	})
	if err := hostEngine.Start(); err != nil {
		t.Fatalf("Host engine failed to start: %v", err)
	}
	defer hostEngine.Stop()

	// 4. Start Client Tunnel Engine
	clientEngine := NewTunnelEngine(EngineConfig{
		HubURL:       hubURL,
		RoomCode:     "TEST-123",
		IsHost:       false,
		MyPeerID:     "peer_client",
		TargetPeerID: "peer_host",
		GamePort:     0, // Dynamic port
	})
	if err := clientEngine.Start(); err != nil {
		t.Fatalf("Client engine failed to start: %v", err)
	}
	defer clientEngine.Stop()

	time.Sleep(150 * time.Millisecond) // Let connections settle

	// 5. Connect simulated Minecraft client to ClientEngine
	clientPort := clientEngine.GetListenPort()
	if clientPort == 0 {
		t.Fatalf("ClientEngine has invalid listen port 0")
	}

	gameClient, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", clientPort), 2*time.Second)
	if err != nil {
		t.Fatalf("Minecraft client failed to connect to local tunnel: %v", err)
	}
	defer gameClient.Close()

	// 6. Transmit test packet (simulating Minecraft Login / Handshake)
	testPayload := []byte("PING_MINECRAFT_P2P_PACKET_VERIFICATION_TEST")
	if _, err := gameClient.Write(testPayload); err != nil {
		t.Fatalf("Failed to write to tunnel: %v", err)
	}

	recvBuf := make([]byte, len(testPayload))
	_ = gameClient.SetReadDeadline(time.Now().Add(2 * time.Second))
	n, err := io.ReadFull(gameClient, recvBuf)
	if err != nil {
		t.Fatalf("Failed to receive echoed data through tunnel: %v", err)
	}

	if !bytes.Equal(recvBuf[:n], testPayload) {
		t.Fatalf("Echo mismatch! Got: %s, Expected: %s", string(recvBuf[:n]), string(testPayload))
	}

	t.Logf("SUCCESS: Tunnel relayed %d bytes seamlessly through WebSocket bridge!", n)
}

func TestTunnelEngineUDPEndToEnd(t *testing.T) {
	// 1. Start local UDP Echo Server (simulating Anime Fighting / ENet Game Server on host)
	udpEchoConn, err := net.ListenUDP("udp4", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
	if err != nil {
		t.Fatalf("Failed to start UDP echo server: %v", err)
	}
	defer udpEchoConn.Close()

	echoPort := udpEchoConn.LocalAddr().(*net.UDPAddr).Port

	go func() {
		buf := make([]byte, 2048)
		for {
			n, clientAddr, err := udpEchoConn.ReadFromUDP(buf)
			if err != nil {
				return
			}
			// Echo back payload to sender
			_, _ = udpEchoConn.WriteToUDP(buf[:n], clientAddr)
		}
	}()

	// 2. Start mock signaling hub
	var (
		hubConns = make(map[string]*websocket.Conn)
		hubMu    sync.Mutex
		upgrader = websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	)

	hubServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		var peerID string
		for {
			msgType, raw, err := conn.ReadMessage()
			if err != nil {
				break
			}
			if msgType == websocket.TextMessage {
				var reg struct {
					Type   string `json:"type"`
					PeerID string `json:"peerId"`
				}
				if err := json.Unmarshal(raw, &reg); err == nil && reg.Type == "tunnel_register" {
					peerID = reg.PeerID
					hubMu.Lock()
					hubConns[peerID] = conn
					hubMu.Unlock()
				}
			} else if msgType == websocket.BinaryMessage {
				if len(raw) > 1 {
					tLen := int(raw[0])
					if len(raw) >= 1+tLen {
						tID := string(raw[1 : 1+tLen])
						hubMu.Lock()
						dst := hubConns[tID]
						hubMu.Unlock()
						if dst != nil {
							_ = dst.WriteMessage(websocket.BinaryMessage, raw[1+tLen:])
						}
					}
				}
			}
		}
		hubMu.Lock()
		delete(hubConns, peerID)
		hubMu.Unlock()
	}))
	defer hubServer.Close()

	hubURL := strings.Replace(hubServer.URL, "http://", "ws://", 1)

	// 3. Start Host Tunnel Engine
	hostEngine := NewTunnelEngine(EngineConfig{
		HubURL:       hubURL,
		RoomCode:     "ANIME-999",
		IsHost:       true,
		MyPeerID:     "host_fighter",
		TargetPeerID: "client_fighter",
		GamePort:     echoPort,
	})
	if err := hostEngine.Start(); err != nil {
		t.Fatalf("Host engine failed to start: %v", err)
	}
	defer hostEngine.Stop()

	// 4. Start Client Tunnel Engine with DiscoveryPort
	discoveryPort := 27846
	clientEngine := NewTunnelEngine(EngineConfig{
		HubURL:        hubURL,
		RoomCode:      "ANIME-999",
		IsHost:        false,
		MyPeerID:      "client_fighter",
		TargetPeerID:  "host_fighter",
		GamePort:      0, // Dynamic port
		DiscoveryPort: discoveryPort,
	})
	if err := clientEngine.Start(); err != nil {
		t.Fatalf("Client engine failed to start: %v", err)
	}
	defer clientEngine.Stop()

	time.Sleep(150 * time.Millisecond)

	clientPort := clientEngine.GetUDPListenPort()
	if clientPort == 0 {
		t.Fatalf("ClientEngine has invalid UDP listen port 0")
	}

	// 5. Connect simulated Anime Fighting client via UDP
	gameClient, err := net.DialUDP("udp4", nil, &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: clientPort})
	if err != nil {
		t.Fatalf("Game client failed to dial tunnel UDP port: %v", err)
	}
	defer gameClient.Close()

	// 6. Send test ENet game datagram
	testPayload := []byte("ANIME_FIGHT_P2P_DATAGRAM_TEST_PACKET_V1")
	if _, err := gameClient.Write(testPayload); err != nil {
		t.Fatalf("Failed to send UDP datagram: %v", err)
	}

	recvBuf := make([]byte, 2048)
	_ = gameClient.SetReadDeadline(time.Now().Add(2 * time.Second))
	n, err := gameClient.Read(recvBuf)
	if err != nil {
		t.Fatalf("Failed to receive echoed UDP datagram: %v", err)
	}

	if !bytes.Equal(recvBuf[:n], testPayload) {
		t.Fatalf("UDP echo mismatch! Got: %s, Expected: %s", string(recvBuf[:n]), string(testPayload))
	}
	t.Logf("SUCCESS: Tunnel relayed %d UDP bytes across WebSocket bridge!", n)

	// 7. Test Discovery Query (simulating client searching for LAN rooms)
	if clientEngine.udpDiscoveryListener != nil {
		discSender, err := net.DialUDP("udp4", nil, &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: discoveryPort})
		if err != nil {
			t.Fatalf("Failed to dial discovery port: %v", err)
		}
		defer discSender.Close()

		_, _ = discSender.Write([]byte("ANIME_FIGHT_ROOM_SEARCH_V1"))
		discBuf := make([]byte, 256)
		_ = discSender.SetReadDeadline(time.Now().Add(2 * time.Second))
		dn, err := discSender.Read(discBuf)
		if err != nil {
			t.Fatalf("Failed to read discovery response: %v", err)
		}
		if string(discBuf[:dn]) != "ANIME_FIGHT_ROOM_READY_V1" {
			t.Fatalf("Unexpected discovery response: %s", string(discBuf[:dn]))
		}
		t.Logf("SUCCESS: Discovery responder returned %s!", string(discBuf[:dn]))
	}
}

// BenchmarkBuildFrame_BaselineMake measures the old pattern: allocating string-to-byte slices and make([]byte) on every packet
func BenchmarkBuildFrame_BaselineMake(b *testing.B) {
	targetPeerID := "peer_client_abc123"
	myPeerID := "peer_host_xyz789"
	payload := make([]byte, 1200) // typical game UDP packet size

	b.ReportAllocs()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		targetBytes := []byte(targetPeerID)
		targetLen := byte(len(targetBytes))
		myBytes := []byte(myPeerID)
		myLen := byte(len(myBytes))

		totalLen := 1 + int(targetLen) + 1 + int(myLen) + 1 + 4 + len(payload)
		buf := make([]byte, totalLen)

		buf[0] = targetLen
		copy(buf[1:1+targetLen], targetBytes)

		offset := 1 + int(targetLen)
		buf[offset] = myLen
		copy(buf[offset+1:offset+1+int(myLen)], myBytes)

		offset += 1 + int(myLen)
		buf[offset] = FrameData
		buf[offset+1] = 0
		buf[offset+2] = 0
		buf[offset+3] = 0
		buf[offset+4] = 1

		if len(payload) > 0 {
			copy(buf[offset+5:], payload)
		}
		_ = buf
	}
}

// BenchmarkBuildFrame_ZeroAlloc measures the optimized zero-alloc pattern with frameBufferPool and cached byte slices
func BenchmarkBuildFrame_ZeroAlloc(b *testing.B) {
	targetBytes := []byte("peer_client_abc123")
	myBytes := []byte("peer_host_xyz789")
	payload := make([]byte, 1200)

	b.ReportAllocs()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		totalLen := 1 + len(targetBytes) + 1 + len(myBytes) + 1 + 4 + len(payload)
		pooledBuf := frameBufferPool.Get().(*[]byte)
		buf := (*pooledBuf)[:totalLen]

		_ = buildFrame(buf, targetBytes, myBytes, FrameData, 1, payload)

		frameBufferPool.Put(pooledBuf)
	}
}

