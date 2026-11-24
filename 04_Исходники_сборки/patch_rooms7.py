# -*- coding: utf-8 -*-
"""Ставит на прототип сайта все 7 категорий номеров с фото-галереями."""
import base64, io, glob, json, os, re
from PIL import Image

BASE = "photos/rp"
ORDER = [
    ("r3", "Стандарт с двуспальной кроватью", "21 м²", "двуспальная кровать", True),
    ("r2", "Стандарт с двумя раздельными кроватями", "21 м²", "две односпальные", False),
    ("r1", "Улучшенный двухместный", "25 м²", "двуспальная или две односпальные", False),
    ("r4", "Двухместный с террасой", "23 м²", "своя терраса", False),
    ("r5", "Семейный", "30 м²", "подходит для семьи с ребёнком", False),
    ("r6", "Семейный Делюкс", "41 м²", "больше пространства и мест для багажа", False),
    ("r7", "Семейный люкс", "42 м²", "две зоны, размещение до 4 гостей", False),
]


def b64(path, width=760, q=72):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > width:
        im = im.resize((width, int(h * width / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


BOOK = "https://reservationsteps.ru/rooms/index/1b6b0db6-12f8-4c54-908e-0e654b11916f?lang=ru"
cards = []
for d, name, area, beds, cheapest in ORDER:
    files = sorted(glob.glob(f"{BASE}/{d}/*.jpg"))
    if not files:
        continue
    main = b64(files[0], 820, 74)
    thumbs = [b64(f, 240, 58) for f in files[:4]]
    th = "".join(f'<img src="data:image/jpeg;base64,{t}" alt="" onclick="setMain(this,event)">' for t in thumbs)
    price = "от 6 200 ₽" if cheapest else "по датам"
    price_sub = "/ ночь" if cheapest else "календарь брони"
    cards.append(f'''      <article class="room">
        <div class="gal">
          <img class="main" src="data:image/jpeg;base64,{main}" alt="{name}">
          <div class="thumbs">{th}</div>
        </div>
        <div class="room-b">
          <h3>{name}</h3>
          <div class="feat"><span class="chip">{area}</span><span class="chip">{beds}</span></div>
          <div class="price"><b>{price}</b><span>{price_sub}</span></div>
          <a class="btn btn-primary" href="{BOOK}" target="_blank" rel="noopener">Забронировать</a>
        </div>
      </article>''')

block = ('    <div class="rooms">\n' + "\n".join(cards) + "\n    </div>\n"
         '    <div class="note">Все 7 категорий — реальные: названия, площади и фото взяты из карточки отеля. '
         'Цену по каждой категории считает календарь брони: в Кисловодске она зависит от дат.</div>\n')

p = "build_proto_prospekt.py"
s = open(p, encoding="utf-8").read()
start = s.find('    <div class="rooms">')
end = s.find('      <div class="note">Цены и категории в прототипе', start)
assert start > 0 and end > start
s = s[:start] + block + s[end:]

# CSS: галерея внутри карточки
old_css = ".room img{{height:200px;object-fit:cover;width:100%}}"
new_css = (".gal{{position:relative}}\n"
           ".room img.main{{height:215px;object-fit:cover;width:100%;display:block}}\n"
           ".thumbs{{display:flex;gap:6px;padding:8px 10px 0;position:absolute;top:0;right:0}}\n"
           ".thumbs img{{width:46px;height:34px;object-fit:cover;border-radius:6px;border:2px solid rgba(255,255,255,.85);"
           "cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.35)}}\n"
           ".thumbs img:hover{{border-color:#fff;transform:scale(1.05)}}")
assert old_css in s
s = s.replace(old_css, new_css)

# JS переключения фото
s = s.replace("<script>\n  var m = L.map('map', {{scrollWheelZoom:false}})",
              "<script>\n  function setMain(t,e){{e.stopPropagation();var c=t.closest('.room');c.querySelector('img.main').src=t.src;}}\n"
              "  var m = L.map('map', {{scrollWheelZoom:false}})")

# заголовок раздела
s = s.replace("<p class=\"sub\">Семь категорий, у каждой свои фотографии и метраж. Гость выбирает глазами и сразу видит цену — без «позвоните, уточним».</p>",
              "<p class=\"sub\">Семь реальных категорий с фотографиями и метражом. Фото переключаются прямо в карточке, цена считается по датам заезда.</p>")

open(p, "w", encoding="utf-8").write(s)
print("патч применён, карточек:", len(cards))
