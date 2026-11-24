// Админка сайта отеля: правит hotels/<slug>.yaml и фото в src/assets, пересобирает и публикует сайт.
import http from 'node:http';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import sharp from 'sharp';

const SITE = path.resolve(process.env.SITE_DIR || path.join(path.dirname(fileURLToPath(import.meta.url)), '..'));
const SLUG = process.env.HOTEL || 'prospekt';
const PORT = Number(process.env.PORT || 8097);
const HOST = process.env.HOST || '127.0.0.1';
const PASSWORD = process.env.ADMIN_PASSWORD || '';
const SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');
const PUBLISH_DIR = process.env.PUBLISH_DIR ? path.resolve(process.env.PUBLISH_DIR) : '';
const PUBLIC = path.join(SITE, 'admin', 'public');
const YAML_FILE = path.join(SITE, 'hotels', `${SLUG}.yaml`);
const HISTORY = path.join(SITE, 'hotels', '.history');
const ASSETS = path.join(SITE, 'src', 'assets', 'hotels', SLUG);
const STATE_FILE = path.join(SITE, 'hotels', `.${SLUG}-admin.json`);
const SESSION_TTL = 7 * 24 * 3600 * 1000;
const IMG_RE = /^[a-z0-9][a-z0-9-]*\.(jpe?g|png|webp)$/;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,60}$/;

if (!PASSWORD) { console.error('ADMIN_PASSWORD is required'); process.exit(1); }

// ---------- state ----------
const state = { build: { status: 'idle', log: '', started: null, finished: null }, savedAt: 0, publishedAt: 0 };
try { Object.assign(state, JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')), { build: { status: 'idle', log: '' } }); } catch {}
const persist = () => fsp.writeFile(STATE_FILE, JSON.stringify({ savedAt: state.savedAt, publishedAt: state.publishedAt }));

// ---------- auth ----------
const sign = (v) => crypto.createHmac('sha256', SECRET).update(v).digest('base64url');
const eq = (a, b) => { const x = Buffer.from(a), y = Buffer.from(b); return x.length === y.length && crypto.timingSafeEqual(x, y); };
const makeToken = () => { const exp = String(Date.now() + SESSION_TTL); return `${exp}.${sign(exp)}`; };
const validToken = (t) => { const [exp, mac] = String(t || '').split('.'); return !!exp && !!mac && eq(mac, sign(exp)) && Number(exp) > Date.now(); };
const cookies = (req) => Object.fromEntries((req.headers.cookie || '').split(';').map((c) => c.trim().split('=').map(decodeURIComponent)).filter((p) => p[0]));
const attempts = new Map();
const tooMany = (ip) => { const a = (attempts.get(ip) || []).filter((t) => t > Date.now() - 15 * 60e3); attempts.set(ip, a); return a.length >= 10; };

// ---------- helpers ----------
const send = (res, code, body, headers = {}) => {
  const isBuf = Buffer.isBuffer(body);
  res.writeHead(code, { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...(isBuf ? {} : { 'Content-Type': 'application/json; charset=utf-8' }), ...headers });
  res.end(isBuf ? body : JSON.stringify(body));
};
const readBody = (req, limit) => new Promise((ok, fail) => {
  const chunks = []; let n = 0;
  req.on('data', (c) => { n += c.length; if (n > limit) { fail(Object.assign(new Error('Файл слишком большой'), { code: 413 })); req.destroy(); } else chunks.push(c); });
  req.on('end', () => ok(Buffer.concat(chunks))); req.on('error', fail);
});
const readJson = async (req) => JSON.parse((await readBody(req, 2e6)).toString('utf8') || '{}');
const bad = (msg) => Object.assign(new Error(msg), { code: 400 });

const loadHotel = async () => yaml.load(await fsp.readFile(YAML_FILE, 'utf8'));
async function writeHotel(h) {
  await fsp.mkdir(HISTORY, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  await fsp.copyFile(YAML_FILE, path.join(HISTORY, `${SLUG}-${stamp}.yaml`)).catch(() => {});
  const old = (await fsp.readdir(HISTORY)).filter((f) => f.startsWith(SLUG + '-')).sort();
  for (const f of old.slice(0, Math.max(0, old.length - 50))) await fsp.unlink(path.join(HISTORY, f));
  const head = '# Конфиг сайта отеля. Редактируется в админке /admin/ — правки руками тоже допустимы.\n# Поля со значением null на сайте не выводятся.\n\n';
  const tmp = YAML_FILE + '.tmp';
  await fsp.writeFile(tmp, head + yaml.dump(h, { lineWidth: 120, noRefs: true, quotingType: '"' }));
  await fsp.rename(tmp, YAML_FILE);
  state.savedAt = Date.now(); await persist();
}

function dirPath(dir, h) {
  if (dir === 'hotel') return path.join(ASSETS, 'hotel');
  const m = /^rooms\/([a-z0-9-]+)$/.exec(String(dir));
  if (m && h.rooms.some((r) => r.slug === m[1])) return path.join(ASSETS, 'rooms', m[1]);
  throw bad('Неизвестная папка фото');
}
const byName = (a, b) => a.localeCompare(b, 'en', { numeric: true });
const listDir = async (p) => (await fsp.readdir(p).catch(() => [])).filter((f) => IMG_RE.test(f)).sort(byName);
async function photos(h) {
  const out = { hotel: await listDir(path.join(ASSETS, 'hotel')) };
  for (const r of h.rooms) out[`rooms/${r.slug}`] = await listDir(path.join(ASSETS, 'rooms', r.slug));
  return out;
}

// ---------- validation of edited config ----------
const str = (v, max = 2000) => (v == null || v === '' ? null : String(v).slice(0, max));
const num = (v) => (v == null || v === '' ? null : Number.isFinite(Number(v)) ? Number(v) : null);
const safeUrl = (v, name, schemes = /^https:\/\//) => { const s = str(v, 500); if (s && !schemes.test(s)) throw bad(`Ссылка «${name}» должна начинаться с https://`); return s; };
const coords = (v) => (Array.isArray(v) && v.length === 2 && v.every((x) => Number.isFinite(Number(x))) ? v.map(Number) : null);
const translit = (s) => {
  const m = { а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'ts',ч:'ch',ш:'sh',щ:'sch',ъ:'',ы:'y',ь:'',э:'e',ю:'yu',я:'ya' };
  return String(s).toLowerCase().split('').map((c) => m[c] ?? c).join('').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 50) || 'nomer';
};
function clean(input, prev) {
  const h = structuredClone(prev);
  const req = (v, name) => { const s = str(v); if (!s) throw bad(`Заполните поле «${name}»`); return s; };
  h.name = req(input.name, 'Название'); h.short_name = req(input.short_name, 'Короткое название');
  h.type = str(input.type, 60) ?? h.type; h.stars = num(input.stars); h.city = req(input.city, 'Город');
  h.city_prep = str(input.city_prep, 80) ?? h.city_prep; h.address = req(input.address, 'Адрес');
  h.postal_code = str(input.postal_code, 12); h.region = str(input.region, 120);
  h.coords = coords(input.coords) ?? h.coords; h.rooms_total = num(input.rooms_total); h.price_from = num(input.price_from);
  h.rating = input.rating && num(input.rating.value) ? { value: num(input.rating.value), count: num(input.rating.count) ?? 0, source: str(input.rating.source, 40) ?? 'Яндекс', url: safeUrl(input.rating.url, 'Ссылка на отзывы') } : null;
  const c = input.contacts || {};
  h.contacts = { phone: req(c.phone, 'Телефон'), phone_display: str(c.phone_display, 40) ?? c.phone, whatsapp: str(c.whatsapp, 20)?.replace(/\D/g, '') || null, telegram: str(c.telegram, 60), email: str(c.email, 120) };
  const l = input.legal || {};
  h.legal = { name: req(l.name, 'Юр. лицо'), inn: str(l.inn, 12), ogrn: str(l.ogrn, 15) };
  const b = input.booking || {};
  const provider = ['bnovo', 'link', 'request'].includes(b.provider) ? b.provider : 'request';
  const url = str(b.url, 500);
  if (url && !/^https:\/\//.test(url)) throw bad('Ссылка на бронирование должна начинаться с https://');
  h.booking = { provider, url, ...(str(b.lang, 5) ? { lang: str(b.lang, 5) } : {}) };
  h.analytics = { metrika_id: num(input.analytics?.metrika_id) };
  h.seo = { title: req(input.seo?.title, 'SEO-заголовок'), description: req(input.seo?.description, 'SEO-описание') };
  h.hero = { image: str(input.hero?.image, 120) ?? h.hero.image, title: req(input.hero?.title, 'Заголовок на главной'), lead: str(input.hero?.lead, 400) ?? '' };
  h.about = str(input.about, 4000) ?? '';
  h.highlights = (input.highlights || []).filter((x) => str(x.title)).slice(0, 8).map((x) => ({ title: str(x.title, 60), text: str(x.text, 200) ?? '' }));
  const seen = new Set();
  h.rooms = (input.rooms || []).map((r) => {
    let slug = SLUG_RE.test(r.slug || '') ? r.slug : translit(r.name);
    while (seen.has(slug)) slug += '-2';
    seen.add(slug);
    return { slug, name: req(r.name, 'Название номера'), area: num(r.area), beds: str(r.beds, 80), guests: num(r.guests), price_from: num(r.price_from), text: str(r.text, 1000) ?? '' };
  });
  if (!h.rooms.length) throw bad('Нужен хотя бы один номер');
  h.faq = (input.faq || []).filter((x) => str(x.q)).map((x) => ({ q: str(x.q, 300), a: str(x.a, 2000) ?? '' }));
  h.places = (input.places || []).filter((x) => str(x.name) && coords(x.coords)).map((x) => ({ name: str(x.name, 80), text: str(x.text, 300) ?? '', coords: coords(x.coords) }));
  h.taxi = (input.taxi || []).filter((x) => str(x.name) && str(x.url)).map((x) => ({ name: str(x.name, 40), text: str(x.text, 120) ?? '', url: safeUrl(x.url, x.name, /^(https:\/\/|tel:\+?[\d\s()-]+$)/) }));
  const a = input.arrival || {};
  h.arrival = { ...h.arrival, steps: (a.steps || []).map((s) => str(s, 500)).filter(Boolean) };
  return h;
}

// ---------- build & publish ----------
function publish() {
  if (state.build.status === 'building') return false;
  state.build = { status: 'building', log: '', started: Date.now(), finished: null };
  const started = Date.now();
  const log = (s) => { state.build.log = (state.build.log + s).slice(-6000); };
  const p = spawn(process.execPath, [path.join(SITE, 'node_modules', 'astro', 'astro.js'), 'build'], { cwd: SITE, env: { ...process.env, HOTEL: SLUG, ASTRO_TELEMETRY_DISABLED: '1' } });
  p.stdout.on('data', (d) => log(d.toString())); p.stderr.on('data', (d) => log(d.toString()));
  p.on('close', async (code) => {
    try {
      if (code !== 0) throw new Error(`Сборка завершилась с кодом ${code}`);
      if (PUBLISH_DIR) {
        const next = PUBLISH_DIR + '.next', prev = PUBLISH_DIR + '.prev';
        await fsp.rm(next, { recursive: true, force: true });
        await fsp.cp(path.join(SITE, 'dist'), next, { recursive: true });
        await fsp.rm(prev, { recursive: true, force: true });
        await fsp.rename(PUBLISH_DIR, prev).catch(() => {});
        await fsp.rename(next, PUBLISH_DIR);
        await fsp.rm(prev, { recursive: true, force: true });
      }
      state.publishedAt = started; await persist();
      state.build.status = 'ok';
    } catch (e) { log('\n' + e.message); state.build.status = 'error'; }
    state.build.finished = Date.now();
  });
  return true;
}

// ---------- routes ----------
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml' };
const thumbs = new Map();

async function handle(req, res) {
  const u = new URL(req.url, 'http://x');
  let p = u.pathname.replace(/^\/admin/, '') || '/';
  const ip = req.headers['x-real-ip'] || req.socket.remoteAddress;

  if (req.method === 'GET' && !p.startsWith('/api/')) {
    if (p === '/') p = '/index.html';
    const f = path.join(PUBLIC, path.normalize(p).replace(/^(\.\.[/\\])+/, ''));
    if (!f.startsWith(PUBLIC + path.sep)) return send(res, 404, { error: 'not found' });
    const data = await fsp.readFile(f).catch(() => null);
    if (!data) return send(res, 404, { error: 'not found' });
    return send(res, 200, data, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Content-Security-Policy': "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'", 'Referrer-Policy': 'no-referrer' });
  }

  if (p === '/api/login' && req.method === 'POST') {
    if (tooMany(ip)) return send(res, 429, { error: 'Слишком много попыток. Подождите 15 минут.' });
    const tries = attempts.get(ip), at = Date.now();
    tries.push(at);
    const { password } = await readJson(req);
    if (!eq(crypto.createHash('sha256').update(String(password || '')).digest('hex'), crypto.createHash('sha256').update(PASSWORD).digest('hex'))) {
      return send(res, 401, { error: 'Неверный пароль' });
    }
    tries.splice(tries.indexOf(at), 1);
    return send(res, 200, { ok: true }, { 'Set-Cookie': `adm=${makeToken()}; Path=/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_TTL / 1000}` });
  }
  if (p === '/api/logout' && req.method === 'POST' && req.headers['x-admin'] === '1') return send(res, 200, { ok: true }, { 'Set-Cookie': 'adm=; Path=/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=0' });
  if (!validToken(cookies(req).adm)) return send(res, 401, { error: 'Нужен вход' });
  if (req.method !== 'GET' && req.headers['x-admin'] !== '1') return send(res, 403, { error: 'forbidden' });

  const h = await loadHotel();
  if (p === '/api/hotel' && req.method === 'GET') {
    return send(res, 200, { hotel: h, photos: await photos(h), status: { ...state.build, savedAt: state.savedAt, publishedAt: state.publishedAt } });
  }
  if (p === '/api/hotel' && req.method === 'PUT') {
    const next = clean(await readJson(req), h);
    await writeHotel(next);
    return send(res, 200, { hotel: next, photos: await photos(next) });
  }
  if (p === '/api/photo' && req.method === 'GET') {
    const dir = dirPath(u.searchParams.get('dir'), h), file = u.searchParams.get('file') || '';
    if (!IMG_RE.test(file)) throw bad('bad file');
    const f = path.join(dir, file);
    const st = await fsp.stat(f).catch(() => null);
    if (!st) return send(res, 404, { error: 'not found' });
    const key = f + st.mtimeMs;
    if (!thumbs.has(key)) { if (thumbs.size > 500) thumbs.clear(); thumbs.set(key, await sharp(f).rotate().resize(480, 480, { fit: 'cover' }).webp({ quality: 72 }).toBuffer()); }
    return send(res, 200, thumbs.get(key), { 'Content-Type': 'image/webp', 'Cache-Control': 'private, max-age=86400' });
  }
  if (p === '/api/photo' && req.method === 'POST') {
    const dir = dirPath(u.searchParams.get('dir'), h);
    const buf = await readBody(req, 30e6);
    const meta = await sharp(buf).metadata().catch(() => null);
    if (!meta || !['jpeg', 'png', 'webp', 'heif', 'avif'].includes(meta.format)) throw bad('Это не фото (нужен JPG, PNG, WEBP или HEIC)');
    await fsp.mkdir(dir, { recursive: true });
    const files = await listDir(dir);
    const prefix = path.basename(dir);
    const max = files.reduce((m, f) => Math.max(m, Number(/-(\d+)\.\w+$/.exec(f)?.[1] || 0)), 0);
    const name = `${prefix}-${max + 1}.jpg`;
    await sharp(buf).rotate().resize(2400, 2400, { fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 84, mozjpeg: true }).toFile(path.join(dir, name));
    state.savedAt = Date.now(); await persist();
    return send(res, 200, { file: name, photos: await photos(h) });
  }
  if (p === '/api/photo' && req.method === 'DELETE') {
    const { dir: d, file } = await readJson(req);
    const dir = dirPath(d, h);
    if (!IMG_RE.test(file || '')) throw bad('bad file');
    const trash = path.join(SITE, 'hotels', '.trash', SLUG, d);
    await fsp.mkdir(trash, { recursive: true });
    await fsp.rename(path.join(dir, file), path.join(trash, `${Date.now()}-${file}`));
    state.savedAt = Date.now(); await persist();
    return send(res, 200, { photos: await photos(h) });
  }
  if (p === '/api/photo/order' && req.method === 'POST') {
    const { dir: d, files } = await readJson(req);
    const dir = dirPath(d, h);
    const cur = await listDir(dir);
    if (!Array.isArray(files) || files.length !== cur.length || [...files].sort().join() !== [...cur].sort().join()) throw bad('Список фото устарел, обновите страницу');
    const prefix = path.basename(dir), tag = Date.now();
    const renamed = {};
    for (const [i, f] of files.entries()) await fsp.rename(path.join(dir, f), path.join(dir, `tmp${tag}-${i}${path.extname(f)}`));
    for (const [i, f] of files.entries()) {
      const to = `${prefix}-${i + 1}${path.extname(f).toLowerCase()}`;
      await fsp.rename(path.join(dir, `tmp${tag}-${i}${path.extname(f)}`), path.join(dir, to));
      renamed[f] = to;
    }
    if (d === 'hotel') {
      const old = h.hero.image.replace(/^hotel\//, '');
      if (renamed[old]) { h.hero.image = `hotel/${renamed[old]}`; await writeHotel(h); }
    }
    state.savedAt = Date.now(); await persist();
    return send(res, 200, { hotel: h, photos: await photos(h) });
  }
  if (p === '/api/publish' && req.method === 'POST') {
    if (!publish()) return send(res, 409, { error: 'Сборка уже идёт' });
    return send(res, 202, { ok: true });
  }
  if (p === '/api/status') return send(res, 200, { ...state.build, savedAt: state.savedAt, publishedAt: state.publishedAt });
  return send(res, 404, { error: 'not found' });
}

http.createServer((req, res) => {
  handle(req, res).catch((e) => {
    if (!e.code || e.code >= 500 || typeof e.code !== 'number') console.error(e);
    if (!res.headersSent) send(res, typeof e.code === 'number' ? e.code : 500, { error: typeof e.code === 'number' ? e.message : 'Ошибка сервера' });
  });
}).listen(PORT, HOST, () => console.log(`admin on http://${HOST}:${PORT}/admin/ (site ${SITE}, hotel ${SLUG})`));
