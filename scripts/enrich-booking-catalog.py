"""Enrich the public catalog with each specialist's actual booking offerings."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime,timezone
import json

path=Path('data/catalog.json');catalog=json.loads(path.read_text(encoding='utf-8'))
known={s['id']:s for s in catalog['services']}
for service in known.values():service['offerings']={}

def read_master(master):
    url='https://dikidi.net/ru/record/1006138?'+urlencode({'st_m':'1','sm_m':master['id']})
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU,ru;q=0.9'})
    with urlopen(req,timeout=30) as response:soup=BeautifulSoup(response.read().decode('utf-8'),'html.parser')
    groups=None
    for node in soup.select('[data-options]'):
        try:
            options=json.loads(node['data-options'])
            if options.get('step_data',{}).get('list'):groups=options['step_data']['list'];break
        except ValueError:pass
    if groups is None:raise RuntimeError('Public specialist catalog unavailable: '+master['id'])
    ids=[];offerings={}
    for group in groups:
        for raw in group.get('services',[]):
            ident=str(raw['company_service_id'])
            if ident not in known:raise RuntimeError('New service not in catalog: '+ident)
            ids.append(ident)
            offerings[ident]={'price':raw['price'],'priceFrom':bool(raw.get('floating')),'durationMinutes':raw['time']}
    print(master['name'],len(ids),'confirmed services',flush=True)
    master['serviceIds']=ids
    master['offeringsSource']=url
    return master['id'],offerings

with ThreadPoolExecutor(max_workers=3) as pool:
    for master_id,offerings in pool.map(read_master,catalog['masters']):
        for ident,offering in offerings.items():known[ident]['offerings'][master_id]=offering
for service in known.values():
    service['masterIds']=list(service['offerings'])
    if not service['masterIds']:raise RuntimeError('No actual booking offering for '+service['id'])
    service['durationMinutes']=min(o['durationMinutes'] for o in service['offerings'].values())
    service['maxDurationMinutes']=max(o['durationMinutes'] for o in service['offerings'].values())
catalog['fetchedAt']=datetime.now(timezone.utc).isoformat()
catalog['verifiedOfferingCount']=sum(len(s['offerings']) for s in catalog['services'])
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('Validated',len(catalog['services']),'services',len(catalog['masters']),'masters',catalog['verifiedOfferingCount'],'relationships',flush=True)
