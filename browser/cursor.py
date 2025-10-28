"""Visual AI cursor overlay management"""
import sys
from typing import Dict, Any
from mcp.logging_config import get_logger

logger = get_logger(__name__)


class AICursor:
    """Manages visual AI cursor overlay in browser"""

    def __init__(self, tab):
        """Initialize cursor manager

        Args:
            tab: pychrome Tab instance
        """
        self.tab = tab
        self._initialized = False

    async def initialize(self) -> Dict[str, Any]:
        """Initialize visual AI cursor overlay"""
        try:
            js_code = """
            (function() {
                if (window.__aiCursorInitialized) {
                    return {success: true, message: 'AI cursor already initialized'};
                }

                // Create cursor element
                const cursor = document.createElement('div');
                cursor.id = '__ai_cursor__';
                cursor.style.cssText = `
                    position: fixed;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    background: radial-gradient(circle, rgba(59, 130, 246, 0.8) 0%, rgba(37, 99, 235, 0.6) 50%, rgba(29, 78, 216, 0.4) 100%);
                    border: 2px solid rgba(59, 130, 246, 1);
                    box-shadow: 0 0 20px rgba(59, 130, 246, 0.8), 0 0 40px rgba(59, 130, 246, 0.4);
                    pointer-events: none;
                    z-index: 2147483647;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: none;
                `;

                // Add animations
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes __ai_cursor_click__ {
                        0% { transform: scale(1); }
                        50% { transform: scale(1.5); }
                        100% { transform: scale(1); }
                    }
                    #__ai_cursor__.clicking {
                        animation: __ai_cursor_click__ 1s ease;
                        background: radial-gradient(circle, rgba(34, 197, 94, 0.9) 0%, rgba(22, 163, 74, 0.7) 50%, rgba(21, 128, 61, 0.5) 100%) !important;
                        border-color: rgba(34, 197, 94, 1) !important;
                        box-shadow: 0 0 30px rgba(34, 197, 94, 1), 0 0 60px rgba(34, 197, 94, 0.8), 0 0 90px rgba(34, 197, 94, 0.5) !important;
                    }
                `;

                document.head.appendChild(style);
                document.body.appendChild(cursor);

                // Store cursor reference
                window.__aiCursor__ = cursor;
                window.__aiCursorInitialized = true;

                // Animation state management (v3.0.0)
                let currentAnimation = null;
                let activeTimeouts = [];

                // Helper functions
                window.__moveAICursor__ = function(x, y, duration = 200) {
                    // Cancel any ongoing animation to prevent visual glitches
                    if (currentAnimation) {
                        cancelAnimationFrame(currentAnimation);
                        cursor.style.transition = 'none';  // Instant cancel
                        // Force reflow to apply instant position
                        void cursor.offsetWidth;
                    }

                    cursor.style.display = 'block';

                    // Use requestAnimationFrame for smooth transition start
                    currentAnimation = requestAnimationFrame(() => {
                        cursor.style.transition = `all ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
                        cursor.style.left = (x - 12) + 'px';
                        cursor.style.top = (y - 12) + 'px';

                        // Clear animation reference after completion
                        const tid = setTimeout(() => {
                            currentAnimation = null;
                        }, duration);
                        activeTimeouts.push(tid);
                    });
                };

                window.__clickAICursor__ = function() {
                    cursor.classList.add('clicking');
                    const tid = setTimeout(() => {
                        cursor.classList.remove('clicking');
                        // Remove from active timeouts array
                        activeTimeouts = activeTimeouts.filter(t => t !== tid);
                    }, 400);  // Reduced from 1000ms to 400ms
                    activeTimeouts.push(tid);
                };

                window.__hideAICursor__ = function() {
                    cursor.style.display = 'none';
                };

                window.__cleanupAICursor__ = function() {
                    // Cancel ongoing animations
                    if (currentAnimation) {
                        cancelAnimationFrame(currentAnimation);
                        currentAnimation = null;
                    }
                    // Clear all pending timeouts to prevent memory leaks
                    activeTimeouts.forEach(clearTimeout);
                    activeTimeouts = [];
                    cursor.style.display = 'none';
                };

                return {success: true, message: 'AI cursor initialized'};
            })()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            self._initialized = True
            return result.get('result', {}).get('value', {})
        except Exception as e:
            logger.error(f"Failed to initialize AI cursor: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def move(self, x: int, y: int, duration: int = 200) -> Dict[str, Any]:
        """Move cursor to coordinates (v3.0.0: default duration reduced to 200ms)"""
        if not self._initialized:
            await self.initialize()

        try:
            js_code = f"""
            (function() {{
                if (window.__moveAICursor__) {{
                    window.__moveAICursor__({x}, {y}, {duration});
                    return {{success: true, position: {{x: {x}, y: {y}}}}};
                }} else {{
                    return {{success: false, message: 'AI cursor not initialized'}};
                }}
            }})()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click_animation(self) -> Dict[str, Any]:
        """Show click animation"""
        try:
            js_code = """
            (function() {
                if (window.__clickAICursor__) {
                    window.__clickAICursor__();
                    return {success: true};
                }
                return {success: false, message: 'AI cursor not initialized'};
            })()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup cursor animations and timeouts to prevent memory leaks (v3.0.0)"""
        try:
            js_code = """
            (function() {
                if (window.__cleanupAICursor__) {
                    window.__cleanupAICursor__();
                    return {success: true, message: 'Cursor cleaned up'};
                }
                return {success: false, message: 'AI cursor not initialized'};
            })()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {"success": False, "error": str(e)}
