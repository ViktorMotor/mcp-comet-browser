# Исследование ассистента Comet Browser

## Цель
Интегрировать взаимодействие с встроенным AI-ассистентом Comet через MCP-сервер.

## План исследования

### 1. Определить точку входа
```javascript
// Проверить горячие клавиши
document.addEventListener('keydown', (e) => {
  console.log(`Key: ${e.key}, Ctrl: ${e.ctrlKey}, Alt: ${e.altKey}, Shift: ${e.shiftKey}`);
});

// Найти кнопки ассистента
document.querySelectorAll('button, [role="button"]').forEach(btn => {
  const text = btn.textContent.toLowerCase();
  if (text.includes('ai') || text.includes('assistant') || text.includes('perplexity')) {
    console.log('Found AI button:', btn, btn.textContent);
  }
});
```

### 2. Найти DOM элементы интерфейса
```javascript
// Поиск полей ввода для ассистента
document.querySelectorAll('input[type="text"], textarea').forEach(input => {
  console.log('Input:', input.placeholder, input.name, input.id);
});

// Поиск панелей/контейнеров
document.querySelectorAll('[class*="assistant"], [class*="ai"], [class*="chat"]').forEach(el => {
  console.log('AI element:', el.className);
});
```

### 3. Проверить специальные URL
- `chrome://settings/` - настройки
- `chrome-extension://...` - расширения
- Внутренние страницы Comet

### 4. Исследовать через DevTools
```bash
# Команды для исследования:
mcp__comet-browser__open_devtools()
mcp__comet-browser__console_command(command="window.location.href")
mcp__comet-browser__get_page_structure()
mcp__comet-browser__find_elements(selector="[role='button']")
```

## Возможные архитектуры ассистента

### Вариант A: Sidebar (боковая панель)
- Постоянно присутствует в браузере
- Доступна через кнопку или хоткей
- DOM элементы в shadow DOM или iframe

### Вариант B: Отдельная страница
- URL типа `comet://assistant` или `https://perplexity.ai/...`
- Обычная веб-страница, легко автоматизировать

### Вариант C: Popup/Modal
- Всплывающее окно поверх текущей страницы
- DOM элементы в основном документе

### Вариант D: Browser Extension
- Реализовано как расширение Chrome
- Возможно ограничено для CDP доступа

## Команды для взаимодействия (проект)

### Новые команды для v2.8:

```python
# commands/comet_assistant.py

@register
class OpenCometAssistantCommand(Command):
    """Open Comet AI assistant"""
    name = "open_comet_assistant"
    description = "Opens the Comet browser's built-in AI assistant"

@register
class SendToCometAssistantCommand(Command):
    """Send message to Comet assistant"""
    name = "send_to_comet_assistant"
    description = "Send a message to Comet AI assistant and get response"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to send"},
            "wait_for_response": {"type": "boolean", "default": True}
        },
        "required": ["message"]
    }

@register
class GetCometAssistantResponseCommand(Command):
    """Get last response from Comet assistant"""
    name = "get_comet_assistant_response"
    description = "Retrieve the latest response from Comet AI assistant"
```

## Использование существующих команд

До создания специализированных команд, можно использовать:

1. **save_page_info()** - найти элементы интерфейса
2. **click_by_text()** - открыть ассистента
3. **evaluate_js()** - ввести текст в поле
4. **get_text()** - прочитать ответ

## Следующие шаги

1. ✅ Создать этот документ
2. ⏳ Открыть Comet и исследовать интерфейс ассистента
3. ⏳ Определить селекторы/API для взаимодействия
4. ⏳ Создать прототип команд
5. ⏳ Протестировать интеграцию
6. ⏳ Документировать для пользователей

## Вопросы для исследования

- [ ] Как называется ассистент в Comet? (Perplexity AI, Comet AI, другое?)
- [ ] Какой хоткей открывает ассистента?
- [ ] В каком элементе располагается интерфейс?
- [ ] Есть ли JavaScript API для программного доступа?
- [ ] Поддерживает ли CDP доступ к ассистенту?
- [ ] Можно ли получить историю чата?
- [ ] Поддерживаются ли вложения/изображения?

---

**Статус:** 🔍 Исследование
**Целевой релиз:** v2.8
**Приоритет:** Высокий
