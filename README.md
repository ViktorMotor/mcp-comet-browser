# MCP Server for Comet Browser

MCP (Model Context Protocol) сервер для управления браузером Comet через Chrome DevTools Protocol.

## Архитектура

Система состоит из трех компонентов:
- **server.py** — асинхронный JSON-RPC 2.0 сервер, работающий через stdin/stdout
- **pychrome** — библиотека для взаимодействия с Chrome DevTools Protocol (CDP)
- **Comet Browser** — запущен с флагом `--remote-debugging-port=9222`

Сервер предоставляет 29 инструментов:

**Навигация (2):** `open_url`, `get_text`

**Взаимодействие (4):** `click`, `click_by_text`, `scroll_page`, `move_cursor`

**DevTools (6):** `open_devtools`, `close_devtools`, `console_command`, `get_console_logs`, `inspect_element`, `get_network_activity`

**Вкладки (4):** `list_tabs`, `create_tab`, `close_tab`, `switch_tab`

**Выполнение кода и скриншоты (4):** `evaluate_js`, `screenshot`, `get_page_snapshot`, `save_page_info`

**Поиск и структура страницы (2):** `find_elements`, `get_page_structure`

**Отладка (3):** `debug_element`, `force_click`, `open_devtools_ui`

**Диагностика (4):** `enable_console_logging`, `diagnose_page`, `get_clickable_elements`, `devtools_report`

## Визуализация курсора AI

Сервер автоматически создаёт **визуальный курсор AI** (синий светящийся кружок), который показывает, куда смотрит модель:

- При `click()` курсор **автоматически анимируется** к элементу перед кликом
- Можно явно перемещать курсор командой `move_cursor()`
- Курсор анимируется плавно с эффектом свечения
- При клике меняет цвет на зелёный с анимацией

Коммуникация через MCP позволяет Claude Code напрямую управлять браузером и использовать возможности DevTools.

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

Если вы используете WSL и Claude Code запущен в Linux-окружении, необходимо настроить проброс портов и брандмауэр.

#### ✅ Решение (ПРОВЕРЕНО И РАБОТАЕТ)

**Проблема:** Служба **IP Helper** (iphlpsvc) в Windows может быть остановлена, из-за чего правило `netsh portproxy` не работает.

**Шаг 1: Запустите браузер на Windows**

```cmd
"C:\Users\<USERNAME>\AppData\Local\Perplexity\Comet\Application\Comet.exe" --remote-debugging-port=9222
```

**Шаг 2: Включите службу IP Helper (ВАЖНО!)**

В Windows PowerShell от администратора:
```powershell
# Запустить службу
net start iphlpsvc

# Настроить автозапуск
Set-Service -Name iphlpsvc -StartupType Automatic
```

**Шаг 3: Настройте проброс портов**

```powershell
# Добавить проброс портов
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1

# Проверить настройку
netsh interface portproxy show all
```

Вы должны увидеть:
```
Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
--------------- ----------  --------------- ----------
0.0.0.0         9222        127.0.0.1       9222
```

**Шаг 4: Настройте брандмауэр Windows**

```powershell
New-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
```

**Шаг 5: Проверка из WSL**

```bash
# Получить IP Windows хоста
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
echo "Windows host IP: $WINDOWS_HOST"

# Проверить доступ к браузеру
curl http://$WINDOWS_HOST:9222/json/version
```

Должен вернуться JSON с информацией о браузере.

#### Автоматическая настройка

Используйте скрипт `fix_portproxy.ps1` (в PowerShell от администратора):
```powershell
.\fix_portproxy.ps1
```

#### Troubleshooting WSL

**Если не работает после перезагрузки:**

1. Проверьте службу IP Helper:
```powershell
Get-Service iphlpsvc
# Если Stopped:
net start iphlpsvc
```

2. Проверьте правило portproxy:
```powershell
netsh interface portproxy show all
# Если пусто - пересоздайте правило
```

**Альтернативное решение:** Если IP Helper не работает, используйте Python прокси `chrome_proxy.py`:
```bash
python3 chrome_proxy.py
# Затем подключайтесь к localhost:9223 вместо IP Windows хоста
```

Подробнее: см. файлы `SOLUTION.md` и `fix_comet_wsl.md` в репозитории.

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

### Вариант 1: Автоматическая установка (рекомендуется)

Скопируйте и отправьте Claude Code этот промпт:

```
Клонируй репозиторий https://github.com/ViktorMotor/mcp-comet-browser в ~/mcp-comet-browser,
установи зависимости (pip install -r requirements.txt),
добавь MCP-сервер в конфигурацию Claude Code,
и проверь подключение запустив check_env.py.

Используй python3 вместо python.
Путь к конфигурации Claude Code: ~/.config/claude-code/mcp_settings.json (Linux/WSL)
или %APPDATA%\Claude Code\mcp_settings.json (Windows).

После настройки протестируй доступ к браузеру.
```

Claude Code автоматически выполнит все шаги установки и настройки.

### Вариант 2: Ручная настройка через конфигурацию

Клонируйте репозиторий:
```bash
cd ~
git clone https://github.com/ViktorMotor/mcp-comet-browser.git
cd mcp-comet-browser
pip install -r requirements.txt
```

Добавьте в `~/.config/claude-code/mcp_settings.json` (Linux/macOS/WSL) или `%APPDATA%\Claude Code\mcp_settings.json` (Windows):

```json
{
  "mcpServers": {
    "comet-browser": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "~/mcp-comet-browser",
      "transport": "stdio"
    }
  }
}
```

### Вариант 3: Использование mcp.json

Скопируйте `mcp.json` в директорию конфигурации Claude Code или укажите путь к серверу вручную.

### Перезапуск Claude Code

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

**Открыть DevTools:**
```json
{"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "open_devtools", "arguments": {}}}
```

**Выполнить команду в консоли:**
```json
{"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "console_command", "arguments": {"command": "document.querySelectorAll('a').length"}}}
```

**Получить логи консоли:**
```json
{"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "get_console_logs", "arguments": {"clear": false}}}
```

**Инспектировать элемент:**
```json
{"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "inspect_element", "arguments": {"selector": "h1"}}}
```

**Получить сетевую активность:**
```json
{"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "get_network_activity", "arguments": {}}}
```

**Получить список вкладок:**
```json
{"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "list_tabs", "arguments": {}}}
```

**Создать новую вкладку:**
```json
{"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "create_tab", "arguments": {"url": "https://google.com"}}}
```

**Переключиться на вкладку:**
```json
{"jsonrpc": "2.0", "id": 13, "method": "tools/call", "params": {"name": "switch_tab", "arguments": {"tab_id": "TAB_ID_HERE"}}}
```

**Закрыть вкладку:**
```json
{"jsonrpc": "2.0", "id": 14, "method": "tools/call", "params": {"name": "close_tab", "arguments": {"tab_id": "TAB_ID_HERE"}}}
```

**Прокрутить страницу вниз:**
```json
{"jsonrpc": "2.0", "id": 15, "method": "tools/call", "params": {"name": "scroll_page", "arguments": {"direction": "down", "amount": 500}}}
```

**Прокрутить в конец страницы:**
```json
{"jsonrpc": "2.0", "id": 16, "method": "tools/call", "params": {"name": "scroll_page", "arguments": {"direction": "bottom"}}}
```

**Прокрутить элемент:**
```json
{"jsonrpc": "2.0", "id": 17, "method": "tools/call", "params": {"name": "scroll_page", "arguments": {"selector": ".content", "direction": "down", "amount": 300}}}
```

**Прокрутить к координатам:**
```json
{"jsonrpc": "2.0", "id": 18, "method": "tools/call", "params": {"name": "scroll_page", "arguments": {"x": 0, "y": 1000}}}
```

## Использование с Claude Code

После подключения вы можете просить Claude:

**Базовые операции:**
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

```
Прокрути страницу вниз на 500 пикселей
```

```
Прокрути в конец страницы
```

```
Прокрути элемент .content вниз
```

```
Перемести курсор к кнопке с классом .submit-button
```

```
Перемести курсор на координаты (100, 200)
```

**DevTools функционал:**
```
Открой DevTools (F12) в браузере
```

```
Выполни в консоли команду: document.title
```

```
Получи все логи из консоли браузера
```

```
Инспектируй элемент h1 на странице (покажи HTML, стили, позицию)
```

```
Покажи сетевую активность страницы (загруженные ресурсы, тайминги)
```

```
Выполни в консоли: console.log("test") и затем получи логи
```

**Работа с вкладками:**
```
Покажи список открытых вкладок в браузере
```

```
Создай новую вкладку и открой в ней https://github.com
```

```
Переключись на вкладку с ID xxx
```

```
Закрой текущую вкладку
```

## Устранение неполадок

**Полное руководство:** См. [docs/troubleshooting.md](docs/troubleshooting.md)

### Быстрые решения

**Ошибка: "Tab has been stopped"**
- Обновите сервер: `cd ~/mcp-comet-browser && git pull`
- Перезапустите Claude Code
- Сервер теперь автоматически переподключается к браузеру

**Ошибка: "Failed to connect to browser on port 9222"**
- Убедитесь, что Comet запущен с флагом `--remote-debugging-port=9222`
- Проверьте порт: `lsof -i :9222` (Linux/macOS) или `netstat -ano | findstr :9222` (Windows)
- Для WSL: убедитесь, что настроены брандмауэр и проброс портов (см. раздел "Настройка для WSL")

**DevTools команды не работают?**
- Обновите сервер: `git pull`
- Перезапустите Claude Code
- Проверьте: должно быть 29 инструментов (включая 6 DevTools, 4 диагностики, 3 отладки)

**Обновление MCP сервера:**
```bash
cd ~/mcp-comet-browser
git pull
# Перезапустите Claude Code
```

Подробнее: [docs/troubleshooting.md](docs/troubleshooting.md)

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
