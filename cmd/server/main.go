package main

import (
	"flag"
	"fmt"
	"os"
	"runtime/debug"
	"strconv"
	"time"

	"github.com/lanforge/lanforge/pkg/server"
)

func main() {
	// Ограничение кучи Go и ускоренный сбор мусора для минимизации RAM
	debug.SetMemoryLimit(16 * 1024 * 1024) // 16 МБ мягкий лимит
	debug.SetGCPercent(50)                 // Более ранний запуск сборщика мусора

	// Фоновый возврат неиспользуемых страниц ОС Windows
	go func() {
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			debug.FreeOSMemory()
		}
	}()

	defaultPort := 8787
	if envPort := os.Getenv("PORT"); envPort != "" {
		if p, err := strconv.Atoi(envPort); err == nil && p > 0 {
			defaultPort = p
		}
	}

	port := flag.Int("port", defaultPort, "Port for signaling server")
	flag.Parse()

	srv := server.NewServer(*port)
	if err := srv.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}
