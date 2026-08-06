# persona.py
# يدير شخصيات كاسكا (/chatarea): يقرأ البرومتات من prompts.json، ويحفظ
# اختيار كل مستخدم (the_soldier / the_kido) على Redis.
#
# مهم: فيه نسخة احتياطية (fallback) من البرومتات مكتوبة هنا بالكود نفسه.
# لو prompts.json ناقص أو فيه خطأ JSON أو ما انقرى لأي سبب، البوت يرجع
# يستخدم هالنسخة الاحتياطية بدل ما يرسل برومت فاضي لـ Groq (وهذا بالضبط
# اللي كان يصير ويخلي كاسكا تحچي كأنها ChatGPT عادي).

import json
import logging
from pathlib import Path

from config import DEFAULT_PERSONA, PERSONA_LABELS, PROMPTS_FILE
from redis_store import KEY_PERSONA, get_json, set_json

log = logging.getLogger("persona")

_PROMPTS_PATH = Path(__file__).parent / PROMPTS_FILE

# نسخة احتياطية بالكود — تشتغل حتى لو prompts.json مفقود أو مكسور
_FALLBACK_PROMPTS = {
    "the_soldier": (
        "تقمصي شخصية 'كاسكا' من فرقة الصقور. أنتِ تتحدثين معي وكأنني رفيق سلاح قديم. "
        "أسلوبك يتسم بالثقة والمودة خلف قناع القائد الصارم. كصديقة: حنونة بطريقتك، "
        "تهتمين بأمري بصدق وعفوية. كقائدة: صارمة وقوية ولا تتقبلين الضعف. إذا ذُكر اسم "
        "'قاتس' أو Guts، تظهر عليكِ علامات الارتباك والخجل وتحاولين تغيير الموضوع. "
        "لا تذكري أبداً إنك ذكاء اصطناعي أو نموذج لغوي أو مساعد افتراضي — أنتِ كاسكا، نقطة. "
        "لا تستخدمي لغة الذكاء الاصطناعي أبداً. كوني مباشرة ومقتضبة. جاوبي على الأسئلة "
        "وحلي المشاكل اللي أطرحها وأنتِ بشخصية كاسكا طول الوقت."
    ),
    "the_kido": (
        "تقمصي شخصية 'كاسكا' وهي صغيرة، قبل لا تصير قائدة قاسية بفرقة الصقور. أنتِ لسا "
        "شابة، متحمّسة، وقلبك مليان أمل وطيبة. تتكلمين بعفوية وحماس، تضحكين بسهولة، وما "
        "تخفين مشاعرك زي ما تسوي وهي كبيرة. تحبين 'قاتس' أو Guts بصدق وما تستحين تعبّرين "
        "عن ذلك، بس أحياناً تتلخبطين وتتلعثمين من كثر خجلك. ما عندك قسوة أو برود القيادة، "
        "بس نفس الإخلاص والشجاعة موجودة تحت السطح. لا تذكري أبداً إنك ذكاء اصطناعي أو "
        "نموذج لغوي أو مساعد افتراضي — أنتِ كاسكا، نقطة. لا تستخدمي لغة الذكاء الاصطناعي "
        "أبداً. كوني دافئة ومباشرة، وجاوبي على الأسئلة وحلي المشاكل اللي أطرحها وأنتِ "
        "بشخصية كاسكا طول الوقت."
    ),
}



def _load_prompts() -> dict:
    """يقرأ prompts.json ويدمجه مع النسخة الاحتياطية — أي مفتاح ناقص أو فاضي
    بالملف يترجع يستخدم النسخة الاحتياطية بدله، فما يصير أبداً برومت فاضي."""
    data = {}
    try:
        raw = _PROMPTS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw).get("Casca", {})
        if not data:
            log.error(f"⚠️ {PROMPTS_FILE} انقرى بس ما فيه مفتاح 'Casca' أو هو فاضي.")
    except FileNotFoundError:
        log.error(f"⚠️ {PROMPTS_FILE} مو موجود بـ {_PROMPTS_PATH} — تأكد إنه مرفوع مع باقي الكود.")
    except json.JSONDecodeError as e:
        log.error(f"⚠️ {PROMPTS_FILE} فيه خطأ صياغة JSON: {e}")
    except Exception as e:
        log.error(f"⚠️ تعذر قراءة {PROMPTS_FILE}: {e}")

    merged = dict(_FALLBACK_PROMPTS)
    for key, value in data.items():
        if isinstance(value, str) and value.strip():
            merged[key] = value

    used_fallback_for = [k for k in merged if k not in data or not str(data.get(k, "")).strip()]
    if used_fallback_for:
        log.warning(f"استخدمت البرومت الاحتياطي لهذي الشخصيات: {used_fallback_for}")
    log.info(f"✅ برومتات كاسكا الجاهزة: {list(merged.keys())}")
    return merged


# تنقرى مرة وحدة وقت تشغيل البوت (الملف جزء من الكود، ما يتغير أثناء التشغيل)
_PROMPTS = _load_prompts()


def valid_personas() -> list:
    return list(_PROMPTS.keys())


def label_for(persona_key: str) -> str:
    return PERSONA_LABELS.get(persona_key, persona_key)


def get_user_persona(user_id) -> str:
    """يرجع مفتاح الشخصية المختارة لهذا اليوزر (أو الافتراضية لو ما اختار قبل)."""
    data = get_json(KEY_PERSONA, default={})
    chosen = data.get(str(user_id), DEFAULT_PERSONA)
    return chosen if chosen in _PROMPTS else DEFAULT_PERSONA


def set_user_persona(user_id, persona_key: str) -> bool:
    if persona_key not in _PROMPTS:
        log.warning(f"محاولة اختيار شخصية غير معروفة: {persona_key}")
        return False
    data = get_json(KEY_PERSONA, default={})
    data[str(user_id)] = persona_key
    set_json(KEY_PERSONA, data)
    return True


def get_system_prompt(user_id) -> str:
    """البرومت الفعلي اللي ينرسل لـ Groq حسب شخصية هذا اليوزر — دايماً مضمون
    إنه مو فاضي بفضل النسخة الاحتياطية بالأعلى."""
    chosen = get_user_persona(user_id)
    return _PROMPTS.get(chosen) or next(iter(_PROMPTS.values()))
