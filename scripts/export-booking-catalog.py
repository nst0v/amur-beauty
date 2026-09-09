"""Export the salon's complete public catalog; never submit or reserve appointments."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from io import BytesIO
from bs4 import BeautifulSoup
from PIL import Image,ImageOps
import json,re,time

BASE='https://dikidi.net';COMPANY='1006138'
PROFILE=BASE+'/ru/profile/salon_krasoty_amur_1006138'
OUT=Path('catalog-research');OUT.mkdir(exist_ok=True)
DATA=Path('data');DATA.mkdir(exist_ok=True)
ASSETS=Path('assets/team');ASSETS.mkdir(parents=True,exist_ok=True)
def read(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU,ru;q=0.9'})
    with urlopen(req,timeout=30) as r:return r.read(10000000),dict(r.headers)
def page(name,url):
    body,headers=read(url);soup=BeautifulSoup(body.decode('utf-8',errors='replace'),'html.parser');views=[];steps=[]
    for node in soup.select('[data-options]'):
        try:
            opt=json.loads(node['data-options']);step=opt.get('step_data',{})
            if step.get('view'):views.append(step['view'])
            steps.append({k:opt[k] for k in ['stacks','step_data','dialog_data','mode','page_url'] if k in opt})
        except ValueError:pass
    text='\n'.join(views) if views else str(soup)
    (OUT/(name+'.html')).write_text(text,encoding='utf-8')
    (OUT/(name+'.json')).write_text(json.dumps({'source':url,'headers':{k:v for k,v in headers.items() if k.lower()!='set-cookie'},'public_options':steps},ensure_ascii=False,indent=2),encoding='utf-8')
    return BeautifulSoup(text,'html.parser'),steps

def txt(root,selector):
    el=root.select_one(selector)
    return re.sub(r'\s+',' ',el.get_text(' ',strip=True)) if el else ''

def service_rows(soup):
    rows=[];seen=set()
    for el in soup.select('.service'):
        title=el.select_one('a.title[href*="/service/"]')
        if not title:continue
        ident=title['href'].rstrip('/').split('/')[-1]
        if not ident.isdigit() or ident in seen:continue
        price=txt(el,'.price').replace('RUB','₽');duration=txt(el,'.time')
        booking=el.select_one('[data-record]')
        amount=re.search(r'\d[\d\s]*',price)
        rows.append({'id':ident,'name':txt(el,'.title'),'category':txt(el,'.type'),'categoryId':el.get('data-category',''),'price':price,'priceValue':int(re.sub(r'\s','',amount.group())) if amount else None,'priceFrom':'от' in price,'duration':duration,'source':urljoin(BASE,title['href']),'bookingUrl':urljoin(BASE,booking['data-record']) if booking else '', 'masterIds':[]})
        seen.add(ident)
    return rows
home,_=page('home',BASE+'/'+COMPANY)
full,_=page('full-catalog',PROFILE+'/services')
services=service_rows(full)
masters=[]
for el in home.select('.card.masters .master[data-id]'):
    image=el.select_one('img');book=el.select_one('[data-record]')
    masters.append({'id':el['data-id'],'name':txt(el,'.name').capitalize(),'role':txt(el,'.title'),'source':urljoin(BASE,el['href']),'bookingUrl':urljoin(BASE,book['data-record']) if book else '', 'imageSource':urljoin(BASE,image['src']) if image else '', 'image':'','serviceIds':[]})
declared_services=txt(home,'.card.services h3 .count')
declared_masters=txt(home,'.card.masters h3 .count')
if not declared_services:
    for h in home.select('.card h3'):
        if 'Услуги' in h.text:
            count=h.select_one('.count')
            if count:declared_services=count.get_text(strip=True);break
print('Full catalog:',len(services),'services;',len(masters),'masters; declared',declared_services,declared_masters,flush=True)
if len(services)<40 or len(masters)<7:raise RuntimeError('Incomplete public catalog: refusing partial replacement')
if declared_services.isdigit() and int(declared_services)!=len(services):raise RuntimeError('Service count mismatch')
if declared_masters.isdigit() and int(declared_masters)!=len(masters):raise RuntimeError('Master count mismatch')

def service_detail(service):
    soup,opts=page('service-'+service['id'],service['source'])
    ids=[]
    for node in soup.select('.master[data-id],.worker[data-id]'):
        ident=node['data-id']
        if ident in {m['id'] for m in masters} and ident not in ids:ids.append(ident)
    # Also collect public specialist links if the page uses a different card class.
    for node in soup.select('a[href*="/master/"]'):
        ident=node['href'].rstrip('/').split('/')[-1]
        if ident in {m['id'] for m in masters} and ident not in ids:ids.append(ident)
    service['masterIds']=ids
    print('Service',service['id'],service['name'],ids,flush=True)
    time.sleep(.1)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(service_detail,services))

def master_detail(master):
    soup,_=page('master-'+master['id'],master['source'])
    master['serviceIds']=[s['id'] for s in services if master['id'] in s['masterIds']]
    src=master['imageSource']
    if '/assets/' in src:return
    try:
        body,_=read(src);im=ImageOps.exif_transpose(Image.open(BytesIO(body))).convert('RGB');im.thumbnail((480,640))
        target=ASSETS/(master['id']+'.webp');im.save(target,'WEBP',quality=87,method=6);master['image']=str(target)
    except Exception as exc:print('Portrait unavailable',master['name'],str(exc),flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(master_detail,masters))
cat={'schemaVersion':1,'companyId':COMPANY,'fetchedAt':datetime.now(timezone.utc).isoformat(),'source':PROFILE+'/services','declaredCounts':{'services':declared_services,'masters':declared_masters},'services':services,'masters':masters}
(DATA/'catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2),encoding='utf-8')
# Inspect the supported public website widget and its public datetime view only.
checks=[('record-selected',BASE+'/ru/record/1006138?p=0.sd&m=3585520&s=9808072'),('record-master',BASE+'/ru/record/1006138?st_m=1&sm_m=3585520')]
for name,url in checks:
    try:page(name,url)
    except Exception as exc:print(name,str(exc),flush=True)
try:
    body,_=read(BASE+'/assets/js/widget_record/widget2.min.js')
    (OUT/'widget2.min.js').write_bytes(body)
except Exception as exc:print('Widget unavailable',str(exc),flush=True)
