from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

YANDEX = 'https://yandex.ru/maps/org/amur/202060827340/reviews/'
BOOKING = 'https://dikidi.net/1006138'

# Hero rating: only Yandex is presented to visitors.
s = re.sub(
    r'<a class="rating-pill"[^>]*>.*?</a>',
    f'<a class="rating-pill" href="{YANDEX}" target="_blank" rel="noopener noreferrer" aria-label="Рейтинг студии 5,0 из 5 на Яндекс Картах"><span class="rating-star" aria-hidden="true">★</span><strong>5,0</strong><span>нам доверяют<br> <b>по оценкам на Яндекс Картах</b></span><svg class="icon"><use href="#i-up"/></svg></a>',
    s,
    count=1,
    flags=re.S,
)

# Reviews block: source, rating and links are Yandex Maps only.
reviews = f'''<section class="reviews-section" aria-labelledby="reviews-title"><div class="container reviews-layout"><div class="reviews-intro"><p class="eyebrow">СЛОВА, КОТОРЫЕ СОГРЕВАЮТ</p><h2 id="reviews-title">Ваши<br> <em>впечатления.</em></h2><a class="review-rating" href="{YANDEX}" target="_blank" rel="noopener noreferrer"><strong>5,0<span>/ 5</span></strong><span>62 оценки на Яндекс Картах <svg class="icon"><use href="#i-up"/></svg></span></a></div><div class="review-cards"><figure class="review-card"><div class="review-top"><span class="quote-mark" aria-hidden="true">“</span><span class="review-source">ЯНДЕКС КАРТЫ</span></div><blockquote>Здесь царит приятная атмосфера: чисто, удобно, персонал внимателен к пожеланиям.</blockquote><figcaption><span class="review-initial" aria-hidden="true">О</span><span><strong>Ольга Медведкова</strong><span>6 мая · Яндекс Карты</span></span></figcaption></figure><figure class="review-card"><div class="review-top"><span class="quote-mark" aria-hidden="true">“</span><span class="review-source">ЯНДЕКС КАРТЫ</span></div><blockquote>Мастер очень приятный, вежливо относится к клиенту, приятная обстановка. Сделала всё аккуратно и красиво.</blockquote><figcaption><span class="review-initial" aria-hidden="true">И</span><span><strong>Ирина Мосылёва</strong><span>14 января · Яндекс Карты</span></span></figcaption></figure><a class="text-link all-reviews" href="{YANDEX}" target="_blank" rel="noopener noreferrer">Читать все отзывы на Яндекс Картах <svg class="icon"><use href="#i-up"/></svg></a></div></div></section>'''
s = re.sub(r'<section class="reviews-section".*?</section>', reviews, s, count=1, flags=re.S)

# Visible booking/provider mentions: booking still technically opens the same external service,
# but visitors only see generic online-booking wording.
s = s.replace('Вся команда в DIKIDI', 'Вся команда и запись')
s = s.replace('Мастера из открытой карточки студии в DIKIDI. Расписание и полный состав команды — при онлайн-записи.', 'Расписание и полный состав команды доступны при онлайн-записи.')
s = s.replace('По графику студии в DIKIDI · по записи', 'Ежедневно · по предварительной записи')
s = s.replace('По открытой карточке DIKIDI на 9 сентября 2026 года. Педикюр, шугаринг и остальные услуги — в полном каталоге онлайн-записи.', 'Дополнительные услуги и актуальная стоимость доступны в полном каталоге онлайн-записи.')
s = s.replace('Актуальный прайс и все услуги в DIKIDI', 'Актуальный прайс и все услуги')
s = s.replace('Нажмите «Записаться онлайн»: можно перейти в DIKIDI, написать в сообщения ВКонтакте или позвонить. В DIKIDI выберите услугу, мастера и доступное время. Запись подтверждается на стороне сервиса, а не на этой демонстрационной странице.', 'Нажмите «Записаться онлайн», затем выберите услугу, мастера и свободное время. Запись подтверждается во внешней форме онлайн-записи.')

# Replace the booking dialog with one booking channel only.
s = re.sub(
    r'<dialog id="booking-dialog".*?</dialog>',
    f'''<dialog id="booking-dialog" class="booking-dialog" aria-labelledby="booking-title"><div class="dialog-header"><p class="eyebrow">ВАШЕ ВРЕМЯ ДЛЯ СЕБЯ</p><button class="icon-button" data-close type="button" aria-label="Закрыть окно записи"><svg class="icon"><use href="#i-close"/></svg></button></div><h2 id="booking-title">Давайте <em>встретимся.</em></h2><p class="dialog-description" id="booking-description">Выберите услугу, мастера и удобное время в форме онлайн-записи.</p><p class="selected-service" id="selected-service" hidden></p><a class="booking-option is-primary" href="{BOOKING}" target="_blank" rel="noopener noreferrer"><span class="option-icon"><svg class="icon"><use href="#i-calendar"/></svg></span><span><strong>Перейти к онлайн-записи</strong><small>Услуги, мастера и свободные окна</small></span><svg class="icon"><use href="#i-up"/></svg></a><p class="dialog-note">Откроется внешняя форма записи. Эта демоверсия не собирает и не хранит персональные данные.</p></dialog>''',
    s,
    count=1,
    flags=re.S,
)

# Demo information visible to visitors: sources are VK + Yandex; booking provider is not named.
s = re.sub(
    r'<dialog id="demo-dialog".*?</dialog>',
    f'''<dialog id="demo-dialog" class="booking-dialog demo-dialog" aria-labelledby="demo-title"><div class="dialog-header"><p class="eyebrow">О ПРОЕКТЕ</p><button class="icon-button" data-close type="button" aria-label="Закрыть информацию"><svg class="icon"><use href="#i-close"/></svg></button></div><h2 id="demo-title">С любовью<br> <em>к деталям.</em></h2><p>Это демонстрационный сайт студии «Амур» для согласования дизайна.</p><p>Фотографии работ и основной прайс взяты из доступных публикаций <a href="https://vk.com/amur_studio33" target="_blank" rel="noopener noreferrer">сообщества ВКонтакте</a>. Актуальность цен и услуг перед запуском нужно подтвердить у студии.</p><p>Рейтинг и отзывы показаны по карточке студии на <a href="{YANDEX}" target="_blank" rel="noopener noreferrer">Яндекс Картах</a>.</p><p>Кнопки записи открывают внешнюю форму онлайн-записи. Сайт не хранит персональные данные.</p><p class="dialog-note">До рабочего запуска необходимо согласовать материалы с владельцем салона и снять запрет индексации.</p></dialog>''',
    s,
    count=1,
    flags=re.S,
)

# The provider name must not be visible anywhere in HTML; its URL is allowed only as booking mechanics.
visible_name = 'DIKIDI'
s = s.replace(visible_name, 'онлайн-запись')

p.write_text(s, encoding='utf-8')

# JS text also must not display the provider name.
js = Path('app.js')
j = js.read_text(encoding='utf-8')
j = j.replace('// Without dialog support the original DIKIDI link remains the working fallback.', '// Without dialog support the original booking link remains the working fallback.')
j = j.replace('Выбор услуги нужно подтвердить в DIKIDI или сообщениях студии.', 'Выбор услуги и времени нужно подтвердить в форме онлайн-записи.')
js.write_text(j, encoding='utf-8')

print('Yandex rating/reviews applied; booking provider branding removed from UI')
