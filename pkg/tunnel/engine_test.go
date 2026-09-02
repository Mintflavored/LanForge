package tunnel

import (
	"bytes"
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
