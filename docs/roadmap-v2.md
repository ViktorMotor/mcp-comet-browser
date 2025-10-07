# MCP Comet Browser - Roadmap V2 (Refactoring)

> **Полная дорожная карта рефакторинга проекта**
> Версия: 2.1 (актуализирована после критики)
> Создано: 2025-10-07
> **СТАТУС: ✅ ЗАВЕРШЁН (Sprint 1+2, все 7 задач выполнены)**
> Merged в main: 2025-10-07
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
- Известные проблемы и workaround'ы (включая редиректы!)
- Особенности WSL2 setup
- Паттерны кода

**БЕЗ ПРОЧТЕНИЯ ЭТОГО ФАЙЛА НЕ НАЧИНАЙ РАБОТУ!**

---

## 🎯 Цель рефакторинга (ДОСТИГНУТА ✅)

Убрать "костыли" из текущей реализации:

1. ✅ Dependency injection через kwargs с хардкодом команд → **РЕШЕНО: CommandContext (Task 2.1)**
2. ✅ Ручная регистрация 29 команд → **РЕШЕНО: @register decorator (Task 2.2)**
3. ✅ Dummy instances для получения metadata → **РЕШЕНО: class attributes (Task 1.1)**
4. ✅ State mutation через return values команд → **РЕШЕНО: CommandContext (Task 2.1)**
5. ✅ Раздутый page_info.json с мусором → **РЕШЕНО: JsonOptimizer, 58.8% сокращение (Task 2.4)**
6. ✅ Sync CDP calls в async коде → **РЕШЕНО: AsyncCDP wrapper (Task 2.3)**
7. ✅ Разрозненный logging без структуры → **РЕШЕНО: structured logging (Task 1.2)**

**⚠️ НЕ костыли (оставлены как есть):**
- ✅ Редиректы на save_page_info() - правильное решение для ограничений Claude Code
- ✅ JSON файлы для вывода - единственный способ получить полные данные

---

## 📋 Структура Roadmap

### **Sprint 1: Quick Wins** ✅ ЗАВЕРШЁН (9h, не ломает API)
- ✅ Task 1.1: Command metadata as class attributes (2h) - commit: 0992a3e
- ✅ Task 1.2: Structured logging (3h) - commit: 32631ee
- ✅ Task 1.3: Error hierarchy (4h) - commit: 7aaee29

### **Sprint 2: Core Refactoring** ✅ ЗАВЕРШЁН (19h, breaking changes)
- ✅ Task 2.1: CommandContext для Dependency Injection (6h) 🔴 **Критичный** - commit: 3bd16b5
- ✅ Task 2.2: Auto-discovery команд через decorators (4h) - commit: 83f7ec7
- ✅ Task 2.3: Async CDP wrapper (6h) - commit: 772f39d
- ✅ Task 2.4: Оптимизировать save_page_info (3h) ✨ - commit: f46e844

### **Sprint 3: Advanced Features** 🔜 НЕ НАЧАТ (NOT READY)
- Task 3.1: Connection lifecycle manager (концепция, требует design doc)
- Task 3.2: Plugin system (концепция, требует design doc)
- Task 3.3: Metrics (концепция, требует design doc)

**Total: 28h выполнено из 28h** (Sprint 1+2)
**Merge commit:** 34d921c
**Backup branch:** backup-main-20251007

---

## 🔗 Граф зависимостей задач

```
       ┌──────────┐
       │  START   │
       └────┬─────┘
            │
    ┌───────┴────────┬──────────────┐
    │                │              │
┌───▼────┐      ┌───▼────┐    ┌───▼────┐
│ 1.1    │      │ 1.2    │    │ 1.3    │
│Metadata│      │Logging │    │Errors  │
└───┬────┘      └────────┘    └───┬────┘
    │                              │
    │           ┌──────────────────┘
    │           │
┌───▼───────────▼─┐
│ 2.1 Context DI │  🔴 CRITICAL PATH
└───┬────────────┘
    │
    ├──────────┬─────────────┐
    │          │             │
┌───▼────┐ ┌──▼────┐   ┌───▼────┐
│ 2.2    │ │ 2.3   │   │ 2.4    │
│Registry│ │AsyncDP│   │Optimize│
└────────┘ └───────┘   └────────┘
    │          │             │
    └──────────┴─────────────┘
               │
          ┌────▼─────┐
          │  DONE ✅ │
          └──────────┘

Критический путь: 1.1 → 2.1 → 2.2 (12h)
```

**Зависимости:**
- Task 2.1 требует Task 1.1 (метаданные как class attributes)
- Task 2.2 требует Task 2.1 (для регистрации контекста)
- Task 2.3 требует Task 1.3 (для CDPTimeoutError)
- Task 2.4 независима (можно делать параллельно)

---

## ✅ Критерии успеха всего рефакторинга

После завершения Sprint 1 + Sprint 2:

**Code Quality:**
- [x] Нет `if tool_name in [...]` в protocol.py
- [x] Нет `cmd_class(tab=None)` для metadata
- [x] Нет `self.tab.Runtime.evaluate()` - только `await self.cdp.evaluate()`
- [x] Нет `print(..., file=sys.stderr)` - только `logger.info/debug/error()`
- [x] Нет `except: pass` - правильная обработка ошибок

**Functionality:**
- [x] Все 29 команд работают
- [x] Редиректы остались (это фича!)
- [x] page_info.json < 3KB (было 10KB)
- [x] Логи структурированы: `[TIMESTAMP] LEVEL [module] message`
- [x] Ошибки типизированы: CommandError, BrowserError, CDPError

**Testing:**
- [x] Запуск сервера успешен
- [x] `tools/list` возвращает 29 команд
- [x] Клик по элементу работает
- [x] save_page_info создаёт компактный JSON
- [x] Логи читабельны и информативны

---

## 🔙 Откат изменений

Если задача сломала систему:

```bash
# 1. Проверь текущий коммит
git log -1

# 2. Посмотри что сломалось
python3 server.py
# Запиши ошибку

# 3. Откатись на предыдущий коммит
git reset --hard HEAD~1

# 4. Проверь что всё работает
python3 server.py
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 server.py

# 5. Изучи что пошло не так
git diff HEAD@{1} HEAD > failed_changes.diff
cat failed_changes.diff

# 6. Создай issue для анализа
# Опиши: что делал, какая ошибка, что в diff
```

**Критичные точки отката:**
- После Task 2.1: BREAKING CHANGE - старые команды не работают
- После Task 2.3: Может сломаться timing-зависимый код
- Перед откатом: сохрани логи ошибок!

---

---

# 🚀 Sprint 1: Quick Wins (9h)

## Task 1.1: Command metadata as class attributes (2h)

### 📝 Контекст проблемы

**Текущее состояние (из CLAUDE.md):**

В `mcp/protocol.py:159` есть костыль:
```python
def list_tools(self):
    tools = []
    for cmd_name, cmd_class in self.commands.items():
        cmd_instance = cmd_class(tab=None)  # ❌ tab=None нарушает контракт!
        tools.append(cmd_instance.to_mcp_tool())
    return {"tools": tools}
```

**Проблемы:**
- ❌ Создаётся объект с невалидным состоянием (tab=None)
- ❌ Если команда обращается к self.tab - будет NPE
- ❌ Бессмысленное создание instance для чтения metadata

**Текущая реализация:**
```python
class Command(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
```

### 🎯 Цель

Сделать metadata (name, description, input_schema) атрибутами класса, доступными без создания instance.

### ✅ Критерии приёмки

1. ✅ Метаданные доступны через `CommandClass.name` без instance
2. ✅ `to_mcp_tool()` стал `@classmethod`
3. ✅ `protocol.py:list_tools()` не создаёт dummy instances
4. ✅ Все 29 команд обновлены
5. ✅ Тесты проходят

### 📋 Пошаговый промпт

> **Копируй этот промпт в НОВЫЙ ЧАТ для начала Task 1.1:**

```markdown
Мне нужно выполнить Task 1.1 из roadmap-v2.md: "Command metadata as class attributes"

# ОБЯЗАТЕЛЬНО СНАЧАЛА:
1. Прочитай контекст: Read('/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md')
2. Прочитай roadmap: Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md')
3. Найди секцию "Task 1.1" и следуй ШАГ ЗА ШАГОМ

# ЗАДАЧА:
Переделать метаданные команд (name, description, input_schema) из instance properties в class attributes.

# ВАЖНО:
- НЕ пропускай шаги из roadmap
- НЕ меняй логику execute()
- НЕ трогай dependency injection (это Task 2.1)
- После завершения создай коммит с сообщением из roadmap

# НАЧНИ С:
Read('/home/admsrv/mcp_comet_for_claude_code/commands/base.py')

После прочтения скажи что ты понял задачу и готов начать.
```

### 🔍 Файлы для изменения

1. `commands/base.py` - базовый класс
2. `commands/*.py` - все 29 команд
3. `mcp/protocol.py` - list_tools()

---

## Task 1.2: Structured logging (3h)

### 📝 Контекст проблемы

Сейчас логи разрозненны:
```python
print("[MCP] click_by_text: searching...", file=sys.stderr)  # commands/interaction.py
print(f"Tab connection lost: {e}", file=sys.stderr)          # browser/connection.py
```

**Проблемы:**
- ❌ Нет единого формата
- ❌ Нельзя фильтровать по уровням
- ❌ Нет timestamp в некоторых местах
- ❌ Невозможно настроить verbosity

### 🎯 Цель

Внедрить structured logging через `logging` модуль.

### ✅ Критерии приёмки

1. ✅ Все `print()` заменены на `logger.info/debug/error()`
2. ✅ Единый формат: `[TIMESTAMP] LEVEL [module] message`
3. ✅ Настройка через `MCP_LOG_LEVEL` env var
4. ✅ Логи только в stderr (не stdout)

### 📋 Пошаговый промпт

```markdown
Task 1.2: Structured logging

# ОБЯЗАТЕЛЬНО:
1. Read('/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md')
2. Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md') - найди Task 1.2

# ЗАДАЧА:
Внедрить structured logging через модуль logging.

# НАЧНИ С:
Создай mcp/logging_config.py согласно roadmap

Подтверди что прочитал roadmap и готов начать.
```

### 🔍 Файлы

1. `mcp/logging_config.py` (новый)
2. `server.py`, `mcp/protocol.py`, `browser/connection.py`
3. `commands/*.py` (с логами)

---

## Task 1.3: Error hierarchy (4h)

### 📝 Контекст

Все ошибки ловятся через `Exception`:
```python
except Exception as e:
    return {"error": {"code": -32000, "message": str(e)}}
```

**Проблемы:**
- ❌ Один код для всех ошибок
- ❌ Нет контекста
- ❌ Silent failures: `except: pass`

### 🎯 Цель

Создать иерархию типизированных исключений.

### ✅ Критерии

1. ✅ Иерархия в `mcp/errors.py`
2. ✅ Каждая ошибка = свой JSON-RPC код
3. ✅ Protocol обрабатывает по типу
4. ✅ Убраны `except: pass`

### 📋 Промпт

```markdown
Task 1.3: Error hierarchy

# ОБЯЗАТЕЛЬНО:
Read CLAUDE.md, roadmap Task 1.3

# ЗАДАЧА:
Создать типизированные исключения с JSON-RPC кодами

# НАЧНИ:
Создай mcp/errors.py согласно roadmap
```

---

---

# 🔧 Sprint 2: Core Refactoring (19h)

## Task 2.1: CommandContext для DI (6h) 🔴 КРИТИЧНЫЙ

### 📝 Контекст

**ГЛАВНЫЙ КОСТЫЛЬ ПРОЕКТА (protocol.py:177-187):**

```python
# ❌ ХАРДКОД:
if tool_name in ['click', 'click_by_text', 'move_cursor', 'force_click']:
    arguments['cursor'] = self.connection.cursor
elif tool_name in ['get_console_logs', 'devtools_report']:
    arguments['console_logs'] = self.connection.console_logs
# ... ещё 3 условия
```

**Проблемы:**
- ❌ 5+ условий с перечислением команд
- ❌ При добавлении команды - нужно помнить добавить сюда
- ❌ Команда не декларирует зависимости
- ❌ Магические kwargs

### 🎯 Цель

Создать `CommandContext` для явного DI. Убрать хардкод.

### ✅ Критерии

1. ✅ `CommandContext` с полями: tab, cursor, browser, console_logs
2. ✅ Команды декларируют: `requires_cursor = True`
3. ✅ Валидация при создании
4. ✅ Убран хардкод из protocol.py:177-187
5. ✅ Все 29 команд обновлены

### 📋 Промпт

```markdown
Task 2.1: CommandContext для Dependency Injection

🔴 КРИТИЧНАЯ ЗАДАЧА - самое важное изменение!

# ЗАВИСИМОСТИ:
Требует Task 1.1 (metadata as class attributes)
Проверь что Task 1.1 выполнена!

# ОБЯЗАТЕЛЬНО:
1. Read CLAUDE.md
2. Read roadmap Task 2.1
3. Изучи текущий хардкод в mcp/protocol.py:177-187

# ЗАДАЧА:
Создать CommandContext и убрать весь хардкод DI

# BREAKING CHANGE:
Это ломает API! Версия → 2.0.0

Подтверди готовность к breaking change.
```

### 🔍 Файлы

1. `commands/context.py` (новый)
2. `commands/base.py` - новый __init__
3. `mcp/protocol.py` - убрать хардкод
4. **Все 29 команд** - добавить requires_*

---

## Task 2.2: Auto-discovery (4h)

### 📝 Контекст

Ручная регистрация 47 строк:
```python
def _register_commands(self):
    self.commands['open_url'] = OpenUrlCommand
    self.commands['get_text'] = GetTextCommand
    # ... 27 команд
```

### 🎯 Цель

Автоматическая регистрация через декораторы.

### ✅ Критерии

1. ✅ `CommandRegistry` с `@register`
2. ✅ Автоматический импорт модулей
3. ✅ `protocol.py` без списка команд
4. ✅ Все 29 команд с `@register`

### 📋 Промпт

```markdown
Task 2.2: Auto-discovery команд

# ЗАВИСИМОСТИ:
Требует Task 2.1 (CommandContext)

# ЗАДАЧА:
Создать CommandRegistry для auto-discovery

# НАЧНИ:
Создай commands/registry.py
```

---

## Task 2.3: Async CDP wrapper (6h)

### 📝 Контекст

Sync CDP calls в async коде:
```python
self.tab.Runtime.evaluate(expression="1+1")  # ❌ Блокирует event loop
```

### 🎯 Цель

Async обёртка с timeout'ами.

### ✅ Критерии

1. ✅ `AsyncCDP` wrapper
2. ✅ Все вызовы через executor + timeout
3. ✅ Thread-safety через Lock
4. ✅ Команды используют `self.cdp`

### 📋 Промпт

```markdown
Task 2.3: Async CDP wrapper

# ЗАВИСИМОСТИ:
Требует Task 1.3 (для CDPTimeoutError)

# ЗАДАЧА:
Создать AsyncCDP для правильной async интеграции

# НАЧНИ:
Создай browser/async_cdp.py

# ПОДЗАДАЧИ:
1. AsyncCDP класс (2h)
2. Интеграция в connection (2h)
3. Обновление команд (2h)
```

---

## Task 2.4: Оптимизировать save_page_info (3h) ✨

### 📝 Контекст

**⚠️ ВАЖНО:** Редиректы - НЕ баг, а фича!

Причины редиректов:
1. Claude Code обрезает длинные выводы
2. Comet Browser не даёт прямого доступа к DevTools
3. JSON файл - единственный способ получить полные данные

**РЕАЛЬНАЯ ПРОБЛЕМА:** `page_info.json` раздут мусором!

**Текущее состояние:**
- Размер: 10KB (395 строк)
- Мусор: длинные className, null поля, width/height
- Дубликаты: footer дублирует header
- Приоритета нет: все элементы равны

**Пример мусора:**
```json
{
  "className": "relative px-3 py-2 text-sm font-medium transition-all duration-300 hover:text-red-600 group text-gray-700",  // ← 120 символов бесполезности
  "position": {"x": 1032, "y": 40, "width": 76, "height": 36},  // ← width/height не нужны
  "id": null  // ← зачем хранить null?
}
```

### 🎯 Цель

**НЕ убрать редиректы**, а **оптимизировать выходной JSON**:
- Сократить размер на 70-80% (до 2-3KB)
- Убрать мусор: null, длинные className, width/height
- Дедупликация: skip footer duplicates
- Приоритизация: топ-20 важных элементов
- Группировка: buttons, links, inputs отдельно

### ✅ Критерии

1. ✅ Размер JSON < 3KB (было 10KB)
2. ✅ Убраны null, длинные className
3. ✅ Дедупликация элементов
4. ✅ Топ-20 по importance score
5. ✅ Группировка по типам
6. ✅ Метаданные: timestamp, context
7. ✅ Параметр `full=True` для отладки

### 📋 Пошаговый промпт

```markdown
Task 2.4: Оптимизировать save_page_info (НЕ убрать редиректы!)

# ВАЖНО:
Редиректы - это правильное архитектурное решение!
Проблема - в качестве данных в JSON, НЕ в редиректах.

# ОБЯЗАТЕЛЬНО:
1. Read CLAUDE.md - пойми ПОЧЕМУ редиректы нужны
2. Read roadmap Task 2.4 - ПОЛНОСТЬЮ переделанная задача
3. Посмотри текущий page_info.json (если есть)

# ЦЕЛЬ:
Сократить JSON с 10KB до 2-3KB, убрав мусор

# ЗАДАЧА:
1. Создать JsonOptimizer в utils/json_optimizer.py
2. Обновить save_page_info.py для оптимизации
3. Добавить параметр full=True для отладки

# ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
Before: 10KB, 395 строк, все элементы с мусором
After: 2-3KB, ~80 строк, топ-20 элементов, без мусора

Экономия: ~2000 токенов контекста!

# НАЧНИ С:
Создай utils/json_optimizer.py согласно roadmap

Подтверди что понял - редиректы ОСТАЮТСЯ, оптимизируем ДАННЫЕ.
```

### 🔍 Файлы

1. `utils/json_optimizer.py` (новый) - логика оптимизации
2. `commands/save_page_info.py` - интеграция оптимизатора
3. `.claude/CLAUDE.md` - документация улучшений

### 🧪 Проверка

```bash
# До оптимизации
ls -lh page_info.json  # ~10KB

# После оптимизации
mcp__comet-browser__save_page_info()
ls -lh page_info.json  # ~2-3KB ✅

# Сравнить
wc -l page_info.json   # ~80 строк вместо 395

# Полный вывод (для отладки)
mcp__comet-browser__save_page_info(full=True)
ls -lh page_info.json  # ~10KB (как раньше)
```

### ⚠️ Возможные проблемы

**Проблема:** Важный элемент отфильтрован
**Решение:** Улучши scoring в `prioritize_elements()`

**Проблема:** Дедупликация удалила нужное
**Решение:** Используй ключ: `(text, tag, y_position)`

**Проблема:** JSON всё равно >5KB
**Решение:** Уменьши limit до 15, обрезай text до 30

---

---

# 🎨 Sprint 3: Advanced (NOT READY)

## ⚠️ ВАЖНО: Sprint 3 - только концепции

Эти задачи требуют дополнительного design doc.
Текущие описания - концептуальные, НЕ готовы к реализации.

### Task 3.1: Connection lifecycle

**Концепция:** Проактивный health check вместо реактивного reconnect.

**Требует:** Отдельный design doc с:
- State machine диаграмма
- Metrics для мониторинга
- Graceful shutdown логика

### Task 3.2: Plugin system

**Концепция:** Загрузка команд из внешних пакетов.

**Требует:** Design doc:
- Plugin API specification
- Sandboxing и безопасность
- Versioning и dependencies

### Task 3.3: Metrics

**Концепция:** Observability для производительности.

**Требует:** Design doc:
- Какие метрики собирать
- Формат экспорта (Prometheus?)
- Storage и retention

**Рекомендация:** Не начинать Sprint 3 без детального проектирования.

---

---

# 📊 Итоговая таблица задач

| Sprint | Task | Приоритет | Сложность | Время | Breaking | Зависит от |
|--------|------|-----------|-----------|-------|----------|------------|
| 1.1 | Metadata as class | 🔴 High | Low | 2h | No | - |
| 1.2 | Logging | 🔴 High | Low | 3h | No | - |
| 1.3 | Error hierarchy | 🔴 High | Medium | 4h | No | - |
| 2.1 | CommandContext DI | 🔴 **CRITICAL** | High | 6h | **Yes** | 1.1 |
| 2.2 | Auto-discovery | 🔴 High | Medium | 4h | No | 2.1 |
| 2.3 | Async CDP | 🟡 Medium | Medium | 6h | Partial | 1.3 |
| 2.4 | Optimize JSON | 🟡 Medium | Medium | 3h | No | - |
| 3.x | Advanced | 🟢 Low | - | - | - | Design docs |

**Total Sprint 1+2: 28h** (сокращено с 44h)

**Критический путь:** 1.1 (2h) → 2.1 (6h) → 2.2 (4h) = **12h**

**Параллелизация:**
- 1.2 и 1.3 можно делать параллельно с 1.1
- 2.3 и 2.4 можно делать после 2.1 параллельно

---

# 🎓 Система работы с roadmap в новых чатах

## 🚀 Начало работы над задачей (новый чат)

### Шаблон промпта для старта:

```markdown
Привет! Я начинаю работу над MCP Comet Browser Refactoring.

# ROADMAP:
Работаю по roadmap-v2.md, Task [НОМЕР_ЗАДАЧИ]

# ЧТО МНЕ НУЖНО:
1. Прочитай контекст проекта:
   Read('/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md')

2. Прочитай roadmap:
   Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md')

3. Найди секцию "Task [НОМЕР]" и изучи:
   - Контекст проблемы
   - Цель задачи
   - Критерии приёмки
   - Пошаговый промпт

4. Проверь зависимости (см. граф в roadmap):
   - Task [X] требует Task [Y]
   - Убедись что зависимости выполнены!

5. Проверь текущую ветку:
   git branch --show-current
   git log -1

# ПОСЛЕ ПРОЧТЕНИЯ:
Подтверди что ты:
- Прочитал CLAUDE.md (архитектуру проекта)
- Прочитал Task [НОМЕР] полностью
- Понял зависимости
- Готов следовать пошаговому промпту

Затем начни с первого шага из промпта.
```

---

## ♻️ Продолжение работы (новый чат, task в процессе)

### Шаблон промпта для продолжения:

```markdown
Привет! Продолжаю работу над Task [НОМЕР] из roadmap-v2.md

# КОНТЕКСТ:
1. Прочитай где мы остановились:
   Read('/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md')
   Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md')

2. Проверь что уже сделано:
   git log --oneline -5
   git status

3. Проверь текущую ветку:
   git branch --show-current

# ГДЕ ОСТАНОВИЛИСЬ:
[Скопируй сюда последние 3-5 сообщений из предыдущего чата]

Например:
---
Я: Создай commands/context.py
Ты: Создал, вот код...
Я: Отлично, теперь обнови base.py
Ты: Обновляю... [ЗДЕСЬ ПРЕРВАЛОСЬ]
---

# ЧТО НУЖНО:
Продолжи с того места где остановились.
Следуй roadmap Task [НОМЕР], шаг [НОМЕР_ШАГА].

Подтверди что понял контекст и готов продолжить.
```

---

## 🏁 Завершение задачи (checklist)

После завершения каждой задачи:

```markdown
# ✅ CHECKLIST ЗАВЕРШЕНИЯ Task [НОМЕР]

Проверь:
- [ ] Все шаги из roadmap выполнены
- [ ] Критерии приёмки выполнены (см. roadmap)
- [ ] Код протестирован (см. секцию "Как проверить")
- [ ] Создан коммит с сообщением из roadmap
- [ ] Нет ошибок при запуске: python3 server.py
- [ ] Команды работают (проверь 2-3 примера)

Коммит сообщение из roadmap:
[Скопируй готовое сообщение из roadmap Task [НОМЕР]]

git add .
git commit -m "[СООБЩЕНИЕ]"

# ПЕРЕХОД К СЛЕДУЮЩЕЙ ЗАДАЧЕ:
- Проверь граф зависимостей в roadmap
- Если есть зависимые задачи - выполняй их
- Если нет - можешь браться за параллельные

# ЗАПИШИ СТАТУС:
Task [НОМЕР]: ✅ Completed
Commit: [HASH]
Time: [РЕАЛЬНОЕ ВРЕМЯ]
Issues: [ЕСЛИ БЫЛИ]
```

---

## 🆘 Если что-то пошло не так

```markdown
# 🚨 ПРОБЛЕМА ПРИ ВЫПОЛНЕНИИ Task [НОМЕР]

Опиши проблему:
[ЧТО СЛУЧИЛОСЬ]

# ОТКАТ:
Read('/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md')
Найди секцию "🔙 Откат изменений"

Следуй инструкциям:
1. git log -1
2. git reset --hard HEAD~1
3. python3 server.py  # Проверь что работает
4. Опиши проблему для анализа

# ЗАТЕМ:
Либо:
A) Попробуй задачу заново (с учётом ошибок)
B) Создай issue с описанием проблемы
C) Пропусти задачу и сделай независимую
```

---

---

# 📚 Дополнительные ресурсы

## Файлы проекта

- **Контекст:** `/home/admsrv/mcp_comet_for_claude_code/.claude/CLAUDE.md`
- **Roadmap:** `/home/admsrv/mcp_comet_for_claude_code/docs/roadmap-v2.md`
- **Код:** `/home/admsrv/mcp_comet_for_claude_code/`

## Внешние ссылки

- **MCP Spec:** https://spec.modelcontextprotocol.io/
- **CDP Docs:** https://chromedevtools.github.io/devtools-protocol/
- **pychrome:** https://github.com/fate0/pychrome

## Git workflow

```bash
# Текущая ветка roadmap
git checkout feature/roadmap-v2

# Для каждой задачи (опционально)
git checkout -b task-1.1-metadata
# ... работа ...
git commit -m "..."
git checkout feature/roadmap-v2
git merge task-1.1-metadata
```

---

# 🎯 Quick Start для нового разработчика

Ты новый разработчик? Начни здесь:

1. **Прочитай контекст проекта:**
   ```bash
   cat .claude/CLAUDE.md
   ```

2. **Прочитай этот roadmap полностью** (да, целиком!)

3. **Проверь текущий статус:**
   ```bash
   git log --oneline --graph --all
   git branch
   ```

4. **Определи что уже сделано:**
   - Ищи коммиты с "Task X.Y"
   - Проверь checklist критериев успеха

5. **Выбери следующую задачу:**
   - Посмотри граф зависимостей
   - Начни с независимой или следующей в цепочке

6. **Используй промпты из roadmap:**
   - Копируй промпт для новой задачи
   - Следуй шагам
   - Не импровизируй - всё уже продумано!

---

**🤖 Roadmap V2.1 - Актуализирован и готов к использованию**

**Изменения в v2.1:**
- ✅ Исправлена Task 2.4 (оптимизация вместо удаления редиректов)
- ✅ Добавлен граф зависимостей
- ✅ Добавлены критерии успеха всего roadmap
- ✅ Добавлены инструкции по откату
- ✅ Сокращено время: 44h → 28h
- ✅ Добавлена система промптов для новых чатов
- ✅ Sprint 3 помечен как "NOT READY" (концепции)
- ✅ Улучшены все промпты с явным указанием зависимостей

**Версия:** 2.1
**Дата:** 2025-10-07
**Статус:** Ready for execution ✅
