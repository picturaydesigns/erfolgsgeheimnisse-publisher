# -*- coding: utf-8 -*-
"""Einmaliger TikTok-OAuth-Login (Desktop-Flow mit PKCE).
Holt access_token + refresh_token + open_id und speichert sie in
../erfolgsgeheimnisse/tiktok_config.json.

Aufruf:  python tiktok_oauth.py

Voraussetzung in der TikTok-App (developers.tiktok.com):
  - Produkte: Login Kit + Content Posting API
  - Scope aktiviert: video.upload  (+ user.info.basic)
  - Redirect-URI registriert: http://localhost:8080/callback/  (Desktop-Plattform)
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser

import requests

sys.stdout.reconfigure(encoding="utf-8")

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erfolgsgeheimnisse", "tiktok_config.json")
cfg = json.load(open(CFG, encoding="utf-8-sig"))

CLIENT_KEY = cfg["client_key"]
CLIENT_SECRET = cfg["client_secret"]
REDIRECT_URI = cfg.get("redirect_uri") or "http://localhost:8080/callback/"
SCOPE = "video.upload,user.info.basic"
PORT = int(urllib.parse.urlparse(REDIRECT_URI).port or 8080)
PATH = urllib.parse.urlparse(REDIRECT_URI).path or "/"

# --- PKCE (Pflicht im Desktop-Flow) ---
code_verifier = secrets.token_hex(48)  # 96 Zeichen, [43..128] erlaubt
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")
state = secrets.token_urlsafe(16)

auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": CLIENT_KEY,
    "scope": SCOPE,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "state": state,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
})

result = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if "code" in params:
            result["code"] = params["code"][0]
            msg = "<h2>Fertig! Du kannst dieses Fenster schliessen und zu Claude zurueck.</h2>"
        else:
            result["error"] = self.path
            msg = "<h2>Kein Code erhalten. Zurueck zu Claude und Bescheid geben.</h2>"
        self.wfile.write(msg.encode("utf-8"))

    def log_message(self, *a):
        pass


def serve_once():
    httpd = http.server.HTTPServer(("localhost", PORT), Handler)
    httpd.handle_request()


print("Starte lokalen Login-Server auf Port", PORT)
t = threading.Thread(target=serve_once, daemon=True)
t.start()
print("Oeffne Browser zur TikTok-Anmeldung. Falls er nicht aufgeht, oeffne diesen Link von Hand:\n")
print(auth_url, "\n")
webbrowser.open(auth_url)
t.join(timeout=300)

if "code" not in result:
    raise SystemExit(f"Kein Auth-Code empfangen (Timeout/Abbruch). Detail: {result.get('error','-')}")

print("Auth-Code erhalten, tausche gegen Tokens...")
r = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    data={
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": result["code"],
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=60,
)
j = r.json()
if "access_token" not in j:
    raise SystemExit(f"Token-Fehler: {j}")

cfg["access_token"] = j["access_token"]
cfg["refresh_token"] = j.get("refresh_token", "")
cfg["open_id"] = j.get("open_id", "")
cfg["scope"] = j.get("scope", SCOPE)
json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("OK! TikTok-Login erfolgreich.")
print(f"  open_id: {str(j.get('open_id',''))[:12]}...")
print(f"  scope:   {j.get('scope')}")
print(f"  access_token gueltig ~{j.get('expires_in','?')} s, refresh_token ~{j.get('refresh_expires_in','?')} s")
print("Tokens in tiktok_config.json gespeichert.")
