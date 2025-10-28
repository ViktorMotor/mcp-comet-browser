"""Form automation commands (v3.0.0)"""

import json
from typing import Dict, Any, Optional
from .base import Command
from .registry import register
from mcp.logging_config import get_logger
from utils.validators import Validators

logger = get_logger(__name__)


@register
class FillInputCommand(Command):
    """Fill text input or textarea field"""

    name = "fill_input"
    description = """Fill an input or textarea field with text (v3.0.0 feature).

Triggers proper events (input, change, blur) to ensure form validation works.
Supports CSS selectors, name attributes, and IDs.

Best for: Form filling, search boxes, text entry.
Tip: Use save_page_info() first to see available input fields."""

    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector, name, or ID of the input field"
            },
            "value": {
                "type": "string",
                "description": "Text value to fill in"
            },
            "clear_first": {
                "type": "boolean",
                "description": "Clear existing value first (default: true)",
                "default": True
            }
        },
        "required": ["selector", "value"]
    }

    requires_cdp = True

    async def execute(self, selector: str, value: str, clear_first: bool = True, **kwargs) -> Dict[str, Any]:
        """Fill input field with value"""
        try:
            selector = Validators.validate_string_length(selector, "selector", min_length=1, max_length=500)
            value_escaped = json.dumps(value)
            selector_escaped = json.dumps(selector)

            js_code = f"""
            (function() {{
                // Try multiple selector strategies
                let el = document.querySelector({selector_escaped});

                // Fallback: try name attribute
                if (!el) {{
                    el = document.querySelector(`[name={selector_escaped}]`);
                }}

                // Fallback: try ID
                if (!el) {{
                    el = document.getElementById({selector_escaped});
                }}

                if (!el) {{
                    return {{
                        success: false,
                        message: `Input field not found: ${{{selector_escaped}}}`
                    }};
                }}

                // Check if it's an input/textarea
                if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') {{
                    return {{
                        success: false,
                        message: `Element is not an input or textarea: ${{el.tagName}}`
                    }};
                }}

                // Clear if requested
                if ({str(clear_first).lower()}) {{
                    el.value = '';
                }}

                // Set value
                el.value = {value_escaped};

                // Trigger events for form validation
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));

                // Focus for visual feedback
                el.focus();

                return {{
                    success: true,
                    message: `Filled input: ${{{selector_escaped}}}`,
                    element: {{
                        tag: el.tagName,
                        type: el.type || null,
                        name: el.name || null,
                        id: el.id || null,
                        value: el.value
                    }}
                }};
            }})()
            """

            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            result_value = result.get('result', {}).get('value', {})

            if result_value.get('success'):
                logger.info(f"✓ Filled input: {selector}")
            else:
                logger.warning(f"✗ Failed to fill input: {selector}")

            return result_value

        except Exception as e:
            logger.error(f"Failed to fill input: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to fill input: {str(e)}",
                "error": str(e)
            }


@register
class SelectOptionCommand(Command):
    """Select option in dropdown/select element"""

    name = "select_option"
    description = """Select an option in a dropdown/select element (v3.0.0 feature).

Can select by visible text, value attribute, or index.
Triggers change event for form validation.

Best for: Dropdowns, select menus, filters.
Tip: Use save_page_info() to see available options."""

    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector, name, or ID of the select element"
            },
            "option": {
                "type": "string",
                "description": "Option to select (by text or value)"
            },
            "by": {
                "type": "string",
                "description": "Selection method: 'text', 'value', or 'index'",
                "enum": ["text", "value", "index"],
                "default": "text"
            }
        },
        "required": ["selector", "option"]
    }

    requires_cdp = True

    async def execute(self, selector: str, option: str, by: str = "text", **kwargs) -> Dict[str, Any]:
        """Select option in dropdown"""
        try:
            selector_escaped = json.dumps(selector)
            option_escaped = json.dumps(option)

            js_code = f"""
            (function() {{
                // Find select element
                let el = document.querySelector({selector_escaped});

                if (!el) {{
                    el = document.querySelector(`[name={selector_escaped}]`);
                }}

                if (!el) {{
                    el = document.getElementById({selector_escaped});
                }}

                if (!el) {{
                    return {{
                        success: false,
                        message: `Select element not found: ${{{selector_escaped}}}`
                    }};
                }}

                if (el.tagName !== 'SELECT') {{
                    return {{
                        success: false,
                        message: `Element is not a select: ${{el.tagName}}`
                    }};
                }}

                const selectionMethod = {json.dumps(by)};
                const searchValue = {option_escaped};

                let optionElement = null;

                if (selectionMethod === 'text') {{
                    // Find by visible text
                    optionElement = Array.from(el.options).find(opt =>
                        opt.text.trim().toLowerCase() === searchValue.toLowerCase()
                    );
                }} else if (selectionMethod === 'value') {{
                    // Find by value attribute
                    optionElement = Array.from(el.options).find(opt =>
                        opt.value === searchValue
                    );
                }} else if (selectionMethod === 'index') {{
                    // Select by index
                    const index = parseInt(searchValue);
                    if (!isNaN(index) && index >= 0 && index < el.options.length) {{
                        optionElement = el.options[index];
                    }}
                }}

                if (!optionElement) {{
                    return {{
                        success: false,
                        message: `Option not found: ${{{option_escaped}}} (method: ${{selectionMethod}})`,
                        available_options: Array.from(el.options).map(opt => ({{
                            text: opt.text.trim(),
                            value: opt.value
                        }}))
                    }};
                }}

                // Set selected
                el.value = optionElement.value;
                optionElement.selected = true;

                // Trigger change event
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));

                return {{
                    success: true,
                    message: `Selected option: ${{optionElement.text.trim()}}`,
                    element: {{
                        name: el.name || null,
                        id: el.id || null,
                        selected_text: optionElement.text.trim(),
                        selected_value: optionElement.value
                    }}
                }};
            }})()
            """

            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            result_value = result.get('result', {}).get('value', {})

            if result_value.get('success'):
                logger.info(f"✓ Selected option: {option} in {selector}")
            else:
                logger.warning(f"✗ Failed to select option: {option}")

            return result_value

        except Exception as e:
            logger.error(f"Failed to select option: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to select option: {str(e)}",
                "error": str(e)
            }


@register
class CheckCheckboxCommand(Command):
    """Check or uncheck a checkbox"""

    name = "check_checkbox"
    description = """Check or uncheck a checkbox (v3.0.0 feature).

Triggers change event for form validation.

Best for: Checkboxes, toggle switches.
Tip: Use save_page_info() to see checkbox states."""

    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector, name, or ID of the checkbox"
            },
            "checked": {
                "type": "boolean",
                "description": "True to check, False to uncheck (default: True)",
                "default": True
            }
        },
        "required": ["selector"]
    }

    requires_cdp = True

    async def execute(self, selector: str, checked: bool = True, **kwargs) -> Dict[str, Any]:
        """Check or uncheck checkbox"""
        try:
            selector_escaped = json.dumps(selector)

            js_code = f"""
            (function() {{
                let el = document.querySelector({selector_escaped});

                if (!el) {{
                    el = document.querySelector(`[name={selector_escaped}]`);
                }}

                if (!el) {{
                    el = document.getElementById({selector_escaped});
                }}

                if (!el) {{
                    return {{
                        success: false,
                        message: `Checkbox not found: ${{{selector_escaped}}}`
                    }};
                }}

                if (el.type !== 'checkbox') {{
                    return {{
                        success: false,
                        message: `Element is not a checkbox: ${{el.type || el.tagName}}`
                    }};
                }}

                // Set checked state
                el.checked = {str(checked).lower()};

                // Trigger change event
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));

                return {{
                    success: true,
                    message: `Checkbox ${{el.checked ? 'checked' : 'unchecked'}}`,
                    element: {{
                        name: el.name || null,
                        id: el.id || null,
                        checked: el.checked
                    }}
                }};
            }})()
            """

            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            result_value = result.get('result', {}).get('value', {})

            if result_value.get('success'):
                logger.info(f"✓ Checkbox {'checked' if checked else 'unchecked'}: {selector}")
            else:
                logger.warning(f"✗ Failed to modify checkbox: {selector}")

            return result_value

        except Exception as e:
            logger.error(f"Failed to check checkbox: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to check checkbox: {str(e)}",
                "error": str(e)
            }


@register
class SubmitFormCommand(Command):
    """Submit a form"""

    name = "submit_form"
    description = """Submit a form by selector or by clicking its submit button (v3.0.0 feature).

Triggers submit event. Use after filling form fields.

Best for: Form submission after filling all fields.
Tip: Ensure all required fields are filled first."""

    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector or ID of the form"
            },
            "method": {
                "type": "string",
                "description": "Submit method: 'submit' (programmatic) or 'click' (click submit button)",
                "enum": ["submit", "click"],
                "default": "click"
            }
        },
        "required": ["selector"]
    }

    requires_cdp = True

    async def execute(self, selector: str, method: str = "click", **kwargs) -> Dict[str, Any]:
        """Submit form"""
        try:
            selector_escaped = json.dumps(selector)

            js_code = f"""
            (function() {{
                let form = document.querySelector({selector_escaped});

                if (!form) {{
                    form = document.getElementById({selector_escaped});
                }}

                if (!form) {{
                    return {{
                        success: false,
                        message: `Form not found: ${{{selector_escaped}}}`
                    }};
                }}

                if (form.tagName !== 'FORM') {{
                    return {{
                        success: false,
                        message: `Element is not a form: ${{form.tagName}}`
                    }};
                }}

                const submitMethod = {json.dumps(method)};

                if (submitMethod === 'click') {{
                    // Find and click submit button
                    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                    if (!submitBtn) {{
                        return {{
                            success: false,
                            message: 'Submit button not found in form'
                        }};
                    }}
                    submitBtn.click();
                }} else {{
                    // Programmatic submit
                    form.submit();
                }}

                return {{
                    success: true,
                    message: 'Form submitted',
                    form: {{
                        id: form.id || null,
                        action: form.action,
                        method: form.method,
                        field_count: form.querySelectorAll('input, textarea, select').length
                    }}
                }};
            }})()
            """

            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            result_value = result.get('result', {}).get('value', {})

            if result_value.get('success'):
                logger.info(f"✓ Form submitted: {selector}")
            else:
                logger.warning(f"✗ Failed to submit form: {selector}")

            return result_value

        except Exception as e:
            logger.error(f"Failed to submit form: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to submit form: {str(e)}",
                "error": str(e)
            }
