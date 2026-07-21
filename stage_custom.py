# -*- coding: utf-8 -*-
"""Stellt beliebige Video-Dateien (nicht nur aus reels.json) in die Airtable-Publish-Queue.
Fuer die 09:00-Morgen-Videos (Deep-Motivation). Nutzt dieselbe Cloudinary->Queue->poster.py-Kette
wie die Abend-Reels. Zeiten in UTC (07:00 UTC = 09:00 lokal im Sommer)."""
import sys, os, hashlib, time, json, requests

# --- Startschutz (20.07.2026): Alt-Skript mit fest verdrahteten IDs/Terminen. ---
# Lief beim blossen Aufruf sofort los. Aktueller Weg: stage_carousel.py / stage_reel.py.
if "--wirklich-ausfuehren" not in sys.argv:
    raise SystemExit(
        "ALT-SKRIPT gestoppt: feste IDs/Termine + altes Feldschema. "
        "Aktuell nutzen: stage_carousel.py --carousel <id> --when <UTC> "
        "bzw. stage_reel.py. Erzwingen mit --wirklich-ausfuehren."
    )

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
    """Seit 20.07.2026: Datei-Queue statt Airtable (Name bleibt, damit alle Aufrufe halten)."""
    import filequeue
    return filequeue.queue_append(fields)
