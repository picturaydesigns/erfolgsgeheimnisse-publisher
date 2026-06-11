# -*- coding: utf-8 -*-
import json, os, requests, sys
sys.stdout.reconfigure(encoding="utf-8")

at = json.load(open("../erfolgsgeheimnisse/airtable_config.json", encoding="utf-8-sig"))
headers = {"Authorization": "Bearer " + at["token"]}
url = "https://api.airtable.com/v0/app4UPxhyg94byp4X/tblF2Q50qGIcuuO2U"
out, offset = [], None
while True:
    params = {"pageSize": 100}
    if offset:
        params["offset"] = offset
    j = requests.get(url, headers=headers, params=params).json()
    out += j.get("records", [])
    offset = j.get("offset")
    if not offset:
        break
print(f"Queue: {len(out)} Eintraege\n")
for rec in sorted(out, key=lambda x: (x["fields"].get("scheduled_time","") , x["fields"].get("reel_id", 0))):
    f = rec["fields"]
    rid = str(f.get("reel_id", "?")).rjust(2)
    st = (f.get("status", "?") or "?").ljust(10)
    dat = (f.get("scheduled_time") or "kein Datum")[:16].ljust(16)
    title = (f.get("title") or "?")[:32]
    print(f"  #{rid} | {st} | {dat} | {title}")
