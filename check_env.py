#!/usr/bin/env python3
"""
Environment checker for MCP Comet Browser server
Verifies all requirements are met before running the server
"""

import sys
import socket
import urllib.request
import urllib.error


def check_python_version():
    """Check if Python version is 3.10 or higher"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (required: >= 3.10)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (required: >= 3.10)")
        return False


def check_pychrome_installed():
    """Check if pychrome library is installed"""
    try:
        import pychrome
        print(f"✓ pychrome is installed (version: {pychrome.__version__ if hasattr(pychrome, '__version__') else 'unknown'})")
        return True
    except ImportError:
        print("✗ pychrome is NOT installed")
        print("  Install it with: pip install pychrome")
        return False


def check_debug_port(port=9222):
    """Check if Chrome DevTools Protocol is accessible on the specified port"""
    try:
        # Try to connect to the debug port
        url = f"http://127.0.0.1:{port}/json/version"
        response = urllib.request.urlopen(url, timeout=5)
        data = response.read().decode('utf-8')

        if data:
            print(f"✓ Chrome DevTools Protocol is accessible on port {port}")

            # Try to parse browser info
            import json
            info = json.loads(data)
            browser = info.get('Browser', 'Unknown')
            print(f"  Browser: {browser}")
            return True
    except urllib.error.URLError:
        print(f"✗ Chrome DevTools Protocol is NOT accessible on port {port}")
        print(f"  Make sure Comet browser is running with: --remote-debugging-port={port}")
        return False
    except socket.timeout:
        print(f"✗ Connection to port {port} timed out")
        return False
    except Exception as e:
        print(f"✗ Error connecting to debug port: {str(e)}")
        return False


def check_all():
    """Run all checks and return overall status"""
    print("=" * 60)
    print("MCP Comet Browser - Environment Check")
    print("=" * 60)
    print()

    checks = [
        check_python_version(),
        check_pychrome_installed(),
        check_debug_port(9222)
    ]

    print()
    print("=" * 60)

    if all(checks):
        print("✓ All checks passed! Environment is ready.")
        print("=" * 60)
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(check_all())
