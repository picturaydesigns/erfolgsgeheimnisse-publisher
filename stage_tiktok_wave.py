# -*- coding: utf-8 -*-
"""LOKAL ausfuehren. Stellt die fertige TikTok-Welle (Desktop\\TIKTOK-SCHEDULE\\01..12) in die
Cloud-Queue: Medien zu Cloudinary (Karussell-Slides als Bilder, Videos als Video), je Stueck
eine Airtable-Zeile. Der Cloud-Runner postet dann automatisch.

Plattform-Regel (seit Auftrag 27, YouTube-Regelbetrieb):
  Videos    -> platforms="instagram,tiktok,youtube" + yt_title/yt_description (Hook-basiert)
  Karussells-> platforms="tiktok" (YouTube nimmt keine Foto-Karussells)
Optional pro Video-Ordner: YT-TITEL.txt / YT-BESCHREIBUNG.txt ueberschreiben die Automatik.

Aufruf:
  python stage_tiktok_wave.py                          -> zeigt nur den Plan (Trockenlauf)
  python stage_tiktok_wave.py --go                     -> fuehrt aus (alle offenen Stuecke)
  python stage_tiktok_wave.py --go --items 1,3,5       -> nur bestimmte Stuecke
  python stage_tiktok_wave.py --go --start 2026-06-12  -> erster Posttag (Standard: morgen)

Postzeit: taeglich 17:00 UTC = 19:00 deutscher Sommerzeit. Bereits gestagte Stuecke werden
ueber staged_tiktok_wave.json uebersprungen (Script ist mehrfach ausfuehrbar).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time

import requests

from yt_meta import build_yt_meta

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_DIR = r"C:\Users\Alexa\OneDrive\Desktop\TIKTOK-SCHEDULE"
LOG_PATH = os.path.join(HERE, "staged_tiktok_wave.json")
POST_HOUR_UTC = "17:00"  # 19:00 lokal (CEST = UTC+2)


def load_cfg():
    with open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8") as f:
        return json.load(f)


def cloudinary_upload(path, cc, kind):
    """kind: 'video' oder 'image' - gleiche Signatur-Logik wie stage.py."""
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/{kind}/upload",
            data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300)
    j = r.json()
    if "secure_url" not in j:
        raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen ({path}): {j}")
    return j["secure_url"]


def airtable_create(at, fields):
    r = requests.post(
        f"https://api.airtable.com/v0/{at['base_id']}/{at['queue_table']}",
        headers={"Authorization": f"Bearer {at['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError(f"Airtable-Fehler: {j}")
    return j["id"]


def read_items():
    """Ordner 01_.. 12_.. einlesen -> (nr, typ, label, medienpfade, caption)."""
    items = []
    for name in sorted(os.listdir(SCHEDULE_DIR)):
        m = re.match(r"^(\d{2})_(Karussell|Video)_(.+)$", name)
        if not m:
            continue
        nr, typ, label = int(m.group(1)), m.group(2), m.group(3)
        folder = os.path.join(SCHEDULE_DIR, name)
        with open(os.path.join(folder, "CAPTION.txt"), encoding="utf-8") as f:
            caption = f.read().strip()
        if typ == "Karussell":
            media = sorted(os.path.join(folder, f) for f in os.listdir(folder)
                           if f.startswith("slide_") and f.endswith(".png"))
        else:
            media = [os.path.join(folder, "Video.mp4")]

        def _opt(fname):
            p = os.path.join(folder, fname)
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    return fh.read().strip()
            return ""

        items.append({"nr": nr, "typ": typ, "label": label, "media": media, "caption": caption,
                      "yt_title": _opt("YT-TITEL.txt"), "yt_description": _opt("YT-BESCHREIBUNG.txt")})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="wirklich ausfuehren (sonst Trockenlauf)")
    ap.add_argument("--items", default="", help="nur diese Nummern, z.B. 1,3,5")
    ap.add_argument("--start", default="", help="erster Posttag YYYY-MM-DD (Standard: morgen)")
    ap.add_argument("--hour", default=POST_HOUR_UTC, help='Postzeit UTC "HH:MM" (Standard 17:00 = 19:00 lokal)')
    ap.add_argument("--now", action="store_true", help="sofort faellig statt Zeitplan (Testpost)")
    args = ap.parse_args()

    staged = {}
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as f:
            staged = json.load(f)

    only = {int(x) for x in args.items.split(",") if x.strip()} if args.items.strip() else None
    start = (dt.date.fromisoformat(args.start) if args.start
             else dt.date.today() + dt.timedelta(days=1))

    items = [it for it in read_items()
             if (only is None or it["nr"] in only) and str(it["nr"]) not in staged]
    if not items:
        print("Nichts zu tun (alles schon gestagt oder Filter leer).")
        return

    cfg = load_cfg()
    day = start
    print(f"{'AUSFUEHREN' if args.go else 'TROCKENLAUF'} - {len(items)} Stuecke ab {start}:")
    for it in items:
        when = "" if args.now else f"{day.isoformat()} {args.hour}"
        h, m = (int(x) for x in args.hour.split(":"))
        local = "SOFORT" if args.now else f"{day.strftime('%d.%m.')} {h + 2:02d}:{m:02d} lokal"
        print(f"  {it['nr']:02d} {it['typ']:9s} {it['label']:24s} -> {local} ({len(it['media'])} Datei(en))")
        if args.go:
            kind = "image" if it["typ"] == "Karussell" else "video"
            urls = [cloudinary_upload(p, cfg["cloudinary"], kind) for p in it["media"]]
            fields = {
                "reel_id": 200 + it["nr"],
                "title": f"TikTok-Welle {it['nr']:02d} {it['label']}",
                "caption_tiktok": it["caption"],
                "scheduled_time": when,
                "ai_label": True,
                "status": "scheduled",
            }
            if it["typ"] == "Karussell":
                fields["platforms"] = "tiktok"
                fields["media_type"] = "carousel"
                fields["image_urls"] = ",".join(urls)
            else:
                yt_t, yt_d = build_yt_meta(it["label"], it["caption"],
                                           it["yt_title"], it["yt_description"])
                fields["platforms"] = "instagram,tiktok,youtube"
                fields["media_type"] = "reel"
                fields["video_url"] = urls[0]
                fields["caption_ig"] = it["caption"]
                fields["yt_title"] = yt_t
                fields["yt_description"] = yt_d
            rec = airtable_create(cfg["airtable"], fields)
            staged[str(it["nr"])] = {"airtable": rec, "when": when}
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(staged, f, indent=1, ensure_ascii=False)
            print(f"       -> in Queue ({rec})")
        day += dt.timedelta(days=1)

    if not args.go:
        print("\nTrockenlauf - nichts hochgeladen. Mit --go ausfuehren.")


if __name__ == "__main__":
    main()
