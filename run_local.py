# -*- coding: utf-8 -*-
"""Loest poster.py LOKAL aus (zuverlaessiger Trigger, falls GitHubs Cron versagt / als Notfall-Rettung).
Liest die Secrets aus den Configs, setzt sie als Env-Variablen, ruft dann poster.main().
Aufruf:  python run_local.py
Kann auch per Windows-Aufgabenplaner zu festen Zeiten laufen (PC muss dann an sein)."""
import json, os

ROOT = r"C:\Users\Alexa\OneDrive\Desktop\Claude\erfolgsgeheimnisse"
ig = json.load(open(os.path.join(ROOT, "instagram_config.json"), encoding="utf-8-sig"))
at = json.load(open(os.path.join(ROOT, "airtable_config.json"), encoding="utf-8-sig"))

os.environ["AIRTABLE_BASE_ID"]    = "app4UPxhyg94byp4X"
os.environ["AIRTABLE_QUEUE_TABLE"] = "tblF2Q50qGIcuuO2U"
os.environ["AIRTABLE_TOKEN"]      = at["token"]
os.environ["IG_USER_ID"]          = ig["instagram_user_id"]
os.environ["IG_ACCESS_TOKEN"]     = ig["access_token"]

# upload-post (TikTok + YouTube) aus der Publisher-Config
HERE = os.path.dirname(os.path.abspath(__file__))
up = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8")).get("uploadpost", {})
if up:
    os.environ["UPLOADPOST_API_KEY"] = up["api_key"]
    os.environ["UPLOADPOST_PROFILE"] = up["profile"]

import poster  # liest die Env-Variablen beim Import
poster.main()
