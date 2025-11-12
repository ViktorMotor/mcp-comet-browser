"""Unified element validation logic for clickable element detection

This module provides centralized JavaScript templates for finding and validating
interactive elements across the codebase. It ensures consistency between commands
and properly handles React/Vue event delegation patterns.

Version: 3.0.1 - Fixed React event delegation support
"""
from typing import List, Dict, Any


class ElementValidator:
    """Generates JavaScript code for finding and validating clickable elements"""

    # Interactive cursor types that indicate clickability
    INTERACTIVE_CURSORS = [
        'pointer',      # Standard clickable
        'grab',         # Draggable (idle)
        'grabbing',     # Draggable (active)
        'move',         # Movable/draggable
        'zoom-in',      # Zoomable (enlarge)
        'zoom-out',     # Zoomable (shrink)
        'all-scroll',   # Scrollable in any direction
    ]

    # Semantic selectors for inherently clickable elements
    SEMANTIC_SELECTORS = [
        'button',
        'a',
        'input[type="button"]',
        'input[type="submit"]',
        '[role="button"]',
        '[role="tab"]',
        '[role="link"]',
        '[role="menuitem"]',
        '[onclick]',    # Elements with inline onclick attribute
        '.btn',
        '.button',
        '[tabindex]',
    ]

    # Generic elements that might be clickable via CSS/events
    POTENTIAL_CLICKABLE_TAGS = [
        'div',
        'span',
        'li',
        'section',
        'article',
        'header',
    ]

    @staticmethod
    def get_interactive_cursor_check_js(cursor_types: List[str] = None) -> str:
        """
        Generate JavaScript condition to check if cursor style is interactive

        Args:
            cursor_types: List of cursor types to check (default: INTERACTIVE_CURSORS)

        Returns:
            JavaScript condition string like:
            "style.cursor === 'pointer' || style.cursor === 'grab' || ..."
        """
        if cursor_types is None:
            cursor_types = ElementValidator.INTERACTIVE_CURSORS

        conditions = [f"style.cursor === '{cursor}'" for cursor in cursor_types]
        return " || ".join(conditions)

    @staticmethod
    def get_visibility_check_js(
        check_dimensions: bool = True,
        check_display: bool = True,
        check_visibility: bool = True,
        check_opacity: bool = True,
        check_offset_parent: bool = True
    ) -> str:
        """
        Generate JavaScript code for comprehensive visibility check

        Args:
            check_dimensions: Check rect.width > 0 && rect.height > 0
            check_display: Check style.display !== 'none'
            check_visibility: Check style.visibility !== 'hidden'
            check_opacity: Check parseFloat(style.opacity) > 0
            check_offset_parent: Check el.offsetParent !== null

        Returns:
            JavaScript boolean expression for visibility check
        """
        checks = []

        if check_dimensions:
            checks.append("rect.width > 0 && rect.height > 0")

        if check_display:
            checks.append("style.display !== 'none'")

        if check_visibility:
            checks.append("style.visibility !== 'hidden'")

        if check_opacity:
            # Use parseFloat for proper numeric comparison (handles "0", "0.5", etc.)
            checks.append("parseFloat(style.opacity) > 0")

        if check_offset_parent:
            checks.append("el.offsetParent !== null")

        return " && ".join(checks)

    @staticmethod
    def get_clickable_elements_js(
        cursor_types: List[str] = None,
        include_semantic: bool = True,
        include_visual_clickable: bool = True,
        check_visibility: bool = True,
        viewport_only: bool = False
    ) -> str:
        """
        Generate complete JavaScript code to find all clickable elements

        This is the main unified function used across all commands.

        Args:
            cursor_types: List of interactive cursor types to check
            include_semantic: Include semantic clickable elements (buttons, links, etc.)
            include_visual_clickable: Include elements with interactive cursor styles
            check_visibility: Filter out non-visible elements
            viewport_only: Only return elements in viewport

        Returns:
            JavaScript IIFE that returns array of clickable elements with metadata
        """
        if cursor_types is None:
            cursor_types = ElementValidator.INTERACTIVE_CURSORS

        semantic_selector = ", ".join(ElementValidator.SEMANTIC_SELECTORS)
        potential_tags = ", ".join(ElementValidator.POTENTIAL_CLICKABLE_TAGS)
        cursor_check = ElementValidator.get_interactive_cursor_check_js(cursor_types)
        visibility_check = ElementValidator.get_visibility_check_js()

        # Generate JavaScript code
        js_code = f"""
(function() {{
    let interactiveElements = [];

    // 1. Semantic clickable elements (buttons, links, etc.)
    {'if (true) {' if include_semantic else 'if (false) {'}
        const semanticSelector = '{semantic_selector}';
        const semanticElements = Array.from(document.querySelectorAll(semanticSelector));
        interactiveElements.push(...semanticElements);
    }}

    // 2. Visually clickable elements (cursor-based detection)
    // CRITICAL FIX (v3.0.1): Use getComputedStyle instead of inline style check
    // This properly detects React/Vue elements with CSS-based cursor styles
    {'if (true) {' if include_visual_clickable else 'if (false) {'}
        const potentialClickable = Array.from(document.querySelectorAll('{potential_tags}'));

        for (const el of potentialClickable) {{
            const style = window.getComputedStyle(el);

            // Check for interactive cursor types OR onclick property
            // NOTE: el.onclick checks JavaScript property (React/Vue), not HTML attribute
            if (({cursor_check}) || el.onclick !== null) {{
                interactiveElements.push(el);
            }}
        }}
    }}

    // Remove duplicates
    const uniqueElements = [...new Set(interactiveElements)];

    // 3. Filter by visibility if requested
    {'if (true) {' if check_visibility else 'if (false) {'}
        return uniqueElements.filter(el => {{
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);

            const isVisible = {visibility_check};

            {'if (true) {' if viewport_only else 'if (false) {'}
                // Also check if element is in viewport
                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;
                return isVisible && inViewport;
            }}

            return isVisible;
        }});
    }}

    return uniqueElements;
}})()
"""
        return js_code.strip()

    @staticmethod
    def get_element_info_js(element_var: str = "el") -> str:
        """
        Generate JavaScript code to extract element information

        Args:
            element_var: JavaScript variable name for the element

        Returns:
            JavaScript object creation code with element metadata
        """
        return f"""{{
    tag: {element_var}.tagName.toLowerCase(),
    text: ({element_var}.innerText || {element_var}.textContent || '').trim().substring(0, 100),
    id: {element_var}.id || null,
    classes: Array.from({element_var}.classList || []),
    role: {element_var}.getAttribute('role'),
    ariaLabel: {element_var}.getAttribute('aria-label'),
    position: (() => {{
        const rect = {element_var}.getBoundingClientRect();
        return {{
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
        }};
    }})(),
    cursor: window.getComputedStyle({element_var}).cursor,
    onclick: {element_var}.onclick !== null,
    visible: (() => {{
        const rect = {element_var}.getBoundingClientRect();
        const style = window.getComputedStyle({element_var});
        return {ElementValidator.get_visibility_check_js()};
    }})()
}}"""

    @classmethod
    def get_supported_cursor_types(cls) -> List[str]:
        """Return list of supported interactive cursor types"""
        return cls.INTERACTIVE_CURSORS.copy()

    @classmethod
    def is_interactive_cursor(cls, cursor: str) -> bool:
        """Check if cursor type is considered interactive"""
        return cursor in cls.INTERACTIVE_CURSORS


# Export main functions
__all__ = ['ElementValidator']
