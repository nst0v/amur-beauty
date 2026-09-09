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

  // Keep native <details> semantics; animate the measured height in both directions.
  const faqMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  $$('.faq-list details').forEach((details, index) => {
    const summary = details.querySelector(':scope > summary');
    const answer = summary?.nextElementSibling;
    if (!summary || !answer || typeof details.animate !== 'function') return;

    const icon = $('.icon', summary);
    const originalHeight = details.style.height;
    const originalOverflow = details.style.overflow;
    let expanded = details.open;
    let animations = [];
    let revision = 0;
    let answerWidth = 0;
    let answerHeight = 0;

    if (!answer.id) answer.id = `faq-answer-${index + 1}`;
    summary.setAttribute('aria-controls', answer.id);
    summary.setAttribute('aria-expanded', String(expanded));
    // The icon follows the same timeline as the panel, including closing/reversals.
    if (icon) icon.style.transition = 'none';

    function finish() {
      revision += 1;
      details.open = expanded;
      details.style.height = originalHeight;
      details.style.overflow = originalOverflow;
      animations.forEach(animation => animation.cancel());
      animations = [];
      summary.setAttribute('aria-expanded', String(expanded));
    }

    function animateTo(nextExpanded) {
      // Capture the currently painted frame before cancelling an interrupted toggle.
      const startHeight = details.getBoundingClientRect().height;
      const startOpacity = details.open ? getComputedStyle(answer).opacity : '0';
      const startRotation = icon ? getComputedStyle(icon).transform : 'none';
      const currentRevision = ++revision;
      animations.forEach(animation => animation.cancel());
      animations = [];
      expanded = nextExpanded;
      summary.setAttribute('aria-expanded', String(expanded));

      if (faqMotion.matches) {
        finish();
        return;
      }

      // Keep the answer rendered until closing finishes. No arbitrary max-height.
      details.open = true;
      details.style.height = 'auto';
      details.style.overflow = 'hidden';
      const openHeight = details.getBoundingClientRect().height;
      const style = getComputedStyle(details);
      const closedHeight = summary.getBoundingClientRect().height +
        parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) +
        parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
      const endHeight = expanded ? openHeight : closedHeight;
      const answerRect = answer.getBoundingClientRect();
      answerWidth = answerRect.width;
      answerHeight = answerRect.height;
      details.style.height = `${startHeight}px`;

      if (Math.abs(endHeight - startHeight) < 0.5) {
        finish();
        return;
      }

      const timing = {
        duration: expanded ? 340 : 280,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
        fill: 'both'
      };
      const heightAnimation = details.animate(
        { height: [`${startHeight}px`, `${endHeight}px`] }, timing
      );
      animations = [heightAnimation, answer.animate(
        { opacity: [startOpacity, expanded ? '1' : '0'] }, timing
      )];
      if (icon) animations.push(icon.animate(
        { transform: [startRotation, expanded ? 'rotate(45deg)' : 'rotate(0deg)'] }, timing
      ));
      heightAnimation.onfinish = () => {
        if (revision === currentRevision) finish();
      };
    }

    summary.addEventListener('click', event => {
      // Preserve links/buttons if a question later gains an independent action.
      if (event.defaultPrevented || event.target.closest('a, button, input, select, textarea')) return;
      event.preventDefault();
      animateTo(!expanded);
    });
    details.addEventListener('toggle', () => {
      if (animations.length) return;
      expanded = details.open;
      summary.setAttribute('aria-expanded', String(expanded));
    });
    faqMotion.addEventListener('change', () => {
      if (faqMotion.matches && animations.length) finish();
    });
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(() => {
        if (!animations.length) return;
        const rect = answer.getBoundingClientRect();
        // Retarget if line wrapping or fonts change mid-animation, not every frame.
        if (Math.abs(rect.width - answerWidth) > 0.5 || Math.abs(rect.height - answerHeight) > 0.5) {
          animateTo(expanded);
        }
      }).observe(answer);
    }
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
})();
