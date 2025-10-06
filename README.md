# MCP Server for Comet Browser

MCP (Model Context Protocol) сервер для управления браузером Comet через Chrome DevTools Protocol.

## Архитектура

Система состоит из трех компонентов:
- **server.py** — асинхронный JSON-RPC 2.0 сервер, работающий через stdin/stdout
- **pychrome** — библиотека для взаимодействия с Chrome DevTools Protocol (CDP)
- **Comet Browser** — запущен с флагом `--remote-debugging-port=9222`

Сервер предоставляет 5 методов: `open_url`, `get_text`, `click`, `screenshot`, `evaluate_js`.
Коммуникация через MCP позволяет Claude Code напрямую управлять браузером.

## Требования

- Python >= 3.10
- Браузер Comet (или любой Chromium-based) с поддержкой Chrome DevTools Protocol
- pychrome >= 0.2.4

## Установка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Запустите Comet с remote debugging

**Windows:**
```cmd
"C:\Path\To\Comet.exe" --remote-debugging-port=9222
```

Для Comet (Perplexity):
```cmd
"C:\Users\<USERNAME>\AppData\Local\Perplexity\Comet\Application\Comet.exe" --remote-debugging-port=9222
```

**Linux:**
```bash
comet --remote-debugging-port=9222
# или
chromium --remote-debugging-port=9222
```

**macOS:**
```bash
/Applications/Comet.app/Contents/MacOS/Comet --remote-debugging-port=9222
```

### 2.1. Настройка для WSL (Windows Subsystem for Linux)

Если вы используете WSL и Claude Code запущен в Linux-окружении, необходимо настроить проброс портов:

**Шаг 1: Настройте брандмауэр Windows**

В Windows PowerShell от администратора выполните:
```powershell
New-NetFirewallRule -DisplayName "Chrome Debug Port" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
```

**Шаг 2: Настройте проброс портов**

В Windows PowerShell от администратора выполните:
```powershell
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1
```

Проверить настройку можно командой:
```powershell
netsh interface portproxy show all
```

**Шаг 3: Проверка из WSL**

В WSL терминале выполните:
```bash
curl http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):9222/json/version
```

Должен вернуться JSON с информацией о браузере.

**Примечание:** `server.py` автоматически определяет IP Windows хоста из `/etc/resolv.conf` и подключается к нему.

### 3. Проверьте окружение

```bash
python check_env.py
```

Вы должны увидеть:
```
============================================================
MCP Comet Browser - Environment Check
============================================================

✓ Python 3.10.x (required: >= 3.10)
✓ pychrome is installed (version: 0.2.4)
✓ Chrome DevTools Protocol is accessible on port 9222
  Browser: Chrome/120.0.6099.109

============================================================
✓ All checks passed! Environment is ready.
============================================================
```

## Подключение к Claude Code

### Вариант 1: Через файл конфигурации Claude Code

Добавьте в `~/.config/claude/config.json` (Linux/macOS) или `%APPDATA%\Claude\config.json` (Windows):

```json
{
  "mcpServers": {
    "comet-browser": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/home/admsrv/mcp_comet_for_claude_code",
      "transport": "stdio"
    }
  }
}
```

### Вариант 2: Использование mcp.json

Скопируйте `mcp.json` в директорию конфигурации Claude Code или укажите путь к серверу вручную.

### 3. Перезапустите Claude Code

После добавления конфигурации перезапустите Claude Code для загрузки MCP-сервера.

## Тестирование

### Ручное тестирование через stdin/stdout

```bash
python server.py
```

Затем введите JSON-RPC запрос:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "open_url", "arguments": {"url": "https://example.com"}}}
```

### Примеры запросов

Полные примеры находятся в `docs/examples.json`.

**Открыть URL:**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "open_url", "arguments": {"url": "https://example.com"}}}
```

**Получить текст:**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_text", "arguments": {"selector": "h1"}}}
```

**Выполнить JavaScript:**
```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "evaluate_js", "arguments": {"code": "return document.title"}}}
```

**Сделать скриншот:**
```json
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "screenshot", "arguments": {"path": "./screenshot.png"}}}
```

**Кликнуть элемент:**
```json
{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "click", "arguments": {"selector": "a"}}}
```

## Использование с Claude Code

После подключения вы можете просить Claude:

```
Открой https://example.com в браузере
```

```
Получи текст заголовка страницы
```

```
Сделай скриншот текущей страницы
```

```
Выполни JavaScript: return document.querySelectorAll('a').length
```

## Устранение неполадок

**Ошибка: "Failed to connect to browser on port 9222"**
- Убедитесь, что Comet запущен с флагом `--remote-debugging-port=9222`
- Проверьте, что порт не занят другим процессом: `lsof -i :9222` (Linux/macOS) или `netstat -ano | findstr :9222` (Windows)
- Для WSL: убедитесь, что настроены брандмауэр и проброс портов (см. раздел "Настройка для WSL")

**Ошибка: "pychrome is NOT installed"**
- Установите: `pip install pychrome`

**Ошибка: "Python version too old"**
- Обновите Python до версии 3.10 или выше

**WSL: Connection timeout при подключении к браузеру**
- Проверьте, что браузер слушает на порту: `netstat -ano | findstr :9222` (в Windows)
- Убедитесь, что правило брандмауэра создано
- Проверьте проброс портов: `netsh interface portproxy show all` (в Windows PowerShell)
- Попробуйте перезапустить браузер после настройки проброса портов

## Структура проекта

```
mcp_comet_for_claude_code/
├── server.py           # Основной MCP-сервер
├── mcp.json            # Манифест MCP
├── check_env.py        # Проверка окружения
├── requirements.txt    # Зависимости Python
├── README.md           # Эта инструкция
└── docs/
    ├── prompt.yaml     # Техническое задание
    └── examples.json   # Примеры MCP-запросов
```

## Лицензия

MIT
