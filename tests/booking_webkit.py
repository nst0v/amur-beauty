"""Touch/WebKit checks of our own booking UI. No live reservation requests."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import json
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8768),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
results=[]
try:
    with sync_playwright() as p:
        browser=p.webkit.launch()
        for width,height in [(320,740),(390,844),(430,932)]:
            page=browser.new_page(viewport={'width':width,'height':height},is_mobile=True,has_touch=True,locale='ru-RU',reduced_motion='reduce')
            page.set_default_timeout(15000)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.route('https://dikidi.net/ru/record/**',lambda route:route.fulfill(status=200,content_type='text/html',body='<html lang="ru"><body>Read-only calendar layout fixture</body></html>'))
            page.goto('http://127.0.0.1:8768/',wait_until='domcontentloaded')
            page.evaluate('Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,6000))])')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.locator('.hero-actions [data-book]').tap()
            expect(page.locator('#booking-dialog [data-service-id]')).to_have_count(44)
            page.locator('#booking-search').fill('Маникюр с покрытием')
            page.locator('#booking-dialog [data-service-id="13949730"]').tap()
            expect(page.locator('#booking-dialog [data-service-id="13949730"]')).to_have_attribute('aria-checked','true')
            page.locator('.bk-next').tap()
            page.locator('#booking-dialog [data-master-id="4295706"]').tap()
            expect(page.locator('.bk-footer-copy')).to_contain_text('Яна')
            page.locator('.bk-next').tap()
            expect(page.locator('#booking-calendar')).to_have_count(1)
            box=page.locator('#booking-calendar').bounding_box()
            assert box and box['width']<=width and box['height']<=height-280
            assert not page.evaluate('document.getElementById("booking-dialog").scrollWidth>document.getElementById("booking-dialog").clientWidth+1')
            page.locator('[data-bk-close]').tap()
            expect(page.locator('#booking-dialog')).not_to_be_visible()
            expect(page.locator('.hero-actions [data-book]')).to_be_focused()
            assert not errors,errors
            results.append({'width':width,'height':height,'status':'passed','errors':errors})
            page.close();print('PASS WebKit touch',width,flush=True)
        browser.close()
finally:
    (OUT/'webkit-booking-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    server.shutdown()
