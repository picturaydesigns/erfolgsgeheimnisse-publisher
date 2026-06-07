# erfolgsgeheimnisse-publisher

Voll-automatische Cross-Platform-Veröffentlichung für @erfolgsgeheimnisse:
**Instagram + TikTok + YouTube Shorts**, ausgelöst per **Cloud-Zeitplan** (PC darf aus sein),
**DIY pro Plattform** (eigene APIs, kein bezahlter Dienst).

## So funktioniert's
```
Lokal:  build_reel.py -> fertiges 9:16-Reel
   |
   v   python stage.py --reel <id> --platforms ... --when "..."
Cloudinary (Video-Host)  +  Airtable "Publish-Queue"
   |
   v   GitHub Actions (Cron alle 30 Min)  ->  poster.py
   |        liest faellige Eintraege, postet je Plattform
   v
platforms/ig.py · youtube.py · tiktok.py  -> status/Permalink zurueck nach Airtable
```

## Dateien
- `stage.py` — LOKAL: Reel zu Cloudinary + in die Airtable-Queue stellen.
- `poster.py` — CLOUD (GitHub Actions): faellige Eintraege posten.
- `platforms/ig.py` — Instagram (erprobt). `youtube.py` / `tiktok.py` — Geruest (Phase 2/3).
- `.github/workflows/publish.yml` — Cron-Runner.
- `publisher_config.example.json` — Vorlage fuer die lokale Konfig.

## Start
Siehe **SETUP.md** — Konten in Reihenfolge anlegen (Phase 0 zuerst: Cloudinary).

## Status
- Phase 0 (IG-Reel-Upload via Cloudinary): wartet auf Cloudinary-Zugang.
- Phase 1 (Cloud-Runner + Queue): Code-Geruest steht, wartet auf GitHub + Airtable-Tabelle.
- Phase 2/3 (YouTube/TikTok): Geruest + dokumentierter Ablauf, wird pro Phase gebaut+getestet.
