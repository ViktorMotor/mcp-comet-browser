# Multi-Client Quick Start Guide

**Version:** 3.1.0
**Feature:** HTTP/WebSocket Wrapper для multiple Claude Code экземпляров

---

## 🎯 Проблема

**До v3.1.0:**
- Только 1 Claude Code может работать с браузером
- Второй экземпляр получает "port in use" error
- MCP сервер = 1 процесс = 1 браузер connection

**После v3.1.0:**
- ✅ Неограниченное количество Claude Code экземпляров
- ✅ Все работают с одним браузером одновременно
- ✅ HTTP wrapper мультиплексирует запросы

---

## 🚀 Быстрый старт

### Шаг 1: Install Dependencies

```bash
cd mcp_comet_for_claude_code
pip install -r requirements.txt
```

**Новые зависимости:**
- FastAPI - HTTP framework
- uvicorn - ASGI server
- websockets - WebSocket support
- aiohttp - Async HTTP client

### Шаг 2: Запустить Comet Browser

```powershell
# Windows
C:\Users\<USER>\AppData\Local\Perplexity\Comet\Application\Comet.exe --remote-debugging-port=9222
```

### Шаг 3: Запустить windows_proxy.py

```powershell
# Windows PowerShell (как обычно)
py C:\Users\<USER>\mcp_comet_for_claude_code\windows_proxy.py
```

**Ожидаемый вывод:**
```
[*] CDP Proxy listening on 0.0.0.0:9224
[*] Forwarding to 127.0.0.1:9222
```

### Шаг 4: Запустить HTTP Wrapper (НОВОЕ!)

```powershell
# Windows PowerShell (новый терминал)
py C:\Users\<USER>\mcp_comet_for_claude_code\mcp_http_wrapper.py
```

**Ожидаемый вывод:**
```
=== MCP HTTP Wrapper v3.1.0 Starting ===
HTTP API: http://127.0.0.1:9223
CDP Proxy: 127.0.0.1:9224
✅ Connected to browser successfully
=== HTTP Wrapper Ready ===
INFO:     Uvicorn running on http://127.0.0.1:9223
```

### Шаг 5: Проверить что работает

```powershell
# Test health endpoint
curl http://localhost:9223/health
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "browser_connected": true,
  "total_clients": 0,
  "active_clients": [],
  "total_requests": 0
}
```

---

## 🧪 Тестирование Multiple Clients

### Вариант A: Через HTTP API (простой тест)

```powershell
# Terminal 1: Execute command
curl -X POST http://localhost:9223/execute `
  -H "Content-Type: application/json" `
  -d '{"method": "Page.navigate", "params": {"url": "https://example.com"}, "id": 1}'

# Terminal 2: Execute another command (одновременно!)
curl -X POST http://localhost:9223/execute `
  -H "Content-Type: application/json" `
  -d '{"method": "Page.navigate", "params": {"url": "https://google.com"}, "id": 2}'
```

### Вариант B: Через Claude Code (production test)

1. Откройте **3 окна Claude Code** одновременно
2. В каждом выполните MCP команду (например, `open_url`)
3. Все 3 должны работать без ошибок!

---

## 📊 Архитектура

```
┌─────────────────┐
│ Claude Code 1   │─┐
├─────────────────┤ │
│ Claude Code 2   │─┼──→ HTTP API (9223)
├─────────────────┤ │      │
│ Claude Code 3   │─┘      │
└─────────────────┘         │
                            ↓
                   ┌────────────────────┐
                   │ mcp_http_wrapper.py│
                   │   [FastAPI]        │
                   │ - Multiplexing     │
                   │ - ID Rewriting     │
                   │ - Shared Connection│
                   └────────┬───────────┘
                            │
                            ↓
                   ┌────────────────────┐
                   │ windows_proxy.py   │
                   │   [TCP Proxy]      │
                   │ - Port: 9224       │
                   └────────┬───────────┘
                            │
                            ↓
                   ┌────────────────────┐
                   │   Comet Browser    │
                   │   CDP Port: 9222   │
                   └────────────────────┘
```

---

## 🔍 Monitoring

### Check active clients

```powershell
curl http://localhost:9223/stats
```

**Response:**
```json
{
  "connected": true,
  "total_clients": 3,
  "active_clients": ["abc123", "def456", "ghi789"],
  "total_requests": 150,
  "failed_requests": 2,
  "success_rate": "98.67%"
}
```

### View API documentation

Открыть в браузере: http://localhost:9223/docs

FastAPI автоматически генерирует Swagger UI!

---

## ⚙️ Configuration (опционально)

Создайте `.env` файл:

```bash
# HTTP Wrapper Settings
MCP_HTTP_PORT=9223          # HTTP API port
MCP_HTTP_HOST=127.0.0.1     # Bind only localhost (security)

# CDP Proxy Settings
CDP_PROXY_HOST=127.0.0.1    # windows_proxy.py host
CDP_PROXY_PORT=9224         # windows_proxy.py port
```

---

## 🐛 Troubleshooting

### Problem: "Browser manager not initialized"

**Причина:** mcp_http_wrapper.py не смог подключиться к windows_proxy.py

**Решение:**
1. Проверьте что windows_proxy.py запущен: `curl http://localhost:9224/json/version`
2. Проверьте что Comet открыт с флагом `--remote-debugging-port=9222`

### Problem: "Connection refused" на порту 9223

**Причина:** mcp_http_wrapper.py не запущен

**Решение:**
```powershell
py mcp_http_wrapper.py
```

### Problem: Медленная работа при multiple clients

**Причина:** Request queueing (normal для heavy operations)

**Решение:** Это ожидаемое поведение - запросы выполняются последовательно для безопасности.

---

## 📝 Next Steps

1. ✅ Убедитесь что все 3 процесса запущены (Comet, windows_proxy, mcp_http_wrapper)
2. ✅ Проверьте `/health` endpoint
3. ✅ Откройте 2-3 окна Claude Code
4. ✅ Выполните команды одновременно
5. ✅ Проверьте `/stats` - должно показать multiple clients

---

## 🔄 Backward Compatibility

**Старый способ (stdio) продолжает работать!**

Если хотите использовать только 1 Claude Code:
- Запускайте только windows_proxy.py (без mcp_http_wrapper)
- Claude Code подключается напрямую к 9224

**Новый способ (HTTP) для multiple clients:**
- Запускайте windows_proxy.py + mcp_http_wrapper.py
- Claude Code подключается к 9223

---

## 📞 Support

Проблемы? Создайте Issue на GitHub:
https://github.com/your-repo/mcp_comet_for_claude_code/issues

Тег: `multi-client`, `v3.1.0`
