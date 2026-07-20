# -*- coding: utf-8 -*-
"""Stellt alle geplanten Reels (#7-#28) auf einmal in die Airtable-Queue.
Jedes Reel wird zu Cloudinary hochgeladen und mit Postzeit eingetragen.
Aufruf:  python batch_stage.py
ACHTUNG: Welle #7-#28 wurde bereits gestagt - NICHT erneut ausfuehren (Duplikate)!
Dient als VORLAGE fuer kuenftige Wellen. Plattform-Regel seit Auftrag 27:
Video-Wellen standardmaessig platforms="instagram,tiktok,youtube" + yt_title/yt_description.
"""
import sys, os, hashlib, time, json, requests
from yt_meta import build_yt_meta
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

def load_cfg():
    with open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8") as f:
        return json.load(f)

def cloudinary_upload(path, cc):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/video/upload",
            data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300)
    j = r.json()
    if "secure_url" not in j:
        raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen: {j}")
    return j["secure_url"]

def airtable_create(at, fields):
    """Seit 20.07.2026: Datei-Queue statt Airtable (Name bleibt, damit alle Aufrufe halten)."""
    import filequeue
    return filequeue.queue_append(fields)