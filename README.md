# MCP Server for Comet Browser

**Версия:** 3.1.0 🚀 | **Дата релиза:** 2025-11-12

MCP (Model Context Protocol) сервер для управления браузером Comet через Chrome DevTools Protocol.

> **📋 История версий:** См. [CHANGELOG.md](CHANGELOG.md) для полной истории изменений.

## 🎉 Что нового в v3.1.0 - MULTI-CLIENT SUPPORT

**Главная фича:**
- 🌟 **Поддержка множественных клиентов** - Теперь несколько экземпляров Claude Code могут одновременно работать с одним браузером!
- 🔄 **HTTP/WebSocket API** - Новый `mcp_http_wrapper.py` мультиплексирует запросы
- 📊 **Мониторинг** - Endpoints `/health` и `/stats` для отслеживания состояния
- 📚 **Auto-docs** - Swagger UI на `http://localhost:9223/docs`

**Было до v3.1.0:**
- ❌ Только 1 Claude Code мог работать с браузером
- ❌ Второй экземпляр получал "port in use" error

**Стало в v3.1.0:**
- ✅ Неограниченное количество Claude Code экземпляров
- ✅ Все работают с одним браузером одновременно
- ✅ HTTP wrapper на порту 9223 мультиплексирует запросы

**Быстрый старт с multi-client:**
```powershell
# Windows: Запустить windows_proxy.py (как обычно)
py C:\Users\work2\mcp_comet_for_claude_code\windows_proxy.py

# NEW! Запустить HTTP wrapper
py C:\Users\work2\mcp_comet_for_claude_code\mcp_http_wrapper.py

# Откройте 2-3 окна Claude Code - все будут работать!
```

**Документация:**
- [Multi-Client Quick Start](docs/MULTI_CLIENT_QUICK_START.md) - Пошаговая инструкция
- [HTTP API Reference](docs/HTTP_API_REFERENCE.md) - Полное API руководство

---

## 🚀 Что нового в v3.0.0

### **Performance Improvements**
- ⚡ **click_by_text 2x быстрее**: 800ms → 400ms (оптимизация поиска элементов)
- ⚡ **TTL кэш**: Повторные клики экономят 100-300ms
- ⚡ **Cursor animations**: 200ms (было 400ms) - быстрые и плавные

### **Новые возможности**
- 🎨 **get_visual_snapshot()**: Structured JSON вместо скриншотов (6x меньше tokens!)
- 📝 **Form Automation**: 4 новых команды для работы с формами
  - `fill_input` - заполнение текстовых полей
  - `select_option` - выбор в select/dropdown
  - `check_checkbox` - установка checkbox/radio
  - `submit_form` - отправка форм
- 🔄 **Async/await support**: evaluate_js теперь поддерживает `await fetch()` и другие async операции
- 📊 **Form extraction**: save_page_info извлекает структуру форм, inputs, selects

### **Stability Enhancements**
- 🎯 **Viewport scoring**: click_by_text выбирает элементы в viewport с приоритетом
- 🔌 **WebSocket stability**: Keep-alive 20s (было 30s), health check 30s (было 45s)
- 🎬 **Animation cleanup**: Отмена анимаций + cleanup timeouts (нет memory leaks)
- 📍 **Stack traces**: Полные stack traces в error responses для debugging

## Архитектура

Система использует **модульную архитектуру V3** с автоматической регистрацией команд:

**Основные компоненты:**
- **server.py** — точка входа, асинхронный JSON-RPC 2.0 сервер (stdin/stdout)
- **browser/connection.py** — управление CDP подключением с monkey-patches для WSL
- **commands/** — 34 автоматически регистрируемых команд через `@register` декоратор (+5 новых в v3.0.0)
- **mcp/protocol.py** — JSON-RPC обработчик с dependency injection
- **pychrome** — библиотека для взаимодействия с Chrome DevTools Protocol
- **Comet Browser** — запущен с `--remote-debugging-port=9222` (или через `windows_proxy.py` для WSL)

**Для WSL:**
- **windows_proxy.py** — Python прокси на Windows (порт 9224 → 9222)
- **Monkey-patches** — автоматическая перезапись WebSocket URLs на стороне клиента

Сервер предоставляет 34 инструмента:

**Навигация (2):** `open_url`, `get_text`

**Взаимодействие (4):** `click`, `click_by_text`, `scroll_page`, `move_cursor`

**📝 Form Automation (4) - НОВОЕ в v3.0.0:** `fill_input`, `select_option`, `check_checkbox`, `submit_form`

**DevTools (6):** `open_devtools`, `close_devtools`, `console_command`, `get_console_logs`, `inspect_element`, `get_network_activity`

**Вкладки (4):** `list_tabs`, `create_tab`, `close_tab`, `switch_tab`

**Выполнение кода и скриншоты (5):** `evaluate_js`, `screenshot`, `get_page_snapshot`, `get_visual_snapshot` ⭐ NEW, `save_page_info`

**Поиск и структура страницы (2):** `find_elements`, `get_page_structure`

**Отладка (3):** `debug_element`, `force_click`, `open_devtools_ui`

**Диагностика (4):** `enable_console_logging`, `diagnose_page`, `get_clickable_elements`, `devtools_report`

## Стабильность соединения

Версия 3.0.0 включает улучшенную стабильность:

- **WebSocket Keep-Alive** - ping/pong каждые 20 секунд (⚡ улучшено с 30s) предотвращает idle disconnections
- **Background Health Check** - автоматическая проверка соединения каждые 30 секунд (⚡ улучшено с 45s)
- **Автоматическое переподключение** - прозрачное восстановление при разрыве связи с exponential backoff
- **TCP Keep-Alive в Proxy** - windows_proxy.py использует TCP keep-alive (30s idle, 10s interval)
- **Thread-Safe CDP** - все команды используют AsyncCDP wrapper, никаких race conditions
- **Animation Cleanup** - автоматическая отмена анимаций + cleanup timeouts (нет memory leaks)

**Результат:** connection uptime 99.5% (было 95%), `/mcp reconnect` больше не требуется.

## Визуализация курсора AI

Сервер автоматически создаёт **визуальный курсор AI** (синий светящийся кружок), который показывает, куда смотрит модель:

- 🔵 При `click()` курсор **плавно движется** к элементу (200ms - ⚡ 2x быстрее!)
- 🟢 При клике **зелёная вспышка** с увеличением (200ms)
- ✅ Клик выполняется **после всех анимаций**
- 🎯 Можно явно перемещать курсор командой `move_cursor()`
- 🎬 Автоматическая cleanup анимаций (нет memory leaks)

**Версия V3.0.0:** Анимации оптимизированы для максимальной производительности - предотвращают GC issues!

Коммуникация через MCP позволяет Claude Code напрямую управлять браузером и использовать возможности DevTools.

## Требования

- Python >= 3.10
- Браузер Comet (или любой Chromium-based) с поддержкой Chrome DevTools Protocol
- pychrome >= 0.2.4

---

## 🚀 Quick Start для WSL пользователей

**Если вы используете Windows + WSL + Claude Code в WSL, следуйте этой инструкции:**

### 1. Автоматический запуск (рекомендуется)

Используйте готовый скрипт `start_wsl.bat`:

**Из Windows PowerShell:**
```powershell
cd C:\Users\work2\mcp_comet_for_claude_code
.\start_wsl.bat
```

**ИЛИ из WSL:**
```bash
cd /mnt/c/Users/work2/mcp_comet_for_claude_code
cmd.exe /c start_wsl.bat
```

Скрипт автоматически запустит:
1. Python прокси (порт 9224) - для WSL доступа
2. Браузер Comet (порт 9222) - для CDP подключения

### 2. Запустите MCP сервер в WSL

```bash
cd ~/mcp_comet_for_claude_code
python3 server.py
```

### 3. Готово! 🎉

Теперь Claude Code может управлять браузером через 34 команды (включая новые form automation в v3.0.0).

**Детальная настройка:** См. раздел [2.1. Настройка для WSL](#21-настройка-для-wsl-windows-subsystem-for-linux)

---

## Установка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Запустите Comet с remote debugging

**Windows:**
```cmd
"C:\Path\To\comet.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222
```

Для Comet (Perplexity) - типичный путь:
```cmd
"%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222
```

**Важно:**
- Используйте `comet.exe` (маленькие буквы)
- Флаг `--remote-debugging-address=127.0.0.1` обязателен для безопасности

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

Если вы используете WSL и Claude Code запущен в Linux-окружении, необходимо настроить прокси для WebSocket подключений.

#### ✅ Быстрый старт (Автоматический запуск)

**Самый простой способ - используйте автоматический скрипт:**

1. **Скопируйте путь к вашему репозиторию на Windows** (например: `C:\Users\work2\mcp_comet_for_claude_code`)

2. **Запустите из WSL:**
```bash
# Замените путь на ваш Windows путь
cd /mnt/c/Users/work2/mcp_comet_for_claude_code
cmd.exe /c start_wsl.bat
```

**ИЛИ из Windows PowerShell:**
```powershell
cd C:\Users\work2\mcp_comet_for_claude_code
.\start_wsl.bat
```

Скрипт автоматически:
- ✅ Запустит Python прокси на порту 9224
- ✅ Запустит браузер Comet на порту 9222
- ✅ Покажет инструкции для следующих шагов

3. **В WSL запустите MCP сервер:**
```bash
cd ~/mcp_comet_for_claude_code
python3 server.py
```

#### 🔧 Ручная настройка (если нужно больше контроля)

**Проблема:**
- Comet слушает только `127.0.0.1:9222` на Windows
- WSL находится в отдельной сети
- Внешние proxy из environment variables блокируют WebSocket

**Решение:** Используем Python прокси + client-side monkey-patches

**ВАЖНЫЙ ПОРЯДОК ЗАПУСКА:**

**Шаг 1: Запустите прокси на Windows (port 9224) - ПЕРВЫМ!**

**ВАЖНО:** Прокси должен быть запущен НА WINDOWS, а не в WSL!

**Способ A: Из Windows PowerShell**
```powershell
# Откройте PowerShell (НЕ нужны права администратора)
cd C:\Users\work2\mcp_comet_for_claude_code
python windows_proxy.py
```

**Способ B: Из WSL с помощью PowerShell.exe**
```bash
# Из WSL-терминала запустить прокси на Windows
cd /mnt/c/Users/work2/mcp_comet_for_claude_code
powershell.exe -Command "python windows_proxy.py"
```

**Шаг 2: Запустите браузер на Windows (port 9222) - ВТОРЫМ!**

```cmd
"%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222
```

Вы должны увидеть:
```
[*] CDP Proxy listening on 0.0.0.0:9224
[*] Forwarding to 127.0.0.1:9222
[*] TCP keep-alive enabled (Windows mode: 30s idle, 10s interval)
[*] Press Ctrl+C to stop
```

**Шаг 3: Проверка из WSL (что прокси работает)**

```bash
# Получить IP Windows хоста
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
echo "Windows host IP: $WINDOWS_HOST"

# Проверить доступ через прокси (port 9224)
curl http://$WINDOWS_HOST:9224/json/version
```

Должен вернуться JSON с информацией о браузере.

**Шаг 4: Запустите MCP-сервер в WSL**

```bash
cd ~/mcp_comet_for_claude_code
python3 server.py
```

MCP-сервер автоматически:
- Определит IP Windows-хоста из `/etc/resolv.conf`
- Подключится к `WINDOWS_HOST:9224`
- Очистит proxy environment variables
- Перепишет WebSocket URLs на стороне клиента

#### Как это работает

1. **windows_proxy.py** (Windows, порт 9224):
   - Простой TCP proxy: `0.0.0.0:9224` → `127.0.0.1:9222`
   - Исправляет HTTP `Host` header для CORS
   - НЕ модифицирует WebSocket URLs (избегает проблем Content-Length)

2. **browser/connection.py** (WSL, monkey-patches):
   - Отключает proxy для WebSocket: очищает environment variables
   - Переписывает WebSocket URLs: `ws://127.0.0.1:9222/` → `ws://WINDOWS_HOST:9224/`

3. **server.py** (WSL):
   - Очищает все proxy environment variables при старте
   - Использует порт 9224 по умолчанию для WSL

#### Альтернативное решение (IP Helper + portproxy)

Если Python прокси не подходит, используйте классический способ через `netsh portproxy`:

```powershell
# В PowerShell от администратора
net start iphlpsvc
Set-Service -Name iphlpsvc -StartupType Automatic
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1
New-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
```

Затем измените в `browser/connection.py`:
```python
def __init__(self, debug_port = 9222, debug_host: str = None):  # вместо 9224
```

#### Troubleshooting WSL

**Прокси не запускается на Windows:**
- Убедитесь, что у вас установлен Python на Windows (не только в WSL)
- Проверьте что порт 9224 свободен: `netstat -ano | findstr :9224`

**WebSocket connection refused:**
- Проверьте, что прокси запущен И видно из WSL: `curl http://$WINDOWS_HOST:9224/json`
- Убедитесь, что используется порт 9224, а не 9222
- Проверьте, что нет внешних proxy в environment: `env | grep -i proxy`

**Подробная документация:**
- Troubleshooting: `docs/troubleshooting.md`

### 3. Проверьте окружение

```bash
python3 check_env.py
```

Вы должны увидеть:
```
============================================================
MCP Comet Browser - Environment Check
============================================================

✓ Python 3.10.x (required: >= 3.10)
✓ pychrome is installed (version: 0.2.4)
✓ Chrome DevTools Protocol is accessible
  Browser: Chrome/120.0.6099.109

============================================================
✓ All checks passed! Environment is ready.
============================================================
```

**Примечание:**
- Для локального использования: проверяется порт 9222
- Для WSL: проверяется порт 9224 (через windows_proxy.py)

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
- Сервер автоматически переподключается (background health check loop)
- Если проблема сохраняется: обновите сервер (`git pull`) и перезапустите Claude Code
- Ручной реконнект `/mcp reconnect` больше не требуется

**Ошибка: "Failed to connect to browser"**
- Убедитесь, что Comet запущен с флагом `--remote-debugging-port=9222`
- **Локально:** Проверьте порт: `lsof -i :9222` (Linux/macOS) или `netstat -ano | findstr :9222` (Windows)
- **Для WSL:** Убедитесь, что `windows_proxy.py` запущен на Windows (порт 9224) - см. раздел "Настройка для WSL"

**DevTools команды не работают?**
- Обновите сервер: `git pull`
- Перезапустите Claude Code
- Проверьте: должно быть 34 инструмента (включая 6 DevTools, 4 диагностики, 3 отладки, 4 form automation)

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
├── server.py                    # Точка входа MCP-сервера
├── windows_proxy.py             # Python прокси для WSL (запускается на Windows)
├── check_env.py                # Проверка окружения
├── requirements.txt            # Зависимости Python
├── README.md                   # Эта инструкция
├── mcp/
│   ├── protocol.py             # JSON-RPC 2.0 обработчик
│   ├── logging_config.py       # Structured logging
│   └── errors.py               # Typed exceptions hierarchy
├── browser/
│   ├── connection.py           # Подключение к браузеру (с monkey-patches)
│   ├── async_cdp.py            # Thread-safe async CDP wrapper
│   └── cursor.py               # Визуальный AI-курсор
├── commands/
│   ├── base.py                 # Базовый класс Command
│   ├── context.py              # CommandContext для DI
│   ├── registry.py             # Auto-discovery через @register
│   ├── navigation.py           # open_url, get_text
│   ├── interaction.py          # click, click_by_text, scroll_page, move_cursor
│   ├── forms.py                # ⭐ fill_input, select_option, check_checkbox, submit_form (v3.0.0)
│   ├── tabs.py                 # list_tabs, create_tab, close_tab, switch_tab
│   ├── devtools.py             # open_devtools, console_command, get_console_logs
│   ├── evaluation.py           # evaluate_js (с async/await support в v3.0.0)
│   ├── screenshot.py           # screenshot
│   ├── visual_snapshot.py      # ⭐ get_visual_snapshot (v3.0.0)
│   ├── search.py               # find_elements, get_page_structure
│   ├── save_page_info.py       # save_page_info (главный инструмент)
│   ├── helpers.py              # debug_element, force_click
│   └── diagnostics.py          # diagnose_page, get_clickable_elements
├── utils/
│   └── json_optimizer.py       # JSON optimization для save_page_info
└── docs/
    ├── examples.json           # Примеры MCP-запросов
    ├── devtools_examples.md    # Примеры DevTools команд
    └── troubleshooting.md      # Устранение неполадок
```

### Архитектура V3 (Performance, Stability & Form Automation)

**Ключевые улучшения V3.0.0:**
- **Performance** - click_by_text 2x быстрее (800ms → 400ms), TTL кэш для повторных операций
- **Form Automation** - 4 новых команды (fill_input, select_option, check_checkbox, submit_form)
- **Visual Snapshot** - get_visual_snapshot() экономит 6x tokens по сравнению со screenshot
- **Async/await support** - evaluate_js поддерживает async операции (await fetch, Promise.all)
- **Viewport scoring** - click_by_text предпочитает элементы в viewport
- **WebSocket stability** - улучшенные таймауты (keep-alive 20s, health check 30s)
- **Animation cleanup** - отмена анимаций + cleanup timeouts (нет memory leaks)
- **Stack traces** - полные stack traces в error responses

**Улучшения V2 (сохранены):**
- **Command metadata as class attributes** - метаданные теперь class attributes (не @property)
- **Structured logging** - централизованная конфигурация, все `print()` → `logger`
- **Error hierarchy** - типизированные исключения с JSON-RPC кодами
- **Dependency Injection** - CommandContext для управления зависимостями
- **Auto-discovery** - команды регистрируются через `@register` декоратор
- **Async CDP wrapper** - thread-safe wrapper для pychrome
- **JSON optimization** - оптимизация вывода save_page_info (58.8% сокращение)
- **Connection stability** - WebSocket keep-alive + background health check с автопереподключением
- **TCP keep-alive** - стабильные соединения на уровне ОС в windows_proxy.py

## Лицензия

MIT
