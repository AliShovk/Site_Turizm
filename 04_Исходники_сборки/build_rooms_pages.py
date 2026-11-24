# -*- coding: utf-8 -*-
"""1) Галерея фото номеров отеля «Проспект». 2) Вставка реальных номеров в прототип сайта."""
import base64, io, json, os, re, glob
from PIL import Image

BASE = "photos/rp"
meta = json.load(open(f"{BASE}/meta.json", encoding="utf-8"))

# порядок и человеческие названия
ROOMS = []
ORDER = [
    ("r3", "Стандарт с двуспальной кроватью", "21 м²", "двуспальная кровать"),
    ("r2", "Стандарт с двумя раздельными кроватями", "21 м²", "две односпальные"),
    ("r1", "Улучшенный двухместный", "25 м²", "двуспальная или две односпальные"),
    ("r4", "Двухместный с террасой", "23 м²", "своя терраса"),
    ("r5", "Семейный", "30 м²", "для семьи с ребёнком"),
    ("r6", "Семейный Делюкс", "41 м²", "больше пространства"),
    ("r7", "Семейный люкс", "42 м²", "две зоны, до 4 гостей"),
]
for d, name, area, beds in ORDER:
    files = sorted(glob.glob(f"{BASE}/{d}/*.jpg"))
    if not files:
        continue
    ROOMS.append(dict(dir=d, name=name, area=area, beds=beds, files=files))


def b64(path, width=1200, q=74):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > width:
        im = im.resize((width, int(h * width / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- галерея
sections = []
for i, r in enumerate(ROOMS, 1):
    pics = "".join(
        f'<figure><img loading="lazy" src="data:image/jpeg;base64,{b64(p)}" alt="{r["name"]} — фото {j}" '
        f'onclick="zoom(this)"><figcaption>{j}</figcaption></figure>' for j, p in enumerate(r["files"][:5], 1))
    sections.append(f"""
  <section class="room">
    <div class="rhead">
      <div class="rnum">{i}</div>
      <div>
        <h2>{r['name']}</h2>
        <div class="rsub">{r['area']} · {r['beds']} · {len(r['files'])} фото</div>
      </div>
    </div>
    <div class="strip">{pics}</div>
  </section>""")

GAL = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Фото номеров — отель «Проспект», Кисловодск</title>
<style>
:root{{--ink:#15171b;--mut:#6b7280;--line:#e5e7eb;--brand:#1c2b45;--gold:#b08448}}
*{{box-sizing:border-box}}
body{{margin:0;background:#f6f7f9;color:var(--ink);font:16px/1.55 -apple-system,"Segoe UI",Roboto,Arial,sans-serif;padding:26px 18px 60px}}
.wrap{{max-width:1180px;margin:0 auto}}
h1{{font-size:30px;line-height:1.2;margin:0 0 8px}}
.lead{{color:var(--mut);max-width:84ch;margin:0 0 22px}}
.room{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-bottom:20px}}
.rhead{{display:flex;gap:14px;align-items:center;margin-bottom:14px}}
.rnum{{width:36px;height:36px;flex:0 0 36px;border-radius:50%;background:var(--brand);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}}
h2{{font-size:20px;margin:0;line-height:1.25}}
.rsub{{color:var(--mut);font-size:13.5px}}
.strip{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}}
figure{{margin:0;position:relative;cursor:zoom-in}}
figure img{{width:100%;height:160px;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block}}
figcaption{{position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.55);color:#fff;font-size:11px;border-radius:6px;padding:1px 7px}}
.note{{background:#fff8e6;border:1px solid #f0dda6;border-radius:14px;padding:14px 18px;margin:0 0 24px;font-size:14.5px}}
.note b{{color:#7a5200}}
#lb{{position:fixed;inset:0;background:rgba(9,12,20,.92);display:none;align-items:center;justify-content:center;z-index:99;padding:20px}}
#lb.on{{display:flex}}
#lb img{{max-width:96vw;max-height:92vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.5)}}
#lb .x{{position:absolute;top:16px;right:22px;color:#fff;font-size:34px;cursor:pointer;line-height:1}}
footer{{color:var(--mut);font-size:12.8px;text-align:center;margin-top:22px}}
@media(max-width:600px){{figure img{{height:130px}}}}
</style></head><body><div class="wrap">
<h1>Фото номеров: отель «Проспект», Кисловодск</h1>
<p class="lead">Семь категорий, {sum(len(r['files']) for r in ROOMS)} фотографий в исходном разрешении 1024×683 — то есть их уже можно ставить на сайт, не переснимая. Источник — публичные карточки отеля (101hotels / ФСА).</p>
<div class="note"><b>Важно перед публикацией:</b> это фото из открытых карточек, а не от самого отеля. Для рабочего сайта нужно письменное разрешение собственника на использование — либо комплект исходников от администратора. Показываю их как доказательство: фотоматериал у объекта есть, и он нормальный.</div>
{''.join(sections)}
<footer>Источник фото: карточка отеля «Проспект» на 101hotels (данные ФСА) · 24.11.2026</footer>
</div>
<div id="lb" onclick="this.classList.remove('on')"><span class="x">×</span><img id="lbi" src="" alt=""></div>
<script>
function zoom(el){{document.getElementById('lbi').src=el.src;document.getElementById('lb').classList.add('on');}}
</script>
</body></html>"""

GAL_PATH = r"C:\Users\Ali PC\Desktop\Фото_номеров_Проспект.html"
open(GAL_PATH, "w", encoding="utf-8").write(GAL)
print("галерея:", GAL_PATH, round(os.path.getsize(GAL_PATH) / 1024), "KB")

# ---------------------------------------------------------------- прототип: реальные номера
p = "build_proto_prospekt.py"
s = open(p, encoding="utf-8").read()

cards = []
for r in ROOMS[:4]:
    first = b64(r["files"][0], width=760)
    price = "от 6 200 ₽" if r["dir"] == "r3" else "цена по датам"
    cards.append(f'''      <article class="room">
        <img src="data:image/jpeg;base64,{first}" alt="{r['name']}">
        <div class="room-b">
          <h3>{r['name']}</h3>
          <div class="feat"><span class="chip">{r['area']}</span><span class="chip">{r['beds']}</span></div>
          <div class="price"><b>{price}</b><span>{'' if price.startswith('от') else 'смотрите в календаре'}</span></div>
          <a class="btn btn-primary" href="https://reservationsteps.ru/rooms/index/1b6b0db6-12f8-4c54-908e-0e654b11916f?lang=ru" target="_blank" rel="noopener">Забронировать</a>
        </div>
      </article>''')

new_section = ('    <div class="rooms">\n' + "\n".join(cards) + "\n    </div>\n"
               '    <div class="note">Показаны 4 из 7 категорий. Все фото — реальные, из карточек отеля.</div>\n'
               '    <p style="margin:14px 0 0"><a class="btn btn-ghost" href="' + GAL_PATH + '">Посмотреть все фото номеров (7 категорий, 33 фото)</a></p>\n')

start = s.find('    <div class="rooms">')
end = s.find('    <div class="note">Цены и категории в прототипе', start)
assert start > 0 and end > start, (start, end)
s = s[:start] + new_section + "  " + s[end:]

# сетка под 4 карточки + ссылка на галерею и заголовок раздела
s = s.replace(".rooms{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}",
              ".rooms{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px}}")
s = s.replace("<h2>Номера</h2>\n    <p class=\"sub\">Каждая карточка — со своими фото, ценой и составом. Гость видит всё сразу и не звонит «уточнить».</p>",
              "<h2>Номера</h2>\n    <p class=\"sub\">Семь категорий, у каждой свои фотографии и метраж. Гость выбирает глазами и сразу видит цену — без «позвоните, уточним».</p>")
open(p, "w", encoding="utf-8").write(s)
print("прототип обновлён")
