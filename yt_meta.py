# -*- coding: utf-8 -*-
"""Hilfsfunktion fuer YouTube-Metadaten beim Staging (Auftrag 27, YouTube-Regelbetrieb).

build_yt_meta(title, caption) -> (yt_title, yt_description)
- yt_title: Hook-basiert (erste Caption-Zeile, sonst Reel-Titel), deutsch,
  max ~90 Zeichen, endet auf "#Shorts".
- yt_description: kurze Beschreibung = Caption inkl. Hashtags, "#Shorts" wird
  ergaenzt, falls noch nicht enthalten.
Explizite Werte (yt_title/yt_description, z.B. aus reels.json) haben Vorrang.
"""


def build_yt_meta(title, caption, yt_title="", yt_description=""):
    if not yt_title:
        hook = next((l.strip() for l in (caption or "").splitlines()
                     if l.strip() and not l.strip().startswith("#")), "")
        base = (hook or title or "").strip().rstrip(".")
        if len(base) > 82:
            base = base[:81].rstrip(" ,;:-") + "…"
        yt_title = (base + " #Shorts").strip()
    if not yt_description:
        desc = (caption or "").strip() or (title or "")
        if "#shorts" not in desc.lower():
            desc += "\n\n#Shorts"
        yt_description = desc
    return yt_title[:100], yt_description[:4900]
