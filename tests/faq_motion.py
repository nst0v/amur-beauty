"""FAQ motion regression tests; no booking requests or external writes.

Run after installing Playwright browsers:
    python3 tests/faq_motion.py
Use FAQ_BROWSERS=chromium and PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH for a local browser.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
import re
import traceback

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}/'
report = {'status': 'running', 'checks': []}


def load_page(page):
    if not os.getenv('FAQ_INLINE'):
        page.goto(base, wait_until='load')
        return
    # Offline rendering for environments where the browser cannot visit localhost.
    markup = (ROOT / 'index.html').read_text(encoding='utf-8')
    scripts = []
    def inline_style(match):
        name = match.group(1).split('?')[0]
        return '<style>' + (ROOT / name).read_text(encoding='utf-8') + '</style>'
    def inline_script(match):
        name = match.group(1).split('?')[0]
        scripts.append((ROOT / name).read_text(encoding='utf-8'))
        return ''
    markup = re.sub(r'<link[^>]+href="\./([^"?]+(?:\?[^" ]*)?\.css[^" ]*|[^" ]+\.css[^" ]*)"[^>]*>', inline_style, markup)
    markup = re.sub(r'<script[^>]+src="\./([^"]+)"[^>]*></script>', inline_script, markup)
    markup = markup.replace('</body>', ''.join('<script>' + script + '</script>' for script in scripts) + '</body>')
    page.set_content(markup, wait_until='load')


def settle(page):
    page.wait_for_function("""() => [...document.querySelectorAll('.faq-list details')]
        .every(item => item.getAnimations({subtree:true}).length === 0)""")


def half_frame(item):
    return item.evaluate("""async element => {
        const animations = element.getAnimations({subtree:true});
        if (!animations.length) throw new Error('No FAQ animation started');
        for (const animation of animations) {
            animation.pause();
            animation.currentTime = animation.effect.getTiming().duration / 2;
        }
        await new Promise(resolve => requestAnimationFrame(resolve));
        return {height: element.getBoundingClientRect().height,
            opacity: Number(getComputedStyle(element.querySelector('summary + div')).opacity),
            open: element.open};
    }""")


def resume(item):
    item.evaluate('element => element.getAnimations({subtree:true}).forEach(animation => animation.play())')


try:
    with sync_playwright() as pw:
        for browser_name in os.getenv('FAQ_BROWSERS', 'chromium,webkit').split(','):
            options = {'headless': True}
            executable = os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
            if browser_name == 'chromium' and executable:
                options['executable_path'] = executable
            browser = getattr(pw, browser_name).launch(**options)
            for width, height in [(320, 740), (390, 844), (768, 1024), (1440, 1000)]:
                page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='no-preference')
                page.set_default_timeout(8000)
                # FAQ does not use external services. Keep the test deterministic/offline.
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                load_page(page)
                page.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
                items = page.locator('.faq-list details')
                expect(items).to_have_count(4)
                first, second = items.nth(0), items.nth(1)
                summary = first.locator('summary')
                expect(summary).to_have_attribute('aria-expanded', 'false')
                summary.scroll_into_view_if_needed()
                closed = first.bounding_box()['height']

                summary.click()
                opening = half_frame(first)
                assert opening['open'] and opening['height'] > closed + 1, opening
                assert 0 < opening['opacity'] < 1, opening
                resume(first)
                settle(page)
                opened = first.bounding_box()['height']
                assert closed < opening['height'] < opened - 0.5, (closed, opening, opened)
                expect(summary).to_have_attribute('aria-expanded', 'true')
                assert first.evaluate("el => el.style.height === '' && el.style.overflow === ''")
                assert first.locator('summary + div').bounding_box()['height'] > 20
                if width == 390:
                    page.locator('.faq-section').screenshot(path=str(OUT / f'faq-open-{browser_name}.png'))

                summary.click()
                closing = half_frame(first)
                assert closing['open'] and closed < closing['height'] < opened, closing
                assert 0 < closing['opacity'] < 1, closing
                expect(summary).to_have_attribute('aria-expanded', 'false')
                resume(first)
                settle(page)
                assert not first.evaluate('el => el.open')
                assert abs(first.bounding_box()['height'] - closed) < 1

                # Both native activation keys must retain focus and work with animation.
                summary.focus()
                page.keyboard.press('Enter')
                settle(page)
                expect(summary).to_have_attribute('aria-expanded', 'true')
                expect(summary).to_be_focused()
                page.keyboard.press('Space')
                settle(page)
                expect(summary).to_have_attribute('aria-expanded', 'false')

                # Reverse in-flight opening twice; no jumps, orphan animations or stuck heights.
                first.evaluate("""async el => {
                    const button = el.querySelector('summary');
                    button.click();
                    await new Promise(resolve => setTimeout(resolve, 80));
                    button.click();
                    await new Promise(resolve => setTimeout(resolve, 50));
                    button.click();
                }""")
                settle(page)
                assert first.evaluate("el => el.open && el.style.height === ''")
                second.locator('summary').click()
                settle(page)
                assert first.evaluate('el => el.open') and second.evaluate('el => el.open')

                # Reflow during closing/opening: measure the new natural height, then release it.
                summary.click()
                page.set_viewport_size({'width': width + 35, 'height': height})
                settle(page)
                assert not first.evaluate('el => el.open')
                summary.click()
                page.set_viewport_size({'width': width, 'height': height})
                settle(page)
                assert first.evaluate("el => el.open && el.style.height === ''")
                delta = first.evaluate("""el => el.getBoundingClientRect().bottom -
                    el.querySelector('summary + div').getBoundingClientRect().bottom""")
                assert delta >= -1, 'Answer clipped after resizing'

                # Turning motion off mid-transition must immediately settle the requested state.
                summary.click()
                page.emulate_media(reduced_motion='reduce')
                settle(page)
                assert not first.evaluate('el => el.open')
                summary.click()
                assert first.evaluate("el => el.open && el.getAnimations({subtree:true}).length === 0")
                expect(summary).to_have_attribute('aria-expanded', 'true')
                summary.click()
                assert not first.evaluate('el => el.open')
                assert not errors, errors
                report['checks'].append({'browser': browser_name, 'width': width, 'status': 'passed'})
                page.close()

            # Without JavaScript (or animation support), native disclosure still works.
            for fallback in ['no-javascript', 'no-animation-api']:
                context = browser.new_context(java_script_enabled=fallback != 'no-javascript')
                if fallback == 'no-animation-api':
                    context.add_init_script('Element.prototype.animate = undefined;')
                page = context.new_page()
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                load_page(page)
                item = page.locator('.faq-list details').first
                item.locator('summary').click()
                expect(item).to_have_attribute('open', '')
                item.locator('summary').click()
                expect(item).not_to_have_attribute('open', '')
                report['checks'].append({'browser': browser_name, 'fallback': fallback, 'status': 'passed'})
                context.close()
            browser.close()
    report['status'] = 'passed'
    print(json.dumps(report, ensure_ascii=False, indent=2))
except Exception:
    report['status'] = 'failed'
    report['failure'] = traceback.format_exc()
    raise
finally:
    (OUT / 'faq-motion-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    server.shutdown()
