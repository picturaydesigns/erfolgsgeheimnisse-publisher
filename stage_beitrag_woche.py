# -*- coding: utf-8 -*-
"""Neuer EG-Tagesrhythmus (Alexanders Beschluss 07.07.2026):
09:00 DE Video · 18:00 DE Beitrag/Karussell (NUR instagram,tiktok — YouTube kann keine
Karussells) · 19:00 DE Video.  Zeiten in der Queue sind UTC (Sommerzeit: DE = UTC+2).

Teil 1: verschiebt die 7 geplanten Videos auf die Slots 07:00/17:00 UTC (2 pro Tag).
Teil 2: staget 7 frische Karussells (beste Slideshow-Formate laut LERNEN.md:
        Gute-Nachrichten-Listen 201-204 + List-Tease/Motiv 2,3,4) auf 16:00 UTC.
Dubletten geprueft: keiner dieser Inhalte war bisher in der Publish-Queue.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

import requests

# --- Startschutz (20.07.2026): Alt-Skript mit fest verdrahteten IDs/Terminen. ---
# Lief beim blossen Aufruf sofort los. Aktueller Weg: stage_carousel.py / stage_reel.py.
if "--wirklich-ausfuehren" not in sys.argv:
    raise SystemExit(
        "ALT-SKRIPT gestoppt: feste IDs/Termine + altes Feldschema. "
        "Aktuell nutzen: stage_carousel.py --carousel <id> --when <UTC> "
        "bzw. stage_reel.py. Erzwingen mit --wirklich-ausfuehren."
    )


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CAR = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\carousels"
CJ = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\carousels.json"

cfg = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
CC = cfg["cloudinary"]
AT = cfg["airtable"]
API = "https://api.airtable.com/v0/%s/%s" % (AT["base_id"], AT["queue_table"])
KOPF = {"Authorization": "Bearer " + AT["token"], "Content-Type": "application/json"}

# ---------- Teil 1: Videos auf 07:00 / 17:00 UTC umlegen ----------
VIDEO_SLOTS = [  # (Titel-Anfang, neue Zeit UTC)
    ("RUHE IST KONTROLLE",        "2026-07-07 07:00"),
    ("ES GAB EIN LETZTES MAL",    "2026-07-07 17:00"),
    ("DU WUSSTEST ES NICHT",      "2026-07-08 07:00"),
    ("DU BIST NICHT ZU SPÄT",     "2026-07-08 17:00"),
    ("MELDE DICH ZUERST",         "2026-07-09 07:00"),
    ("SCHÜTZE DEINE ENERGIE",     "2026-07-09 17:00"),
    ("FEIER DIE KLEINEN SIEGE",   "2026-07-10 07:00"),
]

# ---------- Teil 2: Karussells fuer den 18:00-DE-Slot (16:00 UTC) ----------
BEITRAEGE = [  # (carousel-id, Datum) — Mix: Gute-News-Listen (Top-Format) + List/Motiv
    (201, "2026-07-07"),  # 4 Tierarten Comeback (bestes Format: Gute-News-Liste)
    (4,   "2026-07-08"),  # 5 Sätze vom Grübeln ins Tun (List-Tease)
    (202, "2026-07-09"),  # Klima: mehr Gutes als du denkst
    (3,   "2026-07-10"),  # 3 Fragen für Klarheit (List-Tease)
    (203, "2026-07-11"),  # Medizin: Geschichte geschrieben
    (2,   "2026-07-12"),  # Innerer Dialog (Motiv)
    (204, "2026-07-13"),  # Meere: so viel Schutz wie nie
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


def slides_of(cid):
    """Finale Slides, OHNE die _bg-Rohbilder, numerisch sortiert."""
    alle = glob.glob(os.path.join(CAR, str(cid), "slide_*.png"))
    final = [p for p in alle if not p.endswith("_bg.png")]
    return sorted(final)


print("TEIL 1 — Videos umlegen (09:00/19:00 DE):")
recs = requests.get(API + "?pageSize=100", headers=KOPF, timeout=60).json().get("records", [])
recs += requests.get(API + "?pageSize=100&offset=", headers=KOPF, timeout=60).json().get("records", []) if False else []
geplant = [r for r in recs if r["fields"].get("status") == "scheduled"
           and r["fields"].get("media_type") != "carousel"]
patches = []
for titel_anfang, neu in VIDEO_SLOTS:
    passend = [r for r in geplant if str(r["fields"].get("title", "")).startswith(titel_anfang)]
    if not passend:
        print("  ⚠ nicht gefunden:", titel_anfang)
        continue
    patches.append({"id": passend[0]["id"], "fields": {"scheduled_time": neu}})
    print("  %s -> %s UTC" % (titel_anfang, neu))
for i in range(0, len(patches), 10):
    r = requests.patch(API, headers=KOPF, json={"records": patches[i:i + 10]}, timeout=60).json()
    if "records" not in r:
        raise RuntimeError("Airtable-PATCH: %s" % r)
print("  ✅ %d Videos umgelegt" % len(patches))

print("TEIL 2 — Karussells stagen (18:00 DE, instagram+tiktok):")
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
    files = slides_of(cid)
    if len(files) < 2:
        print("  ⚠ #%s: zu wenige Slides (%d) — übersprungen" % (cid, len(files)))
        continue
    print("  #%s %s: %d Slides -> Cloudinary..." % (cid, c.get("titel", ""), len(files)),
          end=" ", flush=True)
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
print("  ✅ %d Karussells eingeplant, Register aktualisiert" % ok)
print("FERTIG. Rhythmus: 07:00 Video · 16:00 Beitrag (IG+TikTok) · 17:00 Video (alles UTC).")
