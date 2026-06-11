# -*- coding: utf-8 -*-
"""Stellt Tiefsinn-Karussells in die Airtable-Publish-Queue (media_type=carousel).
Laedt die finalen Slides (cover.png + slide_*.png) zu Cloudinary, traegt die Bild-URLs ein.
Der Cloud-Poster (poster.py, neue Carousel-Logik) postet sie zur Zeit. Zeiten in UTC."""
import sys, os, glob, hashlib, time, json, requests
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CAR = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\carousels"

cfg = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
CC = cfg["cloudinary"]; AT = cfg["airtable"]

def cl_image(path):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{CC['api_secret']}".encode()).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(f"https://api.cloudinary.com/v1_1/{CC['cloud_name']}/image/upload",
            data={"api_key": CC["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300).json()
    if "secure_url" not in r: raise RuntimeError(f"Cloudinary: {r}")
    return r["secure_url"]

def slides_of(folder):
    cover = os.path.join(folder, "cover.png")
    rest = sorted(glob.glob(os.path.join(folder, "slide_*.png")))
    return ([cover] if os.path.exists(cover) else []) + rest

def at_create(fields):
    r = requests.post(f"https://api.airtable.com/v0/{AT['base_id']}/{AT['queue_table']}",
        headers={"Authorization": f"Bearer {AT['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60).json()
    if "id" not in r: raise RuntimeError(f"Airtable: {r}")
    return r["id"]

JOBS = [
 (301, "Tiefsinn-Bilder #01 (Disziplin)", "tiefsinn-bilder-01", "2026-06-10 10:00"),
 (302, "Tiefsinn-Bilder #02",             "tiefsinn-bilder-02", "2026-06-11 10:00"),
 (303, "Tiefsinn-Bilder #03",             "tiefsinn-bilder-03", "2026-06-12 10:00"),
 (304, "Tiefsinn-Bilder #04",             "tiefsinn-bilder-04", "2026-06-13 10:00"),
 (305, "Tiefsinn-Bilder #05",             "tiefsinn-bilder-05", "2026-06-14 10:00"),
]

ok, failed = 0, 0
for rid, title, sub, when in JOBS:
    folder = os.path.join(CAR, sub)
    files = slides_of(folder)
    cap_path = os.path.join(folder, "caption.txt")
    caption = open(cap_path, encoding="utf-8").read().strip() if os.path.exists(cap_path) else ""
    if len(files) < 2:
        print(f"  #{rid} ({sub}): zu wenige Slides ({len(files)})"); failed += 1; continue
    print(f"  #{rid} {sub}: {len(files)} Slides -> Cloudinary...", end=" ", flush=True)
    try:
        urls = [cl_image(f) for f in files]
        rec = at_create({
            "reel_id": rid, "title": title, "media_type": "carousel",
            "image_urls": ",".join(urls), "caption_ig": caption, "caption_tiktok": caption,
            "platforms": "instagram", "scheduled_time": when, "ai_label": True, "status": "scheduled",
        })
        print(f"ok -> Queue ({when} UTC) [{rec[:8]}]"); ok += 1
    except Exception as e:
        print(f"FEHLER: {e}"); failed += 1
print(f"\nFertig: {ok} Karussells gestagt, {failed} Fehler.")
