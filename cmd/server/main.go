package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/lanforge/lanforge/pkg/server"
)

func main() {
	port := flag.Int("port", 8787, "Port for signaling server")
	flag.Parse()

	srv := server.NewServer(*port)
	if err := srv.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}
