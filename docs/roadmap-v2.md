# MCP Comet Browser - Roadmap V2 (Refactoring)

> **Полная дорожная карта рефакторинга проекта**
> Создано: 2025-10-07
> Базовый контекст: `/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md`

---

## 📖 Обязательное чтение перед началом

**КРИТИЧНО:** Перед выполнением любого шага из этого roadmap, ты ОБЯЗАН прочитать:

```
/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
```

Этот файл содержит:
- Полную архитектуру проекта
- Описание всех 29 команд
- Известные проблемы и workaround'ы
- Особенности WSL2 setup
- Паттерны кода

**БЕЗ ПРОЧТЕНИЯ ЭТОГО ФАЙЛА НЕ НАЧИНАЙ РАБОТУ!**

---

## 🎯 Цель рефакторинга

Убрать "костыли" из текущей реализации:

1. ❌ Dependency injection через kwargs с хардкодом команд
2. ❌ Ручная регистрация 29 команд
3. ❌ Dummy instances для получения metadata
4. ❌ State mutation через return values команд
5. ❌ 8 команд-редиректов на save_page_info
6. ❌ Sync CDP calls в async коде
7. ❌ Разрозненный logging без структуры

---

## 📋 Структура Roadmap

### **Sprint 1: Quick Wins** (1-2 дня, не ломает API)
- Task 1.1: Command metadata as class attributes
- Task 1.2: Structured logging
- Task 1.3: Error hierarchy

### **Sprint 2: Core Refactoring** (3-5 дней, breaking changes)
- Task 2.1: CommandContext для Dependency Injection
- Task 2.2: Auto-discovery команд через decorators
- Task 2.3: Async CDP wrapper
- Task 2.4: Убрать редиректы команд

### **Sprint 3: Advanced Features** (опционально)
- Task 3.1: Connection lifecycle manager
- Task 3.2: Plugin system для команд
- Task 3.3: Metrics и observability

---

---

# 🚀 Sprint 1: Quick Wins

## Task 1.1: Command metadata as class attributes

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md, раздел "Архитектура"):**

В файле `mcp/protocol.py:159` есть костыль:
```python
def list_tools(self) -> Dict[str, Any]:
    tools = []
    for cmd_name, cmd_class in self.commands.items():
        cmd_instance = cmd_class(tab=None)  # ❌ Создаём объект с невалидным tab!
        tools.append(cmd_instance.to_mcp_tool())
    return {"tools": tools}
```

**Почему это плохо:**
- Команда создаётся с `tab=None`, что нарушает контракт (команда ожидает валидный pychrome.Tab)
- Если команда обращается к `self.tab` в `__init__` или `to_mcp_tool()`, будет NPE
- Бессмысленное создание объекта только для чтения метаданных

**Текущая реализация Command (из CLAUDE.md):**
```python
class Command(ABC):
    def __init__(self, tab):
        self.tab = tab

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]: pass

    def to_mcp_tool(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }
```

---

### 🎯 Цель задачи

Переделать метаданные команд (name, description, input_schema) из instance properties в class attributes, чтобы можно было получать их без создания объекта.

---

### ✅ Критерии приёмки

1. ✅ Метаданные команды доступны через `CommandClass.name` без создания instance
2. ✅ `to_mcp_tool()` стал classmethod и не требует создания объекта
3. ✅ `protocol.py:list_tools()` не создаёт dummy instances
4. ✅ Все 29 команд обновлены и работают
5. ✅ Тесты проходят (если есть)

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Привет! Мне нужно выполнить Task 1.1 из roadmap-v2.md.

ОБЯЗАТЕЛЬНО:
1. Прочитай контекст проекта из /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Прочитай текущую реализацию commands/base.py
3. Изучи как минимум 3 примера команд: commands/navigation.py, commands/interaction.py, commands/tabs.py

ЗАДАЧА:
Переделать метаданные команд (name, description, input_schema) из instance properties в class attributes.

ШАГИ:
1. Обнови commands/base.py:
   - Сделай name, description, input_schema атрибутами класса (используй typing.ClassVar)
   - Переделай to_mcp_tool() в @classmethod, чтобы он работал без instance
   - Добавь docstring с объяснением изменений

2. Обнови ВСЕ 29 команд (список в CLAUDE.md, раздел "🛠️ 29 Инструментов"):
   - Замени @property def name(self) на name: ClassVar[str] = "..."
   - То же для description и input_schema
   - Проверь что команды не обращаются к self.tab в этих атрибутах

3. Обнови mcp/protocol.py:
   - В методе list_tools() убери создание cmd_instance
   - Вызывай cmd_class.to_mcp_tool() напрямую на классе

4. Протестируй:
   - Запусти server.py
   - Выполни JSON-RPC запрос: {"jsonrpc":"2.0","id":1,"method":"tools/list"}
   - Убедись что все 29 команд в списке
   - Попробуй выполнить несколько команд (open_url, click_by_text)

5. Создай коммит с сообщением:
   "refactor: Convert command metadata to class attributes

   - Метаданные теперь ClassVar вместо instance properties
   - to_mcp_tool() стал classmethod
   - Убраны dummy instances из protocol.py:list_tools()

   Fixes: Task 1.1 from roadmap-v2.md"

ВАЖНО:
- Не меняй логику выполнения команд (execute())
- Не трогай dependency injection пока (это Task 2.1)
- Сохрани обратную совместимость API
```

---

### 🔍 Файлы для изменения

1. **commands/base.py** - базовый класс Command
2. **commands/*.py** - все 29 команд (список в CLAUDE.md)
3. **mcp/protocol.py** - метод list_tools()

---

### 🧪 Как проверить результат

```bash
# 1. Запустить сервер
python3 server.py &

# 2. Проверить список команд
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py

# 3. Проверить что команды работают
# (через Claude Code или напрямую через JSON-RPC)

# 4. Проверить что нет dummy instances
# Добавить временно в protocol.py:159 print и убедиться что не печатается
```

---

### ⚠️ Возможные проблемы

**Проблема:** Некоторые команды могут динамически формировать description или schema
**Решение:** Оставь для них instance properties, но добавь комментарий почему

**Проблема:** Забыл обновить какую-то команду
**Решение:** Используй grep для поиска всех @property def name в commands/

**Проблема:** Тесты падают
**Решение:** Обнови тесты чтобы использовали CommandClass.name вместо instance.name

---

---

## Task 1.2: Structured logging

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md):**

Логирование разрозненно по всему коду:

```python
# commands/interaction.py
print("[MCP] click_by_text: searching for 'Главная'...", file=sys.stderr)
print("[MCP] ✓ Successfully clicked: 'Главная'", file=sys.stderr)

# browser/connection.py
print(f"Tab connection lost: {str(e)}, reconnecting...", file=sys.stderr)

# mcp/protocol.py
print("MCP Comet Server starting...", file=sys.stderr)
```

**Проблемы:**
- ❌ Нет единого формата логов
- ❌ Нельзя фильтровать по уровням (DEBUG/INFO/ERROR)
- ❌ Нет timestamp'ов в некоторых логах
- ❌ Невозможно настроить verbosity через ENV
- ❌ Разные префиксы ([MCP], без префикса)

---

### 🎯 Цель задачи

Внедрить структурированное логирование через стандартный модуль `logging` с единым форматом и уровнями важности.

---

### ✅ Критерии приёмки

1. ✅ Все `print(..., file=sys.stderr)` заменены на `logger.info/debug/error()`
2. ✅ Единый формат: `[TIMESTAMP] LEVEL [module] message`
3. ✅ Уровень логирования настраивается через ENV переменную `MCP_LOG_LEVEL`
4. ✅ Модули используют именованные логгеры: `logging.getLogger('mcp_comet.commands')`
5. ✅ Логи не попадают в stdout (только stderr)

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 1.2 из roadmap-v2.md.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Изучи текущее использование print(..., file=sys.stderr) в коде

ЗАДАЧА:
Внедрить структурированное логирование через модуль logging.

ШАГИ:

1. Создай mcp/logging_config.py:
   ```python
   import logging
   import sys
   import os

   def setup_logging():
       """Setup structured logging for MCP server"""
       level = os.environ.get('MCP_LOG_LEVEL', 'INFO').upper()

       formatter = logging.Formatter(
           '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )

       handler = logging.StreamHandler(sys.stderr)
       handler.setFormatter(formatter)

       logger = logging.getLogger('mcp_comet')
       logger.setLevel(getattr(logging, level, logging.INFO))
       logger.addHandler(handler)
       logger.propagate = False

       return logger

   def get_logger(name: str):
       """Get logger for specific module"""
       return logging.getLogger(f'mcp_comet.{name}')
   ```

2. Обнови server.py:
   - Импортируй и вызови setup_logging() в начале main()
   - Замени print на logger.info

3. Обнови mcp/protocol.py:
   - Создай logger = get_logger('protocol')
   - Замени все print на logger.info/debug/error
   - Startup messages → logger.info
   - Errors → logger.error

4. Обнови browser/connection.py:
   - logger = get_logger('connection')
   - Замени print на logger
   - Reconnection → logger.warning
   - Errors → logger.error

5. Обнови browser/cursor.py (если есть логи):
   - logger = get_logger('cursor')

6. Обнови команды (особенно commands/interaction.py с детальными логами):
   - logger = get_logger('commands.interaction')
   - [MCP] click_by_text: ... → logger.info("Searching for text: %s", text)
   - [MCP] ✓ Successfully ... → logger.info("Successfully clicked: %s", text)
   - [MCP] ✗ Failed ... → logger.warning("Failed to click: %s", text)
   - [MCP] ✗ Exception ... → logger.error("Exception during click", exc_info=True)

7. Обнови другие команды с логами:
   - commands/devtools.py
   - commands/diagnostics.py
   - и т.д.

8. Создай .env.example:
   ```
   # Logging level: DEBUG, INFO, WARNING, ERROR
   MCP_LOG_LEVEL=INFO
   ```

9. Обнови README.md:
   - Добавь секцию "Logging"
   - Объясни MCP_LOG_LEVEL
   - Покажи примеры

10. Протестируй:
   - Запусти с MCP_LOG_LEVEL=DEBUG
   - Проверь формат логов
   - Убедись что логи только в stderr

11. Создай коммит:
   "feat: Add structured logging with configurable levels

   - Новый модуль mcp/logging_config.py
   - Все print заменены на logger.info/debug/error
   - Единый формат: [TIMESTAMP] LEVEL [module] message
   - Настройка через MCP_LOG_LEVEL env var

   Fixes: Task 1.2 from roadmap-v2.md"

ВАЖНО:
- НЕ удаляй существующие логи, только замени формат
- Используй logger.debug для подробных логов (координаты, DOM tree)
- Используй logger.warning для recoverable errors
- Используй logger.error для critical failures
- Не логируй sensitive data (passwords, tokens)
```

---

### 🔍 Файлы для изменения

1. **mcp/logging_config.py** (новый файл)
2. **server.py** - setup logging
3. **mcp/protocol.py** - заменить print
4. **browser/connection.py** - заменить print
5. **browser/cursor.py** - заменить print (если есть)
6. **commands/*.py** - заменить print во всех командах с логами
7. **.env.example** (новый файл)
8. **README.md** - добавить секцию Logging

---

### 🧪 Как проверить результат

```bash
# 1. Запуск с разными уровнями логирования
MCP_LOG_LEVEL=DEBUG python3 server.py

# 2. Проверить формат
# Должен быть: [2025-10-07 12:34:56] INFO     [mcp_comet.protocol] MCP Comet Server starting...

# 3. Проверить что логи только в stderr
python3 server.py 2>logs.txt 1>output.txt
# logs.txt должен содержать логи, output.txt - только JSON-RPC responses

# 4. Проверить разные уровни
MCP_LOG_LEVEL=ERROR python3 server.py  # Должны быть только ERROR
MCP_LOG_LEVEL=DEBUG python3 server.py  # Должны быть все логи
```

---

### ⚠️ Возможные проблемы

**Проблема:** Логи дублируются (появляются 2 раза)
**Решение:** Установи `logger.propagate = False` для корневого логгера

**Проблема:** Логи попадают в stdout и ломают JSON-RPC
**Решение:** Убедись что handler = StreamHandler(sys.stderr), НЕ stdout

**Проблема:** Забыл заменить какой-то print
**Решение:** `grep -r "print.*sys\.stderr" .` для поиска всех оставшихся

---

---

## Task 1.3: Error hierarchy

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md):**

В `mcp/protocol.py:142-150` все ошибки ловятся через `Exception`:

```python
try:
    result = await self.call_tool(tool_name, tool_params)
except Exception as e:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32000,  # ❌ Всегда один и тот же код
            "message": str(e)
        }
    }
```

**Проблемы:**
- ❌ Невозможно отличить типы ошибок (валидация, браузер, CDP, логика)
- ❌ Всегда возвращается `-32000` (Server error)
- ❌ Нет контекста ошибки (в каком модуле, какая команда)
- ❌ Silent failures в connection.py (try: ... except: pass)
- ❌ Нет специфичных JSON-RPC error codes

**JSON-RPC 2.0 стандартные коды:**
- `-32700` Parse error
- `-32600` Invalid Request
- `-32601` Method not found
- `-32602` Invalid params
- `-32603` Internal error
- `-32000 to -32099` Server error (reserved)

---

### 🎯 Цель задачи

Создать иерархию типизированных исключений и правильно обрабатывать их в protocol.py.

---

### ✅ Критерии приёмки

1. ✅ Создана иерархия исключений в `mcp/errors.py`
2. ✅ Каждое исключение имеет свой JSON-RPC код
3. ✅ `protocol.py` обрабатывает ошибки по типу и возвращает правильные коды
4. ✅ Убраны все `except: pass` из connection.py
5. ✅ Команды бросают типизированные исключения вместо возврата `{"success": False}`

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 1.3 из roadmap-v2.md.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Изучи текущую обработку ошибок в mcp/protocol.py
3. Найди все места с try-except в коде

ЗАДАЧА:
Создать иерархию типизированных исключений и правильную обработку ошибок.

ШАГИ:

1. Создай mcp/errors.py:
   ```python
   """MCP error hierarchy with JSON-RPC 2.0 error codes"""

   class MCPError(Exception):
       """Base MCP error with JSON-RPC code"""
       code: int = -32000

       def __init__(self, message: str, data: dict = None):
           super().__init__(message)
           self.message = message
           self.data = data or {}

       def to_json_rpc(self):
           """Convert to JSON-RPC error format"""
           error = {
               "code": self.code,
               "message": self.message
           }
           if self.data:
               error["data"] = self.data
           return error

   # Browser connection errors
   class BrowserConnectionError(MCPError):
       code = -32001

   class BrowserDisconnectedError(BrowserConnectionError):
       code = -32002

   class TabNotFoundError(BrowserConnectionError):
       code = -32003

   # Command errors
   class CommandError(MCPError):
       code = -32010

   class CommandNotFoundError(CommandError):
       code = -32601  # JSON-RPC "Method not found"

   class CommandValidationError(CommandError):
       code = -32602  # JSON-RPC "Invalid params"

   class CommandExecutionError(CommandError):
       code = -32011

   # CDP protocol errors
   class CDPError(MCPError):
       code = -32020

   class CDPTimeoutError(CDPError):
       code = -32021

   class CDPProtocolError(CDPError):
       code = -32022

   # Element interaction errors
   class ElementNotFoundError(CommandError):
       code = -32030

   class ElementNotClickableError(CommandError):
       code = -32031

   class ElementNotVisibleError(CommandError):
       code = -32032
   ```

2. Обнови mcp/protocol.py:
   - Импортируй все ошибки из mcp/errors
   - В handle_request() обрабатывай каждый тип:
   ```python
   try:
       # ... existing code ...
   except CommandNotFoundError as e:
       return {
           "jsonrpc": "2.0",
           "id": request_id,
           "error": e.to_json_rpc()
       }
   except CommandValidationError as e:
       logger.warning("Validation error: %s", e)
       return {
           "jsonrpc": "2.0",
           "id": request_id,
           "error": e.to_json_rpc()
       }
   except BrowserConnectionError as e:
       logger.error("Browser connection error: %s", e)
       return {
           "jsonrpc": "2.0",
           "id": request_id,
           "error": e.to_json_rpc()
       }
   except CommandError as e:
       logger.error("Command error: %s", e)
       return {
           "jsonrpc": "2.0",
           "id": request_id,
           "error": e.to_json_rpc()
       }
   except Exception as e:
       # Unexpected error
       logger.exception("Unexpected error")
       return {
           "jsonrpc": "2.0",
           "id": request_id,
           "error": {
               "code": -32603,
               "message": "Internal error"
           }
       }
   ```

   - В call_tool() брось CommandNotFoundError если команды нет:
   ```python
   if tool_name not in self.commands:
       raise CommandNotFoundError(f"Unknown tool: {tool_name}")
   ```

3. Обнови browser/connection.py:
   - Импортируй ошибки
   - В connect() брось BrowserConnectionError вместо ConnectionError
   - В ensure_connected() брось BrowserDisconnectedError
   - УБЕРИ все `except: pass` и замени на:
   ```python
   except Exception as e:
       logger.warning("Failed to stop tab: %s", e)
       # Но НЕ raise, т.к. это cleanup
   ```

4. Обнови commands/base.py:
   - Добавь метод _raise_not_found():
   ```python
   def _raise_not_found(self, selector: str):
       raise ElementNotFoundError(
           f"Element not found: {selector}",
           data={"selector": selector}
       )
   ```

5. Обнови команды для использования исключений:
   - commands/interaction.py:
     - Вместо return {"success": False, "message": "Element not found"}
     - Используй raise ElementNotFoundError(...)
   - commands/navigation.py:
     - Брось CommandValidationError если URL невалидный
   - commands/tabs.py:
     - Брось TabNotFoundError если tab_id не найден

6. ВАЖНО: Сохрани обратную совместимость для команд, которые возвращают {"success": False}:
   - В protocol.py оберни execute() в try-catch:
   ```python
   try:
       result = await cmd_instance.execute(**arguments)
       # Check old-style error format
       if isinstance(result, dict) and result.get('success') is False:
           raise CommandExecutionError(
               result.get('message', 'Command failed'),
               data=result
           )
       return result
   except MCPError:
       raise  # Re-raise typed errors
   except Exception as e:
       raise CommandExecutionError(str(e)) from e
   ```

7. Создай тесты (если есть test framework):
   - test_errors.py для проверки JSON-RPC форматирования
   - Проверь что каждая ошибка возвращает правильный код

8. Обнови CLAUDE.md:
   - Добавь секцию "Error Codes" с таблицей кодов
   - Объясни как обрабатываются ошибки

9. Протестируй:
   - Вызови несуществующую команду → должен вернуть -32601
   - Передай невалидные параметры → -32602
   - Отключи браузер и вызови команду → -32001
   - Попробуй кликнуть по несуществующему элементу → -32030

10. Создай коммит:
    "feat: Add typed error hierarchy with JSON-RPC codes

    - Новый модуль mcp/errors.py с иерархией исключений
    - Каждая ошибка имеет специфичный JSON-RPC код
    - Убраны silent failures из connection.py
    - Команды бросают типизированные исключения
    - Обратная совместимость через wrapper в protocol.py

    Error codes:
    - -32001: Browser connection error
    - -32010: Command error
    - -32030: Element not found
    - и т.д.

    Fixes: Task 1.3 from roadmap-v2.md"

ВАЖНО:
- НЕ ломай существующие команды - добавь wrapper для обратной совместимости
- Логируй исключения перед возвратом ошибки
- Используй exc_info=True для логирования трейсов
- Не показывай внутренние детали пользователю (security)
```

---

### 🔍 Файлы для изменения

1. **mcp/errors.py** (новый файл)
2. **mcp/protocol.py** - обработка ошибок
3. **browser/connection.py** - использование ошибок
4. **commands/base.py** - helper методы
5. **commands/*.py** - использование исключений в командах
6. **.claude/CLAUDE.md** - документация error codes

---

### 🧪 Как проверить результат

```bash
# 1. Вызвать несуществующую команду
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nonexistent"}}' | python3 server.py
# Должен вернуть: {"error": {"code": -32601, "message": "Unknown tool: nonexistent"}}

# 2. Передать невалидные параметры
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"open_url"}}' | python3 server.py
# Должен вернуть: {"error": {"code": -32602, ...}}

# 3. Проверить что логи содержат детали ошибок
MCP_LOG_LEVEL=DEBUG python3 server.py

# 4. Отключить браузер и попробовать команду
# Должен вернуть -32001 (Browser connection error)
```

---

### ⚠️ Возможные проблемы

**Проблема:** Старые команды ломаются т.к. возвращали dict с success=False
**Решение:** Wrapper в protocol.py для обратной совместимости (см. шаг 6)

**Проблема:** Слишком много деталей в ошибках (security issue)
**Решение:** Логируй детали, но возвращай generic message пользователю

**Проблема:** Трейсбеки слишком длинные
**Решение:** Используй `raise ... from e` для сохранения цепочки, но контролируй вывод

---

---

# 🔧 Sprint 2: Core Refactoring

## Task 2.1: CommandContext для Dependency Injection

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md, protocol.py:177-187):**

```python
# ❌ ГЛАВНЫЙ КОСТЫЛЬ ПРОЕКТА:
if tool_name in ['click', 'click_by_text', 'move_cursor', 'force_click']:
    arguments['cursor'] = self.connection.cursor
elif tool_name == 'open_url':
    arguments['cursor'] = self.connection.cursor
elif tool_name in ['get_console_logs', 'devtools_report']:
    arguments['console_logs'] = self.connection.console_logs
elif tool_name == 'enable_console_logging':
    arguments['connection'] = self.connection
elif tool_name in ['list_tabs', 'create_tab', 'close_tab', 'switch_tab', 'open_devtools_ui']:
    arguments['browser'] = self.connection.browser
    arguments['current_tab'] = self.connection.tab
```

**Проблемы:**
- ❌ Хардкод списка команд (4+ условия)
- ❌ При добавлении команды нужно помнить добавить её сюда
- ❌ Команда не декларирует свои зависимости
- ❌ Магические kwargs - невозможно валидировать сигнатуру
- ❌ Нарушение SRP - protocol.py знает какие зависимости нужны каждой команде

**Текущая сигнатура команд:**
```python
class ClickByTextCommand(Command):
    async def execute(self, text: str, cursor=None, exact=False, tag=None):
        # cursor приходит через kwargs, но не объявлен в input_schema
        # Непонятно откуда он берётся
```

---

### 🎯 Цель задачи

Создать `CommandContext` для явного декларирования и инъекции зависимостей команд. Убрать хардкод из protocol.py.

---

### ✅ Критерии приёмки

1. ✅ Создан `CommandContext` с полями: tab, cursor, browser, console_logs
2. ✅ Команды декларируют зависимости через class attributes: `requires_cursor = True`
3. ✅ Валидация зависимостей происходит при создании команды
4. ✅ Убран весь хардкод из protocol.py:177-187
5. ✅ Все 29 команд обновлены и работают
6. ✅ Сигнатуры execute() чистые - нет магических kwargs

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 2.1 из roadmap-v2.md - самое важное изменение в архитектуре.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Изучи текущую инъекцию зависимостей в mcp/protocol.py:177-187
3. Посмотри как команды получают cursor и browser

ЗАДАЧА:
Создать CommandContext для явной декларации зависимостей и убрать хардкод.

ШАГИ:

1. Создай commands/context.py:
   ```python
   """Command execution context with dependencies"""
   from dataclasses import dataclass
   from typing import Optional, List, Dict, Any
   import pychrome

   @dataclass
   class CommandContext:
       """Context for command execution

       Contains all dependencies a command might need.
       Commands declare requirements via class attributes.
       """
       tab: pychrome.Tab
       cursor: Optional['AICursor'] = None
       browser: Optional[pychrome.Browser] = None
       console_logs: Optional[List[Dict[str, Any]]] = None

       def validate_requirements(self, command_class):
           """Validate that context provides all required dependencies"""
           from mcp.errors import CommandValidationError

           if getattr(command_class, 'requires_cursor', False) and not self.cursor:
               raise CommandValidationError(
                   f"Command {command_class.name} requires cursor but it's not available"
               )

           if getattr(command_class, 'requires_browser', False) and not self.browser:
               raise CommandValidationError(
                   f"Command {command_class.name} requires browser but it's not available"
               )

           if getattr(command_class, 'requires_console_logs', False) and not self.console_logs:
               raise CommandValidationError(
                   f"Command {command_class.name} requires console_logs but they're not available"
               )
   ```

2. Обнови commands/base.py:
   ```python
   from typing import ClassVar, Dict, Any
   from abc import ABC, abstractmethod
   from .context import CommandContext

   class Command(ABC):
       """Base class for MCP commands

       Commands should declare their dependencies:
       - requires_cursor: bool = True if needs AICursor
       - requires_browser: bool = True if needs Browser instance
       - requires_console_logs: bool = True if needs console logs
       """

       # Metadata (from Task 1.1)
       name: ClassVar[str]
       description: ClassVar[str]
       input_schema: ClassVar[Dict[str, Any]]

       # Dependency requirements
       requires_cursor: ClassVar[bool] = False
       requires_browser: ClassVar[bool] = False
       requires_console_logs: ClassVar[bool] = False

       def __init__(self, context: CommandContext):
           """Initialize command with context

           Args:
               context: CommandContext with dependencies

           Raises:
               CommandValidationError: if required dependencies missing
           """
           context.validate_requirements(self.__class__)
           self.context = context

       # Convenience properties
       @property
       def tab(self):
           return self.context.tab

       @property
       def cursor(self):
           return self.context.cursor

       @property
       def browser(self):
           return self.context.browser

       @property
       def console_logs(self):
           return self.context.console_logs

       @abstractmethod
       async def execute(self, **kwargs) -> Dict[str, Any]:
           """Execute command with user parameters

           Note: **kwargs contains ONLY user parameters from input_schema,
           NOT internal dependencies (those are in self.context)
           """
           pass

       @classmethod
       def to_mcp_tool(cls) -> Dict[str, Any]:
           """Convert to MCP tool definition"""
           return {
               "name": cls.name,
               "description": cls.description,
               "inputSchema": cls.input_schema
           }
   ```

3. Обнови mcp/protocol.py:
   ```python
   # В call_tool() метод:
   async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
       """Call a tool by name with arguments"""
       if tool_name not in self.commands:
           raise CommandNotFoundError(f"Unknown tool: {tool_name}")

       # Ensure connection is valid
       await self.connection.ensure_connected()

       # ✅ НОВЫЙ КОД: Создаём контекст с ВСЕМИ зависимостями
       context = CommandContext(
           tab=self.connection.tab,
           cursor=self.connection.cursor,
           browser=self.connection.browser,
           console_logs=self.connection.console_logs
       )

       # Get command class and instantiate with context
       cmd_class = self.commands[tool_name]
       cmd_instance = cmd_class(context=context)

       # ❌ УДАЛИ ВЕСЬ БЛОК С if tool_name in [...] (строки 177-187)

       # Execute command with ONLY user parameters
       result = await cmd_instance.execute(**arguments)

       # Handle special cases (tab switching, etc. - оставь как есть)
       if tool_name == 'switch_tab' and result.get('success') and 'newTab' in result:
           self.connection.tab = result.pop('newTab')
           self.connection.cursor = self.connection.cursor.__class__(self.connection.tab)
           await self.connection.cursor.initialize()

       if tool_name == 'close_tab' and result.get('wasCurrentTab'):
           self.connection.tab = None

       return result
   ```

4. Обнови команды для декларации зависимостей:

   **commands/interaction.py:**
   ```python
   class ClickCommand(Command):
       requires_cursor = True  # ✅ Декларативно

       async def execute(self, selector: str, **kwargs):
           # ✅ Больше не нужен cursor в kwargs
           cursor = self.cursor  # Гарантированно есть
           # ... rest of code ...

   class ClickByTextCommand(Command):
       requires_cursor = True

       async def execute(self, text: str, exact: bool = False, tag: str = None):
           # ✅ Чистая сигнатура - только user parameters
           cursor = self.cursor
           # ... rest of code ...

   class MoveCursorCommand(Command):
       requires_cursor = True
       # ...
   ```

   **commands/navigation.py:**
   ```python
   class OpenUrlCommand(Command):
       requires_cursor = True

       async def execute(self, url: str):
           # ...
   ```

   **commands/devtools.py:**
   ```python
   class GetConsoleLogsCommand(Command):
       requires_console_logs = True

       async def execute(self, clear: bool = False):
           logs = self.console_logs  # ✅
           # ...
   ```

   **commands/tabs.py:**
   ```python
   class ListTabsCommand(Command):
       requires_browser = True

       async def execute(self):
           browser = self.browser  # ✅
           # ...

   class CreateTabCommand(Command):
       requires_browser = True
       # ...

   class SwitchTabCommand(Command):
       requires_browser = True
       # ...
   ```

   **commands/helpers.py:**
   ```python
   class ForceClickCommand(Command):
       requires_cursor = True
       # ...

   class DebugElementCommand(Command):
       # Не требует cursor
       requires_cursor = False
       # ...
   ```

   **commands/diagnostics.py:**
   ```python
   class EnableConsoleLoggingCommand(Command):
       # Специальный случай - нужен connection
       # Обсудим позже как обработать
   ```

5. Специальные случаи:

   **EnableConsoleLoggingCommand:**
   Эта команда нужен полный connection объект. Варианты:

   A) Добавь connection в CommandContext:
   ```python
   @dataclass
   class CommandContext:
       tab: pychrome.Tab
       connection: Optional['BrowserConnection'] = None  # ✅
       # ...

   class EnableConsoleLoggingCommand(Command):
       requires_connection = True

       async def execute(self):
           await self.context.connection.force_enable_console_logging()
   ```

   B) Или пусть вызывает методы tab напрямую (предпочтительно):
   ```python
   class EnableConsoleLoggingCommand(Command):
       async def execute(self):
           # Вместо connection.force_enable_console_logging()
           # вызывай методы tab напрямую
           self.tab.Console.enable()
           self.tab.Runtime.enable()
           # ...
   ```

   Рекомендую вариант B - команда не должна знать о connection.

6. Обнови CLAUDE.md:
   - Секция "Архитектура" → обнови описание DI
   - Удали упоминание хардкода в строке 178
   - Добавь примеры декларации зависимостей
   - Обнови секцию "Добавить новую команду":
     ```markdown
     ### 1. Добавить новую команду
     1. Создать класс в commands/ наследуясь от Command
     2. Реализовать execute(), name, description, input_schema
     3. Декларировать зависимости: requires_cursor = True
     4. Зарегистрировать через @CommandRegistry.register (Task 2.2)
     ```

7. Протестируй ВСЕ команды:
   ```bash
   # Проверь команды с cursor
   mcp__comet-browser__click_by_text(text="Test")
   mcp__comet-browser__move_cursor(x=100, y=100)

   # Проверь команды с browser
   mcp__comet-browser__list_tabs()
   mcp__comet-browser__create_tab()

   # Проверь команды с console_logs
   mcp__comet-browser__get_console_logs()

   # Проверь команды без зависимостей
   mcp__comet-browser__get_text(selector="body")
   ```

8. Проверь валидацию:
   - Временно удали cursor из context
   - Попробуй вызвать click_by_text
   - Должна выброситься CommandValidationError

9. Создай коммит:
   "refactor: Implement CommandContext for dependency injection

   BREAKING CHANGE: Command constructor now takes CommandContext

   - Новый класс CommandContext в commands/context.py
   - Команды декларируют зависимости через class attributes
   - Валидация зависимостей при создании команды
   - Убран весь хардкод из protocol.py (строки 177-187)
   - Чистые сигнатуры execute() - только user parameters

   Migration:
   - Старый: Command(tab=...) + cursor через kwargs
   - Новый: Command(context=CommandContext(...))

   Fixes: Task 2.1 from roadmap-v2.md"

ВАЖНО:
- Это BREAKING CHANGE - обнови версию в protocol.py до 2.0.0
- Проверь ВСЕ 29 команд (список в CLAUDE.md)
- Убедись что валидация работает
- Не забудь обновить CLAUDE.md
```

---

### 🔍 Файлы для изменения

1. **commands/context.py** (новый файл)
2. **commands/base.py** - новый __init__ с CommandContext
3. **mcp/protocol.py** - убрать хардкод, создавать context
4. **commands/*.py** - ВСЕ 29 команд:
   - interaction.py (click, click_by_text, scroll, move_cursor)
   - navigation.py (open_url, get_text)
   - devtools.py (get_console_logs, inspect_element, etc.)
   - tabs.py (list_tabs, create_tab, close_tab, switch_tab)
   - helpers.py (debug_element, force_click)
   - diagnostics.py (enable_console_logging, diagnose_page)
   - evaluation.py (evaluate_js)
   - screenshot.py
   - search.py
   - save_page_info.py
   - page_snapshot.py
   - devtools_report.py
   - open_devtools_url.py
5. **.claude/CLAUDE.md** - обновить документацию

---

### 🧪 Как проверить результат

```bash
# 1. Проверить что protocol.py не содержит хардкод
grep -n "if tool_name in" mcp/protocol.py
# Не должно быть строк 177-187

# 2. Проверить декларации зависимостей
grep -r "requires_cursor" commands/
grep -r "requires_browser" commands/
grep -r "requires_console_logs" commands/

# 3. Запустить сервер и протестировать команды
python3 server.py

# 4. Проверить валидацию (временно сломай context)
# В protocol.py замени cursor=self.connection.cursor на cursor=None
# Попробуй вызвать click - должна быть CommandValidationError
```

---

### ⚠️ Возможные проблемы

**Проблема:** Забыл обновить какую-то команду
**Решение:** Grep для поиска всех Command классов, проверь каждый

**Проблема:** Circular import между context.py и base.py
**Решение:** Используй TYPE_CHECKING и forward references

**Проблема:** Команда требует специфичную зависимость (не cursor/browser/console_logs)
**Решение:** Добавь новое поле в CommandContext или переделай команду

**Проблема:** Тесты падают
**Решение:** Обнови моки чтобы передавать CommandContext

---

---

## Task 2.2: Auto-discovery команд через decorators

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md, protocol.py:36-82):**

```python
def _register_commands(self):
    """Register all available commands"""
    # Navigation commands
    self.commands['open_url'] = OpenUrlCommand
    self.commands['get_text'] = GetTextCommand

    # Interaction commands
    self.commands['click'] = ClickCommand
    self.commands['click_by_text'] = ClickByTextCommand
    # ... ещё 25 команд ...
    self.commands['devtools_report'] = DevToolsReportCommand
```

**47 строк ручной регистрации!**

**Проблемы:**
- ❌ Легко забыть зарегистрировать новую команду
- ❌ Дублирование: имя в строке + класс
- ❌ Нет автообнаружения команд
- ❌ Невозможно загрузить команды из плагинов/расширений
- ❌ Нужно импортировать каждую команду в protocol.py

---

### 🎯 Цель задачи

Создать систему автоматической регистрации команд через декораторы и динамический импорт.

---

### ✅ Критерии приёмки

1. ✅ Создан `CommandRegistry` с декоратором `@register`
2. ✅ Команды регистрируются автоматически при импорте модуля
3. ✅ `protocol.py` не содержит списка команд - всё через registry
4. ✅ Поддержка динамической загрузки команд из директории
5. ✅ Все 29 команд зарегистрированы и работают

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 2.2 из roadmap-v2.md.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Посмотри ручную регистрацию в mcp/protocol.py:36-82
3. Убедись что Task 2.1 (CommandContext) уже выполнен

ЗАДАЧА:
Создать систему автоматической регистрации команд через декораторы.

ШАГИ:

1. Создай commands/registry.py:
   ```python
   """Command registry for auto-discovery"""
   from typing import Dict, Type, Optional
   import importlib
   import pkgutil
   import logging

   logger = logging.getLogger('mcp_comet.registry')

   class CommandRegistry:
       """Registry for automatic command discovery

       Usage:
           @CommandRegistry.register()
           class MyCommand(Command):
               name = "my_command"
               ...
       """
       _commands: Dict[str, Type['Command']] = {}

       @classmethod
       def register(cls, name: Optional[str] = None):
           """Decorator for automatic command registration

           Args:
               name: Optional command name override. If not provided,
                     uses Command.name attribute.

           Example:
               @CommandRegistry.register()
               class ClickCommand(Command):
                   name = "click"
                   ...

               @CommandRegistry.register("custom_name")
               class MyCommand(Command):
                   name = "original_name"  # Will use "custom_name" instead
                   ...
           """
           def decorator(command_class: Type['Command']):
               # Use provided name or command's name attribute
               cmd_name = name if name is not None else command_class.name

               if cmd_name in cls._commands:
                   logger.warning(
                       "Command '%s' already registered, overwriting with %s",
                       cmd_name, command_class.__name__
                   )

               cls._commands[cmd_name] = command_class
               logger.debug("Registered command: %s -> %s", cmd_name, command_class.__name__)

               return command_class

           return decorator

       @classmethod
       def get(cls, name: str) -> Optional[Type['Command']]:
           """Get command class by name"""
           return cls._commands.get(name)

       @classmethod
       def get_all(cls) -> Dict[str, Type['Command']]:
           """Get all registered commands"""
           return cls._commands.copy()

       @classmethod
       def discover_commands(cls, package_name: str = 'commands'):
           """Automatically import all modules in package to trigger registration

           This will import all Python modules in the specified package,
           causing their @register decorators to execute and register commands.

           Args:
               package_name: Package name to scan for commands (default: 'commands')
           """
           try:
               package = importlib.import_module(package_name)
           except ImportError as e:
               logger.error("Failed to import package '%s': %s", package_name, e)
               return

           # Iterate over all modules in package
           for importer, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
               full_module_name = f'{package_name}.{module_name}'

               # Skip __init__ and internal modules
               if module_name.startswith('_'):
                   continue

               try:
                   importlib.import_module(full_module_name)
                   logger.debug("Imported module: %s", full_module_name)
               except Exception as e:
                   logger.error("Failed to import module '%s': %s", full_module_name, e)

           logger.info("Discovered %d commands", len(cls._commands))

       @classmethod
       def clear(cls):
           """Clear all registered commands (for testing)"""
           cls._commands.clear()
   ```

2. Обнови commands/__init__.py:
   ```python
   """Commands package with auto-discovery"""
   from .base import Command
   from .context import CommandContext
   from .registry import CommandRegistry

   __all__ = ['Command', 'CommandContext', 'CommandRegistry']
   ```

3. Обнови ВСЕ команды - добавь декоратор @register:

   **commands/navigation.py:**
   ```python
   from .base import Command
   from .registry import CommandRegistry

   @CommandRegistry.register()
   class OpenUrlCommand(Command):
       name = "open_url"
       # ... rest of code ...

   @CommandRegistry.register()
   class GetTextCommand(Command):
       name = "get_text"
       # ... rest of code ...
   ```

   **commands/interaction.py:**
   ```python
   from .registry import CommandRegistry

   @CommandRegistry.register()
   class ClickCommand(Command):
       name = "click"
       # ...

   @CommandRegistry.register()
   class ClickByTextCommand(Command):
       name = "click_by_text"
       # ...

   @CommandRegistry.register()
   class ScrollPageCommand(Command):
       name = "scroll_page"
       # ...

   @CommandRegistry.register()
   class MoveCursorCommand(Command):
       name = "move_cursor"
       # ...
   ```

   **Повтори для ВСЕХ 29 команд** (список в CLAUDE.md раздел "🛠️ 29 Инструментов"):
   - commands/devtools.py (6 команд)
   - commands/tabs.py (4 команды)
   - commands/evaluation.py (1)
   - commands/screenshot.py (1)
   - commands/search.py (2)
   - commands/helpers.py (2)
   - commands/diagnostics.py (3)
   - commands/page_snapshot.py (1)
   - commands/save_page_info.py (1)
   - commands/devtools_report.py (1)
   - commands/open_devtools_url.py (1)

4. Обнови mcp/protocol.py:
   ```python
   from commands import CommandRegistry, CommandContext
   # ❌ УДАЛИ все импорты команд (строки 7-24):
   # from commands.navigation import OpenUrlCommand, GetTextCommand
   # from commands.interaction import ...
   # и т.д.

   class MCPJSONRPCServer:
       def __init__(self):
           self.connection = BrowserConnection()
           self.connected = False

           # ✅ НОВЫЙ КОД: Автоматическая регистрация
           CommandRegistry.discover_commands('commands')
           self.commands = CommandRegistry.get_all()

           logger.info("Loaded %d commands", len(self.commands))

       # ❌ УДАЛИ метод _register_commands() полностью (строки 36-82)
   ```

5. Добавь валидацию при запуске:
   ```python
   # В protocol.py __init__ после discover_commands:
   if len(self.commands) == 0:
       raise RuntimeError("No commands discovered! Check commands/ directory.")

   # Expected commands count (update if adding new commands)
   EXPECTED_COMMANDS = 29
   if len(self.commands) != EXPECTED_COMMANDS:
       logger.warning(
           "Expected %d commands but found %d. List: %s",
           EXPECTED_COMMANDS,
           len(self.commands),
           sorted(self.commands.keys())
       )
   ```

6. Создай helper для вывода всех команд:
   ```python
   # В protocol.py или новый файл commands/cli.py
   def print_registered_commands():
       """Print all registered commands (for debugging)"""
       commands = CommandRegistry.get_all()
       print(f"\n{'='*60}")
       print(f"Registered Commands ({len(commands)}):")
       print(f"{'='*60}")

       for name, cmd_class in sorted(commands.items()):
           deps = []
           if getattr(cmd_class, 'requires_cursor', False):
               deps.append('cursor')
           if getattr(cmd_class, 'requires_browser', False):
               deps.append('browser')
           if getattr(cmd_class, 'requires_console_logs', False):
               deps.append('console_logs')

           deps_str = f" [{', '.join(deps)}]" if deps else ""
           print(f"  • {name:25s} → {cmd_class.__name__}{deps_str}")

       print(f"{'='*60}\n")

   # Вызови при запуске в debug mode:
   if os.environ.get('MCP_LOG_LEVEL') == 'DEBUG':
       print_registered_commands()
   ```

7. Обнови CLAUDE.md:
   ```markdown
   ### Добавить новую команду
   1. Создать класс в `commands/` наследуясь от `Command`
   2. Декларировать метаданные как class attributes (Task 1.1)
   3. Декларировать зависимости: `requires_cursor = True` (Task 2.1)
   4. Добавить декоратор `@CommandRegistry.register()` ✅ НОВОЕ
   5. Реализовать `execute(**kwargs)`
   6. Команда автоматически появится в списке - регистрация не нужна!

   Пример:
   ```python
   from commands.base import Command
   from commands.registry import CommandRegistry

   @CommandRegistry.register()  # ✅ Автоматическая регистрация
   class MyNewCommand(Command):
       name = "my_command"
       description = "Do something awesome"
       input_schema = {
           "type": "object",
           "properties": {
               "param": {"type": "string"}
           }
       }
       requires_cursor = True  # Если нужен cursor

       async def execute(self, param: str):
           # Implementation
           return {"success": True}
   ```
   ```

8. Создай тест (если есть test framework):
   ```python
   # tests/test_registry.py
   from commands.registry import CommandRegistry

   def test_command_registration():
       CommandRegistry.clear()

       @CommandRegistry.register()
       class TestCommand(Command):
           name = "test"
           # ...

       assert "test" in CommandRegistry.get_all()
       assert CommandRegistry.get("test") == TestCommand

   def test_discover_commands():
       CommandRegistry.clear()
       CommandRegistry.discover_commands('commands')

       commands = CommandRegistry.get_all()
       assert len(commands) >= 29  # At least our known commands
       assert "click" in commands
       assert "open_url" in commands
   ```

9. Протестируй:
   ```bash
   # С DEBUG level должен показать все команды
   MCP_LOG_LEVEL=DEBUG python3 server.py

   # Проверь что все 29 команд зарегистрированы
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py | jq '.result.tools | length'
   # Должно быть 29

   # Проверь что команды работают
   # (вызови несколько через Claude Code)
   ```

10. Создай коммит:
    "feat: Add automatic command discovery via registry

    - Новый CommandRegistry с декоратором @register
    - Автоматическое обнаружение команд через discover_commands()
    - Удалена ручная регистрация из protocol.py (47 строк)
    - Все 29 команд обновлены с декоратором @register
    - Валидация количества команд при запуске

    Benefits:
    - Невозможно забыть зарегистрировать команду
    - Поддержка динамической загрузки
    - Готовность к plugin system

    Fixes: Task 2.2 from roadmap-v2.md"

ВАЖНО:
- НЕ забудь добавить @register ко ВСЕМ 29 командам
- Проверь что все команды появляются в tools/list
- Используй grep для проверки что все команды обновлены
- Обнови CLAUDE.md с новым процессом добавления команд
```

---

### 🔍 Файлы для изменения

1. **commands/registry.py** (новый файл)
2. **commands/__init__.py** - экспорт CommandRegistry
3. **mcp/protocol.py** - убрать _register_commands(), использовать registry
4. **commands/*.py** - ВСЕ 29 команд добавить @register
5. **.claude/CLAUDE.md** - обновить процесс добавления команд

---

### 🧪 Как проверить результат

```bash
# 1. Проверить что protocol.py не содержит импортов команд
grep "from commands\." mcp/protocol.py
# Должен быть только: from commands import CommandRegistry, CommandContext

# 2. Проверить что все команды имеют декоратор
for file in commands/*.py; do
  if grep -q "class.*Command" "$file" && ! grep -q "@CommandRegistry.register" "$file"; then
    echo "Missing @register in $file"
  fi
done

# 3. Запустить с DEBUG и посмотреть список
MCP_LOG_LEVEL=DEBUG python3 server.py 2>&1 | grep "Registered command"

# 4. Проверить количество команд
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py | jq '.result.tools | length'
```

---

### ⚠️ Возможные проблемы

**Проблема:** Circular import между registry.py и base.py
**Решение:** Используй TYPE_CHECKING и forward references: `Type['Command']`

**Проблема:** Забыл добавить @register к какой-то команде
**Решение:** Валидация при запуске покажет что команд меньше 29

**Проблема:** Команды регистрируются под неправильными именами
**Решение:** Проверь что `name` class attribute совпадает с ожидаемым именем

**Проблема:** Команда импортируется но не регистрируется
**Решение:** Убедись что декоратор вызывается: `@register()` с скобками

---

---

## Task 2.3: Async CDP wrapper

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md):**

В `browser/connection.py:54` и во многих командах используются синхронные вызовы pychrome:

```python
# connection.py:54
self.tab.Runtime.evaluate(expression="1+1")  # ❌ Sync call в async функции

# commands/interaction.py
result = self.tab.Runtime.evaluate(expression=js_code)  # ❌ Sync

# commands/devtools.py
self.tab.Runtime.evaluate(expression=cmd)  # ❌ Sync
```

**Проблемы:**
- ❌ pychrome не поддерживает async natively
- ❌ Синхронные вызовы блокируют event loop
- ❌ Нет timeout'ов - может зависнуть навсегда
- ❌ Нет thread-safety (если будет concurrent access)
- ❌ Невозможно отменить долгую операцию

---

### 🎯 Цель задачи

Создать async-обёртку над pychrome Tab для правильной интеграции с asyncio и добавить timeout'ы.

---

### ✅ Критерии приёмки

1. ✅ Создан `AsyncCDP` wrapper над pychrome.Tab
2. ✅ Все CDP вызовы идут через executor с timeout'ами
3. ✅ Thread-safety через asyncio.Lock
4. ✅ Все команды обновлены для использования AsyncCDP
5. ✅ Добавлена обработка timeout'ов через CDPTimeoutError

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 2.3 из roadmap-v2.md.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Найди все места с self.tab.Runtime.evaluate() и другими CDP вызовами
3. Убедись что Task 1.3 (Error hierarchy) выполнен (нужен CDPTimeoutError)

ЗАДАЧА:
Создать async-обёртку над pychrome для правильной интеграции с asyncio.

ШАГИ:

1. Создай browser/async_cdp.py:
   ```python
   """Async wrapper for pychrome CDP calls"""
   import asyncio
   import logging
   from typing import Any, Dict, Optional
   import pychrome
   from mcp.errors import CDPTimeoutError, CDPProtocolError

   logger = logging.getLogger('mcp_comet.async_cdp')

   class AsyncCDP:
       """Async-safe wrapper for pychrome Tab

       Wraps synchronous pychrome calls in executor with timeout support.
       Provides thread-safety through asyncio.Lock.

       Usage:
           cdp = AsyncCDP(tab, default_timeout=5.0)
           result = await cdp.evaluate("1 + 1")
       """

       def __init__(self, tab: pychrome.Tab, default_timeout: float = 10.0):
           """Initialize async CDP wrapper

           Args:
               tab: pychrome Tab instance
               default_timeout: Default timeout for CDP calls in seconds
           """
           self.tab = tab
           self.default_timeout = default_timeout
           self._lock = asyncio.Lock()

       async def evaluate(
           self,
           expression: str,
           timeout: Optional[float] = None,
           **kwargs
       ) -> Dict[str, Any]:
           """Async wrapper for Runtime.evaluate

           Args:
               expression: JavaScript expression to evaluate
               timeout: Timeout in seconds (uses default if None)
               **kwargs: Additional parameters for evaluate

           Returns:
               Result dict from CDP

           Raises:
               CDPTimeoutError: If operation times out
               CDPProtocolError: If CDP returns error
           """
           timeout = timeout or self.default_timeout

           async with self._lock:
               loop = asyncio.get_event_loop()

               try:
                   result = await asyncio.wait_for(
                       loop.run_in_executor(
                           None,
                           lambda: self.tab.Runtime.evaluate(
                               expression=expression,
                               **kwargs
                           )
                       ),
                       timeout=timeout
                   )

                   # Check for CDP protocol errors
                   if 'exceptionDetails' in result:
                       exception = result['exceptionDetails']
                       raise CDPProtocolError(
                           f"CDP evaluation error: {exception.get('text', 'Unknown error')}",
                           data=exception
                       )

                   return result

               except asyncio.TimeoutError:
                   logger.error("CDP evaluate timeout after %s seconds: %s", timeout, expression[:100])
                   raise CDPTimeoutError(
                       f"CDP operation timed out after {timeout}s",
                       data={"expression": expression[:100]}
                   )
               except Exception as e:
                   if isinstance(e, (CDPTimeoutError, CDPProtocolError)):
                       raise
                   logger.error("CDP evaluate error: %s", e)
                   raise CDPProtocolError(str(e)) from e

       async def call_function(
           self,
           function_declaration: str,
           arguments: list = None,
           timeout: Optional[float] = None,
           **kwargs
       ) -> Dict[str, Any]:
           """Async wrapper for Runtime.callFunctionOn

           Args:
               function_declaration: Function source code
               arguments: Function arguments
               timeout: Timeout in seconds
               **kwargs: Additional parameters

           Returns:
               Result dict from CDP
           """
           timeout = timeout or self.default_timeout
           arguments = arguments or []

           async with self._lock:
               loop = asyncio.get_event_loop()

               try:
                   result = await asyncio.wait_for(
                       loop.run_in_executor(
                           None,
                           lambda: self.tab.Runtime.callFunctionOn(
                               functionDeclaration=function_declaration,
                               arguments=arguments,
                               **kwargs
                           )
                       ),
                       timeout=timeout
                   )

                   if 'exceptionDetails' in result:
                       exception = result['exceptionDetails']
                       raise CDPProtocolError(
                           f"CDP call error: {exception.get('text', 'Unknown')}",
                           data=exception
                       )

                   return result

               except asyncio.TimeoutError:
                   raise CDPTimeoutError(f"CDP call timed out after {timeout}s")
               except Exception as e:
                   if isinstance(e, (CDPTimeoutError, CDPProtocolError)):
                       raise
                   raise CDPProtocolError(str(e)) from e

       async def get_document(self, timeout: Optional[float] = None) -> Dict[str, Any]:
           """Async wrapper for DOM.getDocument"""
           timeout = timeout or self.default_timeout

           async with self._lock:
               loop = asyncio.get_event_loop()
               try:
                   return await asyncio.wait_for(
                       loop.run_in_executor(None, self.tab.DOM.getDocument),
                       timeout=timeout
                   )
               except asyncio.TimeoutError:
                   raise CDPTimeoutError(f"DOM.getDocument timed out after {timeout}s")

       async def query_selector(
           self,
           node_id: int,
           selector: str,
           timeout: Optional[float] = None
       ) -> Dict[str, Any]:
           """Async wrapper for DOM.querySelector"""
           timeout = timeout or self.default_timeout

           async with self._lock:
               loop = asyncio.get_event_loop()
               try:
                   return await asyncio.wait_for(
                       loop.run_in_executor(
                           None,
                           lambda: self.tab.DOM.querySelector(
                               nodeId=node_id,
                               selector=selector
                           )
                       ),
                       timeout=timeout
                   )
               except asyncio.TimeoutError:
                   raise CDPTimeoutError(f"DOM.querySelector timed out after {timeout}s")

       async def capture_screenshot(
           self,
           timeout: Optional[float] = None,
           **kwargs
       ) -> Dict[str, Any]:
           """Async wrapper for Page.captureScreenshot"""
           timeout = timeout or self.default_timeout

           async with self._lock:
               loop = asyncio.get_event_loop()
               try:
                   return await asyncio.wait_for(
                       loop.run_in_executor(
                           None,
                           lambda: self.tab.Page.captureScreenshot(**kwargs)
                       ),
                       timeout=timeout
                   )
               except asyncio.TimeoutError:
                   raise CDPTimeoutError(f"Page.captureScreenshot timed out after {timeout}s")

       # Direct access to tab for special cases
       @property
       def sync_tab(self) -> pychrome.Tab:
           """Get underlying sync tab (use with caution)"""
           return self.tab
   ```

2. Обнови browser/connection.py:
   ```python
   from .async_cdp import AsyncCDP

   class BrowserConnection:
       def __init__(self, ...):
           # ... existing code ...
           self.cdp: Optional[AsyncCDP] = None

       async def connect(self):
           # ... existing code до tab.start() ...

           # Wrap tab in async CDP
           self.cdp = AsyncCDP(self.tab, default_timeout=10.0)

           # ... rest of code ...

       async def ensure_connected(self):
           try:
               if self.tab:
                   try:
                       # ✅ Используй async CDP
                       await self.cdp.evaluate(expression="1+1", timeout=2.0)
                       return True
                   except (CDPTimeoutError, CDPProtocolError) as e:
                       logger.warning("Health check failed: %s", e)
                       # ... reconnect ...
           # ... rest of code ...
   ```

3. Обнови commands/context.py:
   ```python
   @dataclass
   class CommandContext:
       tab: pychrome.Tab
       cdp: 'AsyncCDP'  # ✅ Добавь CDP wrapper
       cursor: Optional['AICursor'] = None
       browser: Optional[pychrome.Browser] = None
       console_logs: Optional[List[Dict[str, Any]]] = None
   ```

4. Обнови commands/base.py:
   ```python
   @property
   def cdp(self):
       """Async CDP wrapper"""
       return self.context.cdp
   ```

5. Обнови protocol.py для передачи cdp:
   ```python
   context = CommandContext(
       tab=self.connection.tab,
       cdp=self.connection.cdp,  # ✅
       cursor=self.connection.cursor,
       browser=self.connection.browser,
       console_logs=self.connection.console_logs
   )
   ```

6. Обнови команды для использования self.cdp:

   **commands/interaction.py:**
   ```python
   class ClickCommand(Command):
       async def execute(self, selector: str, **kwargs):
           # ❌ Старый код:
           # result = self.tab.Runtime.evaluate(expression=js_code)

           # ✅ Новый код:
           result = await self.cdp.evaluate(
               expression=js_code,
               timeout=5.0
           )
   ```

   **commands/devtools.py:**
   ```python
   class ConsoleCommandCommand(Command):
       async def execute(self, command: str):
           # ✅
           result = await self.cdp.evaluate(
               expression=command,
               returnByValue=True,
               timeout=10.0
           )
   ```

   **commands/screenshot.py:**
   ```python
   class ScreenshotCommand(Command):
       async def execute(self, path: str = "./screenshots/screenshot.png"):
           # ✅
           result = await self.cdp.capture_screenshot(
               format='png',
               timeout=15.0
           )
   ```

   **Обнови ВСЕ команды с CDP вызовами:**
   - interaction.py (click, click_by_text, scroll, move_cursor)
   - navigation.py (open_url, get_text)
   - devtools.py (console_command, inspect_element, get_network_activity)
   - evaluation.py (evaluate_js)
   - screenshot.py
   - search.py (find_elements, get_page_structure)
   - save_page_info.py
   - helpers.py (debug_element, force_click)
   - diagnostics.py

7. Обнови browser/cursor.py:
   ```python
   class AICursor:
       def __init__(self, tab):
           self.tab = tab
           # Создай свой CDP wrapper
           from .async_cdp import AsyncCDP
           self.cdp = AsyncCDP(tab)

       async def initialize(self):
           # ✅
           result = await self.cdp.evaluate(
               expression=js_cursor_code,
               timeout=5.0
           )

       async def move(self, x: int, y: int, duration: int = 400):
           # ✅
           await self.cdp.evaluate(
               expression=f"window.__moveAICursor__({x}, {y}, {duration})",
               timeout=2.0
           )
   ```

8. Добавь конфигурацию timeout'ов:
   ```python
   # В server.py или новый файл config.py
   CDP_TIMEOUTS = {
       'default': 10.0,
       'evaluate': 5.0,
       'screenshot': 15.0,
       'navigation': 30.0,
       'health_check': 2.0
   }
   ```

9. Обнови CLAUDE.md:
   ```markdown
   ## AsyncCDP Wrapper

   Все CDP вызовы идут через AsyncCDP wrapper для:
   - Правильной интеграции с asyncio
   - Timeout'ов на все операции
   - Thread-safety через asyncio.Lock
   - Обработки CDP ошибок

   Usage в командах:
   ```python
   result = await self.cdp.evaluate(expression="...", timeout=5.0)
   ```

   Timeout'ы по умолчанию:
   - default: 10s
   - evaluate: 5s
   - screenshot: 15s
   - navigation: 30s
   ```

10. Протестируй с timeout'ами:
    ```bash
    # Тест обычных операций
    mcp__comet-browser__click_by_text(text="Test")

    # Тест с медленным JS
    mcp__comet-browser__evaluate_js(code="for(let i=0;i<1e9;i++);")
    # Должен timeout через 5s

    # Проверь логи
    MCP_LOG_LEVEL=DEBUG python3 server.py
    ```

11. Создай коммит:
    "refactor: Add AsyncCDP wrapper for proper async integration

    - Новый AsyncCDP wrapper в browser/async_cdp.py
    - Все CDP вызовы идут через executor с timeout'ами
    - Thread-safety через asyncio.Lock
    - Обработка timeout'ов через CDPTimeoutError
    - Все команды обновлены для async CDP

    Benefits:
    - Не блокирует event loop
    - Timeout'ы защищают от зависания
    - Правильная интеграция с asyncio

    Fixes: Task 2.3 from roadmap-v2.md"

ВАЖНО:
- Обнови ВСЕ команды с CDP вызовами
- Выбери разумные timeout'ы для разных операций
- Проверь что ошибки правильно логируются
- Протестируй с медленными операциями
```

---

### 🔍 Файлы для изменения

1. **browser/async_cdp.py** (новый файл)
2. **browser/connection.py** - создать self.cdp
3. **browser/cursor.py** - использовать AsyncCDP
4. **commands/context.py** - добавить cdp в контекст
5. **commands/base.py** - добавить свойство cdp
6. **mcp/protocol.py** - передать cdp в контекст
7. **commands/*.py** - все команды с CDP вызовами:
   - interaction.py
   - navigation.py
   - devtools.py
   - evaluation.py
   - screenshot.py
   - search.py
   - save_page_info.py
   - helpers.py
   - diagnostics.py
8. **.claude/CLAUDE.md** - документация AsyncCDP

---

### 🧪 Как проверить результат

```bash
# 1. Найти все синхронные CDP вызовы
grep -r "self\.tab\.Runtime\.evaluate" commands/
grep -r "self\.tab\.Page\." commands/
grep -r "self\.tab\.DOM\." commands/
# Не должно быть результатов (кроме async_cdp.py)

# 2. Проверить что всё работает
python3 server.py

# 3. Тест timeout'а
# Создай команду с бесконечным циклом
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"evaluate_js","arguments":{"code":"while(true);"}}}' | timeout 10 python3 server.py
# Должен вернуть CDPTimeoutError через ~5s

# 4. Проверить логи timeout'ов
MCP_LOG_LEVEL=DEBUG python3 server.py 2>&1 | grep -i timeout
```

---

### ⚠️ Возможные проблемы

**Проблема:** Deadlock из-за asyncio.Lock
**Решение:** Убедись что lock не держится слишком долго, используй timeout

**Проблема:** Timeout'ы слишком короткие для медленных операций
**Решение:** Настрой индивидуальные timeout'ы для разных типов операций

**Проблема:** Некоторые CDP методы не обёрнуты
**Решение:** Добавь wrapper методы в AsyncCDP по мере необходимости

**Проблема:** Performance деградация из-за executor
**Решение:** Это нормально, безопасность важнее. Можно добавить connection pooling если нужно.

---

---

## Task 2.4: Убрать редиректы команд

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md, раздел "🛠️ 29 Инструментов"):**

8 команд перенаправляют на `save_page_info()` из-за ограничений вывода Claude Code:

1. `evaluate_js` → save_page_info
2. `get_page_snapshot` → save_page_info
3. `find_elements` → save_page_info
4. `get_page_structure` → save_page_info
5. `get_clickable_elements` → save_page_info
6. `devtools_report` → save_page_info
7. `get_console_logs` → save_page_info (частично)

**Пример редиректа (из кода):**
```python
class EvaluateJsCommand(Command):
    async def execute(self, code: str):
        # ❌ Команда не делает то, что обещает!
        return {
            "redirected": True,
            "message": "Output saved to page_info.json. Use Read('./page_info.json') to view.",
            "action": "Called save_page_info() due to large output"
        }
```

**Проблемы:**
- ❌ Команда не делает то, что обещает (нарушение контракта)
- ❌ Пользователь должен знать про workaround
- ❌ Команды-обёртки без реальной логики
- ❌ Дублирование кода перенаправления

---

### 🎯 Цель задачи

Убрать редиректы и автоматически сохранять большие результаты на уровне protocol.py.

---

### ✅ Критерии приёмки

1. ✅ Все команды возвращают реальные результаты
2. ✅ `protocol.py` автоматически сохраняет большие результаты в файл
3. ✅ Убрано поле `{"redirected": true}` из ответов
4. ✅ Единая логика обработки больших результатов
5. ✅ Все 8 команд работают корректно

---

### 📋 Пошаговый промпт для выполнения

```
# ПРОМПТ ДЛЯ CLAUDE CODE:

Мне нужно выполнить Task 2.4 из roadmap-v2.md.

КОНТЕКСТ:
1. Прочитай /home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md
2. Найди все команды с {"redirected": true}
3. Изучи что делает save_page_info()

ЗАДАЧА:
Убрать редиректы команд и сделать автоматическое сохранение больших результатов.

ШАГИ:

1. Создай mcp/output_handler.py:
   ```python
   """Handler for large command outputs"""
   import json
   import logging
   from pathlib import Path
   from typing import Dict, Any
   from datetime import datetime

   logger = logging.getLogger('mcp_comet.output_handler')

   class OutputHandler:
       """Handles large command outputs by saving to file

       If command result is too large to return directly,
       saves it to a file and returns a reference.
       """

       def __init__(
           self,
           max_result_size: int = 50_000,  # characters
           output_dir: str = "./mcp_output"
       ):
           """Initialize output handler

           Args:
               max_result_size: Max size of result in characters
               output_dir: Directory for saved outputs
           """
           self.max_result_size = max_result_size
           self.output_dir = Path(output_dir)
           self.output_dir.mkdir(exist_ok=True)

       def should_save_to_file(self, result: Dict[str, Any]) -> bool:
           """Check if result should be saved to file"""
           try:
               result_json = json.dumps(result)
               size = len(result_json)

               if size > self.max_result_size:
                   logger.info(
                       "Result size %d exceeds limit %d, will save to file",
                       size, self.max_result_size
                   )
                   return True

               return False
           except Exception as e:
               logger.error("Failed to check result size: %s", e)
               return False

       def save_result(
           self,
           result: Dict[str, Any],
           command_name: str
       ) -> Dict[str, Any]:
           """Save result to file and return reference

           Args:
               result: Command result to save
               command_name: Name of command that produced result

           Returns:
               Dict with file reference
           """
           try:
               # Generate filename with timestamp
               timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
               filename = f"{command_name}_{timestamp}.json"
               filepath = self.output_dir / filename

               # Save result
               with open(filepath, 'w', encoding='utf-8') as f:
                   json.dump(result, f, indent=2, ensure_ascii=False)

               logger.info("Saved large result to %s", filepath)

               # Return reference
               return {
                   "success": True,
                   "saved_to_file": True,
                   "file_path": str(filepath),
                   "message": (
                       f"Result too large, saved to {filepath}. "
                       f"Use Read('{filepath}') to view the full output."
                   ),
                   "size_info": {
                       "result_size": len(json.dumps(result)),
                       "max_size": self.max_result_size
                   }
               }

           except Exception as e:
               logger.error("Failed to save result to file: %s", e)
               # Return error but include partial result
               return {
                   "success": False,
                   "message": f"Failed to save result: {str(e)}",
                   "partial_result": str(result)[:1000]  # First 1000 chars
               }
   ```

2. Обнови mcp/protocol.py:
   ```python
   from .output_handler import OutputHandler

   class MCPJSONRPCServer:
       def __init__(self):
           # ... existing code ...
           self.output_handler = OutputHandler(
               max_result_size=50_000,  # 50KB
               output_dir="./mcp_output"
           )

       async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
           """Call a tool by name with arguments"""
           # ... existing code до result = await cmd_instance.execute() ...

           result = await cmd_instance.execute(**arguments)

           # ✅ НОВЫЙ КОД: Автоматически сохранять большие результаты
           if self.output_handler.should_save_to_file(result):
               result = self.output_handler.save_result(result, tool_name)

           # ... rest of code (tab switching, etc.) ...

           return result
   ```

3. Восстанови реальную логику в командах-редиректах:

   **commands/evaluation.py (evaluate_js):**
   ```python
   class EvaluateJsCommand(Command):
       name = "evaluate_js"
       description = "Execute JavaScript code in the browser"
       input_schema = {
           "type": "object",
           "properties": {
               "code": {
                   "type": "string",
                   "description": "JavaScript code to execute"
               }
           },
           "required": ["code"]
       }

       async def execute(self, code: str):
           """Execute JavaScript and return result"""
           try:
               # ✅ РЕАЛЬНОЕ ВЫПОЛНЕНИЕ вместо редиректа
               result = await self.cdp.evaluate(
                   expression=code,
                   returnByValue=True,
                   timeout=10.0
               )

               # Extract value
               value = result.get('result', {})

               return {
                   "success": True,
                   "result": {
                       "type": value.get('type'),
                       "value": value.get('value'),
                       "description": value.get('description')
                   },
                   "code_executed": code
               }

           except Exception as e:
               logger.error("Failed to evaluate JS: %s", e)
               return {
                   "success": False,
                   "message": str(e),
                   "code": code
               }
   ```

   **commands/search.py (find_elements, get_page_structure):**
   ```python
   class FindElementsCommand(Command):
       async def execute(self, text: str = None, tag: str = None, **kwargs):
           """Find elements on page"""
           # ✅ РЕАЛЬНАЯ ЛОГИКА
           js_code = f"""
           (function() {{
               let elements = [];
               let all = document.querySelectorAll('*');

               for (let el of all) {{
                   let match = true;

                   if ({json.dumps(text)}) {{
                       let textContent = el.textContent.toLowerCase();
                       if (!textContent.includes({json.dumps(text.lower())})) {{
                           match = false;
                       }}
                   }}

                   if ({json.dumps(tag)}) {{
                       if (el.tagName.toLowerCase() !== {json.dumps(tag.lower())}) {{
                           match = false;
                       }}
                   }}

                   if (match) {{
                       elements.push({{
                           tag: el.tagName,
                           text: el.textContent.substring(0, 100),
                           id: el.id,
                           class: el.className,
                           visible: el.offsetParent !== null
                       }});
                   }}
               }}

               return elements;
           }})()
           """

           result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
           elements = result.get('result', {}).get('value', [])

           return {
               "success": True,
               "elements": elements,
               "count": len(elements)
           }

   class GetPageStructureCommand(Command):
       async def execute(self, include_text: bool = True):
           """Get page structure"""
           # ✅ РЕАЛЬНАЯ ЛОГИКА
           js_code = """
           (function() {
               return {
                   title: document.title,
                   url: window.location.href,
                   headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
                       tag: h.tagName,
                       text: h.textContent.trim()
                   })),
                   links: Array.from(document.querySelectorAll('a')).map(a => ({
                       text: a.textContent.trim(),
                       href: a.href
                   })),
                   buttons: Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
                       text: b.textContent.trim(),
                       type: b.type
                   })),
                   forms: Array.from(document.querySelectorAll('form')).map(f => ({
                       action: f.action,
                       method: f.method,
                       inputs: Array.from(f.querySelectorAll('input')).length
                   }))
               };
           })()
           """

           result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
           structure = result.get('result', {}).get('value', {})

           return {
               "success": True,
               "structure": structure
           }
   ```

   **commands/page_snapshot.py (get_page_snapshot):**
   ```python
   class PageSnapshotCommand(Command):
       async def execute(self, max_depth: int = 3, include_styles: bool = False):
           """Get page snapshot"""
           # ✅ РЕАЛЬНАЯ ЛОГИКА
           js_code = f"""
           (function() {{
               function getSnapshot(element, depth) {{
                   if (depth === 0) return null;

                   let node = {{
                       tag: element.tagName,
                       id: element.id,
                       class: element.className,
                       text: element.textContent.substring(0, 100)
                   }};

                   if ({json.dumps(include_styles)}) {{
                       let styles = window.getComputedStyle(element);
                       node.styles = {{
                           display: styles.display,
                           visibility: styles.visibility,
                           position: styles.position
                       }};
                   }}

                   node.children = Array.from(element.children)
                       .map(child => getSnapshot(child, depth - 1))
                       .filter(n => n !== null);

                   return node;
               }}

               return getSnapshot(document.body, {max_depth});
           }})()
           """

           result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
           snapshot = result.get('result', {}).get('value', {})

           return {
               "success": True,
               "snapshot": snapshot,
               "max_depth": max_depth
           }
   ```

   **commands/diagnostics.py (get_clickable_elements):**
   ```python
   class GetClickableElementsCommand(Command):
       async def execute(self, text_filter: str = None, visible_only: bool = True):
           """Get all clickable elements"""
           # ✅ РЕАЛЬНАЯ ЛОГИКА
           js_code = f"""
           (function() {{
               let clickable = ['A', 'BUTTON', 'INPUT'];
               let elements = [];

               document.querySelectorAll('*').forEach(el => {{
                   let isClickable = clickable.includes(el.tagName) ||
                                   el.hasAttribute('onclick') ||
                                   el.getAttribute('role') === 'button';

                   if (!isClickable) return;

                   if ({json.dumps(visible_only)}) {{
                       if (el.offsetParent === null) return;
                   }}

                   let text = el.textContent.trim();
                   if ({json.dumps(text_filter)}) {{
                       if (!text.toLowerCase().includes({json.dumps(text_filter.lower())})) {{
                           return;
                       }}
                   }}

                   let rect = el.getBoundingClientRect();
                   elements.push({{
                       tag: el.tagName,
                       text: text.substring(0, 50),
                       id: el.id,
                       class: el.className,
                       position: {{
                           x: rect.x + rect.width / 2,
                           y: rect.y + rect.height / 2
                       }}
                   }});
               }});

               return elements;
           }})()
           """

           result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
           elements = result.get('result', {}).get('value', [])

           return {
               "success": True,
               "elements": elements,
               "count": len(elements)
           }
   ```

   **commands/devtools_report.py:**
   ```python
   class DevToolsReportCommand(Command):
       requires_console_logs = True

       async def execute(self, include_dom: bool = False):
           """Generate DevTools report"""
           # ✅ Комбинируй данные из разных источников
           report = {
               "timestamp": datetime.now().isoformat(),
               "console_logs": self.console_logs[-50:],  # Last 50 logs
               "page_info": {}
           }

           # Get page info
           js_code = """
           ({
               url: window.location.href,
               title: document.title,
               readyState: document.readyState,
               elementCount: document.querySelectorAll('*').length
           })
           """
           result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
           report["page_info"] = result.get('result', {}).get('value', {})

           if include_dom:
               # Get DOM snapshot
               dom_result = await self.cdp.get_document()
               report["dom"] = dom_result

           return {
               "success": True,
               "report": report
           }
   ```

4. Обнови get_console_logs (частичный редирект):
   ```python
   class GetConsoleLogsCommand(Command):
       requires_console_logs = True

       async def execute(self, clear: bool = False):
           """Get console logs"""
           # ✅ Возвращай реальные логи
           logs = self.console_logs.copy()

           if clear:
               self.console_logs.clear()

           return {
               "success": True,
               "logs": logs,
               "count": len(logs),
               "cleared": clear
           }
   ```

5. Обнови CLAUDE.md:
   - Удали упоминания о редиректах
   - Обнови секцию "🛠️ 29 Инструментов":
   ```markdown
   ### **Выполнение кода и скриншоты (4)**
   17. `evaluate_js` - Выполняет JavaScript и возвращает результат ✅
   18. `screenshot` - Скриншот (PNG, сохраняется в ./screenshots/)
   19. `get_page_snapshot` - Получает snapshot DOM дерева ✅
   20. `save_page_info` - Сохраняет полную информацию о странице в JSON

   ### **Поиск и структура (2)**
   21. `find_elements` - Находит элементы по тексту/тегу/атрибутам ✅
   22. `get_page_structure` - Получает структуру страницы ✅

   ### **Диагностика (4)**
   26. `enable_console_logging` - Принудительно включить логирование
   27. `diagnose_page` - Диагностика состояния страницы
   28. `get_clickable_elements` - Получает все кликабельные элементы ✅
   29. `devtools_report` - Генерирует полный DevTools отчёт ✅

   > **ℹ️ Примечание:** Если результат команды слишком большой (>50KB),
   > он автоматически сохраняется в `./mcp_output/` и возвращается ссылка.
   > Используй `Read()` для просмотра полного результата.
   ```

   - Добавь новую секцию:
   ```markdown
   ## 📁 Обработка больших результатов

   Protocol автоматически сохраняет большие результаты (>50KB) в файлы:

   - Директория: `./mcp_output/`
   - Формат: `{command_name}_{timestamp}.json`
   - Команда возвращает: `{"saved_to_file": true, "file_path": "..."}`

   Пример:
   ```python
   result = evaluate_js(code="massive_json_data")
   # Возвращает: {"saved_to_file": true, "file_path": "./mcp_output/evaluate_js_20251007_123456.json"}

   # Читай через:
   Read('./mcp_output/evaluate_js_20251007_123456.json')
   ```
   ```

6. Создай .gitignore для output директории:
   ```
   # В .gitignore
   mcp_output/
   ```

7. Протестируй все восстановленные команды:
   ```bash
   # Evaluate JS
   mcp__comet-browser__evaluate_js(code="1 + 1")
   # Должен вернуть {"success": true, "result": {"value": 2}}

   # Find elements
   mcp__comet-browser__find_elements(tag="button")
   # Должен вернуть список кнопок

   # Get page structure
   mcp__comet-browser__get_page_structure()
   # Должен вернуть структуру

   # Test large result
   mcp__comet-browser__evaluate_js(code="Array(10000).fill('test')")
   # Должен сохранить в файл если >50KB
   ```

8. Создай коммит:
   "refactor: Remove command redirects, add automatic output handling

   - Новый OutputHandler для автоматического сохранения больших результатов
   - Восстановлена реальная логика в 8 командах:
     - evaluate_js: выполняет JS и возвращает результат
     - find_elements: находит элементы по критериям
     - get_page_structure: возвращает структуру страницы
     - get_page_snapshot: возвращает DOM snapshot
     - get_clickable_elements: находит кликабельные элементы
     - devtools_report: генерирует полный отчёт
     - get_console_logs: возвращает логи
   - Protocol автоматически сохраняет результаты >50KB
   - Убрано поле 'redirected' из ответов

   Breaking: Команды теперь возвращают реальные данные вместо редиректов

   Fixes: Task 2.4 from roadmap-v2.md"

ВАЖНО:
- Протестируй ВСЕ 8 восстановленных команд
- Проверь работу с большими результатами
- Убедись что логика корректна и возвращает нужные данные
- Обнови документацию
```

---

### 🔍 Файлы для изменения

1. **mcp/output_handler.py** (новый файл)
2. **mcp/protocol.py** - интеграция OutputHandler
3. **commands/evaluation.py** - восстановить evaluate_js
4. **commands/search.py** - восстановить find_elements, get_page_structure
5. **commands/page_snapshot.py** - восстановить get_page_snapshot
6. **commands/diagnostics.py** - восстановить get_clickable_elements
7. **commands/devtools_report.py** - восстановить devtools_report
8. **commands/devtools.py** - обновить get_console_logs
9. **.claude/CLAUDE.md** - убрать упоминания редиректов
10. **.gitignore** - добавить mcp_output/

---

### 🧪 Как проверить результат

```bash
# 1. Проверить что редиректы убраны
grep -r "redirected.*true" commands/
# Не должно быть результатов

# 2. Тест обычных результатов
mcp__comet-browser__evaluate_js(code="2 + 2")
# Должен вернуть {"success": true, "result": {"value": 4}}

# 3. Тест больших результатов
mcp__comet-browser__evaluate_js(code="JSON.stringify(Array(10000).fill({test: 'data'}))")
# Должен сохранить в ./mcp_output/ если >50KB

# 4. Проверить что файлы создаются
ls -lah mcp_output/
```

---

### ⚠️ Возможные проблемы

**Проблема:** Логика команды сложная и неясно как восстановить
**Решение:** Посмотри что делает save_page_info() и адаптируй для команды

**Проблема:** Результаты всё равно слишком большие даже после сохранения в файл
**Решение:** Добавь пагинацию или фильтрацию в команду

**Проблема:** Не все данные доступны через CDP
**Решение:** Используй JavaScript для получения данных из браузера

---

---

# 🎨 Sprint 3: Advanced Features (опционально)

## Task 3.1: Connection lifecycle manager

### 📝 Контекст

Текущая логика переподключения разбросана по `BrowserConnection.ensure_connected()` и реактивная (переподключаемся только когда что-то сломалось).

### 🎯 Цель

Создать проактивный lifecycle manager с health checks и graceful reconnection.

### 📋 Промпт (краткий)

```
Создай browser/lifecycle.py:
- ConnectionState enum (DISCONNECTED, CONNECTING, READY, UNHEALTHY)
- ConnectionLifecycle класс с:
  - Периодическими health checks (каждые 30s)
  - Автоматическим reconnect при деградации
  - Graceful shutdown
  - Metrics (uptime, reconnect count)

Интегрируй в BrowserConnection:
- connection.lifecycle.ensure_ready() вместо ensure_connected()
- Автоматический запуск background health check task

Benefits:
- Проактивное обнаружение проблем
- Лучший observability
- Более надёжное соединение
```

---

## Task 3.2: Plugin system для команд

### 📝 Контекст

Команды хардкодно живут в `commands/`. Нельзя загрузить команды извне.

### 🎯 Цель

Добавить возможность загружать команды из внешних пакетов/директорий.

### 📋 Промпт (краткий)

```
Расширь CommandRegistry:
- discover_from_directory(path) для загрузки из custom директорий
- discover_from_package(package_name) для внешних пакетов
- Валидация команд при загрузке

Создай механизм плагинов:
- plugins/ директория
- Каждый плагин = Python пакет с командами
- pyproject.toml entry points для автообнаружения

Пример плагина:
```python
# plugins/my_plugin/commands.py
@CommandRegistry.register()
class CustomCommand(Command):
    name = "custom_action"
    ...
```

Benefits:
- Расширяемость без изменения кода
- Возможность third-party расширений
- Изоляция кастомной логики
```

---

## Task 3.3: Metrics и observability

### 📝 Контекст

Нет метрик производительности, только логи.

### 🎯 Цель

Добавить метрики для мониторинга и анализа производительности.

### 📋 Промпт (краткий)

```
Создай mcp/metrics.py:
- MetricsCollector класс
- Метрики:
  - command_duration (histogram)
  - command_errors (counter)
  - cdp_calls (counter)
  - connection_status (gauge)
  - active_tabs (gauge)

Интеграция:
- В protocol.py оборачивай call_tool() для сбора метрик
- В AsyncCDP считай CDP вызовы и latency
- В ConnectionLifecycle трекай connection uptime

Экспорт метрик:
- JSON endpoint: GET /metrics
- Prometheus format (опционально)
- Periodic dump в файл

Benefits:
- Visibility в производительность
- Обнаружение bottleneck'ов
- Capacity planning
```

---

---

# 📊 Итоговая таблица задач

| Sprint | Task | Приоритет | Сложность | Время | Breaking |
|--------|------|-----------|-----------|-------|----------|
| 1.1 | Command metadata as class attrs | 🔴 High | Low | 2h | No |
| 1.2 | Structured logging | 🔴 High | Low | 3h | No |
| 1.3 | Error hierarchy | 🔴 High | Medium | 4h | No |
| 2.1 | CommandContext DI | 🔴 Critical | High | 6h | **Yes** |
| 2.2 | Auto-discovery | 🔴 High | Medium | 4h | No |
| 2.3 | Async CDP wrapper | 🟡 Medium | Medium | 5h | Partial |
| 2.4 | Убрать редиректы | 🟡 Medium | High | 6h | Partial |
| 3.1 | Connection lifecycle | 🟢 Low | Medium | 4h | No |
| 3.2 | Plugin system | 🟢 Low | High | 6h | No |
| 3.3 | Metrics | 🟢 Low | Medium | 4h | No |

**Всего времени:**
- Sprint 1 (Quick Wins): 9h
- Sprint 2 (Core): 21h
- Sprint 3 (Advanced): 14h

**Total: ~44h работы**

---

# 🎓 Как использовать этот roadmap

## Для выполнения задачи:

1. **Прочитай контекст:**
   ```
   Read('/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md')
   ```

2. **Прочитай Task из roadmap:**
   ```
   Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md')
   # Найди нужный Task (например Task 1.1)
   ```

3. **Скопируй промпт из секции "📋 Пошаговый промпт"**

4. **Выполни все шаги по порядку**

5. **Проверь результат через секцию "🧪 Как проверить"**

6. **Создай коммит с предложенным сообщением**

---

## Порядок выполнения:

### **Рекомендуемый (безопасный):**
1. Sprint 1 целиком (Tasks 1.1 → 1.2 → 1.3)
2. Sprint 2 целиком (Tasks 2.1 → 2.2 → 2.3 → 2.4)
3. Sprint 3 по желанию

### **Быстрый (только критичное):**
1. Task 2.1 (CommandContext) - убирает главный костыль
2. Task 1.2 (Logging) - помогает в debugging
3. Task 2.2 (Registry) - убирает ручную регистрацию

### **Minimal (минимум изменений):**
1. Task 1.2 (Logging) - не ломает ничего
2. Task 1.3 (Errors) - улучшает debugging

---

# 🚨 Важные напоминания

1. **ВСЕГДА** читай CLAUDE.md перед началом работы
2. **НЕ пропускай шаги** из промптов - они в правильном порядке
3. **Проверяй результат** через секцию "🧪 Как проверить"
4. **Коммить после каждого Task'а** - не накапливай изменения
5. **Обновляй CLAUDE.md** после значительных изменений
6. **Тестируй ВСЕ команды** после breaking changes

---

# 📚 Дополнительные ресурсы

- **Проект:** `/home/admsrv/mcp_comet_for_claude_code/`
- **Контекст:** `.claude/CLAUDE.md`
- **Roadmap:** `docs/roadmap-v2.md` (этот файл)
- **MCP Spec:** https://spec.modelcontextprotocol.io/
- **CDP Docs:** https://chromedevtools.github.io/devtools-protocol/

---

**🤖 Этот roadmap создан для пошагового рефакторинга MCP Comet Browser**

**Версия:** 2.0
**Дата:** 2025-10-07
**Автор:** Claude Code
