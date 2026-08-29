package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"

	"github.com/lanforge/lanforge/pkg/server"
)

func main() {
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
