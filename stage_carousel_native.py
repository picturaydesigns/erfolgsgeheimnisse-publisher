# -*- coding: utf-8 -*-
"""Plant ein Tiefsinn-Karussell server-seitig bei Instagram (scheduled_publish_time).
Wenn Instagram das akzeptiert, postet IG es selbst zur Zeit -> PC darf aus sein, kein Cron noetig.
Bilder werden zu Cloudinary hochgeladen (zuverlaessig). Zeiten in UTC.
"""
import sys, os, glob, hashlib, time, json, calendar, datetime as dt
import requests
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))

pub = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
ig = json.load(open(os.path.join(HERE, "..", "erfolgsgeheimnisse", "instagram_config.json"), encoding="utf-8-sig"))
CC = pub["cloudinary"]
TOKEN = ig["access_token"]; USER = ig["instagram_user_id"]
API = "https://graph.instagram.com/v22.0"

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
    files = ([cover] if os.path.exists(cover) else []) + rest
    return files

def to_unix_utc(s):  # "2026-06-10 10:00" als UTC interpretiert
    return calendar.timegm(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").timetuple())

def stage(folder, when_utc):
    name = os.path.basename(folder)
    files = slides_of(folder)
    cap_path = os.path.join(folder, "caption.txt")
    caption = open(cap_path, encoding="utf-8").read().strip() if os.path.exists(cap_path) else ""
    print(f"[{name}] {len(files)} Slides, geplant {when_utc} UTC")
    if len(files) < 2:
        print("  zu wenige Slides"); return
    child_ids = []
    for f in files:
        url = cl_image(f)
        r = requests.post(f"{API}/{USER}/media", data={
            "image_url": url, "is_carousel_item": "true", "access_token": TOKEN}, timeout=60).json()
        if "id" not in r:
            print(f"  Child-Fehler ({os.path.basename(f)}): {r}"); return
        child_ids.append(r["id"])
        print(f"  child ok: {os.path.basename(f)}")
    body = {"media_type": "CAROUSEL", "children": ",".join(child_ids),
            "caption": caption, "access_token": TOKEN}
    r = requests.post(f"{API}/{USER}/media", data=body, timeout=60).json()
    print(f"  -> Container (ohne Zeitplan): {r}")

JOBS = [
 (r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\carousels\tiefsinn-bilder-01", "2026-06-10 10:00"),
]
for folder, when in JOBS:
    stage(folder, when)
