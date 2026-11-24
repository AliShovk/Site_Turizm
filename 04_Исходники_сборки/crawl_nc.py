import re, os, json, sys, subprocess
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
links = json.load(open("nc_links.json", encoding="utf-8"))
start, end = int(sys.argv[1]), int(sys.argv[2])
batch = links[start:end]
OUT = "nc_hotels.jsonl"

P = {
    "name": r"<h1[^>]*>(.*?)</h1>",
    "rating": r'<b class="tnum">([\d,\.]+)<small>/ 5</small></b><span>оценка гостей · ([\d\s\xa0]+) отзыв',
    "rooms": r'Номерной фонд</dt><dd><b class="tnum">(\d+)</b>',
    "type": r'<dt>Тип и категория</dt><dd>([^<]+)</dd>',
    "addr": r'<dt>Адрес</dt><dd>([^<]+)</dd>',
    "inn": r'ИНН <b class="tnum">(\d{10,12})</b>',
    "ogrn": r'ОГРН\w* <b class="tnum">(\d{13,15})</b>',
    "owner": r'<dt>Связанн\w+ (?:ИП|юрлицо)</dt><dd><strong>([^<]+)</strong>',
    "phone": r'Позвонить</span><span class="tnum">([^<]+)</span>',
    "score": r"Индекс гостевого доверия: (\d+) из 100",
    "channels": r'<b class="tnum">(\d+)<small>/ 20</small></b><span>каналов бронирования',
    "fsa": r"tourism\.fsa\.gov\.ru/ru/resorts/hotels/([a-f0-9\-]+)",
}
CITY = r'<a href="/oteli/[^"]+">([^<]+)</a>'


def parse(html, url):
    d = {"url": url}
    for k, p in P.items():
        m = re.search(p, html)
        if not m:
            d[k] = None
            continue
        if k == "rating":
            d["rating"] = m.group(1).replace(",", ".")
            d["reviews"] = re.sub(r"\D", "", m.group(2))
        else:
            d[k] = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    m = re.search(r'<a href="([^"]+)" class="ep-contact-action"[^>]*>Сайт из записи ФСА', html)
    d["site"] = m.group(1) if m else None
    # "закрыто/нет в реестре" признаки
    d["in_registry"] = "В реестре классификации" in html
    cities = re.findall(CITY, html)
    city = cities[0] if cities else None
    if not city:
        a = d.get("addr") or ""
        mm = re.search(r"(?:г\.?|город)\s*([А-ЯЁ][а-яё\-]+(?:-[А-ЯЁ][а-яё]+)*)", a)
        pp = re.search(r"(?:п\.|пос\.|поселок|с\.|село|ст-ца|станица)\s*([А-ЯЁ][а-яё\-]+)", a)
        city = (mm.group(1) if mm else None) or (pp.group(1) if pp else None)
    d["city"] = city
    for k in ("reviews", "rooms", "score", "channels"):
        if d.get(k):
            d[k] = int(re.sub(r"\D", "", str(d[k])) or 0)
    return d


def work(u):
    r = subprocess.run(["curl", "-sSL", "--compressed", "--max-time", "30", "-A", UA, "-o", "-", u], capture_output=True)
    h = r.stdout.decode("utf-8", "replace")
    if "<h1" not in h:
        return {"url": u, "error": len(h)}
    return parse(h, u)


with ThreadPoolExecutor(max_workers=16) as ex, open(OUT, "a", encoding="utf-8") as f:
    n = 0
    for d in ex.map(work, batch):
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
        n += 1
print(f"готово {n} из {len(batch)} (диапазон {start}-{end})")
