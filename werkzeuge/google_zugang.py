#!/usr/bin/env python3
"""Einmalig auf deinem eigenen Rechner ausführen, nicht in der Cloud.

Meldet dich bei Google an, holt einen dauerhaften Zugang (Refresh-Token) für das
Unternehmensprofil und zeigt die Konto- und Standort-Kennungen, die GitHub braucht.

Voraussetzung: Python 3 und ein OAuth-Client vom Typ „Desktop-App“ aus der Google Cloud.
Aufruf:  python3 werkzeuge/google_zugang.py
"""

import getpass
import http.server
import json
import secrets
import urllib.parse
import urllib.request
import webbrowser

PORT = 8765
UMFANG = "https://www.googleapis.com/auth/business.manage"


def post(url, daten):
    anfrage = urllib.request.Request(url, data=urllib.parse.urlencode(daten).encode())
    with urllib.request.urlopen(anfrage, timeout=60) as r:
        return json.load(r)


def get(url, token):
    anfrage = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(anfrage, timeout=60) as r:
        return json.load(r)


def main():
    client_id = input("Client-ID: ").strip()
    client_secret = getpass.getpass("Clientschlüssel (wird nicht angezeigt): ").strip()
    rueckweg = f"http://127.0.0.1:{PORT}"
    zustand = secrets.token_urlsafe(16)
    adresse = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": rueckweg, "response_type": "code",
        "scope": UMFANG, "access_type": "offline", "prompt": "consent", "state": zustand,
    })

    ergebnis = {}

    class Empfang(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            werte = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ergebnis.update({k: v[0] for k, v in werte.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Fertig. Du kannst dieses Fenster schließen.".encode())

        def log_message(self, *args):
            pass

    print("\nIm Browser öffnet sich die Google-Anmeldung. Melde dich mit dem Konto an,")
    print("das das Profil von BoConcept Kiel verwaltet, und erlaube den Zugriff.\n")
    webbrowser.open(adresse)
    print("Falls sich nichts öffnet, diese Adresse in den Browser kopieren:\n", adresse, "\n")
    with http.server.HTTPServer(("127.0.0.1", PORT), Empfang) as server:
        while "code" not in ergebnis and "error" not in ergebnis:
            server.handle_request()

    if "error" in ergebnis or ergebnis.get("state") != zustand:
        raise SystemExit(f"Anmeldung abgebrochen: {ergebnis.get('error', 'falscher Zustand')}")

    token = post("https://oauth2.googleapis.com/token", {
        "client_id": client_id, "client_secret": client_secret, "code": ergebnis["code"],
        "redirect_uri": rueckweg, "grant_type": "authorization_code",
    })
    if "refresh_token" not in token:
        raise SystemExit("Google hat keinen Refresh-Token geliefert. Zugriff in deinem Google-Konto entfernen und erneut starten.")

    print("=" * 60)
    print("In GitHub unter Settings → Secrets and variables → Actions eintragen:\n")
    print("GOOGLE_CLIENT_ID      =", client_id)
    print("GOOGLE_CLIENT_SECRET  = (dein Clientschlüssel)")
    print("GOOGLE_REFRESH_TOKEN  =", token["refresh_token"])

    try:
        konten = get("https://mybusinessaccountmanagement.googleapis.com/v1/accounts", token["access_token"])
        for konto in konten.get("accounts", []):
            print(f"\nKonto: {konto.get('accountName')}  →  GBP_KONTO = {konto['name']}")
            orte = get(f"https://mybusinessbusinessinformation.googleapis.com/v1/{konto['name']}/locations"
                       "?readMask=name,title&pageSize=100", token["access_token"])
            for ort in orte.get("locations", []):
                print(f"   Standort: {ort.get('title')}  →  GBP_STANDORT = {ort['name']}")
    except urllib.error.HTTPError as e:
        print(f"\nKonten konnten nicht gelesen werden (HTTP {e.code}).")
        print("Meist ist der API-Zugang noch nicht freigegeben. Den Refresh-Token trotzdem schon eintragen.")
    print("=" * 60)
    print("Diese Werte nirgendwo sonst teilen, auch nicht im Chat.")


if __name__ == "__main__":
    main()
