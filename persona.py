# persona.py
# يدير شخصيات كاسكا (/chatarea): يقرأ البرومتات من prompts.json، ويحفظ
# اختيار كل مستخدم (the_soldier / the_kido) على Redis.

import json
import logging
from pathlib import Path

from config import DEFAULT_PERSONA, PERSONA_LABELS, PROMPTS_FILE
from redis_store import KEY_PERSONA, get_json, set_json

log = logging.getLogger("persona")

_PROMPTS_PATH = Path(__file__).parent / PROMPTS_FILE


def _load_prompts() -> dict:
    try:
        data = json.loads(_PROMPTS_PATH.read_text(encoding="utf-8"))
        return data.get("Casca", {})
    except Exception as e:
        log.error(f"تعذر قراءة {PROMPTS_FILE}: {e}")
        return {}


# تنقرى مرة وحدة وقت تشغيل البوت (الملف جزء من الكود، ما يتغير أثناء التشغيل)
_PROMPTS = _load_prompts()


def valid_personas() -> list:
    return list(PERSONA_LABELS.keys())


def label_for(persona_key: str) -> str:
    return PERSONA_LABELS.get(persona_key, persona_key)


def get_user_persona(user_id) -> str:
    """يرجع مفتاح الشخصية المختارة لهذا اليوزر (أو الافتراضية لو ما اختار قبل)."""
    data = get_json(KEY_PERSONA, default={})
    persona = data.get(str(user_id), DEFAULT_PERSONA)
    return persona if persona in _PROMPTS else DEFAULT_PERSONA


def set_user_persona(user_id, persona_key: str) -> None:
    if persona_key not in _PROMPTS:
        log.warning(f"شخصية غير معروفة: {persona_key}")
        return
    data = get_json(KEY_PERSONA, default={})
    data[str(user_id)] = persona_key
    set_json(KEY_PERSONA, data)


def get_system_prompt(user_id) -> str:
    """البرومت الفعلي اللي ينرسل لـ Groq حسب شخصية هذا اليوزر."""
    persona = get_user_persona(user_id)
    return _PROMPTS.get(persona) or next(iter(_PROMPTS.values()), "")
