import json, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
rows = [json.loads(l) for l in open("nc_hotels.jsonl", encoding="utf-8")]
sites = {}
for r in rows:
    s = r.get("site")
    if not s:
        continue
    host = urlparse(s).netloc.lower().replace("www.", "")
    sites.setdefault(host, []).append(r)

print("уникальных доменов:", len(sites))

BOOK = r"(travelline|bnovo|ostrovok|bookonline|shelter|frontdesk|hotelbook|bookform|rezerv|realtycalendar|tvize|tvizi|edvi|brobrol|bpro|book\.|booking\.|ibooking|smartbook|hoteladvisor)"
ENGINE_OLD = r"(jquery[-/]?1\.|jquery[-/]?2\.|mootools|prototype\.js|table width)"
META = r'<meta[^>]+name=["\']viewport["\'][^>]*>'


def audit(host):
    url = f"https://{host}/"
    t0 = time.time()
    r = subprocess.run(["curl", "-sSL", "--compressed", "--max-time", "25", "-A", UA,
                        "-H", "Accept-Language: ru-RU,ru;q=0.9",
                        "-o", "-", "-w", "\n___META___%{http_code}|%{url_effective}|%{size_download}",
                        url], capture_output=True)
    raw = r.stdout
    idx = raw.rfind(b"\n___META___")
    body, meta = (raw[:idx], raw[idx + 11:].decode("utf-8", "replace")) if idx > 0 else (raw, "")
    dt = time.time() - t0
    code, final, size = (meta.split("|") + ["", "", ""])[:3] if meta else ("", "", "")
    html = body.decode("utf-8", "replace")
    low = html.lower()
    res = dict(host=host, code=code, final=final, size=int(size or 0), ms=int(dt * 1000),
               https=final.startswith("https"), title="", viewport=bool(re.search(META, low)),
               desc=False, booking=bool(re.search(BOOK, low)), old=bool(re.search(ENGINE_OLD, low)),
               metrika=("mc.yandex.ru" in low or "metrika" in low), analytics=("googletagmanager" in low or "google-analytics" in low),
               yandex_builder=False, copyright=None, text_len=0, imgs=0)
    res["yandex_builder"] = host.endswith("clients.site") or "yandex" in low and "site-constructor" in low
    m = re.search(r"<title[^>]*>([^<]{2,200})</title>", html, re.I)
    if m:
        res["title"] = re.sub(r"\s+", " ", m.group(1)).strip()
    res["desc"] = bool(re.search(r'<meta[^>]+name=["\']description["\']', low))
    txt = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    res["text_len"] = len(txt)
    years = [int(y) for y in re.findall(r"(?<!\d)(20[0-2]\d)(?!\d)", txt) if 2015 <= int(y) <= 2026]
    res["copyright"] = max(years) if years else None
    res["imgs"] = len(re.findall(r"<img ", low))
    res["html_head"] = re.sub(r"\s+", " ", txt[:220])
    return res


with ThreadPoolExecutor(max_workers=12) as ex, open("nc_sites.jsonl", "w", encoding="utf-8") as f:
    for i, d in enumerate(ex.map(audit, list(sites)), 1):
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
        if i % 40 == 0:
            print("...", i)
print("готово аудитов:", len(sites))
