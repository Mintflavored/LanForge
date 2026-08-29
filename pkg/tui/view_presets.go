package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/lanforge/lanforge/pkg/presets"
)

func (m Model) viewPresets() string {
	var rows []string

	header := HeaderStyle.Render("🕹️  КАТАЛОГ КООПЕРАТИВНЫХ ИГР (Используйте [↑/↓] для выбора, [Enter] создать комнату):")
	rows = append(rows, header, "")

	for i, preset := range presets.AllPresets {
		cursor := "  "
		itemStyle := lipgloss.NewStyle().Foreground(ColorText)

		if i == m.PresetListIndex {
			cursor = "▶ "
			itemStyle = lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).Background(lipgloss.Color("#1e1b4b"))
		}

		discBadge := lipgloss.NewStyle().Foreground(ColorMuted).Render("[Direct IP]")
		if preset.LanDiscoverySupported {
			discBadge = lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render("[Auto LAN Broadcast]")
		}

		row := fmt.Sprintf("%s%-30s %-10s %-12s %s",
			cursor,
			itemStyle.Render(preset.Name),
			lipgloss.NewStyle().Foreground(ColorCyan).Render(fmt.Sprintf("%s:%d", strings.ToUpper(preset.Protocol), preset.DefaultPort)),
			lipgloss.NewStyle().Foreground(ColorAmber).Render(preset.Category),
			discBadge,
		)
		rows = append(rows, row)
	}

	selectedPreset := presets.AllPresets[m.PresetListIndex]
	details := CardStyle.BorderForeground(ColorPrimary).Render(
		lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).Render(selectedPreset.Name),
			lipgloss.NewStyle().Foreground(ColorMuted).Render(selectedPreset.Description),
			"",
			lipgloss.NewStyle().Foreground(ColorCyan).Render("Подключение: "+selectedPreset.ConnectHint),
		),
	)

	listContent := strings.Join(rows, "\n")
	return CardStyle.Width(m.Width - 4).Render(
		lipgloss.JoinVertical(lipgloss.Left, listContent, "\n", details),
	)
}
