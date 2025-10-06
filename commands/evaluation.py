"""JavaScript evaluation command"""
from typing import Dict, Any
from .base import Command


class EvaluateJsCommand(Command):
    """Execute JavaScript code in browser"""

    @property
    def name(self) -> str:
        return "evaluate_js"

    @property
    def description(self) -> str:
        return "⚠️ NO OUTPUT visible. Use for actions only (e.g. clicks). For data: save_page_info() instead"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "JavaScript code to execute"}
            },
            "required": ["code"]
        }

    async def execute(self, code: str) -> Dict[str, Any]:
        """Execute JS code and return result"""
        try:
            # Wrap code in IIFE if it doesn't already return
            if not code.strip().startswith('(function'):
                code = f"(function() {{ {code} }})()"

            result = self.tab.Runtime.evaluate(expression=code, returnByValue=True)

            if result.get('exceptionDetails'):
                error_msg = result['exceptionDetails'].get('text', 'Unknown error')
                return {"success": False, "error": error_msg}

            value = result.get('result', {}).get('value')
            return {"success": True, "result": value}
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate JavaScript: {str(e)}")
