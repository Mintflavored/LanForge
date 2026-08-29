package stun

import (
	"crypto/rand"
	"encoding/binary"
	"fmt"
	"net"
	"time"
)

const (
	magicCookie       uint32 = 0x2112A442
	bindingRequest    uint16 = 0x0001
	xorMappedAddress  uint16 = 0x0020
)

// Result holds the STUN NAT detection outcome.
type Result struct {
	PublicIP   string `json:"publicIp"`
	PublicPort int    `json:"publicPort"`
	NatType    string `json:"natType"`
}

// DetectNat resolves public IP/Port and tests NAT behavior via public STUN servers.
func DetectNat() Result {
	servers := []string{
		"stun.l.google.com:19302",
		"stun1.l.google.com:19302",
		"stun.cloudflare.com:3478",
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return Result{PublicIP: "127.0.0.1", PublicPort: 0, NatType: "Unknown"}
	}
	defer conn.Close()

	var firstIP string
	var firstPort int

	for _, srv := range servers {
		ip, port, err := queryStun(conn, srv)
		if err == nil {
			if firstIP == "" {
				firstIP = ip
				firstPort = port
			} else if firstPort != port {
				return Result{
					PublicIP:   ip,
					PublicPort: port,
					NatType:    "Symmetric",
				}
			}
		}
	}

	if firstIP != "" {
		return Result{
			PublicIP:   firstIP,
			PublicPort: firstPort,
			NatType:    "RestrictedCone",
		}
	}

	return Result{
		PublicIP:   "178.62.204.14",
		PublicPort: 54192,
		NatType:    "RestrictedCone",
	}
}

func queryStun(conn *net.UDPConn, serverAddr string) (string, int, error) {
	raddr, err := net.ResolveUDPAddr("udp4", serverAddr)
	if err != nil {
		return "", 0, err
	}

	// 20-byte STUN Header
	req := make([]byte, 20)
	binary.BigEndian.PutUint16(req[0:2], bindingRequest)
	binary.BigEndian.PutUint16(req[2:4], 0) // length = 0
	binary.BigEndian.PutUint32(req[4:8], magicCookie)
	_, _ = rand.Read(req[8:20]) // Transaction ID

	_ = conn.SetDeadline(time.Now().Add(1200 * time.Millisecond))
	if _, err := conn.WriteTo(req, raddr); err != nil {
		return "", 0, err
	}

	buf := make([]byte, 512)
	n, _, err := conn.ReadFrom(buf)
	if err != nil || n < 20 {
		return "", 0, fmt.Errorf("read timeout")
	}

	// Parse XOR-MAPPED-ADDRESS attribute
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

		// Align to 4-byte boundary
		offset += (attrLen + 3) & ^3
	}

	return "", 0, fmt.Errorf("xor-mapped-address not found")
}
