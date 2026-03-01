from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Login first
    page.goto('http://127.0.0.1:8000/accounts/login/')
    page.fill('input[name="username"]', 'zakee')
    page.fill('input[name="password"]', 'z')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    # Go to the interactive contract page
    page.goto('http://127.0.0.1:8000/manufacturing/orders/16801/interactive-contract/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)
    
    # Check computed style of progress bar and all parents
    result = page.evaluate('''() => {
        const bar = document.getElementById('progressBarContainer');
        if (!bar) return {error: 'not found'};
        const style = window.getComputedStyle(bar);
        
        let parents = [];
        let el = bar.parentElement;
        while (el) {
            const ps = window.getComputedStyle(el);
            parents.push({
                tag: el.tagName,
                id: el.id || '',
                cls: (el.className || '').toString().substring(0, 80),
                transform: ps.transform,
                filter: ps.filter,
                willChange: ps.willChange,
                contain: ps.contain,
                backdropFilter: ps.backdropFilter,
                perspective: ps.perspective,
                overflow: ps.overflow,
            });
            el = el.parentElement;
        }
        return {
            bar: {
                position: style.position,
                top: style.top,
                left: style.left,
                right: style.right,
                zIndex: style.zIndex,
                transform: style.transform,
                parentTag: bar.parentElement ? bar.parentElement.tagName : 'none',
                parentId: bar.parentElement ? bar.parentElement.id : '',
            },
            parents: parents
        };
    }''')
    print(json.dumps(result, indent=2))
    browser.close()
