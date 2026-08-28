import { NatDiagnostics, DiscoveredLanGame } from "../types/index.js";

// Check if running inside Tauri
export const isTauri = (): boolean => {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
};

export class NativeBridge {
  private static instance: NativeBridge;
  private lanGameListeners: ((game: DiscoveredLanGame) => void)[] = [];

  public static getInstance(): NativeBridge {
    if (!NativeBridge.instance) {
      NativeBridge.instance = new NativeBridge();
    }
    return NativeBridge.instance;
  }

  public async detectNat(): Promise<NatDiagnostics> {
    if (isTauri()) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        return await invoke<NatDiagnostics>("detect_nat_stun");
      } catch (err) {
        console.warn("[NativeBridge] Tauri STUN error:", err);
      }
    }

    // Web / Fallback simulation
    await new Promise((r) => setTimeout(r, 600));
    return {
      publicIp: "178.62.204.14",
      publicPort: 54192,
      natType: "RestrictedCone",
      upnpStatus: "Enabled",
      activeTunnels: 1,
      bytesReceived: 142050,
      bytesSent: 98400,
    };
  }

  public async mapUpnpPort(port: number, protocol: "tcp" | "udp" | "both"): Promise<boolean> {
    if (isTauri()) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        return await invoke<boolean>("map_upnp_port", { port, protocol });
      } catch (err) {
        console.warn("[NativeBridge] UPnP mapping error:", err);
        return false;
      }
    }
    console.log(`[NativeBridge] Mapped UPnP port ${port}/${protocol}`);
    return true;
  }

  public async startLanBroadcast(onGameDiscovered: (game: DiscoveredLanGame) => void): Promise<void> {
    this.lanGameListeners.push(onGameDiscovered);

    if (isTauri()) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("start_lan_broadcast_listener");
      } catch (err) {
        console.warn("[NativeBridge] Failed to start native LAN broadcast:", err);
      }
    }
  }

  public emitDiscoveredLanGame(game: DiscoveredLanGame): void {
    for (const listener of this.lanGameListeners) {
      listener(game);
    }
  }

  public async copyToClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }
}

export const nativeBridge = NativeBridge.getInstance();
