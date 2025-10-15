"""Input validation utilities for command parameters

Provides reusable validators for:
- Coordinates (x, y positions)
- Paths (file security)
- Timeouts (reasonable ranges)
- Selectors (CSS syntax)
- URLs (scheme validation)
- Numeric ranges
"""

import os
import re
from typing import Optional, Union
from urllib.parse import urlparse
from mcp.errors import InvalidArgumentError, ValidationError


class Validators:
    """Collection of input validation methods"""

    # Constants
    MAX_COORDINATE = 100000  # Reasonable max for x/y coordinates
    MIN_TIMEOUT = 0.1  # 100ms minimum timeout
    MAX_TIMEOUT = 600  # 10 minutes maximum timeout
    DEFAULT_TIMEOUT = 30

    ALLOWED_PATH_PREFIXES = ['./screenshots/', './page_info.json', './js_result.json']

    @staticmethod
    def validate_coordinate(
        value: Union[int, float],
        param_name: str = "coordinate",
        allow_negative: bool = False
    ) -> float:
        """Validate coordinate value (x or y position)

        Args:
            value: Coordinate value to validate
            param_name: Parameter name for error messages
            allow_negative: Whether to allow negative coordinates

        Returns:
            Validated coordinate as float

        Raises:
            InvalidArgumentError: If coordinate is invalid
        """
        try:
            coord = float(value)
        except (TypeError, ValueError):
            raise InvalidArgumentError(
                argument=param_name,
                expected="numeric value",
                received=str(value)
            )

        if not allow_negative and coord < 0:
            raise InvalidArgumentError(
                argument=param_name,
                expected="non-negative number",
                received=str(coord)
            )

        if abs(coord) > Validators.MAX_COORDINATE:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"coordinate within ±{Validators.MAX_COORDINATE}",
                received=str(coord)
            )

        return coord

    @staticmethod
    def validate_coordinates(
        x: Union[int, float, None] = None,
        y: Union[int, float, None] = None,
        allow_negative: bool = False
    ) -> tuple[Optional[float], Optional[float]]:
        """Validate x and y coordinates together

        Args:
            x: X coordinate (optional)
            y: Y coordinate (optional)
            allow_negative: Whether to allow negative coordinates

        Returns:
            Tuple of (validated_x, validated_y)

        Raises:
            InvalidArgumentError: If coordinates are invalid
        """
        validated_x = None
        validated_y = None

        if x is not None:
            validated_x = Validators.validate_coordinate(x, "x", allow_negative)

        if y is not None:
            validated_y = Validators.validate_coordinate(y, "y", allow_negative)

        return validated_x, validated_y

    @staticmethod
    def validate_path(
        path: str,
        allowed_prefixes: Optional[list[str]] = None,
        must_exist: bool = False
    ) -> str:
        """Validate file path for security

        Args:
            path: File path to validate
            allowed_prefixes: List of allowed path prefixes (default: screenshots, page_info, js_result)
            must_exist: Whether path must already exist

        Returns:
            Validated path string

        Raises:
            InvalidArgumentError: If path is invalid or unsafe
        """
        if not path or not isinstance(path, str):
            raise InvalidArgumentError(
                argument="path",
                expected="non-empty string",
                received=str(path)
            )

        # Security: prevent directory traversal
        if '..' in path or path.startswith('/'):
            raise InvalidArgumentError(
                argument="path",
                expected="relative path without '..'",
                received=path
            )

        # Check allowed prefixes (before normalization to preserve ./)
        if allowed_prefixes is None:
            allowed_prefixes = Validators.ALLOWED_PATH_PREFIXES

        # Allow exact matches or prefixes
        is_allowed = False
        for prefix in allowed_prefixes:
            # Check both original path and without ./ prefix
            check_paths = [path, path.replace('./', '', 1)]
            for check_path in check_paths:
                if check_path == prefix.rstrip('/') or check_path.startswith(prefix.replace('./', '', 1)):
                    is_allowed = True
                    break
            if is_allowed:
                break

        if not is_allowed:
            raise InvalidArgumentError(
                argument="path",
                expected=f"path starting with one of: {', '.join(allowed_prefixes)}",
                received=path
            )

        # Normalize path after prefix check
        normalized = os.path.normpath(path)

        # Check existence if required
        if must_exist and not os.path.exists(normalized):
            raise InvalidArgumentError(
                argument="path",
                expected="existing file path",
                received=path
            )

        return normalized

    @staticmethod
    def validate_timeout(
        timeout: Union[int, float],
        param_name: str = "timeout",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """Validate timeout value

        Args:
            timeout: Timeout in seconds
            param_name: Parameter name for error messages
            min_value: Minimum allowed timeout (default: 0.1s)
            max_value: Maximum allowed timeout (default: 600s)

        Returns:
            Validated timeout as float

        Raises:
            InvalidArgumentError: If timeout is invalid
        """
        try:
            timeout_val = float(timeout)
        except (TypeError, ValueError):
            raise InvalidArgumentError(
                argument=param_name,
                expected="numeric value (seconds)",
                received=str(timeout)
            )

        min_val = min_value if min_value is not None else Validators.MIN_TIMEOUT
        max_val = max_value if max_value is not None else Validators.MAX_TIMEOUT

        if timeout_val < min_val:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"timeout >= {min_val}s",
                received=str(timeout_val)
            )

        if timeout_val > max_val:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"timeout <= {max_val}s",
                received=str(timeout_val)
            )

        return timeout_val

    @staticmethod
    def validate_selector(
        selector: str,
        param_name: str = "selector",
        allow_xpath: bool = True
    ) -> str:
        """Validate CSS/XPath selector

        Args:
            selector: CSS or XPath selector
            param_name: Parameter name for error messages
            allow_xpath: Whether to allow XPath selectors (starting with //)

        Returns:
            Validated selector string

        Raises:
            InvalidArgumentError: If selector is invalid
        """
        if not selector or not isinstance(selector, str):
            raise InvalidArgumentError(
                argument=param_name,
                expected="non-empty selector string",
                received=str(selector)
            )

        selector = selector.strip()

        if not selector:
            raise InvalidArgumentError(
                argument=param_name,
                expected="non-empty selector after trimming",
                received="empty string"
            )

        # Allow XPath if enabled
        if selector.startswith('//'):
            if not allow_xpath:
                raise InvalidArgumentError(
                    argument=param_name,
                    expected="CSS selector (XPath not allowed)",
                    received=selector
                )
            return selector

        # Basic CSS selector validation (not exhaustive, just catch obvious errors)
        # Disallow dangerous patterns
        dangerous_patterns = [
            r'javascript:',  # XSS attempt
            r'<script',      # Script injection
            r'eval\(',       # Eval attempt
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, selector, re.IGNORECASE):
                raise InvalidArgumentError(
                    argument=param_name,
                    expected="safe CSS selector",
                    received=f"selector contains dangerous pattern: {pattern}"
                )

        return selector

    @staticmethod
    def validate_url(
        url: str,
        param_name: str = "url",
        require_scheme: bool = True,
        allowed_schemes: Optional[list[str]] = None
    ) -> str:
        """Validate URL format

        Args:
            url: URL to validate
            param_name: Parameter name for error messages
            require_scheme: Whether scheme (http://) is required
            allowed_schemes: List of allowed schemes (default: http, https)

        Returns:
            Validated URL string

        Raises:
            InvalidArgumentError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise InvalidArgumentError(
                argument=param_name,
                expected="non-empty URL string",
                received=str(url)
            )

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise InvalidArgumentError(
                argument=param_name,
                expected="valid URL",
                received=f"{url} (parse error: {str(e)})"
            )

        if require_scheme and not parsed.scheme:
            raise InvalidArgumentError(
                argument=param_name,
                expected="URL with scheme (http:// or https://)",
                received=url
            )

        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']

        if parsed.scheme and parsed.scheme not in allowed_schemes:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"URL with scheme: {', '.join(allowed_schemes)}",
                received=f"{url} (scheme: {parsed.scheme})"
            )

        return url

    @staticmethod
    def validate_range(
        value: Union[int, float],
        param_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        allow_none: bool = False
    ) -> Optional[Union[int, float]]:
        """Validate numeric value within range

        Args:
            value: Value to validate
            param_name: Parameter name for error messages
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            allow_none: Whether None is acceptable

        Returns:
            Validated value

        Raises:
            InvalidArgumentError: If value is out of range
        """
        if value is None:
            if allow_none:
                return None
            raise InvalidArgumentError(
                argument=param_name,
                expected="non-None value",
                received="None"
            )

        try:
            num_value = float(value)
        except (TypeError, ValueError):
            raise InvalidArgumentError(
                argument=param_name,
                expected="numeric value",
                received=str(value)
            )

        if min_value is not None and num_value < min_value:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"value >= {min_value}",
                received=str(num_value)
            )

        if max_value is not None and num_value > max_value:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"value <= {max_value}",
                received=str(num_value)
            )

        # Return as int if it was originally int
        return int(num_value) if isinstance(value, int) else num_value

    @staticmethod
    def validate_string_length(
        value: str,
        param_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> str:
        """Validate string length

        Args:
            value: String to validate
            param_name: Parameter name for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length

        Returns:
            Validated string

        Raises:
            InvalidArgumentError: If string length is invalid
        """
        if not isinstance(value, str):
            raise InvalidArgumentError(
                argument=param_name,
                expected="string value",
                received=str(type(value).__name__)
            )

        length = len(value)

        if min_length is not None and length < min_length:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"string with length >= {min_length}",
                received=f"length {length}"
            )

        if max_length is not None and length > max_length:
            raise InvalidArgumentError(
                argument=param_name,
                expected=f"string with length <= {max_length}",
                received=f"length {length}"
            )

        return value
