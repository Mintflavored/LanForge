package upnp

import (
	"encoding/xml"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestFindIGDService(t *testing.T) {
	mockXML := `<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <device>
    <deviceType>urn:schemas-upnp-org:device:InternetGatewayDevice:1</deviceType>
    <friendlyName>Test Router</friendlyName>
    <deviceList>
      <device>
        <deviceType>urn:schemas-upnp-org:device:WANDevice:1</deviceType>
        <deviceList>
          <device>
            <deviceType>urn:schemas-upnp-org:device:WANConnectionDevice:1</deviceType>
            <serviceList>
              <service>
                <serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>
                <controlURL>/ctl/IPConn</controlURL>
              </service>
            </serviceList>
          </device>
        </deviceList>
      </device>
    </deviceList>
  </device>
</root>`

	var root rootXML
	if err := xml.NewDecoder(strings.NewReader(mockXML)).Decode(&root); err != nil {
		t.Fatalf("failed to decode XML: %v", err)
	}

	st, cu := findIGDService(root.Device)
	if st != "urn:schemas-upnp-org:service:WANIPConnection:1" {
		t.Fatalf("unexpected service type: %s", st)
	}
	if cu != "/ctl/IPConn" {
		t.Fatalf("unexpected control URL: %s", cu)
	}
}

func TestSendSoapMapping(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("expected POST, got %s", r.Method)
		}
		body, _ := io.ReadAll(r.Body)
		bodyStr := string(body)
		if !strings.Contains(bodyStr, "<NewExternalPort>25565</NewExternalPort>") {
			t.Errorf("missing port in SOAP request: %s", bodyStr)
		}
		if !strings.Contains(bodyStr, "<NewProtocol>TCP</NewProtocol>") {
			t.Errorf("missing protocol in SOAP request: %s", bodyStr)
		}

		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:AddPortMappingResponse xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"/></s:Body></s:Envelope>`))
	}))
	defer server.Close()

	err := SendSoapMapping(server.URL, "urn:schemas-upnp-org:service:WANIPConnection:1", "192.168.1.50", 25565, "TCP")
	if err != nil {
		t.Fatalf("SendSoapMapping failed: %v", err)
	}
}
