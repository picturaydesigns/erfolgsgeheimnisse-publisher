# -*- coding: utf-8 -*-
"""CLOUD-Runner (laeuft in GitHub Actions per Cron). Liest die Airtable-"Publish-Queue",
nimmt faellige Eintraege (status=scheduled, scheduled_time <= jetzt) und postet sie auf die
gewaehlten Plattformen. Schreibt status/Permalink/Fehler zurueck. PC muss NICHT laufen.

Konfig kommt aus Umgebungsvariablen (GitHub-Actions-Secrets) - siehe SETUP.md.
Geheimnisse NIE in den Code/das Repo schreiben.
"""
import datetime as dt
import os
import requests

from platforms import ig  # youtube, tiktok werden in Phase 2/3 ergaenzt


def env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        raise SystemExit(f"Fehlende Umgebungsvariable: {name}")
    return v


AT_BASE = env("AIRTABLE_BASE_ID")
AT_TABLE = env("AIRTABLE_QUEUE_TABLE")
AT_TOKEN = env("AIRTABLE_TOKEN")
IG_USER = env("IG_USER_ID", required=False)
IG_TOKEN = env("IG_ACCESS_TOKEN", required=False)

AT_URL = f"https://api.airtable.com/v0/{AT_BASE}/{AT_TABLE}"
AT_HEADERS = {"Authorization": f"Bearer {AT_TOKEN}", "Content-Type": "application/json"}


def due_records():
    """Alle scheduled-Eintraege holen; faellige (Zeit <= jetzt oder leer) in Python filtern."""
    now = dt.datetime.utcnow()
    out, offset = [], None
    while True:
        params = {"filterByFormula": "{status}='scheduled'"}
        if offset:
            params["offset"] = offset
        j = requests.get(AT_URL, headers=AT_HEADERS, params=params, timeout=60).json()
        for rec in j.get("records", []):
            f = rec.get("fields", {})
            when = f.get("scheduled_time", "").strip()
            due = True
            if when:
                try:
                    due = dt.datetime.strptime(when, "%Y-%m-%d %H:%M") <= now
                except ValueError:
                    due = True
            if due:
                out.append(rec)
        offset = j.get("offset")
        if not offset:
            break
    return out


def update(rec_id, fields):
    requests.patch(f"{AT_URL}/{rec_id}", headers=AT_HEADERS, json={"fields": fields}, timeout=60)


def post_one(rec):
    f = rec["fields"]
    platforms = [p.strip() for p in f.get("platforms", "").split(",") if p.strip()]
    results, errors = {}, {}
    for p in platforms:
        try:
            if p == "instagram":
                results["instagram"] = ig.publish(f["video_url"], f.get("caption_ig", ""), IG_USER, IG_TOKEN)
            elif p == "youtube":
                from platforms import youtube
                results["youtube"] = youtube.publish(f["video_url"], f.get("yt_title", ""), f.get("yt_description", ""), [], None)
            elif p == "tiktok":
                from platforms import tiktok
                results["tiktok"] = tiktok.publish(f["video_url"], f.get("caption_tiktok", ""), None)
        except Exception as e:  # eine Plattform darf die anderen nicht blockieren
            errors[p] = str(e)

    fields = {
        "status": "posted" if results and not errors else ("failed" if errors and not results else "partial"),
        "permalinks": "; ".join(f"{k}:{v}" for k, v in results.items()),
        "last_error": "; ".join(f"{k}:{v}" for k, v in errors.items()),
        "posted_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    update(rec["id"], fields)
    print(f"#{f.get('reel_id')} -> ok={list(results)} fehler={list(errors)}")


def token_check():
    """Read-only: zeigt in JEDEM Lauf klar, ob der IG-Token lebt (postet nichts)."""
    print("---------------- TOKEN-CHECK ----------------")
    if not (IG_USER and IG_TOKEN):
        print("  uebersprungen: IG_USER_ID / IG_ACCESS_TOKEN nicht gesetzt.")
        return
    ok, info = ig.token_ok(IG_USER, IG_TOKEN)
    if ok:
        print(f"  TOKEN OK  -> @{info.get('username')} ({info.get('followers_count')} Follower)")
    else:
        print(f"  TOKEN TOT -> Instagram lehnt ab: {info}")
        print("  -> Neuen Token holen + GitHub-Secret IG_ACCESS_TOKEN aktualisieren.")
    print("---------------------------------------------")


def main():
    token_check()
    recs = due_records()
    print(f"{len(recs)} faellige Eintraege.")
    for rec in recs:
        post_one(rec)


if __name__ == "__main__":
    main()
