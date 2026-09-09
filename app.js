(() => {
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
})();
