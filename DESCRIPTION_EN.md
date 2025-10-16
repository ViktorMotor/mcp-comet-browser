# MCP Comet Browser - Project Description (EN)

> **Browser Control via Claude Code using Model Context Protocol**

## 🎯 What is it?

**MCP Comet Browser** is a Model Context Protocol (MCP) server that enables Claude Code to directly control the Comet browser via Chrome DevTools Protocol (CDP).

Imagine your AI assistant can:
- 🌐 Open web pages
- 🖱️ Click elements with visual cursor animation
- 📸 Take screenshots (AI-optimized)
- 🔍 Inspect elements and gather page information
- 💻 Execute JavaScript code
- 🐛 Open DevTools and retrieve console logs
- 📂 Manage browser tabs

All this — **automatically**, through natural language!

## ⚡ Key Features

### 29 Commands for Browser Automation

**Navigation & Interaction:**
- `open_url` — open any URL
- `click` / `click_by_text` — smart clicks with text search
- `scroll_page` — scroll pages and elements
- `move_cursor` — visual AI cursor shows where the model is looking

**Analysis & Debugging:**
- `screenshot` — screenshots with AI optimization (JPEG Q75 = -21% size)
- `evaluate_js` — execute JavaScript with console.log capture
- `inspect_element` — detailed element information (HTML, CSS, position)
- `get_console_logs` — browser console logs
- `get_network_activity` — network requests and timings

**DevTools Integration:**
- `open_devtools` — open Chrome DevTools (F12)
- `console_command` — execute commands in console
- `diagnose_page` — comprehensive page diagnostics

**Tab Management:**
- `list_tabs` — list all open tabs
- `create_tab` / `close_tab` / `switch_tab` — full control

### 🎨 Visual AI Cursor

Unique feature — **glowing blue cursor** showing where AI is looking:

- 🔵 **Smooth movement** to element (1 second animation)
- 🟢 **Green flash** on click (1.5x scale increase, 1 second)
- ✅ Click executes **after all animations complete**
- 🎯 Animations **optimized through user testing** (V2.18)

```
User: "didn't see the green click" ❌
   ↓ Iterations V2.16 → V2.17 → V2.18
User: "Yes! I saw it now!" ✅
```

### 🚀 Architecture V2

**Modular system with auto-registration:**
- `@register` decorator — commands auto-register
- **Dependency Injection** via `CommandContext`
- **Thread-safe async CDP** wrapper
- **Structured logging** with timestamps
- **Typed exceptions** hierarchy

**Performance:**
- JSON optimization: 10KB → 3KB (**58.8% reduction**)
- WebSocket keep-alive (ping/pong every 30s)
- Background health check (every 45s)
- Auto-reconnect on connection loss

## 💻 WSL2 Support

Full **Windows Subsystem for Linux** support:

**Automatic Launch:**
```bash
.\start_wsl.bat  # Starts proxy + browser
```

**How it works:**
1. `windows_proxy.py` — Python TCP proxy (port 9224 → 9222)
2. Monkey-patches in `browser/connection.py` — rewrites WebSocket URLs
3. Auto-detection of Windows host IP from `/etc/resolv.conf`

**Alternative:** IP Helper + netsh portproxy (see SOLUTION.md)

## 📊 AI-Optimized Screenshots

**Testing with Claude 3.5 Sonnet:**

| Format | Size | Savings | Readability |
|--------|------|---------|-------------|
| PNG | 127KB | 0% | ✅ Perfect |
| JPEG Q80 | 112KB | 12% | ✅ Perfect |
| **JPEG Q75** | ~100KB | **21%** | ✅ Perfect ⭐ |
| JPEG Q60 | 85KB | 33% | ✅ Good |

**Recommendation:** `screenshot(format="jpeg", quality=75)`
- 20-30% smaller size
- Perfect readability for AI
- Faster network transfer

See [SCREENSHOT_OPTIMIZATION.md](SCREENSHOT_OPTIMIZATION.md) for details.

## 🎯 Use Cases

### Test Automation
```
Open http://localhost:4321/, navigate all pages,
check for console errors, take screenshots
```

### Web Scraping & Analysis
```
Open competitor website, find all product prices,
collect information and save to JSON
```

### UI/UX Analysis
```
Take screenshot of homepage, analyze
element layout, suggest improvements
```

### Debugging & Diagnostics
```
Open DevTools, show all console errors,
analyze network requests, find issues
```

## 🛠️ Technologies

- **Python 3.10+** — async/await, type hints
- **pychrome** — Chrome DevTools Protocol client
- **JSON-RPC 2.0** — MCP protocol (stdin/stdout)
- **Pillow** — image optimization (optional)
- **Comet Browser** — Chromium-based by Perplexity

## 📈 Project Stats

- **Version:** 2.18.1 (2025-10-16)
- **Lines of code:** ~3800 (Python)
- **Commands:** 29 tools
- **Test coverage:** 66% (542 tests)
- **Architecture:** V2 (after complete refactoring)
- **Platforms:** Linux, macOS, Windows, WSL2

## 🎉 Highlights

### ✅ What Works Great

- ✨ **0 JavaScript errors** in production (verified by QA testing)
- 🚀 **Stable connection** regardless of idle duration
- 🎨 **Beautiful animations** cursor (optimized through user testing)
- 📦 **Optimized JSON** (58.8% reduction in save_page_info)
- 🔄 **Auto-reconnect** on connection loss
- 🐛 **Production-ready** after Phase 8 bug fixes

### 🔧 Real-World Testing

**QA Report (2025-10-16):**
- Tested 5 website pages
- Used 15+ MCP commands
- 0 critical errors
- **Score:** 8/10

**Bug Discovery:**
- Unit tests (66% coverage) DIDN'T find critical bug
- Real browser testing via JSON-RPC found it in 5 minutes
- **Lesson:** Integration tests > Unit tests for browser automation

## 🌟 Why This Project?

### Alternatives & Differences

**Selenium / Playwright:**
- ❌ Complex setup
- ❌ No AI integration
- ❌ Heavy solutions

**MCP Comet Browser:**
- ✅ Works out-of-the-box with Claude Code
- ✅ Natural language control
- ✅ Visual feedback (AI cursor)
- ✅ Optimized for AI vision models
- ✅ Modular extensible architecture

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/ViktorMotor/mcp-comet-browser.git
cd mcp-comet-browser

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Comet with CDP
comet --remote-debugging-port=9222

# 4. Start MCP server
python3 server.py

# 5. Configure Claude Code (mcp_settings.json)
# See README.md for details
```

**For WSL:**
```bash
# Automatic launch (Windows)
.\start_wsl.bat

# Start MCP server (WSL)
python3 server.py
```

## 📚 Documentation

- **[README.md](README.md)** — complete installation guide
- **[CHANGELOG.md](CHANGELOG.md)** — version history (V1.0 → V2.18)
- **[.claude/CLAUDE.md](.claude/CLAUDE.md)** — detailed architecture for Claude Code
- **[SCREENSHOT_OPTIMIZATION.md](SCREENSHOT_OPTIMIZATION.md)** — optimization guide
- **[docs/](docs/)** — examples, troubleshooting, tutorials

## 🤝 Contributing

Project open for contributions:
- 🐛 Bug reports: create an Issue
- 💡 Ideas: discuss in Discussions
- 🔧 Pull Requests: welcome!

## 📄 License

**MIT License** — use freely in commercial and personal projects.

---

**Made with ❤️ for Claude Code**

🤖 Powered by Anthropic Claude 3.5 Sonnet
