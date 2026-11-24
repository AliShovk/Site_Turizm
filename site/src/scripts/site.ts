declare global { interface Window { ym?: (...a: unknown[]) => void; __ym?: number } }

const goal = (name: string) => { if (window.ym && window.__ym) window.ym(window.__ym, 'reachGoal', name); };
document.addEventListener('click', (e) => {
  const el = (e.target as HTMLElement).closest<HTMLElement>('[data-goal]');
  if (el) goal(el.dataset.goal!);
});

// mobile menu
const burger = document.querySelector<HTMLButtonElement>('.burger');
const nav = document.getElementById('nav');
burger?.addEventListener('click', () => {
  const open = nav!.classList.toggle('open');
  burger.setAttribute('aria-expanded', String(open));
});

// booking form
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const ru = (s: string) => s.split('-').reverse().join('-');
const ruDots = (s: string) => s.split('-').reverse().join('.');
const nextDay = (s: string) => { const [y, m, d] = s.split('-').map(Number); return iso(new Date(y, m - 1, d + 1)); };
const book = document.getElementById('book') as HTMLFormElement | null;
if (book) {
  const fin = book.elements.namedItem('in') as HTMLInputElement;
  const fout = book.elements.namedItem('out') as HTMLInputElement;
  const today = new Date(); const tomorrow = new Date(Date.now() + 864e5);
  fin.min = iso(today); fin.value = iso(today);
  fout.min = iso(tomorrow); fout.value = iso(tomorrow);
  fin.addEventListener('change', () => {
    const next = nextDay(fin.value);
    fout.min = next;
    if (!fout.value || fout.value <= fin.value) fout.value = next;
  });
  book.addEventListener('submit', (e) => {
    e.preventDefault();
    const adults = (book.elements.namedItem('adults') as HTMLSelectElement).value;
    const d = book.dataset;
    let url: string;
    if (d.mode === 'bnovo') {
      const q = new URLSearchParams({ dfrom: ru(fin.value), dto: ru(fout.value), adults });
      if (d.lang) q.set('lang', d.lang);
      url = `${d.url}?${q}`;
      goal('book_search');
    } else if (d.mode === 'link') {
      url = d.link!;
      goal('book_click');
    } else {
      const text = `Здравствуйте! Хочу забронировать номер в ${d.hotel}: заезд ${ruDots(fin.value)}, выезд ${ruDots(fout.value)}, взрослых: ${adults}.`;
      url = d.wa ? `${d.wa}?text=${encodeURIComponent(text)}`
        : `mailto:${d.email}?subject=${encodeURIComponent('Заявка на бронирование')}&body=${encodeURIComponent(text)}`;
      goal('request_send');
    }
    window.open(url, url.startsWith('mailto:') ? '_self' : '_blank', 'noopener');
  });
}

// request form (contacts page) -> WhatsApp / e-mail
const req = document.getElementById('zayavka-form') as HTMLFormElement | null;
const zin = document.getElementById('z-in') as HTMLInputElement | null;
const zout = document.getElementById('z-out') as HTMLInputElement | null;
if (zin && zout) {
  zin.min = iso(new Date());
  const sync = () => {
    zout.min = zin.value ? nextDay(zin.value) : zin.min;
    zout.setCustomValidity(zin.value && zout.value && zout.value <= zin.value ? 'Дата выезда должна быть позже даты заезда' : '');
  };
  zin.addEventListener('change', sync); zout.addEventListener('change', sync); sync();
}
req?.addEventListener('submit', (e) => {
  e.preventDefault();
  const f = new FormData(req);
  const parts = [
    `Заявка с сайта ${req.dataset.hotel}`,
    `Имя: ${f.get('name')}`, `Телефон: ${f.get('phone')}`,
    f.get('in') ? `Заезд: ${ruDots(String(f.get('in')))}` : '',
    f.get('out') ? `Выезд: ${ruDots(String(f.get('out')))}` : '',
    f.get('room') ? `Номер: ${f.get('room')}` : '',
    f.get('msg') ? `Комментарий: ${f.get('msg')}` : '',
  ].filter(Boolean).join('\n');
  goal('request_send');
  const via = (e as SubmitEvent).submitter?.getAttribute('value');
  const url = via === 'email' ? `mailto:${req.dataset.email}?subject=${encodeURIComponent('Заявка на бронирование')}&body=${encodeURIComponent(parts)}`
    : `${req.dataset.wa}?text=${encodeURIComponent(parts)}`;
  window.open(url, via === 'email' ? '_self' : '_blank', 'noopener');
});

// room gallery thumbs
document.querySelectorAll<HTMLElement>('[data-gallery]').forEach((g) => {
  const main = g.querySelector<HTMLImageElement>('.gal-main img')!;
  g.querySelectorAll<HTMLButtonElement>('.gal-th button').forEach((b) => b.addEventListener('click', () => {
    const img = b.querySelector('img')!;
    main.srcset = b.dataset.srcset || ''; main.src = b.dataset.src || img.src;
    g.querySelectorAll('.gal-th button').forEach((x) => x.setAttribute('aria-current', String(x === b)));
    main.closest('a')!.setAttribute('data-index', b.dataset.index || '0');
  }));
});

// lightbox
const lb = document.getElementById('lb')!;
const lbImg = lb.querySelector('img')!;
const lbCap = lb.querySelector<HTMLElement>('.cap')!;
let set: HTMLAnchorElement[] = []; let idx = 0;
const show = (i: number) => {
  idx = (i + set.length) % set.length;
  lbImg.src = set[idx].href; lbImg.alt = set[idx].dataset.cap || '';
  lbCap.textContent = `${set[idx].dataset.cap || ''} · ${idx + 1} / ${set.length}`;
};
document.addEventListener('click', (e) => {
  const a = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[data-lb]');
  if (!a) return;
  e.preventDefault();
  set = Array.from(document.querySelectorAll<HTMLAnchorElement>(`a[data-lb="${a.dataset.lb}"]:not([data-lb-skip])`));
  const start = a.dataset.index ? Number(a.dataset.index) : set.indexOf(a);
  lb.classList.add('open'); document.body.style.overflow = 'hidden'; show(Math.max(0, start));
});
const close = () => { lb.classList.remove('open'); document.body.style.overflow = ''; };
lb.querySelector('.x')!.addEventListener('click', close);
lb.querySelector('.pv')!.addEventListener('click', () => show(idx - 1));
lb.querySelector('.nx')!.addEventListener('click', () => show(idx + 1));
lb.addEventListener('click', (e) => { if (e.target === lb) close(); });
document.addEventListener('keydown', (e) => {
  if (!lb.classList.contains('open')) return;
  if (e.key === 'Escape') close(); if (e.key === 'ArrowLeft') show(idx - 1); if (e.key === 'ArrowRight') show(idx + 1);
});

// cookie notice
const ck = document.getElementById('cookie');
if (ck && !localStorage.getItem('cookie-ok')) ck.classList.add('show');
ck?.querySelector('button')!.addEventListener('click', () => { localStorage.setItem('cookie-ok', '1'); ck!.classList.remove('show'); });

export {};
