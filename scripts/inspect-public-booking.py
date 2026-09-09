"""Read only public salon pages and the public booking widget, never create a booking."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json

ROOT = Path('booking-research'); ROOT.mkdir(exist_ok=True)
BASE = 'https://dikidi.net'
class Extract(HTMLParser):
    def __init__(self):
        super().__init__(); self.options=[]; self.links=[]; self.scripts=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'data-options' in a:
            try: self.options.append(json.loads(a['data-options']))
            except ValueError: pass
        if tag=='a' and a.get('href'): self.links.append(a['href'])
        if tag=='script' and a.get('src'): self.scripts.append(a['src'])

def read(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU,ru;q=0.9'})
    with urlopen(req,timeout=30) as r:
        return r.read(12000000).decode('utf-8',errors='replace'),dict(r.headers),r.geturl()

def inspect(item):
    name,url=item
    try:
        text,headers,resolved=read(url)
        parsed=Extract();parsed.feed(text)
        views=[];steps=[]
        for options in parsed.options:
            step=options.get('step_data',{})
            if step.get('view'):views.append(step['view'])
            # These fields describe public business information and public navigation only.
            steps.append({k:options[k] for k in ['step_data','step_acronyms','stacks','page_url','direct_link_design','design','mode'] if k in options})
        (ROOT/(name+'.json')).write_text(json.dumps({'source':url,'resolved':resolved,'headers':headers,'links':parsed.links,'scripts':parsed.scripts,'public_options':steps},ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/(name+'.html')).write_text('\n'.join(views) if views else text,encoding='utf-8')
        print(name,len(text),'bytes',len(views),'views',flush=True)
        return parsed
    except Exception as exc:
        print(name,type(exc).__name__,str(exc),flush=True)
        (ROOT/(name+'-error.txt')).write_text(str(exc))

pages=[('home',BASE+'/1006138'),('catalog',BASE+'/ru/profile/salon_krasoty_amur_1006138/services'),('booking',BASE+'/ru/record/1006138')]
with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(inspect,pages))
scripts=set()
for parsed in results:
    if parsed:
        for src in parsed.scripts:
            if any(word in src for word in ['newrecord','widget.js','dialog2','frontend.js','dynamic-2.0']): scripts.add(urljoin(BASE,src))
for i,url in enumerate(sorted(scripts)):
    try:
        text,headers,resolved=read(url)
        (ROOT/('public-'+url.split('/')[-1].split('?')[0])).write_text(text,encoding='utf-8')
        print('Saved public script',url,len(text),flush=True)
    except Exception as exc: print('Script unavailable',url,str(exc),flush=True)
