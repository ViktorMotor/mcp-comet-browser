# 🔍 Verbose Proxy Guide - Детальное логирование трафика

## 📋 Что изменилось

Добавлен **verbose режим** в `windows_proxy.py` для просмотра трафика между WSL и браузером.

---

## 🚀 Использование

### Обычный режим (по умолчанию):
```powershell
python windows_proxy.py
```
**Показывает:**
- TCP подключения (IP:порт)
- Старт/стоп прокси

### Verbose режим - только вызовы инструментов (НОВОЕ):

#### Level 1 (рекомендуется) - только tool calls:
```powershell
python windows_proxy.py -v
# ИЛИ
python windows_proxy.py --verbose 1
```
**Показывает ТОЛЬКО:**
- 🌐 Navigate to: https://example.com
- 🖱️  Move cursor
- 🖱️  Click element
- 🔍 Query DOM
- 📸 Take screenshot
- ✅ Success / ❌ Error для каждого действия

**Скрывает весь технический шум!**

#### Level 2 - tool calls + все CDP responses:
```powershell
python windows_proxy.py --verbose 2
```
**Показывает:**
- ✅ Все из Level 1
- ✅ CDP responses для непомеченных команд
- ✅ JavaScript evaluation previews
- ✅ Console и exception события

#### Level 3 - полный дамп (для отладки протокола):
```powershell
python windows_proxy.py --verbose 3
```
**Показывает:**
- ✅ Абсолютно всё
- ✅ Все CDP события (Network.*, Page.frame*, и т.д.)
- ⚠️ **Внимание:** Очень много логов!

---

## 📺 Примеры вывода

### Обычный режим:
```
[2025-10-22 14:23:45] [*] CDP Proxy listening on 0.0.0.0:9224
[2025-10-22 14:23:45] [*] Forwarding to 127.0.0.1:9222
[2025-10-22 14:23:45] [*] Press Ctrl+C to stop
[2025-10-22 14:23:45] [*] Tip: Use --verbose or -v to see detailed traffic logs

[2025-10-22 14:23:46] [+] Connection from 172.23.128.1:52341
```

### Verbose Level 1 (только tool calls) - ЧИСТО И ПОЛЕЗНО:
```
[2025-10-22 14:23:45] [*] CDP Proxy listening on 0.0.0.0:9224
[2025-10-22 14:23:45] [*] VERBOSE MODE: Level 1 - tool calls only (clicks, navigation, screenshots)
[2025-10-22 14:23:45] [*] Press Ctrl+C to stop

[2025-10-22 14:23:46] [+] Connection from 172.23.128.1:52341
[2025-10-22 14:23:46] [VERBOSE] WSL→Browser GET /json/version HTTP/1.1
[2025-10-22 14:23:48] [VERBOSE] WSL→Browser GET /devtools/page/ABC123 HTTP/1.1
[2025-10-22 14:23:48] [VERBOSE] Browser→WSL WebSocket connected
[2025-10-22 14:23:50] [VERBOSE] WSL→Browser 🌐 Navigate to: https://example.com
[2025-10-22 14:23:51] [VERBOSE] Browser→WSL   ✅ Success: 🌐 Navigate to: https://example.com
[2025-10-22 14:23:52] [VERBOSE] WSL→Browser 🔍 Query DOM
[2025-10-22 14:23:52] [VERBOSE] Browser→WSL   ✅ Success: 🔍 Query DOM
[2025-10-22 14:23:53] [VERBOSE] WSL→Browser 🖱️  Move cursor
[2025-10-22 14:23:53] [VERBOSE] Browser→WSL   ✅ Success: 🖱️  Move cursor
[2025-10-22 14:23:54] [VERBOSE] WSL→Browser 🖱️  Click element
[2025-10-22 14:23:54] [VERBOSE] Browser→WSL   ✅ Success: 🖱️  Click element
[2025-10-22 14:23:55] [VERBOSE] WSL→Browser 📸 Take screenshot
[2025-10-22 14:23:56] [VERBOSE] Browser→WSL   ✅ Success: 📸 Take screenshot
```
✅ **Только действия браузера - ничего лишнего!**

---

## 🎯 Что показывает VERBOSE режим (Level 1)

| Действие | Формат лога | Пример |
|----------|-------------|--------|
| **Подключение** | `Connection from <IP>` | `[+] Connection from 172.23.128.1:52341` |
| **WebSocket handshake** | `GET /devtools/...` | `WSL→Browser GET /devtools/page/ABC123` |
| **Навигация** | `🌐 Navigate to: <URL>` | `🌐 Navigate to: https://example.com` |
| **Поиск элементов** | `🔍 Query DOM` | `🔍 Query DOM` |
| **Перемещение курсора** | `🖱️  Move cursor` | `🖱️  Move cursor` |
| **Клик** | `🖱️  Click element` | `🖱️  Click element` |
| **Скриншот** | `📸 Take screenshot` | `📸 Take screenshot` |
| **Успех** | `✅ Success: <действие>` | `✅ Success: 🖱️  Click element` |
| **Ошибка** | `❌ Error: <действие> - <msg>` | `❌ Error: 🖱️  Click - Node not found` |

---

## ⚠️ Важно понимать

### Что VERBOSE Level 1 покажет:
✅ **Действия браузера:** клики, навигация, скриншоты
✅ **Результаты действий:** успех/ошибка
✅ **Чистый вывод** без технического шума
✅ **Идеально для мониторинга** работы Claude Code

### Что VERBOSE НЕ покажет (Level 1):
❌ Network.* события (загрузка ресурсов)
❌ Page.frame* события (внутренние переходы)
❌ Runtime.executionContext* (создание контекстов)
❌ WebSocket binary frames
❌ **Логи MCP сервера** (смотри Claude Code stderr)

---

## 📊 Где смотреть разные типы логов

| Что нужно увидеть | Где смотреть | Как включить |
|-------------------|--------------|--------------|
| TCP подключения | `windows_proxy.py` | Запустить без флагов |
| **Действия браузера (клики, навигация)** | **`windows_proxy.py -v`** | **Level 1 (рекомендуется)** |
| Действия + CDP responses | `windows_proxy.py --verbose 2` | Level 2 |
| Полный CDP дамп | `windows_proxy.py --verbose 3` | Level 3 (debug only) |
| **Логи MCP сервера** | **Claude Code stderr** | Автоматически |
| Детальная отладка MCP | Claude Code stderr | `MCP_LOG_LEVEL=DEBUG` |

---

## 🔄 Как перезапустить с verbose

1. **Остановите текущий прокси:**
   ```powershell
   # В PowerShell где запущен прокси: Ctrl+C
   ```

2. **Запустите с verbose:**
   ```powershell
   python windows_proxy.py --verbose
   ```

3. **Смотрите улучшенные логи** (без мусора!)

---

## 🎓 Улучшения в verbose режиме

### До (версия 2.18.1):
```
[VERBOSE] WSL→Browser Data: ♀W" J↑ضWOԁTC♫ؔCQYܟRQ ~☻☻☻҂WK♂ށL☻☻☻☻... (3167 bytes)
[VERBOSE] Browser→WSL CDP Event: Network.dataReceived (150 bytes)
[VERBOSE] Browser→WSL CDP Event: Network.dataReceived (150 bytes)
[VERBOSE] Browser→WSL Text: ldId":"","executionContextAuxData":... (8192 bytes)
[VERBOSE] Browser→WSL Text: iAgb25TZWxlY3RBbGw6ICgpID0+IHZvaWQ7XG4gIG... (8192 bytes)
[VERBOSE] Browser→WSL JSON-like data (125 bytes)
```
❌ Мусор от WebSocket fragments
❌ Шум от CDP событий
❌ Нечитаемо

### После (версия 2.18.1+tool-calls-only):
```
[VERBOSE] WSL→Browser 🌐 Navigate to: https://example.com
[VERBOSE] Browser→WSL   ✅ Success: 🌐 Navigate to: https://example.com
[VERBOSE] WSL→Browser 🖱️  Click element
[VERBOSE] Browser→WSL   ✅ Success: 🖱️  Click element
[VERBOSE] WSL→Browser 📸 Take screenshot
[VERBOSE] Browser→WSL   ✅ Success: 📸 Take screenshot
```
✅ **95% меньше логов!**
✅ Только действия браузера
✅ Вызов + результат для каждого действия
✅ Идеально для мониторинга Claude Code

---

## 💡 Итог

**Рекомендации по выбору уровня:**

| Сценарий | Уровень | Команда |
|----------|---------|---------|
| Обычное использование | Без verbose | `python windows_proxy.py` |
| Отладка подключения | Level 1 | `python windows_proxy.py -v` |
| Проблемы с CDP | Level 2 | `python windows_proxy.py --verbose 2` |
| Глубокая отладка | Level 3 | `python windows_proxy.py --verbose 3` |

**Используйте verbose режим когда:**
- ✅ Нужно **мониторить действия Claude Code** в браузере
- ✅ Проверить что **клики и навигация работают**
- ✅ Увидеть **результаты выполнения** (success/error)
- ✅ Отладить проблемы с **browser automation**

**НО помните:**
- ℹ️ **Level 1** - только tool calls (рекомендуется для повседневного использования)
- ℹ️ **Level 2** - для детальной отладки CDP
- ℹ️ **Level 3** - для отладки протокола (очень много логов!)
- ❌ Для **логов MCP сервера** смотрите **Claude Code stderr**

---

**Автор:** Рефакторинг логирования MCP Comet Browser
**Дата:** 2025-10-22
**Версия:** 2.18.1+tool-calls-only
**Новые фичи:**
- 🎯 **Только tool calls на Level 1** - чистый и полезный вывод
- 🔄 **Request/Response tracking** - вызов + результат
- 🎨 **Эмодзи индикаторы** для действий (🌐🖱️📸🔍)
- ✅ **Success/Error статусы** для каждого действия
- 📉 **95% сокращение логов** на Level 1
