# -*- coding: utf-8 -*-
"""Laedt die 7 Reel-Cover zu Cloudinary + TESTET, ob graph.instagram.com cover_url akzeptiert
(erstellt nur einen Container, postet NICHTS). Gibt die {reel_id: cover_url}-Map aus.
Erst nach erfolgreichem Test werden die Queue-Zeilen aktualisiert (separater Schritt)."""
import sys, os, hashlib, time, json, requests
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\reels\strand-test\covers"

pub = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8"))
ig = json.load(open(os.path.join(HERE, "..", "erfolgsgeheimnisse", "instagram_config.json"), encoding="utf-8-sig"))
CC = pub["cloudinary"]; AT = pub["airtable"]
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

# reel_id -> cover-Datei (entspricht stage_ig_reels.py 110..116)
MAP = {
 110: "cover_ig01_vergleich.png", 111: "cover_ig02_stille-staerke.png",
 112: "cover_ig03_geduld.png", 113: "cover_ig04_loslassen.png",
 114: "cover_ig05_selbstwert.png", 115: "cover_ig06_unsichtbar.png",
 116: "cover_ig07_mut.png",
}
covers = {}
for rid, fn in MAP.items():
    p = os.path.join(COVERS, fn)
    covers[rid] = cl_image(p)
    print(f"  #{rid}: {covers[rid]}")
json.dump(covers, open(os.path.join(HERE, "_reel_covers.json"), "w"), indent=2)
print("\nMapping gespeichert in _reel_covers.json")

# --- TEST: akzeptiert IG cover_url? (Container anlegen, NICHT publishen) ---
row = requests.get(f"https://api.airtable.com/v0/{AT['base_id']}/{AT['queue_table']}",
    headers={"Authorization": f"Bearer {AT['token']}"},
    params={"filterByFormula": "{reel_id}=110", "maxRecords": 1}, timeout=60).json()
vid = row["records"][0]["fields"].get("video_url") if row.get("records") else None
print(f"\nTEST cover_url mit Reel #110 (video_url vorhanden: {bool(vid)})")
if vid:
    t = requests.post(f"{API}/{USER}/media", data={
        "media_type": "REELS", "video_url": vid, "caption": "TEST (wird nicht gepostet)",
        "cover_url": covers[110], "access_token": TOKEN}, timeout=60).json()
    if "id" in t:
        print(f"  ✓ cover_url AKZEPTIERT (Container {t['id']} angelegt, NICHT gepostet).")
        print("  -> Queue-Zeilen koennen mit cover_url aktualisiert werden.")
    else:
        print(f"  ✗ cover_url NICHT akzeptiert: {t}")
