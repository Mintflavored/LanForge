package tui

import "github.com/charmbracelet/lipgloss"

var (
	// Colors
	ColorPrimary   = lipgloss.Color("#818cf8") // Indigo / Purple
	ColorSecondary = lipgloss.Color("#6366f1")
	ColorCyan      = lipgloss.Color("#06b6d4")
	ColorEmerald   = lipgloss.Color("#10b981")
	ColorAmber     = lipgloss.Color("#f59e0b")
	ColorRose      = lipgloss.Color("#f43f5e")
	ColorBg        = lipgloss.Color("#0d1117")
	ColorSurface   = lipgloss.Color("#161b22")
	ColorBorder    = lipgloss.Color("#30363d")
	ColorText      = lipgloss.Color("#f3f4f6")
	ColorMuted     = lipgloss.Color("#6b7280")

	// Base Box Styles
	CardStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(ColorBorder).
			Padding(1, 2)

	ActiveCardStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(ColorPrimary).
			Padding(1, 2)

	HeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorPrimary)

	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#ffffff")).
			Background(ColorSecondary).
			Padding(0, 1)

	// Tab styles
	ActiveTabStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#ffffff")).
			Background(ColorSecondary).
			Padding(0, 2)

	InactiveTabStyle = lipgloss.NewStyle().
			Foreground(ColorMuted).
			Padding(0, 2)

	// Badges
	HostBadge = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorAmber).
			Background(lipgloss.Color("#451a03")).
			Padding(0, 1).
			SetString("HOST")

	YouBadge = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorPrimary).
			Background(lipgloss.Color("#1e1b4b")).
			Padding(0, 1).
			SetString("YOU")

	OnlineBadge = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorEmerald).
			SetString("● ONLINE")

	OfflineBadge = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorRose).
			SetString("○ OFFLINE")

	// Hotkey Bar
	HelpStyle = lipgloss.NewStyle().
			Foreground(ColorMuted).
			MarginTop(1)

	KeyStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorCyan)
)
