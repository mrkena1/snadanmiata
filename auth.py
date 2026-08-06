# auth.py
# بوابة كلمة السر + إدارة الاشتراك بأمر /newsongs — كلها مخزنة على Upstash Redis
# (SET لكل حالة) بدل ملف JSON محلي.

from redis_store import (
    KEY_AUTHORIZED_USERS, KEY_SUBSCRIBED_USERS,
    sadd, sismember, smembers, srem,
)


# ---------------- بوابة كلمة السر ----------------
def is_authorized(user_id: int) -> bool:
    return sismember(KEY_AUTHORIZED_USERS, user_id)


def authorize_user(user_id: int) -> None:
    sadd(KEY_AUTHORIZED_USERS, user_id)


def revoke_user(user_id: int) -> None:
    """يسحب صلاحية الدخول + يلغي اشتراكه بالشارت اليومي تلقائياً."""
    srem(KEY_AUTHORIZED_USERS, user_id)
    srem(KEY_SUBSCRIBED_USERS, user_id)


def list_authorized_users() -> list:
    return smembers(KEY_AUTHORIZED_USERS)


# ---------------- اشتراك /newsongs (أفضل استماعات اليوم) ----------------
def is_subscribed(user_id: int) -> bool:
    return sismember(KEY_SUBSCRIBED_USERS, user_id)


def subscribe_user(user_id: int) -> None:
    sadd(KEY_SUBSCRIBED_USERS, user_id)


def unsubscribe_user(user_id: int) -> None:
    srem(KEY_SUBSCRIBED_USERS, user_id)


def list_subscribed_users() -> list:
    return smembers(KEY_SUBSCRIBED_USERS)
