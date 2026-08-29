package tui

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"
	"github.com/lanforge/lanforge/pkg/presets"
)

func (m Model) viewCreateModal() string {
	title := TitleStyle.Render(" 🚀 СОЗДАНИЕ ИГРОВОЙ КОМНАТЫ ")
	selectedPreset := presets.AllPresets[m.PresetIndex]

	nameField := fmt.Sprintf("Название комнаты:\n%s", m.RoomNameInput.View())
	presetField := fmt.Sprintf("Выбранная игра: %s (%s:%d)",
		lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render(selectedPreset.Name),
		selectedPreset.Protocol,
		selectedPreset.DefaultPort,
	)
	passField := fmt.Sprintf("Пароль (опционально):\n%s", m.RoomPassInput.View())

	hints := lipgloss.NewStyle().Foreground(ColorMuted).Render("\n[ Enter ] Создать комнату  |  [ Esc ] Отмена")

	modalContent := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		nameField,
		"",
		presetField,
		"",
		passField,
		hints,
	)

	return lipgloss.Place(m.Width, m.Height,
		lipgloss.Center, lipgloss.Center,
		ActiveCardStyle.Width(50).Render(modalContent),
	)
}

func (m Model) viewJoinModal() string {
	title := TitleStyle.Render(" 🔑 ПОДКЛЮЧЕНИЕ К КОМНАТЕ ПО КОДУ ")

	codeField := fmt.Sprintf("Код комнаты (6 знаков, например LAN-9X4K):\n%s", m.JoinCodeInput.View())
	passField := fmt.Sprintf("Пароль комнаты (если требуется):\n%s", m.JoinPassInput.View())

	hints := lipgloss.NewStyle().Foreground(ColorMuted).Render("\n[ Enter ] Войти в комнату  |  [ Esc ] Отмена")

	modalContent := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		codeField,
		"",
		passField,
		hints,
	)

	return lipgloss.Place(m.Width, m.Height,
		lipgloss.Center, lipgloss.Center,
		ActiveCardStyle.Width(50).Render(modalContent),
	)
}
