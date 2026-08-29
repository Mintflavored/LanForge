package stun

import (
	"crypto/rand"
	"encoding/binary"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/lanforge/lanforge/pkg/protocol"
)

const (
	magicCookie      uint32 = 0x2112A442
	bindingRequest   uint16 = 0x0001
	xorMappedAddress uint16 = 0x0020
	mappedAddress    uint16 = 0x0001
)

// Result holds the STUN NAT detection outcome.
type Result struct {
	PublicIP     string `json:"publicIp"`
	PublicPort   int    `json:"publicPort"`
	NatType      string `json:"natType"`
	IsBehindVPN  bool   `json:"isBehindVpn"`
	ActiveServer string `json:"activeServer"`
}

// Global 100% verified, fast STUN servers
var DefaultStunServers = []string{
	"stun.l.google.com:19302",
	"stun1.l.google.com:19302",
	"stun3.l.google.com:19302",
	"stun4.l.google.com:19302",
	"stun.cloudflare.com:3478",
	"global.stun.twilio.com:3478",
	"stun.nextcloud.com:443",
	"stun.framasoft.org:3478",
	"stun.sipgate.net:3478",
}

// DetectNat resolves public IP/Port and tests NAT behavior via concurrent fast STUN queries.
func DetectNat() Result {
	type stunResponse struct {
		server string
		ip     string
		port   int
	}

	resChan := make(chan stunResponse, len(DefaultStunServers))
	var wg sync.WaitGroup

	for _, srv := range DefaultStunServers[:4] {
		wg.Add(1)
		go func(serverAddr string) {
			defer wg.Done()
			ip, port, _, err := queryStunDirect(serverAddr, 800*time.Millisecond)
			if err == nil && isValidPublicIP(ip) {
				resChan <- stunResponse{server: serverAddr, ip: ip, port: port}
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
			break
		}
	}

	if len(responses) == 0 {
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

// ProbeAllStunServers probes all configured STUN servers in parallel with ultra-fast latency benchmarking.
func ProbeAllStunServers() []protocol.StunProbeResult {
	results := make([]protocol.StunProbeResult, len(DefaultStunServers))
	var wg sync.WaitGroup

	for i, srv := range DefaultStunServers {
		wg.Add(1)
		go func(idx int, serverAddr string) {
			defer wg.Done()
			ip, _, rtt, err := queryStunDirect(serverAddr, 1000*time.Millisecond)
			if err != nil {
				results[idx] = protocol.StunProbeResult{
					Server: serverAddr,
					RTTMs:  0,
					Status: "timeout",
				}
			} else {
				results[idx] = protocol.StunProbeResult{
					Server:   serverAddr,
					RTTMs:    int(rtt.Milliseconds()),
					Status:   "ok",
					PublicIP: ip,
				}
			}
		}(i, srv)
	}

	wg.Wait()
	return results
}

func isValidPublicIP(ipStr string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsUnspecified() {
		return false
	}

	if ip4 := ip.To4(); ip4 != nil {
		if ip4[0] == 198 && (ip4[1] == 18 || ip4[1] == 19) {
			return false
		}
	}
	return true
}

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

func queryStunDirect(serverAddr string, timeout time.Duration) (string, int, time.Duration, error) {
	t0 := time.Now()

	raddr, err := net.ResolveUDPAddr("udp4", serverAddr)
	if err != nil {
		return "", 0, 0, err
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return "", 0, 0, err
	}
	defer conn.Close()

	req := make([]byte, 20)
	binary.BigEndian.PutUint16(req[0:2], bindingRequest)
	binary.BigEndian.PutUint16(req[2:4], 0)
	binary.BigEndian.PutUint32(req[4:8], magicCookie)
	_, _ = rand.Read(req[8:20])

	_ = conn.SetDeadline(time.Now().Add(timeout))

	if _, err := conn.WriteTo(req, raddr); err != nil {
		return "", 0, 0, err
	}

	buf := make([]byte, 512)
	n, _, err := conn.ReadFrom(buf)
	if err != nil || n < 20 {
		return "", 0, 0, fmt.Errorf("read timeout")
	}

	rtt := time.Since(t0)

	offset := 20
	for offset+4 <= n {
		attrType := binary.BigEndian.Uint16(buf[offset : offset+2])
		attrLen := int(binary.BigEndian.Uint16(buf[offset+2 : offset+4]))
		offset += 4

		if offset+attrLen > n {
			break
		}

		// Support both RFC 5389 (XOR-MAPPED-ADDRESS) and RFC 3489 (MAPPED-ADDRESS)
		if attrType == xorMappedAddress && attrLen >= 8 {
			family := buf[offset+1]
			if family == 0x01 {
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

				return xorIP.String(), xorPort, rtt, nil
			}
		} else if attrType == mappedAddress && attrLen >= 8 {
			family := buf[offset+1]
			if family == 0x01 {
				port := int(binary.BigEndian.Uint16(buf[offset+2 : offset+4]))
				ip := net.IPv4(buf[offset+4], buf[offset+5], buf[offset+6], buf[offset+7])
				return ip.String(), port, rtt, nil
			}
		}

		offset += (attrLen + 3) & ^3
	}

	return "", 0, rtt, fmt.Errorf("address attribute not found")
}
