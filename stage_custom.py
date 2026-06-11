# -*- coding: utf-8 -*-
"""Stellt beliebige Video-Dateien (nicht nur aus reels.json) in die Airtable-Publish-Queue.
Fuer die 09:00-Morgen-Videos (Deep-Motivation). Nutzt dieselbe Cloudinary->Queue->poster.py-Kette
wie die Abend-Reels. Zeiten in UTC (07:00 UTC = 09:00 lokal im Sommer)."""
import sys, os, hashlib, time, json, requests
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))

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
    r = requests.post(f"https://api.airtable.com/v0/{at['base_id']}/{at['queue_table']}",
        headers={"Authorization": f"Bearer {at['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError(f"Airtable-Fehler: {j}")
    return j["id"]

DM = r"C:\Content\deep-motivation"
ST = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\reels\strand-test"
KB = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\CONTENT-BIBLIOTHEK\01_KOSTENLOS_0-Credits\KI-Business"

JOBS = [
 (101, "Hamsterrad", os.path.join(DM, "hamsterrad", "Hamsterrad_FLOW_Marcus_tief.mp4"), "2026-06-10 07:00",
  "230 Tage im Jahr. Aufstehen, funktionieren, schlafen - und wieder von vorn.\n\nDu kannst das Rad nicht anhalten. Aber du kannst entscheiden, ob du drin bleibst.\n\nSpeichere das, wenn du dich gerade wiedererkennst.\n\n#hamsterrad #mindset #aufwachen #erfolgsgeheimnisse #motivationdeutsch #disziplin #selbstreflexion #mentalestaerke"),
]

cfg = load_cfg()
ok, failed = 0, 0
for rid, title, path, when, caption in JOBS:
    if not os.path.exists(path):
        print(f"  #{rid} FEHLER: Datei fehlt: {path}"); failed += 1; continue
    print(f"  #{rid} ({title}) -> Cloudinary...", end=" ", flush=True)
    try:
        url = cloudinary_upload(path, cfg["cloudinary"])
        fields = {"reel_id": rid, "title": title, "video_url": url, "platforms": "instagram",
                  "caption_ig": caption, "caption_tiktok": caption, "yt_title": title + " #Shorts",
                  "yt_description": caption, "scheduled_time": when, "ai_label": True, "status": "scheduled"}
        rec = airtable_create(cfg["airtable"], fields)
        print(f"ok -> Queue ({when} UTC) [{rec[:8]}]"); ok += 1
    except Exception as e:
        print(f"FEHLER: {e}"); failed += 1
print(f"\nFertig: {ok} Morgen-Videos gestagt, {failed} Fehler.")
