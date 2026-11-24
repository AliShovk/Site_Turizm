const $ = (s, el = document) => el.querySelector(s);
const api = async (url, opts = {}) => {
  const r = await fetch('/admin/api/' + url, { credentials: 'same-origin', ...opts, headers: { 'X-Admin': '1', ...(opts.json !== undefined ? { 'Content-Type': 'application/json' } : {}), ...opts.headers }, body: opts.json !== undefined ? JSON.stringify(opts.json) : opts.body });
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && url !== 'login') { showLogin(); throw new Error(data.error || 'Нужен вход'); }
  if (!r.ok) throw new Error(data.error || `Ошибка ${r.status}`);
  return data;
};
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'class') el.className = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) el.append(k.nodeType ? k : String(k));
  return el;
};
let toastT;
const toast = (msg) => { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 3200); };

let H = null, REV = '', P = {}, S = {}, dirty = false, tab = 'rooms', roomIdx = null, ver = Date.now();
const setDirty = (v = true) => { dirty = v; $('#save').disabled = !v; renderStatus(); };

// ---------- form helpers ----------
const parseNum = (s) => { const t = s.replace(/[\s\u00a0₽]/g, '').replace(',', '.'); return t === '' ? null : /^-?\d+(\.\d+)?$/.test(t) ? Number(t) : NaN; };
function numInput(el, set) {
  const v = parseNum(el.value);
  el.setCustomValidity(Number.isNaN(v) ? 'Введите число, например 6200' : '');
  el.reportValidity();
  if (!Number.isNaN(v)) set(v);
  setDirty();
}
function field(label, obj, key, o = {}) {
  const val = obj[key];
  const el = o.type === 'textarea' ? h('textarea', { rows: o.rows || 4 }) : o.options ? h('select', {}, o.options.map(([v, t]) => h('option', { value: v }, t)))
    : h('input', { type: o.type === 'number' ? 'text' : o.type || 'text', inputmode: o.type === 'number' ? 'decimal' : null, placeholder: o.ph, autocomplete: 'off' });
  el.value = val ?? '';
  el.addEventListener('input', () => {
    if (o.type === 'number') return numInput(el, (v) => { obj[key] = v; o.onchange?.(); });
    const v = el.value.trim();
    obj[key] = v === '' && o.nullable !== false ? null : el.value;
    setDirty(); o.onchange?.();
  });
  return h('label', { class: 'f' }, h('span', {}, label), el, o.hint && h('small', {}, o.hint));
}
const coordsField = (label, obj, key) => {
  const el = h('input', { placeholder: '43.9133, 42.7194', inputmode: 'decimal' });
  el.value = obj[key] ? obj[key].join(', ') : '';
  el.addEventListener('input', () => { const m = el.value.split(/[,;\s]+/).filter(Boolean).map(Number); obj[key] = m.length === 2 && m.every(Number.isFinite) ? m : null; setDirty(); });
  return h('label', { class: 'f' }, h('span', {}, label), el, h('small', {}, 'Широта, долгота — можно скопировать из Яндекс.Карт'));
};
function listEditor(arr, render, blank, addLabel, onchange) {
  const changed = () => { setDirty(); onchange?.(); };
  const wrap = h('div', { class: 'list' });
  const draw = () => {
    wrap.replaceChildren(...arr.map((it, i) => h('div', { class: 'card item' }, render(it, i),
      h('div', { class: 'item-acts' },
        h('button', { class: 'btn sm', type: 'button', disabled: i === 0, 'aria-label': 'Выше', onclick: () => { [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]; changed(); draw(); } }, '↑'),
        h('button', { class: 'btn sm', type: 'button', disabled: i === arr.length - 1, 'aria-label': 'Ниже', onclick: () => { [arr[i + 1], arr[i]] = [arr[i], arr[i + 1]]; changed(); draw(); } }, '↓'),
        h('button', { class: 'btn sm danger', type: 'button', onclick: () => { if (confirm('Удалить?')) { arr.splice(i, 1); changed(); draw(); } } }, 'Удалить')))),
      h('button', { class: 'btn wide', type: 'button', onclick: () => { arr.push(blank()); changed(); draw(); } }, addLabel));
  };
  draw();
  return wrap;
}

// ---------- photos ----------
const thumb = (dir, file) => `/admin/api/photo?dir=${encodeURIComponent(dir)}&file=${encodeURIComponent(file)}&v=${ver}`;
async function shrink(file) {
  try {
    const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const k = Math.min(1, 2400 / Math.max(bmp.width, bmp.height));
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return await new Promise((ok) => c.toBlob((b) => ok(b || file), 'image/jpeg', 0.88));
  } catch { return file; }
}
function photoGrid(dir, opts = {}) {
  const wrap = h('div');
  const draw = () => {
    const files = P[dir] || [];
    const move = async (i, d) => {
      const order = [...files]; [order[i], order[i + d]] = [order[i + d], order[i]];
      try { const r = await api('photo/order', { method: 'POST', json: { dir, files: order }, headers: { 'X-Rev': REV } }); P = r.photos; if (r.rev) { H.hero.image = r.hotel.hero.image; REV = r.rev; } ver = Date.now(); draw(); }
      catch (e) { toast(e.message); }
    };
    const input = h('input', { type: 'file', accept: 'image/*', multiple: true });
    input.addEventListener('change', async () => {
      const list = [...input.files]; input.value = '';
      for (const [n, f] of list.entries()) {
        toast(`Загружаю ${n + 1} из ${list.length}…`);
        try { const r = await api(`photo?dir=${encodeURIComponent(dir)}`, { method: 'POST', body: await shrink(f), headers: { 'Content-Type': 'application/octet-stream' } }); P = r.photos; ver = Date.now(); draw(); }
        catch (e) { toast(`${f.name}: ${e.message}`); return; }
      }
      toast('Фото загружены. Не забудьте опубликовать.'); renderStatus(true);
    });
    wrap.replaceChildren(h('div', { class: 'ph-grid' },
      files.map((f, i) => {
        const isMain = opts.hero && H.hero.image === `hotel/${f}`;
        return h('div', { class: 'ph' + (isMain ? ' main' : '') },
          h('img', { src: thumb(dir, f), alt: '', loading: 'lazy' }),
          isMain && h('span', { class: 'tag' }, 'Главное'), h('span', { class: 'num' }, i + 1),
          h('div', { class: 'acts' },
            h('button', { type: 'button', disabled: i === 0, 'aria-label': 'Раньше', onclick: () => move(i, -1) }, '←'),
            h('button', { type: 'button', disabled: i === files.length - 1, 'aria-label': 'Позже', onclick: () => move(i, 1) }, '→'),
            opts.hero && !isMain && h('button', { type: 'button', title: 'Сделать главным', 'aria-label': 'Сделать главным', onclick: () => { H.hero.image = `hotel/${f}`; setDirty(); draw(); toast('Главное фото выбрано — нажмите «Сохранить»'); } }, '★'),
            h('button', { type: 'button', class: 'del', 'aria-label': 'Удалить', onclick: async () => {
              if (!confirm('Удалить фото?')) return;
              try { P = (await api('photo', { method: 'DELETE', json: { dir, file: f } })).photos; draw(); renderStatus(true); } catch (e) { toast(e.message); }
            } }, '✕')));
      }),
      h('label', { class: 'upload' }, input, h('span', {}, '+ Добавить фото'), h('span', { class: 'small' }, 'с телефона или компьютера'))));
  };
  draw();
  return wrap;
}

// ---------- tabs ----------
const views = {
  rooms() {
    if (roomIdx != null && H.rooms[roomIdx]) return roomEditor(H.rooms[roomIdx]);
    roomIdx = null;
    const list = h('div', { class: 'list' }, H.rooms.map((r, i) => {
      const ph = P[`rooms/${r.slug}`]?.[0];
      const price = h('input', { class: 'price-in', type: 'text', inputmode: 'numeric', placeholder: 'цена от', 'aria-label': `Цена от, ${r.name}` });
      price.value = r.price_from ?? '';
      price.addEventListener('click', (e) => e.stopPropagation());
      price.addEventListener('input', () => numInput(price, (v) => { r.price_from = v == null ? null : Math.round(v); }));
      return h('div', { class: 'card room-item', onclick: () => { roomIdx = i; render(); scrollTo(0, 0); } },
        ph ? h('img', { src: thumb(`rooms/${r.slug}`, ph), alt: '' }) : h('div', { class: 'noimg' }),
        h('div', { class: 'ri' }, h('b', {}, r.name || 'Без названия'), h('span', { class: 'muted small' }, `${P[`rooms/${r.slug}`]?.length || 0} фото · ${r.area ? r.area + ' м²' : 'площадь не указана'}`)),
        price, h('span', { class: 'muted small' }, '₽'));
    }));
    return [h('h1', {}, 'Номера и цены'), h('p', { class: 'muted small' }, 'Цену «от» можно поменять прямо в списке. Нажмите на номер, чтобы изменить описание и фото. Пустая цена — на сайте будет «Цена по датам».'),
      list, h('h2', {}, ''), h('div', { class: 'grid' }, field('Цена «от» на главной, ₽', H, 'price_from', { type: 'number' }), field('Всего номеров в отеле', H, 'rooms_total', { type: 'number' })),
      h('button', { class: 'btn wide', type: 'button', onclick: () => { H.rooms.push({ slug: '', name: 'Новый номер', area: null, beds: null, guests: 2, price_from: null, text: '' }); roomIdx = H.rooms.length - 1; setDirty(); render(); } }, '+ Добавить категорию номера')];
  },
  photos() {
    return [h('h1', {}, 'Фото отеля'), h('p', { class: 'muted small' }, 'Фасад, холл, территория. ★ — сделать фото главным (обложка сайта). Порядок здесь = порядок на сайте. Фото номеров — во вкладке «Номера и цены».'), photoGrid('hotel', { hero: true })];
  },
  main() {
    return [h('h1', {}, 'Главная страница'),
      h('div', { class: 'card' }, field('Название отеля', H, 'name', { nullable: false }), field('Короткое название', H, 'short_name', { nullable: false }),
        h('div', { class: 'grid' }, field('Звёзд', H, 'stars', { type: 'number' }), field('Город', H, 'city', { nullable: false }), field('«в городе»', H, 'city_prep', { hint: 'Например: в Кисловодске' })),
        field('Адрес', H, 'address', { nullable: false }), coordsField('Координаты на карте', H, 'coords')),
      h('h2', {}, 'Обложка'), h('div', { class: 'card' }, field('Заголовок', H.hero, 'title', { nullable: false }), field('Подзаголовок', H.hero, 'lead', { type: 'textarea', rows: 3 })),
      h('h2', {}, 'Рейтинг'), ratingCard(),
      h('h2', {}, 'Преимущества (карточки под формой брони)'), listEditor(H.highlights, (it) => h('div', { class: 'grid' }, field('Заголовок', it, 'title'), field('Текст', it, 'text')), () => ({ title: '', text: '' }), '+ Добавить преимущество'),
      h('h2', {}, 'Об отеле'), h('div', { class: 'card' }, field('Текст', H, 'about', { type: 'textarea', rows: 6 })),
      h('h2', {}, 'Для поисковиков'), h('div', { class: 'card' }, field('Title', H.seo, 'title', { nullable: false, hint: 'До 70 символов, с названием города' }), field('Description', H.seo, 'description', { type: 'textarea', rows: 3, nullable: false, hint: 'До 160 символов' }))];
  },
  contacts() {
    H.booking ||= { provider: 'request', url: null }; H.analytics ||= { metrika_id: null };
    return [h('h1', {}, 'Контакты и бронирование'),
      h('div', { class: 'card' }, h('div', { class: 'grid' }, field('Телефон для звонка', H.contacts, 'phone', { nullable: false, ph: '+79281234567' }), field('Телефон как показывать', H.contacts, 'phone_display', { ph: '+7 928 123-45-67' })),
        h('div', { class: 'grid' }, field('WhatsApp (только цифры)', H.contacts, 'whatsapp', { ph: '79281234567' }), field('Telegram', H.contacts, 'telegram', { ph: '@hotel' }), field('E-mail', H.contacts, 'email', { type: 'email' }))),
      h('h2', {}, 'Бронирование'),
      h('div', { class: 'card' }, field('Как бронируют', H.booking, 'provider', { options: [['bnovo', 'Модуль брони (ReservationSteps / Bnovo) — с датами'], ['link', 'Ссылка на внешний модуль'], ['request', 'Заявка в WhatsApp / на e-mail']] }),
        field('Ссылка на модуль бронирования', H.booking, 'url', { ph: 'https://reservationsteps.ru/rooms/index/…' }), field('Язык модуля', H.booking, 'lang', { ph: 'ru' })),
      h('h2', {}, 'Аналитика'), h('div', { class: 'card' }, field('Номер счётчика Яндекс.Метрики', H.analytics, 'metrika_id', { type: 'number', hint: 'После публикации включится счётчик и плашка про cookie' })),
      h('h2', {}, 'Реквизиты'), h('div', { class: 'card' }, field('Юр. лицо', H.legal, 'name', { nullable: false }), h('div', { class: 'grid' }, field('ИНН', H.legal, 'inn'), field('ОГРН / ОГРНИП', H.legal, 'ogrn')), field('Индекс', H, 'postal_code'), field('Регион', H, 'region'))];
  },
  faq() {
    return [h('h1', {}, 'Частые вопросы'), listEditor(H.faq, (it) => [field('Вопрос', it, 'q'), field('Ответ', it, 'a', { type: 'textarea', rows: 3 })], () => ({ q: '', a: '' }), '+ Добавить вопрос')];
  },
  places() {
    H.arrival ||= { steps: [], airport: null, station: null };
    const steps = H.arrival.steps.map((s) => ({ s }));
    const syncSteps = () => { H.arrival.steps = steps.map((x) => x.s).filter(Boolean); };
    return [h('h1', {}, 'Рядом и такси'),
      h('h2', {}, 'Как проехать к входу (по шагам)'),
      listEditor(steps, (it) => field('Шаг', it, 's', { type: 'textarea', rows: 2, onchange: syncSteps }), () => ({ s: '' }), '+ Добавить шаг', syncSteps),
      h('h2', {}, 'Достопримечательности'), listEditor(H.places, (it) => [field('Название', it, 'name'), field('Описание', it, 'text'), coordsField('Координаты', it, 'coords')], () => ({ name: '', text: '', coords: null }), '+ Добавить место'),
      h('h2', {}, 'Такси'), listEditor(H.taxi, (it) => h('div', { class: 'grid' }, field('Название', it, 'name'), field('Подпись', it, 'text'), field('Ссылка', it, 'url')), () => ({ name: '', text: '', url: '' }), '+ Добавить такси')];
  },
};
function ratingCard() {
  const r = H.rating || { value: null, count: null, source: 'Яндекс', url: null };
  const sync = () => { H.rating = r.value ? r : null; };
  return h('div', { class: 'card', oninput: sync }, h('div', { class: 'grid' }, field('Оценка', r, 'value', { type: 'number', ph: '4.8' }), field('Отзывов', r, 'count', { type: 'number' }), field('Источник', r, 'source')), field('Ссылка на отзывы', r, 'url'));
}
function roomEditor(r) {
  const dir = `rooms/${r.slug}`;
  return [h('button', { class: 'btn sm back', type: 'button', onclick: () => { roomIdx = null; render(); } }, '← Все номера'),
    h('h1', {}, r.name || 'Номер'),
    h('div', { class: 'card' }, field('Название', r, 'name', { nullable: false, onchange: () => { $('h1', $('#view')).textContent = r.name; } }),
      h('div', { class: 'grid' }, field('Цена от, ₽ за ночь', r, 'price_from', { type: 'number', hint: 'Пусто — «Цена по датам»' }), field('Площадь, м²', r, 'area', { type: 'number' }), field('Гостей до', r, 'guests', { type: 'number' })),
      field('Кровати', r, 'beds', { ph: 'двуспальная кровать' }), field('Описание', r, 'text', { type: 'textarea', rows: 4 })),
    h('h2', {}, 'Фото номера'),
    r.slug && P[dir] ? photoGrid(dir) : h('p', { class: 'card muted' }, 'Нажмите «Сохранить», после этого можно будет добавить фото.'),
    h('h2', {}, ''),
    h('button', { class: 'btn danger wide', type: 'button', onclick: () => { if (confirm(`Удалить категорию «${r.name}» с сайта?`)) { H.rooms.splice(roomIdx, 1); roomIdx = null; setDirty(); render(); } } }, 'Удалить категорию')];
}

function render() {
  document.querySelectorAll('#tabs button').forEach((b) => b.setAttribute('aria-current', String(b.dataset.tab === tab)));
  $('#view').replaceChildren(...[views[tab]()].flat());
  $('#hotel-name').textContent = H.name;
}

// ---------- status / save / publish ----------
const fmtT = (t) => new Date(t).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
function renderStatus(changed) {
  if (changed) S.savedAt = Date.now();
  const el = $('#pub-status');
  if (S.status === 'building') el.replaceChildren(h('span', { class: 'badge' }, 'Публикую…'));
  else if (S.status === 'error') el.replaceChildren(h('span', { class: 'badge err' }, 'Ошибка публикации'));
  else if (dirty) el.replaceChildren(h('span', { class: 'badge' }, 'Не сохранено'));
  else if (S.savedAt > S.publishedAt) el.replaceChildren(h('span', { class: 'badge' }, 'Не опубликовано'));
  else el.replaceChildren(h('span', { class: 'badge ok' }, S.publishedAt ? `Опубликовано ${fmtT(S.publishedAt)}` : 'Сайт актуален'));
  $('#publish').disabled = S.status === 'building';
}
async function save() {
  const invalid = $('#view').querySelector(':invalid');
  if (invalid) { invalid.focus(); invalid.reportValidity(); toast('Исправьте поле с ошибкой'); return false; }
  $('#save').disabled = true;
  try { const r = await api('hotel', { method: 'PUT', json: H, headers: { 'X-Rev': REV } }); H = r.hotel; REV = r.rev; P = r.photos; setDirty(false); renderStatus(true); render(); toast('Сохранено. Нажмите «Опубликовать», чтобы изменения появились на сайте.'); return true; }
  catch (e) { toast(e.message); $('#save').disabled = false; return false; }
}
async function publish() {
  if (dirty && !(await save())) return;
  try { await api('publish', { method: 'POST' }); } catch (e) { toast(e.message); }
  S.status = 'building'; renderStatus();
  while (S.status === 'building') { await new Promise((ok) => setTimeout(ok, 2000)); S = await api('status').catch(() => S); }
  renderStatus();
  if (S.status === 'ok') toast('Готово — сайт обновлён');
  else { toast('Не удалось опубликовать'); $('#view').prepend(h('pre', { class: 'log' }, S.log || '')); }
}

// ---------- boot ----------
function showLogin() { $('#app').hidden = true; $('#login').hidden = false; }
async function boot() {
  try {
    const r = await api('hotel');
    H = r.hotel; REV = r.rev; P = r.photos; S = r.status;
    H.highlights ||= []; H.faq ||= []; H.places ||= []; H.taxi ||= [];
    $('#login').hidden = true; $('#app').hidden = false;
    $('#site-link').href = '/';
    render(); renderStatus();
    if (S.status === 'building') publish();
  } catch (e) { if (!$('#login').hidden) return; toast(e.message); }
}
$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try { await api('login', { method: 'POST', json: { password: e.target.password.value } }); e.target.reset(); $('#login-err').textContent = ''; boot(); }
  catch (err) { $('#login-err').textContent = err.message; }
});
$('#tabs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; tab = b.dataset.tab; roomIdx = null; render(); scrollTo(0, 0); });
$('#save').addEventListener('click', save);
$('#publish').addEventListener('click', publish);
$('#logout').addEventListener('click', async () => { await api('logout', { method: 'POST' }).catch(() => {}); location.reload(); });
addEventListener('beforeunload', (e) => { if (dirty) e.preventDefault(); });
boot();
