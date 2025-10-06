# Troubleshooting Guide - MCP Comet Browser

## Проблема: Клики не срабатывают

### Диагностика

1. **Найти элемент и посмотреть его свойства:**
```python
debug_element(text="Тестирование")
# Вернёт все способы кликнуть по элементу
```

2. **Получить все кликабельные элементы:**
```python
get_clickable_elements(text_filter="Тестирование")
# Покажет позиции и доступные методы клика
```

3. **Диагностировать состояние страницы:**
```python
diagnose_page()
# Проверит состояние страницы, курсоры, счётчики элементов
```

### Решения

#### Способ 1: Использовать force_click (самый надёжный)
```python
# По тексту
force_click(text="Тестирование")

# По координатам (если знаете позицию)
force_click(x=500, y=300)
```

`force_click` использует **ВСЕ** доступные методы клика:
- `element.click()`
- MouseEvent (mousedown, mouseup, click)
- PointerEvent  
- TouchEvent
- focus() + onclick()

#### Способ 2: Найти точные координаты
```python
# 1. Найти элемент
elements = get_clickable_elements(text_filter="Тестирование")

# 2. Взять координаты из результата
pos = elements['elements'][0]['position']

# 3. Кликнуть по координатам
force_click(x=pos['x'], y=pos['y'])
```

#### Способ 3: Использовать debug_element
```python
# Получить все возможные селекторы
info = debug_element(text="Тестирование")

# Использовать лучший селектор
click(selector=info['elements'][0]['selectors'][0])
```

---

## Проблема: get_console_logs возвращает пустой массив

### Диагностика

1. **Проверить включено ли логирование:**
```python
diagnose_page()
# Смотрим на cursors.consoleInterceptor
```

2. **Проверить есть ли вообще логи в браузере:**
```python
console_command("console.log('test'); console.warn('warning'); console.error('error')")
# Затем сразу:
get_console_logs()
```

### Решения

#### Способ 1: Принудительно включить логирование
```python
enable_console_logging()
# Это:
# - Re-enable Console domain в CDP
# - Пересоздаёт listeners
# - Переустанавливает JS interceptor
# - Проверяет что логирование работает
```

#### Способ 2: Использовать console_command напрямую
```python
# Вместо get_console_logs, выполнить JS:
console_command("""
    window.__consoleHistory || []
""")
# Вернёт логи из JS interceptor
```

#### Способ 3: Проверить логи через Performance API
```python
console_command("""
    performance.getEntriesByType('mark').map(m => ({
        name: m.name,
        startTime: m.startTime
    }))
""")
```

---

## Проблема: DevTools открыты, но не видны на скриншоте

### Объяснение

CDP (Chrome DevTools Protocol) управляет браузером **программно**, но DevTools UI не всегда отображается визуально в Comet.

**Это нормально!** DevTools **функционально активны**, даже если не видны.

### Проверка что DevTools работают

```python
# 1. Открыть DevTools
open_devtools()

# 2. Проверить что они активны
diagnose_page()
# Смотрим на devtools.open

# 3. Использовать функции DevTools
console_command("navigator.userAgent")
inspect_element(selector="button")
get_network_activity()
```

### Если нужно ВИЗУАЛЬНО увидеть DevTools

DevTools UI в Comet может не показываться через CDP. Но вы можете:

1. **Использовать screenshot после команд:**
```python
console_command("document.title = 'DevTools Active'")
screenshot(path="./devtools_check.png")
# На скриншоте будет видно изменение title
```

2. **Вставить визуальный индикатор:**
```python
console_command("""
    const indicator = document.createElement('div');
    indicator.textContent = 'DevTools Active';
    indicator.style.cssText = 'position:fixed;top:0;right:0;background:green;color:white;padding:10px;z-index:999999';
    document.body.appendChild(indicator);
""")
screenshot(path="./indicator.png")
```

---

## Новые команды (25 total, было 20)

### Отладка кликов
1. **debug_element** - получить все селекторы и способы клика
2. **force_click** - принудительный клик всеми методами
3. **get_clickable_elements** - список всех кликабельных элементов

### Диагностика
4. **enable_console_logging** - принудительно включить логирование
5. **diagnose_page** - диагностика состояния страницы

---

## Quick Fix Checklist

### Клики не работают:
- [ ] `get_clickable_elements(text_filter="...")` - найти элемент
- [ ] `force_click(text="...")` - форсированный клик
- [ ] Если не помогло: `force_click(x=..., y=...)` по координатам

### Логи пустые:
- [ ] `enable_console_logging()` - включить логирование
- [ ] `console_command("console.log('test')")` - проверить работу
- [ ] `get_console_logs()` - получить логи

### DevTools не видны:
- [ ] Использовать `console_command()` - работает без UI
- [ ] Использовать `inspect_element()` - работает без UI
- [ ] Добавить визуальный индикатор через console_command

---

**Все новые команды протестированы и работают!** ✅
