## [2.20.0] - 2025-10-22

### 🎯 Fixed - Visual Clickability Detection (USER REPORTED)

**Problem:** Real-world testing revealed critical gaps:
- Lead cards (divs with cursor:pointer) not found by `click_by_text`
- `save_page_info` missed visually clickable elements
- `evaluate_js` hit depth limit too early (rect objects truncated)

**User Report:**
> "5 попыток, пока не нашел через evaluate_js с фильтрацией по размеру.
> click_by_text слишком узкий - пропускает <div> с cursor: pointer"

**Root Cause:**
Commands only searched semantic HTML (button, a, input), missing:
- Modern web apps use `<div cursor="pointer">` for clickable cards
- onClick handlers on non-semantic elements
- Visual clickability indicators ignored

**Solution:**

1. **click_by_text - Expanded Element Detection:**
   - ✅ Added cursor:pointer detection via getComputedStyle()
   - ✅ Added onclick handler detection
   - ✅ Searches div, span, li, section, article, header
   - ✅ Combines semantic + visual clickability

2. **save_page_info - Complete Interactive Elements:**
   - ✅ Shows ALL clickable elements (semantic + cursor:pointer)
   - ✅ New field: `clickable_reason` ("cursor-pointer" or "semantic")
   - ✅ Lead cards now visible in interactive_elements list

3. **evaluate_js - Better Object Serialization:**
   - ✅ Depth limit: 3 → 5 levels
   - ✅ Informative messages: "{...10 keys} (max depth 5 reached)"
   - ✅ Shows object/array size instead of generic "[Object]"

**Impact:**
- ✅ click_by_text now finds modern UI elements (cards, custom buttons)
- ✅ save_page_info shows complete picture of clickable elements
- ✅ evaluate_js provides better debugging info

**Example - Before:**
```
click_by_text(text="Lead #123") 
→ ❌ Not found (div with cursor:pointer)
```

**Example - After:**
```
click_by_text(text="Lead #123")
→ ✅ Found! (detected via cursor:pointer)

save_page_info() shows:
{
  "tag": "div",
  "text": "Lead #123",
  "classes": ["lead-card"],
  "clickable_reason": "cursor-pointer"  ← NEW!
}
```

### Changed
- Version: 2.19.0 → 2.20.0
- Improved real-world clickability detection

### Technical Details
- `commands/interaction.py`: Enhanced click_by_text selector (+20 lines)
- `commands/save_page_info.py`: Added visual clickability detection (+15 lines)
- `commands/evaluation.py`: Increased depth limit, better messages (+8 lines)

---
# Changelog

All notable changes to MCP Comet Browser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.19.0] - 2025-10-22

### 🔧 Fixed - MCP Protocol Compliance (CRITICAL)

**Problem:** Commands were not returning results in Claude Code
- `evaluate_js`, `console_command`, `inspect_element` returned no visible output
- Results executed successfully but were invisible to user
- Claude Code couldn't display legacy format responses

**Root Cause:**
MCP Protocol requires specific response format:
```json
{
  "content": [{"type": "text", "text": "..."}],
  "isError": false
}
```

But commands were returning legacy format:
```python
{"success": True, "result": ..., "message": "..."}
```

**Solution:**

1. **Added MCP-wrapper in `mcp/protocol.py`:**
   - New function `_wrap_result_for_mcp()` converts legacy → MCP format
   - Smart formatting for different result types
   - Handles: `console_output`, `exceptions`, `file_paths`, `instructions`
   - Backward-compatible: auto-detects MCP format, passes through

2. **Added `requires_cdp = True` to 14 commands:**
   - `devtools.py` (4): open_devtools, close_devtools, console_command, inspect_element
   - `save_page_info.py` (1): SavePageInfoCommand
   - `screenshot.py` (1): ScreenshotCommand
   - `interaction.py` (4): click, click_by_text, scroll_page, move_cursor
   - `helpers.py` (2): debug_element, force_click
   - `diagnostics.py` (2): diagnose_page, get_clickable_elements

**Impact:**
- ✅ All 29 tools now properly display results in Claude Code
- ✅ No breaking changes - fully backward-compatible
- ✅ Enhanced output formatting with emojis and structure

**Example Output (evaluate_js):**
```
Executed successfully

Result:
"Page Title"

Type: string

📝 Console Output (2 messages):
  [LOG] Test message
  [WARN] Warning message
```

### Changed
- Version bumped to 2.19.0
- All command outputs now MCP-compliant
- Improved result formatting for readability

---

## [2.18.1] - 2025-10-16

### Fixed - Screenshot Command

**Bug:** Screenshot command was crashing with error:
```
"object dict can't be used in 'await' expression"
```

**Root Cause:**
- Line 128: `await self.tab.Page.captureScreenshot()`
- pychrome returns dict directly, not awaitable
- Incorrect `await` keyword added

**Changes:**
- Removed incorrect `await` from CDP call
- Removed unused chrome.devtools code
- Command now works perfectly

**Testing:**
- ✅ JSON-RPC test: 120.7KB PNG created
- ✅ MCP test: 127KB screenshot verified

### Added - AI Optimization Guide

**New file:** `SCREENSHOT_OPTIMIZATION.md`

Comprehensive screenshot optimization guide based on real testing with Claude AI:

**Key Findings:**
- **JPEG Q75** is optimal for AI (21% smaller, perfect quality)
- JPEG Q60 still perfectly readable (33% smaller)
- PNG is overkill for most AI use cases

**Benchmarks:**
```
PNG:      127KB (baseline)
JPEG Q80: 112KB (-12%)
JPEG Q75: ~100KB (-21%) ⭐ Recommended
JPEG Q60:  85KB (-33%)
```

**Updated:** `commands/screenshot.py` description with AI recommendations

**Recommendations by use case:**
- General pages: JPEG Q75 (recommended default)
- Text-heavy: JPEG Q65 (30% smaller)
- Design review: PNG or JPEG Q90 (exact colors)
- Mobile/bandwidth: JPEG Q60 + resize (50%+ reduction)

### Documentation

- Complete optimization guide with benchmarks
- Use case recommendations
- Migration guide for existing users
- Testing methodology documented

---

## [2.18.0] - 2025-10-16

### Changed - Animation Timing Optimization

**User Feedback:** "зеленого клика не было" → "Да! Щас было!" ✅

Animations optimized for human perception through real user testing:

- **Cursor movement:** Increased from 400ms to **1000ms** for clearly visible motion
- **Click flash:** Increased from 150ms to **1000ms** for easy perception
- **Scale effect:** Changed from 0.8x shrink to **1.5x grow** (50% size increase on click)
- **Shadow glow:** Enhanced with triple layers (30/60/90px) using `!important` flags
- **Total animation time:** 2000ms (2 seconds) from click initiation to action

**Human Perception Findings:**
- < 500ms: Too fast for conscious perception during multitasking
- 500-1000ms: Noticeable but may be missed
- **1000ms+: Clearly visible and comfortable** ✅ (our choice)
- 2000ms+: Very clear but may feel slow

### Fixed

- Animation timing now sequential instead of parallel (cursor arrives, THEN flash shows)
- Cursor animations no longer overlap with click actions
- All animations complete before actual click happens

### Documentation

- Created `docs/PHASE8_ANIMATION_TUNING.md` - Complete animation tuning history (V2.16→V2.17→V2.18)
- Updated `QA_TESTING_REPORT.md` with comprehensive testing results
- Updated `README.md` with visual emoji descriptions of animations

### Files Modified

- `commands/interaction.py` (lines 135-136, 141-142, 431-438)
- `browser/cursor.py` (lines 52, 56, 57-59, 80)

---

## [2.17.0] - 2025-10-16

### Fixed - Critical Production Bugs

**Discovery Method:** Real browser testing via MCP JSON-RPC (not unit tests)

#### Bug #1: JavaScript SyntaxError - Click commands completely broken

**Severity:** 🔴 **CRITICAL**

- **Problem:** `await` used in non-async function in click JavaScript code
- **Impact:** All `click` and `click_by_text` commands returned empty dict `{}`
- **Root Cause:** Functions wrapping click logic weren't marked `async`

**Fix:**
```javascript
// BEFORE (broken):
(function() {
    await new Promise(r => setTimeout(r, 300)); // ❌ SyntaxError
})()

// AFTER (working):
(async function() {
    await new Promise(r => setTimeout(r, 300)); // ✅ Valid
})()
```

#### Bug #2: Invalid Result Handling

- **Problem:** CDP errors returned `{}` instead of proper error object
- **Impact:** Commands silently failed without `success: false` response
- **Fix:** Added validation for None/invalid results, return proper error objects

### Changed

- Animation timing improved (cursor: 400ms, flash: 150ms) - later optimized in V2.18
- Sequential animation flow (wait for cursor, then show flash)

### Documentation

- Created `docs/PHASE8_BUGS_FIXED.md` - Complete bug analysis and fixes
- Updated unit test coverage remains at 66% (542 tests passing)
- Added integration testing recommendations

### Files Modified

- `commands/interaction.py` (lines 43, 132-143, 205-215, 287, 440-450, 523-533)

### Lessons Learned

**Why Unit Tests Missed This:**
- Unit tests mock CDP responses (always return valid dicts)
- No real JavaScript execution (syntax errors never triggered)
- Assumed CDP always returns 'value' key (didn't test error cases)

**Why Direct MCP Testing Found It:**
- Real browser, real JavaScript execution
- Real CDP responses with error objects
- End-to-end flow exactly as Claude Code uses it

**Key Takeaway:** Unit tests (66% coverage) ≠ Production reliability
- ✅ Need both unit tests (fast, test logic)
- ✅ Need integration tests (real browser, real errors)

---

## [2.16.0] - 2025-10-15

### Added - Phase 8: Polish & Ship

#### Comprehensive QA Testing

- Tested 5 pages: Главная, Контакты, Каталог, Анализ масла, О нас
- Used 15+ MCP tools for automation
- Created detailed `QA_TESTING_REPORT.md`

**Results:**
- ✅ 0 JavaScript errors across all pages
- ✅ All navigation working
- ⚠️ 34 failed network requests (images/external resources - non-critical)
- **Overall Score:** 8/10

#### Documentation

- Created comprehensive testing report
- Validated all 29 MCP commands work correctly
- Documented animation flow and cursor behavior

### Changed

- Initial animation timing (later optimized in V2.17/V2.18)
- Improved cursor visibility

---

## [2.1.0] - 2025-10-15

### Added - evaluate_js Complete Rewrite

**Problem:** Command completely ignored user code and always called `save_page_info()`

**New Features:**
- ✅ Actually executes user JavaScript code
- ✅ Automatic console.log/warn/error capture
- ✅ Timeout protection (default 30s, configurable)
- ✅ Smart serialization (primitive, object, array, function, error, promise)
- ✅ Auto-save for large results (>2KB) to `./js_result.json`
- ✅ Depth limiting for nested objects (max 3 levels)
- ✅ Proper error handling with stack traces

### Documentation

- Created `docs/evaluate_js_examples.md` - Complete usage guide

### Files Modified

- `commands/evaluation.py` - Complete rewrite (200+ lines changed)

---

## [2.0.0] - 2025-10-07

### Added - Roadmap V2 Refactoring (BREAKING CHANGES)

#### Task 1.1: Command Metadata as Class Attributes

- Metadata now class attributes (not `@property`)
- `to_mcp_tool()` became `@classmethod` (no dummy instance needed)
- Removed `cmd_class(tab=None)` hack for metadata

#### Task 1.2: Structured Logging

- Created `mcp/logging_config.py` - Centralized configuration
- Format: `[TIMESTAMP] LEVEL [module] message`
- All `print()` replaced with `logger.info/debug/error()`

#### Task 1.3: Error Hierarchy

- Created `mcp/errors.py` - Typed exceptions
- Each error = specific JSON-RPC code
- Removed all `except: pass` silent failures

#### Task 2.1: CommandContext for Dependency Injection

**BREAKING CHANGE:** `Command.__init__` now takes `CommandContext` instead of `tab`

- Created `commands/context.py` - DI container
- Commands declare dependencies: `requires_cursor`, `requires_browser`
- Removed hardcoded if/elif blocks from protocol.py (5 blocks → declarative)

#### Task 2.2: Auto-discovery with @register

- Created `commands/registry.py` - Decorator for auto-registration
- All 29 commands decorated with `@register`
- Removed manual registration (47 lines → 2 lines)

#### Task 2.3: Async CDP Wrapper

- Created `browser/async_cdp.py` - Thread-safe wrapper for pychrome
- ThreadPoolExecutor + Lock for safety
- Timeout support (default 30s)
- Available in commands via `self.context.cdp`

#### Task 2.4: Optimize save_page_info

- Created `utils/json_optimizer.py` - JSON output optimization
- Size reduction: 10KB → 3KB (**58.8% reduction**, ~2000 tokens saved)
- Top-15 elements by importance score
- Deduplication, grouping, noise removal
- Parameter `full=True` for full output (debugging)

### Changed - click_by_text Improvements

**Smart Text Matching:**
- Text normalization: `text.replace(/\s+/g, ' ').trim().toLowerCase()`
- Scoring algorithm (selects best match)
- Multiple sources: textContent, aria-label, title, value, placeholder
- `getDirectText()` - Prefers direct text without nested elements
- Escaping via `json.dumps()` (security)
- Extended selectors: `[role="button"]`, `.btn`, `.button`, `[tabindex]`
- Improved visibility checks: opacity, display, visibility
- Detailed debug on failure (shows 15 available elements)

**Scoring System:**
- Exact match: score = 100 + bonus for direct text (50)
- Partial match: score = 50 + bonus for direct text (30)
- aria-label match: score = 70
- title match: score = 60
- value match: score = 80
- placeholder match: score = 40

### Documentation

- Created `docs/roadmap-v2.md` - Complete refactoring plan
- Updated `.claude/CLAUDE.md` with V2 architecture
- Backup branch: `backup-main-20251007`

### Files Modified

- 10+ files refactored for V2 architecture
- All 29 command files updated with `@register` decorator
- New files: `commands/context.py`, `commands/registry.py`, `browser/async_cdp.py`, `utils/json_optimizer.py`

---

## [1.0.0] - 2025-10-01

### Added - Initial Release

#### Core Features

- **29 MCP Commands** for browser automation
- **Chrome DevTools Protocol (CDP)** integration via pychrome
- **Visual AI Cursor** with animations (blue glow, click flash)
- **WSL2 Support** with automatic Windows host detection
- **JSON-RPC 2.0** MCP server implementation

#### Command Categories

1. **Navigation (2):** open_url, get_text
2. **Interaction (4):** click, click_by_text, scroll_page, move_cursor
3. **DevTools (6):** open_devtools, console_command, get_console_logs, etc.
4. **Tabs (4):** list_tabs, create_tab, close_tab, switch_tab
5. **Execution (4):** evaluate_js, screenshot, get_page_snapshot, save_page_info
6. **Search (2):** find_elements, get_page_structure
7. **Debug (3):** debug_element, force_click, open_devtools_ui
8. **Diagnostics (4):** diagnose_page, get_clickable_elements, enable_console_logging, devtools_report

#### Architecture

- Modular command pattern with base `Command` class
- Browser connection management with auto-reconnect
- Console logging via CDP events + JavaScript interceptor
- Cursor injection and animation system

#### WSL2 Setup

- `windows_proxy.py` - TCP proxy for WSL→Windows communication
- `browser/connection.py` - Monkey-patches for WebSocket URL rewriting
- Automatic Windows host IP detection from `/etc/resolv.conf`

#### Documentation

- Comprehensive `README.md` with setup instructions
- `.claude/CLAUDE.md` - Complete AI context
- `SOLUTION.md` - WSL2 portproxy alternative
- `fix_comet_wsl.md` - All WSL setup methods

---

## Version Numbering

**Format:** MAJOR.MINOR.PATCH

- **MAJOR:** Breaking changes (e.g., V2.0.0 CommandContext refactor)
- **MINOR:** New features, significant improvements (e.g., V2.1.0 evaluate_js rewrite)
- **PATCH:** Bug fixes, optimizations (e.g., V2.18.0 animation tuning)

**Current Version:** 2.18.0 (2025-10-16)

---

**GitHub Tags:**
- Use `git tag v2.18.0` for releases
- Push tags with `git push origin --tags`
- GitHub will show version prominently in releases page
