# Сайт отеля на Astro

Статический многостраничный сайт объекта размещения. Весь контент берётся из `hotels/<slug>.yaml`, а фото — из `src/assets/hotels/<slug>/`, поэтому для нового отеля шаблон править не нужно.

## Запуск

```bash
npm install
npm run dev                  # http://localhost:4321
npm run build                # готовый сайт в dist/
HOTEL=prospekt npm run build # собрать другой отель (по умолчанию prospekt)
npm run check                # проверка типов
```

## Новый отель

1. Скопировать `hotels/prospekt.yaml` в `hotels/<slug>.yaml` и заполнить. Поле со значением `null` на сайт не выводится.
2. Положить фото: `src/assets/hotels/<slug>/hotel/*.jpg` (здание и территория) и `src/assets/hotels/<slug>/rooms/<room.slug>/*.jpg` (порядок задаёт имя файла).
3. Выбрать `booking.provider`:
   - `bnovo` — у отеля есть ReservationSteps/Bnovo: форма дат открывает модуль с подставленными `dfrom`, `dto` и `adults`;
   - `request` — модуля нет: форма отправляет заявку администратору в WhatsApp.
4. Указать `analytics.metrika_id`: подключатся Метрика, плашка про cookie и цели `book_click`, `book_search`, `phone_click`, `wa_click`, `route_click`, `taxi_click`, `request_send`.
5. `HOTEL=<slug> npm run build` — содержимое `dist/` можно выложить на любой статический хостинг или nginx.

## Админка

`ADMIN_PASSWORD=… npm run admin` → http://127.0.0.1:8097/admin/. Админка работает с телефона. В ней правятся цены и тексты номеров, фото (загрузка, порядок, удаление, главное фото), контакты, бронь, Метрика, FAQ, места, такси и схема подъезда. Кнопка «Опубликовать» запускает `astro build` и подменяет `PUBLISH_DIR` новой сборкой.

Переменные окружения: `ADMIN_PASSWORD` (обязательно), `SESSION_SECRET`, `HOTEL` (по умолчанию `prospekt`), `PORT` (8097), `PUBLISH_DIR` (папка, которую раздаёт nginx).

- При каждом сохранении прошлая версия yaml копируется в `hotels/.history/` (хранятся 50 последних). Удалённые фото переносятся в `hotels/.trash/`.
- Загруженные фото поворачиваются по EXIF и уменьшаются до 2400 px (JPEG). Новые файлы получают имена `<папка>-N.jpg`.
- Правки из админки сохраняются только на сервере и в git не попадают. Перед выкладкой новой версии шаблона нужно забрать с сервера `hotels/<slug>.yaml` и `src/assets/hotels/<slug>/`.

nginx:
```nginx
location /admin/ { proxy_pass http://127.0.0.1:8097; proxy_set_header X-Real-IP $remote_addr; client_max_body_size 30m; }
```

## Страницы

`/` главная · `/nomera/` и `/nomera/<slug>/` номера · `/foto/` галерея · `/kak-dobratsya/` карта, маршруты, такси · `/chto-ryadom/` достопримечательности с расстояниями · `/voprosy/` FAQ · `/kontakty/` контакты, реквизиты, заявка · `/politika/` политика ПДн · `sitemap-index.xml`, `robots.txt`, разметка schema.org Hotel/HotelRoom/FAQPage.

## Что запросить у «Проспекта» перед запуском

- разрешение на фото или исходники в высоком разрешении;
- схему подъезда и парковки (`arrival.steps`) с фото въезда;
- время заезда и выезда, правила для детей и животных, список удобств по номерам → в `faq` и `rooms`;
- цены «от» по каждой категории (`rooms[].price_from`);
- номер счётчика Метрики и домен.
