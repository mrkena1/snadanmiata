# charts.py
# يجيب "أفضل الأغاني عالمياً حالياً" من Deezer — API عام ومجاني بدون أي مفتاح
# ولا تسجيل حساب. المصدر: https://api.deezer.com/chart/0/tracks

import logging

import requests

log = logging.getLogger("charts")

DEEZER_CHART_URL = "https://api.deezer.com/chart/0/tracks"


def get_top_tracks(limit: int = 10) -> list[dict]:
    """
    يرجع لستة بأفضل الأغاني عالمياً حالياً حسب Deezer.
    كل عنصر: id / title / artist / link / cover / duration
    يرجع لستة فاضية لو صار خطأ بالاتصال (مايرمي Exception عشان ما يوقف الإرسال اليومي).
    """
    try:
        resp = requests.get(DEEZER_CHART_URL, params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        log.error(f"تعذر جلب الشارت من Deezer: {e}")
        return []

    # الـ endpoint يرجع عادة {"data": [...], "total": .., "next": ..}
    # نتعامل بشكل دفاعي لو تغير الشكل مستقبلاً.
    raw_tracks = payload.get("data") or payload.get("tracks", {}).get("data", [])

    tracks = []
    for t in raw_tracks[:limit]:
        artist = (t.get("artist") or {}).get("name", "Unknown Artist")
        album = t.get("album") or {}
        tracks.append({
            "id": t.get("id"),
            "title": t.get("title_short") or t.get("title", "Unknown"),
            "artist": artist,
            "link": t.get("link", ""),
            "cover": album.get("cover_big") or album.get("cover_medium"),
            "duration": t.get("duration", 0),
        })
    return tracks
