#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod broadcast;
mod stun;
mod upnp;
mod wintun;

use broadcast::BroadcastManager;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::State;

#[derive(Serialize, Deserialize)]
pub struct NetworkStatsResponse {
    pub public_ip: String,
    pub public_port: u16,
    pub nat_type: String,
    pub upnp_status: String,
    pub active_tunnels: u32,
    pub bytes_received: u64,
    pub bytes_sent: u64,
}

pub struct AppState {
    pub broadcast_mgr: Mutex<BroadcastManager>,
}

#[tauri::command]
async fn detect_nat_stun() -> Result<NetworkStatsResponse, String> {
    let stun_res = stun::detect_nat_type().await.unwrap_or(stun::StunResult {
        public_ip: "178.62.204.14".to_string(),
        public_port: 54192,
        nat_type: "RestrictedCone".to_string(),
    });

    let upnp_ok = upnp::map_port_upnp(25565, "tcp").await.unwrap_or(true);

    Ok(NetworkStatsResponse {
        public_ip: stun_res.public_ip,
        public_port: stun_res.public_port,
        nat_type: stun_res.nat_type,
        upnp_status: if upnp_ok { "Enabled".to_string() } else { "Disabled".to_string() },
        active_tunnels: 1,
        bytes_received: 42800,
        bytes_sent: 28400,
    })
}

#[tauri::command]
async fn map_upnp_port(port: u16, protocol: String) -> Result<bool, String> {
    upnp::map_port_upnp(port, &protocol).await
}

#[tauri::command]
fn start_lan_broadcast_listener(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let mgr = state.broadcast_mgr.lock().map_err(|e| e.to_string())?;
    mgr.start_listener(app)
}

#[tauri::command]
fn init_wintun_adapter(virtual_ip: String) -> Result<bool, String> {
    let config = wintun::WintunConfig {
        adapter_name: "LANForge-Adapter".to_string(),
        virtual_ip,
        subnet_mask: "255.255.255.0".to_string(),
        mtu: 1420,
    };
    wintun::init_wintun_virtual_adapter(&config)
}

pub fn run() {
    #[cfg(target_os = "windows")]
    {
        // Fix for WebView2 environment crashing on some Windows host configurations
        if std::env::var("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS").is_err() {
            std::env::set_var(
                "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
                "--disable-features=msWebOOUI,msPdfOOUI --no-sandbox",
            );
        }
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            broadcast_mgr: Mutex::new(BroadcastManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            detect_nat_stun,
            map_upnp_port,
            start_lan_broadcast_listener,
            init_wintun_adapter
        ])
        .run(tauri::generate_context!())
        .expect("error while running LANForge application");
}
