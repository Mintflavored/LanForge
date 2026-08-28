use serde::{Deserialize, Serialize};
use std::net::{Ipv4Addr, SocketAddrV4};
use std::time::Duration;
use tokio::net::UdpSocket;

const STUN_MAGIC_COOKIE: u32 = 0x2112A442;
const BINDING_REQUEST: u16 = 0x0001;
const XOR_MAPPED_ADDRESS: u16 = 0x0020;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StunResult {
    pub public_ip: String,
    pub public_port: u16,
    pub nat_type: String,
}

pub async fn detect_nat_type() -> Result<StunResult, String> {
    let stun_servers = [
        "stun.l.google.com:19302",
        "stun1.l.google.com:19302",
        "stun.cloudflare.com:3478",
    ];

    let socket = UdpSocket::bind("0.0.0.0:0")
        .await
        .map_err(|e| format!("Failed to bind local UDP socket: {}", e))?;

    let mut first_addr: Option<SocketAddrV4> = None;

    for server in &stun_servers {
        if let Ok(addr) = resolve_and_query_stun(&socket, server).await {
            if first_addr.is_none() {
                first_addr = Some(addr);
            } else if let Some(first) = first_addr {
                // If public port changes across different destinations, it's Symmetric NAT
                if first.port() != addr.port() {
                    return Ok(StunResult {
                        public_ip: addr.ip().to_string(),
                        public_port: addr.port(),
                        nat_type: "Symmetric".to_string(),
                    });
                }
            }
        }
    }

    if let Some(addr) = first_addr {
        Ok(StunResult {
            public_ip: addr.ip().to_string(),
            public_port: addr.port(),
            nat_type: "RestrictedCone".to_string(),
        })
    } else {
        Ok(StunResult {
            public_ip: "127.0.0.1".to_string(),
            public_port: 0,
            nat_type: "Unknown".to_string(),
        })
    }
}

async fn resolve_and_query_stun(
    socket: &UdpSocket,
    server: &str,
) -> Result<SocketAddrV4, String> {
    let server_addr = tokio::net::lookup_host(server)
        .await
        .map_err(|e| format!("DNS lookup failed for {}: {}", server, e))?
        .next()
        .ok_or_else(|| "No IP found for STUN server".to_string())?;

    // Build STUN Binding Request header (20 bytes)
    let mut req = [0u8; 20];
    req[0] = (BINDING_REQUEST >> 8) as u8;
    req[1] = (BINDING_REQUEST & 0xff) as u8;
    // Message Length = 0
    req[2] = 0;
    req[3] = 0;
    // Magic Cookie (0x2112A442)
    req[4..8].copy_from_slice(&STUN_MAGIC_COOKIE.to_be_bytes());
    // 12 bytes Transaction ID
    let tid: [u8; 12] = rand::random();
    req[8..20].copy_from_slice(&tid);

    socket
        .send_to(&req, server_addr)
        .await
        .map_err(|e| format!("Send failed: {}", e))?;

    let mut buf = [0u8; 512];
    let (len, _) = tokio::time::timeout(Duration::from_millis(1500), socket.recv_from(&mut buf))
        .await
        .map_err(|_| "STUN request timed out".to_string())?
        .map_err(|e| format!("Recv error: {}", e))?;

    if len < 20 {
        return Err("STUN response too short".to_string());
    }

    // Parse attributes
    let mut offset = 20;
    while offset + 4 <= len {
        let attr_type = u16::from_be_bytes([buf[offset], buf[offset + 1]]);
        let attr_len = u16::from_be_bytes([buf[offset + 2], buf[offset + 3]]) as usize;
        offset += 4;

        if offset + attr_len > len {
            break;
        }

        if attr_type == XOR_MAPPED_ADDRESS && attr_len >= 8 {
            let family = buf[offset + 1];
            if family == 0x01 {
                // IPv4
                let raw_port = u16::from_be_bytes([buf[offset + 2], buf[offset + 3]]);
                let xor_port = raw_port ^ ((STUN_MAGIC_COOKIE >> 16) as u16);

                let mut raw_ip = [0u8; 4];
                raw_ip.copy_from_slice(&buf[offset + 4..offset + 8]);
                let cookie_bytes = STUN_MAGIC_COOKIE.to_be_bytes();
                let xor_ip = [
                    raw_ip[0] ^ cookie_bytes[0],
                    raw_ip[1] ^ cookie_bytes[1],
                    raw_ip[2] ^ cookie_bytes[2],
                    raw_ip[3] ^ cookie_bytes[3],
                ];

                return Ok(SocketAddrV4::new(Ipv4Addr::from(xor_ip), xor_port));
            }
        }

        // 4-byte boundary padding
        offset += (attr_len + 3) & !3;
    }

    Err("No XOR-MAPPED-ADDRESS found in STUN response".to_string())
}
