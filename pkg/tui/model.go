package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/lanforge/lanforge/pkg/broadcast"
	"github.com/lanforge/lanforge/pkg/client"
	"github.com/lanforge/lanforge/pkg/presets"
	"github.com/lanforge/lanforge/pkg/protocol"
	"github.com/lanforge/lanforge/pkg/stun"
	"github.com/lanforge/lanforge/pkg/upnp"
)

type Tab int

const (
	TabLobby Tab = iota
	TabPresets
	TabRadar
	TabDiagnostics
	TabChat
)

type ModalType int

const (
	ModalNone ModalType = iota
	ModalCreate
	ModalJoin
)

// Msg types for Tea loop
type ServerEventMsg protocol.ServerMessage
type DiscoveredGameMsg broadcast.DiscoveredGame
type NatResultMsg stun.Result
type TickMsg time.Time

// Model is the main Bubbletea state model for LANForge.
type Model struct {
	Client       *client.Client
	RelayManager *broadcast.RelayManager
	Width        int
	Height       int
	ActiveTab    Tab
	Modal        ModalType

	// State
	Nick            string
	ServerURL       string
	ChatHistory     []protocol.ChatMessage
	DiscoveredGames []broadcast.DiscoveredGame
	NatInfo         stun.Result
	UpnpStatus      bool
	StatusMessage   string

	// Inputs for Modals
	RoomNameInput   textinput.Model
	PresetIndex     int
	RoomPassInput   textinput.Model
	JoinCodeInput   textinput.Model
	JoinPassInput   textinput.Model
	ChatInput       textinput.Model
	PresetListIndex int
}

// NewModel constructs the initial TUI model.
func NewModel(serverURL, nick string) Model {
	if nick == "" {
		nick = fmt.Sprintf("Player_%d", time.Now().Unix()%10000)
	}

	nameIn := textinput.New()
	nameIn.Placeholder = "LAN Party Room"
	nameIn.Focus()

	passIn := textinput.New()
	passIn.Placeholder = "(Optional Password)"
	passIn.EchoMode = textinput.EchoPassword

	joinCodeIn := textinput.New()
	joinCodeIn.Placeholder = "LAN-XXXX"
	joinCodeIn.CharLimit = 8
	joinCodeIn.Focus()

	joinPassIn := textinput.New()
	joinPassIn.Placeholder = "Password if required"
	joinPassIn.EchoMode = textinput.EchoPassword

	chatIn := textinput.New()
	chatIn.Placeholder = "Type message and press Enter..."

	c := client.NewClient(serverURL)
	relay := broadcast.NewRelayManager()

	return Model{
		Client:          c,
		RelayManager:    relay,
		ActiveTab:       TabLobby,
		Nick:            nick,
		ServerURL:       serverURL,
		ChatHistory:     make([]protocol.ChatMessage, 0),
		DiscoveredGames: make([]broadcast.DiscoveredGame, 0),
		NatInfo:         stun.Result{NatType: "Testing...", PublicIP: "Resolving..."},
		UpnpStatus:      true,
		StatusMessage:   "Ready",
		RoomNameInput:   nameIn,
		RoomPassInput:   passIn,
		JoinCodeInput:   joinCodeIn,
		JoinPassInput:   joinPassIn,
		ChatInput:       chatIn,
	}
}

func (m Model) Init() tea.Cmd {
	return tea.Batch(
		m.connectCmd(),
		m.listenEventsCmd(),
		m.listenDiscoveryCmd(),
		m.detectNatCmd(),
		m.tickCmd(),
	)
}

func (m Model) connectCmd() tea.Cmd {
	return func() tea.Msg {
		_ = m.Client.Connect()
		return nil
	}
}

func (m Model) listenEventsCmd() tea.Cmd {
	return func() tea.Msg {
		if m.Client == nil || m.Client.Events == nil {
			return nil
		}
		event, ok := <-m.Client.Events
		if !ok {
			return nil
		}
		return ServerEventMsg(event)
	}
}

func (m Model) listenDiscoveryCmd() tea.Cmd {
	m.RelayManager.Start()
	ch := m.RelayManager.Subscribe()
	return func() tea.Msg {
		game, ok := <-ch
		if !ok {
			return nil
		}
		return DiscoveredGameMsg(game)
	}
}

func (m Model) detectNatCmd() tea.Cmd {
	return func() tea.Msg {
		res := stun.DetectNat()
		_ = upnp.MapPort(25565, "tcp")
		return NatResultMsg(res)
	}
}

func (m Model) tickCmd() tea.Cmd {
	return tea.Tick(1*time.Second, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Height = msg.Height

	case NatResultMsg:
		m.NatInfo = stun.Result(msg)
		m.UpnpStatus = true

	case DiscoveredGameMsg:
		game := broadcast.DiscoveredGame(msg)
		exists := false
		for _, g := range m.DiscoveredGames {
			if g.ID == game.ID {
				exists = true
				break
			}
		}
		if !exists {
			m.DiscoveredGames = append([]broadcast.DiscoveredGame{game}, m.DiscoveredGames...)
		}
		cmds = append(cmds, m.listenDiscoveryCmd())

	case ServerEventMsg:
		event := protocol.ServerMessage(msg)
		switch event.Type {
		case "room_created", "room_joined":
			m.Modal = ModalNone
			m.StatusMessage = fmt.Sprintf("Connected to room %s", event.Room.Code)
		case "chat_broadcast":
			if event.Message != nil {
				m.ChatHistory = append(m.ChatHistory, *event.Message)
			}
		case "peer_joined":
			m.StatusMessage = fmt.Sprintf("%s joined the room", event.Peer.Nick)
		case "peer_left":
			m.StatusMessage = "A player left the room"
		case "error":
			m.StatusMessage = fmt.Sprintf("Error: %s", event.ErrorMessage)
		}
		cmds = append(cmds, m.listenEventsCmd())

	case TickMsg:
		cmds = append(cmds, m.tickCmd())

	case tea.KeyMsg:
		// Modal Key Handling
		if m.Modal != ModalNone {
			return m.handleModalKeys(msg)
		}

		// Chat Input Handling when on Chat Tab
		if m.ActiveTab == TabChat && m.ChatInput.Focused() {
			if msg.Type == tea.KeyEnter {
				text := strings.TrimSpace(m.ChatInput.Value())
				if text != "" {
					_ = m.Client.SendChat(text)
					m.ChatInput.SetValue("")
				}
				return m, nil
			}
			if msg.Type == tea.KeyEsc {
				m.ChatInput.Blur()
				return m, nil
			}
			var cmd tea.Cmd
			m.ChatInput, cmd = m.ChatInput.Update(msg)
			return m, cmd
		}

		switch msg.String() {
		case "q", "ctrl+c":
			m.RelayManager.Stop()
			m.Client.Disconnect()
			return m, tea.Quit

		case "tab":
			m.ActiveTab = (m.ActiveTab + 1) % 5
			if m.ActiveTab == TabChat {
				m.ChatInput.Focus()
			} else {
				m.ChatInput.Blur()
			}

		case "shift+tab":
			if m.ActiveTab == 0 {
				m.ActiveTab = 4
			} else {
				m.ActiveTab--
			}

		case "1":
			m.ActiveTab = TabLobby
		case "2":
			m.ActiveTab = TabPresets
		case "3":
			m.ActiveTab = TabRadar
		case "4":
			m.ActiveTab = TabDiagnostics
		case "5":
			m.ActiveTab = TabChat
			m.ChatInput.Focus()

		case "c":
			m.Modal = ModalCreate
			m.RoomNameInput.Focus()

		case "j":
			m.Modal = ModalJoin
			m.JoinCodeInput.Focus()

		case "l":
			if m.Client.Room != nil {
				_ = m.Client.LeaveRoom()
				m.StatusMessage = "Left room"
			}

		case "r":
			m.StatusMessage = "Testing STUN NAT & UPnP..."
			cmds = append(cmds, m.detectNatCmd())

		case "up", "k":
			if m.ActiveTab == TabPresets && m.PresetListIndex > 0 {
				m.PresetListIndex--
			}
		case "down", "j_down":
			if m.ActiveTab == TabPresets && m.PresetListIndex < len(presets.AllPresets)-1 {
				m.PresetListIndex++
			}
		case "enter":
			if m.ActiveTab == TabPresets {
				preset := presets.AllPresets[m.PresetListIndex]
				m.Modal = ModalCreate
				m.RoomNameInput.SetValue(fmt.Sprintf("%s's %s", m.Nick, preset.Name))
				m.PresetIndex = m.PresetListIndex
			}
		}
	}

	return m, tea.Batch(cmds...)
}

func (m Model) handleModalKeys(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if msg.Type == tea.KeyEsc {
		m.Modal = ModalNone
		return m, nil
	}

	if m.Modal == ModalCreate {
		if msg.Type == tea.KeyEnter {
			presetID := presets.AllPresets[m.PresetIndex].ID
			name := strings.TrimSpace(m.RoomNameInput.Value())
			pass := strings.TrimSpace(m.RoomPassInput.Value())
			_ = m.Client.CreateRoom(name, presetID, pass, m.Nick)
			m.Modal = ModalNone
			return m, nil
		}

		var cmd1, cmd2 tea.Cmd
		m.RoomNameInput, cmd1 = m.RoomNameInput.Update(msg)
		m.RoomPassInput, cmd2 = m.RoomPassInput.Update(msg)
		return m, tea.Batch(cmd1, cmd2)
	}

	if m.Modal == ModalJoin {
		if msg.Type == tea.KeyEnter {
			code := strings.TrimSpace(m.JoinCodeInput.Value())
			pass := strings.TrimSpace(m.JoinPassInput.Value())
			if code != "" {
				_ = m.Client.JoinRoom(code, m.Nick, pass)
			}
			m.Modal = ModalNone
			return m, nil
		}

		var cmd1, cmd2 tea.Cmd
		m.JoinCodeInput, cmd1 = m.JoinCodeInput.Update(msg)
		m.JoinPassInput, cmd2 = m.JoinPassInput.Update(msg)
		return m, tea.Batch(cmd1, cmd2)
	}

	return m, nil
}

func (m Model) View() string {
	if m.Width == 0 {
		return "Initializing LANForge TUI..."
	}

	// Modal Render Overlays
	if m.Modal == ModalCreate {
		return m.viewCreateModal()
	}
	if m.Modal == ModalJoin {
		return m.viewJoinModal()
	}

	// Top App Header
	header := m.renderHeader()

	// Content based on Active Tab
	var body string
	switch m.ActiveTab {
	case TabLobby:
		body = m.viewLobby()
	case TabPresets:
		body = m.viewPresets()
	case TabRadar:
		body = m.viewRadar()
	case TabDiagnostics:
		body = m.viewDiagnostics()
	case TabChat:
		body = m.viewChat()
	}

	// Bottom Hotkeys Bar
	footer := m.renderFooter()

	return lipgloss.JoinVertical(lipgloss.Left, header, body, footer)
}

func (m Model) renderHeader() string {
	title := TitleStyle.Render(" 🎮 LANFORGE v1.0 ")
	subtitle := lipgloss.NewStyle().Foreground(ColorMuted).Render(" [P2P Virtual LAN Mesh] ")

	status := OfflineBadge.Render()
	if m.Client.Connected {
		ping := m.Client.PingRTT()
		if ping > 0 {
			status = fmt.Sprintf("%s (%d ms)", OnlineBadge.Render(), ping)
		} else {
			status = OnlineBadge.Render()
		}
	}

	tabs := []string{
		m.renderTab("1. Lobby", TabLobby),
		m.renderTab("2. Games", TabPresets),
		m.renderTab(fmt.Sprintf("3. LAN Radar (%d)", len(m.DiscoveredGames)), TabRadar),
		m.renderTab("4. Network & NAT", TabDiagnostics),
		m.renderTab(fmt.Sprintf("5. Chat (%d)", len(m.ChatHistory)), TabChat),
	}

	tabsRow := strings.Join(tabs, " ")
	headerTop := lipgloss.JoinHorizontal(lipgloss.Center, title, subtitle, "  ", status)
	return lipgloss.JoinVertical(lipgloss.Left, headerTop, tabsRow, "")
}

func (m Model) renderTab(label string, tab Tab) string {
	if m.ActiveTab == tab {
		return ActiveTabStyle.Render(label)
	}
	return InactiveTabStyle.Render(label)
}

func (m Model) renderFooter() string {
	status := lipgloss.NewStyle().Foreground(ColorAmber).Render("● " + m.StatusMessage)
	hotkeys := HelpStyle.Render(
		fmt.Sprintf("%s Create Room  |  %s Join Code  |  %s Leave  |  %s Test NAT  |  %s Switch Tab  |  %s Quit",
			KeyStyle.Render("[C]"),
			KeyStyle.Render("[J]"),
			KeyStyle.Render("[L]"),
			KeyStyle.Render("[R]"),
			KeyStyle.Render("[Tab]"),
			KeyStyle.Render("[Q]"),
		),
	)
	return lipgloss.JoinVertical(lipgloss.Left, "", status, hotkeys)
}
