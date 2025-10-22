"""Version information for MCP Comet Browser"""

__version__ = "2.20.0"
__version_info__ = (2, 20, 0)
__release_date__ = "2025-10-22"

# Version history
VERSION_HISTORY = {
    "2.20.0": {
        "date": "2025-10-22",
        "description": "🎯 Critical Fix - Visual Clickability Detection",
        "changes": [
            "FIXED: click_by_text now finds elements with cursor:pointer (lead cards!)",
            "FIXED: save_page_info includes visually clickable elements, not just semantic",
            "FIXED: evaluate_js depth limit increased 3→5 for better object serialization",
            "Added cursor:pointer detection in click_by_text",
            "Added onclick handler detection",
            "New field 'clickable_reason' in save_page_info output",
            "Better depth limit messages: shows object/array size"
        ],
        "user_reported": "Lead cards not found by click_by_text - only semantic buttons visible"
    },
    "2.19.0": {
        "date": "2025-10-22",
        "description": "🔧 Critical MCP Protocol Fix - Command Results Now Visible",
        "changes": [
            "FIXED: Commands now return MCP-compliant format (content array)",
            "FIXED: evaluate_js, console_command, inspect_element results now visible in Claude Code",
            "Added _wrap_result_for_mcp() with smart formatting for all result types",
            "Added requires_cdp=True to 14 commands using AsyncCDP",
            "Smart output formatting: console_output, exceptions, file_paths, instructions",
            "Backward-compatible: legacy format auto-converted to MCP format",
            "All 29 tools now properly display results in Claude Code"
        ],
        "breaking_changes": [],
        "migration": "No migration needed - all changes are backward-compatible"
    },
    "2.18.1": {
        "date": "2025-10-16",
        "description": "Screenshot bugfix and AI optimization guide",
        "changes": [
            "Fixed screenshot command crash (removed incorrect await)",
            "Added comprehensive AI-optimization guide (SCREENSHOT_OPTIMIZATION.md)",
            "Recommended JPEG Q75 for 21% size reduction with perfect quality",
            "Tested and benchmarked 4 quality levels for Claude AI",
            "Updated screenshot command description with AI recommendations"
        ]
    },
    "2.18.0": {
        "date": "2025-10-16",
        "description": "Animation timing optimization for human perception",
        "changes": [
            "Increased cursor movement animation to 1000ms (was 400ms)",
            "Increased click flash animation to 1000ms (was 150ms)",
            "Changed scale effect to 1.5x increase (was 0.8x decrease)",
            "Enhanced shadow glow with triple layers (30/60/90px)",
            "User testing confirmed animations now clearly visible"
        ]
    },
    "2.17.0": {
        "date": "2025-10-16",
        "description": "Critical bugs fixed via real browser testing",
        "changes": [
            "Fixed JavaScript SyntaxError in click commands (await in non-async function)",
            "Fixed empty dict {} returns by adding proper error handling",
            "Sequential animation timing (cursor movement, then click flash)",
            "All 29 MCP commands validated with real browser"
        ]
    },
    "2.16.0": {
        "date": "2025-10-15",
        "description": "Phase 8 Polish & Ship - Initial release",
        "changes": [
            "Comprehensive QA testing across 5 pages",
            "15+ MCP tools validated",
            "Documentation updates"
        ]
    }
}
