"""
Unit tests for utils/validators.py - Input validation utilities
"""
import pytest
from utils.validators import Validators
from mcp.errors import InvalidArgumentError


class TestCoordinateValidation:
    """Test coordinate validation"""

    def test_validate_coordinate_success(self):
        """Valid coordinates should pass"""
        assert Validators.validate_coordinate(100, "x") == 100.0
        assert Validators.validate_coordinate(0, "y") == 0.0
        assert Validators.validate_coordinate(99999, "x") == 99999.0

    def test_validate_coordinate_float(self):
        """Float coordinates should be accepted"""
        assert Validators.validate_coordinate(100.5, "x") == 100.5

    def test_validate_coordinate_negative_disallowed(self):
        """Negative coordinates should fail by default"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_coordinate(-10, "x")
        assert "non-negative" in str(exc.value)

    def test_validate_coordinate_negative_allowed(self):
        """Negative coordinates should pass when allowed"""
        assert Validators.validate_coordinate(-10, "x", allow_negative=True) == -10.0

    def test_validate_coordinate_too_large(self):
        """Coordinates exceeding MAX_COORDINATE should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_coordinate(200000, "x")
        assert "100000" in str(exc.value)

    def test_validate_coordinate_invalid_type(self):
        """Non-numeric coordinates should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_coordinate("abc", "x")

    def test_validate_coordinates_both(self):
        """Validate both x and y together"""
        x, y = Validators.validate_coordinates(100, 200)
        assert x == 100.0
        assert y == 200.0

    def test_validate_coordinates_partial(self):
        """Validate only one coordinate"""
        x, y = Validators.validate_coordinates(x=100)
        assert x == 100.0
        assert y is None

        x, y = Validators.validate_coordinates(y=200)
        assert x is None
        assert y == 200.0


class TestPathValidation:
    """Test file path validation"""

    def test_validate_path_screenshots(self):
        """Valid screenshot paths should pass"""
        path = Validators.validate_path("./screenshots/test.png")
        assert path == "screenshots/test.png"  # normpath removes ./

    def test_validate_path_page_info(self):
        """Valid page_info path should pass"""
        path = Validators.validate_path("./page_info.json")
        assert path == "page_info.json"  # normpath removes ./

    def test_validate_path_directory_traversal(self):
        """Directory traversal should be blocked"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_path("../etc/passwd")
        assert ".." in str(exc.value)

    def test_validate_path_absolute(self):
        """Absolute paths should be blocked"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_path("/etc/passwd")

    def test_validate_path_not_allowed_prefix(self):
        """Paths without allowed prefix should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_path("./forbidden/file.txt")
        assert "starting with" in str(exc.value).lower() or "allowed" in str(exc.value).lower()

    def test_validate_path_empty(self):
        """Empty path should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_path("")

    def test_validate_path_custom_prefixes(self):
        """Custom allowed prefixes should work"""
        path = Validators.validate_path("./custom/file.txt", allowed_prefixes=["./custom/"])
        assert path == "custom/file.txt"  # normpath removes ./


class TestTimeoutValidation:
    """Test timeout validation"""

    def test_validate_timeout_success(self):
        """Valid timeouts should pass"""
        assert Validators.validate_timeout(30) == 30.0
        assert Validators.validate_timeout(0.5) == 0.5
        assert Validators.validate_timeout(600) == 600.0

    def test_validate_timeout_too_small(self):
        """Timeouts below minimum should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_timeout(0.05)
        assert "0.1" in str(exc.value)

    def test_validate_timeout_too_large(self):
        """Timeouts above maximum should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_timeout(1000)
        assert "600" in str(exc.value)

    def test_validate_timeout_custom_range(self):
        """Custom timeout ranges should work"""
        timeout = Validators.validate_timeout(5, min_value=1, max_value=10)
        assert timeout == 5.0

        with pytest.raises(InvalidArgumentError):
            Validators.validate_timeout(0.5, min_value=1, max_value=10)

    def test_validate_timeout_invalid_type(self):
        """Non-numeric timeouts should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_timeout("abc")


class TestSelectorValidation:
    """Test CSS/XPath selector validation"""

    def test_validate_selector_css(self):
        """Valid CSS selectors should pass"""
        assert Validators.validate_selector("#myid") == "#myid"
        assert Validators.validate_selector(".myclass") == ".myclass"
        assert Validators.validate_selector("div > p") == "div > p"

    def test_validate_selector_xpath(self):
        """Valid XPath selectors should pass when allowed"""
        assert Validators.validate_selector("//button", allow_xpath=True) == "//button"

    def test_validate_selector_xpath_disallowed(self):
        """XPath should fail when not allowed"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_selector("//button", allow_xpath=False)
        assert "XPath" in str(exc.value)

    def test_validate_selector_empty(self):
        """Empty selectors should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_selector("")

        with pytest.raises(InvalidArgumentError):
            Validators.validate_selector("   ")

    def test_validate_selector_dangerous_patterns(self):
        """Dangerous patterns should be blocked"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_selector("javascript:alert(1)")

        with pytest.raises(InvalidArgumentError):
            Validators.validate_selector("<script>alert(1)</script>")

        with pytest.raises(InvalidArgumentError):
            Validators.validate_selector("eval('alert(1)')")


class TestURLValidation:
    """Test URL validation"""

    def test_validate_url_success(self):
        """Valid URLs should pass"""
        url = Validators.validate_url("https://example.com")
        assert url == "https://example.com"

        url = Validators.validate_url("http://localhost:3000")
        assert url == "http://localhost:3000"

    def test_validate_url_no_scheme(self):
        """URLs without scheme should fail when required"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_url("example.com")
        assert "scheme" in str(exc.value)

    def test_validate_url_no_scheme_optional(self):
        """URLs without scheme should pass when not required"""
        url = Validators.validate_url("example.com", require_scheme=False)
        assert url == "example.com"

    def test_validate_url_invalid_scheme(self):
        """URLs with invalid scheme should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_url("ftp://example.com")
        assert "http" in str(exc.value)

    def test_validate_url_custom_schemes(self):
        """Custom allowed schemes should work"""
        url = Validators.validate_url("ftp://example.com", allowed_schemes=["ftp"])
        assert url == "ftp://example.com"

    def test_validate_url_empty(self):
        """Empty URLs should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_url("")


class TestRangeValidation:
    """Test numeric range validation"""

    def test_validate_range_success(self):
        """Valid values in range should pass"""
        assert Validators.validate_range(50, "value", min_value=0, max_value=100) == 50
        assert Validators.validate_range(0, "value", min_value=0, max_value=100) == 0
        assert Validators.validate_range(100, "value", min_value=0, max_value=100) == 100

    def test_validate_range_below_min(self):
        """Values below minimum should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_range(-1, "value", min_value=0, max_value=100)
        assert ">=" in str(exc.value)

    def test_validate_range_above_max(self):
        """Values above maximum should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_range(101, "value", min_value=0, max_value=100)
        assert "<=" in str(exc.value)

    def test_validate_range_none_allowed(self):
        """None should pass when allowed"""
        assert Validators.validate_range(None, "value", allow_none=True) is None

    def test_validate_range_none_disallowed(self):
        """None should fail when not allowed"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_range(None, "value", allow_none=False)

    def test_validate_range_float(self):
        """Float values should work"""
        assert Validators.validate_range(50.5, "value", min_value=0, max_value=100) == 50.5

    def test_validate_range_int_preserved(self):
        """Int type should be preserved"""
        result = Validators.validate_range(50, "value", min_value=0, max_value=100)
        assert isinstance(result, int)

    def test_validate_range_invalid_type(self):
        """Non-numeric values should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_range("abc", "value", min_value=0, max_value=100)


class TestStringLengthValidation:
    """Test string length validation"""

    def test_validate_string_length_success(self):
        """Valid strings should pass"""
        text = Validators.validate_string_length("hello", "text", min_length=1, max_length=10)
        assert text == "hello"

    def test_validate_string_length_too_short(self):
        """Strings below minimum length should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_string_length("ab", "text", min_length=3)
        assert "length >= 3" in str(exc.value)

    def test_validate_string_length_too_long(self):
        """Strings above maximum length should fail"""
        with pytest.raises(InvalidArgumentError) as exc:
            Validators.validate_string_length("toolongstring", "text", max_length=5)
        assert "length <= 5" in str(exc.value)

    def test_validate_string_length_exact_boundaries(self):
        """Exact boundary values should pass"""
        Validators.validate_string_length("abc", "text", min_length=3, max_length=3)
        Validators.validate_string_length("abc", "text", min_length=3, max_length=5)
        Validators.validate_string_length("abcde", "text", min_length=3, max_length=5)

    def test_validate_string_length_not_string(self):
        """Non-string values should fail"""
        with pytest.raises(InvalidArgumentError):
            Validators.validate_string_length(123, "text", min_length=1)


class TestValidatorsConstants:
    """Test validator constants"""

    def test_constants_defined(self):
        """Constants should be defined"""
        assert Validators.MAX_COORDINATE == 100000
        assert Validators.MIN_TIMEOUT == 0.1
        assert Validators.MAX_TIMEOUT == 600
        assert Validators.DEFAULT_TIMEOUT == 30
        assert isinstance(Validators.ALLOWED_PATH_PREFIXES, list)
        assert len(Validators.ALLOWED_PATH_PREFIXES) > 0
