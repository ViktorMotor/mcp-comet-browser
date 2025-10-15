"""
Shared utilities for page scraping and element extraction
Eliminates code duplication across search/devtools/diagnostics commands
"""
import json
import os
from typing import Dict, Any, Optional
from browser.async_cdp import AsyncCDP


class PageScraper:
    """Centralized page scraping logic"""

    # Shared JavaScript for getting interactive elements
    JS_GET_INTERACTIVE_ELEMENTS = """
    (function() {
        function getVisibleText(el) {
            if (!el) return '';
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return '';
            return (el.innerText || el.textContent || '').trim();
        }

        const interactive = Array.from(document.querySelectorAll('button, a, [role="button"], [role="tab"]'))
            .filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
            })
            .map(el => {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    text: getVisibleText(el).substring(0, 100),
                    id: el.id || null,
                    classes: Array.from(el.classList || []),
                    position: {
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2)
                    }
                };
            });

        // Get console logs if available
        const consoleLogs = window.__consoleHistory || [];

        // Get network info
        const networkEntries = performance.getEntriesByType('resource') || [];

        return {
            url: window.location.href,
            title: document.title,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            interactive_elements: interactive,
            console: {
                logs: consoleLogs.slice(-10),  // Last 10 logs
                total: consoleLogs.length
            },
            network: {
                total_requests: networkEntries.length,
                failed: networkEntries.filter(e => e.transferSize === 0).length,
                recent: networkEntries.slice(-5).map(e => ({
                    name: e.name.split('/').pop().substring(0, 50),
                    type: e.initiatorType,
                    duration: Math.round(e.duration)
                }))
            },
            summary: {
                total_buttons: document.querySelectorAll('button').length,
                total_links: document.querySelectorAll('a').length,
                visible_interactive: interactive.length,
                page_loaded: document.readyState === 'complete'
            }
        };
    })()
    """

    @staticmethod
    async def get_page_info(cdp: AsyncCDP) -> Dict[str, Any]:
        """
        Get comprehensive page information using CDP

        Args:
            cdp: AsyncCDP wrapper for thread-safe evaluation

        Returns:
            Dictionary with page info (interactive elements, console, network, summary)
        """
        result = await cdp.evaluate(
            expression=PageScraper.JS_GET_INTERACTIVE_ELEMENTS,
            returnByValue=True
        )
        return result.get('result', {}).get('value', {})

    @staticmethod
    async def save_to_file(
        data: Dict[str, Any],
        output_file: str = "./page_info.json"
    ) -> Dict[str, Any]:
        """
        Save page info to JSON file

        Args:
            data: Page info dictionary
            output_file: Output file path

        Returns:
            Success result with file info
        """
        # Create directory if needed
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Calculate size
        file_size = os.path.getsize(output_file)
        size_kb = round(file_size / 1024, 1)

        return {
            "success": True,
            "message": f"✅ Page info saved to {output_file} ({size_kb}KB)",
            "file": output_file,
            "size_kb": size_kb,
            "instruction": "Use Read('./page_info.json') to view the data",
            "data_preview": {
                "total_elements": len(data.get('interactive_elements', [])),
                "url": data.get('url'),
                "title": data.get('title')
            }
        }

    @staticmethod
    async def scrape_and_save(
        cdp: AsyncCDP,
        output_file: str = "./page_info.json"
    ) -> Dict[str, Any]:
        """
        Combined scrape + save operation (most common use case)

        Args:
            cdp: AsyncCDP wrapper
            output_file: Output file path

        Returns:
            Success result with file info
        """
        try:
            page_info = await PageScraper.get_page_info(cdp)
            return await PageScraper.save_to_file(page_info, output_file)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to scrape and save page info: {str(e)}"
            }
