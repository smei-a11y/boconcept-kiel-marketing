#!/usr/bin/env python3
"""Einmalig auf deinem eigenen Rechner ausführen, nicht in der Cloud.

Macht aus einem kurzlebigen Meta-Zugang (aus dem Graph API Explorer) einen
dauerhaften Seiten-Zugang und zeigt die Kennungen von Facebook-Seite und Instagram-Konto.

Aufruf:  python3 werkzeuge/meta_zugang.py
"""

import getpass
import json
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v23.0"


def get(pfad, **parameter):
    with urllib.request.urlopen(f"{GRAPH}/{pfad}?{urllib.parse.urlencode(parameter)}", timeout=60) as r:
        return json.load(r)


def main():
    app_id = input("App-ID: ").strip()
    app_geheimnis = getpass.getpass("App-Geheimcode (wird nicht angezeigt): ").strip()
    kurz = getpass.getpass("Zugangsschlüssel aus dem Graph API Explorer (wird nicht angezeigt): ").strip()

    lang = get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
               client_secret=app_geheimnis, fb_exchange_token=kurz)["access_token"]
    seiten = get("me/accounts", access_token=lang,
                 fields="id,name,access_token,instagram_business_account{id,username}").get("data", [])
    if not seiten:
        raise SystemExit("Keine Facebook-Seite gefunden. Hast du beim Zugriff die Seite von BoConcept Kiel ausgewählt?")

    print("=" * 60)
    for seite in seiten:
        ig = seite.get("instagram_business_account") or {}
        print(f"\nSeite: {seite['name']}")
        print("   FB_SEITE   =", seite["id"])
        print("   IG_KONTO   =", ig.get("id", "(kein Instagram-Konto verknüpft)"), f"@{ig.get('username', '')}")
        print("   META_TOKEN =", seite["access_token"])
    print("\nDiese Werte für die Seite von BoConcept Kiel in GitHub unter")
    print("Settings → Secrets and variables → Actions eintragen. Nirgendwo sonst teilen.")
    print("=" * 60)


if __name__ == "__main__":
    main()
