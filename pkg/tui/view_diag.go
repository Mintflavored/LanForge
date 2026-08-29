package tui

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"
)

func (m Model) viewDiagnostics() string {
	title := HeaderStyle.Render("⚡ СЕТЕВАЯ ДИАГНОСТИКА И NAT TRAVERSAL")
	desc := lipgloss.NewStyle().Foreground(ColorMuted).Render(
		"Мониторинг STUN детекции (RFC 5389), авто-проброса портов UPnP и P2P сокетов.",
	)

	// NAT Box
	natColor := ColorEmerald
	if m.NatInfo.NatType == "Symmetric" {
		natColor = ColorRose
	} else if m.NatInfo.NatType == "PortRestricted" {
		natColor = ColorAmber
	}

	natCard := CardStyle.Width(35).Render(
		lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).Render("ТИП NAT (STUN):"),
			lipgloss.NewStyle().Bold(true).Foreground(natColor).Render(m.NatInfo.NatType),
			"",
			lipgloss.NewStyle().Foreground(ColorMuted).Render(fmt.Sprintf("Внешний IP:Port:\n%s:%d", m.NatInfo.PublicIP, m.NatInfo.PublicPort)),
		),
	)

	// UPnP Box
	upnpCard := CardStyle.Width(35).Render(
		lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorCyan).Render("UPnP / NAT-PMP IGD:"),
			lipgloss.NewStyle().Bold(true).Foreground(ColorEmerald).Render("● АВТО-ПРОБРОС АКТИВЕН"),
			"",
			lipgloss.NewStyle().Foreground(ColorMuted).Render("Порты игровых серверов автоматически открываются на домашнем роутере."),
		),
	)

	// Subnet Box
	subnetCard := CardStyle.Width(35).Render(
		lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorAmber).Render("ВИРТУАЛЬНАЯ ПОДСЕТЬ:"),
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render("10.42.0.0/24"),
			"",
			lipgloss.NewStyle().Foreground(ColorMuted).Render("Хост: 10.42.0.1\nКлиенты: 10.42.0.2..254\nMTU: 1420"),
		),
	)

	cardsRow := lipgloss.JoinHorizontal(lipgloss.Top, natCard, "  ", upnpCard, "  ", subnetCard)

	retestHint := lipgloss.NewStyle().Foreground(ColorCyan).Render("\n[ R ] Запустить повторный тест NAT и UPnP")

	return CardStyle.Width(m.Width - 4).Render(
		lipgloss.JoinVertical(lipgloss.Left, title, desc, "\n", cardsRow, retestHint),
	)
}
