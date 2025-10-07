#!/usr/bin/env python3
"""
Chrome DevTools Protocol Proxy with Host Header Fix
Fixes the issue where Chromium-based browsers reject connections from WSL2
"""
import socket
import threading
import sys
import re

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 9223
# Must connect to Windows localhost via WSL gateway IP
# because Chrome only listens on 127.0.0.1, not 0.0.0.0
TARGET_HOST = '172.23.128.1'
TARGET_PORT = 9222
# The Host header we'll send to Chrome
TARGET_HOST_HEADER = 'localhost'

def handle_client(client_socket):
    """Handle a client connection and proxy to target with header modification"""
    try:
        # Connect to target server
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.settimeout(10)
        target_socket.connect((TARGET_HOST, TARGET_PORT))

        def forward(source, destination, modify_host=False):
            """Forward data between sockets, optionally modifying Host header"""
            try:
                first_chunk = True
                while True:
                    data = source.recv(8192)
                    if not data:
                        break

                    # Only modify the first chunk (HTTP headers)
                    if modify_host and first_chunk:
                        first_chunk = False
                        try:
                            data_str = data.decode('utf-8', errors='ignore')

                            # Replace any Host header with localhost
                            # This regex catches Host: <anything>:<port>
                            data_str = re.sub(
                                r'Host: [^\r\n]+',
                                f'Host: localhost:{TARGET_PORT}',
                                data_str,
                                count=1
                            )

                            data = data_str.encode('utf-8')
                            print(f"Modified headers: {data[:200].decode('utf-8', errors='ignore')}")
                        except Exception as e:
                            print(f"Warning: Could not modify headers: {e}")

                    destination.sendall(data)
            except Exception as e:
                print(f"Forward error: {e}")
            finally:
                try:
                    source.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    destination.shutdown(socket.SHUT_RDWR)
                except:
                    pass

        # Create threads for bidirectional proxying
        client_to_server = threading.Thread(
            target=forward,
            args=(client_socket, target_socket, True),
            daemon=True
        )
        server_to_client = threading.Thread(
            target=forward,
            args=(target_socket, client_socket, False),
            daemon=True
        )

        client_to_server.start()
        server_to_client.start()

        client_to_server.join()
        server_to_client.join()

    except Exception as e:
        print(f"Error handling client: {e}", file=sys.stderr)
    finally:
        try:
            client_socket.close()
        except:
            pass

def main():
    """Main proxy server loop"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
    except OSError as e:
        print(f"Error: Cannot bind to {LISTEN_HOST}:{LISTEN_PORT}")
        print(f"Reason: {e}")
        print(f"\nMake sure port {LISTEN_PORT} is not already in use.")
        sys.exit(1)

    server.listen(5)
    print(f"✓ Chrome DevTools Proxy started")
    print(f"✓ Listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"✓ Forwarding to {TARGET_HOST}:{TARGET_PORT} (with Host header rewrite)")
    print(f"\nUsage in your code:")
    print(f"  import pychrome")
    print(f"  browser = pychrome.Browser(url='http://{LISTEN_HOST}:{LISTEN_PORT}')")
    print(f"\nOr test with:")
    print(f"  curl http://{LISTEN_HOST}:{LISTEN_PORT}/json/version")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"→ New connection from {addr}")
            client_handler = threading.Thread(
                target=handle_client,
                args=(client_socket,),
                daemon=True
            )
            client_handler.start()
    except KeyboardInterrupt:
        print("\n\n✓ Shutting down gracefully...")
    finally:
        server.close()

if __name__ == '__main__':
    main()
