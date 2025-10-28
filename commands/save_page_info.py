"""Save page info to file for debugging MCP output issues"""
import json
import os
from typing import Dict, Any
from .base import Command
from .registry import register
from utils.json_optimizer import JsonOptimizer
from mcp.logging_config import get_logger

logger = get_logger("commands.save_page_info")


@register
class SavePageInfoCommand(Command):
    """Save page snapshot to file (workaround for Claude Code not showing MCP results)"""

    name = "save_page_info"
    description = """Save complete page state to JSON file. ALWAYS use Read tool after this to see results!

Returns: All interactive elements with coordinates, console logs, network info
Usage: 1) Call save_page_info() 2) Read('./page_info.json') to see data
Contains: buttons/links positions, DevTools console (last 10 logs), network requests"""
    input_schema = {
        "type": "object",
        "properties": {
            "output_file": {
                "type": "string",
                "description": "Output file path",
                "default": "./page_info.json"
            },
            "full": {
                "type": "boolean",
                "description": "If true, return full unoptimized data (for debugging)",
                "default": False
            }
        }
    }

    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, output_file: str = "./page_info.json", full: bool = False) -> Dict[str, Any]:
        """Save page info to file (optimized by default, use full=True for debugging)"""
        logger.info(f"save_page_info: file={output_file}, full={full}")
        try:
            js_code = """
            (function() {
                function getVisibleText(el) {
                    if (!el) return '';
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return '';
                    return (el.innerText || el.textContent || '').trim();
                }

                // CRITICAL FIX: Find ALL interactive elements (semantic + visually clickable)
                let interactiveElements = [];

                // 1. Semantic clickable elements
                const semanticSelector = 'button, a, input[type="button"], input[type="submit"], [role="button"], [role="tab"], [role="link"], [onclick], .btn, .button, [tabindex]';
                const semanticElements = Array.from(document.querySelectorAll(semanticSelector));
                interactiveElements.push(...semanticElements);

                // 2. Visually clickable elements (cursor: pointer) - like lead cards!
                const potentialClickable = Array.from(document.querySelectorAll('div, span, li, section, article, header'));
                for (const el of potentialClickable) {
                    const style = window.getComputedStyle(el);
                    if (style.cursor === 'pointer' || el.onclick !== null) {
                        interactiveElements.push(el);
                    }
                }

                // Remove duplicates and filter visible
                const interactive = [...new Set(interactiveElements)]
                    .filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
                    })
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return {
                            tag: el.tagName.toLowerCase(),
                            text: getVisibleText(el).substring(0, 100),
                            id: el.id || null,
                            classes: Array.from(el.classList || []),
                            position: {
                                x: Math.round(rect.left + rect.width/2),
                                y: Math.round(rect.top + rect.height/2)
                            },
                            clickable_reason: el.onclick || style.cursor === 'pointer' ? 'cursor-pointer' : 'semantic'
                        };
                    });

                // Get console logs if available
                const consoleLogs = window.__consoleHistory || [];

                // Get network info
                const networkEntries = performance.getEntriesByType('resource') || [];

                // FORM AUTOMATION SUPPORT (v3.0.0): Extract form structures
                const forms = Array.from(document.querySelectorAll('form')).map(form => {
                    const fields = Array.from(form.querySelectorAll('input, textarea, select')).map(field => {
                        const label = form.querySelector(`label[for="${field.id}"]`) ||
                                     field.closest('label') ||
                                     field.previousElementSibling?.tagName === 'LABEL' ? field.previousElementSibling : null;

                        return {
                            name: field.name || field.id || null,
                            type: field.type || field.tagName.toLowerCase(),
                            placeholder: field.placeholder || null,
                            value: field.value || null,
                            required: field.required || false,
                            disabled: field.disabled || false,
                            label: label ? getVisibleText(label) : null,
                            id: field.id || null,
                            selector: field.id ? `#${field.id}` : field.name ? `[name="${field.name}"]` : null
                        };
                    });

                    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');

                    return {
                        id: form.id || null,
                        action: form.action || null,
                        method: form.method || 'GET',
                        field_count: fields.length,
                        fields: fields,
                        submit_button: submitBtn ? {
                            text: getVisibleText(submitBtn),
                            type: submitBtn.type,
                            id: submitBtn.id || null
                        } : null
                    };
                });

                // Extract all inputs (not just in forms)
                const allInputs = Array.from(document.querySelectorAll('input, textarea')).map(input => {
                    const label = document.querySelector(`label[for="${input.id}"]`) ||
                                 input.closest('label') ||
                                 input.previousElementSibling?.tagName === 'LABEL' ? input.previousElementSibling : null;

                    return {
                        name: input.name || input.id || null,
                        type: input.type || 'text',
                        placeholder: input.placeholder || null,
                        value: input.value || null,
                        required: input.required || false,
                        label: label ? getVisibleText(label) : null,
                        selector: input.id ? `#${input.id}` : input.name ? `[name="${input.name}"]` : null
                    };
                });

                // Extract all selects
                const allSelects = Array.from(document.querySelectorAll('select')).map(select => {
                    const options = Array.from(select.options).map(opt => opt.text.trim());
                    const selectedValue = select.value;
                    const selectedText = select.options[select.selectedIndex]?.text.trim() || null;

                    const label = document.querySelector(`label[for="${select.id}"]`) ||
                                 select.closest('label') ||
                                 select.previousElementSibling?.tagName === 'LABEL' ? select.previousElementSibling : null;

                    return {
                        name: select.name || select.id || null,
                        label: label ? getVisibleText(label) : null,
                        options: options,
                        selected_value: selectedValue,
                        selected_text: selectedText,
                        selector: select.id ? `#${select.id}` : select.name ? `[name="${select.name}"]` : null
                    };
                });

                return {
                    url: window.location.href,
                    title: document.title,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    interactive_elements: interactive,
                    forms: forms,
                    inputs: allInputs,
                    selects: allSelects,
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

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            page_info = result.get('result', {}).get('value', {})

            # Optimize data (unless full=True)
            optimized_data = JsonOptimizer.optimize_page_info(page_info, full=full)

            # Save to file
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(optimized_data, f, indent=2, ensure_ascii=False)

            # Calculate size info
            file_size = os.path.getsize(output_file)
            size_kb = round(file_size / 1024, 1)

            logger.info(f"✓ Page info saved: {output_file} ({size_kb}KB, {'full' if full else 'optimized'})")
            logger.debug(f"  Elements: {len(page_info.get('interactive_elements', []))}, "
                        f"Console logs: {page_info.get('console', {}).get('total', 0)}")

            return {
                "success": True,
                "message": f"Page info saved to {output_file} ({size_kb}KB, {'full' if full else 'optimized'} mode)",
                "file": output_file,
                "size_kb": size_kb,
                "optimized": not full,
                "summary": optimized_data.get('summary', {})
            }

        except Exception as e:
            logger.error(f"✗ Failed to save page info: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to save page info: {str(e)}",
                "error": str(e)
            }
