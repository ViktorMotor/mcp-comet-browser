"""
Unit tests for utils/page_scraper.py - Shared scraping utilities
"""
import pytest
from unittest.mock import AsyncMock, mock_open, patch
from utils.page_scraper import PageScraper


class TestPageScraper:
    """Test page scraping utilities"""

    @pytest.mark.asyncio
    async def test_get_page_info(self, mock_async_cdp):
        """Test get_page_info extracts data via CDP"""
        # Mock CDP response
        mock_async_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "url": "https://example.com",
                    "title": "Test Page",
                    "interactive_elements": [
                        {"tag": "button", "text": "Submit"}
                    ]
                }
            }
        }

        result = await PageScraper.get_page_info(mock_async_cdp)

        # Should call CDP evaluate
        mock_async_cdp.evaluate.assert_called_once()
        call_args = mock_async_cdp.evaluate.call_args

        # Should use shared JS code
        assert "interactive_elements" in str(call_args)
        assert "console" in str(call_args)

        # Should return page info
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert len(result["interactive_elements"]) == 1

    @pytest.mark.asyncio
    async def test_save_to_file(self, tmp_path):
        """Test save_to_file creates JSON file"""
        data = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": [{"tag": "button"}]
        }

        output_file = tmp_path / "test_page_info.json"

        result = await PageScraper.save_to_file(data, str(output_file))

        # Should return success
        assert result["success"] is True
        assert "file" in result
        assert "size_kb" in result

        # File should exist
        assert output_file.exists()

        # Should contain data
        import json
        with open(output_file) as f:
            saved_data = json.load(f)
        assert saved_data["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_save_creates_directory(self, tmp_path):
        """Test save_to_file creates missing directories"""
        output_file = tmp_path / "subdir" / "page_info.json"

        data = {"url": "https://example.com"}

        result = await PageScraper.save_to_file(data, str(output_file))

        assert result["success"] is True
        assert output_file.exists()

    @pytest.mark.asyncio
    async def test_scrape_and_save_combined(self, mock_async_cdp, tmp_path):
        """Test scrape_and_save performs both operations"""
        # Mock CDP response
        mock_async_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "url": "https://example.com",
                    "interactive_elements": []
                }
            }
        }

        output_file = tmp_path / "page_info.json"

        result = await PageScraper.scrape_and_save(mock_async_cdp, str(output_file))

        # Should call CDP
        mock_async_cdp.evaluate.assert_called_once()

        # Should create file
        assert output_file.exists()

        # Should return success
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_scrape_and_save_error_handling(self, mock_async_cdp):
        """Test scrape_and_save handles errors gracefully"""
        # Mock CDP error
        mock_async_cdp.evaluate.side_effect = Exception("CDP failed")

        result = await PageScraper.scrape_and_save(mock_async_cdp, "./test.json")

        # Should return error
        assert result["success"] is False
        assert "error" in result
        assert "CDP failed" in result["error"]

    @pytest.mark.asyncio
    async def test_shared_js_code(self):
        """Test shared JavaScript code is valid"""
        js_code = PageScraper.JS_GET_INTERACTIVE_ELEMENTS

        # Should be non-empty
        assert len(js_code) > 100

        # Should contain key parts
        assert "interactive_elements" in js_code
        assert "console" in js_code or "__consoleHistory" in js_code
        assert "network" in js_code or "performance" in js_code

        # Should be IIFE
        assert "(function()" in js_code or "() =>" in js_code

    def test_js_code_consistency(self):
        """Shared JS should match what save_page_info uses"""
        js_code = PageScraper.JS_GET_INTERACTIVE_ELEMENTS

        # Should return structured object
        assert "url: window.location.href" in js_code
        assert "title: document.title" in js_code
        assert "viewport" in js_code or "interactive_elements" in js_code


class TestPageScraperIntegration:
    """Integration-style tests (still using mocks)"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_async_cdp, tmp_path):
        """Test complete scraping workflow"""
        # Mock realistic page data
        page_data = {
            "url": "https://example.com/page",
            "title": "Example Page",
            "viewport": {"width": 1920, "height": 1080},
            "interactive_elements": [
                {"tag": "button", "text": "Submit", "position": {"x": 100, "y": 200}},
                {"tag": "a", "text": "Home", "position": {"x": 50, "y": 50}}
            ],
            "console": {"logs": [], "total": 0},
            "network": {"total_requests": 5, "failed": 0},
            "summary": {
                "total_buttons": 1,
                "total_links": 1,
                "visible_interactive": 2,
                "page_loaded": True
            }
        }

        mock_async_cdp.evaluate.return_value = {
            "result": {"value": page_data}
        }

        output_file = tmp_path / "page_info.json"

        # Execute workflow
        result = await PageScraper.scrape_and_save(mock_async_cdp, str(output_file))

        # Verify success
        assert result["success"] is True
        assert result["data_preview"]["total_elements"] == 2

        # Verify file content
        import json
        with open(output_file) as f:
            saved = json.load(f)

        assert saved["url"] == "https://example.com/page"
        assert saved["title"] == "Example Page"
        assert len(saved["interactive_elements"]) == 2
