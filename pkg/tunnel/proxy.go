package tunnel

import (
	"fmt"
	"io"
	"net"
	"sync"
)

// GameProxy manages TCP/UDP port forwarding between virtual IP and localhost.
type GameProxy struct {
	listeners map[int]net.Listener
	mu        sync.Mutex
	running   bool
}

// NewGameProxy creates a new game proxy.
func NewGameProxy() *GameProxy {
	return &GameProxy{
		listeners: make(map[int]net.Listener),
	}
}

// ForwardTCP starts a local TCP proxy for a game port (e.g. 25565 or 7777).
func (p *GameProxy) ForwardTCP(localPort int, targetAddr string) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	l, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", localPort))
	if err != nil {
		return err
	}
	p.listeners[localPort] = l

	go func() {
		for {
			conn, err := l.Accept()
			if err != nil {
				break
			}

			go func(src net.Conn) {
				defer src.Close()
				dst, err := net.Dial("tcp", targetAddr)
				if err != nil {
					return
				}
				defer dst.Close()

				errc := make(chan error, 2)
				go func() {
					_, err := io.Copy(dst, src)
					errc <- err
				}()
				go func() {
					_, err := io.Copy(src, dst)
					errc <- err
				}()
				<-errc
			}(conn)
		}
	}()

	return nil
}

// CloseAll closes all active proxy forwarders.
func (p *GameProxy) CloseAll() {
	p.mu.Lock()
	defer p.mu.Unlock()
	for _, l := range p.listeners {
		_ = l.Close()
	}
	p.listeners = make(map[int]net.Listener)
}
