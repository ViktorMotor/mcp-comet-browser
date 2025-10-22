#!/usr/bin/env python3
"""
Simple CDP proxy for Windows - fixes Host header and WebSocket URLs

USAGE:
    python windows_proxy.py              # Normal mode (only connections)
    python windows_proxy.py -v           # Verbose Level 1 (filtered, recommended)
    python windows_proxy.py --verbose 2  # Verbose Level 2 (detailed)
    python windows_proxy.py --verbose 3  # Verbose Level 3 (full dump)

VERBOSE LEVELS:
    Level 1: Tool calls only (RECOMMENDED)
        - Shows ONLY browser actions: clicks, navigation, screenshots
        - Connection handshake (GET /json, WebSocket)
        - Clean and readable output
        - Perfect for monitoring Claude Code's browser interactions

    Level 2: Tool calls + CDP responses
        - All from Level 1
        - CDP command responses (success/error)
        - JavaScript evaluation previews
        - Console and exception events

    Level 3: Full dump (debug only)
        - Everything including all CDP internal events
        - Network traffic, frame events, execution contexts
        - Use only for deep protocol debugging

WHAT YOU'LL SEE (Level 1):
    🌐 Navigate to: https://example.com
    🖱️  Move cursor
    🖱️  Click element
    🔍 Query DOM
    📸 Take screenshot

See VERBOSE_PROXY_GUIDE.md for detailed documentation.
"""
import socket
import threading
import re
import json
import sys
from datetime import datetime

# Listen on all interfaces (WSL can connect)
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9224

# Forward to browser on localhost
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 9222

# Global verbose flag (set from command line)
VERBOSE = False
VERBOSE_LEVEL = 1  # 1 = tool calls only, 2 = +responses, 3 = all

# Request tracking for matching requests to responses
request_tracker = {}  # id -> description

def log(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def log_verbose(message):
    """Print verbose message (only if VERBOSE=True)"""
    if VERBOSE:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [VERBOSE] {message}")

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

        def forward(src, dst, fix_host_header=False, direction=""):
            """Forward data between sockets with optional verbose logging"""
            try:
                first_chunk = fix_host_header
                chunk_count = 0
                while True:
                    data = src.recv(8192)
                    if not data:
                        break

                    chunk_count += 1

                    # Fix Host header in first request chunk only
                    if first_chunk:
                        first_chunk = False
                        text = data.decode('utf-8', errors='ignore')
                        text = re.sub(r'Host: [^\r\n]+', f'Host: {TARGET_HOST}:{TARGET_PORT}', text, count=1)
                        data = text.encode('utf-8')

                    # Verbose logging: try to decode and show traffic
                    if VERBOSE:
                        try:
                            # Try to decode as text (HTTP/JSON-RPC)
                            text = data.decode('utf-8', errors='ignore')

                            # Level 3: Show everything (old behavior)
                            if VERBOSE_LEVEL >= 3:
                                if text.startswith('GET ') or text.startswith('POST ') or text.startswith('HTTP/'):
                                    lines = text.split('\n', 3)
                                    log_verbose(f"{direction} HTTP: {lines[0].strip()} ({len(data)} bytes)")
                                elif text.strip().startswith('{') and text.strip().endswith('}'):
                                    try:
                                        parsed = json.loads(text.strip())
                                        if 'method' in parsed:
                                            log_verbose(f"{direction} CDP Event: {parsed['method']} ({len(data)} bytes)")
                                        elif 'id' in parsed and 'result' in parsed:
                                            log_verbose(f"{direction} CDP Response: id={parsed['id']} ({len(data)} bytes)")
                                        elif 'id' in parsed and 'error' in parsed:
                                            log_verbose(f"{direction} CDP Error: id={parsed['id']} ({len(data)} bytes)")
                                        else:
                                            log_verbose(f"{direction} JSON data ({len(data)} bytes)")
                                    except:
                                        log_verbose(f"{direction} JSON fragment ({len(data)} bytes)")
                                else:
                                    log_verbose(f"{direction} Data ({len(data)} bytes)")
                            else:
                                # Level 1-2: ONLY show MCP tool calls (the useful stuff!)
                                # Check if it's HTTP handshake (connection debug)
                                if text.startswith('GET /json') or text.startswith('GET /devtools'):
                                    lines = text.split('\n', 1)
                                    log_verbose(f"{direction} {lines[0].strip()}")
                                elif text.startswith('HTTP/1.1 101'):
                                    log_verbose(f"{direction} WebSocket connected")
                                # Check for CDP commands (evaluate, click, etc)
                                elif text.strip().startswith('{') and text.strip().endswith('}'):
                                    try:
                                        parsed = json.loads(text.strip())
                                        # Check if it's a CDP command we care about
                                        if 'method' in parsed and 'params' in parsed:
                                            method = parsed['method']
                                            params = parsed.get('params', {})
                                            req_id = parsed.get('id')
                                            description = None

                                            # Runtime.evaluate = tool execution
                                            if method == 'Runtime.evaluate':
                                                expr = params.get('expression', '')
                                                # Try to extract tool name from expression
                                                if 'window.__moveAICursor__' in expr:
                                                    description = "🖱️  Move cursor"
                                                elif 'window.__clickAICursor__' in expr:
                                                    description = "🖱️  Click animation"
                                                elif '.click()' in expr:
                                                    description = "🖱️  Click element"
                                                elif 'document.querySelector' in expr and len(expr) < 200:
                                                    description = "🔍 Query DOM"
                                                elif 'window.location' in expr:
                                                    description = "🌐 Navigate"
                                                elif VERBOSE_LEVEL >= 2:
                                                    # Level 2: show expression preview
                                                    preview = expr[:60].replace('\n', ' ')
                                                    description = f"📝 Evaluate: {preview}..."
                                            # Page.navigate = open_url
                                            elif method == 'Page.navigate':
                                                url = params.get('url', 'unknown')
                                                description = f"🌐 Navigate to: {url}"
                                            # Page.captureScreenshot = screenshot
                                            elif method == 'Page.captureScreenshot':
                                                description = "📸 Take screenshot"
                                            # Important CDP events (Level 2)
                                            elif VERBOSE_LEVEL >= 2 and method in ['Runtime.consoleAPICalled', 'Runtime.exceptionThrown']:
                                                description = f"CDP Event: {method}"

                                            # Log and track request
                                            if description:
                                                log_verbose(f"{direction} {description}")
                                                if req_id:
                                                    request_tracker[req_id] = description

                                        # Show responses for tracked requests
                                        elif 'id' in parsed:
                                            req_id = parsed['id']
                                            if req_id in request_tracker:
                                                description = request_tracker.pop(req_id)
                                                if 'result' in parsed:
                                                    log_verbose(f"{direction}   ✅ Success: {description}")
                                                elif 'error' in parsed:
                                                    error_msg = parsed.get('error', {}).get('message', 'Unknown')
                                                    log_verbose(f"{direction}   ❌ Error: {description} - {error_msg}")
                                            elif VERBOSE_LEVEL >= 2:
                                                # Level 2: show all responses
                                                if 'result' in parsed:
                                                    log_verbose(f"{direction}   ✅ Response: id={req_id}")
                                                elif 'error' in parsed:
                                                    log_verbose(f"{direction}   ❌ Error: id={req_id}")
                                    except:
                                        pass  # Ignore malformed JSON
                        except:
                            pass  # Ignore binary data

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
        t1 = threading.Thread(target=forward, args=(client_socket, target_socket, True, "WSL→Browser"), daemon=True)
        # Browser → Client: pass through unchanged
        t2 = threading.Thread(target=forward, args=(target_socket, client_socket, False, "Browser→WSL"), daemon=True)

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
    global VERBOSE, VERBOSE_LEVEL

    # Parse command line arguments
    if '--verbose' in sys.argv or '-v' in sys.argv:
        VERBOSE = True
        # Check for verbose level
        for i, arg in enumerate(sys.argv):
            if arg in ('--verbose', '-v') and i + 1 < len(sys.argv):
                try:
                    level = int(sys.argv[i + 1])
                    if 1 <= level <= 3:
                        VERBOSE_LEVEL = level
                except ValueError:
                    pass

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
        if VERBOSE:
            level_desc = {
                1: "tool calls only (clicks, navigation, screenshots)",
                2: "tool calls + CDP responses",
                3: "full dump (all CDP events)"
            }
            log(f"[*] VERBOSE MODE: Level {VERBOSE_LEVEL} - {level_desc[VERBOSE_LEVEL]}")
        log(f"[*] Press Ctrl+C to stop")
        if not VERBOSE:
            log(f"[*] Tip: Use --verbose to see browser tool calls")
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
