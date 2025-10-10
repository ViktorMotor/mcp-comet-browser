#!/usr/bin/env python3
"""Simple CDP proxy for Windows - fixes Host header and WebSocket URLs"""
import socket
import threading
import re
from datetime import datetime

# Listen on all interfaces (WSL can connect)
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9224

# Forward to browser on localhost
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 9222

def log(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def handle_client(client_socket, addr):
    """Handle client connection"""
    target_socket = None
    try:
        log(f"[+] Connection from {addr[0]}:{addr[1]}")

        # Connect to browser
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # STABILITY FIX: Enable TCP keep-alive to prevent idle disconnections
        target_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # Platform-specific keep-alive settings
        try:
            # Windows: Use SIO_KEEPALIVE_VALS ioctl
            # Parameters: (onoff, keepalivetime_ms, keepaliveinterval_ms)
            # keepalivetime: 30 seconds, keepaliveinterval: 10 seconds
            target_socket.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 30000, 10000))
            log("[*] TCP keep-alive enabled (Windows mode: 30s idle, 10s interval)")
        except AttributeError:
            # Linux/Unix: Use TCP socket options
            try:
                target_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                target_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                target_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                log("[*] TCP keep-alive enabled (Linux mode: 30s idle, 10s interval, 3 probes)")
            except (AttributeError, OSError) as e:
                log(f"[!] Warning: Could not set platform-specific keep-alive parameters: {e}")

        target_socket.settimeout(5)
        target_socket.connect((TARGET_HOST, TARGET_PORT))
        target_socket.settimeout(None)

        def forward(src, dst, fix_host_header=False):
            """Forward data between sockets"""
            try:
                first_chunk = fix_host_header
                while True:
                    data = src.recv(8192)
                    if not data:
                        break

                    # Fix Host header in first request chunk only
                    if first_chunk:
                        first_chunk = False
                        text = data.decode('utf-8', errors='ignore')
                        text = re.sub(r'Host: [^\r\n]+', f'Host: {TARGET_HOST}:{TARGET_PORT}', text, count=1)
                        data = text.encode('utf-8')

                    dst.sendall(data)
            except:
                pass
            finally:
                try:
                    src.shutdown(socket.SHUT_RD)
                except:
                    pass

        # Bidirectional forwarding
        # Client → Browser: fix Host header
        t1 = threading.Thread(target=forward, args=(client_socket, target_socket, True), daemon=True)
        # Browser → Client: pass through unchanged
        t2 = threading.Thread(target=forward, args=(target_socket, client_socket, False), daemon=True)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        log(f"[!] Error: {e}")
    finally:
        if target_socket:
            target_socket.close()
        client_socket.close()

def main():
    """Start proxy server"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Set timeout to allow Ctrl+C to work properly
    server.settimeout(1.0)

    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
        server.listen(5)
        log(f"[*] CDP Proxy listening on {LISTEN_HOST}:{LISTEN_PORT}")
        log(f"[*] Forwarding to {TARGET_HOST}:{TARGET_PORT}")
        log(f"[*] WebSocket URLs rewritten for WSL compatibility")
        log(f"[*] Press Ctrl+C to stop")
        print()  # Empty line for readability

        while True:
            try:
                client_socket, addr = server.accept()
                threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
            except socket.timeout:
                # Timeout is expected, just continue to check for Ctrl+C
                continue
            except OSError:
                # Socket closed, exit gracefully
                break

    except KeyboardInterrupt:
        print()  # New line after ^C
        log("[*] Shutting down gracefully...")
    except Exception as e:
        log(f"[!] Server error: {e}")
    finally:
        server.close()
        log("[*] Proxy stopped")

if __name__ == '__main__':
    main()
