"""End-to-end checks against the actual static site, without making appointments.
Run: pip install playwright && playwright install chromium && python tests/browser_check.py
"""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
from html.parser import HTMLParser
import json
import os
import traceback
import zipfile
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',8765),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
report={'commit':os.getenv('GITHUB_SHA','local'),'viewports':[],'public_url':'https://nst0v.github.io/amur-beauty/'}

class StaticCheck(HTMLParser):
    def __init__(self): super().__init__();self.ids=[];self.hashes=[];self.files=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if tag=='a' and a.get('href','').startswith('#'): self.hashes.append(a['href'][1:])
        if tag in ['img','link','script']:
            path=a.get('src',a.get('href',''))
            if path.startswith('./'): self.files.append(path[2:].split('?',1)[0])
        if a.get('data-image'): self.files.append('assets/'+a['data-image']+'.webp')
static=StaticCheck();static.feed((ROOT/'index.html').read_text())
assert len(static.ids)==len(set(static.ids)),'Duplicate HTML IDs'
assert all(h and h in static.ids for h in static.hashes),'Broken internal anchors'
assert all((ROOT/f).is_file() for f in static.files),'Missing local asset'

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for width,height in [(320,740),(360,800),(390,844),(430,932),(768,1024),(1024,900),(1440,1000)]:
            page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce',is_mobile=width<=600,has_touch=width<=600)
            page.set_default_timeout(12000)
            errors=[];local_failures=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:local_failures.append(r.url) if r.url.startswith('http://127.0.0.1') and r.status>=400 else None)
            page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded')
            page.evaluate('Promise.race([document.fonts.ready.then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),10000))])')
            expect(page.locator('h1')).to_have_count(1)
            expect(page.locator('html')).to_have_attribute('lang','ru')
            assert page.locator('meta[name="robots"]').get_attribute('content')=='noindex, nofollow'
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'),f'Horizontal overflow at {width}'
            # Eager images are used only to capture the full-page preview.
            page.locator('img[src]').evaluate_all('images=>images.forEach(img=>img.loading="eager")')
            page.wait_for_function("""Array.from(document.images).filter(img=>img.getAttribute('src')?.startsWith('./')).every(img=>img.complete&&img.naturalWidth>0)""")
            if width in [390,1440]:
                page.wait_for_timeout(1000)
                page.screenshot(path=str(OUT/f'preview-{width}.png'),full_page=True)
            expect(page.locator('.work-card:visible')).to_have_count(4)
            # Full catalog and booking steps are covered by booking_smoke.py.
            page.locator('[data-filter="brows"]').click()
            expect(page.locator('.work-card:visible')).to_have_count(1)
            page.locator('.work-card:visible').click()
            expect(page.locator('#lightbox')).to_be_visible()
            page.wait_for_function('document.getElementById("lightbox-image").naturalWidth>0')
            expect(page.locator('#lightbox-count')).to_have_text('1 / 1')
            expect(page.locator('#lightbox-next')).to_be_hidden()
            page.keyboard.press('Escape')
            page.locator('[data-filter="all"]').click()
            page.locator('#show-more').click()
            expect(page.locator('.work-card:visible')).to_have_count(8)
            page.locator('.work-card').first.click()
            page.wait_for_function('document.getElementById("lightbox-image").naturalWidth>0')
            page.keyboard.press('ArrowRight')
            expect(page.locator('#lightbox-count')).to_have_text('2 / 8')
            page.keyboard.press('ArrowLeft')
            expect(page.locator('#lightbox-count')).to_have_text('1 / 8')
            page.keyboard.press('Escape')
            if width<=820:
                page.locator('.menu-toggle').click()
                expect(page.locator('#menu-dialog')).to_be_visible()
                page.locator('#menu-dialog a[href="#contacts"]').click()
                expect(page.locator('#menu-dialog')).not_to_be_visible()
            page.locator('.faq-list summary').first.click()
            assert page.locator('.faq-list details').first.get_attribute('open') is not None
            page.locator('#demo-info').click()
            expect(page.locator('#demo-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'),f'Overflow after interactions at {width}'
            assert not errors,errors
            assert not local_failures,local_failures
            report['viewports'].append({'width':width,'height':height,'status':'passed','javascript_errors':errors,'local_asset_failures':local_failures})
            print('PASS',width,height,flush=True)
            page.close()
        # Check graceful booking fallback without JavaScript.
        context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        page=context.new_page();page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded')
        expect(page.locator('.hero-actions [data-book]')).to_have_attribute('href','https://dikidi.net/1006138')
        expect(page.locator('.hero-actions [data-book]')).to_be_visible()
        report['no_javascript_booking']='passed'
        browser.close()
    try:
        with urlopen(report['public_url'],timeout=20) as response:
            html=response.read().decode('utf-8',errors='replace')
            report['public_http_status']=response.status
            report['public_content_matches']='hero-title' in html and 'АМУР' in html
    except Exception as exc:
        report['public_url_check']=str(exc)
    report['status']='passed'
except Exception:
    report['status']='failed';report['failure']=traceback.format_exc();raise
finally:
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    # Portable website copy, with only files used by the demo; no font binaries.
    files={'index.html','styles.css','app.js','.nojekyll','README.md','CONTENT-SOURCES.md','assets/sources.json','booking.js','booking-flow.css','data/catalog.json',*static.files}
    with zipfile.ZipFile(OUT/'amur-beauty-demo.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            if (ROOT/name).is_file():archive.write(ROOT/name,'amur-beauty/'+name)
    server.shutdown()
