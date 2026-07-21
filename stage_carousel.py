# -*- coding: utf-8 -*-
"""LOKAL ausfuehren. Plant ein fertiges Karussell fuer die Cloud ein:
  1) laedt die Slides (slide_*.png, OHNE *_bg.png und OHNE cover.*) zu Cloudinary hoch,
  2) haengt eine Zeile an die Datei-Queue (queue.json) an -> git push.
Der Cloud-Runner (poster.py via GitHub Actions) postet es zur Postzeit auf IG + TikTok.

Aufruf:
  python stage_carousel.py --carousel 209 --when "2026-07-21 16:00"
  python stage_carousel.py --carousel 209                    # ohne --when = sofort faellig

Zeit IMMER in UTC! (dt. Sommerzeit = UTC+2 -> 18:00 dt. = 16:00 UTC)
Konfig: publisher_config.json (Cloudinary). Register: erfolgsgeheimnisse/content/carousels.json
Ordner-Konvention: <content_root>/content/output/carousels/<id>/
"""
import argparse
import hashlib
import json
import os
import time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CAROUSELS = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse\content\carousels.json"


def load_cfg():
    with open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def cloudinary_upload(path, cc, tries=4):
    last = None
    for attempt in range(1, tries + 1):
        ts = str(int(time.time()))
        sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
        try:
            with open(path, "rb") as fh:
                r = requests.post(
                    f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/image/upload",
                    data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
                    files={"file": fh}, timeout=300)
            j = r.json()
            if "secure_url" in j:
                return j["secure_url"]
            last = f"Antwort ohne secure_url: {j}"
        except Exception as e:
            last = str(e)
        if attempt < tries:
            print(f"   (Versuch {attempt} fehlgeschlagen, neuer Versuch...)")
            time.sleep(3 * attempt)
    raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen nach {tries} Versuchen: {last}")


def airtable_create(at, fields):
    """Seit 20.07.2026: Datei-Queue statt Airtable (Name bleibt, damit alle Aufrufe halten)."""
    import filequeue
    return filequeue.queue_append(fields)


def find_slides(folder):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))
                   and not f.lower().endswith("_bg.png")      # Roh-Hintergruende (fal/Higgsfield)
                   and not f.lower().startswith("cover."))    # und das Roh-Cover nie mit hochladen
    return [os.path.join(folder, f) for f in files]


def resolve(cfg, n):
    register = cfg.get("carousels_json") or DEFAULT_CAROUSELS
    with open(register, encoding="utf-8-sig") as f:
        data = json.load(f)
    liste = data["carousels"] if isinstance(data, dict) else data
    entry = next(c for c in liste if c.get("id", c.get("karussell_nummer")) == n)
    ordner = entry.get("ordner") or os.path.join("content", "output", "carousels", str(n))
    folder = os.path.join(cfg["content_root"], ordner.replace("/", os.sep))
    caption = entry.get("caption", "")
    if entry.get("hashtags"):
        caption = (caption + "\n\n" + entry["hashtags"]).strip()
    return folder, caption, entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carousel", type=int, required=True)
    ap.add_argument("--when", default="", help='Postzeit UTC "YYYY-MM-DD HH:MM" (leer = sofort)')
    args = ap.parse_args()

    cfg = load_cfg()
    folder, caption, entry = resolve(cfg, args.carousel)
    slides = find_slides(folder)
    if not (2 <= len(slides) <= 10):
        raise SystemExit(f"Karussell braucht 2-10 Bilder, gefunden: {len(slides)} in {folder}")

    titel = entry.get("titel", "")
    print(f"Karussell {args.carousel}: {titel}  ({len(slides)} Slides)\nOrdner: {folder}")
    print("Lade zu Cloudinary hoch...")
    urls = []
    for s in slides:
        urls.append(cloudinary_upload(s, cfg["cloudinary"]))
        print("   ", os.path.basename(s))

    fields = {
        "name": f"K{args.carousel} - {titel}",
        "typ": "carousel",
        "image_urls": "\n".join(urls),
        "caption": caption,
        # IG + TikTok; YouTube nimmt keine Foto-Karussells
        "platforms": "instagram,tiktok",
        "scheduled_time": args.when,
        "status": "scheduled",
        "ki_label": True,
    }
    rec = airtable_create(cfg.get("airtable"), fields)
    print(f"\nIn Cloud-Queue gestellt ({rec}). Zeit: {args.when or 'sofort faellig'} (UTC)")


if __name__ == "__main__":
    main()
