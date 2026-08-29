package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

func (m Model) viewRadar() string {
	radarTitle := HeaderStyle.Render("📡 MAGIC LAN DISCOVERY RADAR (UDP 255.255.255.255 Broadcast Scanner)")
	desc := lipgloss.NewStyle().Foreground(ColorMuted).Render(
		"LANForge перехватывает широковещательные пакеты игр (Minecraft, Terraria, Source) и ретранслирует их всем участникам комнаты.\n" +
			"Игры видят хост во вкладке «Локальная игра» автоматически.",
	)

	var list []string
	if len(m.DiscoveredGames) == 0 {
		emptyMsg := lipgloss.JoinVertical(lipgloss.Center,
			"",
			lipgloss.NewStyle().Foreground(ColorCyan).Render("◎ Сканирование локальных широковещательных пакетов..."),
			lipgloss.NewStyle().Foreground(ColorMuted).Render("Когда хост в комнате откроет мир для сети, он сразу появится здесь."),
			"",
		)
		list = append(list, emptyMsg)
	} else {
		list = append(list, lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render("ОБНАРУЖЕННЫЕ ИГРОВЫЕ СЕРВЕРА В СЕТИ:"))
		for _, g := range m.DiscoveredGames {
			card := lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(ColorEmerald).
				Padding(0, 1).
				Render(
					fmt.Sprintf("%s\nХост: %s | Адрес: %s:%d\nMOTD: %s",
						lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(g.GameName),
						lipgloss.NewStyle().Foreground(ColorCyan).Render(g.HostNick),
						lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render(g.HostIP),
						g.Port,
						lipgloss.NewStyle().Foreground(ColorMuted).Render(g.Motd),
					),
				)
			list = append(list, card)
		}
	}

	content := lipgloss.JoinVertical(lipgloss.Left, radarTitle, desc, "\n", strings.Join(list, "\n"))
	return CardStyle.Width(m.Width - 4).Render(content)
}
