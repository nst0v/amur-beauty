"""Read-only smoke test of the provider's supported embedded date/time step.
No time-slot clicks, reservations, login attempts, or appointment submissions.
"""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

OUT=Path('widget-probe');OUT.mkdir(exist_ok=True)
params={'st_m':'1','sm_m':'4295706','ss_s':'13949730','mode':'website','source':'widget','modalId':'amur-readonly-check'}
url='https://dikidi.net/ru/record/1006138?'+urlencode(params)
results={'url':url}
req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU'})
with urlopen(req,timeout=30) as r:
    soup=BeautifulSoup(r.read().decode('utf-8'),'html.parser')
    results['headers']={k:v for k,v in r.headers.items() if k.lower()!='set-cookie'}
for el in soup.select('[data-options]'):
    try:
        opt=json.loads(el['data-options'])
        results['stacks']=opt.get('stacks');results['mode']=opt.get('mode')
        results['selection']=opt.get('dialog_data');results['stepDataKeys']=list(opt.get('step_data',{}))
    except ValueError:pass
(OUT/'host.html').write_text('<!doctype html><html lang="ru"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0"><iframe title="Выбор даты и времени" src="'+url.replace('&','&amp;')+'" style="display:block;width:100%;height:850px;border:0"></iframe></body></html>')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8766),partial(Quiet,directory=str(OUT)))
Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':390,'height':844},locale='ru-RU')
        errors=[];responses=[];messages=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.expose_function('probeMessage',lambda event:messages.append(event))
        page.add_init_script("window.addEventListener('message',e=>{try{window.probeMessage({origin:e.origin,data:e.data})}catch{}})")
        def guard(route):
            u=route.request.url.lower()
            if 'reservation' in u or '/newrecord/final' in u or route.request.method not in ('GET','HEAD','OPTIONS'):
                route.abort();return
            route.continue_()
        page.route('**/*',guard)
        def capture(response):
            if '/newrecord/' in response.url and any(x in response.url for x in ['get_date','get_time']):
                try:responses.append({'url':response.url,'status':response.status,'headers':response.headers,'data':response.json()})
                except Exception:pass
        page.on('response',capture)
        page.goto('http://127.0.0.1:8766/host.html',wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(18000)
        frame=page.frames[1]
        results['frameUrl']=frame.url
        results['frameText']=frame.locator('body').inner_text(timeout=10000)
        results['frameHtml']=frame.locator('body').inner_html(timeout=10000)
        results['errors']=errors;results['messages']=messages;results['timeResponses']=responses
        page.screenshot(path=str(OUT/'calendar-mobile.png'),full_page=True)
        browser.close()
finally:
    results.pop('frameHtml',None)
    (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    server.shutdown()
print('Embedded calendar probe saved',flush=True)
