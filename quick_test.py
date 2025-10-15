#!/usr/bin/env python3
"""Quick interactive test of evaluate_js"""
import asyncio
import json
from browser.connection import BrowserConnection
from browser.async_cdp import AsyncCDP
from commands.evaluation import EvaluateJsCommand
from commands.context import CommandContext

async def main():
    # Connect
    browser = BrowserConnection(debug_port=9224)
    await browser.ensure_connected()
    cdp = AsyncCDP(browser.tab)
    context = CommandContext(tab=browser.tab, cdp=cdp, cursor=None, browser=browser)
    cmd = EvaluateJsCommand(context)

    # Quick tests
    tests = [
        ("Page title", "document.title"),
        ("URL", "window.location.href"),
        ("Links count", "document.querySelectorAll('a').length"),
        ("Buttons count", "document.querySelectorAll('button').length"),
        ("Page viewport", "{width: window.innerWidth, height: window.innerHeight}"),
        ("With console", "console.log('Test log'); console.warn('Test warning'); return {message: 'Console captured!'};"),
    ]

    for name, code in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {name}")
        print(f"{'='*60}")
        result = await cmd.execute(code=code)

        if result.get('success'):
            print(f"✅ Success")
            print(f"   Type: {result.get('type')}")
            print(f"   Result: {json.dumps(result.get('result'), ensure_ascii=False)}")
            if result.get('console_output'):
                print(f"   Console: {len(result['console_output'])} messages")
                for log in result['console_output']:
                    print(f"     [{log['level']}] {' '.join(log['args'])}")
        else:
            print(f"❌ Failed: {result.get('error')}")

    print(f"\n{'='*60}")
    print("✅ All tests completed successfully!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
