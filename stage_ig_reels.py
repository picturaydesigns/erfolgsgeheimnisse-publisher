# -*- coding: utf-8 -*-
"""Stellt die 7 neuen ruhigen IG-Reels (Hamsterrad-Flow, Stimme Victor) in die Publish-Queue.
Slot 09:00 lokal = 07:00 UTC, 15.-21.06.2026 (fuellt den Morgen-Slot, der nach dem 14.06. leer laeuft).
KI-Kennzeichnung in jeder Caption + ai_label.
ACHTUNG: Welle vom 15.-21.06. wurde bereits gestagt - NICHT erneut ausfuehren (Duplikate)!
Dient als VORLAGE fuer kuenftige Reel-Wellen. Plattform-Regel seit Auftrag 27:
Video-Wellen standardmaessig platforms="instagram,tiktok,youtube" + yt_title/yt_description."""
import sys, os, hashlib, time, json, requests
from yt_meta import build_yt_meta
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\reels\strand-test"

def load_cfg():
    with open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8") as f:
        return json.load(f)

def cloudinary_upload(path, cc):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/video/upload",
            data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=600)
    j = r.json()
    if "secure_url" not in j:
        raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen: {j}")
    return j["secure_url"]

def airtable_create(at, fields):
    """Seit 20.07.2026: Datei-Queue statt Airtable (Name bleibt, damit alle Aufrufe halten)."""
    import filequeue
    return filequeue.queue_append(fields)