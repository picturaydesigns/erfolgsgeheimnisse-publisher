# -*- coding: utf-8 -*-
"""Stellt die 7 KI-Business-Karussells (408-414) als TikTok-ONLY-Posts in die Queue.
Der 4. Tagespost (Beschluss Alexander 12.06.2026): Muster Video, Karussell, Karussell, Video
-> dieses Karussell laeuft mittags 13:00 lokal (11:00 UTC), zwischen 9:00-Karussell und Abend-Video.
408 startet noch HEUTE 15:00 lokal (13:00 UTC). Quelle der Texte: content/carousels.json.
WICHTIG: erste Caption-Zeile = TikTok-Foto-Titel (<=90 Zeichen, einzeilig)."""
import sys, os, glob, hashlib, time, json, requests

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
CAR = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\carousels"
CJ = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\carousels.json"

cfg = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
CC = cfg["cloudinary"]; AT = cfg["airtable"]

WHEN = {  # UTC
    408: "2026-06-12 13:00",
    409: "2026-06-13 11:00",
    410: "2026-06-14 11:00",
    411: "2026-06-15 11:00",
    412: "2026-06-16 11:00",
    413: "2026-06-17 11:00",
    414: "2026-06-18 11:00",
}


def cl_image(path):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{CC['api_secret']}".encode()).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(f"https://api.cloudinary.com/v1_1/{CC['cloud_name']}/image/upload",
            data={"api_key": CC["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300).json()
    if "secure_url" not in r:
        raise RuntimeError(f"Cloudinary: {r}")
    return r["secure_url"]


def at_create(fields):
    r = requests.post(f"https://api.airtable.com/v0/{AT['base_id']}/{AT['queue_table']}",
        headers={"Authorization": f"Bearer {AT['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60).json()
    if "id" not in r:
        raise RuntimeError(f"Airtable: {r}")
    return r["id"]


data = json.load(open(CJ, encoding="utf-8-sig"))
by_id = {c["id"]: c for c in data["carousels"]}

ok, failed = 0, 0
for cid, when in WHEN.items():
    c = by_id[cid]
    hook = c["slides"][0]["text"].replace("\n", " ").strip()
    assert len(hook) <= 90, f"#{cid}: Hook zu lang ({len(hook)})"
    caption = f"{hook}\n\n{c['caption']}\n\n{c['hashtags']}"
    files = sorted(glob.glob(os.path.join(CAR, str(cid), "slide_*.png")))
    if len(files) < 2:
        print(f"  #{cid}: zu wenige Slides ({len(files)})"); failed += 1; continue
    print(f"  #{cid} {c['titel']}: {len(files)} Slides -> Cloudinary...", end=" ", flush=True)
    try:
        urls = [cl_image(f) for f in files]
        rec = at_create({
            "reel_id": cid,
            "title": f"KI-Karussell {cid} {c['titel']}",
            "media_type": "carousel",
            "image_urls": ",".join(urls),
            "caption_tiktok": caption,
            "platforms": "tiktok",
            "scheduled_time": when,
            "ai_label": True,
            "status": "scheduled",
        })
        print(f"ok -> Queue ({when} UTC) [{rec[:8]}]"); ok += 1
    except Exception as e:
        print(f"FEHLER: {e}"); failed += 1

print(f"\nFertig: {ok} Karussells gestagt, {failed} Fehler.")
