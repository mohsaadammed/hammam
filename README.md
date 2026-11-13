# salla-watch

بوت يراقب منتج **جوز حمام محشي** من متجر "أصل الحمام" على سلة، ويرسل لك رسالة تيليجرام أول ما يتوفر.

## كيف يشتغل
- GitHub Actions يشغّل `check.py` كل 5 دقايق (`.github/workflows/watch.yml`).
- السكربت يقرأ 3 إشارات من صفحة المنتج: نص زر السلة (`salla-add-product-button`)، و meta `product:availability`، و schema.org availability. إذا أي وحدة قالت متوفر (مثلاً الزر ما عاد مكتوب فيه "نفدت الكمية") يرسل التنبيه.
- ما يرسل شي وهو غير متوفر. أول ما يتوفر يرسل التنبيه 3 مرات (بين كل وحدة 10 ثواني) مع الرابط.
- إذا صار متوفر: يرسل رسالة تيليجرام، والـ workflow يوقف نفسه (`gh workflow disable`) عشان ما يكرر الرسالة.
- إذا المتجر أخفى المنتج (سلة تحوّل الرابط لصفحة المتجر)، يعتبره غير متوفر بدون خطأ، ويرجع يفحص عادي لما يرجع المنتج.
- إذا ما لقى ولا إشارة (أو سلة حظرت الطلب)، الـ run يفشل ويجيك إيميل من GitHub.

## الإعداد
1. افتح @BotFather في تيليجرام ← `/newbot` ← اختر اسم ويوزر ينتهي بـ `bot` ← انسخ التوكن.
2. أرسل أي رسالة للبوت حقك، بعدين افتح `https://api.telegram.org/bot<TOKEN>/getUpdates` وخذ الرقم اللي في `"chat":{"id": ...}`.
3. في الـ repo: Settings ← Secrets and variables ← Actions ← New repository secret:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID` (لأكثر من شخص افصل بين الأرقام بفاصلة، مثل `111,222`)
4. Actions ← Salla stock watch ← Run workflow عشان تجربه يدوي.

## إعادة التشغيل بعد ما يتوقف
Actions ← Salla stock watch ← Enable workflow.
