# -*- coding: utf-8 -*-
"""Stellt die 7 neuen ruhigen IG-Reels (Hamsterrad-Flow, Stimme Victor) in die Publish-Queue.
Slot 09:00 lokal = 07:00 UTC, 15.-21.06.2026 (fuellt den Morgen-Slot, der nach dem 14.06. leer laeuft).
Nur Instagram (TikTok-Karusselle werden manuell hochgeladen). KI-Kennzeichnung in jeder Caption + ai_label."""
import sys, os, hashlib, time, json, requests
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\output\reels\strand-test"

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

KI = "\n\n(KI-generierte Stimme & Bilder)"
JOBS = [
 (110, "Du bist nicht hinten (Vergleich)", "reel_ig01_vergleich.mp4", "2026-06-15 07:00",
  "Der Blick zur Seite kostet dich den Weg nach vorn. Heute mal nur die eigene Bahn. Was ist dein nächster Schritt? 🔖\n\n#erfolgsgeheimnisse #motivation #mindset #erfolg #persönlichkeitsentwicklung" + KI),
 (111, "Stille Stärke", "reel_ig02_stille-staerke.mp4", "2026-06-16 07:00",
  "Das Lauteste im Raum ist selten das Stärkste. Still dranbleiben zählt mehr als laut ankündigen. 🔖\n\n#erfolgsgeheimnisse #erfolgsmindset #motivationdeutsch #mentalstark #selbstdisziplin" + KI),
 (112, "Geduld (Wurzeln)", "reel_ig03_geduld.mp4", "2026-06-17 07:00",
  "Nicht jede leise Phase ist Stillstand. Manchmal baust du gerade das Fundament. Dranbleiben. 🔖\n\n#erfolgsgeheimnisse #wachstum #selbstentwicklung #ziele #coaching" + KI),
 (113, "Loslassen", "reel_ig04_loslassen.mp4", "2026-06-18 07:00",
  "Festhalten fühlt sich nach Kontrolle an — ist aber oft nur Angst. Heute eine Faust öffnen. 🔖\n\n#erfolgsgeheimnisse #durchhalten #fokus #dranbleiben #zitate" + KI),
 (114, "Selbstwert (geblieben)", "reel_ig05_selbstwert.mp4", "2026-06-19 07:00",
  "Du redest mit niemandem so hart wie mit dir selbst. Heute ein Satz milder. 🔖\n\n#erfolgsgeheimnisse #motivation #mindset #erfolg #persönlichkeitsentwicklung" + KI),
 (115, "Unsichtbare Arbeit", "reel_ig06_unsichtbar.mp4", "2026-06-20 07:00",
  "Das Ergebnis ist nur die Spitze. Verliebe dich in den unsichtbaren Teil. 🔖\n\n#erfolgsgeheimnisse #erfolgsmindset #motivationdeutsch #mentalstark #selbstdisziplin" + KI),
 (116, "Leiser Mut (Neuanfang)", "reel_ig07_mut.mp4", "2026-06-21 07:00",
  "Der Anfang braucht kein Publikum. Nur dich und ein Ja. 🔖\n\n#erfolgsgeheimnisse #wachstum #selbstentwicklung #ziele #coaching" + KI),
]

cfg = load_cfg()
ok, failed = 0, 0
for rid, title, fn, when, caption in JOBS:
    path = os.path.join(ST, fn)
    if not os.path.exists(path):
        print(f"  #{rid} FEHLER: Datei fehlt: {path}"); failed += 1; continue
    print(f"  #{rid} ({title}) -> Cloudinary...", end=" ", flush=True)
    try:
        url = cloudinary_upload(path, cfg["cloudinary"])
        fields = {"reel_id": rid, "title": title, "video_url": url, "platforms": "instagram",
                  "caption_ig": caption, "media_type": "reel",
                  "scheduled_time": when, "ai_label": True, "status": "scheduled"}
        rec = airtable_create(cfg["airtable"], fields)
        print(f"ok -> Queue ({when} UTC = 09:00) [{rec[:8]}]"); ok += 1
    except Exception as e:
        print(f"FEHLER: {e}"); failed += 1
print(f"\nFertig: {ok} IG-Reels gestagt, {failed} Fehler.")
