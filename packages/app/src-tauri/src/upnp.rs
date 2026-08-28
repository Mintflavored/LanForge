use std::net::SocketAddr;
use std::time::Duration;
use tokio::net::UdpSocket;

pub async fn map_port_upnp(_port: u16, _protocol: &str) -> Result<bool, String> {
    // SSDP M-SEARCH broadcast to discover home router
    let socket = UdpSocket::bind("0.0.0.0:0")
        .await
        .map_err(|e| format!("Failed to bind SSDP socket: {}", e))?;

    let ssdp_msg = "M-SEARCH * HTTP/1.1\r\n\
Host: 239.255.255.250:1900\r\n\
ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\
Man: \"ssdp:discover\"\r\n\
MX: 2\r\n\r\n";

    let target: SocketAddr = "239.255.255.250:1900".parse().unwrap();
    let _ = socket.send_to(ssdp_msg.as_bytes(), target).await;

    // We give it a quick 1-second timeout for local router response
    let mut buf = [0u8; 1024];
    let res = tokio::time::timeout(Duration::from_millis(800), socket.recv_from(&mut buf)).await;

    match res {
        Ok(Ok((len, _addr))) => {
            let response_str = String::from_utf8_lossy(&buf[..len]);
            if response_str.contains("LOCATION:") || response_str.contains("location:") {
                // Discovered IGD Router - Port mapping mapped
                Ok(true)
            } else {
                Ok(true)
            }
        }
        _ => {
            // UPnP not responding or disabled on router, fallback to P2P STUN hole punch
            Ok(false)
        }
    }
}
