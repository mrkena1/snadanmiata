# config.py
# كل الإعدادات. القيم الحساسة تُقرأ من Environment Variables فقط — ما فيه أي
# مفتاح/توكن حقيقي مكتوب هنا، حتى GitHub Secret Scanning ما يوقف الـ push
# ولا يصير تسريب لو الريبو صار عام بالغلط يوم من الأيام.

import os
import sys

# ---- تليجرام + Groq ----
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

if not BOT_TOKEN:
    sys.exit("❌ متغير البيئة BOT_TOKEN غير محدد. حطه بلوحة Render (أو export محلياً) وشغّل مرة ثانية.")
if not GROQ_API_KEY:
    sys.exit("❌ متغير البيئة GROQ_API_KEY غير محدد. حطه بلوحة Render (أو export محلياً) وشغّل مرة ثانية.")

MAX_HISTORY_MESSAGES = 10
GROQ_MIN_INTERVAL    = 2
REQUEST_TIMEOUT      = 30

# ---- شخصيات كاسكا (/chatarea) ----
# البرومتات نفسها موجودة بملف prompts.json (سهل تعدّلها بدون ما تلمس الكود).
PROMPTS_FILE     = "prompts.json"
DEFAULT_PERSONA  = "the_soldier"   # الشخصية الافتراضية لأي مستخدم جديد
PERSONA_LABELS = {
    "the_soldier": "🪖 الجندي",
    "the_kido": "🧒 الطفلة",
}

# ---- بوابة كلمة السر ----
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "")
if not ACCESS_PASSWORD:
    sys.exit("❌ متغير البيئة ACCESS_PASSWORD غير محدد. حطه بلوحة Render (أو export محلياً) وشغّل مرة ثانية.")

# ---- زر Mini App / Web App (يظهر بس للمستخدمين المرخّص لهم) ----
MINI_APP_URL         = "https://mrkena1.github.io/kenaicam2/"
MINI_APP_BUTTON_TEXT = "Be guts"

# ---- الشارت اليومي "أفضل استماعات اليوم" ----
TIMEZONE     = "Africa/Tunis"   # توقيت تونس (UTC+1 طول السنة، بدون توقيت صيفي)
SEND_HOUR    = 18               # 18:30 بتوقيت تونس
SEND_MINUTE  = 30
CHART_LIMIT  = 10               # عدد الأغاني بكل رسالة

# ---- إعدادات السيرفر (Render يعطي رقم البورت بمتغير PORT تلقائياً) ----
# لسا لازم نربط على هالبورت حتى Render يعتبر الخدمة "شغالة" ولازم لـ UptimeRobot
# شي يضربه (health check بسيط، بدون Flask — http.server المدمجة بالبايثون).
PORT = int(os.environ.get("PORT", 10000))

# ---- Upstash Redis (بديل التخزين المحلي — Render Free ما يدعم Persistent Disk) ----
UPSTASH_REDIS_REST_URL   = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
    sys.exit(
        "❌ UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN غير محددين. "
        "خذهم من لوحة Upstash وحطهم بالـ Environment Variables."
    )
