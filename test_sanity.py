#!/usr/bin/env python3
"""Sanity check for refactored MCP server"""
import sys

print("=" * 60)
print("MCP Comet Server - Sanity Check")
print("=" * 60)
print()

tests_passed = 0
tests_failed = 0

# Test 1: Import main protocol
print("Test 1: Import mcp.protocol...")
try:
    from mcp.protocol import MCPJSONRPCServer
    print("  ✅ PASS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 2: Import browser connection
print("Test 2: Import browser.connection...")
try:
    from browser.connection import BrowserConnection
    print("  ✅ PASS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 3: Import all commands
print("Test 3: Import all commands...")
try:
    from commands.navigation import OpenUrlCommand, GetTextCommand
    from commands.interaction import ClickCommand, ClickByTextCommand
    from commands.devtools import ConsoleCommandCommand, InspectElementCommand
    from commands.tabs import ListTabsCommand
    from commands.evaluation import EvaluateJsCommand
    from commands.screenshot import ScreenshotCommand
    from commands.search import FindElementsCommand, GetPageStructureCommand
    print("  ✅ PASS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 4: Instantiate server
print("Test 4: Instantiate MCPJSONRPCServer...")
try:
    server = MCPJSONRPCServer()
    print(f"  ✅ PASS (registered {len(server.commands)} commands)")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 5: Check command count
print("Test 5: Verify command count...")
try:
    assert len(server.commands) == 20, f"Expected 20 commands, got {len(server.commands)}"
    print(f"  ✅ PASS (20 commands)")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 6: Check critical commands exist
print("Test 6: Check critical commands...")
try:
    critical_commands = [
        'open_url', 'click', 'click_by_text', 'console_command', 
        'inspect_element', 'find_elements', 'get_page_structure',
        'screenshot', 'evaluate_js'
    ]
    for cmd in critical_commands:
        assert cmd in server.commands, f"Missing command: {cmd}"
    print(f"  ✅ PASS (all {len(critical_commands)} critical commands present)")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

# Test 7: Check MCP tool definitions
print("Test 7: Generate MCP tool definitions...")
try:
    tools = server.list_tools()
    assert 'tools' in tools
    assert len(tools['tools']) == 20
    # Check one tool definition
    tool = tools['tools'][0]
    assert 'name' in tool
    assert 'description' in tool
    assert 'inputSchema' in tool
    print(f"  ✅ PASS ({len(tools['tools'])} tool definitions)")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    tests_failed += 1

print()
print("=" * 60)
print(f"Results: {tests_passed} passed, {tests_failed} failed")
print("=" * 60)

if tests_failed > 0:
    print("❌ SANITY CHECK FAILED - DO NOT COMMIT")
    sys.exit(1)
else:
    print("✅ SANITY CHECK PASSED - Safe to commit")
    sys.exit(0)
