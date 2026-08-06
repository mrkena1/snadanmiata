# البوت (كاسكا + أفضل استماعات اليوم) — نسخة Render + Upstash Redis

## ⚠️ تنبيه أمني (مهم — اقرأه قبل أي push)
`config.py` الحين **ما فيه أي مفتاح/توكن حقيقي مكتوب بالكود** — كلها لازم
تنجي من Environment Variables، والبوت يرفض يشتغل لو ناقصة (تعمّدت هذا حتى
GitHub Secret Scanning ما يوقفك مرة ثانية).

بس التوكن والمفتاح اللي كانوا مكتوبين بالنسخة القديمة (اللي طلعلك تحذير
GitHub بسببها) **صاروا معروفين ولازم تسويلهم rotate**، حتى لو الـ push
انصد ولا كملّ:
1. [@BotFather](https://t.me/BotFather) → `/revoke` وخذ توكن جديد.
2. [console.groq.com](https://console.groq.com) → مفتاح جديد، امسح القديم.
3. حط القيم الجديدة كـ **Environment Variables** بلوحة Render (مو بالكود) — شرح تحت.

**لو الـ push انصد فعلاً (زي التحذير اللي شفته)**: يعني المفتاح القديم لسا
بس بالـ commit المحلي عندك، ما وصل GitHub. اضغط **Cancel** مو "Allow Secret"،
وبعد ما تحدّث `config.py` بالنسخة الجديدة (بدون مفاتيح مكتوبة)، سوّي commit
جديد واعمل push عادي. أما لو أي وقت *كمّل* الـ push بمفتاح حقيقي بداخله،
اعتبره مسرّب حتى لو حذفته بعدين — لازم rotate إجباري (git يحتفظ بالتاريخ).

## شنو تغيّر بهذا التحديث؟
- ❌ ما فيه Flask خالص — بدلها سيرفر HTTP صغير جداً من مكتبة بايثون المدمجة
  (`http.server`)، بس يرد "ok" — كافي لـ Render (لازم أي Web Service يربط
  على `$PORT`) ولـ UptimeRobot يضربه كل 5 دقايق يخليه صاحي.
- ✅ **كل التخزين صار على Upstash Redis** بدل ملفات JSON محلية، لأن Render
  Free ما يدعم Persistent Disk (أي ملف تسويه يروح أول ما السيرفر يعيد التشغيل):
  - اليوزرات المرخّص لهم (كلمة السر)
  - المشتركين بـ `/newsongs`
  - ذاكرة محادثة كاسكا
  - تاريخ آخر إرسال يومي (حتى ما يتكرر)
- ✅ **`/newsongs` أمر جديد**: المستخدم يكتبه ويوافق (زرار Yes/No)، وبعدها
  يوصله تلقائياً كل يوم الساعة **18:30 بتوقيت تونس** أفضل 10 أغاني عالمياً.
  الإرسال اليومي صار **اختياري (opt-in)** — بس المستخدمين اللي وافقوا يستلمونه،
  مو كل المرخّص لهم تلقائياً. يقدر يلغي الاشتراك بإرسال `/newsongs` مرة ثانية.
- ✅ `/topsongs` يعرض نفس الشارت فوراً بأي وقت (بدون اشتراك دائم).
- ✅ **`/chatarea` أمر جديد**: يخلي المستخدم يختار طريقة كلام كاسكا وياه —
  🪖 "الجندي" (النسخة القاسية/القائدة الأصلية) أو 🧒 "الطفلة" (نسخة أصغر
  وأدفأ وألطف). الاختيار يترزن لكل مستخدم على حدة بـ Redis، والبرومتات
  نفسها موجودة بملف `prompts.json` سهل تعدّلها بدون ما تلمس الكود.
- ✅ **`update.py`**: سكربت تشغّله محلياً على هاتفك بـ Termux بس (ما يترفع
  لـ GitHub — مضاف بـ `.gitignore`). يقرأ `update.txt` ويرسل محتواه كرسالة
  لكل مستخدمين البوت المسجّلين. مفيد لإرسال إعلانات/تحديثات يدوية.

## هيكل المشروع
```
merged_bot/
├── main.py                 # التشغيل: بوابة كلمة سر + شات + /topsongs + /newsongs
├── config.py                 # كل الإعدادات (تقرأ من Environment Variables)
├── redis_store.py              # طبقة موحدة فوق Upstash Redis
├── auth.py                       # كلمة السر + اشتراك /newsongs (Redis)
├── chat_engine.py                  # منطق كاسكا (Groq) + ذاكرة على Redis
├── persona.py                         # شخصيات كاسكا (/chatarea) — قراءة prompts.json + اختيار كل يوزر
├── prompts.json                         # نصوص البرومتات (the_soldier / the_kido)
├── charts.py                              # يجيب شارت Deezer العالمي
├── broadcast.py                        # يبني رسالة الشارت ويرسلها للمشتركين
├── update.py         # 🚫 محلي فقط (Termux) — لا يُرفع لـ GitHub
├── update.txt          # 🚫 محلي فقط — نص التحديث
├── migrate_old_users.py  # سكربت لمرة وحدة (شرح تحت)
├── render.yaml
└── requirements.txt
```

## 1) إعداد Upstash Redis (مجاني)
1. سوّي حساب بـ [upstash.com](https://upstash.com) → Create Database (اختر
   أقرب Region لسيرفر Render تبعك).
2. من صفحة الداتابيس، انسخ:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`

## 2) النشر على Render
- New → Web Service → اربط الـ repo (Render يقرأ `render.yaml` تلقائياً).
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Instance Type**: Free
- بتبويب **Environment** ضيف:

| Key | القيمة |
|---|---|
| `BOT_TOKEN` | توكن البوت الجديد |
| `GROQ_API_KEY` | مفتاح Groq الجديد |
| `ACCESS_PASSWORD` | كلمة السر اللي تبيها |
| `UPSTASH_REDIS_REST_URL` | من Upstash |
| `UPSTASH_REDIS_REST_TOKEN` | من Upstash |

(`PORT` يحطه Render تلقائياً.)

## 3) فعّل UptimeRobot (يبقي البوت صاحي)
بما إنك رح تستخدم UptimeRobot: سوّي **HTTP(s) Monitor** جديد على
`https://YOUR-APP.onrender.com/` كل **5 دقايق**. هذا يمنع Render Free من
تنويم السيرفر، يعني البوت يضل يستقبل رسائل ويرسل الشارت اليومي بالوقت
المضبوط بدون ما تحتاج أي كرون خارجي إضافي.

## 4) استرجاع اليوزرات القدامى (5 مستخدمين)
كان عندك 5 يوزرات مرخّص لهم بالملف القديم. بعد ما تضبط Upstash، شغّل مرة
وحدة (محلياً أو بـ Render Shell):
```bash
python migrate_old_users.py
```
بعدها احذف الملف أو خله بس تأكد إنه مو مرفوع لـ GitHub (مضاف بـ `.gitignore`).

## كيف يشتغل البوت الحين؟
1. **بوابة كلمة سر**: أي مستخدم جديد لازم يرسل `ACCESS_PASSWORD` قبل أي شي.
2. **الشات هو الافتراضي**: أي رسالة عادية بعد التحقق = رد من كاسكا (`/reset` يمسح الذاكرة).
3. **`/topsongs`**: يعرض أفضل 10 أغاني عالمياً الحين (مرة وحدة، بدون اشتراك).
4. **`/newsongs`**: يعرض له زرار موافقة. لو وافق → ينضاف لقائمة المشتركين
   ويستلم الشارت تلقائياً كل يوم 18:30 تونس. لو أرسل الأمر وهو مشترك أصلاً →
   يعرضله زرار "إلغاء الاشتراك".
5. **`/chatarea`**: يعرض زرارين (🪖 الجندي / 🧒 الطفلة)، يختار وحدة وتصير هي
   طريقة كلام كاسكا وياه من هسه، تقدر تغيّرها بأي وقت.

## استخدام update.py (على هاتفك، Termux فقط)
```bash
pkg install python -y
pip install -r requirements.txt
# عدّل update.txt وحط فيه النص اللي تبي ترسله
python update.py
# يعرضلك عدد المستلمين ومعاينة النص، اكتب y للتأكيد
```
هذا السكربت يستخدم نفس `config.py` و `auth.py` الموجودين بالمجلد، فلازم
يكون عندك نفس متغيرات البيئة (`BOT_TOKEN`, `UPSTASH_REDIS_REST_URL`,
`UPSTASH_REDIS_REST_TOKEN`) — إما بالقيم الافتراضية داخل `config.py` أو
مصدّرة بـ Termux (`export BOT_TOKEN=...`).

## سحب صلاحية مستخدم
```python
from main import revoke_user_access
revoke_user_access(123456789)
```
يشيله من قائمة المرخّص لهم + يلغي اشتراكه بالشارت اليومي تلقائياً.
