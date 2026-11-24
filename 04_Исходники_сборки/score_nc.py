import json, re
from urllib.parse import urlparse

rows = [json.loads(l) for l in open("nc_hotels.jsonl", encoding="utf-8")]
sites = {s["host"]: s for s in (json.loads(l) for l in open("nc_sites.jsonl", encoding="utf-8"))}

CITY = {"kislovodsk": "Кисловодск", "pyatigorsk": "Пятигорск", "essentuki": "Ессентуки",
        "zheleznovodsk": "Железноводск", "mineralnye-vody": "Минеральные Воды", "nalchik": "Нальчик",
        "vladikavkaz": "Владикавказ", "makhachkala": "Махачкала", "derbent": "Дербент",
        "izberbash": "Избербаш", "kaspiysk": "Каспийск", "groznyy": "Грозный", "maykop": "Майкоп",
        "cherkessk": "Черкесск", "nevinnomyssk": "Невинномысск", "stavropol": "Ставрополь",
        "karachaevsk": "Карачаевск", "teberda": "Теберда", "magas": "Магас", "budennovsk": "Будённовск",
        "georgievsk": "Георгиевск", "beslan": "Беслан", "prokhladnyy": "Прохладный"}
REGION = {"karachaevo-cherkesskaya-respublika": "КЧР", "kabardino-balkarskaya-respublika": "КБР",
          "respublika-severnaya-osetiya-alaniya": "Северная Осетия", "respublika-dagestan": "Дагестан",
          "respublika-adygeya": "Адыгея", "chechenskaya-respublika": "Чечня",
          "respublika-ingushetiya": "Ингушетия", "stavropolskiy-kray": "Ставрополье"}
BAD = re.compile(r"покер|casino|казино|кредит|займ|ставки|1xbet|букмекер", re.I)


def rt(r):
    try:
        return float(str(r.get("rating")).replace(",", "."))
    except Exception:
        return 0.0


def addr_city(a):
    a = a or ""
    for pat in [r"г\.?\s*([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)", r"город\s+([А-ЯЁ][а-яё]+)",
                r"с\.\s*([А-ЯЁ][а-яё]+)", r"(?:п\.|пос\.|поселок)\s*([А-ЯЁ][а-яё]+)"]:
        m = re.search(pat, a)
        if m:
            return m.group(1)
    return ""


out = []
for r in rows:
    host = urlparse(r["site"]).netloc.lower().replace("www.", "") if r.get("site") else None
    a = sites.get(host) if host else None
    slug = r["url"].split("/hotel/")[-1].split("/")[0]
    city = CITY.get(slug) or addr_city(r.get("addr")) or REGION.get(slug, "?")
    flags, score = [], 0
    if not r.get("site"):
        flags.append("НЕТ САЙТА"); score += 3
    elif a:
        if a["code"] != "200":
            flags.append(f"сайт не открывается ({a['code'] or 'таймаут'})"); score += 4
        if a["yandex_builder"]:
            flags.append("сайт-заглушка от Яндекс.Бизнеса (clients.site)"); score += 3
        if not a["viewport"]:
            flags.append("не адаптивен под телефон"); score += 2
        if a["copyright"] and a["copyright"] < 2024:
            flags.append(f"не обновлялся (©{a['copyright']})"); score += 2
        if a["ms"] > 3000:
            flags.append(f"медленный: {a['ms']/1000:.1f} c отклик"); score += 2
        if not a["booking"]:
            flags.append("нет онлайн-бронирования"); score += 2
        if not a["https"]:
            flags.append("без HTTPS"); score += 2
        if a["text_len"] < 800:
            flags.append("пустая/неинформативная страница"); score += 2
        if BAD.search((a["title"] or "") + " " + (a["html_head"] or "")):
            flags.append("домен уведён, сайт не про отель"); score += 5
        if not a["metrika"] and not a["analytics"]:
            flags.append("нет аналитики"); score += 1
    out.append(dict(url=r["url"], name=r["name"], city=city, slug=slug, type=r.get("type"),
                    inn=r.get("inn"), ogrn=r.get("ogrn"), owner=r.get("owner"), phone=r.get("phone"),
                    rooms=r.get("rooms") or 0, rating=rt(r), reviews=r.get("reviews") or 0,
                    site=r.get("site"), host=host, audit=a, flags=flags, weak=score,
                    in_registry=r.get("in_registry"),
                    potential=round((r.get("reviews") or 0) * rt(r) * (1 + score / 4) / 100, 1)))
out.sort(key=lambda x: -x["potential"])
json.dump(out, open("nc_scored.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

t1 = [o for o in out if o["reviews"] >= 150 and o["rating"] >= 4.2 and o["rooms"] >= 10 and not o["site"]]
t2 = [o for o in out if o["reviews"] >= 150 and o["rating"] >= 4.2 and o["rooms"] >= 10 and o["site"] and o["weak"] >= 4]
print("всего:", len(out), "| сильных без сайта:", len(t1), "| сайт есть но слабый:", len(t2))
print("\n=== TIER 1: нет сайта ===")
for o in sorted(t1, key=lambda x: -x["potential"])[:26]:
    print(f"{o['reviews']:5}|{o['rating']:.2f}|{o['rooms']:>4}|{o['city'][:14]:<14}| {o['name'][:38]:<38}| {str(o['type'])[:12]:<12}| ИНН {o['inn']}")
print("\n=== TIER 2: сайт есть, но слабый ===")
for o in sorted(t2, key=lambda x: -x["potential"])[:26]:
    print(f"{o['reviews']:5}|{o['rating']:.2f}|{o['rooms']:>4}|{o['city'][:12]:<12}| {o['name'][:30]:<30}| {o['host'][:30]:<30}| {'; '.join(o['flags'])[:66]}")
