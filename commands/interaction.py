"""Interactive browser commands: click, scroll, cursor movement"""
import asyncio
from typing import Dict, Any, Optional
from .base import Command
from .registry import register
from mcp.logging_config import get_logger
from mcp.errors import InvalidArgumentError, CommandError
from utils.validators import Validators

logger = get_logger("commands.interaction")


@register
class ClickCommand(Command):
    """Click on an element with multiple search strategies"""

    name = "click"
    description = """Click on an element. Supports multiple strategies including smart UI patterns.

Strategies:
- CSS selectors: 'button.submit'
- XPath: '//button[@type="submit"]'
- Text search: contains text
- SMART PATTERNS:
  - 'close' or '[close]' - Finds close buttons (SVG icons, top-right position, no text)
  - Scores candidates by: class names, position, size, SVG presence

Auto-scrolls to element and shows cursor animation."""
    input_schema = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector, XPath, text, or smart pattern like 'close'"}
        },
        "required": ["selector"]
    }

    requires_cursor = True
    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, selector: str, show_cursor: bool = True, **kwargs) -> Dict[str, Any]:
        """Execute click with multiple strategies and cursor animation"""
        try:
            # Validate selector
            selector = Validators.validate_selector(selector, "selector", allow_xpath=True)

            # Always initialize and show cursor
            cursor = self.context.cursor
            if cursor:
                await cursor.initialize()

            logger.debug(f"click: targeting selector '{selector}' (show_cursor={show_cursor})")

            js_code = f"""
            (async function() {{
                // Try multiple strategies to find the element
                let el = null;
                let strategy = '';

                // SMART PATTERN: Close button detection
                if ('{selector}'.toLowerCase().includes('close') ||
                    '{selector}' === '[close]' ||
                    '{selector}' === 'close-button') {{

                    // Find typical close buttons (SVG icons, top-right position)
                    const candidates = Array.from(document.querySelectorAll(
                        'button, [role="button"], [aria-label*="close" i], [aria-label*="dismiss" i], ' +
                        '.close, .dismiss, .modal-close, [class*="close"], [class*="dismiss"]'
                    ));

                    // Score each candidate
                    let bestScore = 0;
                    let bestCandidate = null;

                    for (const btn of candidates) {{
                        let score = 0;
                        const rect = btn.getBoundingClientRect();
                        const parent = btn.closest('dialog, [role="dialog"], .modal, .popup, [class*="modal"], [class*="dialog"]');

                        // Check if visible
                        if (rect.width === 0 || rect.height === 0) continue;

                        // +50: Has close-related class
                        if (btn.classList.contains('close') ||
                            btn.classList.contains('dismiss') ||
                            Array.from(btn.classList).some(c => c.includes('close') || c.includes('dismiss'))) {{
                            score += 50;
                        }}

                        // +30: Contains SVG (typical for icon-only buttons)
                        if (btn.querySelector('svg')) {{
                            score += 30;
                        }}

                        // +40: In top-right corner of parent
                        if (parent) {{
                            const parentRect = parent.getBoundingClientRect();
                            const isTopRight = rect.right > (parentRect.right - 100) &&
                                              rect.top < (parentRect.top + 100);
                            if (isTopRight) score += 40;
                        }}

                        // +20: Small size (typical for close icons)
                        if (rect.width < 50 && rect.height < 50) {{
                            score += 20;
                        }}

                        // +30: Has aria-label with close/dismiss
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        if (ariaLabel.toLowerCase().includes('close') ||
                            ariaLabel.toLowerCase().includes('dismiss')) {{
                            score += 30;
                        }}

                        if (score > bestScore) {{
                            bestScore = score;
                            bestCandidate = btn;
                        }}
                    }}

                    if (bestCandidate) {{
                        el = bestCandidate;
                        strategy = 'smart-close-button (score: ' + bestScore + ')';
                    }}
                }}

                // Strategy 1: Direct CSS selector
                if (!el) {{
                    el = document.querySelector('{selector}');
                    if (el) strategy = 'css';
                }}

                // Strategy 2: XPath
                if (!el && '{selector}'.startsWith('//')) {{
                    try {{
                        const result = document.evaluate('{selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        el = result.singleNodeValue;
                        if (el) strategy = 'xpath';
                    }} catch(e) {{}}
                }}

                // Strategy 3: Text content search
                if (!el && ('{selector}'.includes('text') || '{selector}'.includes('содержит'))) {{
                    const textMatch = '{selector}'.match(/["']([^"']+)["']/);
                    if (textMatch) {{
                        const searchText = textMatch[1];
                        el = Array.from(document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick]'))
                            .find(e => e.textContent.trim() === searchText || e.textContent.includes(searchText));
                        if (el) strategy = 'text-exact';
                    }}
                }}

                // Strategy 4: Common clickable patterns
                if (!el) {{
                    const allClickable = document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick], input[type="button"], input[type="submit"]');
                    el = Array.from(allClickable).find(e =>
                        e.textContent.includes('{selector}') ||
                        e.getAttribute('aria-label')?.includes('{selector}') ||
                        e.title?.includes('{selector}')
                    );
                    if (el) strategy = 'text-contains';
                }}

                if (!el) {{
                    const allMatches = document.querySelectorAll('{selector}');
                    return {{
                        success: false,
                        reason: 'not_found',
                        message: 'Element not found: {selector}',
                        matchCount: allMatches.length,
                        suggestion: allMatches.length > 0 ? 'Selector matches ' + allMatches.length + ' elements' : 'Try using text content or XPath'
                    }};
                }}

                // Check visibility
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                 style.display !== 'none' &&
                                 style.visibility !== 'hidden' &&
                                 style.opacity !== '0';

                if (!isVisible) {{
                    return {{
                        success: false,
                        reason: 'not_visible',
                        message: 'Element found but not visible',
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        dimensions: {{ width: rect.width, height: rect.height }}
                    }};
                }}

                // Check viewport
                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                // Scroll into view if needed
                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    await new Promise(r => setTimeout(r, 300));
                    const newRect = el.getBoundingClientRect();
                    rect.top = newRect.top;
                    rect.left = newRect.left;
                }}

                // Calculate click position
                const clickX = rect.left + rect.width / 2;
                const clickY = rect.top + rect.height / 2;

                // Animate cursor and wait for completion
                const showCursor = {str(show_cursor).lower()};
                if (showCursor && window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 1000);
                    await new Promise(r => setTimeout(r, 1000)); // Wait for cursor animation
                }}

                // Show click animation and wait
                if (showCursor && window.__clickAICursor__) {{
                    window.__clickAICursor__();
                    await new Promise(r => setTimeout(r, 1000)); // Wait for click flash
                }}

                // Multiple click methods
                el.click();

                ['mousedown', 'mouseup', 'click'].forEach(eventType => {{
                    const event = new MouseEvent(eventType, {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: clickX,
                        clientY: clickY
                    }});
                    el.dispatchEvent(event);
                }});

                if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'A') {{
                    try {{
                        el.focus();
                        if (el.onclick) el.onclick.call(el);
                    }} catch (e3) {{}}
                }}

                return {{
                    success: true,
                    selector: '{selector}',
                    strategy: strategy,
                    message: 'Clicked element using strategy: ' + strategy,
                    cursorAnimated: showCursor,
                    cursorVisible: window.__aiCursor__ && window.__aiCursor__.style.display !== 'none',
                    elementInfo: {{
                        tagName: el.tagName,
                        id: el.id,
                        className: el.className,
                        text: el.textContent.trim().substring(0, 100),
                        position: {{
                            top: rect.top,
                            left: rect.left,
                            width: rect.width,
                            height: rect.height,
                            clickX: clickX,
                            clickY: clickY
                        }},
                        inViewport: inViewport
                    }}
                }};
            }})()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True, awaitPromise=True)
            click_result = result.get('result', {}).get('value')

            # Handle None or missing value
            if not click_result or not isinstance(click_result, dict):
                logger.error(f"✗ Invalid click result: {result}")
                return {
                    "success": False,
                    "reason": "invalid_result",
                    "message": f"Click returned invalid result for selector: {selector}",
                    "raw_result": str(result)
                }

            # Log result for debugging
            if click_result.get('success'):
                element_info = click_result.get('elementInfo', {})
                logger.info(f"✓ Successfully clicked: '{selector}' (element: {element_info.get('tagName', 'unknown')}, strategy: {click_result.get('strategy', 'unknown')})")
                await asyncio.sleep(0.3)
            else:
                logger.warning(f"✗ Failed to click: '{selector}' - {click_result.get('message', 'unknown error')}")

            return click_result
        except Exception as e:
            error_result = {
                "success": False,
                "reason": "exception",
                "message": f"Failed to click element: {str(e)}",
                "error": str(e)
            }
            logger.error(f"✗ Exception during click: '{selector}' - {str(e)}")
            return error_result


@register
class ClickByTextCommand(Command):
    """Click element by visible text content"""

    name = "click_by_text"
    description = """Click element by text. Auto-finds coordinates, moves cursor, clicks. Returns success/failure.

Best for: buttons, links, tabs. Auto-scrolls into view if needed.
Tip: Use save_page_info() first to see available elements and verify click worked."""
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to search for"},
            "tag": {"type": "string", "description": "Optional: limit search to specific tag"},
            "exact": {"type": "boolean", "description": "If true, match exact text", "default": False}
        },
        "required": ["text"]
    }

    requires_cursor = True
    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, text: str, tag: Optional[str] = None, exact: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute click by text with cursor animation"""
        try:
            # Validate text
            text = Validators.validate_string_length(text, "text", min_length=1, max_length=500)

            # Always initialize and show cursor
            cursor = self.context.cursor
            if cursor:
                await cursor.initialize()

            logger.debug(f"click_by_text: searching for '{text}' (exact={exact}, tag={tag})")

            # Escape special characters for JavaScript
            import json
            text_escaped = json.dumps(text)

            if tag:
                tags_js = json.dumps([tag])
            else:
                # Start with semantic clickable elements
                tags_js = json.dumps([
                    'button', 'a', 'input[type="button"]', 'input[type="submit"]',
                    '[role="button"]', '[role="tab"]', '[role="link"]', '[role="menuitem"]',
                    '[onclick]', '.btn', '.button', '[tabindex]'
                ])

            js_code = f"""
            (async function() {{
                let elements = [];

                // 1. Get semantic clickable elements
                const semanticTags = {tags_js};
                const semanticSelector = semanticTags.join(', ');
                const semanticElements = Array.from(document.querySelectorAll(semanticSelector));
                elements.push(...semanticElements);

                // 2. CRITICAL FIX: Find visually clickable elements (cursor: pointer)
                // Check common container elements that might be clickable cards/divs
                const potentialClickable = Array.from(document.querySelectorAll('div, span, li, section, article, header'));
                for (const el of potentialClickable) {{
                    const style = window.getComputedStyle(el);
                    // Include if cursor is pointer OR has click handler
                    if (style.cursor === 'pointer' ||
                        el.onclick !== null ||
                        el.hasAttribute('onclick')) {{
                        elements.push(el);
                    }}
                }}

                // Remove duplicates
                elements = [...new Set(elements)];
                const searchText = {text_escaped};
                const exactMatch = {str(exact).lower()};

                // Normalize text function - removes extra whitespace and normalizes
                function normalizeText(text) {{
                    return text.replace(/\\s+/g, ' ').trim().toLowerCase();
                }}

                // Check if element is truly visible and clickable
                function isElementVisible(el) {{
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);

                    return rect.width > 0 &&
                           rect.height > 0 &&
                           style.display !== 'none' &&
                           style.visibility !== 'hidden' &&
                           style.opacity !== '0' &&
                           el.offsetParent !== null;
                }}

                // Get direct text content (without nested elements)
                function getDirectText(el) {{
                    let text = '';
                    for (let node of el.childNodes) {{
                        if (node.nodeType === Node.TEXT_NODE) {{
                            text += node.textContent;
                        }}
                    }}
                    return text.trim();
                }}

                // Find best matching element
                const searchNorm = normalizeText(searchText);
                let bestMatch = null;
                let bestScore = 0;

                for (const el of elements) {{
                    if (!isElementVisible(el)) continue;

                    // Get various text representations
                    const fullText = normalizeText(el.textContent || '');
                    const directText = normalizeText(getDirectText(el));
                    const ariaLabel = normalizeText(el.getAttribute('aria-label') || '');
                    const title = normalizeText(el.title || '');
                    const value = normalizeText(el.value || '');
                    const placeholder = normalizeText(el.placeholder || '');

                    let score = 0;
                    let matched = false;

                    if (exactMatch) {{
                        // Exact match mode
                        if (fullText === searchNorm || directText === searchNorm ||
                            ariaLabel === searchNorm || title === searchNorm ||
                            value === searchNorm || placeholder === searchNorm) {{
                            matched = true;
                            score = 100;
                            // Prefer elements with less nested content
                            if (directText === searchNorm) score += 50;
                        }}
                    }} else {{
                        // Partial match mode
                        if (fullText.includes(searchNorm)) {{
                            matched = true;
                            score = 50;
                            // Prefer direct text match
                            if (directText.includes(searchNorm)) score += 30;
                            // Prefer shorter text (more specific)
                            if (fullText.length < 100) score += 10;
                        }}
                        if (ariaLabel.includes(searchNorm)) {{
                            matched = true;
                            score = Math.max(score, 70);
                        }}
                        if (title.includes(searchNorm)) {{
                            matched = true;
                            score = Math.max(score, 60);
                        }}
                        if (value.includes(searchNorm)) {{
                            matched = true;
                            score = Math.max(score, 80);
                        }}
                        if (placeholder.includes(searchNorm)) {{
                            matched = true;
                            score = Math.max(score, 40);
                        }}
                    }}

                    if (matched && score > bestScore) {{
                        bestScore = score;
                        bestMatch = el;
                    }}
                }}

                const el = bestMatch;

                if (!el) {{
                    // Better debug information
                    const visibleElements = elements.filter(isElementVisible);
                    const partialMatches = visibleElements.filter(e => {{
                        const text = normalizeText(e.textContent || '');
                        return text.includes(searchNorm) || searchNorm.includes(text);
                    }});

                    return {{
                        success: false,
                        message: `Element with text not found: "${{searchText}}"`,
                        searchedTags: tags,
                        totalElements: elements.length,
                        visibleElements: visibleElements.length,
                        partialMatches: partialMatches.length,
                        availableTexts: visibleElements.slice(0, 15).map(e => ({{
                            tag: e.tagName,
                            text: e.textContent.trim().substring(0, 60),
                            ariaLabel: e.getAttribute('aria-label'),
                            role: e.getAttribute('role')
                        }}))
                    }};
                }}

                // Scroll into view if needed
                const rect = el.getBoundingClientRect();
                let clickX = Math.round(rect.left + rect.width / 2);
                let clickY = Math.round(rect.top + rect.height / 2);

                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    await new Promise(r => setTimeout(r, 300));
                    // Recalculate after scroll
                    const newRect = el.getBoundingClientRect();
                    clickX = Math.round(newRect.left + newRect.width / 2);
                    clickY = Math.round(newRect.top + newRect.height / 2);
                }}

                // Debug logging
                console.log('[MCP] Click target:', {{
                    searchText: searchText,
                    foundText: el.textContent.trim().substring(0, 100),
                    tag: el.tagName,
                    score: bestScore,
                    coords: {{ x: clickX, y: clickY }},
                    rect: {{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
                }});

                // Animate cursor and wait for completion
                if (window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 1000);
                    await new Promise(r => setTimeout(r, 1000)); // Wait for cursor animation
                }}

                // Show click animation and wait
                if (window.__clickAICursor__) {{
                    window.__clickAICursor__();
                    await new Promise(r => setTimeout(r, 1000)); // Wait for click flash
                }}

                // Now perform the actual click
                let clicked = false;

                // Method 1: Direct click
                try {{
                    el.click();
                    clicked = true;
                }} catch (e1) {{
                    console.warn('[MCP] Direct click failed:', e1);
                }}

                // Method 2: Dispatch mouse events
                try {{
                    ['mousedown', 'mouseup', 'click'].forEach(eventType => {{
                        const event = new MouseEvent(eventType, {{
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: clickX,
                            clientY: clickY
                        }});
                        el.dispatchEvent(event);
                    }});
                    clicked = true;
                }} catch (e2) {{
                    console.warn('[MCP] Mouse events failed:', e2);
                }}

                // Method 3: Focus and trigger onclick
                if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'INPUT') {{
                    try {{
                        el.focus();
                        if (el.onclick) {{
                            el.onclick.call(el);
                            clicked = true;
                        }}
                    }} catch (e3) {{
                        console.warn('[MCP] Focus/onclick failed:', e3);
                    }}
                }}

                return {{
                    success: clicked,
                    searchText: searchText,
                    matchScore: bestScore,
                    message: clicked ? `Clicked element with text: "${{searchText}}"` : 'All click methods failed',
                    cursorVisible: window.__aiCursor__ && window.__aiCursor__.style.display !== 'none',
                    element: {{
                        tag: el.tagName,
                        id: el.id,
                        className: el.className,
                        actualText: el.textContent.trim().substring(0, 100),
                        ariaLabel: el.getAttribute('aria-label'),
                        role: el.getAttribute('role'),
                        position: {{ x: clickX, y: clickY }}
                    }}
                }};
            }})()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True, awaitPromise=True)

            # Debug logging
            logger.debug(f"click_by_text CDP result: {result}")

            click_result = result.get('result', {}).get('value')

            # Handle None or missing value
            if not click_result or not isinstance(click_result, dict):
                logger.error(f"✗ Invalid click_by_text result for '{text}'")
                logger.error(f"   Raw CDP result: {result}")
                logger.error(f"   Extracted value: {click_result}")
                logger.error(f"   Value type: {type(click_result)}")

                # Check for exception in CDP result
                if 'exceptionDetails' in result:
                    exception = result['exceptionDetails']
                    return {
                        "success": False,
                        "reason": "javascript_error",
                        "message": f"JavaScript error while clicking '{text}': {exception.get('text', 'Unknown error')}",
                        "exception": str(exception)
                    }

                return {
                    "success": False,
                    "reason": "invalid_result",
                    "message": f"Click by text returned invalid result for: {text}",
                    "raw_result": str(result),
                    "debug_info": f"result.keys={list(result.keys())}, value={click_result}, type={type(click_result).__name__}"
                }

            # Log result to stderr for debugging
            if click_result.get('success'):
                logger.info(f"✓ Successfully clicked: '{text}' (element: {click_result.get('element', {}).get('tag', 'unknown')}, score: {click_result.get('matchScore', 0)})")
            else:
                logger.warning(f"✗ Failed to click: '{text}' - {click_result.get('message', 'unknown error')}")

            return click_result
        except Exception as e:
            error_result = {
                "success": False,
                "message": f"Failed to click by text: {str(e)}",
                "error": str(e)
            }
            logger.error(f"✗ Exception during click: '{text}' - {str(e)}")
            return error_result


@register
class ScrollPageCommand(Command):
    """Scroll page or element"""

    name = "scroll_page"
    description = "Scroll the page or a specific element. Returns detailed position information."
    input_schema = {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "description": "Scroll direction: 'up', 'down', 'left', 'right', 'top', 'bottom'", "default": "down"},
            "amount": {"type": "integer", "description": "Pixels to scroll (default: 500 for page, 300 for element)"},
            "x": {"type": "integer", "description": "Absolute X coordinate to scroll to"},
            "y": {"type": "integer", "description": "Absolute Y coordinate to scroll to"},
            "selector": {"type": "string", "description": "CSS selector of element to scroll"}
        }
    }

    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, direction: str = "down", amount: Optional[int] = None,
                     x: Optional[int] = None, y: Optional[int] = None,
                     selector: Optional[str] = None) -> Dict[str, Any]:
        """Execute scroll operation"""
        try:
            # Validate coordinates if provided
            if x is not None or y is not None:
                x, y = Validators.validate_coordinates(x, y, allow_negative=False)

            # Validate selector if provided
            if selector:
                selector = Validators.validate_selector(selector, "selector")

            # Validate amount if provided
            if amount is not None:
                amount = int(Validators.validate_range(amount, "amount", min_value=0, max_value=50000))

            # Build JavaScript based on parameters
            if x is not None and y is not None:
                js_code = f"""
                (function() {{
                    window.scrollTo({x}, {y});
                    return {{
                        x: window.pageXOffset || window.scrollX,
                        y: window.pageYOffset || window.scrollY,
                        maxX: document.documentElement.scrollWidth - window.innerWidth,
                        maxY: document.documentElement.scrollHeight - window.innerHeight,
                        viewportHeight: window.innerHeight,
                        viewportWidth: window.innerWidth,
                        pageHeight: document.documentElement.scrollHeight,
                        pageWidth: document.documentElement.scrollWidth
                    }};
                }})()
                """
            elif selector:
                if amount is None:
                    amount = 300
                scroll_delta = amount if direction in ["down", "right"] else -amount
                scroll_property = "scrollTop" if direction in ["down", "up"] else "scrollLeft"

                js_code = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) return {{success: false, message: 'Element not found: {selector}'}};

                    el.{scroll_property} += {scroll_delta};

                    return {{
                        success: true,
                        element: '{selector}',
                        scrollTop: el.scrollTop,
                        scrollLeft: el.scrollLeft,
                        scrollHeight: el.scrollHeight,
                        scrollWidth: el.scrollWidth,
                        clientHeight: el.clientHeight,
                        clientWidth: el.clientWidth
                    }};
                }})()
                """
            else:
                if amount is None:
                    amount = 500

                scroll_map = {
                    "down": f"window.scrollBy(0, {amount})",
                    "up": f"window.scrollBy(0, -{amount})",
                    "left": f"window.scrollBy(-{amount}, 0)",
                    "right": f"window.scrollBy({amount}, 0)",
                    "top": "window.scrollTo(0, 0)",
                    "bottom": "window.scrollTo(0, document.documentElement.scrollHeight)"
                }

                scroll_expr = scroll_map.get(direction)
                if not scroll_expr:
                    return {"success": False, "message": f"Invalid direction: {direction}"}

                js_code = f"""
                (function() {{
                    {scroll_expr};
                    return {{
                        x: window.pageXOffset || window.scrollX,
                        y: window.pageYOffset || window.scrollY,
                        maxX: document.documentElement.scrollWidth - window.innerWidth,
                        maxY: document.documentElement.scrollHeight - window.innerHeight,
                        viewportHeight: window.innerHeight,
                        viewportWidth: window.innerWidth,
                        pageHeight: document.documentElement.scrollHeight,
                        pageWidth: document.documentElement.scrollWidth,
                        scrolledToBottom: (window.innerHeight + window.pageYOffset) >= document.documentElement.scrollHeight - 10,
                        scrolledToTop: window.pageYOffset <= 10
                    }};
                }})()
                """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            scroll_info = result.get('result', {}).get('value', {})

            if selector and not scroll_info.get('success', True):
                return scroll_info

            return {
                "success": True,
                "direction": direction if not (x is not None and y is not None) else "absolute",
                "amount": amount,
                "selector": selector,
                "position": scroll_info,
                "message": f"Scrolled {'element ' + selector if selector else 'page'} {direction if not (x is not None and y is not None) else f'to ({x}, {y})'}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to scroll page: {str(e)}")


@register
class MoveCursorCommand(Command):
    """Move AI cursor to position"""

    name = "move_cursor"
    description = "Move the visual AI cursor to specific coordinates or element center."
    input_schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "selector": {"type": "string", "description": "CSS selector to move cursor to (element center)"},
            "duration": {"type": "integer", "description": "Animation duration in ms", "default": 400}
        }
    }

    requires_cursor = True
    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None,
                     selector: Optional[str] = None, duration: int = 400, **kwargs) -> Dict[str, Any]:
        """Execute cursor movement"""
        try:
            # Validate coordinates if provided
            if x is not None or y is not None:
                x, y = Validators.validate_coordinates(x, y, allow_negative=False)

            # Validate selector if provided
            if selector:
                selector = Validators.validate_selector(selector, "selector")

            # Validate duration
            duration = int(Validators.validate_range(duration, "duration", min_value=0, max_value=10000))

            if selector:
                js_code = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) {{
                        return {{success: false, message: 'Element not found: {selector}'}};
                    }}

                    const rect = el.getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;

                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__(centerX, centerY, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to element: {selector}',
                            position: {{x: centerX, y: centerY}},
                            element: {{
                                tagName: el.tagName,
                                id: el.id,
                                className: el.className,
                                bounds: {{
                                    top: rect.top,
                                    left: rect.left,
                                    width: rect.width,
                                    height: rect.height
                                }}
                            }}
                        }};
                    }} else {{
                        return {{success: false, message: 'AI cursor not initialized'}};
                    }}
                }})()
                """
            elif x is not None and y is not None:
                js_code = f"""
                (function() {{
                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__({x}, {y}, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to coordinates',
                            position: {{x: {x}, y: {y}}}
                        }};
                    }} else {{
                        return {{success: false, message: 'AI cursor not initialized'}};
                    }}
                }})()
                """
            else:
                return {"success": False, "message": "Either provide x,y coordinates or selector"}

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {"success": False, "message": f"Failed to move cursor: {str(e)}", "error": str(e)}
