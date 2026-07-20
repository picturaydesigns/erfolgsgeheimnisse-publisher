# -*- coding: utf-8 -*-
"""Staget die 4 neuen EG-Beitrags-Karusselle (205-208, fal.ai-Bilder) in den
18:00-DE-Slot (16:00 UTC) vom 14.-17.07. — platforms instagram,tiktok (kein YouTube).
Muster wie stage_beitrag_woche.py Teil 2."""
import glob
import hashlib
import json
import os
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CAR = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\carousels"
CJ = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\carousels.json"

cfg = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
CC = cfg["cloudinary"]
AT = cfg["airtable"]
API = "https://api.airtable.com/v0/%s/%s" % (AT["base_id"], AT["queue_table"])
KOPF = {"Authorization": "Bearer " + AT["token"], "Content-Type": "application/json"}

BEITRAEGE = [
    (205, "2026-07-14"),  # 4 Comebacks vor unserer Haustür (Gute-News-Liste)
    (206, "2026-07-15"),  # 5 Dinge, die still besser werden
    (207, "2026-07-16"),  # 5 Zeichen, dass du wächst
    (208, "2026-07-17"),  # 4 Gewohnheiten, die deinen Kopf leise machen
]


def cl_image(path):
    ts = str(int(time.time()))
    sig = hashlib.sha1(("timestamp=%s%s" % (ts, CC["api_secret"])).encode()).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post("https://api.cloudinary.com/v1_1/%s/image/upload" % CC["cloud_name"],
                          data={"api_key": CC["api_key"], "timestamp": ts, "signature": sig},
                          files={"file": fh}, timeout=300).json()
    if "secure_url" not in r:
        raise RuntimeError("Cloudinary: %s" % r)
    return r["secure_url"]


data = json.load(open(CJ, encoding="utf-8-sig"))
by_id = {c["id"]: c for c in data["carousels"]}
ok = 0
for cid, tag in BEITRAEGE:
    c = by_id[cid]
    hook = re.sub(r"\s+", " ", c["slides"][0]["text"]).strip()
    if len(hook) > 90:
        hook = hook[:87] + "..."
    cap_ig = "%s\n\n%s" % (c["caption"], c["hashtags"])
    cap_tt = "%s\n\n%s\n\n%s" % (hook, c["caption"], c["hashtags"])
    files = sorted(f for f in glob.glob(os.path.join(CAR, str(cid), "slide_*.png"))
                   if not f.endswith("_bg.png"))
    if len(files) < 2:
        print("⚠ #%s: zu wenige finale Slides (%d) — erst rendern!" % (cid, len(files)))
        continue
    print("#%s %s: %d Slides -> Cloudinary..." % (cid, c.get("titel", ""), len(files)), end=" ", flush=True)
    urls = [cl_image(f) for f in files]
    r = requests.post(API, headers=KOPF, json={"fields": {
        "reel_id": cid,
        "title": "Beitrag %s %s" % (cid, c.get("titel", "")[:60]),
        "media_type": "carousel",
        "image_urls": ",".join(urls),
        "caption_ig": cap_ig,
        "caption_tiktok": cap_tt,
        "platforms": "instagram,tiktok",
        "scheduled_time": "%s 16:00" % tag,
        "ai_label": True,
        "status": "scheduled",
    }}, timeout=60).json()
    if "id" not in r:
        raise RuntimeError("Airtable: %s" % r)
    c["status"] = "scheduled"
    print("ok -> %s 16:00 UTC" % tag)
    ok += 1

json.dump(data, open(CJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("FERTIG: %d Beitraege eingeplant, Register aktualisiert." % ok)
