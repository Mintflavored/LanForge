//go:build windows
// +build windows

package tunnel

import (
	"fmt"
	"log"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"
)

const (
	k_nSteamNetworkingSend_Unreliable          = 0
	k_nSteamNetworkingSend_NoNagle             = 1
	k_nSteamNetworkingSend_UnreliableNoNagle   = 1
	k_nSteamNetworkingSend_NoDelay             = 4
	k_nSteamNetworkingSend_Reliable            = 8
	k_nSteamNetworkingSend_ReliableNoNagle     = 9

	k_ESteamNetworkingConnectionState_None                   = 0
	k_ESteamNetworkingConnectionState_Connecting             = 1
	k_ESteamNetworkingConnectionState_FindingRoute           = 2
	k_ESteamNetworkingConnectionState_Connected              = 3
	k_ESteamNetworkingConnectionState_ClosedByPeer           = 4
	k_ESteamNetworkingConnectionState_ProblemDetectedLocally = 5
)

// SteamFriend represents a friend in Steam.
type SteamFriend struct {
	SteamID  string `json:"steam_id"`
	Name     string `json:"name"`
	Online   bool   `json:"online"`
	InGame   bool   `json:"in_game"`
	InTunnel bool   `json:"in_tunnel"`
}

// SteamSelfInfo represents current user profile.
type SteamSelfInfo struct {
	SteamID string `json:"steam_id"`
	Name    string `json:"name"`
}

// SteamStatus contains complete real-time status of Steam P2P engine.
type SteamStatus struct {
	SteamRunning bool          `json:"steamRunning"`
	Initialized  bool          `json:"initialized"`
	SelfInfo     SteamSelfInfo `json:"self_info"`
	Friends      []SteamFriend `json:"friends"`
	Hosting      bool          `json:"hosting"`
	HostPort     int           `json:"hostPort"`
	ClientActive bool          `json:"clientActive"`
	ClientPort   int           `json:"clientPort"`
	TargetHostID string        `json:"targetHostId"`
	Ping         int           `json:"ping"`
	BytesUp      uint64        `json:"bytesUp"`
	BytesDown    uint64        `json:"bytesDown"`
}

type steamConn struct {
	hConn   uint32
	tcpConn net.Conn
	closed  atomic.Bool
}

func (sc *steamConn) close() {
	if sc.closed.CompareAndSwap(false, true) {
		if sc.tcpConn != nil {
			_ = sc.tcpConn.Close()
		}
	}
}

// SteamRealTimeStatus maps SteamNetConnectionRealTimeStatus_t.
type SteamRealTimeStatus struct {
	State                   int32
	Ping                    int32
	ConnectionQualityLocal  float32
	ConnectionQualityRemote float32
	OutPacketsPerSec        float32
	OutBytesPerSec          float32
	InPacketsPerSec         float32
	InBytesPerSec           float32
	SendRateBytesPerSecond  int32
	CbPendingUnreliable     int32
	CbPendingReliable       int32
	CbSentUnackedReliable   int32
	UsecQueueTime           int64
}

// SteamManager provides native Valve Steamworks P2P (SDR) tunnel capabilities.
type SteamManager struct {
	dll                  *syscall.LazyDLL
	procInit             *syscall.LazyProc
	procShutdown         *syscall.LazyProc
	procRunCallbacks     *syscall.LazyProc
	procIsSteamRunning   *syscall.LazyProc
	procSteamUser        *syscall.LazyProc
	procGetSteamID       *syscall.LazyProc
	procSteamFriends     *syscall.LazyProc
	procGetPersonaName   *syscall.LazyProc
	procGetFriendCount   *syscall.LazyProc
	procGetFriendByIndex *syscall.LazyProc
	procGetFriendName    *syscall.LazyProc
	procGetFriendState   *syscall.LazyProc
	procInviteUser       *syscall.LazyProc
	procSocketsRunCallbacks *syscall.LazyProc
	procGetConnInfo         *syscall.LazyProc
	procSockets             *syscall.LazyProc
	procUtils            *syscall.LazyProc
	procSetCallback      *syscall.LazyProc
	procCreateListen     *syscall.LazyProc
	procCloseListen      *syscall.LazyProc
	procConnectP2P       *syscall.LazyProc
	procAcceptConn       *syscall.LazyProc
	procCloseConn        *syscall.LazyProc
	procSendMsg          *syscall.LazyProc
	procRecvMsgs         *syscall.LazyProc
	procReleaseMsg       *syscall.LazyProc
	procGetRealTime      *syscall.LazyProc
	procSetSteamID64     *syscall.LazyProc
	procClearIdent       *syscall.LazyProc

	initMu      sync.Mutex
	initialized bool
	socketsPtr  uintptr
	utilsPtr    uintptr
	userPtr     uintptr
	friendsPtr  uintptr
	mySteamID   uint64
	myPersona   string

	// Active sessions
	stateMu        sync.RWMutex
	hosting        bool
	hostGamePort   int
	listenSocket   uint32
	clientActive   bool
	clientPort     int
	targetHostID   uint64
	clientListener net.Listener

	connsMu     sync.Mutex
	activeConns map[uint32]*steamConn
	stopPump    chan struct{}
	pumpRunning atomic.Bool
	lastPing    atomic.Int32
	BytesUp     atomic.Uint64
	BytesDown   atomic.Uint64
}

var (
	globalSteamMgr  *SteamManager
	globalSteamOnce sync.Once
)

// GetSteamManager returns the singleton instance of SteamManager.
func GetSteamManager() *SteamManager {
	globalSteamOnce.Do(func() {
		globalSteamMgr = newSteamManager()
	})
	return globalSteamMgr
}

func newSteamManager() *SteamManager {
	dllPath := findSteamDLL()
	dll := syscall.NewLazyDLL(dllPath)

	m := &SteamManager{
		dll:                  dll,
		procInit:             dll.NewProc("SteamAPI_InitFlat"),
		procShutdown:         dll.NewProc("SteamAPI_Shutdown"),
		procRunCallbacks:     dll.NewProc("SteamAPI_RunCallbacks"),
		procIsSteamRunning:   dll.NewProc("SteamAPI_IsSteamRunning"),
		procSteamUser:        dll.NewProc("SteamAPI_SteamUser_v023"),
		procGetSteamID:       dll.NewProc("SteamAPI_ISteamUser_GetSteamID"),
		procSteamFriends:     dll.NewProc("SteamAPI_SteamFriends_v018"),
		procGetPersonaName:   dll.NewProc("SteamAPI_ISteamFriends_GetPersonaName"),
		procGetFriendCount:   dll.NewProc("SteamAPI_ISteamFriends_GetFriendCount"),
		procGetFriendByIndex: dll.NewProc("SteamAPI_ISteamFriends_GetFriendByIndex"),
		procGetFriendName:    dll.NewProc("SteamAPI_ISteamFriends_GetFriendPersonaName"),
		procGetFriendState:   dll.NewProc("SteamAPI_ISteamFriends_GetFriendPersonaState"),
		procInviteUser:          dll.NewProc("SteamAPI_ISteamFriends_InviteUserToGame"),
		procSocketsRunCallbacks: dll.NewProc("SteamAPI_ISteamNetworkingSockets_RunCallbacks"),
		procGetConnInfo:         dll.NewProc("SteamAPI_ISteamNetworkingSockets_GetConnectionInfo"),
		procSockets:             dll.NewProc("SteamAPI_SteamNetworkingSockets_SteamAPI_v012"),
		procUtils:            dll.NewProc("SteamAPI_SteamNetworkingUtils_SteamAPI_v004"),
		procSetCallback:      dll.NewProc("SteamAPI_ISteamNetworkingUtils_SetGlobalCallback_SteamNetConnectionStatusChanged"),
		procCreateListen:     dll.NewProc("SteamAPI_ISteamNetworkingSockets_CreateListenSocketP2P"),
		procCloseListen:      dll.NewProc("SteamAPI_ISteamNetworkingSockets_CloseListenSocket"),
		procConnectP2P:       dll.NewProc("SteamAPI_ISteamNetworkingSockets_ConnectP2P"),
		procAcceptConn:       dll.NewProc("SteamAPI_ISteamNetworkingSockets_AcceptConnection"),
		procCloseConn:        dll.NewProc("SteamAPI_ISteamNetworkingSockets_CloseConnection"),
		procSendMsg:          dll.NewProc("SteamAPI_ISteamNetworkingSockets_SendMessageToConnection"),
		procRecvMsgs:         dll.NewProc("SteamAPI_ISteamNetworkingSockets_ReceiveMessagesOnConnection"),
		procReleaseMsg:       dll.NewProc("SteamAPI_SteamNetworkingMessage_t_Release"),
		procGetRealTime:      dll.NewProc("SteamAPI_ISteamNetworkingSockets_GetConnectionRealTimeStatus"),
		procSetSteamID64:     dll.NewProc("SteamAPI_SteamNetworkingIdentity_SetSteamID64"),
		procClearIdent:       dll.NewProc("SteamAPI_SteamNetworkingIdentity_Clear"),
		activeConns:          make(map[uint32]*steamConn),
		stopPump:             make(chan struct{}),
	}
	m.lastPing.Store(-1)
	return m
}

func findSteamDLL() string {
	candidates := []string{
		"steam_api64.dll",
		filepath.Join("bin", "steam-tunnel", "steam_api64.dll"),
		filepath.Join("bin", "steam_api64.dll"),
	}
	if exe, err := os.Executable(); err == nil {
		dir := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(dir, "steam_api64.dll"),
			filepath.Join(dir, "bin", "steam_api64.dll"),
			filepath.Join(dir, "bin", "steam-tunnel", "steam_api64.dll"),
		)
	}
	for _, c := range candidates {
		if fi, err := os.Stat(c); err == nil && !fi.IsDir() {
			return c
		}
	}
	return "steam_api64.dll"
}

func ensureAppID() {
	_ = os.Setenv("SteamAppId", "480")
	_ = os.Setenv("SteamGameId", "480")

	// Ensure steam_appid.txt exists in current directory and next to binary
	dirs := []string{"."}
	if exe, err := os.Executable(); err == nil {
		dirs = append(dirs, filepath.Dir(exe))
	}
	for _, d := range dirs {
		p := filepath.Join(d, "steam_appid.txt")
		if _, err := os.Stat(p); os.IsNotExist(err) {
			_ = os.WriteFile(p, []byte("480\n"), 0644)
		}
	}
}

// IsSteamRunning returns true if Steam client process is detected.
func (m *SteamManager) IsSteamRunning() bool {
	if m.procIsSteamRunning.Find() == nil {
		r, _, _ := m.procIsSteamRunning.Call()
		return r != 0
	}
	return false
}

// Init initializes the Steamworks API with AppID 480.
func (m *SteamManager) Init() error {
	m.initMu.Lock()
	defer m.initMu.Unlock()

	if m.initialized {
		return nil
	}

	ensureAppID()

	var errMsg [1024]byte
	r, _, err := m.procInit.Call(uintptr(unsafe.Pointer(&errMsg[0])))
	if r != 0 {
		return fmt.Errorf("SteamAPI_InitFlat failed (code %d): %v", r, err)
	}

	m.userPtr, _, _ = m.procSteamUser.Call()
	m.friendsPtr, _, _ = m.procSteamFriends.Call()
	m.socketsPtr, _, _ = m.procSockets.Call()
	m.utilsPtr, _, _ = m.procUtils.Call()

	// Read local SteamID
	if m.userPtr != 0 {
		steamID, _, _ := m.procGetSteamID.Call(m.userPtr)
		m.mySteamID = uint64(steamID)
	}

	// Read local persona name
	if m.friendsPtr != 0 {
		namePtr, _, _ := m.procGetPersonaName.Call(m.friendsPtr)
		if namePtr != 0 {
			var nameBytes []byte
			p := (*byte)(unsafe.Pointer(namePtr))
			for *p != 0 {
				nameBytes = append(nameBytes, *p)
				p = (*byte)(unsafe.Pointer(uintptr(unsafe.Pointer(p)) + 1))
			}
			m.myPersona = string(nameBytes)
		}
	}

	// Register global connection status callback
	cb := syscall.NewCallback(func(pInfo uintptr) uintptr {
		if pInfo == 0 {
			return 0
		}
		m.onConnectionStatusChanged(pInfo)
		return 0
	})
	m.procSetCallback.Call(m.utilsPtr, cb)

	m.initialized = true
	log.Printf("[Steam P2P] Native Valve SDR engine initialized for %s (SteamID: %d)", m.myPersona, m.mySteamID)

	// Run callbacks ticker (66 Hz)
	go func() {
		ticker := time.NewTicker(15 * time.Millisecond)
		defer ticker.Stop()
		for range ticker.C {
			m.initMu.Lock()
			init := m.initialized
			m.initMu.Unlock()
			if !init {
				return
			}
			m.procSocketsRunCallbacks.Call(m.socketsPtr)
			m.procRunCallbacks.Call()
		}
	}()

	return nil
}

func (m *SteamManager) onConnectionStatusChanged(pInfo uintptr) {
	if pInfo == 0 {
		return
	}

	hConn := *(*uint32)(unsafe.Pointer(pInfo))
	// In SteamNetConnectionStatusChangedCallback_t:
	// m_hConn: offset 0 (4 bytes)
	// padding: offset 4 (4 bytes)
	// m_info: offset 8 (SteamNetConnectionInfo_t)
	// In SteamNetConnectionInfo_t: m_eState is at offset 176 (4 bytes)
	// Therefore m_info.m_eState in callback is at offset 8 + 176 = 184
	cbState := *(*int32)(unsafe.Pointer(pInfo + 184))
	state := cbState

	// Verify via GetConnectionInfo to ensure state is accurate
	var infoBuf [1024]byte
	rInfo, _, _ := m.procGetConnInfo.Call(m.socketsPtr, uintptr(hConn), uintptr(unsafe.Pointer(&infoBuf[0])))
	if rInfo != 0 {
		infoState := *(*int32)(unsafe.Pointer(&infoBuf[176]))
		if infoState != 0 {
			state = infoState
		}
	}

	var rtStatus SteamRealTimeStatus
	m.procGetRealTime.Call(m.socketsPtr, uintptr(hConn), uintptr(unsafe.Pointer(&rtStatus)), 0, 0)
	if rtStatus.Ping >= 0 {
		m.lastPing.Store(rtStatus.Ping)
	}

	m.stateMu.RLock()
	isHost := m.hosting
	gamePort := m.hostGamePort
	m.stateMu.RUnlock()

	log.Printf("[Steam P2P] Connection #%d status event: state=%d (cbState=%d), ping=%dms", hConn, state, cbState, rtStatus.Ping)

	switch state {
	case k_ESteamNetworkingConnectionState_Connecting:
		if isHost {
			log.Printf("[Steam P2P Host] Accepting incoming peer connection #%d...", hConn)
			rAccept, _, _ := m.procAcceptConn.Call(m.socketsPtr, uintptr(hConn))
			if rAccept != 1 {
				log.Printf("[Steam P2P Host] AcceptConnection failed for #%d: result=%d", hConn, rAccept)
				m.procCloseConn.Call(m.socketsPtr, uintptr(hConn), 0, 0, 0)
				return
			}
			log.Printf("[Steam P2P Host] Accepted peer connection #%d successfully!", hConn)

			// Connect to local Minecraft server
			localAddr := fmt.Sprintf("127.0.0.1:%d", gamePort)
			tcpConn, err := net.DialTimeout("tcp", localAddr, 3*time.Second)
			if err != nil {
				log.Printf("[Steam P2P Host] Failed to dial local game on %s: %v", localAddr, err)
				m.procCloseConn.Call(m.socketsPtr, uintptr(hConn), 0, 0, 0)
				return
			}

			sc := &steamConn{hConn: hConn, tcpConn: tcpConn}
			m.connsMu.Lock()
			m.activeConns[hConn] = sc
			m.connsMu.Unlock()

			m.ensurePump()
			go m.pipeTCPToSteam(sc)
		}

	case k_ESteamNetworkingConnectionState_Connected:
		log.Printf("[Steam P2P] Connection #%d is now fully ESTABLISHED and active", hConn)

	case k_ESteamNetworkingConnectionState_ClosedByPeer, k_ESteamNetworkingConnectionState_ProblemDetectedLocally:
		m.connsMu.Lock()
		if sc, exists := m.activeConns[hConn]; exists {
			sc.close()
			delete(m.activeConns, hConn)
		}
		m.connsMu.Unlock()
		m.procCloseConn.Call(m.socketsPtr, uintptr(hConn), 0, 0, 0)
		log.Printf("[Steam P2P] Connection #%d closed.", hConn)
	}
}

// StartHost creates a P2P listen socket and routes incoming connections to local gamePort.
func (m *SteamManager) StartHost(gamePort int) error {
	if err := m.Init(); err != nil {
		return err
	}

	m.stateMu.Lock()
	defer m.stateMu.Unlock()

	if m.hosting {
		m.hostGamePort = gamePort
		log.Printf("[Steam P2P Host] Updated game port to %d", gamePort)
		return nil
	}

	// Stop any existing client session
	m.stopClientLocked()

	hListen, _, _ := m.procCreateListen.Call(m.socketsPtr, 0, 0, 0)
	if uint32(hListen) == 0 {
		return fmt.Errorf("failed to create Steam P2P listen socket")
	}

	m.listenSocket = uint32(hListen)
	m.hosting = true
	m.hostGamePort = gamePort
	log.Printf("[Steam P2P Host] Listening on Valve SDR P2P (Socket: %d) -> Local game port %d", m.listenSocket, gamePort)

	m.ensurePump()
	return nil
}

// StartClient starts a local TCP listener and dials remote hostSteamID over Steam P2P.
func (m *SteamManager) StartClient(hostSteamID uint64, localPort int) (int, error) {
	if err := m.Init(); err != nil {
		return 0, err
	}

	m.stateMu.Lock()
	defer m.stateMu.Unlock()

	// Stop existing sessions
	m.stopHostLocked()
	m.stopClientLocked()

	listenAddr := fmt.Sprintf("127.0.0.1:%d", localPort)
	l, err := net.Listen("tcp", listenAddr)
	if err != nil {
		// Fallback to dynamic port if requested port is taken
		l, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			return 0, fmt.Errorf("failed to listen on local TCP port: %w", err)
		}
	}

	actualPort := l.Addr().(*net.TCPAddr).Port
	m.clientListener = l
	m.clientActive = true
	m.clientPort = actualPort
	m.targetHostID = hostSteamID

	log.Printf("[Steam P2P Client] Listening for Minecraft on 127.0.0.1:%d -> Target Host SteamID: %d", actualPort, hostSteamID)

	m.ensurePump()

	// Accept local Minecraft connections and dial Host via Steam SDR
	go func(targetID uint64, listener net.Listener) {
		for {
			tcpConn, err := listener.Accept()
			if err != nil {
				return
			}

			log.Printf("[Steam P2P Client] Accepted game connection from %s, dialing Steam host %d...", tcpConn.RemoteAddr(), targetID)

			// Prepare SteamNetworkingIdentity
			var ident [144]byte
			m.procClearIdent.Call(uintptr(unsafe.Pointer(&ident[0])))
			m.procSetSteamID64.Call(uintptr(unsafe.Pointer(&ident[0])), uintptr(targetID))

			hConn, _, _ := m.procConnectP2P.Call(m.socketsPtr, uintptr(unsafe.Pointer(&ident[0])), 0, 0, 0)
			if uint32(hConn) == 0 {
				log.Printf("[Steam P2P Client] Failed to connect to Steam host %d", targetID)
				_ = tcpConn.Close()
				continue
			}

			sc := &steamConn{hConn: uint32(hConn), tcpConn: tcpConn}
			m.connsMu.Lock()
			m.activeConns[uint32(hConn)] = sc
			m.connsMu.Unlock()

			go m.pipeTCPToSteam(sc)
		}
	}(hostSteamID, l)

	// Start local Minecraft LAN multicast beacon so game auto-appears in Multiplayer list
	go m.startMinecraftBeacon(actualPort)

	return actualPort, nil
}

func (m *SteamManager) startMinecraftBeacon(port int) {
	addr, err := net.ResolveUDPAddr("udp4", "224.0.2.60:4445")
	if err != nil {
		return
	}
	conn, err := net.DialUDP("udp4", nil, addr)
	if err != nil {
		return
	}
	defer conn.Close()

	msg := []byte(fmt.Sprintf("[MOTD]LANForge World[/MOTD][AD]%d[/AD]", port))
	ticker := time.NewTicker(1500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.stateMu.RLock()
			active := m.clientActive
			m.stateMu.RUnlock()
			if !active {
				return
			}
			_, _ = conn.Write(msg)
		case <-m.stopPump:
			return
		}
	}
}

// pipeTCPToSteam reads from local TCP and sends via Steam SDR P2P.
func (m *SteamManager) pipeTCPToSteam(sc *steamConn) {
	defer func() {
		sc.close()
		m.connsMu.Lock()
		delete(m.activeConns, sc.hConn)
		m.connsMu.Unlock()
		m.procCloseConn.Call(m.socketsPtr, uintptr(sc.hConn), 0, 0, 0)
	}()

	buf := make([]byte, 16384)
	for {
		n, err := sc.tcpConn.Read(buf)
		if n > 0 {
			r, _, _ := m.procSendMsg.Call(
				m.socketsPtr,
				uintptr(sc.hConn),
				uintptr(unsafe.Pointer(&buf[0])),
				uintptr(uint32(n)),
				k_nSteamNetworkingSend_ReliableNoNagle,
				0,
			)
			if r != 1 {
				// Send failure: r != k_EResultOK
				log.Printf("[Steam P2P] SendMessage failed on conn #%d: result=%d", sc.hConn, r)
				return
			}
			m.BytesUp.Add(uint64(n))
		}
		if err != nil {
			return
		}
	}
}

// ensurePump starts the low-latency message receiver loop.
func (m *SteamManager) ensurePump() {
	if m.pumpRunning.CompareAndSwap(false, true) {
		m.stopPump = make(chan struct{})
		go m.pumpLoop()
	}
}

// pumpLoop reads Steam SDR messages for all active connections.
func (m *SteamManager) pumpLoop() {
	for m.pumpRunning.Load() {
		hasData := false
		m.procSocketsRunCallbacks.Call(m.socketsPtr)

		m.connsMu.Lock()
		for hConn, sc := range m.activeConns {
			var status SteamRealTimeStatus
			m.procGetRealTime.Call(m.socketsPtr, uintptr(hConn), uintptr(unsafe.Pointer(&status)), 0, 0)
			if status.Ping >= 0 {
				m.lastPing.Store(status.Ping)
			}

			if status.State == k_ESteamNetworkingConnectionState_ClosedByPeer ||
				status.State == k_ESteamNetworkingConnectionState_ProblemDetectedLocally {
				sc.close()
				delete(m.activeConns, hConn)
				m.procCloseConn.Call(m.socketsPtr, uintptr(hConn), 0, 0, 0)
				continue
			}

			// Read up to 32 messages
			var msgs [32]uintptr
			n, _, _ := m.procRecvMsgs.Call(m.socketsPtr, uintptr(hConn), uintptr(unsafe.Pointer(&msgs[0])), 32)
			if n > 0 {
				hasData = true
				for i := 0; i < int(n); i++ {
					msgPtr := msgs[i]
					if msgPtr == 0 {
						continue
					}
					pData := *(*uintptr)(unsafe.Pointer(msgPtr))
					cbSize := *(*int32)(unsafe.Pointer(msgPtr + 8))
					if cbSize > 0 && pData != 0 {
						payload := unsafe.Slice((*byte)(unsafe.Pointer(pData)), int(cbSize))
						_, _ = sc.tcpConn.Write(payload)
						m.BytesDown.Add(uint64(cbSize))
					}
					m.procReleaseMsg.Call(msgPtr)
				}
			}
		}
		m.connsMu.Unlock()

		if !hasData {
			select {
			case <-m.stopPump:
				return
			case <-time.After(1 * time.Millisecond):
			}
		}
	}
}

// Stop stops hosting and client listeners and closes all connections.
func (m *SteamManager) Stop() {
	m.stateMu.Lock()
	defer m.stateMu.Unlock()

	m.stopHostLocked()
	m.stopClientLocked()

	if m.pumpRunning.CompareAndSwap(true, false) {
		close(m.stopPump)
	}

	m.connsMu.Lock()
	for hConn, sc := range m.activeConns {
		sc.close()
		m.procCloseConn.Call(m.socketsPtr, uintptr(hConn), 0, 0, 0)
		delete(m.activeConns, hConn)
	}
	m.connsMu.Unlock()

	m.lastPing.Store(-1)
	log.Printf("[Steam P2P] Stopped all active Steam sessions.")
}

func (m *SteamManager) stopHostLocked() {
	if m.hosting {
		if m.listenSocket != 0 {
			m.procCloseListen.Call(m.socketsPtr, uintptr(m.listenSocket))
			m.listenSocket = 0
		}
		m.hosting = false
		m.hostGamePort = 0
	}
}

func (m *SteamManager) stopClientLocked() {
	if m.clientActive {
		if m.clientListener != nil {
			_ = m.clientListener.Close()
			m.clientListener = nil
		}
		m.clientActive = false
		m.clientPort = 0
		m.targetHostID = 0
	}
}

// GetStatus returns the current status, user profile, and friends list.
func (m *SteamManager) GetStatus() SteamStatus {
	st := SteamStatus{
		SteamRunning: m.IsSteamRunning(),
		Ping:         int(m.lastPing.Load()),
		BytesUp:      m.BytesUp.Load(),
		BytesDown:    m.BytesDown.Load(),
	}

	m.initMu.Lock()
	st.Initialized = m.initialized
	st.SelfInfo = SteamSelfInfo{
		SteamID: strconv.FormatUint(m.mySteamID, 10),
		Name:    m.myPersona,
	}
	friendsPtr := m.friendsPtr
	m.initMu.Unlock()

	m.stateMu.RLock()
	st.Hosting = m.hosting
	st.HostPort = m.hostGamePort
	st.ClientActive = m.clientActive
	st.ClientPort = m.clientPort
	if m.targetHostID != 0 {
		st.TargetHostID = strconv.FormatUint(m.targetHostID, 10)
	}
	m.stateMu.RUnlock()

	// Load Steam Friends if initialized
	if st.Initialized && friendsPtr != 0 {
		count, _, _ := m.procGetFriendCount.Call(friendsPtr, 0x04) // k_EFriendFlagImmediate = 0x04
		friends := make([]SteamFriend, 0, int(count))

		for i := 0; i < int(count); i++ {
			friendID, _, _ := m.procGetFriendByIndex.Call(friendsPtr, uintptr(i), 0x04)
			if friendID == 0 {
				continue
			}

			namePtr, _, _ := m.procGetFriendName.Call(friendsPtr, friendID)
			state, _, _ := m.procGetFriendState.Call(friendsPtr, friendID)

			var nameBytes []byte
			if namePtr != 0 {
				p := (*byte)(unsafe.Pointer(namePtr))
				for *p != 0 {
					nameBytes = append(nameBytes, *p)
					p = (*byte)(unsafe.Pointer(uintptr(unsafe.Pointer(p)) + 1))
				}
			}

			friends = append(friends, SteamFriend{
				SteamID:  strconv.FormatUint(uint64(friendID), 10),
				Name:     string(nameBytes),
				Online:   state > 0, // 0 = Offline
				InGame:   state == 1 || state == 3, // In-game
				InTunnel: false,
			})
		}
		st.Friends = friends
	}

	return st
}

// InviteFriend sends a game invite via Steam to the specified SteamID.
func (m *SteamManager) InviteFriend(targetSteamID uint64, connectString string) bool {
	if !m.initialized || m.friendsPtr == 0 {
		return false
	}

	cstr, err := syscall.BytePtrFromString(connectString)
	if err != nil {
		return false
	}

	r, _, _ := m.procInviteUser.Call(m.friendsPtr, uintptr(targetSteamID), uintptr(unsafe.Pointer(cstr)))
	return r != 0
}
