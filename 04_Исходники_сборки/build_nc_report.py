# -*- coding: utf-8 -*-
import json, html, os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

data = {o["host"]: o for o in json.load(open("nc_final.json", encoding="utf-8")) if o.get("host")}

# (host, категория, что не так (человеческим языком), первый заход)
LEADS = [
 ("nok-juravli.ru", "ДОМЕН УВЕДЁН",
  "Домен из реестра ФСА (nok-juravli.ru) сейчас отдаёт азартный сайт: редирект на crownthai-kazan.ru с «Zooma Casino». Отель на 82 номера, 453 отзыва, 4,5 — а по его адресу в интернете казино.",
  "«Ваш домен nok-juravli.ru сейчас показывает казино вместо отеля. Это видно всем, кто ищет вас по названию. Я делаю сайты для гостиниц — давайте закроем это за неделю»"),
 ("al-firay.ru", "ДОМЕН УВЕДЁН",
  "al-firay.ru показывает сайт казино Coinplay («официальный сайт и зеркало»). Сайт не обновлялся с 2021 года — похоже, домен просто бросили и его заняли.",
  "«Сайт Аль Фирай сейчас — страница казино. Гость, который ищет вас, попадает туда. Покажу, как выглядит со стороны, и предложу замену»"),
 ("metropolderbent.ru", "ДОМЕН УВЕДЁН",
  "metropolderbent.ru отдаёт casino-сайт Dragon Money. Отель 4,7 с 319 отзывами остался без своего сайта полностью.",
  "«На вашем домене сейчас казино Dragon Money. Плюс: домен живой, его можно вернуть и поставить нормальный сайт отеля»"),
 ("xn----7sbcqc7aadz4b8g.xn--p1ai", "ДОМЕН УВЕДЁН",
  "Официальный сайт «Беллы» (база отдыха на 41 номер, 311 отзывов) теперь PokerStars. Плюс страница грузится 25 секунд.",
  "«Сайт вашей базы сейчас — покер-рум. И грузится 25 секунд. Это не сайт, это антиреклама»"),
 ("edelveis09.ru", "САЙТ МЁРТВ",
  "Домен не резолвится вообще (проверено через DNS 8.8.8.8): сайта нет, сервер не отвечает. Гостиничный комплекс на 65 номеров, 544 отзыва, 4,5.",
  "«Ваш домен edelveis09.ru не открывается — его нет в DNS. Гости ищут вас и не находят ничего, кроме агрегаторов»"),
 ("shahristan.ru", "САЙТ МЁРТВ",
  "Домен не существует (нет DNS-записи). При этом 609 отзывов и 4,4 — объект в Дербенте работает и востребован.",
  "«Домен shahristan.ru не существует — сайта фактически нет. При 600 отзывах это потерянные прямые брони»"),
 ("hoteladenium.ru", "САЙТ МЁРТВ",
  "Домен не резолвится. Отель 4,7, 393 отзыва, 20 номеров — сайта нет.",
  "«Ваш домен не открывается. Скорее всего, его не продлили. Могу поднять сайт на новом домене за неделю»"),
 ("otel-kosmos-essentuki.com", "САЙТ МЁРТВ",
  "Домен не резолвится: сайта нет. 31 номер, 382 отзыва, 4,4.",
  "«Сайт otel-kosmos-essentuki.com не существует. Гости находят вас только в агрегаторах — а там комиссия»"),
 ("topolyahotel.ru", "САЙТ МЁРТВ",
  "Домен не резолвится. Мини-отель 4,6 с 364 отзывами без сайта.",
  "«Домена topolyahotel.ru больше нет. Зато есть 364 отзыва — спрос есть, канала прямых продаж нет»"),
 ("art.hotel.essentuki.ru", "САЙТ НЕ ОТВЕЧАЕТ",
  "Сайт не отвечает ни по https, ни по http (проверял четыре раза, с разными таймаутами). Поддомен на чужом домене — типичная история «сделали один раз и забыли».",
  "«Ваш сайт art.hotel.essentuki.ru не открывается. Плюс он на поддомене — это не ваш адрес, его нельзя нормально продвигать»"),
 ("hotelfeniks.tb.ru", "САЙТ СЛОМАН",
  "Сайт отдаёт 404. Отель 4,7, 283 отзыва.",
  "«Ваш сайт отдаёт ошибку 404 — страницы нет. Проверьте сами: hotelfeniks.tb.ru»"),
 ("dizak.turbo.site", "САЙТ НЕ ОТВЕЧАЕТ",
  "Сайт на бесплатном конструкторе turbo.site не открывается. Гостиница 4,8 с 215 отзывами.",
  "«Сайт на бесплатном конструкторе уже не открывается. Зато 4,8 и 215 отзывов — есть что показывать»"),
 ("turbaza-dzinaga.ru", "САЙТ НЕ ОПЛАЧЕН",
  "Вместо сайта — заглушка конструктора uKit: «Сайт не оплачен». Гостиница на 65 номеров в Дигории, 169 отзывов.",
  "«Ваш сайт пишет «не оплачен». Это буквально табличка «здесь ничего нет» для гостя»"),
 ("pribrezhnaja-primorskaja-ulitsa.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Сайта нет: вместо него микро-сайт, который Яндекс.Бизнес сгенерировал сам (адрес из названия улицы). 500 отзывов, 22 номера, 4,4.",
  "«У вас нет сайта — есть автостраница Яндекса с адресом в 60 символов. Её нельзя продвигать, нельзя поставить бронь»"),
 ("shaherezada-1655474079.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Автосайт Яндекса вместо своего. 38 номеров, 458 отзывов на Эльбрусе — отель в топе, а домена нет.",
  "«Ваш «сайт» — это страница, которую сгенерировал Яндекс: shaherezada-1655474079... Своих фото, цен и брони там нет»"),
 ("arbat-ulitsa-345-j-dagestanskoj-strelkovoj-divizii.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Автосайт Яндекса с адресом на 61 символ. 19 номеров, 415 отзывов, 4,7 в Дербенте.",
  "«Отель 4,7 без сайта: только автостраница Яндекса. Для Дербента, где идёт поток туристов, это потерянные деньги»"),
 ("u-zajnab.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Автосайт Яндекса. 4,9 при 272 отзывах и всего 10 номеров — очень сильный маленький объект.",
  "«4,9 из 5 — это редкость. Но сайта нет: только автостраница. С таким рейтингом вы продаёте себя дешевле, чем могли бы»"),
 ("otel-mineral.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Автосайт Яндекса, 273 отзыва, 14 номеров, Минеральные Воды (транзитный поток).",
  "«У вас автостраница Яндекса. При потоке Минвод сайт с бронью окупается за месяц»"),
 ("shale-zheleznovodskaja-ulitsa.clients.site", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА",
  "Автосайт Яндекса, 11 номеров, 189 отзывов, 4,6.",
  "«Сайт-автостраница от Яндекса — это не ваш актив: завтра Яндекс поменяет шаблон, а вы ничего не сохраните»"),
 ("hotelprospekt.ru", "САЙТ ЕСТЬ, НО ПУСТОЙ",
  "Одна страница на Tilda: 205 символов текста, 1 картинка, в title просто «Prospekt». Бронь через ReservationSteps есть и работает — но самого сайта нет: ни номеров, ни цен, ни фото, ни одной внутренней страницы, нет аналитики.",
  "«У вас 639 отзывов и 4,8 — а сайт на 200 символов. Бронь подключена, а рассказать о номерах негде: гость уходит в Островок»"),
 ("xn--26-glchbriop2b.xn--p1ai", "САЙТ ЕСТЬ, НО ПУСТОЙ",
  "Сайт-визитка без цен, номеров и брони; аналитики нет — сколько людей заходит, неизвестно. 33 номера, 411 отзывов.",
  "«Сайт есть, но он ничего не продаёт: ни цен, ни формы заявки, ни счётчиков. Нельзя даже понять, сколько гостей приходит»"),
 ("europa-hotel.ru", "САЙТ ЕСТЬ, НО СЛАБЫЙ",
  "Страница отвечает 10,7 секунды — половина гостей с телефона уйдёт раньше. 297 отзывов, 4,6, Дербент.",
  "«Ваш сайт грузится 11 секунд. Google и Яндекс это видят, гость тоже — он уходит до загрузки»"),
 ("spisladko-26.ru", "САЙТ ЕСТЬ, НО СЛАБЫЙ",
  "Старая вёрстка: нет адаптации под телефон, нет модуля брони, нет аналитики. 28 номеров, 184 отзыва.",
  "«С телефона ваш сайт выглядит как в 2010-м: нужно пальцем зумить. Половина гостей до брони не доходит»"),
 ("red-stones.ru", "САЙТ ЕСТЬ, НО СЛАБЫЙ",
  "Копирайт 2021, нет онлайн-брони. 274 отзыва, 4,6 (Теберда).",
  "«Сайт не обновлялся с 2021-го, бронирование только по телефону. Для горного курорта это потеря прямых продаж»"),
 ("rodnik-cmw.ru", "САЙТ ЕСТЬ, НО МЕДЛЕННЫЙ",
  "Отклик 13,6 секунды на большом санатории (155 номеров, 658 отзывов). Бронь есть — проблема только в скорости и весе страницы.",
  "«Сайт у вас есть и бронь работает — но грузится 13 секунд. Это лечится: скорость плюс мобильная версия»"),
]

HOSTS_SKIP = ["istochnik-essentuki.ru"]

CLEAN = [("Федеральное государственное бюджетное учреждение ", ""), ("ФГБУ ", ""),
         ("Общество с ограниченной ответственностью ", "ООО «"), ("Гостиничный комплекс Эдельвейс", "ГК «Эдельвейс»"),
         ("Гостинично-ресторанный комплекс Сенгилеевский", "ГРК «Сенгилеевский»")]


OVR = {"edelveis09.ru": "ГК «Эдельвейс», Черкесск",
       "xn--26-glchbriop2b.xn--p1ai": "ГРК «Сенгилей», Ставрополь",
       "red-stones.ru": "База отдыха «Красные камни», Теберда",
       "shaherezada-1655474079.clients.site": "Гостиница «Шахерезада», Приэльбрусье",
       "shale-zheleznovodskaja-ulitsa.clients.site": "ГРК «Шале», Минеральные Воды",
       "art.hotel.essentuki.ru": "ART HOTEL, Ессентуки",
       "nok-juravli.ru": "НОК «Журавли», Махачкала",
       "hotelprospekt.ru": "Отель «Проспект», Кисловодск",
       "hotelfeniks.tb.ru": "Отель «Феникс», Дербент",
       "u-zajnab.clients.site": "Гостиница «У Зайнаб», Дагестан",
       "pribrezhnaja-primorskaja-ulitsa.clients.site": "Гостиница «Прибрежная», Дагестан"}


def clean(n, host="", city=""):
    if host in OVR:
        return OVR[host]
    if n.isupper() or n.upper() == n:
        n = n.title()
    if city and city != "?" and city.split()[0].lower() not in n.lower():
        n = f"{n}, {city}"
    for a, b in CLEAN:
        n = n.replace(a, b)
    n = n.replace("»»", "»").strip()
    if len(n) > 46:
        n = n[:44].rstrip(" ,.") + "…"
    return n


rows = []
for i, (host, cat, what, pitch) in enumerate(LEADS, 1):
    o = data.get(host)
    if not o:
        print("!! нет данных:", host)
        continue
    rows.append(dict(rank=i, cat=cat, name=clean(o["name"], host, o["city"]), city=o["city"], type=o.get("type") or "",
                     rooms=o["rooms"], rating=o["rating"], reviews=o["reviews"], site=o["site"],
                     host=host, owner=o.get("owner") or "", inn=o.get("inn") or "", ogrn=o.get("ogrn") or "",
                     phone=o.get("phone") or "", what=what, pitch=pitch,
                     flags="; ".join(o["flags"]), url=o["url"]))

print("лидов:", len(rows))
json.dump(rows, open("nc_leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- Excel
XL = r"C:\Users\Ali PC\Desktop\СКФО_отели_с_плохим_сайтом_2026-11-24.xlsx"
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Лиды"
head = ["№", "Категория", "Объект", "Город", "Тип", "Номеров", "Рейтинг", "Отзывов",
        "Сайт (что стоит в реестре)", "Что не так", "Владелец / ЛПР", "ИНН", "ОГРН/ОГРНИП",
        "Телефон", "Первый заход", "Статус", "Дата контакта", "Комментарий"]
ws.append(head)
for r in rows:
    ws.append([r["rank"], r["cat"], r["name"], r["city"], r["type"], r["rooms"], r["rating"], r["reviews"],
               r["site"], r["what"], r["owner"], r["inn"], r["ogrn"], r["phone"], r["pitch"], "Не contacted", "", ""])
for c in ws[1]:
    c.fill = PatternFill("solid", fgColor="1F3864"); c.font = Font(bold=True, color="FFFFFF")
    c.alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[1].height = 40
for i, w in enumerate([5, 24, 30, 15, 14, 9, 9, 9, 40, 60, 28, 14, 17, 20, 60, 14, 12, 24], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
thin = Side(style="thin", color="BFBFBF")
FILLS = {"ДОМЕН УВЕДЁН": "F8D7DA", "САЙТ МЁРТВ": "FCE4D6", "САЙТ НЕ ОТВЕЧАЕТ": "FCE4D6",
         "САЙТ СЛОМАН": "FCE4D6", "САЙТ НЕ ОПЛАЧЕН": "FCE4D6", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА": "FFF2CC",
         "САЙТ ЕСТЬ, НО ПУСТОЙ": "E2EFDA", "САЙТ ЕСТЬ, НО СЛАБЫЙ": "E2EFDA", "САЙТ ЕСТЬ, НО МЕДЛЕННЫЙ": "E2EFDA"}
for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
    fill = PatternFill("solid", fgColor=FILLS.get(str(row[1].value), "FFFFFF"))
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        c.fill = fill
ws.freeze_panes = "C2"
ws.auto_filter.ref = ws.dimensions

ws2 = wb.create_sheet("Как проверял")
for line in [
    ["Методика", ""],
    ["Источник объектов", "Каталоги HotGrade (отели и гостевые дома СКФО): 887 объектов по 31 городу/региону — Ставрополье, КМВ, КЧР (Архыз, Домбай, Теберда), КБР (Приэльбрусье, Нальчик), Северная Осетия, Дагестан, Адыгея, Чечня, Ингушетия"],
    ["Данные по объекту", "HotGrade из реестра ФСА: ИНН/ОГРН, владелец (ИП/юрлицо), номерной фонд, категория, отзывы Яндекса, адрес, телефон"],
    ["Проверка сайта", "217 уникальных доменов: HTTP-статус, HTTPS, редирект, время отклика, наличие viewport (мобильная адаптация), копирайт, признак онлайн-брони, аналитика, содержимое страницы"],
    ["Проверка доменов", "DNS-запрос через 8.8.8.8 + повторные попытки по http и https с таймаутом 35 с"],
    ["Отбор", "Сильный объект = 150+ отзывов, рейтинг 4,3+, 10+ номеров. Плохой сайт = мёртвый домен, уведённый домен, автосайт Яндекса, отсутствие брони/адаптива/обновлений"],
    ["Что исключил", "Сетевые и крупные санатории, у которых сайт работает (Источник — istochnikspa.ru, Родник, Русь, Плаза, AZIMUT и т.д.)"],
    ["Проверено вручную", "7Peaks, АРИЯ, Бугарь, АльтаРио — у них сайты есть, в лиды не попали, хотя в реестре ФСА ссылки нет"],
    ["Ограничение", "55 доменов отвечали нестабильно из-за сети: все такие случаи перепроверены повторно, в лиды попали только подтверждённые"],
]:
    ws2.append(line)
ws2.column_dimensions["A"].width = 26
ws2.column_dimensions["B"].width = 130
for row in ws2.iter_rows(min_row=1, max_row=ws2.max_row):
    row[0].font = Font(bold=True)
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
wb.save(XL)
print("saved:", XL)

# ---------------------------------------------------------------- HTML
CATCOL = {"ДОМЕН УВЕДЁН": "#b3151f", "САЙТ МЁРТВ": "#b3151f", "САЙТ НЕ ОТВЕЧАЕТ": "#b3151f",
          "САЙТ СЛОМАН": "#b3151f", "САЙТ НЕ ОПЛАЧЕН": "#b3151f", "ТОЛЬКО АВТОСАЙТ ЯНДЕКСА": "#a86400",
          "САЙТ ЕСТЬ, НО ПУСТОЙ": "#1d6b45", "САЙТ ЕСТЬ, НО СЛАБЫЙ": "#1d6b45", "САЙТ ЕСТЬ, НО МЕДЛЕННЫЙ": "#1d6b45"}
cards = []
for r in rows:
    col = CATCOL.get(r["cat"], "#333")
    cards.append(f"""
<tr class="row" style="--c:{col}">
 <td class="n">{r['rank']}</td>
 <td>
   <div class="nm">{html.escape(r['name'])}</div>
   <div class="meta">{html.escape(r['city'])} · {r['rooms']} ном. · {r['rating']:.2f} ★ · {r['reviews']} отзывов</div>
   <div class="cat">{html.escape(r['cat'])}</div>
 </td>
 <td class="what">{html.escape(r['what'])}</td>
 <td class="facts">
   <div><span>Сайт в реестре</span><b>{html.escape(r['host'])}</b></div>
   <div><span>Владелец</span><b>{html.escape(r['owner']) or '—'}</b></div>
   <div><span>ИНН</span><b>{html.escape(r['inn']) or '—'}</b></div>
   <div><span>Телефон</span><b>{html.escape(r['phone']) or '—'}</b></div>
 </td>
 <td class="pitch">{html.escape(r['pitch'])}</td>
</tr>""")

HTML = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>СКФО: сильные отели с плохим сайтом</title>
<style>
:root{{--line:#e3e5e9;--mut:#6b7280;--ink:#15171b;--accent:#1f3864}}
*{{box-sizing:border-box}}
body{{margin:0;padding:26px 20px 60px;background:#f6f7f9;color:var(--ink);font:15px/1.55 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
.wrap{{max-width:1280px;margin:0 auto}}
h1{{font-size:29px;line-height:1.2;margin:0 0 8px}}
.lead{{color:var(--mut);max-width:90ch;margin:0 0 18px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 22px}}
.stat{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}}
.stat b{{display:block;font-size:26px;line-height:1.1}}
.stat span{{color:var(--mut);font-size:12.5px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden}}
thead th{{background:var(--accent);color:#fff;font-size:12px;text-transform:uppercase;letter-spacing:.04em;text-align:left;padding:10px}}
td{{padding:12px 10px;border-top:1px solid var(--line);vertical-align:top;font-size:14px}}
tr.row{{border-left:5px solid var(--c)}}
td.n{{font-weight:700;color:var(--mut);width:34px}}
.nm{{font-weight:700;font-size:15.5px}}
.meta{{color:var(--mut);font-size:12.5px;margin-top:2px}}
.cat{{display:inline-block;margin-top:7px;padding:2px 9px;border-radius:999px;background:color-mix(in srgb,var(--c) 14%,#fff);color:var(--c);font-size:11.5px;font-weight:700;letter-spacing:.02em}}
td.what{{max-width:330px}}
td.facts{{min-width:230px;font-size:13px}}
td.facts span{{display:block;color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.03em}}
td.facts b{{font-weight:600;word-break:break-word}}
td.facts>div{{margin-bottom:6px}}
td.pitch{{max-width:330px;font-style:italic;color:#333}}
.note{{background:#fff8e6;border:1px solid #f0dda6;border-radius:14px;padding:14px 18px;margin:0 0 22px}}
.note h3{{margin:0 0 8px;font-size:15px}}
.note ul{{margin:0;padding-left:20px;font-size:14px}} .note li{{margin:4px 0}}
footer{{color:var(--mut);font-size:12.5px;text-align:center;margin-top:24px}}
@media(max-width:900px){{.stats{{grid-template-columns:repeat(2,1fr)}}table,thead,tbody,tr,td{{display:block}}thead{{display:none}}tr.row{{border:1px solid var(--line);border-left:5px solid var(--c);border-radius:12px;margin-bottom:12px;background:#fff}}td{{border:none;padding:8px 12px}}}}
</style></head><body><div class="wrap">
<h1>Сильные отели Северного Кавказа с плохим сайтом</h1>
<p class="lead">Прогнал 887 объектов размещения по СКФО (Ставрополье и КМВ, КЧР, КБР, Северная Осетия, Дагестан, Адыгея, Чечня, Ингушетия),
проверил 217 сайтов и доменов из реестра ФСА. Ниже — те, у кого всё хорошо с гостями и плохо с сайтом. Отсортировано по силе аргумента для звонка.</p>

<div class="stats">
 <div class="stat"><b>887</b><span>объектов проверено</span></div>
 <div class="stat"><b>217</b><span>доменов протестировано</span></div>
 <div class="stat"><b>4</b><span>домена отдают казино</span></div>
 <div class="stat"><b>9</b><span>доменов мертвы или сломаны</span></div>
</div>

<div class="note">
<h3>Что даёт этот список</h3>
<ul>
<li><b>Самые сильные заходы — первые четыре:</b> у отелей домены захвачены азартными сайтами. Это не «нужен сайт», это репутационная проблема, которую видно сразу.</li>
<li><b>Дальше — мёртвые домены:</b> DNS не отвечает, сайта нет вообще. При этом от 300 до 600 отзывов и рейтинг 4,4–4,7.</li>
<li><b>Автосайты Яндекса</b> — не сайт: генерируемая страница с адресом из названия улицы, без своих цен и брони.</li>
<li>Все ИНН, владельцы и телефоны — из реестра ФСА и ЕГРЮЛ/ЕГРИП, их можно проверить перед звонком.</li>
</ul>
</div>

<table>
<thead><tr><th>№</th><th>Объект</th><th>Диагноз по сайту</th><th>Контакты и владелец</th><th>Первый заход</th></tr></thead>
<tbody>
{''.join(cards)}
</tbody></table>

<footer>Проверено 24.11.2026 · объекты и владельцы — реестр ФСА (tourism.fsa.gov.ru) через HotGrade, ЕГРЮЛ/ЕГРИП · сайты — прямые HTTP/DNS-проверки (статус, время отклика, адаптивность, бронь, содержимое)</footer>
</div></body></html>"""

HP = r"C:\Users\Ali PC\Desktop\СКФО_отели_с_плохим_сайтом_2026-11-24.html"
open(HP, "w", encoding="utf-8").write(HTML)
print("saved:", HP, round(os.path.getsize(HP) / 1024), "KB")
