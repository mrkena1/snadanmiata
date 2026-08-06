# chat_engine.py
# منطق بوت الشات (كاسكا) — نفس المنطق الأصلي، فقط الذاكرة صارت تترزن على
# Upstash Redis بدل ملف JSON محلي (Render Free ما يدعم Persistent Disk).

import logging
import threading
import time

import requests
from requests.adapters import HTTPAdapter, Retry

from config import (
    GROQ_API_KEY, GROQ_MODEL,
    MAX_HISTORY_MESSAGES, GROQ_MIN_INTERVAL, REQUEST_TIMEOUT,
)
from persona import get_system_prompt
from redis_store import KEY_MEMORY, get_json, set_json

log = logging.getLogger("chat_engine")
GROQ_API = "https://api.groq.com/openai/v1/chat/completions"


def _make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=4, backoff_factor=1.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


session = _make_session()


class RateLimiter:
    """يضمن فاصلًا زمنيًا أدنى بين طلبات Groq المتتالية لتفادي تجاوز حد RPM."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()


groq_rate_limiter = RateLimiter(GROQ_MIN_INTERVAL)


class Memory:
    """ذاكرة محادثة لكل مستخدم، محفوظة كـ JSON واحد بمفتاح Redis (صيغة OpenAI: user/assistant)."""

    def __init__(self):
        self._lock = threading.Lock()

    def _load_all(self) -> dict:
        return get_json(KEY_MEMORY, default={})

    def _save_all(self, data: dict):
        set_json(KEY_MEMORY, data)

    def get(self, user_id: str) -> list:
        return self._load_all().get(user_id, [])

    def append(self, user_id: str, role: str, text: str):
        with self._lock:
            data = self._load_all()
            history = data.setdefault(user_id, [])
            history.append({"role": role, "content": text})
            if len(history) > MAX_HISTORY_MESSAGES:
                data[user_id] = history[-MAX_HISTORY_MESSAGES:]
            self._save_all(data)

    def reset(self, user_id: str):
        with self._lock:
            data = self._load_all()
            data.pop(user_id, None)
            self._save_all(data)


memory = Memory()


def ask_groq(user_id: str, user_text: str) -> str:
    """يرسل رسالة المستخدم + تاريخ محادثته لـ Groq ويرجع الرد.
    البرومت يتغير حسب شخصية كاسكا اللي اختارها هذا اليوزر بـ /chatarea."""
    groq_rate_limiter.wait()

    system_prompt = get_system_prompt(user_id)
    messages = (
        [{"role": "system", "content": system_prompt}]
        + memory.get(user_id)
        + [{"role": "user", "content": user_text}]
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    try:
        resp = session.post(GROQ_API, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)

        if resp.status_code == 429:
            log.warning("Groq أرجع 429 (تجاوز الحصة)")
            return "⚠️ تم تجاوز الحد المسموح من الطلبات لدى Groq حاليًا. انتظر قليلًا ثم حاول مجددًا."

        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text or "⚠️ تم استلام رد فارغ من النموذج."

    except requests.exceptions.Timeout:
        return "⚠️ انتهت مهلة الاتصال بـ Groq، حاول مرة أخرى."
    except requests.exceptions.RequestException as e:
        log.error(f"خطأ في طلب Groq: {e}")
        return "⚠️ حدث خطأ أثناء الاتصال بـ Groq، حاول لاحقًا."


def handle_chat_text(user_id: str, text: str) -> str:
    """نقطة الدخول اللي يستدعيها main.py: يرد ويحدّث الذاكرة."""
    if text.strip() == "/reset":
        memory.reset(user_id)
        return "✅ تم مسح سياق المحادثة، يمكنك البدء من جديد."

    reply = ask_groq(user_id, text)
    memory.append(user_id, "user", text)
    memory.append(user_id, "assistant", reply)
    return reply
