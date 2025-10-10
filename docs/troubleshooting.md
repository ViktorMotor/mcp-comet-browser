# Устранение неполадок MCP Comet Browser

## Обновление MCP сервера

### Если MCP сервер уже установлен в Claude Code

1. **Обновите код из репозитория:**
   ```bash
   cd ~/mcp-comet-browser
   git pull
   ```

2. **Перезапустите Claude Code:**
   - Полностью закройте Claude Code
   - Запустите снова
   - Новые команды появятся автоматически

3. **Проверьте доступность новых команд:**
   - Спросите Claude: "Какие команды доступны в comet-browser?"
   - Должно быть 29 команд, включая DevTools и диагностику

### Альтернативный способ (если не помогло)

1. Удалите старую конфигурацию:
   ```bash
   # Linux/WSL/macOS
   nano ~/.config/claude-code/mcp_settings.json

   # Windows
   notepad "%APPDATA%\Claude Code\mcp_settings.json"
   ```

2. Перезапустите Claude Code

3. Добавьте конфигурацию заново (см. README.md)

---

## Ошибка: "Tab has been stopped"

### Причины

Эта ошибка возникает, когда:
- Вкладка браузера была закрыта
- Браузер был перезапущен
- CDP соединение было разорвано

### Решение (автоматическое)

**Начиная с версии 1.1.0**, сервер автоматически переподключается к браузеру при потере соединения.

**Что происходит автоматически:**
1. При каждой команде проверяется статус вкладки
2. Если вкладка мертва, сервер переподключается
3. Команда выполняется на новой вкладке

### Решение (ручное для старых версий)

Если у вас старая версия сервера:

1. **Обновите сервер:**
   ```bash
   cd ~/mcp-comet-browser
   git pull
   ```

2. **Перезапустите Claude Code**

3. **Проверьте версию:**
   Спросите Claude: "Открой https://example.com"

   Если ошибка пропала - обновление прошло успешно!

### Проверка статуса браузера

Запустите в терминале:

```bash
# Проверка доступности CDP (для локального использования)
curl http://localhost:9222/json/version

# Для WSL - см. раздел "WSL Setup" ниже
```

Если возвращается JSON с информацией о браузере - CDP работает.

---

## Ошибка: "Failed to connect to browser" (WSL)

### Для пользователей WSL

**Настройка WSL подключения полностью документирована в `.claude/CLAUDE.md`**

Кратко:
1. Запустите `windows_proxy.py` на Windows (порт 9224)
2. MCP-сервер автоматически определит IP Windows-хоста
3. Monkey-patches в `browser/connection.py` обработают WebSocket URLs

**Полная инструкция:** См. `.claude/CLAUDE.md` → "WSL2 Setup"

### Для локального использования (не WSL)

**1. Проверьте, запущен ли браузер с CDP:**

```bash
lsof -i :9222
# или на Windows
netstat -ano | findstr :9222
```

**2. Запустите браузер с CDP:**

```bash
# Linux/Mac
/path/to/chrome --remote-debugging-port=9222

# Windows (Comet/Perplexity)
"C:\Users\<USERNAME>\AppData\Local\Perplexity\Comet\Application\Comet.exe" --remote-debugging-port=9222
```

---

## MCP сервер не отвечает

### Причины
- Сервер не запущен
- Ошибка в конфигурации
- Python зависимости не установлены

### Решение

**1. Проверьте логи Claude Code:**

Linux/WSL:
```bash
tail -f ~/.config/claude-code/logs/mcp-server-*.log
```

Windows:
```cmd
type "%APPDATA%\Claude Code\logs\mcp-server-*.log"
```

**2. Проверьте зависимости:**
```bash
cd ~/mcp-comet-browser
pip install -r requirements.txt
```

**3. Проверьте конфигурацию:**
```bash
cat ~/.config/claude-code/mcp_settings.json
```

Должно быть:
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

**4. Тестируйте сервер вручную:**
```bash
cd ~/mcp-comet-browser
python3 server.py
```

Введите:
```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}
```

Должен вернуться JSON с serverInfo.

---

## Команды DevTools не работают

### Причины
- Старая версия сервера (до 1.1.0)
- Claude Code не перезапущен после обновления

### Решение

**1. Обновите сервер:**
```bash
cd ~/mcp-comet-browser
git pull
```

**2. Перезапустите Claude Code полностью**

**3. Проверьте список команд:**

Спросите Claude:
```
Покажи список всех доступных команд comet-browser
```

Должно быть **29 команд** (полный список в `.claude/CLAUDE.md`):
- Навигация: open_url, get_text
- Взаимодействие: click, click_by_text, scroll_page, move_cursor
- DevTools: open_devtools, console_command, get_console_logs, inspect_element, get_network_activity, etc.
- Вкладки: list_tabs, create_tab, close_tab, switch_tab
- Диагностика: diagnose_page, debug_element, force_click, etc.
- И другие...

---

## Консольные логи не перехватываются

### Причина
Перехватчик устанавливается только после первого вызова `get_console_logs`.

### Решение

**1. Инициализируйте перехватчик:**

Спросите Claude:
```
Получи логи консоли из браузера
```

**2. После этого все новые логи будут перехватываться**

**3. Проверьте:**
```
Выполни в консоли: console.log("test")
Получи логи консоли
```

Должен вернуться лог с сообщением "test".

---

## Производительность

### Медленная работа

**Причины:**
- Много вкладок открыто в браузере
- Большие страницы с тяжелым DOM
- Медленное сетевое соединение

**Оптимизация:**

1. **Закройте лишние вкладки**

2. **Используйте таймауты:**
   ```
   Открой URL с таймаутом 10 секунд
   ```

3. **Отключите изображения (опционально):**
   ```
   Выполни в консоли: document.querySelectorAll('img').forEach(img => img.remove())
   ```

---

## Диагностика

### Полная проверка системы

Запустите:
```bash
cd ~/mcp-comet-browser
python3 check_env.py
```

Должно вернуть:
```
✓ Python 3.10.x
✓ pychrome is installed
✓ Chrome DevTools Protocol is accessible
✓ All checks passed!
```

### Проверка версии сервера

```bash
cd ~/mcp-comet-browser
git log --oneline -1
```

Последний коммит должен содержать "DevTools" или дату после 2025-01-15.

### Проверка MCP протокола

Тест через stdin/stdout:
```bash
cd ~/mcp-comet-browser
python3 server.py
```

Введите:
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

Должен вернуться список из 29 инструментов.

---

## Часто задаваемые вопросы

**Q: Нужно ли перезапускать браузер после обновления сервера?**
A: Нет, только перезапустите Claude Code.

**Q: Как узнать, что сервер обновился?**
A: Спросите Claude: "Сколько команд доступно в comet-browser?" Должно быть 29 команд.

**Q: Работает ли автопереподключение?**
A: Да, начиная с версии 1.1.0. Проверьте: закройте вкладку браузера, затем попросите Claude открыть URL - должно работать.

**Q: Можно ли использовать несколько вкладок одновременно?**
A: Сейчас сервер работает только с первой вкладкой. Поддержка множества вкладок планируется.

**Q: Как отладить проблемы с DevTools?**
A: Включите логирование:
```bash
cd ~/mcp-comet-browser
python3 server.py 2>&1 | tee server.log
```

---

## Получение помощи

Если проблема не решена:

1. **Проверьте Issues на GitHub:**
   https://github.com/ViktorMotor/mcp-comet-browser/issues

2. **Создайте новый Issue с информацией:**
   - Версия Python: `python3 --version`
   - Версия сервера: `git log -1 --oneline`
   - Текст ошибки
   - Логи: `tail -100 ~/.config/claude-code/logs/mcp-server-comet-browser.log`

3. **Попробуйте полную переустановку:**
   ```bash
   cd ~
   rm -rf mcp-comet-browser
   git clone https://github.com/ViktorMotor/mcp-comet-browser.git
   cd mcp-comet-browser
   pip install -r requirements.txt
   python3 check_env.py
   ```
