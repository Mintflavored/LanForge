package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

func (m Model) viewChat() string {
	title := HeaderStyle.Render("💬 ЧАТ ИГРОВОЙ КОМНАТЫ")

	var messages []string
	if len(m.ChatHistory) == 0 {
		empty := lipgloss.NewStyle().Foreground(ColorMuted).Render("Чат пуст. Напишите сообщение и нажмите Enter...")
		messages = append(messages, empty)
	} else {
		for _, msg := range m.ChatHistory {
			timeStr := time.UnixMilli(msg.Timestamp).Format("15:04")
			isMe := msg.FromPeerID == m.Client.You.ID

			nickColor := ColorCyan
			if isMe {
				nickColor = ColorPrimary
			}

			nick := lipgloss.NewStyle().Bold(true).Foreground(nickColor).Render(msg.FromNick)
			t := lipgloss.NewStyle().Foreground(ColorMuted).Render(fmt.Sprintf("[%s]", timeStr))
			text := lipgloss.NewStyle().Foreground(ColorText).Render(msg.Text)

			messages = append(messages, fmt.Sprintf("%s %s: %s", t, nick, text))
		}
	}

	historyBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Padding(1, 2).
		Height(10).
		Width(m.Width - 8).
		Render(strings.Join(messages, "\n"))

	inputBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorPrimary).
		Padding(0, 1).
		Width(m.Width - 8).
		Render(m.ChatInput.View())

	return CardStyle.Width(m.Width - 4).Render(
		lipgloss.JoinVertical(lipgloss.Left, title, "\n", historyBox, "\n", inputBox),
	)
}
