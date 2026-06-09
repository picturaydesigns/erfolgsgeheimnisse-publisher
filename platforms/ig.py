# -*- coding: utf-8 -*-
"""Instagram-Poster (Instagram-Login-API, graph.instagram.com).
Portiert die bewaehrte Logik aus scripts/publish_reel.ps1:
  Cloudinary-URL -> REELS-Container -> Status pollen bis FINISHED -> media_publish.
LAEUFT: Logik ist auf Instagram bereits erprobt (nur Cloudinary-Zugang noch noetig).
"""
import time
import requests

API = "https://graph.instagram.com/v22.0"


def publish(video_url, caption, ig_user_id, access_token,
            share_to_feed=True, poll_max=60, poll_every=5):
    """Postet ein Reel und gibt die Media-ID zurueck. Wirft RuntimeError bei Fehler."""
    # 1) REELS-Container anlegen
    r = requests.post(f"{API}/{ig_user_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": access_token,
    }, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError(f"IG Container-Fehler: {j}")
    cid = j["id"]

    # 2) Status pollen (Video-Verarbeitung dauert)
    status = None
    for _ in range(poll_max):
        time.sleep(poll_every)
        s = requests.get(f"{API}/{cid}", params={
            "fields": "status_code,status", "access_token": access_token
        }, timeout=60).json()
        status = s.get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG Verarbeitung {status}: {s}")
    if status != "FINISHED":
        raise RuntimeError("IG Timeout: Video nicht fertig verarbeitet")

    # 3) Veroeffentlichen
    time.sleep(2)
    p = requests.post(f"{API}/{ig_user_id}/media_publish", data={
        "creation_id": cid, "access_token": access_token
    }, timeout=60).json()
    if "id" not in p:
        raise RuntimeError(f"IG Publish-Fehler: {p}")
    return p["id"]


def token_ok(ig_user_id, access_token):
    """Read-only Health-Check: prueft ob der Token gueltig ist (postet NICHTS).
    Gibt (True, info-dict) bei gueltigem Token, sonst (False, fehler-dict/str)."""
    try:
        r = requests.get(f"{API}/{ig_user_id}", params={
            "fields": "username,followers_count", "access_token": access_token
        }, timeout=30).json()
    except Exception as e:
        return False, str(e)
    if "username" in r:
        return True, r
    return False, r


def refresh_long_lived_token(access_token):
    """Verlaengert den Long-Lived-Token (alle ~60 Tage noetig). Gibt das JSON zurueck
    (access_token, token_type, expires_in). Der neue Token muss persistiert werden."""
    return requests.get(f"{API}/refresh_access_token", params={
        "grant_type": "ig_refresh_token", "access_token": access_token
    }, timeout=60).json()
