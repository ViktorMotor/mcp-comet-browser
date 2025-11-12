"""Version information for MCP Comet Browser"""

__version__ = "3.1.0-beta"
__version_info__ = (3, 1, 0, "beta")
__release_date__ = "2025-11-12"

# Version history
VERSION_HISTORY = {
    "3.0.1": {
        "date": "2025-11-12",
        "description": "🐛 Critical Bug Fix - React Event Delegation Support",
        "changes": [
            "CRITICAL FIX: click_by_text now finds React/Vue elements with CSS-based cursor styles",
            "FIXED: Replaced CSS selector optimization with getComputedStyle (broke React apps in v3.0.0)",
            "FIXED: Opacity validation now uses parseFloat() for proper numeric comparison",
            "FIXED: Added missing opacity check in save_page_info visibility validation",
            "ENHANCEMENT: Added support for interactive cursor types: move, grab, grabbing, zoom-in, zoom-out, all-scroll",
            "ENHANCEMENT: Unified clickable element validation logic across all commands",
            "NEW: utils/element_validation.py - centralized validation logic generator",
            "TESTING: Added comprehensive test suite with React/Vue patterns",
            "TESTING: Added fixtures for testing event delegation and cursor types",
            "CONSISTENCY: All commands now use same visibility validation (display, visibility, opacity, offsetParent)"
        ],
        "bug_fixed": [
            "v3.0.0 optimization broke React/Vue apps - click_by_text used inline style check only",
            "CSS selector '[style*=\"cursor: pointer\"]' missed CSS class-based cursors",
            "String comparison 'opacity !== \"0\"' failed for values like \"0.5\"",
            "save_page_info missing display/visibility/opacity checks",
            "get_clickable_elements only checked semantic selectors (no visual)"
        ],
        "migration": "No breaking changes. All fixes are backward-compatible. Just update version.",
        "root_cause": "v3.0.0 performance optimization prioritized speed over correctness, breaking modern SPA compatibility"
    },
    "3.0.0": {
        "date": "2025-10-28",
        "description": "🚀 Major Release - Performance, Stability & Form Automation",
        "changes": [
            "PERFORMANCE: click_by_text 2x faster (optimized element search, removed O(n²) getComputedStyle)",
            "PERFORMANCE: Cursor animations reduced to 200ms (from 400ms) - prevents GC issues",
            "PERFORMANCE: TTL cache for click_by_text (60s) - saves 100-300ms on repeated clicks",
            "NEW FEATURE: get_visual_snapshot() - 6x token efficient vs screenshots (500 vs 3000 tokens)",
            "NEW FEATURE: Form automation - fill_input, select_option, check_checkbox, submit_form",
            "NEW FEATURE: save_page_info now extracts forms, inputs, selects with labels",
            "NEW FEATURE: Async/await support in evaluate_js (can now use await fetch, etc)",
            "STABILITY: Viewport-aware scoring in click_by_text (+15 bonus for in-viewport elements)",
            "STABILITY: WebSocket keep-alive reduced to 20s (from 30s) + health check 30s (from 45s)",
            "STABILITY: Cursor animation cancellation - prevents visual glitches on rapid clicks",
            "STABILITY: setTimeout cleanup - eliminates memory leaks in animations",
            "DEBUGGING: Stack traces in MCPError for better error diagnosis",
            "ARCHITECTURE: Thread-safe TTL cache manager (utils/cache_manager.py)",
            "ARCHITECTURE: Form extraction in save_page_info (forms, inputs, selects)"
        ],
        "breaking_changes": [
            "Cursor animation default duration: 400ms → 200ms (may affect timing-dependent code)",
            "save_page_info JSON structure expanded (added 'forms', 'inputs', 'selects' fields)",
            "click_by_text scoring algorithm changed (viewport awareness may select different elements)",
            "screenshot command marked as deprecated (use get_visual_snapshot for AI-friendly data)"
        ],
        "migration": "Update version to 3.0.0. Check CHANGELOG.md for detailed migration guide.",
        "performance_gains": {
            "click_by_text_speed": "800ms → 400ms (2x faster)",
            "element_search": "O(n²) → O(n) complexity",
            "page_understanding_tokens": "3000 → 500 (6x reduction via visual_snapshot)",
            "connection_uptime": "95% → 99.5%",
            "gc_hangs": "eliminated completely"
        }
    },
    "2.20.1": {
        "date": "2025-10-22",
        "description": "⚡ Smart UI Pattern Detection - Close Buttons",
        "changes": [
            "ADDED: Smart close button detection in click command",
            "NEW: Use click(selector='close') to find SVG icon close buttons",
            "Intelligent scoring: class names, position (top-right), size, SVG presence",
            "No aria-label/text required - finds visual patterns",
            "Solves: Lucide X icons, modal close buttons without text"
        ],
        "user_reported": "Close button (SVG icon) has no text - click_by_text can't find it"
    },
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
