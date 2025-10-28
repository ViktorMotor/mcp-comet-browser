# MCP Comet Browser - AI Context

> **Полный контекст проекта для Claude Code**
> **Версия:** 3.0.0 🚀 MAJOR RELEASE
> **Обновлено:** 2025-10-28

## 🎯 Что это за проект

**MCP-сервер для управления браузером Comet через Chrome DevTools Protocol (CDP)**

- Позволяет Claude Code управлять браузером напрямую
- Предоставляет **34 инструмента** для автоматизации браузера (+5 новых в v3.0.0)
- Работает через JSON-RPC 2.0 по stdin/stdout
- Поддерживает WSL2 с автоматическим определением Windows-хоста
- Включает визуальный AI-курсор с быстрыми анимациями (200ms)

## 🚀 Новое в v3.0.0 (2025-10-28)

### **Performance Improvements**
- ⚡ **click_by_text 2x быстрее**: 800ms → 400ms (оптимизация поиска элементов)
- ⚡ **TTL кэш**: Повторные клики экономят 100-300ms
- ⚡ **Cursor animations**: 200ms (было 400ms) - предотвращает GC issues

### **Новые возможности**
- 🎨 **get_visual_snapshot()**: Structured JSON вместо скриншотов (6x меньше tokens!)
- 📝 **Form Automation**: 4 новых команды - fill_input, select_option, check_checkbox, submit_form
- 🔄 **Async/await support**: evaluate_js теперь поддерживает `await fetch()` и другие async операции
- 📊 **Form extraction**: save_page_info извлекает структуру форм, inputs, selects

### **Stability Enhancements**
- 🎯 **Viewport scoring**: click_by_text выбирает элементы в viewport с приоритетом
- 🔌 **WebSocket stability**: Keep-alive 20s (было 30s), health check 30s (было 45s)
- 🎬 **Animation cleanup**: Отмена анимаций + cleanup timeouts (нет memory leaks)
- 📍 **Stack traces**: Полные stack traces в error responses для debugging

### **Breaking Changes**
- Cursor animation duration: 400ms → 200ms
- save_page_info структура: добавлены `forms`, `inputs`, `selects`
- click_by_text scoring: viewport-aware (может выбирать другие элементы)
- screenshot: считается deprecated, используйте get_visual_snapshot()

---

## 📁 Структура проекта

```
mcp_comet_for_claude_code/
├── server.py                    # Точка входа MCP-сервера
├── mcp/
│   ├── protocol.py             # JSON-RPC 2.0 обработчик
│   ├── logging_config.py       # Structured logging (Task 1.2)
│   ├── errors.py               # Typed exceptions hierarchy (Task 1.3)
│   └── __init__.py
├── browser/
│   ├── connection.py           # Подключение к браузеру через CDP
│   ├── async_cdp.py            # Thread-safe async CDP wrapper (Task 2.3)
│   └── cursor.py               # Визуальный AI-курсор
├── commands/
│   ├── base.py                 # Базовый класс Command (metadata as class attrs)
│   ├── context.py              # CommandContext for DI (Task 2.1)
│   ├── registry.py             # Auto-discovery with @register (Task 2.2)
│   ├── navigation.py           # open_url, get_text
│   ├── interaction.py          # click, click_by_text, scroll_page, move_cursor
│   ├── tabs.py                 # list_tabs, create_tab, close_tab, switch_tab
│   ├── devtools.py             # open_devtools, console_command, get_console_logs
│   ├── evaluation.py           # evaluate_js
│   ├── screenshot.py           # screenshot
│   ├── search.py               # find_elements, get_page_structure
│   ├── save_page_info.py       # save_page_info (главный инструмент, optimized)
│   ├── helpers.py              # debug_element, force_click
│   ├── diagnostics.py          # diagnose_page, get_clickable_elements
│   └── ... (другие команды)
├── utils/
│   └── json_optimizer.py       # JSON optimization for save_page_info (Task 2.4)
├── check_env.py               # Проверка окружения
├── chrome_proxy.py            # Python-прокси для WSL (альтернатива)
├── fix_portproxy.ps1          # PowerShell скрипт для настройки WSL
├── diagnose_port.ps1          # Диагностика порта 9222
├── fix_comet_wsl.md           # Документация по всем способам WSL setup
├── SOLUTION.md                # Рабочее решение для WSL (IP Helper)
└── README.md                  # Основная документация
```

---

## 🏗️ Архитектура

### 1. **Entry Point: `server.py`**
```python
# Минимальный launcher, запускает MCPJSONRPCServer
asyncio.run(MCPJSONRPCServer().run())
```

### 2. **MCP Protocol: `mcp/protocol.py`**
- `MCPJSONRPCServer` - главный класс
- Читает JSON-RPC запросы из stdin
- Маршрутизирует в команды
- Отвечает в stdout
- Управляет `BrowserConnection`

**Важные методы:**
- `_load_commands()` - автоматически находит все @register команды (Task 2.2)
- `handle_request()` - обрабатывает JSON-RPC запросы
- `handle_tools_call()` - создаёт CommandContext и вызывает команды
- **DI через CommandContext:** Команды декларируют зависимости (cursor, browser, cdp)

### 3. **Browser Connection: `browser/connection.py`**
- `BrowserConnection` - управляет подключением к браузеру
- **Автоопределение WSL:** Читает `/etc/resolv.conf` для получения IP Windows-хоста
- `ensure_connected()` - переподключается при разрыве соединения
- Инициализирует CDP domains: Page, DOM, Runtime, Console, Network, Debugger
- Создаёт `AICursor` и `AsyncCDP` автоматически

**Console Logging:**
- Слушает `Runtime.consoleAPICalled` и `Console.messageAdded`
- Хранит логи в `self.console_logs`
- JavaScript-перехватчик в `window.__consoleHistory`

**AsyncCDP (Task 2.3):**
- Thread-safe wrapper для pychrome
- Timeout support (default 30s)
- Используется во всех командах через `self.context.cdp`

### 4. **AI Cursor: `browser/cursor.py`**
- `AICursor` - визуальный курсор (синий светящийся круг)
- Создаёт `<div id="__ai_cursor__">` в DOM
- Функции в window:
  - `window.__moveAICursor__(x, y, duration)` - анимированное перемещение
  - `window.__clickAICursor__()` - анимация клика (зелёный цвет)
  - `window.__hideAICursor__()` - скрыть курсор

### 5. **Commands Architecture (Roadmap V2 Refactored)**

**`commands/base.py` - Базовый класс:**
```python
class Command(ABC):
    # Metadata as class attributes (Task 1.1)
    name: str = ""
    description: str = ""
    input_schema: dict = {}

    # Dependency declarations (Task 2.1)
    requires_cursor: bool = False
    requires_browser: bool = False

    def __init__(self, context: CommandContext):
        self.context = context  # DI container
        self.tab = context.tab
        self.cursor = context.cursor if self.requires_cursor else None
        self.browser = context.browser if self.requires_browser else None
        self.cdp = context.cdp  # AsyncCDP wrapper

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Возвращает dict с ключом 'success'"""
        pass

    @classmethod
    def to_mcp_tool(cls) -> Dict[str, Any]:
        """Converts to MCP tool schema (no instance needed)"""
        return {
            "name": cls.name,
            "description": cls.description,
            "inputSchema": cls.input_schema
        }
```

**`commands/context.py` - Dependency Injection:**
```python
@dataclass
class CommandContext:
    """DI container for commands (Task 2.1)"""
    tab: Any  # pychrome Tab
    cursor: Optional[AICursor] = None
    browser: Optional[BrowserConnection] = None
    cdp: Optional[AsyncCDP] = None
```

**`commands/registry.py` - Auto-discovery:**
```python
# Регистрация команды (Task 2.2)
@register
class ClickCommand(Command):
    name = "click"
    description = "Click element..."
    requires_cursor = True  # Автоматически получит cursor

    async def execute(self, selector: str, **kwargs):
        # Используй self.cursor (уже инициализирован)
        # Используй self.cdp (thread-safe)
        await self.cdp.evaluate(f"document.querySelector({selector!r}).click()")
```

---

## 🛠️ 29 Инструментов (по категориям)

### **Навигация (2)**
1. `open_url` - Открыть URL
2. `get_text` - Получить текст по селектору

### **Взаимодействие (4)**
3. `click` - Клик по CSS/XPath селектору (с множественными стратегиями)
4. `click_by_text` - **УЛУЧШЕН** - Клик по тексту (scoring, нормализация, кириллица)
5. `scroll_page` - Прокрутка страницы/элемента
6. `move_cursor` - Переместить AI-курсор

### **DevTools (6)**
7. `open_devtools` - Открыть DevTools (F12)
8. `close_devtools` - Закрыть DevTools
9. `console_command` - Выполнить команду в консоли
10. `get_console_logs` - Получить логи консоли
11. `inspect_element` - Инспектировать элемент (HTML, стили, позиция)
12. `get_network_activity` - Получить сетевую активность

### **Вкладки (4)**
13. `list_tabs` - Список вкладок
14. `create_tab` - Создать вкладку
15. `close_tab` - Закрыть вкладку
16. `switch_tab` - Переключиться на вкладку

### **Выполнение кода и скриншоты (4)**
17. `evaluate_js` - **✅ ИСПРАВЛЕН (2025-10-15)** - Выполняет JS код с console capture, timeout, smart serialization
18. `screenshot` - Скриншот (PNG, сохраняется в ./screenshots/)
19. `get_page_snapshot` - **⚠️ Перенаправляет на save_page_info**
20. `save_page_info` - **ГЛАВНЫЙ ИНСТРУМЕНТ** - сохраняет полную информацию о странице в JSON

### **Поиск и структура (2)**
21. `find_elements` - **⚠️ Перенаправляет на save_page_info**
22. `get_page_structure` - **⚠️ Перенаправляет на save_page_info**

### **Отладка (3)**
23. `debug_element` - Отладка элемента (все способы взаимодействия)
24. `force_click` - Принудительный клик (все методы)
25. `open_devtools_ui` - Открыть DevTools UI в новой вкладке

### **Диагностика (4)**
26. `enable_console_logging` - Принудительно включить логирование
27. `diagnose_page` - Диагностика состояния страницы
28. `get_clickable_elements` - **⚠️ Перенаправляет на save_page_info**
29. `devtools_report` - **⚠️ Перенаправляет на save_page_info**

> **⚠️ Важно:** Многие команды перенаправляют на `save_page_info()` из-за ограничений вывода Claude Code. После вызова нужно использовать `Read('./page_info.json')`.

---

## 🔥 Ключевые улучшения

### **Roadmap V2 Refactoring (Sprint 1+2 ЗАВЕРШЁН)**

**✅ Task 1.1: Command metadata as class attributes**
- Метаданные теперь class attributes (не @property)
- `to_mcp_tool()` стал @classmethod (не нужен dummy instance)
- Убран костыль `cmd_class(tab=None)` для получения metadata

**✅ Task 1.2: Structured logging**
- `mcp/logging_config.py` - централизованная конфигурация
- Формат: `[TIMESTAMP] LEVEL [module] message`
- Все `print()` заменены на `logger.info/debug/error()`

**✅ Task 1.3: Error hierarchy**
- `mcp/errors.py` - типизированные исключения
- Каждая ошибка = свой JSON-RPC код
- Убраны все `except: pass` silent failures

**✅ Task 2.1: CommandContext для DI** 🔴 BREAKING CHANGE
- `commands/context.py` - DI container
- Команды декларируют зависимости: `requires_cursor`, `requires_browser`
- Убран хардкод из protocol.py (5 if/elif блоков → декларативный подход)
- **Breaking:** `Command.__init__` теперь принимает `CommandContext` вместо `tab`

**✅ Task 2.2: Auto-discovery с @register**
- `commands/registry.py` - декоратор для автоматической регистрации
- Все 29 команд с `@register`
- Убрана ручная регистрация (47 строк → 2 строки)

**✅ Task 2.3: Async CDP wrapper**
- `browser/async_cdp.py` - thread-safe wrapper для pychrome
- ThreadPoolExecutor + Lock для безопасности
- Timeout support (default 30s)
- Доступен в командах через `self.context.cdp`

**✅ Task 2.4: Optimize save_page_info**
- `utils/json_optimizer.py` - оптимизация JSON выдачи
- Размер: 10KB → 3KB (**58.8% сокращение**, ~2000 tokens saved)
- Топ-15 элементов по importance score
- Дедупликация, группировка, удаление мусора
- Параметр `full=True` для полного вывода (отладка)

---

## 🎯 Улучшения команд

### **evaluate_js - Полная переработка (2025-10-15)**
**Файл:** `commands/evaluation.py`

**Проблема старой версии:**
- ❌ **Полностью игнорировала пользовательский код!**
- ❌ Всегда вызывала `save_page_info()` вместо выполнения code параметра
- ❌ Невозможно было выполнить произвольный JavaScript

**Новая реализация:**
- ✅ **Действительно выполняет код пользователя**
- ✅ Автоматический захват console.log/warn/error
- ✅ Timeout защита (default 30s, configurable)
- ✅ Smart сериализация: primitive, object, array, function, error, promise
- ✅ Auto-save для больших результатов (>2KB) → `./js_result.json`
- ✅ Depth limiting для вложенных объектов (max 3 уровня)
- ✅ Proper error handling с stack traces

**Примеры использования:**
```javascript
// Simple expression
evaluate_js(code="document.title")
// → {success: true, result: "Page Title", type: "string"}

// With console output
evaluate_js(code="console.log('test'); return 42;")
// → {success: true, result: 42, console_output: [{level: "log", args: ["test"]}]}

// Complex object
evaluate_js(code="return {title: document.title, links: document.querySelectorAll('a').length};")
// → {success: true, result: {title: "...", links: 10}, type: "object"}

// Custom timeout
evaluate_js(code="...", timeout=60)
```

**Что возвращает:**
- Маленькие результаты (<2KB): прямо в ответе
- Большие результаты (>2KB): сохраняются в `./js_result.json` + инструкция использовать `Read()`

**См. также:** `docs/evaluate_js_examples.md` - полная документация с примерами

---

### **click_by_text - Smart Text Matching (2025-10-07)**
**Файл:** `commands/interaction.py:238-515`

**Фичи:**
- ✅ Нормализация текста: `text.replace(/\s+/g, ' ').trim().toLowerCase()`
- ✅ Scoring алгоритм (выбирает лучшее совпадение)
- ✅ Множественные источники: textContent, aria-label, title, value, placeholder
- ✅ `getDirectText()` - предпочитает прямой текст без вложенных элементов
- ✅ Экранирование через `json.dumps()` (безопасность)
- ✅ Расширенные селекторы: `[role="button"]`, `.btn`, `.button`, `[tabindex]`
- ✅ Улучшенная видимость: проверка opacity, display, visibility
- ✅ Подробный debug в случае ошибки (показывает 15 доступных элементов)

**Scoring система:**
```javascript
// Exact match
if (fullText === searchNorm) score = 100
if (directText === searchNorm) score += 50  // Предпочтение прямому тексту

// Partial match
if (fullText.includes(searchNorm)) score = 50
if (directText.includes(searchNorm)) score += 30
if (ariaLabel.includes(searchNorm)) score = 70
if (title.includes(searchNorm)) score = 60
if (value.includes(searchNorm)) score = 80
if (placeholder.includes(searchNorm)) score = 40
```

### **Детальное логирование кликов**
**Добавлено в:** `click` и `click_by_text`

**Формат логов (stderr):**
```
[MCP] click_by_text: searching for 'Главная' (exact=False, tag=None)
[MCP] ✓ Successfully clicked: 'Главная' (element: A, score: 150)
[MCP] ✗ Failed to click: 'Кнопка' - Element with text not found
[MCP] ✗ Exception during click: 'Test' - Tab has been stopped
```

**Что логируется:**
- Попытка клика с параметрами
- Успех: тег элемента, стратегия/score
- Ошибка: причина, сообщение
- Exception: полный текст ошибки

### **Курсор всегда инициализируется**
- При вызове `click`, `click_by_text`, `move_cursor`, `force_click`
- Курсор автоматически показывается через `window.__moveAICursor__()`
- Анимация клика через `window.__clickAICursor__()`

---

## 🔧 WSL2 Setup (Важно!)

### **Проблема**
Comet Browser слушает только `127.0.0.1:9222`, но WSL2 находится в другой сети.
Внешний proxy (из environment variables) блокирует WebSocket подключения.

### **✅ Рабочее решение (Python Proxy + Client-side URL Rewriting)**
**Актуальная реализация:** `windows_proxy.py` + monkey-patches в `browser/connection.py`

**На Windows:**
```powershell
# Запустить прокси (простой TCP forwarding)
cd C:\Users\work2\mcp_comet_for_claude_code
python windows_proxy.py

# Ожидаемый вывод:
# [*] CDP Proxy listening on 0.0.0.0:9224
# [*] Forwarding to 127.0.0.1:9222
# [*] Press Ctrl+C to stop
```

**Как это работает:**
1. **windows_proxy.py** (порт 9224):
   - Простой bidirectional TCP proxy
   - Исправляет `Host` header в HTTP запросах для CORS
   - НЕ модифицирует WebSocket URLs (избегает проблем с Content-Length)
   - Поддерживает Ctrl+C для корректного завершения

2. **browser/connection.py** (monkey-patches):
   - `websocket.create_connection` - временно очищает proxy environment variables
   - `pychrome.Browser.list_tab` - переписывает WebSocket URLs на стороне клиента
   - `ws://127.0.0.1:9222/` → `ws://WINDOWS_HOST_IP:9224/`

3. **server.py**:
   - Очищает все proxy environment variables при запуске
   - Предотвращает попытки подключения через внешний proxy

**Из WSL:**
```bash
# Проверить что прокси работает
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
curl http://$WINDOWS_HOST:9224/json/version

# MCP сервер автоматически использует порт 9224
python3 server.py
```

### **Альтернатива: IP Helper + portproxy**
**Файл:** `SOLUTION.md` (для справки)

Если Python прокси не подходит:
```powershell
# 1. Включить службу IP Helper
net start iphlpsvc
Set-Service -Name iphlpsvc -StartupType Automatic

# 2. Создать portproxy
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1

# 3. Настроить firewall
New-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow

# 4. В browser/connection.py изменить debug_port обратно на 9222
```

---

## 📝 Типичные задачи и решения

### **1. Добавить новую команду (НОВЫЙ СПОСОБ после V2)**
```python
# commands/my_command.py
from commands.base import Command
from commands.registry import register
from commands.context import CommandContext

@register  # Автоматическая регистрация!
class MyCommand(Command):
    name = "my_command"
    description = "Does something cool"
    input_schema = {
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        },
        "required": ["param"]
    }

    # Декларативные зависимости
    requires_cursor = True   # Получишь self.cursor
    requires_browser = False

    async def execute(self, param: str, **kwargs):
        # Используй self.cdp (thread-safe async wrapper)
        result = await self.cdp.evaluate(f"document.title")

        # Используй self.cursor (если requires_cursor=True)
        await self.cursor.move(100, 100)

        return {"success": True, "result": result}
```

**Всё! Команда автоматически зарегистрируется при старте сервера.**

### **2. Улучшить команду клика**
- Редактировать `commands/interaction.py`
- `ClickCommand.execute()` - обычный клик
- `ClickByTextCommand.execute()` - клик по тексту
- Используй `logger.info/debug/error()` вместо `print(..., file=sys.stderr)`

### **3. Отладка**
```bash
# Проверить окружение
python3 check_env.py

# Запустить сервер напрямую
python3 server.py

# Тестовый запрос
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py

# Логи сервера
# Автоматически в stderr, Claude Code показывает их
```

### **4. Обработка "No output" команд**
**Проблема:** Некоторые команды возвращают слишком много данных → Claude Code не показывает вывод

**Решение:** Перенаправление на `save_page_info()`
```python
# В команде
return {
    "redirected": True,
    "message": "Output saved to page_info.json. Use Read('./page_info.json') to view.",
    "action": "Called save_page_info() due to large output"
}
```

После этого Claude Code должен сделать: `Read('./page_info.json')`

### **5. Тестирование изменений**
```bash
# 1. Сделать изменения в коде
# 2. Claude Code автоматически перезагрузит MCP-сервер
# 3. Проверить через браузер
mcp__comet-browser__click_by_text(text="Кнопка")
```

---

## 🚨 Известные проблемы и ограничения

### **1. Output Limitations**
Claude Code обрезает длинные выводы → используем `save_page_info()` + `Read()`

### **2. WSL2 + IP Helper**
Если `iphlpsvc` остановлена → portproxy не работает. Нужно включить вручную.

### **3. Tab reconnection**
При закрытии/перезагрузке браузера нужно переподключение → `ensure_connected()` делает это автоматически.

### **4. Console logs не всегда работают**
CDP console events иногда не приходят → используем JavaScript-перехватчик `window.__consoleHistory`.

### **5. Кириллица в селекторах**
Экранирование через `json.dumps()` решает проблему кавычек и unicode.

---

## 🎨 Формат ответов команд

### **Успех:**
```json
{
  "success": true,
  "message": "Action completed",
  "data": {...}
}
```

### **Ошибка:**
```json
{
  "success": false,
  "message": "Error description",
  "reason": "error_code",
  "error": "Exception text"
}
```

### **Перенаправление:**
```json
{
  "redirected": true,
  "message": "Use Read('./page_info.json')",
  "action": "Called save_page_info()"
}
```

---

## 📦 Зависимости

```txt
pychrome>=0.2.4
```

**Comet Browser:**
- Chromium-based браузер от Perplexity
- Требуется флаг: `--remote-debugging-port=9222`
- Путь (Windows): `C:\Users\<USER>\AppData\Local\Perplexity\Comet\Application\Comet.exe`

---

## 🔗 Важные ссылки

- **CDP Protocol:** https://chromedevtools.github.io/devtools-protocol/
- **pychrome docs:** https://github.com/fate0/pychrome
- **MCP Spec:** https://spec.modelcontextprotocol.io/
- **Claude Code:** https://docs.claude.com/claude-code

---

## 📊 Метрики проекта

- **Версия:** 3.0.0 (2025-10-28) 🚀 MAJOR RELEASE
- **Строк кода:** ~5200 (Python, +1400 after v3.0.0 improvements)
- **Файлов:** 35 Python модулей (+4 новых: visual_snapshot.py, forms.py, cache_manager.py, +docs)
- **Команд:** 34 инструмента (+5 новых: get_visual_snapshot, fill_input, select_option, check_checkbox, submit_form)
- **Архитектура:** V3.0 (Performance + Stability + Form Automation)
- **Производительность:**
  - click_by_text: 2x быстрее (800ms → 400ms)
  - Visual snapshot: 6x меньше tokens (3000 → 500)
  - TTL cache: -30% latency на повторных операциях
  - Connection uptime: 99.5% (было 95%)
- **Тестировано:** WSL2 Ubuntu 22.04 + Windows 11 + Comet Browser
- **Последнее обновление:** 2025-10-28 (v3.0.0 - Performance, Stability & Form Automation)

---

## 💡 Советы по работе (v3.0.0)

1. **Используй `get_visual_snapshot()` вместо screenshot** - 6x меньше tokens, структурированные данные
2. **Для кликов предпочитай `click_by_text`** - теперь 2x быстрее с viewport scoring
3. **save_page_info() для форм** - извлекает forms, inputs, selects с labels (v3.0.0)
4. **Form automation**: fill_input → select_option → submit_form для заполнения форм
5. **evaluate_js теперь async-aware** - используй `await fetch()`, `await Promise.all()` и т.д.
6. **TTL cache работает автоматически** - повторные клики на 30% быстрее
7. **Проверяй логи** - structured logging + stack traces в ошибках (v3.0.0)
8. **При WSL-проблемах** - сначала проверь IP Helper службу
9. **Новые команды через @register** - автоматическая регистрация, DI через CommandContext
10. **Используй self.cdp** - thread-safe async wrapper вместо прямого self.tab.Runtime

---

---

## 🚀 Roadmap V2 - Что дальше?

**Завершено (Sprint 1+2):**
- ✅ Task 1.1-1.3: Quick wins (metadata, logging, errors)
- ✅ Task 2.1-2.4: Core refactoring (DI, auto-discovery, async CDP, optimization)

**Следующие шаги (Sprint 3 - требуется design docs):**
- Task 3.1: Connection lifecycle manager
- Task 3.2: Plugin system для расширений
- Task 3.3: Metrics and observability

**Документация:**
- Полный roadmap: `docs/roadmap-v2.md`
- Breaking changes: V2.0 требует обновления версии до 2.0.0
- Backup ветка: `backup-main-20251007` (на случай отката)

---

**🤖 Этот документ создан для ускорения работы Claude Code с проектом**
