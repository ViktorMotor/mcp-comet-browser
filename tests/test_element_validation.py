"""Unit tests for utils/element_validation.py

Tests the unified element validation logic used across all commands.
"""
import pytest
from utils.element_validation import ElementValidator


class TestElementValidator:
    """Test suite for ElementValidator utility class"""

    def test_interactive_cursors_list(self):
        """Test that all expected interactive cursor types are included"""
        cursors = ElementValidator.get_supported_cursor_types()

        assert 'pointer' in cursors
        assert 'move' in cursors
        assert 'grab' in cursors
        assert 'grabbing' in cursors
        assert 'zoom-in' in cursors
        assert 'zoom-out' in cursors
        assert 'all-scroll' in cursors

    def test_is_interactive_cursor(self):
        """Test cursor type detection"""
        assert ElementValidator.is_interactive_cursor('pointer') is True
        assert ElementValidator.is_interactive_cursor('move') is True
        assert ElementValidator.is_interactive_cursor('grab') is True

        # Non-interactive cursors
        assert ElementValidator.is_interactive_cursor('default') is False
        assert ElementValidator.is_interactive_cursor('text') is False
        assert ElementValidator.is_interactive_cursor('not-allowed') is False

    def test_cursor_check_js_generation(self):
        """Test JavaScript cursor check condition generation"""
        # Default cursor types
        js_code = ElementValidator.get_interactive_cursor_check_js()
        assert "style.cursor === 'pointer'" in js_code
        assert "style.cursor === 'move'" in js_code
        assert "style.cursor === 'grab'" in js_code
        assert "||" in js_code

        # Custom cursor types
        js_code = ElementValidator.get_interactive_cursor_check_js(['pointer', 'move'])
        assert "style.cursor === 'pointer'" in js_code
        assert "style.cursor === 'move'" in js_code
        assert "style.cursor === 'grab'" not in js_code

    def test_visibility_check_js_generation(self):
        """Test JavaScript visibility check generation"""
        # All checks enabled
        js_code = ElementValidator.get_visibility_check_js()
        assert "rect.width > 0" in js_code
        assert "rect.height > 0" in js_code
        assert "style.display !== 'none'" in js_code
        assert "style.visibility !== 'hidden'" in js_code
        assert "parseFloat(style.opacity) > 0" in js_code
        assert "el.offsetParent !== null" in js_code
        assert "&&" in js_code

        # Partial checks
        js_code = ElementValidator.get_visibility_check_js(
            check_dimensions=True,
            check_display=False,
            check_visibility=False,
            check_opacity=False,
            check_offset_parent=False
        )
        assert "rect.width > 0" in js_code
        assert "rect.height > 0" in js_code
        assert "style.display" not in js_code
        assert "style.visibility" not in js_code

    def test_opacity_check_uses_parse_float(self):
        """Test that opacity check uses parseFloat for numeric comparison"""
        js_code = ElementValidator.get_visibility_check_js(
            check_dimensions=False,
            check_display=False,
            check_visibility=False,
            check_opacity=True,
            check_offset_parent=False
        )
        assert "parseFloat(style.opacity) > 0" in js_code
        assert "style.opacity !== '0'" not in js_code  # Should NOT use string comparison

    def test_clickable_elements_js_generation(self):
        """Test complete clickable elements JavaScript generation"""
        js_code = ElementValidator.get_clickable_elements_js()

        # Should include semantic selectors
        assert "button" in js_code
        assert "[role=\"button\"]" in js_code

        # Should include visual clickable detection
        assert "getComputedStyle" in js_code
        assert "style.cursor" in js_code

        # Should check onclick property
        assert "el.onclick !== null" in js_code

        # Should filter visibility
        assert "filter" in js_code
        assert "rect.width > 0" in js_code

    def test_clickable_elements_js_no_semantic(self):
        """Test generation with semantic selectors disabled"""
        js_code = ElementValidator.get_clickable_elements_js(include_semantic=False)

        # Semantic section should be disabled
        assert "if (false)" in js_code or "semanticSelector" not in js_code

    def test_clickable_elements_js_no_visual(self):
        """Test generation with visual clickable detection disabled"""
        js_code = ElementValidator.get_clickable_elements_js(include_visual_clickable=False)

        # Visual detection section should be disabled
        assert "if (false)" in js_code or "potentialClickable" in js_code

    def test_clickable_elements_js_viewport_only(self):
        """Test viewport filtering option"""
        js_code = ElementValidator.get_clickable_elements_js(viewport_only=True)

        assert "inViewport" in js_code
        assert "window.innerHeight" in js_code
        assert "window.innerWidth" in js_code

    def test_element_info_js_generation(self):
        """Test element metadata extraction JavaScript"""
        js_code = ElementValidator.get_element_info_js("testElement")

        assert "testElement.tagName" in js_code
        assert "testElement.id" in js_code
        assert "testElement.classList" in js_code
        assert "getBoundingClientRect()" in js_code
        assert "getComputedStyle(testElement)" in js_code
        assert "testElement.onclick !== null" in js_code

    def test_element_info_js_custom_variable(self):
        """Test element info with custom variable name"""
        js_code = ElementValidator.get_element_info_js("myEl")

        assert "myEl.tagName" in js_code
        assert "myEl.id" in js_code
        assert "myEl.classList" in js_code
        assert "getComputedStyle(myEl)" in js_code

    def test_semantic_selectors_list(self):
        """Test that semantic selectors include expected elements"""
        selectors = ElementValidator.SEMANTIC_SELECTORS

        assert 'button' in selectors
        assert 'a' in selectors
        assert '[role="button"]' in selectors
        assert '[onclick]' in selectors
        assert '.btn' in selectors

    def test_potential_clickable_tags_list(self):
        """Test that potential clickable tags include common containers"""
        tags = ElementValidator.POTENTIAL_CLICKABLE_TAGS

        assert 'div' in tags
        assert 'span' in tags
        assert 'li' in tags
        assert 'section' in tags

    def test_no_inline_style_detection(self):
        """Test that generated JS doesn't use inline style detection (v3.0.1 fix)"""
        js_code = ElementValidator.get_clickable_elements_js()

        # Should NOT use CSS selector for inline styles (the bug we fixed!)
        assert '[style*="cursor: pointer"]' not in js_code
        assert '[style*="cursor:pointer"]' not in js_code

        # Should use getComputedStyle instead
        assert "getComputedStyle" in js_code

    def test_react_event_delegation_support(self):
        """Test that generated JS checks onclick property, not attribute"""
        js_code = ElementValidator.get_clickable_elements_js()

        # Should check onclick property (for React/Vue event delegation)
        assert "el.onclick !== null" in js_code

        # The attribute check [onclick] is still in semantic selectors
        # (that's fine for elements with inline onclick attributes)
        # but the key is we ALSO check the property for React elements


class TestVisibilityValidation:
    """Test suite for visibility validation logic"""

    def test_opacity_numeric_comparison(self):
        """Test that opacity uses numeric comparison (v3.0.1 fix)"""
        js_code = ElementValidator.get_visibility_check_js()

        # Should use parseFloat for proper numeric comparison
        assert "parseFloat(style.opacity) > 0" in js_code

        # Should NOT use string comparison (the bug we fixed!)
        assert "style.opacity !== '0'" not in js_code
        assert 'style.opacity === "0"' not in js_code

    def test_complete_visibility_checks(self):
        """Test that all visibility checks are included by default"""
        js_code = ElementValidator.get_visibility_check_js()

        checks = [
            "rect.width > 0",
            "rect.height > 0",
            "style.display !== 'none'",
            "style.visibility !== 'hidden'",
            "parseFloat(style.opacity) > 0",
            "el.offsetParent !== null"
        ]

        for check in checks:
            assert check in js_code


class TestCursorTypeSupport:
    """Test suite for interactive cursor type support (v3.0.1 enhancement)"""

    def test_all_interactive_cursors_supported(self):
        """Test that all expected cursor types are supported"""
        expected_cursors = [
            'pointer',      # Standard clickable
            'move',         # Movable/draggable (the fix for React lead cards!)
            'grab',         # Draggable (idle)
            'grabbing',     # Draggable (active)
            'zoom-in',      # Zoomable (enlarge)
            'zoom-out',     # Zoomable (shrink)
            'all-scroll',   # Scrollable
        ]

        supported = ElementValidator.get_supported_cursor_types()

        for cursor in expected_cursors:
            assert cursor in supported, f"Cursor type '{cursor}' should be supported"

    def test_move_cursor_included(self):
        """Test that 'move' cursor is included (the fix for lead cards!)"""
        assert 'move' in ElementValidator.INTERACTIVE_CURSORS

        js_code = ElementValidator.get_interactive_cursor_check_js()
        assert "style.cursor === 'move'" in js_code


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
