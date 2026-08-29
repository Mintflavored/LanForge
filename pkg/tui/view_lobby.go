package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/lanforge/lanforge/pkg/presets"
)

func (m Model) viewLobby() string {
	if m.Client.Room == nil {
		return CardStyle.Width(m.Width - 4).Render(
			lipgloss.JoinVertical(lipgloss.Center,
				HeaderStyle.Render("⚡ ГОТОВЫ ИГРАТЬ С ДРУЗЬЯМИ ПО СЕТИ? ⚡"),
				"",
				lipgloss.NewStyle().Foreground(ColorText).Render("Создайте игровую комнату или введите 6-значный код комнаты друга:"),
				"",
				lipgloss.JoinHorizontal(lipgloss.Center,
					lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render("[ C ] Создать комнату"),
					"      ",
					lipgloss.NewStyle().Bold(true).Foreground(ColorCyan).Render("[ J ] Подключиться по коду"),
				),
				"",
				lipgloss.NewStyle().Foreground(ColorMuted).Render("Поддерживает автопоиск в локальной сети для Minecraft, Terraria, CS, Source и др."),
			),
		)
	}

	room := m.Client.Room
	hostIP := "10.42.0.1"

	// Room Info Header Banner
	gamePreset := presets.FindPreset(room.GamePreset)
	gameName := "Custom Game"
	gamePort := 25565
	if gamePreset != nil {
		gameName = gamePreset.Name
		gamePort = gamePreset.DefaultPort
	}

	roomCodeBanner := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#000000")).
		Background(ColorEmerald).
		Padding(0, 1).
		Render(" КОД: " + room.Code + " ")

	roomTitle := HeaderStyle.Render(room.Name)
	roomMeta := fmt.Sprintf("Игра: %s | Виртуальная подсеть: 10.42.0.0/24 | Игроков: %d/%d", gameName, len(room.Peers), room.MaxPeers)

	headerBox := lipgloss.JoinVertical(lipgloss.Left,
		lipgloss.JoinHorizontal(lipgloss.Center, roomCodeBanner, "  ", roomTitle),
		lipgloss.NewStyle().Foreground(ColorMuted).Render(roomMeta),
		"",
		lipgloss.NewStyle().Foreground(ColorCyan).Bold(true).Render(
			fmt.Sprintf("★ ПРЯМОЕ ПОДКЛЮЧЕНИЕ В ИГРЕ: %s:%d", hostIP, gamePort),
		),
	)

	// Peers Table / List
	var peerRows []string
	peerRows = append(peerRows, lipgloss.NewStyle().Bold(true).Foreground(ColorMuted).Render(
		fmt.Sprintf("%-16s %-16s %-10s %-10s", "НИКНЕЙМ", "ВИРТУАЛЬНЫЙ IP", "РОЛЬ", "PING"),
	))
	peerRows = append(peerRows, lipgloss.NewStyle().Foreground(ColorBorder).Render(strings.Repeat("─", 56)))

	for _, p := range room.Peers {
		roleBadge := ""
		if p.IsHost {
			roleBadge = HostBadge.Render()
		}
		if p.ID == m.Client.You.ID {
			roleBadge += " " + YouBadge.Render()
		}

		pingStr := "< 1 ms"
		pingColor := ColorEmerald
		if p.PingMs > 0 {
			pingStr = fmt.Sprintf("%d ms", p.PingMs)
			if p.PingMs > 90 {
				pingColor = ColorRose
			} else if p.PingMs > 45 {
				pingColor = ColorAmber
			}
		}
		pingBadge := lipgloss.NewStyle().Foreground(pingColor).Render(pingStr)

		row := fmt.Sprintf("%-16s %-16s %-10s %-10s",
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(p.Nick),
			lipgloss.NewStyle().Foreground(ColorCyan).Render(p.VirtualIP),
			roleBadge,
			pingBadge,
		)
		peerRows = append(peerRows, row)
	}

	peersBox := strings.Join(peerRows, "\n")

	return CardStyle.Width(m.Width - 4).Render(
		lipgloss.JoinVertical(lipgloss.Left, headerBox, "\n", peersBox),
	)
}
