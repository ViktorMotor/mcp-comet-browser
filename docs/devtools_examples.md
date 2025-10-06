# DevTools Features Examples

## Обзор

MCP сервер для Comet теперь поддерживает работу с DevTools (панель разработчика). Это позволяет ИИ:
- Открывать/закрывать DevTools (F12)
- Выполнять команды в консоли
- Получать логи консоли
- Инспектировать элементы (как в DevTools Inspector)
- Анализировать сетевую активность (как в Network панели)

## Доступные команды

### 1. open_devtools
Открывает DevTools в браузере (эмулирует нажатие F12).

**Пример:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "open_devtools",
    "arguments": {}
  }
}
```

**Ответ:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "message": "DevTools opened (F12). Note: UI may not show via CDP, but debugging is active.",
    "tip": "DevTools functionality is available through console_command and get_console_logs"
  }
}
```

---

### 2. close_devtools
Закрывает DevTools в браузере.

**Пример:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "close_devtools",
    "arguments": {}
  }
}
```

---

### 3. console_command
Выполняет команду в консоли DevTools и возвращает результат.

**Примеры команд:**

**Получить заголовок страницы:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "console_command",
    "arguments": {
      "command": "document.title"
    }
  }
}
```

**Подсчитать количество ссылок:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "console_command",
    "arguments": {
      "command": "document.querySelectorAll('a').length"
    }
  }
}
```

**Получить текущий URL:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "console_command",
    "arguments": {
      "command": "window.location.href"
    }
  }
}
```

**Выполнить console.log:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "console_command",
    "arguments": {
      "command": "console.log('Hello from Claude!')"
    }
  }
}
```

**Ответ:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "success": true,
    "result": "Example Domain",
    "type": "string"
  }
}
```

---

### 4. get_console_logs
Получает все логи из консоли браузера (log, warn, error, info, debug).

**Пример:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "get_console_logs",
    "arguments": {
      "clear": false
    }
  }
}
```

**С очисткой после получения:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "get_console_logs",
    "arguments": {
      "clear": true
    }
  }
}
```

**Ответ:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "success": true,
    "logs": [
      {
        "type": "log",
        "message": "Hello from Claude!",
        "timestamp": "2025-01-15T10:30:00.000Z"
      },
      {
        "type": "error",
        "message": "TypeError: Cannot read property 'foo' of undefined",
        "timestamp": "2025-01-15T10:30:05.000Z"
      },
      {
        "type": "warn",
        "message": "Deprecated API usage",
        "timestamp": "2025-01-15T10:30:10.000Z"
      }
    ],
    "count": 3,
    "cleared": false
  }
}
```

---

### 5. inspect_element
Инспектирует элемент на странице (как DevTools Inspector). Возвращает HTML, атрибуты, стили, позицию.

**Пример:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "tools/call",
  "params": {
    "name": "inspect_element",
    "arguments": {
      "selector": "h1"
    }
  }
}
```

**Ответ:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "success": true,
    "selector": "h1",
    "nodeId": 12,
    "html": "<h1>Example Domain</h1>",
    "attributes": ["id", "main-heading", "class", "title"],
    "info": {
      "tagName": "H1",
      "id": "main-heading",
      "className": "title",
      "textContent": "Example Domain",
      "position": {
        "top": 100,
        "left": 50,
        "width": 300,
        "height": 40
      },
      "styles": {
        "display": "block",
        "position": "static",
        "color": "rgb(0, 0, 0)",
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "fontSize": "32px",
        "fontFamily": "Arial, sans-serif"
      }
    }
  }
}
```

---

### 6. get_network_activity
Получает сетевую активность страницы (как DevTools Network панель). Показывает загруженные ресурсы, тайминги, размеры.

**Пример:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "get_network_activity",
    "arguments": {}
  }
}
```

**Ответ:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "success": true,
    "navigation": {
      "url": "https://example.com/",
      "duration": 250.5,
      "domContentLoaded": 150.2,
      "loadComplete": 200.8
    },
    "resources": [
      {
        "name": "https://example.com/style.css",
        "type": "link",
        "duration": 50.2,
        "size": 15420,
        "startTime": 10.5
      },
      {
        "name": "https://example.com/script.js",
        "type": "script",
        "duration": 80.5,
        "size": 45230,
        "startTime": 15.2
      },
      {
        "name": "https://example.com/image.png",
        "type": "img",
        "duration": 120.8,
        "size": 125000,
        "startTime": 20.1
      }
    ],
    "resourceCount": 3
  }
}
```

---

## Примеры использования через Claude Code

### Отладка JavaScript ошибок

```
1. Открой https://example.com
2. Получи логи консоли
3. Если есть ошибки, покажи их
```

### Анализ производительности

```
1. Открой https://example.com
2. Получи сетевую активность
3. Покажи самые медленные ресурсы
```

### Инспекция элементов

```
1. Открой https://example.com
2. Инспектируй элемент .header
3. Покажи его размеры и позицию
```

### Выполнение команд в консоли

```
1. Открой https://example.com
2. Выполни в консоли: document.querySelectorAll('img').length
3. Покажи сколько изображений на странице
```

### Отслеживание логов в реальном времени

```
1. Открой https://example.com
2. Выполни в консоли: console.log("Start monitoring")
3. Кликни на кнопку "Submit"
4. Получи логи консоли
5. Очисти логи
```

---

## Расширение функционала

Вы можете расширить DevTools функционал через команду `console_command`:

**Примеры расширенных команд:**

**Получить cookies:**
```javascript
document.cookie
```

**Изменить стиль элемента:**
```javascript
document.querySelector('h1').style.color = 'red'
```

**Получить localStorage:**
```javascript
Object.keys(localStorage).map(key => ({key, value: localStorage.getItem(key)}))
```

**Прокрутить страницу:**
```javascript
window.scrollTo(0, document.body.scrollHeight)
```

**Выполнить fetch запрос:**
```javascript
fetch('https://api.example.com/data').then(r => r.json())
```

**Получить размеры окна:**
```javascript
({width: window.innerWidth, height: window.innerHeight})
```

---

## Технические детали

### Принцип работы

1. **Chrome DevTools Protocol (CDP)** - все команды используют CDP для взаимодействия с браузером
2. **Runtime Domain** - используется для выполнения JavaScript в контексте страницы
3. **Console Domain** - включается автоматически при подключении для перехвата логов
4. **Network Domain** - включается для мониторинга сетевой активности
5. **DOM Domain** - используется для инспекции элементов

### Ограничения

- **UI DevTools** - визуальное открытие/закрытие DevTools панели может не работать через CDP, но функционал доступен через API
- **Консольные логи** - перехватываются только после первого вызова `get_console_logs` (устанавливается перехватчик)
- **Сетевая активность** - показывает только ресурсы, загруженные через Performance API
- **Асинхронные операции** - для команд с Promise используется `awaitPromise: true`

### Безопасность

- Все команды выполняются в контексте текущей страницы
- Нет доступа к файловой системе через DevTools API
- Ограничения CORS применяются ко всем fetch запросам

---

## FAQ

**Q: Почему DevTools UI не открывается визуально?**
A: CDP не может открыть физическое окно DevTools, но весь функционал доступен через API команды.

**Q: Как получить логи, которые были до запуска сервера?**
A: Логи перехватываются только после первого вызова `get_console_logs`. Предыдущие логи недоступны.

**Q: Можно ли выполнять асинхронный код в консоли?**
A: Да, используйте `console_command` с Promise или async/await кодом.

**Q: Как отладить ошибки JavaScript на странице?**
A: Используйте `get_console_logs` для получения всех ошибок, или `console_command` для проверки состояния.
