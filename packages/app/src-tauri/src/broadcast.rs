use serde::{Deserialize, Serialize};
use socket2::{Domain, Protocol, Socket, Type};
use std::net::SocketAddr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::net::UdpSocket;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanGameDiscovery {
    pub id: String,
    pub game_name: String,
    pub host_nick: String,
    pub host_ip: String,
    pub port: u16,
    pub detected_at: u64,
    pub motd: Option<String>,
}

pub struct BroadcastManager {
    running: Arc<AtomicBool>,
}

impl BroadcastManager {
    pub fn new() -> Self {
        Self {
            running: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn start_listener(&self, _app_handle: tauri::AppHandle) -> Result<(), String> {
        if self.running.load(Ordering::SeqCst) {
            return Ok(());
        }
        self.running.store(true, Ordering::SeqCst);

        let running_clone = self.running.clone();

        tokio::spawn(async move {
            // Setup broadcast socket with SO_REUSEADDR & SO_BROADCAST
            let socket_result = (|| -> Result<UdpSocket, std::io::Error> {
                let sock = Socket::new(Domain::IPV4, Type::DGRAM, Some(Protocol::UDP))?;
                sock.set_reuse_address(true)?;
                sock.set_broadcast(true)?;
                let addr: SocketAddr = "0.0.0.0:4445".parse().unwrap();
                sock.bind(&addr.into())?;
                sock.set_nonblocking(true)?;
                UdpSocket::from_std(sock.into())
            })();

            if let Ok(socket) = socket_result {
                let mut buf = [0u8; 2048];
                while running_clone.load(Ordering::SeqCst) {
                    if let Ok((len, src)) = socket.recv_from(&mut buf).await {
                        let text = String::from_utf8_lossy(&buf[..len]);
                        // Minecraft LAN format: [MOTD]World Name[/MOTD][AD]Port[/AD]
                        if text.contains("[MOTD]") && text.contains("[/MOTD]") {
                            let motd = text
                                .split("[MOTD]")
                                .nth(1)
                                .and_then(|s| s.split("[/MOTD]").next())
                                .unwrap_or("Minecraft LAN")
                                .to_string();

                            let port_str = text
                                .split("[AD]")
                                .nth(1)
                                .and_then(|s| s.split("[/AD]").next())
                                .unwrap_or("25565");

                            let port = port_str.parse::<u16>().unwrap_or(25565);

                            let _discovery = LanGameDiscovery {
                                id: format!("mc_{}", port),
                                game_name: "Minecraft LAN World".to_string(),
                                host_nick: "Local Player".to_string(),
                                host_ip: src.ip().to_string(),
                                port,
                                detected_at: std::time::SystemTime::now()
                                    .duration_since(std::time::UNIX_EPOCH)
                                    .unwrap()
                                    .as_millis() as u64,
                                motd: Some(motd),
                            };
                        }
                    }
                }
            }
        });

        Ok(())
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
    }
}
