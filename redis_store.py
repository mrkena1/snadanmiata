# redis_store.py
# طبقة تخزين موحدة فوق Upstash Redis (REST، بدون اتصال TCP دائم — مناسب
# لـ Render Free اللي ينوّم السيرفر). تبدل كل ملفات الـ JSON المحلية اللي كانت
# تنستخدم قبل (authorized_users.json / memory.json / daily_state.json).

import json
import logging

from upstash_redis import Redis

from config import UPSTASH_REDIS_REST_TOKEN, UPSTASH_REDIS_REST_URL

log = logging.getLogger("redis_store")

if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
    log.warning(
        "⚠️ UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN غير محددين — "
        "التخزين (اليوزرات/الذاكرة/الاشتراكات) ما رح يشتغل صح."
    )

redis = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)

# ---- أسماء المفاتيح المستخدمة بكل المشروع ----
KEY_AUTHORIZED_USERS = "bot:authorized_users"       # SET: يوزرات دخلوا كلمة السر
KEY_SUBSCRIBED_USERS = "bot:newsongs_subscribers"    # SET: يوزرات فعّلوا /newsongs
KEY_DAILY_STATE       = "bot:daily_state"             # STRING (JSON): آخر تاريخ إرسال
KEY_MEMORY            = "bot:chat_memory"              # STRING (JSON): ذاكرة الشات لكل اليوزرات
KEY_PERSONA           = "bot:chat_persona"              # STRING (JSON): شخصية كاسكا المختارة لكل يوزر


# ---------------- عام: JSON key/value ----------------
def get_json(key: str, default=None):
    try:
        raw = redis.get(key)
        if raw is None:
            return default
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        log.error(f"Redis get_json({key}) error: {e}")
        return default


def set_json(key: str, value) -> None:
    try:
        redis.set(key, json.dumps(value, ensure_ascii=False))
    except Exception as e:
        log.error(f"Redis set_json({key}) error: {e}")


# ---------------- Sets (يوزرات مرخّصين / مشتركين بالشارت) ----------------
def sadd(key: str, member) -> None:
    try:
        redis.sadd(key, str(member))
    except Exception as e:
        log.error(f"Redis sadd({key}) error: {e}")


def srem(key: str, member) -> None:
    try:
        redis.srem(key, str(member))
    except Exception as e:
        log.error(f"Redis srem({key}) error: {e}")


def sismember(key: str, member) -> bool:
    try:
        return bool(redis.sismember(key, str(member)))
    except Exception as e:
        log.error(f"Redis sismember({key}) error: {e}")
        return False


def smembers(key: str) -> list:
    try:
        members = redis.smembers(key)
        return [int(m) for m in members]
    except Exception as e:
        log.error(f"Redis smembers({key}) error: {e}")
        return []
