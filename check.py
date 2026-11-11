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


def diagnose(html):
    print(f"--- تشخيص: حجم الصفحة {len(html)} حرف")
    for phrase in (SOLD_OUT_TEXT, "إضافة للسلة", "أضف للسلة", "اضف للسلة", "اضافة للسلة", "أضف إلى السلة"):
        for m in list(re.finditer(phrase, html))[:8]:
            ctx = html[max(0, m.start() - 150): m.end() + 80].replace("\n", " ")
            print(f"[{phrase} @{m.start()}] {ctx}")
    for pat in [r'<meta[^>]+product:[^>]+>', r'"(?:is_available|status|quantity|stock|in_stock|is_out_of_stock|out_of_stock)"\s*:\s*[^,}]{1,40}',
                r'availability"?\s*[:=]\s*"?[^",}]{1,60}', r'<button[^>]*(?:add|cart|sold|out)[^>]*>']:
        for m in list(re.finditer(pat, html, re.I))[:15]:
            print(f"[{pat[:20]}] {m.group(0)[:200]}")
    print("--- نهاية التشخيص")


def fetch():
    last_error = None
    for attempt in range(3):
        try:
            return requests.get(URL, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            last_error = e
            print(f"محاولة {attempt + 1} فشلت: {e}")
            time.sleep(10)
    sys.exit(f"خطأ: ما قدرت أوصل لسلة بعد 3 محاولات: {last_error}")


def main():
    resp = fetch()
    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        sys.exit(f"خطأ: سلة رجّعت HTTP {resp.status_code} (ممكن حظر أو Cloudflare)")
    html = resp.text

    match = META_RE.search(html)
    availability = (match.group(1) or match.group(2)).strip().lower() if match else None
    sold_out = SOLD_OUT_TEXT in html
    print(f"product:availability = {availability!r}, نص نفدت الكمية موجود = {sold_out}")
    diagnose(html)

    # نتأكد إنها صفحة المنتج فعلاً (مو صفحة خطأ أو حظر) قبل ما نعتبر اختفاء "نفدت الكمية" توفّر
    if PRODUCT_ID not in html:
        sys.exit("خطأ: الصفحة اللي رجعت ما هي صفحة المنتج (ممكن حظر أو صفحة خطأ)")

    # يعتبر متوفر إذا اختفت جملة "نفدت الكمية"، أو تغيّر الـ meta إلى in stock
    if not sold_out or availability == "in stock":
        for i in range(3):
            if i:
                time.sleep(10)
            send_telegram(f"🔔 جوز حمام محشي صار متوفر الحين! ({i + 1}/3)\n{URL}")
        print("متوفر! تم إرسال 3 رسائل تيليجرام")
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write("available=true\n")
    else:
        print("لا يزال غير متوفر")


if __name__ == "__main__":
    main()
