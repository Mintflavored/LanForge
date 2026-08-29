package main

import (
	"flag"
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/lanforge/lanforge/pkg/tui"
)

func main() {
	serverURL := flag.String("server", "ws://localhost:8787", "Signaling server URL")
	nick := flag.String("nick", "", "Player nickname")
	flag.Parse()

	m := tui.NewModel(*serverURL, *nick)
	p := tea.NewProgram(m, tea.WithAltScreen(), tea.WithMouseCellMotion())

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running LANForge: %v\n", err)
		os.Exit(1)
	}
}
