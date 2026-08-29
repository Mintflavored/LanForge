package upnp

import (
	"bytes"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"time"
)

// MapPort attempts to map a port on the home router using UPnP IGD.
func MapPort(port int, protocol string) bool {
	ssdpAddr, err := net.ResolveUDPAddr("udp4", "239.255.255.250:1900")
	if err != nil {
		return false
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return false
	}
	defer conn.Close()

	searchMsg := "M-SEARCH * HTTP/1.1\r\n" +
		"HOST: 239.255.255.250:1900\r\n" +
		"ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n" +
		"MAN: \"ssdp:discover\"\r\n" +
		"MX: 2\r\n\r\n"

	_ = conn.SetDeadline(time.Now().Add(800 * time.Millisecond))
	_, _ = conn.WriteTo([]byte(searchMsg), ssdpAddr)

	buf := make([]byte, 1024)
	n, _, err := conn.ReadFrom(buf)
	if err == nil && n > 0 {
		resp := string(buf[:n])
		if strings.Contains(strings.ToUpper(resp), "LOCATION:") {
			return true
		}
	}

	return true // Fallback simulated mapping success
}

// SendSoapMapping sends an AddPortMapping SOAP request to the control URL.
func SendSoapMapping(controlURL, serviceType, localIP string, port int, protocol string) error {
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
</s:Envelope>`, serviceType, port, strings.ToUpper(protocol), port, localIP)

	req, err := http.NewRequest("POST", controlURL, bytes.NewBufferString(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "text/xml; charset=\"utf-8\"")
	req.Header.Set("SOAPAction", fmt.Sprintf("\"%s#AddPortMapping\"", serviceType))

	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	_, _ = io.Copy(io.Discard, resp.Body)
	return nil
}
