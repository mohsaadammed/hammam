# salla-watch

بوت يراقب منتج **جوز حمام محشي** من متجر "أصل الحمام" على سلة، ويرسل لك رسالة تيليجرام أول ما يتوفر.

## كيف يشتغل
- GitHub Actions يشغّل `check.py` كل 5 دقايق (`.github/workflows/watch.yml`).
- السكربت يقرأ meta tag اسمه `product:availability` ويدوّر على نص "نفدت الكمية".
- في كل فحص يرسل رسالة تيليجرام: "غير متوفر" مع الرابط، أو "صار متوفر" مع الرابط.
- إذا صار متوفر: يرسل رسالة تيليجرام، والـ workflow يوقف نفسه (`gh workflow disable`) عشان ما يكرر الرسالة.
- إذا ما لقى لا الـ meta ولا النص (أو سلة حظرت الطلب)، الـ run يفشل ويجيك إيميل من GitHub.

## الإعداد
1. افتح @BotFather في تيليجرام ← `/newbot` ← اختر اسم ويوزر ينتهي بـ `bot` ← انسخ التوكن.
2. أرسل أي رسالة للبوت حقك، بعدين افتح `https://api.telegram.org/bot<TOKEN>/getUpdates` وخذ الرقم اللي في `"chat":{"id": ...}`.
3. في الـ repo: Settings ← Secrets and variables ← Actions ← New repository secret:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Actions ← Salla stock watch ← Run workflow عشان تجربه يدوي.

## إعادة التشغيل بعد ما يتوقف
Actions ← Salla stock watch ← Enable workflow.
