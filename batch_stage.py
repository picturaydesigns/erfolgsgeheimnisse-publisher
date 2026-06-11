# -*- coding: utf-8 -*-
"""Stellt alle geplanten Reels (#7-#28) auf einmal in die Airtable-Queue.
Jedes Reel wird zu Cloudinary hochgeladen und mit Postzeit eingetragen.
Aufruf:  python batch_stage.py
"""
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
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/video/upload",
            data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300)
    j = r.json()
    if "secure_url" not in j:
        raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen: {j}")
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

# Zeitplan: #7 heute (08.06.), dann taeglich 19:00, bis Reel #28 am 29.06.
SCHEDULE = {
     7: "2026-06-08 19:00",
     8: "2026-06-09 19:00",
     9: "2026-06-10 19:00",
    10: "2026-06-11 19:00",
    11: "2026-06-12 19:00",
    12: "2026-06-13 19:00",
    13: "2026-06-14 19:00",
    14: "2026-06-15 19:00",
    15: "2026-06-16 19:00",
    16: "2026-06-17 19:00",
    17: "2026-06-18 19:00",
    18: "2026-06-19 19:00",
    19: "2026-06-20 19:00",
    20: "2026-06-21 19:00",
    21: "2026-06-22 19:00",
    22: "2026-06-23 19:00",
    23: "2026-06-24 19:00",
    24: "2026-06-25 19:00",
    25: "2026-06-26 19:00",
    26: "2026-06-27 19:00",
    27: "2026-06-28 19:00",
    28: "2026-06-29 19:00",
}

cfg = load_cfg()
with open(cfg["reels_json"], encoding="utf-8") as f:
    all_reels = {r["id"]: r for r in json.load(f)["reels"]}

ok, failed = 0, 0
for rid, when in SCHEDULE.items():
    reel = all_reels.get(rid)
    if not reel:
        print(f"  #{rid}: nicht in reels.json gefunden, uebersprungen.")
        continue

    video_path = reel["file"]
    if not os.path.isabs(video_path):
        video_path = os.path.join(cfg["content_root"], video_path)

    if not os.path.exists(video_path):
        print(f"  #{rid} FEHLER: Datei nicht gefunden: {video_path}")
        failed += 1
        continue

    print(f"  #{rid} ({reel['title']}) -> Cloudinary...", end=" ", flush=True)
    try:
        url = cloudinary_upload(video_path, cfg["cloudinary"])
        print(f"ok -> Airtable...", end=" ", flush=True)
        fields = {
            "reel_id": rid,
            "title": reel["title"],
            "video_url": url,
            "platforms": "instagram",
            "caption_ig": reel["caption"],
            "caption_tiktok": reel["caption"],
            "yt_title": reel["title"] + " #Shorts",
            "yt_description": reel["caption"],
            "scheduled_time": when,
            "ai_label": bool(reel.get("ki_required")),
            "status": "scheduled",
        }
        rec = airtable_create(cfg["airtable"], fields)
        print(f"ok ({when}) [{rec[:8]}...]")
        ok += 1
    except Exception as e:
        print(f"FEHLER: {e}")
        failed += 1

print(f"\nFertig: {ok} gestagt, {failed} Fehler.")
