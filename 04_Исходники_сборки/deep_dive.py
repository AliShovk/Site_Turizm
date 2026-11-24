# -*- coding: utf-8 -*-
import json, re, subprocess, os
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
rows = {o["host"]: o for o in json.load(open("nc_final.json", encoding="utf-8")) if o.get("host")}
TARGETS = ["nok-juravli.ru", "edelveis09.ru", "shahristan.ru", "u-zajnab.clients.site",
           "arbat-ulitsa-345-j-dagestanskoj-strelkovoj-divizii.clients.site"]
os.makedirs("deep", exist_ok=True)


def fetch(url, out):
    r = subprocess.run(["curl", "-sSL", "--compressed", "-4", "--max-time", "35", "-A", UA,
                        "-H", "Accept-Language: ru-RU,ru;q=0.9", "-o", out, "-w", "%{http_code}", url], capture_output=True)
    return r.stdout.decode("utf-8", "replace").strip()


def text_of(path):
    h = open(path, encoding="utf-8", errors="ignore").read()
    s = BeautifulSoup(h, "lxml")
    return re.sub(r"\s+", " ", s.get_text(" ", strip=True))


out = {}
for host in TARGETS:
    o = rows[host]
    inn = o["inn"]
    rec = dict(host=host, name=o["name"], inn=inn, ogrn=o.get("ogrn"), owner=o.get("owner"),
               phone=o.get("phone"), rooms=o["rooms"], rating=o["rating"], reviews=o["reviews"],
               city=o["city"], site=o["site"], hotgrade=o["url"])

    # --- sbis (ЕГРЮЛ/ЕГРИП выжимка)
    p = f"deep/sbis_{inn}.html"
    code = fetch(f"https://sbis.ru/contragents/{inn}", p)
    t = text_of(p) if code == "200" else ""
    rec["sbis_title"] = (BeautifulSoup(open(p, encoding="utf-8", errors="ignore").read(), "lxml").title.get_text(strip=True)
                         if os.path.exists(p) else "")[:160]
    m = re.search(r"ОКВЭД[:\s]*([\d\.]+)\s*[-—]\s*([^.]{5,90})", t)
    rec["okved"] = f"{m.group(1)} — {m.group(2).strip()[:80]}" if m else ""
    m = re.search(r"(Действующ\w+|Ликвидир\w+|Прекратил\w+|Недействующ\w+)", t)
    rec["status"] = m.group(1) if m else ""
    m = re.search(r"(?:Руководитель|Директор|Глава)[:\s]*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})", t)
    rec["director"] = m.group(1) if m else ""
    m = re.search(r"(\d{6},?\s*[^|]{10,120})", t)
    rec["reg_addr"] = m.group(1)[:120] if m else ""
    rec["employees"] = (re.search(r"Среднесписочная[^.]{0,80}", t).group(0) if re.search(r"Среднесписочная[^.]{0,80}", t) else "")
    rec["income"] = (re.search(r"(?:Выручка|Доходы)[^А-Яа-я]{0,40}[\d\s]{5,20}", t).group(0) if re.search(r"(?:Выручка|Доходы)[^А-Яа-я]{0,40}[\d\s]{5,20}", t) else "")

    # --- hotgrade подробнее
    p = f"deep/hg_{host}.html"
    code = fetch(o["url"], p)
    h = open(p, encoding="utf-8", errors="ignore").read() if code == "200" else ""
    m = re.search(r'tourism\.fsa\.gov\.ru/ru/resorts/hotels/([a-f0-9\-]+)', h)
    rec["fsa_uuid"] = m.group(1) if m else ""
    m = re.search(r"Индекс гостевого доверия: (\d+) из 100", h)
    rec["trust"] = int(m.group(1)) if m else None
    m = re.search(r'<b class="tnum">(\d+)<small>/ 20</small></b><span>каналов бронирования', h)
    rec["channels"] = int(m.group(1)) if m else None
    m = re.search(r"<dt>Тип и категория</dt><dd>([^<]+)</dd>", h)
    rec["type"] = m.group(1) if m else ""
    m = re.search(r"<dt>Адрес</dt><dd>([^<]+)</dd>", h)
    rec["addr"] = m.group(1) if m else ""
    m = re.search(r'<b class="tnum">([\d,\.]+)<small>/ 5</small></b><span>оценка гостей · ([\d\s]+) отзыв', h)
    if m:
        rec["rating"] = float(m.group(1).replace(",", "."))
        rec["reviews"] = int(re.sub(r"\D", "", m.group(2)))

    # --- что сейчас на домене
    p = f"deep/site_{host}.html"
    code = fetch("https://" + host + "/", p)
    rec["site_code"] = code
    if os.path.exists(p) and os.path.getsize(p) > 200:
        t = text_of(p)
        rec["site_title"] = (re.search(r"", "") and "") or (BeautifulSoup(open(p, encoding="utf-8", errors="ignore").read(), "lxml").title.get_text(strip=True) if True else "")
        rec["site_text"] = t[:700]
    out[host] = rec
    print(f"== {o['name']}")
    for k in ("status", "okved", "director", "fsa_uuid", "trust", "channels", "type", "addr", "site_code", "site_title"):
        print(f"   {k}: {rec.get(k)}")

json.dump(out, open("deep/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
