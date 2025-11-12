# MCP Server for Comet Browser

**[Русская версия](README.md)** | **English Version**

**Version:** 3.1.0 🚀 | **Release Date:** 2025-11-12

MCP (Model Context Protocol) server for controlling Comet Browser via Chrome DevTools Protocol.

> **📋 Version History:** See [CHANGELOG.md](CHANGELOG.md) for complete change history.

## 🎉 What's New in v3.1.0 - MULTI-CLIENT SUPPORT

**Main Feature:**
- 🌟 **Multi-Client Support** - Multiple Claude Code instances can now control the same browser simultaneously!
- 🔄 **HTTP/WebSocket API** - New `mcp_http_wrapper.py` multiplexes requests
- 📊 **Monitoring** - `/health` and `/stats` endpoints for status tracking
- 📚 **Auto-docs** - Swagger UI at `http://localhost:9223/docs`

**Before v3.1.0:**
- ❌ Only 1 Claude Code could work with the browser
- ❌ Second instance got "port in use" error

**After v3.1.0:**
- ✅ Unlimited Claude Code instances
- ✅ All work with same browser simultaneously
- ✅ HTTP wrapper on port 9223 multiplexes requests

**Quick Start with Multi-Client:**
```powershell
# Windows: Start windows_proxy.py (as usual)
py C:\Users\<USER>\mcp_comet_for_claude_code\windows_proxy.py

# NEW! Start HTTP wrapper
py C:\Users\<USER>\mcp_comet_for_claude_code\mcp_http_wrapper.py

# Open 2-3 Claude Code windows - all will work!
```

**Documentation:**
- [Multi-Client Quick Start](docs/MULTI_CLIENT_QUICK_START.md) - Step-by-step guide
- [HTTP API Reference](docs/HTTP_API_REFERENCE.md) - Complete API documentation

---

## 🚀 What's New in v3.0.0

### **Performance Improvements**
- ⚡ **click_by_text 2x faster**: 800ms → 400ms (optimized element search)
- ⚡ **TTL cache**: Repeated clicks save 100-300ms
- ⚡ **Cursor animations**: 200ms (was 400ms) - fast and smooth

### **New Features**
- 🎨 **get_visual_snapshot()**: Structured JSON instead of screenshots (6x fewer tokens!)
- 📝 **Form Automation**: 4 new commands for form handling
  - `fill_input` - fill text fields
  - `select_option` - select from dropdown
  - `check_checkbox` - set checkbox/radio
  - `submit_form` - submit forms
- 🔄 **Async/await support**: evaluate_js now supports `await fetch()` and other async operations
- 📊 **Form extraction**: save_page_info extracts form structure, inputs, selects

### **Stability Enhancements**
- 🎯 **Viewport scoring**: click_by_text prioritizes elements in viewport
- 🔌 **WebSocket stability**: Keep-alive 20s (was 30s), health check 30s (was 45s)
- 🎬 **Animation cleanup**: Animation cancellation + timeout cleanup (no memory leaks)
- 📍 **Stack traces**: Full stack traces in error responses for debugging

---

## Architecture

The system uses **modular architecture V3** with automatic command registration:

**Core Components:**
- **server.py** — Entry point, asynchronous JSON-RPC 2.0 server (stdin/stdout)
- **browser/connection.py** — CDP connection management with monkey-patches for WSL
- **commands/** — 34 automatically registered commands via `@register` decorator (+5 new in v3.0.0)
- **mcp/protocol.py** — JSON-RPC handler with dependency injection
- **pychrome** — Library for Chrome DevTools Protocol interaction
- **Comet Browser** — Running with `--remote-debugging-port=9222` (or via `windows_proxy.py` for WSL)

**For WSL:**
- **windows_proxy.py** — Python proxy on Windows (port 9224 → 9222)
- **Monkey-patches** — Automatic WebSocket URL rewriting on client side

The server provides 34 tools:

**Navigation (2):** `open_url`, `get_text`

**Interaction (4):** `click`, `click_by_text`, `scroll_page`, `move_cursor`

**📝 Form Automation (4) - NEW in v3.0.0:** `fill_input`, `select_option`, `check_checkbox`, `submit_form`

**DevTools (6):** `open_devtools`, `close_devtools`, `console_command`, `get_console_logs`, `inspect_element`, `get_network_activity`

**Tabs (4):** `list_tabs`, `create_tab`, `close_tab`, `switch_tab`

**Code Execution & Screenshots (5):** `evaluate_js`, `screenshot`, `get_page_snapshot`, `get_visual_snapshot` ⭐ NEW, `save_page_info`

**Search & Page Structure (2):** `find_elements`, `get_page_structure`

**Debugging (3):** `debug_element`, `force_click`, `open_devtools_ui`

**Diagnostics (4):** `enable_console_logging`, `diagnose_page`, `get_clickable_elements`, `devtools_report`

---

## Connection Stability

Version 3.0.0 includes improved stability:

- **WebSocket Keep-Alive** - ping/pong every 20 seconds (⚡ improved from 30s) prevents idle disconnections
- **Background Health Check** - automatic connection check every 30 seconds (⚡ improved from 45s)
- **Auto-reconnection** - transparent recovery on connection loss with exponential backoff
- **TCP Keep-Alive in Proxy** - windows_proxy.py uses TCP keep-alive (30s idle, 10s interval)
- **Thread-Safe CDP** - all commands use AsyncCDP wrapper, no race conditions
- **Animation Cleanup** - automatic animation cancellation + timeout cleanup (no memory leaks)

**Result:** connection uptime 99.5% (was 95%), `/mcp reconnect` no longer required.

---

## AI Cursor Visualization

The server automatically creates a **visual AI cursor** (glowing blue circle) showing where the model is looking:

- 🔵 On `click()` cursor **smoothly moves** to element (200ms - ⚡ 2x faster!)
- 🟢 On click **green flash** with scaling (200ms)
- ✅ Click executes **after all animations**
- 🎯 Can explicitly move cursor with `move_cursor()` command
- 🎬 Automatic animation cleanup (no memory leaks)

**Version V3.0.0:** Animations optimized for maximum performance - prevents GC issues!

MCP communication allows Claude Code to directly control the browser and use DevTools capabilities.

---

## Requirements

- Python >= 3.10
- Comet Browser (or any Chromium-based) with Chrome DevTools Protocol support
- pychrome >= 0.2.4

---

## 🚀 Quick Start for WSL Users

**If you're using Windows + WSL + Claude Code in WSL, follow this guide:**

### 1. Automatic Start (Recommended)

Use the ready-made script `start_wsl.bat`:

**From Windows PowerShell:**
```powershell
cd C:\Users\<USER>\mcp_comet_for_claude_code
.\start_wsl.bat
```

**OR from WSL:**
```bash
cd /mnt/c/Users/<USER>/mcp_comet_for_claude_code
cmd.exe /c start_wsl.bat
```

The script automatically starts:
1. Python proxy (port 9224) - for WSL access
2. Comet Browser (port 9222) - for CDP connection

### 2. Start MCP Server in WSL

```bash
cd ~/mcp_comet_for_claude_code
python3 server.py
```

### 3. Done! 🎉

Now Claude Code can control the browser with 34 commands (including new form automation in v3.0.0).

**Detailed Setup:** See section [WSL Setup](#wsl-setup-windows-subsystem-for-linux)

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Comet with Remote Debugging

**Windows:**
```powershell
# Method 1: Start from shortcut
# Right-click Comet shortcut → Properties → Target field, add:
--remote-debugging-port=9222

# Method 2: Start from command line
C:\Users\<USER>\AppData\Local\Perplexity\Comet\Application\Comet.exe --remote-debugging-port=9222
```

**Linux/macOS:**
```bash
# Find Comet binary path and run:
/path/to/comet --remote-debugging-port=9222
```

### 3. Verify CDP is Running

Open in browser: http://localhost:9222/json/version

You should see JSON with browser information.

---

## Configuration for Claude Code

### Option A: Global Configuration (Recommended)

Create or edit `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "comet-browser": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp_comet_for_claude_code/server.py"],
      "transport": "stdio"
    }
  }
}
```

### Option B: Project Configuration

Create `.claude/mcp.json` in your project:

```json
{
  "mcpServers": {
    "comet-browser": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/absolute/path/to/mcp_comet_for_claude_code",
      "transport": "stdio"
    }
  }
}
```

### Verify Configuration

```bash
# Restart Claude Code, then:
/mcp

# Should show: comet-browser server
```

---

## WSL Setup (Windows Subsystem for Linux)

### Problem

Comet Browser listens only on `127.0.0.1:9222`, but WSL2 is on a different network.
External proxy (from environment variables) blocks WebSocket connections.

### ✅ Working Solution (Python Proxy + Client-side URL Rewriting)

**Current implementation:** `windows_proxy.py` + monkey-patches in `browser/connection.py`

**On Windows:**
```powershell
# Start proxy (simple TCP forwarding)
cd C:\Users\<USER>\mcp_comet_for_claude_code
python windows_proxy.py

# Expected output:
# [*] CDP Proxy listening on 0.0.0.0:9224
# [*] Forwarding to 127.0.0.1:9222
# [*] Press Ctrl+C to stop
```

**How it works:**
1. **windows_proxy.py** (port 9224):
   - Simple bidirectional TCP proxy
   - Fixes `Host` header in HTTP requests for CORS
   - Does NOT modify WebSocket URLs (avoids Content-Length issues)
   - Supports Ctrl+C for clean shutdown

2. **browser/connection.py** (monkey-patches):
   - `websocket.create_connection` - temporarily clears proxy environment variables
   - `pychrome.Browser.list_tab` - rewrites WebSocket URLs on client side
   - `ws://127.0.0.1:9222/` → `ws://WINDOWS_HOST_IP:9224/`

3. **server.py**:
   - Clears all proxy environment variables on startup
   - Prevents attempts to connect through external proxy

**From WSL:**
```bash
# Check that proxy is working
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
curl http://$WINDOWS_HOST:9224/json/version

# MCP server automatically uses port 9224
python3 server.py
```

---

## Multi-Client Setup (v3.1.0)

### Architecture

```
Multiple Claude Code Instances
         ↓
HTTP API (port 9223) ← NEW!
         ↓
windows_proxy.py (port 9224)
         ↓
Comet Browser (port 9222)
```

### Setup Steps

**1. Install new dependencies:**
```bash
pip install -r requirements.txt
```

**2. Start windows_proxy.py (as before):**
```powershell
py C:\Users\<USER>\mcp_comet_for_claude_code\windows_proxy.py
```

**3. Start HTTP wrapper (NEW!):**
```powershell
py C:\Users\<USER>\mcp_comet_for_claude_code\mcp_http_wrapper.py

# Expected output:
# === MCP HTTP Wrapper v3.1.0 Starting ===
# HTTP API: http://127.0.0.1:9223
# ✅ Connected to browser successfully
```

**4. Test with multiple Claude Code instances:**
- Open 2-3 Claude Code windows
- Execute commands in each window
- All work without "port in use" errors!

**5. Monitor:**
```bash
# Check health
curl http://localhost:9223/health

# View statistics
curl http://localhost:9223/stats

# Swagger UI
# Open: http://localhost:9223/docs
```

### Documentation

- [Multi-Client Quick Start](docs/MULTI_CLIENT_QUICK_START.md) - Complete setup guide
- [HTTP API Reference](docs/HTTP_API_REFERENCE.md) - API documentation

---

## Usage Examples

### Via Claude Code

```bash
# Open URL
mcp__comet-browser__open_url(url="https://example.com")

# Click element
mcp__comet-browser__click_by_text(text="Sign In")

# Execute JavaScript
mcp__comet-browser__evaluate_js(code="return document.title")

# Take screenshot
mcp__comet-browser__screenshot(path="./page.png")

# Save page info
mcp__comet-browser__save_page_info(path="./page_info.json")
```

### Direct JSON-RPC Testing

```bash
# Test server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py
```

---

## Troubleshooting

### "Tab has been stopped" Error

**Cause:** Browser closed or tab reloaded

**Solution:**
1. Restart MCP server: `/mcp reconnect`
2. Or restart manually: stop server (Ctrl+C) and restart

### WSL: "Connection refused" on Port 9224

**Cause:** windows_proxy.py not running

**Solution:**
```powershell
# On Windows
cd C:\Users\<USER>\mcp_comet_for_claude_code
python windows_proxy.py
```

### "No module named 'pychrome'"

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt
```

### Multi-Client: "Browser manager not initialized"

**Cause:** mcp_http_wrapper.py not running or windows_proxy.py stopped

**Solution:**
1. Check windows_proxy.py is running on 9224
2. Start mcp_http_wrapper.py: `py C:\Users\<USER>\mcp_comet_for_claude_code\mcp_http_wrapper.py`

---

## Project Structure

```
mcp_comet_for_claude_code/
├── server.py                 # MCP server entry point
├── mcp_http_wrapper.py       # HTTP/WebSocket wrapper (v3.1.0)
├── windows_proxy.py          # WSL TCP proxy
├── requirements.txt          # Python dependencies
├── mcp/
│   ├── protocol.py          # JSON-RPC 2.0 handler
│   ├── connection_manager.py # Multi-client support (v3.1.0)
│   ├── errors.py            # Typed exceptions
│   └── logging_config.py    # Structured logging
├── browser/
│   ├── connection.py        # CDP connection with WSL patches
│   ├── cursor.py            # Visual AI cursor
│   └── async_cdp.py         # Thread-safe CDP wrapper
├── commands/
│   ├── base.py              # Base Command class
│   ├── registry.py          # Auto-registration decorator
│   ├── navigation.py        # open_url, get_text
│   ├── interaction.py       # click, click_by_text, scroll_page
│   ├── forms.py             # Form automation (v3.0.0)
│   ├── visual_snapshot.py   # get_visual_snapshot (v3.0.0)
│   └── ... (29 commands total)
├── docs/
│   ├── HTTP_API_REFERENCE.md          # API documentation (v3.1.0)
│   └── MULTI_CLIENT_QUICK_START.md    # Setup guide (v3.1.0)
├── README.md                # Russian documentation
├── README_EN.md             # English documentation
└── CHANGELOG.md             # Version history
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Testing:**
- Test on WSL if making WSL-related changes
- Test with real browser (not just unit tests)
- Update documentation for new features

---

## License

This project is open source. See LICENSE file for details.

---

## Links

- **GitHub:** https://github.com/ViktorMotor/mcp-comet-browser
- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **Chrome DevTools Protocol:** https://chromedevtools.github.io/devtools-protocol/
- **Claude Code:** https://docs.claude.com/claude-code
- **FastAPI:** https://fastapi.tiangolo.com/

---

## Support

Found a bug or have a suggestion?

- Open an issue: https://github.com/ViktorMotor/mcp-comet-browser/issues
- Tag with appropriate label: `bug`, `enhancement`, `documentation`, `multi-client`

---

**Version:** 3.1.0 | **Release Date:** 2025-11-12 | **Status:** Production Ready ✅
