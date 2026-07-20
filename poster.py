# -*- coding: utf-8 -*-
"""CLOUD-Runner (laeuft in GitHub Actions per Cron). Liest die Datei-Queue (queue.json, frueher Airtable-"Publish-Queue",
nimmt faellige Eintraege (status=scheduled, scheduled_time <= jetzt) und postet sie auf die
gewaehlten Plattformen. Schreibt status/Permalink/Fehler zurueck. PC muss NICHT laufen.

Konfig kommt aus Umgebungsvariablen (GitHub-Actions-Secrets) - siehe SETUP.md.
Geheimnisse NIE in den Code/das Repo schreiben.
"""
import datetime as dt
import os
import requests  # noqa: F401 (platforms nutzen eigene Sessions)

import filequeue

from platforms import ig  # youtube, tiktok werden in Phase 2/3 ergaenzt


def env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        raise SystemExit(f"Fehlende Umgebungsvariable: {name}")
    return v


# Datei-Queue statt Airtable (20.07.2026): queue.json im Repo, siehe filequeue.py
IG_USER = env("IG_USER_ID", required=False)
IG_TOKEN = env("IG_ACCESS_TOKEN", required=False)
UP_KEY = env("UPLOADPOST_API_KEY", required=False)      # upload-post.com (TikTok + YouTube)
UP_PROFILE = env("UPLOADPOST_PROFILE", required=False)  # Profilname dort (= Marke)



MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "1"))   # Anti-Blast: hoechstens N Posts pro Lauf


def parse_when(when):
    s = (when or "").strip().replace("T", " ").replace("Z", "").split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def posted_content_keys(days=10):
    """Inhalte, die in den letzten <days> Tagen schon gepostet wurden -> Anti-Duplikat."""
    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    keys = set()
    for e in filequeue.lade().get("entries", []):
        if e.get("status") != "posted":
            continue
        if (e.get("posted_at") or "") < cutoff:
            continue
        k = (e.get("video_url") or e.get("image_urls") or e.get("name") or "").strip()
        if k:
            keys.add(k)
    return keys


def due_records():
    """Faellige scheduled-Eintraege aus queue.json (Zeit <= jetzt UTC oder leer)."""
    now = dt.datetime.utcnow()
    out = []
    for e in filequeue.lade().get("entries", []):
        if e.get("status") != "scheduled":
            continue
        when = (e.get("scheduled_time") or "").strip()
        if not when:
            out.append({"id": e.get("id"), "fields": e})
            continue
        t = parse_when(when)
        if t is None:
            print(f"  WARN: unlesbares scheduled_time '{when}' -> uebersprungen (postet NICHT)")
            continue
        if t <= now:
            out.append({"id": e.get("id"), "fields": e})
    return out


def update(rec_id, fields):
    """Status in queue.json schreiben (der Actions-Workflow committet die Datei zurueck)."""
    daten = filequeue.lade()
    for e in daten.get("entries", []):
        if e.get("id") == rec_id:
            e.update(fields)
            filequeue.speichere(daten)
            return True
    print(f"  FEHLER: Eintrag {rec_id} nicht in queue.json gefunden!")
    return False


def post_one(rec):
    f = rec["fields"]
    platforms = [p.strip() for p in f.get("platforms", "").split(",") if p.strip()]
    results, errors = {}, {}
    for p in platforms:
        try:
            if p == "instagram":
                if (f.get("media_type") or "reel").lower() == "carousel":
                    urls = [u.strip() for u in (f.get("image_urls") or "").split(",") if u.strip()]
                    results["instagram"] = ig.publish_carousel(urls, f.get("caption_ig", ""), IG_USER, IG_TOKEN)
                else:
                    results["instagram"] = ig.publish(f["video_url"], f.get("caption_ig", ""), IG_USER, IG_TOKEN,
                                                       cover_url=(f.get("cover_url") or None))
            elif p == "youtube":
                from platforms import youtube
                if not (UP_KEY and UP_PROFILE):
                    raise RuntimeError("UPLOADPOST_API_KEY / UPLOADPOST_PROFILE nicht gesetzt")
                yt_title = (f.get("yt_title") or f.get("name")
                            or next((l.strip() for l in (f.get("caption") or "").splitlines() if l.strip()), "")
                            or "Video")[:100]
                results["youtube"] = youtube.publish(f["video_url"], yt_title,
                                                     f.get("yt_description") or f.get("caption", "") or yt_title,
                                                     UP_KEY, UP_PROFILE,
                                                     ai_generated=bool(f.get("ai_label")))
            elif p == "tiktok":
                from platforms import tiktok
                if not (UP_KEY and UP_PROFILE):
                    raise RuntimeError("UPLOADPOST_API_KEY / UPLOADPOST_PROFILE nicht gesetzt")
                ai = bool(f.get("ai_label"))
                if (f.get("media_type") or "reel").lower() == "carousel":
                    urls = [u.strip() for u in (f.get("image_urls") or "").split(",") if u.strip()]
                    results["tiktok"] = tiktok.publish_photos(urls, f.get("caption_tiktok", ""),
                                                              UP_KEY, UP_PROFILE, ai_generated=ai)
                else:
                    results["tiktok"] = tiktok.publish_video(f["video_url"], f.get("caption_tiktok", ""),
                                                             UP_KEY, UP_PROFILE, ai_generated=ai)
        except Exception as e:  # eine Plattform darf die anderen nicht blockieren
            errors[p] = str(e)

    # Voruebergehende Plattform-Drosselungen (z.B. TikTok-Tages-Kontingent der upload-post-App):
    # Eintrag auf "scheduled" lassen -> der naechste Cron-Lauf (~20 Min) versucht es erneut.
    TRANSIENT = ("temporary restriction", "user cap", "try again in a few hours", "rate limit")
    all_transient = errors and not results and all(
        any(t in msg.lower() for t in TRANSIENT) for msg in errors.values())
    if all_transient:
        update(rec["id"], {"last_error": "RETRY " + "; ".join(f"{k}:{v}" for k, v in errors.items())[:500]})
        print(f"#{f.get('reel_id')} -> voruebergehend gedrosselt, bleibt scheduled (Retry naechster Lauf)")
        return

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
    if UP_KEY:
        from platforms import uploadpost
        ok, info = uploadpost.token_ok(UP_KEY)
        print(f"  UPLOAD-POST {'OK' if ok else 'TOT'} -> {str(info)[:120]}")
    print("---------------------------------------------")


def main():
    token_check()
    recs = due_records()
    posted_keys = posted_content_keys()      # Anti-Duplikat (letzte 10 Tage)
    AUTHORS = {"confucius", "konfuzius", "benjamin franklin", "marcus aurelius", "epictetus",
               "epiktet", "lao tzu", "laozi", "seneca", "socrates", "sokrates", "plato", "platon",
               "aristotle", "aristoteles", "mark twain", "buddha", "rumi", "nietzsche", "goethe"}

    def is_junk(f):
        return (f.get("name") or "").strip().lower() in AUTHORS

    def ckey(f):
        return (f.get("video_url") or f.get("image_urls") or f.get("name") or "").strip()

    eligible = []
    for rec in recs:
        f = rec["fields"]
        if is_junk(f):
            print(f"  UEBERSPRUNGEN (Muell-Kachel): {f.get('name')}")
            update(rec["id"], {"status": "skipped", "last_error": "Autoren-/Muell-Kachel"})
            continue
        if ckey(f) and ckey(f) in posted_keys:
            print(f"  UEBERSPRUNGEN (Duplikat): {f.get('name')}")
            update(rec["id"], {"status": "skipped", "last_error": "Duplikat (<10 Tage schon gepostet)"})
            continue
        eligible.append(rec)

    eligible.sort(key=lambda r: r["fields"].get("scheduled_time") or "")
    batch = eligible[:MAX_PER_RUN]
    print(f"{len(recs)} faellig | {len(eligible)} nach Filter | poste {len(batch)} (Cap {MAX_PER_RUN})")
    for rec in batch:
        post_one(rec)


if __name__ == "__main__":
    main()
