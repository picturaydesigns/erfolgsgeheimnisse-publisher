# SETUP — Konten & Schlüssel (das musst DU anlegen)

Das ist der kritische Pfad: **kein Code läuft, bevor diese Konten existieren.** In dieser
Reihenfolge abarbeiten — jede Phase liefert für sich Ergebnis. Werte gibst du mir, ich trage sie
ein (privat, nie ins Repo).

---

## ✅ Phase 0 — Cloudinary (JETZT — damit Instagram-Reels überhaupt live gehen)
1. **cloudinary.com → „Sign up for free"** (gratis, keine Kreditkarte).
2. Im **Dashboard** stehen: **Cloud name**, **API Key**, **API Secret**.
3. Diese 3 Werte in **`erfolgsgeheimnisse/cloudinary_config.json`** eintragen (Datei ist schon angelegt + offen).
4. → Danach poste ich **Reel #4 live als Test** (`publish_reel.ps1 -id 4`). Damit ist die Video-Kette bewiesen.

## 🔜 Phase 1 — GitHub-Cloud-Runner (die eigentliche Voll-Automatik, PC darf aus)
**Schon erledigt (von Claude):** Airtable-Tabelle `Publish-Queue` angelegt · `publisher_config.json`
befüllt · `stage.py` live getestet (Cloudinary-Upload + Queue-Zeile funktionieren).

**Dein Teil — GitHub (gratis):**
1. **github.com → Konto** anlegen (falls keins).
2. **GitHub Desktop** installieren (desktop.github.com) — einfachster Weg ohne Kommandozeile.
3. In GitHub Desktop: *File → Add local repository* → Ordner `erfolgsgeheimnisse-publisher` wählen →
   *Publish repository* → **Häkchen „Keep this code private"** setzen → Publish.
   (`publisher_config.json` wird durch `.gitignore` NICHT mit hochgeladen — gut so.)
4. Auf github.com im Repo → **Settings → Secrets and variables → Actions → New repository secret**
   und diese **5 Secrets** anlegen:

   | Secret-Name | Wert |
   |---|---|
   | `AIRTABLE_BASE_ID` | `app4UPxhyg94byp4X` |
   | `AIRTABLE_QUEUE_TABLE` | `tblF2Q50qGIcuuO2U` |
   | `AIRTABLE_TOKEN` | (aus `erfolgsgeheimnisse/airtable_config.json` → Feld `token`) |
   | `IG_USER_ID` | `26747704248263278` |
   | `IG_ACCESS_TOKEN` | (aus `erfolgsgeheimnisse/instagram_config.json` → Feld `access_token`) |

5. Repo → Tab **Actions** → Workflow „publish" → **Run workflow** (manueller Erst-Test).

**End-to-End-Test (PC aus):** lokal ein Reel einplanen, dann PC herunterfahren:
```
python stage.py --reel 6 --platforms instagram --when "<in ~15 Min, UTC: YYYY-MM-DD HH:mm>"
```
→ Der GitHub-Cron (alle 30 Min) postet es von selbst; Status in der Airtable-Queue wird `posted`.
Hinweis: Cron kann 5–15 Min später feuern; Zeiten in **UTC** (aktuell = lokale Zeit − 2 Std im Sommer).

## 🔜 Phase 2 — YouTube Shorts (Google)
1. **console.cloud.google.com** → Projekt anlegen → **YouTube Data API v3** aktivieren.
2. **OAuth-Zustimmungsbildschirm** einrichten + App **verifizieren/„published"** (wichtig für
   dauerhafte Tokens — sonst verfallen sie nach 7 Tagen).
3. OAuth-Client (Desktop) → einmal autorisieren → **Refresh-Token** sichern. Werte gibst du mir.

## 🔜 Phase 3 — TikTok
1. **developers.tiktok.com** → App anlegen → Scope `video.publish`.
2. **Audit für öffentliches Posten beantragen** (bis Freigabe nur privat/Entwurf — wir testen privat).
3. OAuth einmal autorisieren → Refresh-Token sichern. Werte gibst du mir.

---

> **Sicherheit:** Alle Schlüssel landen in privaten Configs / GitHub-Secrets, nie im Code, nie auf
> öffentlichen Hostern. Das Repo ist **privat**. `.gitignore` schützt `*_config.json`.
