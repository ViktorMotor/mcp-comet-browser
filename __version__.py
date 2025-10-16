"""Version information for MCP Comet Browser"""

__version__ = "2.18.0"
__version_info__ = (2, 18, 0)
__release_date__ = "2025-10-16"

# Version history
VERSION_HISTORY = {
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
