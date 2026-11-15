import datetime
import os
import re
import sys
import time

import requests

URL = "https://salla.sa/asl-al7mam/%D8%AC%D9%88%D8%B2-%D8%AD%D9%85%D8%A7%D9%85-%D9%85%D8%AD%D8%B4%D9%8A/p706307288"
SOLD_OUT_TEXT = "نفدت الكمية"
PRODUCT_ID = "706307288"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.8",
}
META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']product:availability["\'][^>]*content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']product:availability["\']',
    re.IGNORECASE,
)


def send_telegram(text):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_ids = [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]
    failed = []
    for chat_id in chat_ids:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        if not r.ok:
            print(f"خطأ من تيليجرام للرقم {chat_ids.index(chat_id) + 1}: HTTP {r.status_code} — {r.text}")
            failed.append(chat_id)
    if len(failed) == len(chat_ids):
        sys.exit("فشل الإرسال لكل الأرقام")


BUTTON_RE = re.compile(r"<salla-add-product-button\b[^>]*>(.*?)</salla-add-product-button>", re.S | re.I)
SCHEMA_RE = re.compile(r'"availability"\s*:\s*"https?://schema\.org/(\w+)"', re.I)


def signals(html):
    """يقرأ ثلاث إشارات من الصفحة: الـ meta، و schema.org، ونص زر السلة.
    كل إشارة True إذا تغيّرت عن قيمة "نفدت الكمية" المعروفة (يعني ممكن متوفر)، False إذا لسا نفدت، None إذا ما انلقت.
    نعتمد على "تغيّرت عن نفدت" بدل "صارت متوفر بالضبط"، عشان أي قيمة جديدة ما نعرفها تعطي تنبيه بدل ما تفوت."""
    match = META_RE.search(html)
    meta = (match.group(1) or match.group(2)).strip().lower() if match else None
    schema = SCHEMA_RE.search(html)
    schema = schema.group(1) if schema else None
    button = BUTTON_RE.search(html)
    button = " ".join(re.sub(r"<[^>]+>", " ", button.group(1)).split()) if button else None
    print(f"meta={meta!r} | schema={schema!r} | زر السلة={button!r}")
    raw = {"meta": meta, "schema": schema, "button": button}
    flags = {
        "meta": None if meta is None else meta not in ("out of stock", "outofstock"),
        "schema": None if schema is None else schema.lower() != "outofstock",
        "button": None if button is None else SOLD_OUT_TEXT not in button,
    }
    return flags, raw


def dump(resp):
    html = resp.text
    print(f"--- تشخيص: الرابط النهائي {resp.url} | الحجم {len(html)} | تحويلات {[r.status_code for r in resp.history]}")
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    print("title:", t.group(1).strip()[:200] if t else None)
    for m in re.findall(r"<meta[^>]+>", html)[:40]:
        print("meta:", m[:200])
    print("salla tags:", sorted(set(re.findall(r"<(salla-[a-z-]+)", html)))[:40])
    for phrase in (PRODUCT_ID, SOLD_OUT_TEXT, "السلة", "availability", "InStock", "OutOfStock", "quantity"):
        for m in list(re.finditer(re.escape(phrase), html))[:4]:
            print(f"[{phrase}] " + html[max(0, m.start() - 150): m.end() + 150].replace("\n", " "))
    print("--- بداية الصفحة:", html[:1500].replace("\n", " "))


ERRORS_FILE = os.path.join("state", "errors")
MAX_ERRORS = 15  # كم فحص متتالي يفشل قبل ما يطلع خطأ ويجيك إيميل (تقريباً 15 دقيقة)


def read_errors():
    try:
        with open(ERRORS_FILE) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def write_errors(n):
    os.makedirs(os.path.dirname(ERRORS_FILE), exist_ok=True)
    with open(ERRORS_FILE, "w") as f:
        f.write(str(n))


class SoftError(Exception):
    """خطأ مؤقت (حظر عابر، انقطاع، صفحة غريبة). ما يطلع خطأ إلا إذا تكرر MAX_ERRORS مرة ورا بعض."""


def fetch():
    last = None
    for attempt in range(3):
        if attempt:
            time.sleep(10)
        try:
            resp = requests.get(URL, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            last = f"انقطاع: {e}"
        else:
            print(f"HTTP {resp.status_code}")
            if resp.status_code == 200:
                return resp
            last = f"سلة رجّعت HTTP {resp.status_code} (ممكن حظر أو Cloudflare)"
        print(f"محاولة {attempt + 1} فشلت: {last}")
    raise SoftError(last)


RIYADH = datetime.timezone(datetime.timedelta(hours=3))
WATCH_HOURS = {19, 20, 21, 22, 23, 0, 1}  # يراقب كل يوم من 7 المساء لين 2 الفجر بتوقيت السعودية
LAST_FILE = os.path.join("state", "available")


def read_state(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def write_state(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(value)


def main():
    now = datetime.datetime.now(RIYADH)
    if now.hour not in WATCH_HOURS:
        print(f"الساعة {now:%H:%M} بتوقيت السعودية — خارج وقت المراقبة (7 م – 2 ص)، ما نفحص")
        return
    try:
        check()
    except SoftError as e:
        n = read_errors() + 1
        write_errors(n)
        if n >= MAX_ERRORS:
            sys.exit(f"خطأ: {e} — صار له {n} فحص متتالي يفشل")
        print(f"تحذير: {e} — فشل مؤقت رقم {n} من {MAX_ERRORS}، نكمّل بدون خطأ")
        return
    write_errors(0)


def check():
    resp = fetch()
    html = resp.text

    # سلة تحوّل رابط المنتج لصفحة المتجر الرئيسية إذا المتجر أخفى المنتج أو حذفه.
    # هذي مو مشكلة في البوت: نعتبره غير متوفر ونكمّل بدون خطأ، ولما يرجع المنتج يرجع الفحص عادي.
    if resp.history and f"p{PRODUCT_ID}" not in resp.url:
        print(f"المنتج مخفي أو محذوف من المتجر حالياً (الرابط يحوّل إلى {resp.url}) — نعتبره غير متوفر")
        return "المنتج مخفي من المتجر حالياً"

    # نتأكد إنها صفحة المنتج فعلاً (مو صفحة خطأ أو حظر)
    if PRODUCT_ID not in html:
        raise SoftError("الصفحة اللي رجعت ما هي صفحة المنتج (ممكن حظر أو صفحة خطأ)")

    flags, raw = signals(html)
    found = {k: v for k, v in flags.items() if v is not None}
    if not found:
        dump(resp)
        raise SoftError("ما لقيت ولا إشارة للتوفر في الصفحة — شكل الصفحة تغيّر")

    # يعتبر متوفر إذا أي إشارة قالت متوفر (مثلاً زر السلة ما عاد مكتوب فيه "نفدت الكمية")
    available = any(found.values())
    was_available = read_state(LAST_FILE) == "1"
    write_state(LAST_FILE, "1" if available else "0")
    if available and not was_available:
        print(f"متوفر! الإشارات: {found}")
        for i in range(3):
            if i:
                time.sleep(10)
            send_telegram(f"🔔 جوز حمام محشي صار متوفر الحين! ({i + 1}/3)\n{URL}\n(زر السلة: {raw['button']})")
        print("متوفر! تم إرسال 3 رسائل تيليجرام")
        return "متوفر 🔔"
    if available:
        print("لا يزال متوفر — سبق وأرسلنا التنبيه، ما نكرره")
        return "متوفر"
    if was_available:
        print("نفد مرة ثانية — بننبهك لما يتوفر من جديد")
    print("لا يزال غير متوفر")
    return f"غير متوفر — زر السلة مكتوب عليه \"{raw['button']}\"" if raw["button"] else "غير متوفر"


if __name__ == "__main__":
    main()
