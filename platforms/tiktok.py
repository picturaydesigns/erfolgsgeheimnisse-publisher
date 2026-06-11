# -*- coding: utf-8 -*-
"""TikTok-Poster ueber upload-post.com (auditierte TikTok-App, kein eigenes Audit noetig).

Warum nicht die offizielle TikTok Content Posting API direkt? Ohne bestandenes App-Audit
(1-4 Wochen, Demo-Video, Ausgang unsicher) postet sie nur privat (SELF_ONLY). upload-post
hat das Audit bestanden -> wir posten ueber deren REST-API sofort oeffentlich.
Eigenes Audit bleibt spaetere Spar-Option (dann diesen Adapter austauschen, Signatur behalten).

API-Doku: https://docs.upload-post.com  (OpenAPI: /openapi.json)
  POST https://api.upload-post.com/api/upload         -> Video  (nimmt PUBLIC URL direkt an)
  POST https://api.upload-post.com/api/upload_photos  -> Foto-Karussell (nur Datei-Upload,
                                                         daher erst von Cloudinary herunterladen)
Auth-Header: "Authorization: Apikey <key>"
Kosten/Limit: Gratis-Tarif 10 Uploads/Monat, danach Bezahl-Tarif.
"""
import os
import tempfile

import requests

API = "https://api.upload-post.com/api"


def _headers(api_key):
    return {"Authorization": f"Apikey {api_key}"}


def _check(resp):
    """Antwort pruefen und Post-ID/URL fuer das permalinks-Feld extrahieren."""
    try:
        j = resp.json()
    except ValueError:
        raise RuntimeError(f"upload-post: keine JSON-Antwort (HTTP {resp.status_code}): {resp.text[:300]}")
    if resp.status_code >= 400 or j.get("success") is False:
        raise RuntimeError(f"upload-post-Fehler (HTTP {resp.status_code}): {j}")
    # Ergebnis-Formate variieren: results.tiktok / request_id (async)
    results = j.get("results") or {}
    tk = results.get("tiktok") or {}
    if isinstance(tk, dict):
        if tk.get("error"):
            raise RuntimeError(f"TikTok-Fehler: {tk['error']}")
        ref = tk.get("url") or tk.get("post_id") or tk.get("publish_id")
        if ref:
            return str(ref)
    return str(j.get("request_id") or "ok")


def publish_video(video_url, caption, api_key, tiktok_user, ai_generated=True):
    """Video posten. video_url = oeffentliche Cloudinary-URL (wird durchgereicht)."""
    data = {
        "user": tiktok_user,
        "platform[]": "tiktok",
        "video": video_url,
        "title": (caption or "")[:2200],
        "tiktok_title": (caption or "")[:2200],
        "post_mode": "DIRECT_POST",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "is_aigc": "true" if ai_generated else "false",
    }
    r = requests.post(f"{API}/upload", headers=_headers(api_key), data=data, timeout=600)
    return _check(r)


def publish_photos(image_urls, caption, api_key, tiktok_user, ai_generated=True):
    """Foto-Karussell posten. image_urls = Cloudinary-URLs in Slide-Reihenfolge.
    Die API verlangt Datei-Uploads -> Bilder kurz herunterladen und als multipart senden.
    ai_generated: kein is_aigc-Parameter im Foto-Endpoint -> Kennzeichnung steht im Caption-Text.
    """
    data = {
        "user": tiktok_user,
        "platform[]": "tiktok",
        "title": (caption or "")[:90],            # Foto-Post-Titel ist kurz
        "tiktok_description": (caption or "")[:2200],
        "photo_cover_index": "0",
        "auto_add_music": "true",                 # TikTok verlangt Musik bei Foto-Posts
    }
    files, handles = [], []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for i, url in enumerate(image_urls, 1):
                p = os.path.join(tmp, f"slide_{i:02d}.png")
                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                with open(p, "wb") as fh:
                    fh.write(resp.content)
                h = open(p, "rb")
                handles.append(h)
                files.append(("photos[]", (os.path.basename(p), h, "image/png")))
            r = requests.post(f"{API}/upload_photos", headers=_headers(api_key),
                              data=data, files=files, timeout=600)
    finally:
        for h in handles:
            h.close()
    return _check(r)


def token_ok(api_key):
    """Read-only Gesundheits-Check: stimmt der API-Key, haengt das TikTok-Profil dran?"""
    try:
        r = requests.get(f"{API}/uploadposts/users", headers=_headers(api_key), timeout=60)
        j = r.json()
        if r.status_code >= 400:
            return False, j
        profiles = j.get("profiles") or j.get("users") or j
        return True, profiles
    except Exception as e:
        return False, str(e)
