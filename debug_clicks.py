#!/usr/bin/env python3
"""Debug script to test different click strategies"""
import asyncio
import sys
sys.path.insert(0, '.')

from mcp.protocol import MCPJSONRPCServer

async def test_clicks():
    server = MCPJSONRPCServer()
    await server.initialize()
    
    print("Testing different strategies to click 'Тестирование' tab...")
    print("=" * 60)
    
    # Strategy 1: find_elements
    print("\n1. Finding elements with text 'Тестирование':")
    result = await server.call_tool('find_elements', {
        'text': 'Тестирование',
        'visible_only': True,
        'limit': 10
    })
    print(f"   Found {result.get('count', 0)} elements")
    if result.get('elements'):
        for i, el in enumerate(result['elements'][:3]):
            print(f"   [{i}] {el.get('tagName')} - {el.get('textContent', '')[:50]}")
            print(f"       Selector: {el.get('selector')}")
            print(f"       Attributes: {el.get('attributes', [])[:3]}")
    
    # Strategy 2: get_page_structure
    print("\n2. Getting page structure:")
    structure = await server.call_tool('get_page_structure', {'include_text': True})
    print(f"   Buttons found: {structure.get('counts', {}).get('buttons', 0)}")
    
    # Strategy 3: Try click_by_text
    print("\n3. Trying click_by_text:")
    result = await server.call_tool('click_by_text', {
        'text': 'Тестирование'
    })
    print(f"   Result: {result}")
    
    # Strategy 4: Console command to inspect tabs
    print("\n4. Console inspection of tabs:")
    result = await server.call_tool('console_command', {
        'command': '''
        Array.from(document.querySelectorAll('[role="tab"]'))
            .map((t, i) => ({
                index: i,
                text: t.textContent.trim(),
                selected: t.getAttribute('aria-selected'),
                id: t.id,
                classes: t.className
            }))
        '''
    })
    print(f"   Tabs found: {result}")

if __name__ == '__main__':
    asyncio.run(test_clicks())
