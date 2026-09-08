"""Import only selected, source-verified images from the public VK group mirror.
No stock images, generated portfolio images, or trend/moodboard photographs.
Run explicitly through the import-assets workflow; requires Pillow.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import json

MIRROR = 'https://amur-studio33.orgs.biz/'
OUT = Path('assets'); OUT.mkdir(exist_ok=True)
RESEARCH = Path('source-details'); RESEARCH.mkdir(exist_ok=True)
class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.images = []; self.text = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script','style'): self.skip += 1
        if tag == 'img': self.images.append(a)
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip = max(0,self.skip-1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.text.append(data.strip())
def read(url):
    req = Request(url, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})
    with urlopen(req, timeout=25) as r: return r.read(12_000_000)

def capture(pair):
    name,url = pair
    try:
        html = read(url).decode('utf-8',errors='replace')
        (RESEARCH/f'{name}.html').write_text(html,encoding='utf-8')
        p = Parser();p.feed(html)
        (RESEARCH/f'{name}.txt').write_text('\n'.join(p.text),encoding='utf-8')
        print('Captured',name,len(html),flush=True)
    except Exception as exc: print('Unavailable',name,str(exc),flush=True)

html = read(MIRROR).decode('utf-8'); parser = Parser(); parser.feed(html)
# Indices match the inspected public mirror snapshot; expected fragments prevent mismatches.
selected = [
 (25,'hero-nails','9y9cqFa6',121),
 (12,'nails-milk','YXwjWA7_',136),
 (11,'nails-french','Gvmb2YBP',136),
 (28,'nails-flower','KfxbpqDX',121),
 (26,'nails-art','bz33GH7o',121),
 (29,'nails-pearl','',121),
 (13,'nails-blue','RMxzn2qp',136),
 (53,'brows','',113),
 (8,'master-varvara','T7YLFsV3',138),
 (10,'master-ksenia','Lg3rj-rV',136),
 (24,'master-anna','b2CikJak',121),
 (0,'salon-mark','ei9Qas8A',None),
]
def import_one(item):
    i,name,expected,post = item
    original = parser.images[i]['src']
    if expected and expected not in original: raise RuntimeError('Source changed: '+name)
    host = urlparse(original).hostname or ''
    if not host.endswith('.userapi.com'): raise ValueError('Non-VK asset rejected')
    parts = urlparse(original); query = parse_qs(parts.query)
    url = original
    if 'as' in query:
        sizes = [tuple(map(int,s.split('x'))) for s in query['as'][0].split(',')]
        width,height = max((s for s in sizes if s[0] <= 1080),key=lambda s:s[0])
        query['cs'] = [f'{width}x{height}']
        url = urlunparse(parts._replace(query=urlencode(query,doseq=True)))
    try: body=read(url)
    except Exception: body=read(original); url=original
    im=ImageOps.exif_transpose(Image.open(BytesIO(body))).convert('RGB')
    original_size=im.size
    im.thumbnail((1100,1500))
    im.save(OUT/f'{name}.webp','WEBP',quality=86,method=6)
    small=im.copy();small.thumbnail((480,650))
    small.save(OUT/f'{name}-sm.webp','WEBP',quality=82,method=6)
    print('Imported',name,original_size,'=>',im.size,flush=True)
    return {'file':f'{name}.webp','thumbnail':f'{name}-sm.webp','width':im.width,'height':im.height,'original':original,'downloaded':url,'source':MIRROR+(f'news/{post}' if post else ''),'primary':'https://vk.com/amur_studio33'}
with ThreadPoolExecutor(max_workers=4) as pool:
    result=list(pool.map(import_one,selected))
(OUT/'sources.json').write_text(json.dumps({'collected':'2026-09-09','notice':'Photographs from the public copy of amur_studio33; publication dates are 2023–2025. Current team and prices require salon approval. Trend collages were deliberately excluded.','images':result},ensure_ascii=False,indent=2),encoding='utf-8')
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(capture,[('brow-price',MIRROR+'product/11164181'),('extension-price',MIRROR+'product/11159434'),('manicure-price',MIRROR+'product/11159399'),('gel-price',MIRROR+'product/11159299'),('dikidi','https://dikidi.net/1006138'),('vk-modern','https://vk.com/amur_studio33')]))
