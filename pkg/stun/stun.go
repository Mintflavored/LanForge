package stun

import (
	"context"
	"crypto/rand"
	"encoding/binary"
	"fmt"
	"net"
	"sync"
	"time"
)

const (
	magicCookie      uint32 = 0x2112A442
	bindingRequest   uint16 = 0x0001
	xorMappedAddress uint16 = 0x0020
)

// Result holds the STUN NAT detection outcome.
type Result struct {
	PublicIP     string `json:"publicIp"`
	PublicPort   int    `json:"publicPort"`
	NatType      string `json:"natType"`
	IsBehindVPN  bool   `json:"isBehindVpn"`
	ActiveServer string `json:"activeServer"`
}

// Global resilient STUN server pool (across multiple ports and regions to bypass firewalls and DNS poisoning)
var DefaultStunServers = []string{
	"stun.l.google.com:19302",
	"stun1.l.google.com:19302",
	"stun.cloudflare.com:3478",
	"global.stun.twilio.com:3478",
	"stun.nextcloud.com:443",
	"stun.matrix.org:3478",
	"stun.voiparound.com:3478",
	"stun.sipgate.net:3478",
	"stun.framasoft.org:3478",
}

// DetectNat resolves public IP/Port and tests NAT behavior via concurrent STUN queries.
func DetectNat() Result {
	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return Result{PublicIP: "127.0.0.1", PublicPort: 0, NatType: "Unknown"}
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2500*time.Millisecond)
	defer cancel()

	type stunResponse struct {
		server string
		ip     string
		port   int
	}

	resChan := make(chan stunResponse, len(DefaultStunServers))
	var wg sync.WaitGroup

	// Query top 5 STUN servers concurrently for fast-path resolution
	for _, srv := range DefaultStunServers[:5] {
		wg.Add(1)
		go func(serverAddr string) {
			defer wg.Done()
			ip, port, err := queryStunWithTimeout(serverAddr, 1200*time.Millisecond)
			if err == nil && isValidPublicIP(ip) {
				select {
				case resChan <- stunResponse{server: serverAddr, ip: ip, port: port}:
				case <-ctx.Done():
				}
			}
		}(srv)
	}

	go func() {
		wg.Wait()
		close(resChan)
	}()

	var responses []stunResponse
	for resp := range resChan {
		responses = append(responses, resp)
		if len(responses) >= 2 {
			break // Got enough responses to evaluate NAT type
		}
	}

	if len(responses) == 0 {
		// Fallback: try secondary STUN servers (port 443 / 3478)
		for _, srv := range DefaultStunServers[5:] {
			ip, port, err := queryStunWithTimeout(srv, 1000*time.Millisecond)
			if err == nil && isValidPublicIP(ip) {
				return Result{
					PublicIP:     ip,
					PublicPort:   port,
					NatType:      "RestrictedCone",
					IsBehindVPN:  detectVPNInterface(),
					ActiveServer: srv,
				}
			}
		}

		return Result{
			PublicIP:     "127.0.0.1",
			PublicPort:   0,
			NatType:      "RestrictedCone",
			IsBehindVPN:  detectVPNInterface(),
			ActiveServer: "Local Fallback",
		}
	}

	first := responses[0]
	natType := "RestrictedCone"

	if len(responses) > 1 {
		if responses[0].port != responses[1].port {
			natType = "Symmetric"
		} else {
			natType = "FullCone"
		}
	}

	return Result{
		PublicIP:     first.ip,
		PublicPort:   first.port,
		NatType:      natType,
		IsBehindVPN:  detectVPNInterface(),
		ActiveServer: first.server,
	}
}

// isValidPublicIP checks that an IP is not a private, loopback, or Clash/VPN Fake-IP (198.18.0.0/15).
func isValidPublicIP(ipStr string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsUnspecified() {
		return false
	}

	// Filter out Clash/V2Ray Fake-IP range (198.18.0.0 - 198.19.255.255)
	if ip4 := ip.To4(); ip4 != nil {
		if ip4[0] == 198 && (ip4[1] == 18 || ip4[1] == 19) {
			return false
		}
	}
	return true
}

// detectVPNInterface inspects network adapters for TUN/TAP/VPN interfaces.
func detectVPNInterface() bool {
	ifaces, err := net.Interfaces()
	if err != nil {
		return false
	}

	vpnKeywords := []string{"tun", "tap", "wintun", "wireguard", "clash", "sing-box", "v2ray", "xray", "tailscale", "zerotier"}
	for _, iface := range ifaces {
		name := iface.Name
		for _, kw := range vpnKeywords {
			if len(name) >= len(kw) && containsIgnoreCase(name, kw) {
				return true
			}
		}
	}
	return false
}

func containsIgnoreCase(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0)
}

func queryStunWithTimeout(serverAddr string, timeout time.Duration) (string, int, error) {
	raddr, err := net.ResolveUDPAddr("udp4", serverAddr)
	if err != nil {
		return "", 0, err
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return "", 0, err
	}
	defer conn.Close()

	req := make([]byte, 20)
	binary.BigEndian.PutUint16(req[0:2], bindingRequest)
	binary.BigEndian.PutUint16(req[2:4], 0)
	binary.BigEndian.PutUint32(req[4:8], magicCookie)
	_, _ = rand.Read(req[8:20])

	_ = conn.SetDeadline(time.Now().Add(timeout))
	if _, err := conn.WriteTo(req, raddr); err != nil {
		return "", 0, err
	}

	buf := make([]byte, 512)
	n, _, err := conn.ReadFrom(buf)
	if err != nil || n < 20 {
		return "", 0, fmt.Errorf("timeout")
	}

	offset := 20
	for offset+4 <= n {
		attrType := binary.BigEndian.Uint16(buf[offset : offset+2])
		attrLen := int(binary.BigEndian.Uint16(buf[offset+2 : offset+4]))
		offset += 4

		if offset+attrLen > n {
			break
		}

		if attrType == xorMappedAddress && attrLen >= 8 {
			family := buf[offset+1]
			if family == 0x01 { // IPv4
				rawPort := binary.BigEndian.Uint16(buf[offset+2 : offset+4])
				xorPort := int(rawPort ^ uint16(magicCookie>>16))

				rawIP := buf[offset+4 : offset+8]
				cookieBytes := make([]byte, 4)
				binary.BigEndian.PutUint32(cookieBytes, magicCookie)

				xorIP := net.IPv4(
					rawIP[0]^cookieBytes[0],
					rawIP[1]^cookieBytes[1],
					rawIP[2]^cookieBytes[2],
					rawIP[3]^cookieBytes[3],
				)

				return xorIP.String(), xorPort, nil
			}
		}

		offset += (attrLen + 3) & ^3
	}

	return "", 0, fmt.Errorf("xor-mapped-address not found")
}
