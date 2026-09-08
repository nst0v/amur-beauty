"""Collect public salon source material for the requested demo. No authentication.
Raw research is an Actions artifact, not part of the published website.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
import json
import re

OUT = Path('source-research')
OUT.mkdir(exist_ok=True)
SOURCES = {
    'vk-mobile': 'https://m.vk.ru/amur_studio33',
    'vk-desktop': 'https://vk.com/amur_studio33',
    'vk-mirror': 'https://amur-studio33.orgs.biz/',
    'salon-directory': 'https://vladimir.gdekrasa.ru/studiya-amur',
    'group-directory': 'https://vladimir.vyboruslug.com/turizm/amur_studio33.html',
}
class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images, self.links, self.text = [], [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            for key in ['src','data-src','data-original']:
                if a.get(key): self.images.append({'url': a[key], 'alt': a.get('alt','')})
        if tag == 'meta' and a.get('property') == 'og:image':
            self.images.append({'url': a.get('content',''), 'alt': 'OpenGraph'})
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
    def handle_data(self, data):
        if data.strip(): self.text.append(data.strip())

def read(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; AmurDemoSourceCollector/1.0)'})
    with urlopen(req, timeout=25) as r:
        return r.read(8_000_000), r.headers.get('content-type',''), r.geturl()

report = {}
for name, url in SOURCES.items():
    try:
        body, typ, resolved = read(url)
        html = body.decode('utf-8',errors='replace')
        (OUT / (name + '.html')).write_text(html,encoding='utf-8')
        p = Extract(); p.feed(html)
        (OUT / (name + '.txt')).write_text('\n'.join(p.text),encoding='utf-8')
        report[name] = {'source':url,'resolved':resolved,'type':typ,'bytes':len(body),'images':p.images,'links':p.links}
        print(name, len(body), 'bytes;', len(p.images), 'images')
        if name == 'vk-mirror':
            seen = set()
            for i, image in enumerate(p.images[:60]):
                image_url = urljoin(url,image['url'])
                if image_url in seen or urlparse(image_url).scheme != 'https': continue
                seen.add(image_url)
                try:
                    data, mime, _ = read(image_url)
                    if not mime.startswith('image/') or len(data) < 2000: continue
                    ext = '.png' if 'png' in mime else '.webp' if 'webp' in mime else '.jpg'
                    filename = f'mirror-image-{i:02d}{ext}'
                    (OUT / filename).write_bytes(data)
                    image['file'] = filename
                    print('Image:', filename, len(data), image.get('alt',''))
                except Exception as exc:
                    image['error'] = str(exc)
    except Exception as exc:
        report[name] = {'source':url,'error':str(exc)}
        print(name, type(exc).__name__, str(exc))
(OUT / 'sources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
