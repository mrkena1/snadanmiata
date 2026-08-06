# main.py
# نقطة التشغيل الموحدة: بوابة كلمة سر -> شات مباشر (كاسكا/Groq)
# + /topsongs لعرض أفضل استماعات اليوم فوراً
# + /newsongs لتفعيل/إلغاء الاشتراك بإرسال أفضل استماعات اليوم تلقائياً كل يوم
#
# ما فيه Flask — بس سيرفر HTTP صغير جداً (مكتبة http.server المدمجة بالبايثون)
# يرد "ok" على أي طلب، عشان:
#   1) Render يعتبر الخدمة "شغالة" (لازم أي Web Service يربط على $PORT).
#   2) UptimeRobot يقدر يضربها كل 5 دقايق ويخليها صاحية.
# الإرسال اليومي نفسه يصير من جدولة داخلية بسيطة (thread) تفحص الوقت كل 30 ثانية.

import http.server
import logging
import socketserver
import threading
import time as time_module
from datetime import datetime
from zoneinfo import ZoneInfo

import telebot
from telebot import types

import broadcast
import chat_engine
import charts
import persona
from auth import (
    authorize_user, is_authorized, is_subscribed,
    revoke_user, subscribe_user, unsubscribe_user,
)
from config import (
    ACCESS_PASSWORD, BOT_TOKEN, MINI_APP_BUTTON_TEXT,
    MINI_APP_URL, PORT, SEND_HOUR, SEND_MINUTE, TIMEZONE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("main")

bot = telebot.TeleBot(BOT_TOKEN)

# يشيل زر الـ Web App/Mini App الافتراضي (يترجع يتفعّل بس للمرخّص لهم)
try:
    try:
        _default_button = types.MenuButtonDefault(type="default")
    except TypeError:
        _default_button = types.MenuButtonDefault()
    bot.set_chat_menu_button(menu_button=_default_button)
except Exception as e:
    log.warning(f"تعذر تصفير Menu Button: {e}")

try:
    bot.set_my_commands([
        types.BotCommand("start", "بدء / فتح البوت"),
        types.BotCommand("topsongs", "🎧 أفضل استماعات اليوم (الحين)"),
        types.BotCommand("newsongs", "🔔 تفعيل/إلغاء الإرسال اليومي التلقائي"),
        types.BotCommand("chatarea", "🎭 تغيير طريقة كلام كاسكا"),
        types.BotCommand("reset", "🔄 مسح سياق المحادثة"),
    ])
except Exception as e:
    log.warning(f"تعذر تصفير قائمة الأوامر: {e}")


def enable_mini_app_button(chat_id):
    try:
        try:
            menu_button = types.MenuButtonWebApp(
                type="web_app", text=MINI_APP_BUTTON_TEXT,
                web_app=types.WebAppInfo(url=MINI_APP_URL),
            )
        except TypeError:
            menu_button = types.MenuButtonWebApp(
                text=MINI_APP_BUTTON_TEXT, web_app=types.WebAppInfo(url=MINI_APP_URL),
            )
        bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)
    except Exception as e:
        log.warning(f"تعذر تفعيل زر Mini App للمستخدم {chat_id}: {e}")


def disable_mini_app_button(chat_id):
    try:
        try:
            menu_button = types.MenuButtonDefault(type="default")
        except TypeError:
            menu_button = types.MenuButtonDefault()
        bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)
    except Exception as e:
        log.warning(f"تعذر تصفير زر Mini App للمستخدم {chat_id}: {e}")


def revoke_user_access(user_id):
    """يسحب صلاحية المستخدم كاملة: يشيله من قائمة المرخّص لهم + من الاشتراك + يصفر له الزر."""
    revoke_user(user_id)
    disable_mini_app_button(user_id)


def _safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id

    if not is_authorized(user_id):
        bot.send_message(
            message.chat.id,
            "🔒 هذا البوت خاص.\nأرسل كلمة السر للمتابعة:",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

    enable_mini_app_button(message.chat.id)
    bot.send_message(
        message.chat.id,
        "أهلاً 👋 تقدر تحچي وياي عادي بأي وقت.\n"
        "اكتب /topsongs لو تبي تشوف أفضل استماعات اليوم الحين.\n"
        "أو اكتب /newsongs لو تبيني أبعتهالك تلقائياً كل يوم.\n"
        "أو اكتب /chatarea لو تبي تغيّر طريقة كلامي وياك.",
    )


# ---------------------------------------------------------------------------
# /topsongs — يعرض شارت اليوم فوراً عند الطلب
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['topsongs'])
def cmd_topsongs(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_authorized(user_id):
        bot.send_message(chat_id, "🔒 هذا البوت خاص.\nأرسل كلمة السر للمتابعة:")
        return

    msg = bot.send_message(chat_id, "🔎 *جاري جلب الشارت...*", parse_mode="Markdown")
    try:
        tracks = charts.get_top_tracks()
        _safe_delete(chat_id, msg.message_id)

        if not tracks:
            bot.send_message(chat_id, "⚠️ ما قدرت أجيب الشارت حالياً، جرب بعد شوي.")
            return

        bot.send_message(
            chat_id, broadcast.build_message(tracks),
            parse_mode="Markdown", disable_web_page_preview=True,
        )
    except Exception as e:
        _safe_delete(chat_id, msg.message_id)
        bot.send_message(chat_id, "⚠️ صار خطأ أثناء جلب الشارت.")
        log.error(f"Topsongs Error: {e}")


# ---------------------------------------------------------------------------
# /newsongs — تفعيل/إلغاء الإرسال اليومي التلقائي (يحتاج موافقة صريحة)
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['newsongs'])
def cmd_newsongs(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_authorized(user_id):
        bot.send_message(chat_id, "🔒 هذا البوت خاص.\nأرسل كلمة السر للمتابعة:")
        return

    if is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔕 إلغاء الاشتراك", callback_data="newsongs_unsub"))
        bot.send_message(
            chat_id,
            "🎧 أنت مشترك أصلاً بـ *أفضل استماعات اليوم* — توصلك تلقائياً كل يوم.",
            parse_mode="Markdown", reply_markup=markup,
        )
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ موافق، فعّلها", callback_data="newsongs_approve"),
        types.InlineKeyboardButton("❌ لا، شكراً", callback_data="newsongs_decline"),
    )
    bot.send_message(
        chat_id,
        "🎧 *أفضل استماعات اليوم*\n\n"
        f"إذا وافقت، رح أبعتلك تلقائياً كل يوم الساعة {SEND_HOUR:02d}:{SEND_MINUTE:02d} "
        "(بتوقيت تونس) أفضل 10 أغاني عالمياً.\n\n"
        "تفعّل الاشتراك؟",
        parse_mode="Markdown", reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda c: c.data in ("newsongs_approve", "newsongs_decline", "newsongs_unsub"))
def cb_newsongs(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if call.data == "newsongs_approve":
        subscribe_user(user_id)
        bot.answer_callback_query(call.id, "تم التفعيل ✅")
        bot.edit_message_text(
            "✅ تم تفعيل الاشتراك! رح توصلك أفضل استماعات اليوم كل يوم تلقائياً.\n"
            "تقدر تلغيها بأي وقت بإرسال /newsongs مرة ثانية.",
            chat_id, call.message.message_id,
        )
    elif call.data == "newsongs_decline":
        bot.answer_callback_query(call.id, "تمام، ملغى")
        bot.edit_message_text(
            "تمام، ما فعّلتها. تقدر ترسل /newsongs بأي وقت لو غيّرت رأيك.",
            chat_id, call.message.message_id,
        )
    elif call.data == "newsongs_unsub":
        unsubscribe_user(user_id)
        bot.answer_callback_query(call.id, "تم إلغاء الاشتراك")
        bot.edit_message_text(
            "🔕 تم إلغاء اشتراكك من أفضل استماعات اليوم.",
            chat_id, call.message.message_id,
        )


# ---------------------------------------------------------------------------
# /chatarea — تغيير طريقة كلام كاسكا (الجندي / الطفلة)
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['chatarea'])
def cmd_chatarea(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_authorized(user_id):
        bot.send_message(chat_id, "🔒 هذا البوت خاص.\nأرسل كلمة السر للمتابعة:")
        return

    current = persona.get_user_persona(user_id)
    markup = types.InlineKeyboardMarkup()
    for key in persona.valid_personas():
        label = persona.label_for(key)
        text = f"✅ {label} (الحالية)" if key == current else label
        markup.add(types.InlineKeyboardButton(text, callback_data=f"persona_{key}"))

    bot.send_message(
        chat_id,
        f"🎭 *طريقة كلام كاسكا وياك*\n\nالحالية: *{persona.label_for(current)}*\n\nاختار وحدة:",
        parse_mode="Markdown", reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("persona_"))
def cb_chatarea(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    persona_key = call.data.removeprefix("persona_")

    if persona_key not in persona.valid_personas():
        bot.answer_callback_query(call.id, "❌ خيار غير معروف")
        return

    persona.set_user_persona(user_id, persona_key)
    label = persona.label_for(persona_key)
    bot.answer_callback_query(call.id, f"تم التغيير لـ {label}")
    bot.edit_message_text(
        f"✅ تم تغيير طريقة كلام كاسكا وياك لـ *{label}*.\n"
        "جرب احچي وياها الحين وشوف الفرق 🎭\n"
        "تقدر تغيّرها بأي وقت بإرسال /chatarea مرة ثانية.",
        chat_id, call.message.message_id, parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# الموجّه المركزي لكل رسالة نصية (غير الأوامر) — بوابة كلمة سر ثم شات مباشر
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.content_type == 'text' and not m.text.startswith('/'))
def route_text(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip()

    # 1) بوابة كلمة السر
    if not is_authorized(user_id):
        if text == ACCESS_PASSWORD:
            authorize_user(user_id)
            enable_mini_app_button(chat_id)
            bot.send_message(chat_id, "✅ تم التحقق! أهلاً فيك.")
            bot.send_message(
                chat_id,
                "تقدر تحچي وياي عادي، واكتب /newsongs لو تبيني أبعتلك أفضل "
                "استماعات اليوم تلقائياً كل يوم، أو /topsongs لو تبي تشوفها الحين.\n"
                "واكتب /chatarea لو تبي تغيّر طريقة كلامي وياك.",
            )
        else:
            bot.send_message(
                chat_id, "🔒 كلمة السر غلط. حاول مرة ثانية:",
                reply_markup=types.ReplyKeyboardRemove(),
            )
        return

    # 2) الوضع الافتراضي: شات مباشر
    reply = chat_engine.handle_chat_text(str(user_id), text)
    bot.send_message(chat_id, reply)


# ---------------------------------------------------------------------------
# سيرفر HTTP صغير جداً — بس عشان Render + UptimeRobot، بدون Flask
# ---------------------------------------------------------------------------
class _PingHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass  # نطفي لوقات http.server الافتراضية عشان ما تزحم اللوق


def _http_server_loop():
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), _PingHandler) as httpd:
        log.info(f"✅ سيرفر Ping شغال على البورت {PORT} (لـ Render + UptimeRobot)")
        httpd.serve_forever()


def _scheduler_loop():
    """جدولة بسيطة: كل 30 ثانية تتأكد إذا وصلنا وقت الإرسال اليومي وترسله."""
    while True:
        try:
            now = datetime.now(ZoneInfo(TIMEZONE))
            if now.hour == SEND_HOUR and now.minute == SEND_MINUTE:
                broadcast.send_daily_chart(bot)
        except Exception as e:
            log.warning(f"خطأ بالجدولة الداخلية: {e}")
        time_module.sleep(30)


def _polling_loop():
    log.info("✅ Telegram polling شغال...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    threading.Thread(target=_polling_loop, daemon=True).start()
    threading.Thread(target=_scheduler_loop, daemon=True).start()
    _http_server_loop()  # بالثريد الرئيسي عشان يبقى البروسس شغال
