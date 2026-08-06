# broadcast.py
# يبني رسالة "أفضل استماعات اليوم" ويرسلها لكل المستخدمين اللي فعّلوا /newsongs
# (مو كل المرخّص لهم — الإرسال اليومي صار اختياري/opt-in). حالة "انرسل اليوم
# أو لا" تترزن على Redis بدل ملف محلي.

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import charts
from auth import list_subscribed_users
from config import CHART_LIMIT, TIMEZONE
from redis_store import KEY_DAILY_STATE, get_json, set_json

log = logging.getLogger("broadcast")

RANK_EMOJIS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def _today_str() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")


def already_sent_today() -> bool:
    return get_json(KEY_DAILY_STATE, default={}).get("last_sent") == _today_str()


def _mark_sent_today() -> None:
    set_json(KEY_DAILY_STATE, {"last_sent": _today_str()})


def build_message(tracks: list[dict]) -> str:
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y")
    lines = ["🎧 *أفضل استماعات اليوم عالمياً*", f"📅 {today}", ""]

    for i, t in enumerate(tracks):
        emoji = RANK_EMOJIS[i] if i < len(RANK_EMOJIS) else f"{i + 1}."
        lines.append(f"{emoji} *{t['title']}*")
        lines.append(f"      🎤 {t['artist']}")
        if t.get("link"):
            lines.append(f"      🔗 [استمع الحين]({t['link']})")
        lines.append("")

    lines.append("_📊 المصدر: Deezer Global Chart_")
    lines.append("_🔕 لإلغاء الاشتراك، أرسل /newsongs مرة ثانية_")
    return "\n".join(lines)


def send_daily_chart(bot, force: bool = False) -> dict:
    """
    يبني رسالة الشارت اليومي ويرسلها لكل المشتركين بـ /newsongs.
    force=True يتجاوز فحص 'انرسل اليوم أو لا' (مفيد للاختبار اليدوي).
    """
    if not force and already_sent_today():
        return {"status": "skipped", "reason": "already_sent_today"}

    tracks = charts.get_top_tracks(CHART_LIMIT)
    if not tracks:
        return {"status": "error", "reason": "no_chart_data"}

    message = build_message(tracks)
    users = list_subscribed_users()

    sent, failed = 0, 0
    for user_id in users:
        try:
            bot.send_message(user_id, message, parse_mode="Markdown", disable_web_page_preview=True)
            sent += 1
        except Exception as e:
            failed += 1
            log.warning(f"فشل إرسال الشارت للمستخدم {user_id}: {e}")
        time.sleep(0.05)  # تفادي حد Telegram لعدد الرسائل بالثانية

    _mark_sent_today()
    log.info(f"✅ تم إرسال الشارت اليومي: {sent} نجاح / {failed} فشل من أصل {len(users)}")
    return {"status": "sent", "sent": sent, "failed": failed, "total": len(users)}
