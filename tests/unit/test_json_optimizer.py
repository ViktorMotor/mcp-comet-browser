"""
Unit tests for utils/json_optimizer.py - JSON optimization
"""
import pytest
from utils.json_optimizer import JsonOptimizer


class TestJsonOptimizer:
    """Test JSON optimization for page_info data"""

    def test_optimize_page_info_basic(self):
        """Test basic page info optimization"""
        page_info = {
            "url": "https://example.com",
            "title": "Example Page",
            "interactive_elements": [
                {"tag": "button", "text": "Submit", "position": {"x": 100, "y": 200}},
                {"tag": "a", "text": "Home", "position": {"x": 50, "y": 50}},
                {"tag": "button", "text": "Cancel", "position": {"x": 120, "y": 200}},
            ],
            "console": {"logs": ["log1", "log2"], "total": 2},
            "network": {"total_requests": 10, "failed": 0},
            "summary": {"total_buttons": 2, "total_links": 1}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        assert "url" in result
        assert "title" in result
        assert "interactive_elements" in result
        assert "summary" in result

    def test_optimize_limits_elements(self):
        """Optimization should limit number of elements"""
        # Create 50 elements
        elements = [
            {"tag": "button", "text": f"Button {i}", "position": {"x": i*10, "y": 100}}
            for i in range(50)
        ]

        page_info = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": elements,
            "summary": {"total_buttons": 50}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        # Should limit to top 15 (or similar reasonable limit)
        assert len(result["interactive_elements"]) <= 20

    def test_optimize_removes_duplicates(self):
        """Optimization should remove duplicate elements"""
        page_info = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": [
                {"tag": "button", "text": "Submit", "position": {"x": 100, "y": 200}},
                {"tag": "button", "text": "Submit", "position": {"x": 100, "y": 200}},  # duplicate
                {"tag": "a", "text": "Home", "position": {"x": 50, "y": 50}},
            ],
            "summary": {}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        # Should remove duplicate
        assert len(result["interactive_elements"]) == 2

    def test_full_mode_no_optimization(self):
        """full=True should return data without optimization"""
        page_info = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": [{"tag": "button", "text": f"Button {i}"} for i in range(30)],
            "summary": {}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=True)

        # Should not limit elements in full mode
        assert len(result["interactive_elements"]) == 30

    def test_importance_scoring(self):
        """Optimizer should prioritize important elements"""
        page_info = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": [
                {"tag": "button", "text": "Submit", "id": "submit-btn"},  # High importance (button + ID)
                {"tag": "div", "text": "Random div"},  # Low importance
                {"tag": "a", "text": "Important Link", "role": "button"},  # High importance (link + role)
                {"tag": "span", "text": ""},  # Low importance (no text)
            ],
            "summary": {}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        # Important elements should come first
        elements = result["interactive_elements"]
        assert elements[0]["tag"] in ["button", "a"]

    def test_preserves_metadata(self):
        """Optimization should preserve metadata fields"""
        page_info = {
            "url": "https://example.com",
            "title": "Test Page",
            "viewport": {"width": 1920, "height": 1080},
            "interactive_elements": [{"tag": "button", "text": "Test"}],
            "console": {"logs": ["log1"], "total": 1},
            "network": {"total_requests": 5},
            "summary": {"total_buttons": 1, "page_loaded": True}
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert "summary" in result
        assert result["summary"]["page_loaded"] is True

    def test_empty_page_info(self):
        """Should handle empty page info gracefully"""
        page_info = {}

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        assert isinstance(result, dict)
        # Should have default structure
        assert "interactive_elements" in result or len(result) == 0

    def test_size_reduction(self):
        """Optimization should reduce data size"""
        import json

        # Create large page info
        elements = [
            {
                "tag": "button",
                "text": f"Very long button text that repeats many times {i}",
                "id": f"button-{i}",
                "classes": ["class1", "class2", "class3"],
                "position": {"x": i*10, "y": 100, "width": 100, "height": 30}
            }
            for i in range(100)
        ]

        page_info = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": elements,
            "summary": {}
        }

        # Measure sizes
        original_size = len(json.dumps(page_info))
        optimized = JsonOptimizer.optimize_page_info(page_info, full=False)
        optimized_size = len(json.dumps(optimized))

        # Should be significantly smaller
        reduction_pct = (1 - optimized_size / original_size) * 100
        assert reduction_pct > 30, f"Expected >30% reduction, got {reduction_pct:.1f}%"


class TestJsonOptimizerEdgeCases:
    """Test edge cases and error handling"""

    def test_none_input(self):
        """Should handle None input"""
        result = JsonOptimizer.optimize_page_info(None, full=False)
        assert result == {} or result is None

    def test_missing_interactive_elements(self):
        """Should handle missing interactive_elements key"""
        page_info = {
            "url": "https://example.com",
            "title": "Test"
        }

        result = JsonOptimizer.optimize_page_info(page_info, full=False)

        assert "url" in result
        assert "title" in result

    def test_malformed_elements(self):
        """Should handle malformed elements gracefully"""
        page_info = {
            "url": "https://example.com",
            "interactive_elements": [
                {"tag": "button"},  # Missing text, position
                None,  # Invalid element
                {"text": "No tag"},  # Missing tag
            ]
        }

        # Should not crash
        result = JsonOptimizer.optimize_page_info(page_info, full=False)
        assert isinstance(result, dict)
