# -*- coding: utf-8 -*-
"""TikTok-Poster ueber upload-post.com (auditierte TikTok-App, kein eigenes Audit noetig).

Warum nicht die offizielle TikTok Content Posting API direkt? Ohne bestandenes App-Audit
(1-4 Wochen, Demo-Video, Ausgang unsicher) postet sie nur privat (SELF_ONLY). upload-post
hat das Audit bestanden -> wir posten ueber deren REST-API sofort oeffentlich.
Eigenes Audit bleibt spaetere Spar-Option (dann diesen Adapter austauschen, Signatur behalten).

  POST {API}/upload         -> Video  (nimmt PUBLIC URL direkt an)
  POST {API}/upload_photos  -> Foto-Karussell (nur Datei-Upload -> erst herunterladen)
Kosten/Limit: Gratis-Tarif 10 Uploads/Monat, Basic unbegrenzt.
"""
import os
import tempfile

import requests

from platforms.uploadpost import API, check, headers, token_ok  # noqa: F401 (token_ok re-export)


def publish_video(video_url, caption, api_key, profile, ai_generated=True):
    """Video posten. video_url = oeffentliche Cloudinary-URL (wird durchgereicht)."""
    data = {
        "user": profile,
        "platform[]": "tiktok",
        "video": video_url,
        "title": (caption or "")[:2200],
        "tiktok_title": (caption or "")[:2200],
        "post_mode": "DIRECT_POST",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "is_aigc": "true" if ai_generated else "false",
    }
    r = requests.post(f"{API}/upload", headers=headers(api_key), data=data, timeout=600)
    return check(r, "tiktok")


def publish_photos(image_urls, caption, api_key, profile, ai_generated=True):
    """Foto-Karussell posten. image_urls = Cloudinary-URLs in Slide-Reihenfolge.
    Die API verlangt Datei-Uploads -> Bilder kurz herunterladen und als multipart senden.
    ai_generated: kein is_aigc-Parameter im Foto-Endpoint -> Kennzeichnung steht im Caption-Text.
    """
    data = {
        "user": profile,
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
            r = requests.post(f"{API}/upload_photos", headers=headers(api_key),
                              data=data, files=files, timeout=600)
    finally:
        for h in handles:
            h.close()
    return check(r, "tiktok")
