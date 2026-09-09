/* Public catalog selection on this site; live availability stays in the supported booking widget. */
(() => {
  'use strict';
  const dialog = document.getElementById('booking-dialog');
  if (!dialog) return;
  const $ = (selector, root = dialog) => root.querySelector(selector);
  const $$ = (selector, root = dialog) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const icon = name => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  const normalize = value => String(value).toLocaleLowerCase('ru').replace(/ё/g, 'е').trim();
  const money = amount => `${new Intl.NumberFormat('ru-RU').format(amount)} ₽`;
  const duration = minutes => `${Math.floor(minutes / 60) ? `${Math.floor(minutes / 60)} ч` : ''}${minutes % 60 ? ` ${minutes % 60} мин` : ''}`.trim();
  const groupOrder = ['manicure', 'extension', 'design', 'depilation', 'massage', 'lashes', 'other'];
  const groupNames = { manicure: 'Маникюр', extension: 'Наращивание', design: 'Дизайн и ремонт', depilation: 'Депиляция', massage: 'Массаж', lashes: 'Ресницы', other: 'Другие услуги' };
  function groupOf(service) {
    const category = normalize(service.category);
    const name = normalize(service.name);
    if (category === 'шугаринг') return 'depilation';
    if (category === 'массаж') return 'massage';
    if (category === 'наращивание ресниц') return 'lashes';
    if (name.includes('дизайн') || name.includes('ремонт')) return 'design';
    if (name.includes('наращ')) return 'extension';
    if (name.includes('маникюр')) return 'manicure';
    return 'other';
  }
  let catalog = null;
  let loading = null;
  let restoreFocus = null;
  let timer = null;
  let frameId = '';
  let openVersion = 0;
  let state = { step: 1, serviceId: '', masterId: '', filterMasterId: '', category: 'all', search: '' };

  function validate(data) {
    if (!data || data.schemaVersion !== 1 || data.companyId !== '1006138' || !Array.isArray(data.services) || !Array.isArray(data.masters)) throw new Error('Invalid catalog');
    const masterIds = new Set(data.masters.map(master => master.id));
    if (!data.services.length || !data.masters.length) throw new Error('Empty catalog');
    if (data.services.some(service => !/^\d+$/.test(service.id) || !service.name || !service.masterIds?.length || service.masterIds.some(id => !masterIds.has(id) || !service.offerings?.[id]))) throw new Error('Unverified service mapping');
    return data;
  }
  async function loadCatalog() {
    if (catalog) return catalog;
    if (!loading) loading = fetch('./data/catalog.json', { cache: 'no-cache', signal: AbortSignal.timeout(15000) })
      .then(response => { if (!response.ok) throw new Error('Catalog unavailable'); return response.json(); })
      .then(validate).then(data => { catalog = data; return data; }).catch(error => { loading = null; throw error; });
    return loading;
  }
  const service = () => catalog?.services.find(item => item.id === state.serviceId);
  const master = () => catalog?.masters.find(item => item.id === state.masterId);
  function priceLabel(item, masterId = '') {
    const offering = item.offerings?.[masterId];
    return offering ? `${offering.priceFrom ? 'от ' : ''}${money(offering.price)}` : item.price;
  }
  function timeLabel(item, masterId = '') {
    const offering = item.offerings?.[masterId];
    if (offering) return duration(offering.durationMinutes);
    return item.durationMinutes === item.maxDurationMinutes ? duration(item.durationMinutes) : `от ${duration(item.durationMinutes)}`;
  }
  function calendarUrl() {
    const item = service(); const specialist = master();
    if (!item || !specialist || !item.offerings[specialist.id]) throw new Error('Choose a compatible service and specialist');
    const url = new URL('https://dikidi.net/ru/record/1006138');
    // The provider's company_master_service format preserves both actual IDs.
    url.search = new URLSearchParams({ st_m: '1', sm_m: specialist.id, ss_s: item.id, mode: 'website', source: 'widget', modalId: frameId }).toString();
    return url.href;
  }
  function releaseFrame() {
    clearTimeout(timer);
    const frame = $('#booking-calendar');
    if (frame?.contentWindow) frame.contentWindow.postMessage(JSON.stringify({ modalId: frameId, action: 'beforeRemove' }), 'https://dikidi.net');
    frameId = '';
  }
  function showDialog(trigger) {
    const open = document.querySelector('dialog[open]');
    restoreFocus = open?.contains(trigger) ? document.querySelector('.menu-toggle') : trigger;
    if (open && open !== dialog) open.close();
    if (!dialog.open) dialog.showModal();
  }
  function closeDialog() { releaseFrame(); dialog.close(); }
  function shell() {
    dialog.innerHTML = `<header class="bk-head"><div class="bk-topline"><div><span class="bk-wordmark">АМУР</span><small>Онлайн-запись · Владимир</small></div><button class="bk-close" type="button" data-bk-close aria-label="Закрыть запись">${icon('close')}</button></div><nav class="bk-steps" aria-label="Шаги записи">${['Услуга', 'Мастер', 'Дата и время'].map((name, index) => `<button type="button" class="bk-step-tab" data-step="${index + 1}" ${index + 1 === state.step ? 'aria-current="step"' : ''} ${index + 1 > state.step ? 'disabled' : ''}><span>${index + 1}</span>${name}</button>`).join('')}</nav></header><div class="bk-body"></div><footer class="bk-footer"></footer>`;
    $('[data-bk-close]').addEventListener('click', closeDialog);
    $$('.bk-step-tab').forEach(button => button.addEventListener('click', () => setStep(Number(button.dataset.step))));
  }
  function updateHeader() {
    $$('.bk-step-tab').forEach(button => {
      const step = Number(button.dataset.step);
      button.disabled = step > state.step;
      if (step === state.step) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
      button.classList.toggle('is-complete', step < state.step);
      $('span', button).innerHTML = step < state.step ? '✓' : String(step);
    });
  }
  function announce(message) {
    const el = document.getElementById('booking-announcement');
    if (el) el.textContent = message;
  }
  function footer() {
    const item = service(); const specialist = master(); const element = $('.bk-footer');
    element.hidden = state.step === 3;
    if (state.step === 3) return;
    const enabled = state.step === 1 ? Boolean(item) : Boolean(item && specialist && item.offerings[specialist.id]);
    const price = item ? priceLabel(item, specialist?.id || state.filterMasterId) : 'Выберите услугу';
    const detail = item ? (state.step === 2 && specialist ? `${specialist.name} · ${timeLabel(item, specialist.id)}` : item.name) : 'Цена и длительность появятся здесь';
    element.innerHTML = `<div class="bk-footer-copy" aria-live="polite"><strong>${esc(price)}</strong><small>${esc(detail)}</small></div><button type="button" class="button bk-next" ${enabled ? '' : 'disabled'}>${state.step === 1 ? 'К мастерам' : 'Выбрать время'}${icon('arrow')}</button>`;
    $('.bk-next').addEventListener('click', () => setStep(state.step + 1));
  }
  function setStep(step) {
    if (step > 1 && !service()) return;
    if (step === 3 && (!master() || !service().offerings[state.masterId])) return;
    releaseFrame();
    state.step = step;
    dialog.classList.toggle('is-calendar', step === 3);
    updateHeader();
    const body = $('.bk-body');
    body.classList.toggle('is-calendar', step === 3);
    if (step === 1) renderServices();
    if (step === 2) renderMasters();
    if (step === 3) renderCalendar();
    footer();
    body.scrollTop = 0;
    $('#booking-title')?.focus({ preventScroll: true });
  }
  function serviceOption(item) {
    const selected = item.id === state.serviceId;
    const names = item.masterIds.map(id => catalog.masters.find(person => person.id === id)?.name).filter(Boolean).join(', ');
    return `<button type="button" class="bk-option" role="radio" aria-checked="${selected}" data-service-id="${item.id}" tabindex="${selected ? '0' : '-1'}"><span><strong>${esc(item.name)}</strong><span class="bk-meta"><b>${esc(priceLabel(item, state.filterMasterId))}</b><span>${esc(timeLabel(item, state.filterMasterId))}</span></span><small>${esc(names)}</small></span><span class="bk-check">${icon('check')}</span></button>`;
  }
  function matches(item) {
    const names = item.masterIds.map(id => catalog.masters.find(person => person.id === id)?.name || '').join(' ');
    return (!state.filterMasterId || item.masterIds.includes(state.filterMasterId)) && (state.category === 'all' || groupOf(item) === state.category) && (!state.search || normalize(`${item.name} ${item.category} ${names}`).includes(state.search));
  }
  function filterServices() {
    const list = $('.bk-list');
    const items = catalog.services.filter(matches);
    list.innerHTML = items.length ? items.map(serviceOption).join('') : `<div class="bk-empty">По этому запросу услуг нет.<button type="button" data-clear-search>Сбросить поиск</button></div>`;
    const radios = $$('.bk-option', list);
    if (radios.length && !radios.some(radio => radio.tabIndex === 0)) radios[0].tabIndex = 0;
    radios.forEach(button => button.addEventListener('click', () => {
      state.serviceId = button.dataset.serviceId;
      if (state.masterId && !service().masterIds.includes(state.masterId)) state.masterId = '';
      radios.forEach(radio => { const active = radio === button; radio.setAttribute('aria-checked', String(active)); radio.tabIndex = active ? 0 : -1; });
      footer(); announce(`Выбрано: ${service().name}`);
    }));
    $('[data-clear-search]')?.addEventListener('click', () => {
      state.search = ''; state.category = 'all'; renderServices(); $('#booking-search').focus();
    });
    $('#booking-count').textContent = `Показано ${items.length} из ${catalog.services.length}`;
  }
  function renderServices() {
    const filteredMaster = catalog.masters.find(item => item.id === state.filterMasterId);
    const groups = groupOrder.filter(group => catalog.services.some(item => groupOf(item) === group));
    $('.bk-body').innerHTML = `<h2 class="bk-title" id="booking-title" tabindex="-1">Выберите услугу</h2><p class="bk-intro">Посмотрите цену и длительность, затем выберите мастера.</p>${filteredMaster ? `<div class="bk-master-filter"><span>Услуги мастера: <b>${esc(filteredMaster.name)}</b></span><button type="button" data-clear-master>Все мастера</button></div>` : ''}<label class="bk-search">${icon('zoom')}<input type="search" id="booking-search" placeholder="Найти услугу или мастера" aria-label="Поиск услуги или мастера" value="${esc(state.search)}" autocomplete="off"></label><div class="bk-filters" role="group" aria-label="Категории услуг">${[['all','Все услуги'], ...groups.map(group => [group, groupNames[group]])].map(([id,name]) => `<button type="button" class="bk-chip" data-category="${id}" aria-pressed="${state.category === id}">${name}</button>`).join('')}</div><p class="catalog-status" id="booking-count" role="status"></p><div class="bk-list" role="radiogroup" aria-label="Услуги"></div><p class="bk-note">У одноимённых услуг могут отличаться мастера и длительность. Точная стоимость выбранного мастера показана на следующем шаге.</p>`;
    $('#booking-search').addEventListener('input', event => { state.search = normalize(event.target.value); filterServices(); });
    $$('.bk-chip').forEach(chip => chip.addEventListener('click', () => {
      state.category = chip.dataset.category;
      $$('.bk-chip').forEach(button => button.setAttribute('aria-pressed', String(button === chip)));
      chip.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
      filterServices();
    }));
    $('[data-clear-master]')?.addEventListener('click', () => { state.filterMasterId = ''; state.masterId = ''; renderServices(); footer(); });
    filterServices();
  }
  function renderMasters() {
    const item = service();
    const people = catalog.masters.filter(person => item.masterIds.includes(person.id));
    $('.bk-body').innerHTML = `<h2 class="bk-title" id="booking-title" tabindex="-1">Выберите мастера</h2><p class="bk-intro">Эти мастера выполняют выбранную услугу.</p><div class="bk-summary"><div><strong>${esc(item.name)}</strong><small>Стоимость и длительность могут различаться</small></div><button class="bk-edit" type="button" data-edit-service>Изменить</button></div><div class="bk-list" role="radiogroup" aria-label="Мастера">${people.map(person => `<button type="button" class="bk-option bk-master-option" role="radio" aria-checked="${person.id === state.masterId}" data-master-id="${person.id}" tabindex="${person.id === state.masterId ? '0' : '-1'}"><span class="bk-avatar" aria-hidden="true">${esc(person.name[0])}${person.image ? `<img src="./${esc(person.image)}" alt="" width="66" height="72" loading="lazy">` : ''}</span><span><strong>${esc(person.name)}</strong><small>${esc(person.role)}</small><span class="bk-meta"><b>${esc(priceLabel(item, person.id))}</b><span>${esc(timeLabel(item, person.id))}</span></span></span><span class="bk-check">${icon('check')}</span></button>`).join('')}</div><p class="bk-note">На следующем шаге появятся свободные даты и время именно этого мастера.</p>`;
    $('[data-edit-service]').addEventListener('click', () => setStep(1));
    const radios = $$('.bk-master-option');
    if (radios.length && !radios.some(radio => radio.tabIndex === 0)) radios[0].tabIndex = 0;
    radios.forEach(button => button.addEventListener('click', () => {
      state.masterId = button.dataset.masterId;
      radios.forEach(radio => { const active = radio === button; radio.setAttribute('aria-checked', String(active)); radio.tabIndex = active ? 0 : -1; });
      footer(); announce(`Мастер: ${master().name}`);
    }));
  }
  function renderCalendar() {
    const item = service(); const person = master();
    frameId = `amur-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
    const url = calendarUrl();
    $('.bk-body').innerHTML = `<div class="bk-calendar-top"><div><h2 id="booking-title" tabindex="-1">Дата и время</h2><p>Время местное · Владимир, МСК</p></div><button type="button" class="bk-edit" data-edit-master>Назад</button></div><div class="bk-summary"><div><strong>${esc(item.name)}</strong><small>${esc(person.name)} · ${esc(priceLabel(item, person.id))} · ${esc(timeLabel(item, person.id))}</small></div><button type="button" class="bk-edit" data-edit-selection>Изменить</button></div><div class="bk-calendar-shell"><div class="bk-calendar-loader" role="status"><span class="bk-spinner" aria-hidden="true"></span><span>Загружаем расписание мастера…</span></div><iframe class="bk-calendar-frame" id="booking-calendar" title="Выбор свободной даты и времени" src="${esc(url)}" referrerpolicy="strict-origin-when-cross-origin" allow="publickey-credentials-get" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe></div><div class="bk-calendar-help"><span>Свободные окна из расписания салона</span><button type="button" data-reload-calendar>Обновить</button><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Открыть отдельно</a></div><div class="bk-calendar-error" hidden>Расписание долго загружается. Попробуйте обновить его или открыть отдельно — услуга и мастер сохранятся.</div><p class="bk-note">Запись появится у салона только после подтверждения в форме. До этого выбранное время не считается подтверждённым.</p>`;
    $('[data-edit-master]').addEventListener('click', () => setStep(2));
    $('[data-edit-selection]').addEventListener('click', () => setStep(1));
    $('[data-reload-calendar]').addEventListener('click', () => { releaseFrame(); renderCalendar(); });
    timer = setTimeout(() => {
      $('.bk-calendar-loader')?.setAttribute('hidden','');
      $('.bk-calendar-error')?.removeAttribute('hidden');
    }, 16000);
  }
  window.addEventListener('message', event => {
    const frame = $('#booking-calendar');
    if (!frame || event.origin !== 'https://dikidi.net' || event.source !== frame.contentWindow) return;
    let data;
    try { data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; } catch { return; }
    if (!data || data.modalId !== frameId) return;
    if (['ready','show','setSize'].includes(data.action)) {
      clearTimeout(timer); $('.bk-calendar-loader')?.setAttribute('hidden',''); $('.bk-calendar-error')?.setAttribute('hidden','');
    }
    if (data.action === 'setSize' && Number.isFinite(Number(data.height))) frame.style.height = `${Math.max(560, Math.min(Number(data.height), 1600))}px`;
    if (data.action === 'close') closeDialog();
    // Provider messages are never converted into fabricated booking confirmations.
  });
  dialog.addEventListener('keydown', event => {
    const radio = event.target.closest('[role="radio"]');
    if (!radio || !['ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    const choices = $$('[role="radio"]', radio.closest('[role="radiogroup"]'));
    const index = choices.indexOf(radio); const direction = ['ArrowDown','ArrowRight'].includes(event.key) ? 1 : -1;
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? choices.length - 1 : (index + direction + choices.length) % choices.length;
    event.preventDefault(); choices[next].focus(); choices[next].click();
  });
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeDialog(); });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeDialog();
  });
  dialog.addEventListener('close', () => {
    releaseFrame(); openVersion++;
    $('#booking-calendar')?.remove();
    if (restoreFocus?.isConnected) restoreFocus.focus({ preventScroll: true });
  });
  async function start(trigger) {
    const version = ++openVersion;
    const selectedService = trigger.dataset.serviceId || '';
    const selectedMaster = trigger.dataset.masterId || '';
    showDialog(trigger);
    if (!catalog) {
      dialog.innerHTML = `<div class="bk-head"><div class="bk-topline"><span class="bk-wordmark">АМУР</span><button type="button" class="bk-close" data-bk-close aria-label="Закрыть запись">${icon('close')}</button></div></div><div class="bk-body"><h2 class="bk-title" id="booking-title">Загружаем услуги…</h2><p class="bk-intro">Проверяем каталог студии.</p></div>`;
      $('[data-bk-close]').addEventListener('click', closeDialog);
    }
    try { await loadCatalog(); } catch {
      if (version !== openVersion || !dialog.open) return;
      $('.bk-body').innerHTML = `<h2 class="bk-title" id="booking-title">Каталог не загрузился</h2><p class="bk-intro">Проверьте подключение и попробуйте ещё раз.</p><button class="button" type="button" data-retry>Повторить</button><p class="bk-note"><a href="https://dikidi.net/1006138" target="_blank" rel="noopener noreferrer">Открыть форму записи отдельно</a></p>`;
      $('[data-retry]').addEventListener('click', () => start(trigger)); return;
    }
    if (version !== openVersion || !dialog.open) return;
    if (selectedService || selectedMaster) state = { step: 1, serviceId: selectedService, masterId: selectedMaster, filterMasterId: selectedMaster, category: 'all', search: '' };
    else state.step = 1;
    if (state.serviceId && !service()) state.serviceId = '';
    if (state.masterId && !master()) { state.masterId = ''; state.filterMasterId = ''; }
    releaseFrame(); shell(); setStep(1);
  }
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-book]');
    if (!trigger || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || typeof dialog.showModal !== 'function') return;
    event.preventDefault(); start(trigger);
  });
  // Searchable page catalog works independently from the booking dialog.
  const pageSearch = document.getElementById('catalog-search');
  if (pageSearch) {
    let category = 'all';
    const rows = [...document.querySelectorAll('.catalog-row')];
    const groups = [...document.querySelectorAll('.catalog-group')];
    function filterPage() {
      const query = normalize(pageSearch.value);
      rows.forEach(row => { row.hidden = (category !== 'all' && row.dataset.group !== category) || !normalize(row.dataset.search || '').includes(query); });
      groups.forEach(group => {
        group.hidden = ![...group.querySelectorAll('.catalog-row')].some(row => !row.hidden);
        if (query || category !== 'all') group.open = !group.hidden;
      });
      const count = rows.filter(row => !row.hidden).length;
      document.getElementById('catalog-status').textContent = `Показано ${count} из ${rows.length} услуг`;
      document.getElementById('catalog-empty').hidden = count > 0;
    }
    pageSearch.addEventListener('input', filterPage);
    document.querySelectorAll('.catalog-chip').forEach(chip => chip.addEventListener('click', () => {
      category = chip.dataset.category;
      document.querySelectorAll('.catalog-chip').forEach(button => button.setAttribute('aria-pressed', String(chip === button)));
      filterPage();
    }));
    filterPage();
  }
})();
