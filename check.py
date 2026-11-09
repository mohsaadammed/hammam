import os
import re
import sys

import requests

URL = "https://salla.sa/asl-al7mam/%D8%AC%D9%88%D8%B2-%D8%AD%D9%85%D8%A7%D9%85-%D9%85%D8%AD%D8%B4%D9%8A/p706307288"
SOLD_OUT_TEXT = "نفدت الكمية"
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
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    r.raise_for_status()


def main():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        sys.exit(f"خطأ: سلة رجّعت HTTP {resp.status_code} (ممكن حظر أو Cloudflare)")
    html = resp.text

    match = META_RE.search(html)
    availability = (match.group(1) or match.group(2)).strip().lower() if match else None
    sold_out = SOLD_OUT_TEXT in html
    print(f"product:availability = {availability!r}, نص نفدت الكمية موجود = {sold_out}")

    if availability is None and not sold_out:
        sys.exit("خطأ: ما لقيت لا الـ meta ولا نص نفدت الكمية — الصفحة تغيرت أو انحظر الطلب")

    if availability == "in stock" and not sold_out:
        send_telegram(f"🔔 جوز حمام محشي صار متوفر الحين!\n{URL}")
        print("متوفر! تم إرسال رسالة تيليجرام")
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write("available=true\n")
    else:
        send_telegram(f"❌ جوز حمام محشي لا يزال غير متوفر\n{URL}")
        print("لا يزال غير متوفر — تم إرسال تنبيه تيليجرام")


if __name__ == "__main__":
    main()
