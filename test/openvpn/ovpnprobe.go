package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net"
	"net/textproto"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

var (
	targetHost     = flag.String("host", "", "openvpn server host")
	targetPort     = flag.Int("port", 80, "openvpn server port")
	certPath       = flag.String("cert", "", "path to client certificate and key (PEM)")
	caPath         = flag.String("ca", "", "path to server CA")
	connectTimeout = flag.Duration("timeout", 60*time.Second, "openvpn connection timeout")
	probeIP        = flag.String("test-ipaddr", "8.8.8.8", "IP address to ping")
)

func waitForConnection(ctx context.Context, mgmtSock string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	dialer := new(net.Dialer)
	c, err := dialer.DialContext(ctx, "unix", mgmtSock)
	if err != nil {
		return err
	}
	c.SetDeadline(deadline)

	conn := textproto.NewConn(c)
	defer conn.Close()

	// The way to make sure that we are always up to date with
	// OpenVPN status is to execute the 'state on all' command,
	// which will atomically dump current state and enable
	// realtime updates. So in our main loop, we first have to
	// consume the command response, and then switch to parsing
	// real-time updates.
	if err := conn.PrintfLine("state on all"); err != nil {
		return err
	}
	readingResponse := true

	for {
		line, err := conn.ReadLine()
		if err == io.EOF {
			break
		} else if err != nil {
			log.Printf("openvpn management connection error: %v", err)
			return err
		}

		if readingResponse {
			if line == "END" {
				readingResponse = false
				continue
			}
		} else {
			if !strings.HasPrefix(line, ">STATE:") {
				log.Printf("openvpn management connection: unexpected line '%s'", line)
				continue
			}
			line = line[7:]
		}

		fields := strings.Split(line, ",")
		if len(fields) < 2 {
			// Preamble, or broken state line, don't care.
			continue
		}
		log.Printf("openvpn state: %s", fields[1])
		if fields[1] == "CONNECTED" {
			return nil
		}
	}

	return errors.New("openvpn has exited while we were monitoring it")
}

func connectOpenVPN(ctx context.Context, host string, port int, certPath, caPath string) error {
	tmpdir, err := ioutil.TempDir("", "")
	if err != nil {
		return fmt.Errorf("could not create temp dir: %v", err)
	}
	mgmtSock := filepath.Join(tmpdir, "mgmt")
	defer os.RemoveAll(tmpdir)

	cmd := exec.CommandContext(
		ctx,
		"openvpn", "--nobind", "--dev", "tun", "--client",
		"--tls-client", "--remote-cert-tls", "server",
		"--tls-version-min", "1.2", "--cipher", "AES-256-GCM", "--auth", "SHA512",
		"--tls-cipher", "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384",
		"--ca", caPath, "--cert", certPath, "--key", certPath,
		"--persist-key", "--persist-local-ip",
		"--management", mgmtSock, "unix",
		"--ignore-unknown-option", "block-outside-dns",
		"--verb", "3", "--remote", host, strconv.Itoa(port), "tcp4",
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return err
	}

	// Give OpenVPN some time to start before we try to connect to
	// the management socket.
	time.Sleep(1 * time.Second)

	if err := waitForConnection(ctx, mgmtSock, *connectTimeout); err != nil {
		return err
	}

	log.Printf("connection successful")
	return nil
}

// Test the connection by running 'ping'.
func testConnection(ctx context.Context, host string) error {
	cmd := exec.CommandContext(ctx, "ping", "-c", "3", host)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func main() {
	log.SetFlags(0)
	flag.Parse()

	// Create a controlling context that can be canceled by
	// signals. Canceling the context will result in killing the
	// openvpn process.
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	go func() {
		<-sigCh
		cancel()
	}()
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	if err := connectOpenVPN(ctx, *targetHost, *targetPort, *certPath, *caPath); err != nil {
		log.Printf("test failed: %v", err)
		os.Exit(1)
	}

	if err := testConnection(ctx, *probeIP); err != nil {
		log.Printf("test connection failed: %v", err)
		os.Exit(1)
	}
}
