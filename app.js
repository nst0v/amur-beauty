(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const menu = $('#menu-dialog');
  const booking = $('#booking-dialog');
  const lightbox = $('#lightbox');
  let restoreFocus = null;

  const bookingCss = document.createElement('link');
  bookingCss.rel = 'stylesheet';
  bookingCss.href = './booking-flow.css';
  document.head.appendChild(bookingCss);

  const SERVICES = [
    { id: 'manicure-clean', name: 'Маникюр без покрытия', price: '700–900 ₽', group: 'nails' },
    { id: 'manicure-gel', name: 'Маникюр с гель-лаком', price: '1 200–1 500 ₽', group: 'nails' },
    { id: 'extensions', name: 'Наращивание ногтей', price: '2 500 ₽', group: 'nails' },
    { id: 'brows-shape', name: 'Коррекция бровей', price: '500 ₽', group: 'brows' },
    { id: 'brows-color', name: 'Окрашивание бровей', price: '1 000 ₽', group: 'brows' },
    { id: 'brows-lami', name: 'Ламинирование бровей с окрашиванием', price: '1 500 ₽', group: 'brows' },
    { id: 'design-light', name: 'Лёгкий дизайн', price: '200 ₽', group: 'nails', bookingService: '11473226' },
    { id: 'french', name: 'Френч', price: '400 ₽', group: 'nails', bookingService: '16488540' },
    { id: 'design-hard', name: 'Сложный дизайн', price: 'от 500 ₽', group: 'nails', bookingService: '16488520' },
    { id: 'repair', name: 'Ремонт ногтя', price: 'от 100 ₽', group: 'nails', bookingService: '11473332' },
    { id: 'pedicure', name: 'Педикюр', price: 'по прайсу записи', group: 'pedicure' },
    { id: 'sugaring', name: 'Шугаринг', price: 'по прайсу записи', group: 'sugaring' }
  ];

  const MASTERS = [
    { id: 'any', name: 'Любой свободный мастер', role: 'Покажем ближайшее доступное время', groups: ['nails', 'brows', 'pedicure', 'sugaring'], initial: 'А' },
    { id: '3585520', name: 'Наталья', role: 'Маникюр и педикюр', groups: ['nails', 'pedicure'], initial: 'Н' },
    { id: '4295706', name: 'Яна', role: 'Маникюр', groups: ['nails'], initial: 'Я' },
    { id: '4120856', name: 'Кристина', role: 'Шугаринг', groups: ['sugaring'], initial: 'К' }
  ];

  let bookingState = { service: null, master: null, step: 1 };

  function openDialog(dialog, trigger) {
    if (!dialog || typeof dialog.showModal !== 'function') return false;
    const open = $('dialog[open]');
    let focusTarget = trigger || document.activeElement;
    if (open && open !== dialog) {
      if (open.contains(focusTarget)) focusTarget = restoreFocus || $('.menu-toggle');
      open.close();
    }
    restoreFocus = focusTarget;
    dialog.showModal();
    return true;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  }

  function bookingUrl() {
    const base = 'https://dikidi.net/en/record/1006138';
    const service = bookingState.service;
    const master = bookingState.master;
    if (service?.bookingService) return `${base}?st_m=2&ss_s=${encodeURIComponent(service.bookingService)}`;
    if (master && master.id !== 'any') return `${base}?st_m=1&sm_m=${encodeURIComponent(master.id)}`;
    return 'https://dikidi.net/1006138';
  }

  function renderBooking() {
    const service = bookingState.service;
    const master = bookingState.master;
    const step = bookingState.step;
    const masters = service ? MASTERS.filter(item => item.groups.includes(service.group)) : MASTERS;

    booking.innerHTML = `
      <div class="dialog-header booking-flow-head">
        <div>
          <p class="eyebrow">ОНЛАЙН-ЗАПИСЬ</p>
          <div class="booking-progress" aria-label="Шаг ${step} из 3">
            <span class="${step >= 1 ? 'is-done' : ''}"></span><span class="${step >= 2 ? 'is-done' : ''}"></span><span class="${step >= 3 ? 'is-done' : ''}"></span>
          </div>
        </div>
        <button class="icon-button" data-close type="button" aria-label="Закрыть окно записи"><svg class="icon"><use href="#i-close"/></svg></button>
      </div>
      ${step === 1 ? `
        <div class="booking-step" data-step="1">
          <span class="booking-step-number">Шаг 1 из 3</span>
          <h2>Выберите <em>услугу.</em></h2>
          <p class="dialog-description">Выбор происходит здесь — переходить в другой сервис не нужно.</p>
          <div class="booking-service-list">
            ${SERVICES.map(item => `<button type="button" class="booking-choice service-choice ${service?.id === item.id ? 'is-selected' : ''}" data-service-id="${item.id}"><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.price)}</small></span><span class="choice-check">✓</span></button>`).join('')}
          </div>
        </div>` : ''}
      ${step === 2 ? `
        <div class="booking-step" data-step="2">
          <button class="booking-back" type="button" data-booking-back>← Назад к услугам</button>
          <span class="booking-step-number">Шаг 2 из 3</span>
          <h2>Выберите <em>мастера.</em></h2>
          <div class="booking-current"><span>${escapeHtml(service.name)}</span><strong>${escapeHtml(service.price)}</strong></div>
          <div class="booking-master-list">
            ${masters.map(item => `<button type="button" class="booking-choice master-choice ${master?.id === item.id ? 'is-selected' : ''}" data-master-id="${item.id}"><span class="master-mini">${item.initial}</span><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.role)}</small></span><span class="choice-check">✓</span></button>`).join('')}
          </div>
        </div>` : ''}
      ${step === 3 ? `
        <div class="booking-step booking-confirm" data-step="3">
          <button class="booking-back" type="button" data-booking-back>← Изменить мастера</button>
          <span class="booking-step-number">Шаг 3 из 3</span>
          <h2>Всё <em>выбрано.</em></h2>
          <div class="booking-summary">
            <div><span>Услуга</span><strong>${escapeHtml(service.name)}</strong><small>${escapeHtml(service.price)}</small></div>
            <div><span>Мастер</span><strong>${escapeHtml(master.name)}</strong><small>${escapeHtml(master.role)}</small></div>
          </div>
          <p class="dialog-description">Осталось выбрать свободное время. Только на этом шаге откроется внешняя форма расписания.</p>
          <a class="button booking-time-button" href="${bookingUrl()}" target="_blank" rel="noopener noreferrer">Выбрать свободное время <svg class="icon"><use href="#i-up"/></svg></a>
          <button class="booking-reset" type="button" data-booking-reset>Начать заново</button>
        </div>` : ''}
    `;

    $$('[data-close]', booking).forEach(button => button.addEventListener('click', () => booking.close()));
    $$('.service-choice', booking).forEach(button => button.addEventListener('click', () => {
      bookingState.service = SERVICES.find(item => item.id === button.dataset.serviceId);
      bookingState.master = null;
      bookingState.step = 2;
      renderBooking();
    }));
    $$('.master-choice', booking).forEach(button => button.addEventListener('click', () => {
      bookingState.master = MASTERS.find(item => item.id === button.dataset.masterId);
      bookingState.step = 3;
      renderBooking();
    }));
    const back = $('[data-booking-back]', booking);
    if (back) back.addEventListener('click', () => {
      bookingState.step = Math.max(1, bookingState.step - 1);
      if (bookingState.step === 1) bookingState.master = null;
      renderBooking();
    });
    const reset = $('[data-booking-reset]', booking);
    if (reset) reset.addEventListener('click', () => {
      bookingState = { service: null, master: null, step: 1 };
      renderBooking();
    });
  }

  function startBooking(trigger, serviceName = '') {
    let preselected = null;
    if (serviceName) {
      const normalized = serviceName.toLowerCase().replace(' с окрашиванием', '');
      preselected = SERVICES.find(item => item.name.toLowerCase() === serviceName.toLowerCase()) ||
        SERVICES.find(item => normalized.includes(item.name.toLowerCase()) || item.name.toLowerCase().includes(normalized));
    }
    bookingState = preselected ? { service: preselected, master: null, step: 2 } : { service: null, master: null, step: 1 };
    renderBooking();
    openDialog(booking, trigger);
  }

  $$('dialog').forEach(dialog => {
    if (dialog !== booking) $$('[data-close]', dialog).forEach(button => button.addEventListener('click', () => dialog.close()));
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

  $$('[data-book]').forEach(anchor => {
    anchor.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if (typeof booking.showModal !== 'function') return;
      event.preventDefault();
      startBooking(anchor, anchor.dataset.service || '');
    });
  });

  // Clicking the visible master CTA now starts with that master preselected when possible.
  $$('.team-card .text-link').forEach(link => {
    const card = link.closest('.team-card');
    const name = $('h3', card)?.textContent.trim();
    const matched = MASTERS.find(item => item.name === name);
    if (!matched) return;
    link.addEventListener('click', event => {
      event.preventDefault();
      bookingState = { service: null, master: matched, step: 1 };
      renderBooking();
      openDialog(booking, link);
    });
  });

  const tabs = $$('.tab');
  function activateTab(tab, focus = false) {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      item.classList.toggle('is-active', active);
      document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
    });
    if (focus) tab.focus({ preventScroll: true });
    tab.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      activateTab(tabs[next], true);
    });
  });

  const cards = $$('.work-card');
  const filters = $$('.filter');
  let activeFilter = 'all';
  let expanded = false;
  let visibleCards = [];
  let currentImage = 0;
  let loadVersion = 0;
  const more = $('#show-more');
  function applyFilter() {
    const matches = cards.filter(card => activeFilter === 'all' || card.dataset.category.split(' ').includes(activeFilter));
    const max = expanded || activeFilter !== 'all' ? matches.length : 4;
    visibleCards = matches.slice(0, max);
    cards.forEach(card => { card.hidden = !visibleCards.includes(card); });
    more.hidden = activeFilter !== 'all' || expanded || matches.length <= 4;
    $('#gallery-status').textContent = `Показано работ: ${visibleCards.length} из ${matches.length}.`;
  }
  filters.forEach(filter => filter.addEventListener('click', () => {
    activeFilter = filter.dataset.filter;
    filters.forEach(item => {
      const selected = item === filter;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    applyFilter();
  }));
  more.addEventListener('click', () => {
    const firstNewCard = cards[4];
    expanded = true;
    applyFilter();
    firstNewCard.focus({ preventScroll: true });
  });
  function showImage(index) {
    if (!visibleCards.length) return;
    currentImage = (index + visibleCards.length) % visibleCards.length;
    const card = visibleCards[currentImage];
    const picture = $('#lightbox-image');
    const version = ++loadVersion;
    lightbox.classList.add('is-loading');
    lightbox.classList.remove('image-error');
    picture.alt = $('img', card).alt;
    picture.onload = () => { if (version === loadVersion) lightbox.classList.remove('is-loading'); };
    picture.onerror = () => {
      if (version !== loadVersion || !lightbox.open) return;
      lightbox.classList.remove('is-loading');
      lightbox.classList.add('image-error');
    };
    picture.src = `./assets/${card.dataset.image}.webp`;
    $('#lightbox-title').textContent = card.dataset.title;
    $('#lightbox-detail').textContent = card.dataset.detail;
    $('#lightbox-count').textContent = `${currentImage + 1} / ${visibleCards.length}`;
    $('#lightbox-prev').hidden = visibleCards.length < 2;
    $('#lightbox-next').hidden = visibleCards.length < 2;
  }
  cards.forEach(card => card.addEventListener('click', () => {
    if (typeof lightbox.showModal !== 'function') {
      window.open(`./assets/${card.dataset.image}.webp`, '_blank', 'noopener');
      return;
    }
    openDialog(lightbox, card);
    showImage(visibleCards.indexOf(card));
  }));
  $('#lightbox-prev').addEventListener('click', () => showImage(currentImage - 1));
  $('#lightbox-next').addEventListener('click', () => showImage(currentImage + 1));
  lightbox.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      showImage(currentImage + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  let touchStart = null;
  $('.lightbox-stage').addEventListener('touchstart', event => {
    if (event.touches.length === 1) touchStart = { x: event.touches[0].clientX, y: event.touches[0].clientY };
    else touchStart = null;
  }, { passive: true });
  $('.lightbox-stage').addEventListener('touchend', event => {
    if (!touchStart || !event.changedTouches.length) return;
    const dx = event.changedTouches[0].clientX - touchStart.x;
    const dy = event.changedTouches[0].clientY - touchStart.y;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) showImage(currentImage + (dx < 0 ? 1 : -1));
    touchStart = null;
  }, { passive: true });
  $$('.team-avatar img').forEach(image => {
    const loaded = () => image.classList.toggle('is-loaded', image.naturalWidth > 0);
    image.addEventListener('load', loaded);
    image.addEventListener('error', () => image.classList.remove('is-loaded'));
    if (image.complete) loaded();
  });
  $('#year').textContent = String(new Date().getFullYear());
  applyFilter();
  renderBooking();
})();