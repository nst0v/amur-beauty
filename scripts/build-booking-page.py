"""Generate catalog and team from verified source data without touching the hero layout.
No network access. Re-running is deterministic and never fabricates appointments.
"""
from pathlib import Path
from collections import OrderedDict
from html import escape
from urllib.parse import urlencode
import json,re
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
services=data['services'];masters=data['masters'];by_master={m['id']:m for m in masters}
assert len(services)==int(data['declaredCounts']['services'])
assert len(masters)==int(data['declaredCounts']['masters'])
assert all(s.get('offerings') and all(mid in by_master for mid in s['masterIds']) for s in services)
E=lambda value:escape(str(value),quote=True)
def icon(name):return f'<svg class="icon" aria-hidden="true"><use href="#i-{name}"/></svg>'
def duration(n):return (f'{n//60} ч ' if n//60 else '')+(f'{n%60} мин' if n%60 else '')
def group(s):
    category=s['category'].lower();name=s['name'].lower()
    if category=='шугаринг':return 'depilation'
    if category=='массаж':return 'massage'
    if category=='наращивание ресниц':return 'lashes'
    if 'дизайн' in name or 'ремонт' in name:return 'design'
    if 'наращ' in name:return 'extension'
    if 'маникюр' in name:return 'manicure'
    return 'other'
group_names=OrderedDict(manicure='Маникюр',extension='Наращивание',design='Дизайн и ремонт',depilation='Депиляция',massage='Массаж',lashes='Ресницы',other='Другие услуги')
group_names={k:v for k,v in group_names.items() if any(group(s)==k for s in services)}
def url(service_id='',master_id=''):
    params={'st_m':'1' if master_id else '2'}
    if master_id:params['sm_m']=master_id
    if service_id:params['ss_s']=service_id
    return 'https://dikidi.net/ru/record/1006138?'+urlencode(params)
rows=[]
for group_id,name in group_names.items():
    items=[s for s in services if group(s)==group_id]
    html=[]
    for s in items:
        names=', '.join(by_master[mid]['name'] for mid in s['masterIds'])
        time=duration(s['durationMinutes']).strip()
        if s['durationMinutes']!=s['maxDurationMinutes']:time='от '+time
        html.append(f'<a class="catalog-row" href="{E(url(s["id"]))}" data-book data-service-id="{s["id"]}" data-group="{group_id}" data-search="{E(s["name"]+" "+s["category"]+" "+names)}"><div><h3>{E(s["name"])}</h3><small>{E(time)} · {E(names)}</small></div><span>{E(s["price"])}{icon("up")}</span></a>')
    rows.append(f'<details class="catalog-group" data-group="{group_id}" {"open" if group_id in ("manicure","extension") else ""}><summary><span>{name}<span class="catalog-count">{len(items)}</span></span>{icon("plus")}</summary><div>{"".join(html)}</div></details>')
chips=''.join(f'<button class="catalog-chip" type="button" data-category="{key}" aria-pressed="false">{label}</button>' for key,label in group_names.items())
section=f'''<section class="section services-section" id="services" aria-labelledby="services-title"><div class="container">
<div class="section-heading"><div><p class="eyebrow">01 / УСЛУГИ И ЦЕНЫ</p><h2 id="services-title">Услуги и <em>стоимость.</em></h2></div><p class="section-description">{len(services)} услуги в каталоге студии.<br>Выберите услугу, затем мастера и время.</p></div>
<div class="catalog-layout"><aside class="catalog-side"><div class="service-editorial"><img src="./assets/nails-milk.webp" alt="Маникюр с молочным покрытием в студии Амур" width="810" height="1080" loading="lazy"><div><span class="eyebrow">МАНИКЮР В «АМУРЕ»</span><p>Покрытие,<br>наращивание и <em>дизайн.</em></p></div></div></aside>
<div class="catalog-content"><label class="catalog-search">{icon('zoom')}<input id="catalog-search" type="search" placeholder="Найти услугу или мастера" aria-label="Поиск по каталогу услуг" autocomplete="off"></label><div class="catalog-filters" role="group" aria-label="Категории каталога"><button class="catalog-chip" type="button" data-category="all" aria-pressed="true">Все услуги</button>{chips}</div><p class="catalog-status" id="catalog-status" role="status"></p>{''.join(rows)}<p class="bk-empty" id="catalog-empty" hidden>Услуги не найдены. Попробуйте другой запрос.</p><p class="price-note">Каталог обновлён 9 сентября 2026 года. Цена и длительность могут зависеть от мастера — его условия показаны при выборе.</p></div></div></div></section>'''
cards=[]
for m in masters:
    image=f'<img src="./{E(m["image"])}" alt="" width="88" height="100" loading="lazy">' if m['image'] else ''
    role=m['role'][0].upper()+m['role'][1:].lower() if m['role'] else ''
    cards.append(f'<article class="team-card"><div class="team-avatar" aria-hidden="true"><span>{E(m["name"][0])}</span>{image}</div><div class="team-info"><h3>{E(m["name"])}</h3><p class="team-specialty">{E(role)}</p><a class="team-book" href="{E(url(master_id=m["id"]))}" data-book data-master-id="{m["id"]}">Выбрать услуги{icon("arrow")}</a></div></article>')
team=f'''<section class="section team-section" id="team" aria-labelledby="team-title"><div class="container"><div class="section-heading"><div><p class="eyebrow">03 / МАСТЕРА</p><h2 id="team-title">Мастера <em>студии.</em></h2></div><p class="section-description">{len(masters)} мастеров. Выберите специалиста,<br>чтобы посмотреть его услуги и цены.</p></div><div class="team-grid team-grid-complete">{''.join(cards)}</div></div></section>'''
html_path=ROOT/'index.html';html=html_path.read_text(encoding='utf-8')
def replace_section(css,new):
    global html
    pattern=r'<section class="section '+re.escape(css)+r'"[^>]*>.*?</section>'
    html,count=re.subn(pattern,lambda _:new,html,count=1,flags=re.S)
    if count!=1:raise RuntimeError('Section not found: '+css)
replace_section('services-section',section);replace_section('team-section',team)
booking='''<dialog id="booking-dialog" class="booking-dialog" aria-labelledby="booking-title"><div class="bk-body"><h2 id="booking-title">Онлайн-запись</h2><p class="bk-intro">Для выбора на сайте включите JavaScript.</p><a class="button" href="https://dikidi.net/1006138" target="_blank" rel="noopener noreferrer">Открыть форму записи</a></div></dialog>'''
html,count=re.subn(r'<dialog id="booking-dialog".*?</dialog>',lambda _:booking,html,count=1,flags=re.S)
if count!=1:raise RuntimeError('Booking dialog not found')
if 'id="booking-announcement"' not in html:html=html.replace('</body>','<p class="sr-only" id="booking-announcement" role="status" aria-live="polite"></p>\n</body>')
if 'href="./booking-flow.css' not in html:html=html.replace('</head>','  <link rel="stylesheet" href="./booking-flow.css?v=booking-20260909">\n</head>')
if 'src="./booking.js' not in html:html=html.replace('</head>','  <script src="./booking.js?v=booking-20260909" defer></script>\n</head>')
html=html.replace('src="./app.js"','src="./app.js?v=booking-20260909"')
for old,new in {
    'Маникюр и брови<br> в студии':'Салон красоты<br>',
    'Маникюр, педикюр, оформление бровей и другие услуги.':'Маникюр, наращивание ногтей, депиляция и массаж.',
    'Маникюр и педикюр</span>':'Маникюр и наращивание</span>',
    'Брови и ресницы</span>':'Депиляция и массаж</span>',
    'В «Амуре» делают маникюр, педикюр, оформление бровей и другие процедуры.':'В «Амуре» делают маникюр, наращивание ногтей, депиляцию и массаж.',
    'Маникюр · педикюр · брови':'Маникюр · депиляция · массаж',
    'Нажмите «Записаться онлайн», затем выберите услугу, мастера и свободное время. Запись подтверждается во внешней форме онлайн-записи.':'Нажмите «Записаться онлайн». Выберите услугу и мастера на сайте. На третьем шаге откроется встроенный календарь со свободным временем. Завершите запись в этой форме и дождитесь подтверждения.',
    'Перейдите к онлайн-записи и выберите удобное свободное время.':'Выберите услугу и мастера. Свободное время появится в календаре на следующем шаге.',
    'Фотографии работ и основной прайс взяты из доступных публикаций':'Фотографии работ взяты из доступных публикаций',
    'Актуальность цен и услуг перед запуском нужно подтвердить у студии.':'Полный каталог услуг и мастеров обновлён из открытой формы записи 9 сентября 2026 года.',
    'Кнопки записи открывают внешнюю форму онлайн-записи. Сайт не хранит персональные данные.':'Услуга и мастер выбираются на сайте. Календарь и подтверждение встроены из действующей системы записи салона. Данные для записи обрабатывает эта система, а не сайт.',
    'С любовью<br> <em>к деталям.</em>':'О <em>демоверсии.</em>',
    'АМУР — красота с любовью к себе':'АМУР — салон красоты во Владимире',
}.items():html=html.replace(old,new)
# Retain the existing gallery; the new booking module owns its dialog lifecycle.
js_path=ROOT/'app.js';js=js_path.read_text(encoding='utf-8')
if 'const SERVICES = [' in js:
    marker="  const cards = $$('.work-card');"
    if marker not in js:raise RuntimeError('Cannot locate gallery code; refusing destructive rewrite')
    head='''(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const menu = $('#menu-dialog');
  const lightbox = $('#lightbox');
  let restoreFocus = null;
  function openDialog(dialog, trigger) {
    if (!dialog || typeof dialog.showModal !== 'function') return false;
    const previous = $('dialog[open]');
    if (previous && previous !== dialog) previous.close();
    restoreFocus = trigger || document.activeElement;
    dialog.showModal();
    return true;
  }
  $$('dialog:not(#booking-dialog)').forEach(dialog => {
    $$('[data-close]', dialog).forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
      if (dialog === lightbox) $('#lightbox-image').removeAttribute('src');
      if (restoreFocus && document.contains(restoreFocus) && !$('dialog[open]')) restoreFocus.focus({ preventScroll: true });
    });
  });
  $('.menu-toggle').addEventListener('click', event => openDialog(menu, event.currentTarget));
  $$('nav a', menu).forEach(anchor => anchor.addEventListener('click', () => menu.close()));
  $('#demo-info').addEventListener('click', event => openDialog($('#demo-dialog'), event.currentTarget));

'''
    js_path.write_text(head+js[js.index(marker):],encoding='utf-8')
html_path.write_text(html,encoding='utf-8')
# Retain gallery/navigation checks; booking_smoke.py replaces obsolete hardcoded-tab tests.
test_path=ROOT/'tests/browser_check.py';test=test_path.read_text(encoding='utf-8')
test=test.replace("self.files.append(path[2:])", "self.files.append(path[2:].split('?',1)[0])")
start="            page.locator('#tab-brows').click()"
end="            page.locator('[data-filter=\"brows\"]').click()"
if start in test and end in test:
    begin=test.index(start);finish=test.index(end,begin)
    test=test[:begin]+"            # Full catalog and booking steps are covered by booking_smoke.py.\n"+test[finish:]
test=test.replace("'assets/sources.json',*static.files}","'assets/sources.json','booking.js','booking-flow.css','data/catalog.json',*static.files}")
test_path.write_text(test,encoding='utf-8')
print('Generated catalog:',len(services),'services,',len(masters),'masters')
