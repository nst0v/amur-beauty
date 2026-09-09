"""On-site booking checks. No appointments, reservations or SMS are submitted."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
import json,traceback
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
data=json.loads((ROOT/'data/catalog.json').read_text())
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8767),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
results={'viewports':[],'liveCalendar':None}
def geometry(page):
 return page.evaluate("""Array.from(document.querySelectorAll('body *')).filter(el=>el.getBoundingClientRect().right>innerWidth+1).map(el=>({tag:el.tagName,cls:el.className,text:el.textContent.slice(0,80),right:el.getBoundingClientRect().right,width:el.getBoundingClientRect().width})).slice(0,35)""")
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width,height in [(320,740),(360,800),(390,844),(430,932),(768,1024),(1024,900),(1440,1000)]:
   page=browser.new_page(viewport={'width':width,'height':height},locale='ru-RU',reduced_motion='reduce')
   page.set_default_timeout(12000);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('https://dikidi.net/ru/record/**',lambda route:route.fulfill(status=200,content_type='text/html',body='<html lang="ru"><body>Изолированная проверка контейнера календаря</body></html>'))
   page.goto('http://127.0.0.1:8767/',wait_until='domcontentloaded')
   page.evaluate('Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,6000))])')
   expect(page.locator('.catalog-row')).to_have_count(44)
   expect(page.locator('.team-grid-complete .team-card')).to_have_count(7)
   if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
    page.screenshot(path=str(OUT/f'overflow-{width}.png'),full_page=True)
    results['overflow']=geometry(page);print(json.dumps(results['overflow'],ensure_ascii=False),flush=True)
    raise AssertionError(f'Page overflow at {width}')
   page.locator('.hero-actions [data-book]').click()
   expect(page.locator('#booking-title')).to_have_text('Выберите услугу')
   expect(page.locator('#booking-dialog [data-service-id]')).to_have_count(44)
   expect(page.locator('.bk-next')).to_be_disabled()
   if width in [390,1440]:page.screenshot(path=str(OUT/f'booking-services-{width}.png'))
   page.locator('#booking-search').fill('несуществующий запрос')
   expect(page.locator('#booking-dialog .bk-empty')).to_be_visible()
   page.locator('#booking-search').fill('Маникюр с покрытием')
   expect(page.locator('#booking-dialog [data-service-id]')).to_have_count(1)
   page.locator('#booking-dialog [data-service-id="13949730"]').click()
   expect(page.locator('#booking-dialog [data-service-id="13949730"]')).to_have_attribute('aria-checked','true')
   expect(page.locator('#booking-title')).to_have_text('Выберите услугу')
   page.locator('.bk-next').click()
   expect(page.locator('#booking-title')).to_have_text('Выберите мастера')
   offering=next(s for s in data['services'] if s['id']=='13949730')
   ids=page.locator('.bk-master-option').evaluate_all('(els)=>els.map(el=>el.dataset.masterId)')
   assert set(ids)==set(offering['masterIds'])
   expect(page.locator('.bk-next')).to_be_disabled()
   page.locator('#booking-dialog [data-master-id="4295706"]').click()
   expect(page.locator('#booking-title')).to_have_text('Выберите мастера')
   expect(page.locator('.bk-footer-copy')).to_contain_text('Яна')
   assert str(offering['offerings']['4295706']['price']) in page.locator('.bk-footer-copy strong').inner_text().replace('\u00a0','').replace(' ','')
   if width in [390,1440]:page.screenshot(path=str(OUT/f'booking-masters-{width}.png'))
   page.locator('.bk-next').click()
   expect(page.locator('#booking-calendar')).to_have_count(1)
   params=parse_qs(urlparse(page.locator('#booking-calendar').get_attribute('src')).query)
   assert params['ss_s']==['13949730'] and params['sm_m']==['4295706'] and params['mode']==['website']
   assert page.url.startswith('http://127.0.0.1:8767/')
   assert not page.evaluate('document.getElementById("booking-dialog").scrollWidth>document.getElementById("booking-dialog").clientWidth+1')
   page.locator('[data-edit-master]').click()
   expect(page.locator('#booking-dialog [data-master-id="4295706"]')).to_have_attribute('aria-checked','true')
   page.keyboard.press('Escape')
   expect(page.locator('#booking-dialog')).not_to_be_visible()
   expect(page.locator('.hero-actions [data-book]')).to_be_focused()
   page.locator('.team-book[data-master-id="4120856"]').click()
   expect(page.locator('.bk-master-filter')).to_contain_text('Кристина')
   visible=page.locator('#booking-dialog [data-service-id]').evaluate_all('(els)=>els.map(el=>el.dataset.serviceId)')
   person=next(m for m in data['masters'] if m['id']=='4120856')
   assert set(visible)==set(person['serviceIds'])
   page.locator('#booking-dialog [data-service-id]').first.click();page.locator('.bk-next').click()
   expect(page.locator('#booking-dialog [data-master-id="4120856"]')).to_have_attribute('aria-checked','true')
   page.keyboard.press('Escape')
   page.locator('#catalog-search').fill('Яна')
   assert page.locator('.catalog-row:visible').count()>0
   page.locator('#catalog-search').fill('неттакойуслуги');expect(page.locator('#catalog-empty')).to_be_visible()
   page.locator('#catalog-search').fill('')
   if width<=820:
    page.locator('.menu-toggle').click();page.locator('#menu-dialog [data-book]').click()
    expect(page.locator('#booking-dialog')).to_be_visible();page.keyboard.press('Escape')
    expect(page.locator('.menu-toggle')).to_be_focused()
   assert not errors,errors
   results['viewports'].append({'width':width,'status':'passed','errors':errors})
   page.close();print('PASS booking',width,flush=True)
  # Separate read-only network test, without calendar fixtures.
  page=browser.new_page(viewport={'width':390,'height':844},locale='ru-RU',reduced_motion='reduce')
  page.set_default_timeout(25000);requests=[]
  def guard(route):
   request=route.request;u=request.url.lower()
   if 'dikidi.net' in u:
    requests.append({'url':request.url,'method':request.method})
    if request.method not in ('GET','HEAD','OPTIONS') or 'reservation' in u or '/newrecord/final' in u:route.abort();return
   route.continue_()
  page.route('**/*',guard)
  page.goto('http://127.0.0.1:8767/',wait_until='domcontentloaded')
  page.locator('.hero-actions [data-book]').click();page.locator('#booking-search').fill('Маникюр с покрытием')
  page.locator('#booking-dialog [data-service-id="13949730"]').click();page.locator('.bk-next').click()
  page.locator('#booking-dialog [data-master-id="4295706"]').click();page.locator('.bk-next').click()
  frame=page.frame_locator('#booking-calendar')
  expect(frame.locator('body')).to_contain_text('Дата и время',timeout=40000)
  expect(frame.locator('body')).to_contain_text('Яна',timeout=25000)
  expect(page.locator('.bk-calendar-loader')).to_be_hidden(timeout=25000)
  assert page.url.startswith('http://127.0.0.1:8767/')
  page.screenshot(path=str(OUT/'booking-calendar-mobile.png'))
  results['liveCalendar']={'status':'passed','parentUrl':page.url,'frameUrl':page.locator('#booking-calendar').get_attribute('src'),'text':frame.locator('body').inner_text(),'appointmentActionsPerformed':False,'networkRequests':requests}
  print('PASS live calendar: actual service and master; no appointment submitted',flush=True)
  browser.close()
except Exception:
 results['failure']=traceback.format_exc()
 raise
finally:
 (OUT/'booking-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 server.shutdown()
