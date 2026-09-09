package upnp

import (
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Gateway represents an Internet Gateway Device (IGD) found on the local network.
type Gateway struct {
	Location    string `json:"location"`
	ControlURL  string `json:"controlUrl"`
	ServiceType string `json:"serviceType"`
	LocalIP     string `json:"localIp"`
	RouterIP    string `json:"routerIp"`
}

// XML structures for UPnP Device Description
type rootXML struct {
	XMLName xml.Name  `xml:"root"`
	Device  deviceXML `xml:"device"`
}

type deviceXML struct {
	DeviceType   string      `xml:"deviceType"`
	FriendlyName string      `xml:"friendlyName"`
	Services     []servXML   `xml:"serviceList>service"`
	Devices      []deviceXML `xml:"deviceList>device"`
}

type servXML struct {
	ServiceType string `xml:"serviceType"`
	ControlURL  string `xml:"controlURL"`
}

func findIGDService(dev deviceXML) (string, string) {
	for _, s := range dev.Services {
		st := strings.ToLower(s.ServiceType)
		if strings.Contains(st, "wanipconnection") || strings.Contains(st, "wanpppconnection") {
			return s.ServiceType, s.ControlURL
		}
	}
	for _, sub := range dev.Devices {
		if st, cu := findIGDService(sub); st != "" {
			return st, cu
		}
	}
	return "", ""
}

// DiscoverGateway scans the local network via SSDP M-SEARCH for an Internet Gateway Device.
func DiscoverGateway(timeout time.Duration) (*Gateway, error) {
	ssdpAddr, err := net.ResolveUDPAddr("udp4", "239.255.255.250:1900")
	if err != nil {
		return nil, err
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return nil, err
	}
	defer conn.Close()

	searchMsg := "M-SEARCH * HTTP/1.1\r\n" +
		"HOST: 239.255.255.250:1900\r\n" +
		"ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n" +
		"MAN: \"ssdp:discover\"\r\n" +
		"MX: 2\r\n\r\n"

	_ = conn.SetDeadline(time.Now().Add(timeout))
	if _, err := conn.WriteTo([]byte(searchMsg), ssdpAddr); err != nil {
		return nil, err
	}

	buf := make([]byte, 2048)
	var location string
	var srcAddr net.Addr

	for {
		n, src, err := conn.ReadFrom(buf)
		if err != nil {
			break
		}
		resp := string(buf[:n])
		lines := strings.Split(resp, "\r\n")
		for _, line := range lines {
			lower := strings.ToLower(line)
			if strings.HasPrefix(lower, "location:") {
				location = strings.TrimSpace(line[len("location:"):])
				srcAddr = src
				break
			}
		}
		if location != "" {
			break
		}
	}

	if location == "" {
		return nil, fmt.Errorf("no UPnP IGD response received")
	}

	// Fetch device XML description
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(location)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch IGD description from %s: %w", location, err)
	}
	defer resp.Body.Close()

	var root rootXML
	if err := xml.NewDecoder(resp.Body).Decode(&root); err != nil {
		return nil, fmt.Errorf("failed to parse IGD XML description: %w", err)
	}

	servType, ctrlPath := findIGDService(root.Device)
	if servType == "" || ctrlPath == "" {
		return nil, fmt.Errorf("no compatible WAN IP/PPP connection service in IGD description")
	}

	// Resolve absolute control URL
	locURL, err := url.Parse(location)
	if err != nil {
		return nil, err
	}
	ctrlURLRef, err := url.Parse(ctrlPath)
	if err != nil {
		return nil, err
	}
	fullCtrlURL := locURL.ResolveReference(ctrlURLRef).String()

	// Determine local IP addressing this router
	routerHost := locURL.Hostname()
	if srcUDP, ok := srcAddr.(*net.UDPAddr); ok && routerHost == "" {
		routerHost = srcUDP.IP.String()
	}

	localIP := "127.0.0.1"
	if dialConn, err := net.DialTimeout("udp4", net.JoinHostPort(routerHost, "80"), 1*time.Second); err == nil {
		if localUDP, ok := dialConn.LocalAddr().(*net.UDPAddr); ok {
			localIP = localUDP.IP.String()
		}
		_ = dialConn.Close()
	}

	return &Gateway{
		Location:    location,
		ControlURL:  fullCtrlURL,
		ServiceType: servType,
		LocalIP:     localIP,
		RouterIP:    routerHost,
	}, nil
}

// MapPort attempts to map a port on the home router using UPnP IGD.
// Returns true on successful mapping, false otherwise (without fake fallbacks).
func MapPort(port int, protocol string) bool {
	gw, err := DiscoverGateway(1200 * time.Millisecond)
	if err != nil {
		return false
	}
	err = SendSoapMapping(gw.ControlURL, gw.ServiceType, gw.LocalIP, port, protocol)
	return err == nil
}

// SendSoapMapping sends an AddPortMapping SOAP request to the control URL.
func SendSoapMapping(controlURL, serviceType, localIP string, port int, protocol string) error {
	proto := strings.ToUpper(strings.TrimSpace(protocol))
	if proto == "" {
		proto = "TCP"
	}

	body := fmt.Sprintf(`<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
<u:AddPortMapping xmlns:u="%s">
<NewRemoteHost></NewRemoteHost>
<NewExternalPort>%d</NewExternalPort>
<NewProtocol>%s</NewProtocol>
<NewInternalPort>%d</NewInternalPort>
<NewInternalClient>%s</NewInternalClient>
<NewEnabled>1</NewEnabled>
<NewPortMappingDescription>LANForge</NewPortMappingDescription>
<NewLeaseDuration>0</NewLeaseDuration>
</u:AddPortMapping>
</s:Body>
</s:Envelope>`, serviceType, port, proto, port, localIP)

	req, err := http.NewRequest("POST", controlURL, bytes.NewBufferString(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "text/xml; charset=\"utf-8\"")
	req.Header.Set("SOAPAction", fmt.Sprintf("\"%s#AddPortMapping\"", serviceType))

	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("UPnP mapping failed with HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	_, _ = io.Copy(io.Discard, resp.Body)
	return nil
}
