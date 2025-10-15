# evaluate_js - Examples & Testing Guide

> Updated implementation with smart output handling (2025-10-15)

## What's New

### Key Improvements
1. **Actually executes user code** (old version just called save_page_info!)
2. **Console.log capture** - Automatically captures console output
3. **Smart serialization** - Handles objects, arrays, functions, errors
4. **Timeout protection** - 30s default, configurable
5. **Auto file save** - Large results (>2KB) saved to `./js_result.json`
6. **Better error messages** - Stack traces, line numbers

---

## Usage Examples

### 1. Simple Expressions
```javascript
// Get page title
evaluate_js(code="document.title")
// → {success: true, result: "Page Title", type: "string"}

// Count links
evaluate_js(code="document.querySelectorAll('a').length")
// → {success: true, result: 42, type: "number"}

// Get URL
evaluate_js(code="window.location.href")
// → {success: true, result: "https://example.com", type: "string"}
```

### 2. With console.log
```javascript
// Console output is captured
evaluate_js(code=`
  console.log('Starting calculation');
  const result = 2 + 2;
  console.log('Result:', result);
  return result;
`)
// → {
//   success: true,
//   result: 4,
//   type: "number",
//   console_output: [
//     {level: "log", args: ["Starting calculation"]},
//     {level: "log", args: ["Result:", "4"]}
//   ]
// }
```

### 3. Return Objects
```javascript
// Return complex object
evaluate_js(code=`
  return {
    title: document.title,
    links: document.querySelectorAll('a').length,
    images: document.querySelectorAll('img').length,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight
    }
  };
`)
// → {
//   success: true,
//   result: {title: "...", links: 10, images: 5, viewport: {...}},
//   type: "object"
// }
```

### 4. Arrays
```javascript
// Get all link texts
evaluate_js(code=`
  return Array.from(document.querySelectorAll('a'))
    .map(a => a.textContent.trim())
    .filter(text => text.length > 0);
`)
// → {success: true, result: ["Home", "About", "Contact"], type: "array"}
```

### 5. Error Handling
```javascript
// Syntax error
evaluate_js(code="this is invalid javascript")
// → {
//   success: false,
//   error: "JavaScript execution error",
//   exception: {
//     type: "SyntaxError",
//     message: "Unexpected identifier",
//     line: 1,
//     column: 5
//   }
// }

// Runtime error
evaluate_js(code="document.querySelector('.nonexistent').click()")
// → {
//   success: true,
//   result: {
//     error: true,
//     name: "TypeError",
//     message: "Cannot read property 'click' of null",
//     stack: [...]
//   },
//   type: "error"
// }
```

### 6. Functions
```javascript
// Return function (gets stringified)
evaluate_js(code=`
  return function greet(name) {
    return 'Hello, ' + name;
  };
`)
// → {
//   success: true,
//   result: {function_source: "function greet(name) { return 'Hello, ' + name; }"},
//   type: "function"
// }
```

### 7. Timeout Control
```javascript
// Short timeout for quick checks
evaluate_js(code="document.title", timeout=5)

// Longer timeout for complex operations
evaluate_js(code=`
  // Complex DOM manipulation
  return Array.from(document.querySelectorAll('*')).map(el => ({
    tag: el.tagName,
    id: el.id
  }));
`, timeout=60)
```

### 8. Disable Console Capture
```javascript
// Don't capture console (faster)
evaluate_js(code="document.title", capture_console=false)
// → {success: true, result: "Page Title", type: "string"}
// (no console_output field)
```

---

## Testing Checklist

### Basic Operations
- [ ] Simple string: `evaluate_js(code="document.title")`
- [ ] Number: `evaluate_js(code="document.querySelectorAll('a').length")`
- [ ] Boolean: `evaluate_js(code="window.scrollY > 0")`
- [ ] Null: `evaluate_js(code="null")`
- [ ] Undefined: `evaluate_js(code="undefined")`

### Complex Types
- [ ] Object: `evaluate_js(code="return {a: 1, b: 2};")`
- [ ] Array: `evaluate_js(code="[1, 2, 3, 4, 5]")`
- [ ] Nested object (depth limit): `evaluate_js(code="return {a: {b: {c: {d: {e: 'deep'}}}}};")`
- [ ] Large array (50 item limit): `evaluate_js(code="Array(100).fill(0).map((_, i) => i)")`

### Console Capture
- [ ] console.log: `evaluate_js(code="console.log('test'); return 42;")`
- [ ] console.warn: `evaluate_js(code="console.warn('warning'); return 'ok';")`
- [ ] console.error: `evaluate_js(code="console.error('error'); return 'done';")`
- [ ] Multiple logs: `evaluate_js(code="console.log('a'); console.log('b'); return 'c';")`

### Error Handling
- [ ] Syntax error: `evaluate_js(code="invalid javascript")`
- [ ] Runtime error: `evaluate_js(code="throw new Error('test error');")`
- [ ] Null reference: `evaluate_js(code="document.querySelector('.none').click()")`

### Large Results
- [ ] Large object (>2KB): Should auto-save to `./js_result.json`
  ```javascript
  evaluate_js(code=`
    return Array(1000).fill(0).map((_, i) => ({
      id: i,
      text: 'Item ' + i,
      data: {x: i, y: i * 2}
    }));
  `)
  ```
- [ ] Then: `Read('./js_result.json')` to verify

### Timeout
- [ ] Quick operation with 1s timeout: `evaluate_js(code="document.title", timeout=1)`
- [ ] Should fail on infinite loop (30s timeout):
  ```javascript
  evaluate_js(code="while(true) {}")
  ```

---

## Common Use Cases

### 1. Get Page Metadata
```javascript
evaluate_js(code=`
  return {
    title: document.title,
    url: window.location.href,
    referrer: document.referrer,
    cookies_enabled: navigator.cookieEnabled,
    language: navigator.language,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY
    }
  };
`)
```

### 2. Count Elements by Type
```javascript
evaluate_js(code=`
  const counts = {};
  document.querySelectorAll('*').forEach(el => {
    const tag = el.tagName.toLowerCase();
    counts[tag] = (counts[tag] || 0) + 1;
  });
  return counts;
`)
```

### 3. Find Elements with Text
```javascript
evaluate_js(code=`
  const searchText = 'button';
  return Array.from(document.querySelectorAll('*'))
    .filter(el => el.textContent.toLowerCase().includes(searchText))
    .map(el => ({
      tag: el.tagName,
      text: el.textContent.substring(0, 50),
      id: el.id || null,
      className: el.className || null
    }));
`)
```

### 4. Check Element Visibility
```javascript
evaluate_js(code=`
  const selector = '#my-element';
  const el = document.querySelector(selector);
  if (!el) return {exists: false};

  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);

  return {
    exists: true,
    visible: rect.width > 0 && rect.height > 0 && style.display !== 'none',
    rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
    style: {
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity
    }
  };
`)
```

### 5. Modify Page (with feedback)
```javascript
evaluate_js(code=`
  console.log('Adding dark mode styles...');
  const style = document.createElement('style');
  style.textContent = 'body { background: #1a1a1a; color: #fff; }';
  document.head.appendChild(style);
  console.log('Dark mode enabled');
  return {success: true, message: 'Dark mode applied'};
`)
```

---

## Comparison: Old vs New

### Old Implementation (BROKEN)
```javascript
// ❌ Ignored user code, always called save_page_info
evaluate_js(code="document.title")
// → Saved page_info.json with ALL interactive elements (wrong!)
```

### New Implementation (FIXED)
```javascript
// ✅ Actually executes the code you provide
evaluate_js(code="document.title")
// → {success: true, result: "Page Title", type: "string"}

// ✅ Large results auto-save
evaluate_js(code="Array(1000).fill(0).map((_, i) => ({id: i}))")
// → {success: true, message: "Result too large - saved to js_result.json", ...}
```

---

## Performance Notes

### Token Usage
- **Small results (<2KB)**: Returned directly (~500 tokens)
- **Large results (>2KB)**: Saved to file, only preview returned (~200 tokens)
- **Console output**: ~10 tokens per log message

### Execution Speed
- Simple expressions: <100ms
- DOM queries: 100-500ms
- Complex operations: 500ms-5s
- Timeout default: 30s (configurable)

---

## Troubleshooting

### "Result too large" error
**Cause:** Result >2KB
**Solution:** File auto-saved to `./js_result.json`, use `Read('./js_result.json')`

### Timeout error
**Cause:** Code runs >30s
**Solutions:**
1. Increase timeout: `evaluate_js(code="...", timeout=60)`
2. Simplify code (avoid infinite loops)

### "Cannot read property X of null"
**Cause:** Element not found
**Solution:** Add null checks:
```javascript
const el = document.querySelector('.my-element');
if (!el) return {error: 'Element not found'};
return el.textContent;
```

### Console output not captured
**Cause:** `capture_console=false`
**Solution:** Use default or `capture_console=true`

---

## Migration Guide

If you were using the old `evaluate_js`:

### Before (old broken version)
```javascript
// This NEVER executed your code!
evaluate_js(code="document.title")
// Always returned page_info.json with interactive elements
```

### After (new fixed version)
```javascript
// This actually runs your code
evaluate_js(code="document.title")
// → {success: true, result: "Page Title", type: "string"}

// If you need page info, use the dedicated command:
save_page_info()  // Then Read('./page_info.json')
```

---

## Architecture

### Execution Flow
1. **Wrap user code** with console capture + serialization
2. **Execute** via CDP Runtime.evaluate
3. **Parse result** - extract return value, type, console output
4. **Format** - handle primitives, objects, arrays, functions, errors
5. **Size check** - if >2KB, save to file; else return directly
6. **Response** - success/error with formatted data

### Code Wrapping
User code is wrapped in an IIFE:
```javascript
(function() {
  const capturedConsole = [];

  // Console monkey-patch
  console.log = function(...args) {
    capturedConsole.push({level: 'log', args: args.map(String)});
  };

  // Execute user code
  const userFunction = new Function(`USER_CODE_HERE`);
  result = userFunction();

  // Type detection + serialization
  return {
    result: result,
    type: typeof result,
    console: capturedConsole
  };
})()
```

---

## See Also

- `save_page_info` - Get full page state (elements, console, network)
- `console_command` - Execute commands in DevTools console
- `get_console_logs` - Get existing console logs
- `open_devtools` - Open DevTools for manual debugging

---

**Last Updated:** 2025-10-15
**Version:** 2.1.0 (Roadmap V2 + evaluate_js fix)
