#!/usr/bin/env python3
"""Holt die Marketing-Zahlen von BoConcept Kiel und schreibt sie nach daten/marketing.json.

Quellen (alle kostenlos, nur lesend):
- Google Business Profile Performance API: Profilaufrufe, Website-Klicks, Anrufe, Routen, Suchbegriffe
- Google My Business API v4: Bewertungen
- Meta Graph API: Instagram- und Facebook-Statistiken

Nur Python-Standardbibliothek, damit keine fremden Pakete mitlaufen.
Zugangsdaten kommen ausschließlich aus Umgebungsvariablen (GitHub-Secrets).
Eine Quelle ohne Zugangsdaten wird übersprungen.
"""

from __future__ import annotations

import calendar
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

MONATE_ZURUECK = 13
GRAPH = "https://graph.facebook.com/v23.0"
ORDNER = Path(__file__).resolve().parent / "daten"
AUSGABE = ORDNER / "marketing.json"
FOLLOWER_DATEI = ORDNER / "follower_verlauf.json"

FELDER = [
    "gbp_suche", "gbp_maps", "gbp_web", "gbp_anrufe", "gbp_routen",
    "gbp_bewertungen", "gbp_sterne",
    "ig_follower", "ig_reichweite", "ig_interaktionen", "ig_beitraege",
    "fb_follower", "fb_reichweite", "fb_interaktionen", "fb_beitraege",
]

GBP_METRIKEN = {
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "gbp_suche",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "gbp_suche",
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "gbp_maps",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "gbp_maps",
    "WEBSITE_CLICKS": "gbp_web",
    "CALL_CLICKS": "gbp_anrufe",
    "BUSINESS_DIRECTION_REQUESTS": "gbp_routen",
}

STERNE = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}

# Meta benennt Seiten-Metriken immer wieder um. Die erste, die antwortet, wird genommen.
FB_REICHWEITE_KANDIDATEN = ["page_impressions_unique", "page_total_media_view_unique"]
FB_INTERAKTION_KANDIDATEN = ["page_post_engagements"]

fehler: list[str] = []


# ---------------------------------------------------------------- Hilfen

def http_json(url: str, *, daten: dict | None = None, token: str | None = None) -> dict:
    kopf = {"Accept": "application/json"}
    if token:
        kopf["Authorization"] = f"Bearer {token}"
    body = urllib.parse.urlencode(daten).encode() if daten is not None else None
    anfrage = urllib.request.Request(url, data=body, headers=kopf)
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:
        return json.load(antwort)


def versuch(beschreibung: str, fn, *args, **kwargs):
    """Führt fn aus. Ein Fehler wird notiert, ohne URL (dort könnten Schlüssel stehen)."""
    try:
        return fn(*args, **kwargs)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")[:300]
        fehler.append(f"{beschreibung}: HTTP {e.code} {text}")
    except Exception as e:  # noqa: BLE001
        fehler.append(f"{beschreibung}: {type(e).__name__}: {e}")
    return None


def monatsschluessel(d: dt.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def monatsliste(heute: dt.date) -> list[str]:
    """Die letzten MONATE_ZURUECK vollen Monate, ältester zuerst."""
    index = heute.year * 12 + heute.month - 1
    return [f"{(index - i) // 12:04d}-{(index - i) % 12 + 1:02d}" for i in range(MONATE_ZURUECK, 0, -1)]


def grenzen(monat: str) -> tuple[dt.date, dt.date]:
    jahr, mon = map(int, monat.split("-"))
    return dt.date(jahr, mon, 1), dt.date(jahr, mon, calendar.monthrange(jahr, mon)[1])


def fenster(start: dt.date, ende: dt.date, tage: int = 30):
    """Teilt einen Zeitraum in Stücke von höchstens `tage` Tagen (Meta erlaubt nicht mehr)."""
    von = start
    while von <= ende:
        bis = min(ende, von + dt.timedelta(days=tage - 1))
        yield von, bis
        von = bis + dt.timedelta(days=1)


def unix(d: dt.date) -> int:
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())


# ---------------------------------------------------------------- Google

def google_token() -> str:
    antwort = http_json("https://oauth2.googleapis.com/token", daten={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    return antwort["access_token"]


def google_summen(antwort: dict) -> dict[tuple[str, str], int]:
    """Summiert die Tageswerte der Performance API je (Monat, Feld)."""
    summen: dict[tuple[str, str], int] = defaultdict(int)
    for block in antwort.get("multiDailyMetricTimeSeries", []):
        for reihe in block.get("dailyMetricTimeSeries", []):
            feld = GBP_METRIKEN.get(reihe.get("dailyMetric", ""))
            if not feld:
                continue
            for punkt in reihe.get("timeSeries", {}).get("datedValues", []):
                datum = punkt.get("date", {})
                if "year" not in datum or "month" not in datum:
                    continue
                schluessel = (f"{datum['year']:04d}-{datum['month']:02d}", feld)
                summen[schluessel] += int(punkt.get("value", 0) or 0)
    return summen


def google_leistung(token: str, standort: str, start: dt.date, ende: dt.date) -> dict:
    abfrage = [("dailyMetrics", m) for m in GBP_METRIKEN] + [
        ("dailyRange.startDate.year", start.year), ("dailyRange.startDate.month", start.month),
        ("dailyRange.startDate.day", start.day),
        ("dailyRange.endDate.year", ende.year), ("dailyRange.endDate.month", ende.month),
        ("dailyRange.endDate.day", ende.day),
    ]
    url = (f"https://businessprofileperformance.googleapis.com/v1/{standort}"
           f":fetchMultiDailyMetricsTimeSeries?{urllib.parse.urlencode(abfrage)}")
    return google_summen(http_json(url, token=token))


def google_suchbegriffe(token: str, standort: str, monat: str, anzahl: int = 15) -> list[dict]:
    jahr, mon = map(int, monat.split("-"))
    basis = {
        "monthlyRange.startMonth.year": jahr, "monthlyRange.startMonth.month": mon,
        "monthlyRange.endMonth.year": jahr, "monthlyRange.endMonth.month": mon,
        "pageSize": 100,
    }
    begriffe = []
    seite = None
    for _ in range(5):
        abfrage = dict(basis, **({"pageToken": seite} if seite else {}))
        url = (f"https://businessprofileperformance.googleapis.com/v1/{standort}"
               f"/searchkeywords/impressions/monthly?{urllib.parse.urlencode(abfrage)}")
        antwort = http_json(url, token=token)
        for eintrag in antwort.get("searchKeywordsCounts", []):
            wert = eintrag.get("insightsValue", {})
            if "value" in wert:
                begriffe.append({"begriff": eintrag.get("searchKeyword"), "aufrufe": int(wert["value"]), "unter": None})
            elif "threshold" in wert:
                begriffe.append({"begriff": eintrag.get("searchKeyword"), "aufrufe": None, "unter": int(wert["threshold"])})
        seite = antwort.get("nextPageToken")
        if not seite:
            break
    begriffe.sort(key=lambda b: (b["aufrufe"] is None, -(b["aufrufe"] or 0)))
    return [dict(b, monat=monat) for b in begriffe[:anzahl]]


def google_bewertungen(token: str, konto: str, standort: str) -> list[dict]:
    """Alle Bewertungen über die API v4 (benötigt accounts/…/locations/…)."""
    standort_id = standort.split("/")[-1]
    alle = []
    seite = None
    for _ in range(40):
        abfrage = {"pageSize": 50, **({"pageToken": seite} if seite else {})}
        url = (f"https://mybusiness.googleapis.com/v4/{konto}/locations/{standort_id}/reviews?"
               f"{urllib.parse.urlencode(abfrage)}")
        antwort = http_json(url, token=token)
        alle.extend(antwort.get("reviews", []))
        seite = antwort.get("nextPageToken")
        if not seite:
            break
    return alle


def bewertungen_je_monat(bewertungen: list[dict], monate: list[str]) -> dict[str, dict]:
    """Anzahl und Schnitt aller Bewertungen bis zum jeweiligen Monatsende."""
    punkte = []
    for b in bewertungen:
        sterne = STERNE.get(b.get("starRating", ""))
        datum = (b.get("createTime") or "")[:10]
        if sterne and datum:
            punkte.append((datum, sterne))
    ergebnis = {}
    for monat in monate:
        ende = grenzen(monat)[1].isoformat()
        bis_dahin = [s for d, s in punkte if d <= ende]
        ergebnis[monat] = {
            "gbp_bewertungen": len(bis_dahin),
            "gbp_sterne": round(sum(bis_dahin) / len(bis_dahin), 2) if bis_dahin else None,
        }
    return ergebnis


def offene_bewertungen(bewertungen: list[dict], anzahl: int = 10) -> list[dict]:
    """Neueste Bewertungen ohne Antwort. Ohne Namen der Verfasser."""
    offen = [b for b in bewertungen if not b.get("reviewReply")]
    offen.sort(key=lambda b: b.get("createTime", ""), reverse=True)
    return [{
        "datum": (b.get("createTime") or "")[:10],
        "sterne": STERNE.get(b.get("starRating", "")),
        "text": (b.get("comment") or "")[:400],
    } for b in offen[:anzahl]]


# ---------------------------------------------------------------- Meta

def graph(pfad: str, token: str, **parameter) -> dict:
    return http_json(f"{GRAPH}/{pfad}?{urllib.parse.urlencode(parameter)}", token=token)


def graph_seiten(pfad: str, token: str, stopp=None, maximal: int = 20, **parameter) -> list[dict]:
    """Liest eine Liste über mehrere Seiten. `stopp(eintrag)` beendet früh."""
    eintraege = []
    url = f"{GRAPH}/{pfad}?{urllib.parse.urlencode(parameter)}"
    for _ in range(maximal):
        antwort = http_json(url, token=token)
        for e in antwort.get("data", []):
            if stopp and stopp(e):
                return eintraege
            eintraege.append(e)
        url = antwort.get("paging", {}).get("next")
        if not url:
            break
    return eintraege


def tageswerte_summe(antwort: dict) -> int:
    summe = 0
    for reihe in antwort.get("data", []):
        for wert in reihe.get("values", []):
            v = wert.get("value")
            if isinstance(v, (int, float)):
                summe += v
    return int(summe)


def gesamtwert(antwort: dict) -> int:
    summe = 0
    for reihe in antwort.get("data", []):
        v = reihe.get("total_value", {}).get("value")
        if isinstance(v, (int, float)):
            summe += v
    return int(summe)


def zaehle_je_monat(eintraege: list[dict], zeitfeld: str) -> dict[str, int]:
    zaehler: dict[str, int] = defaultdict(int)
    for e in eintraege:
        zeit = e.get(zeitfeld) or ""
        if len(zeit) >= 7:
            zaehler[zeit[:7]] += 1
    return dict(zaehler)


def instagram(token: str, ig: str, monate: list[str]) -> tuple[dict, dict, list]:
    werte: dict[str, dict] = defaultdict(dict)
    for monat in monate:
        start, ende = grenzen(monat)
        reichweite = interaktionen = 0
        ok_r = ok_i = True
        for von, bis in fenster(start, ende):
            zeit = {"since": unix(von), "until": unix(bis + dt.timedelta(days=1))}
            r = versuch(f"Instagram Reichweite {monat}", graph, f"{ig}/insights", token,
                        metric="reach", period="day", **zeit)
            i = versuch(f"Instagram Interaktionen {monat}", graph, f"{ig}/insights", token,
                        metric="total_interactions", period="day", metric_type="total_value", **zeit)
            if r is None:
                ok_r = False
            else:
                reichweite += tageswerte_summe(r)
            if i is None:
                ok_i = False
            else:
                interaktionen += gesamtwert(i)
        werte[monat]["ig_reichweite"] = reichweite if ok_r else None
        werte[monat]["ig_interaktionen"] = interaktionen if ok_i else None

    erster = grenzen(monate[0])[0].isoformat()
    medien_roh = versuch("Instagram Beiträge", graph_seiten, f"{ig}/media", token,
                         stopp=lambda m: (m.get("timestamp") or "")[:10] < erster,
                         fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
                         limit=50)
    medien = medien_roh or []
    je_monat = zaehle_je_monat(medien, "timestamp")
    for monat in monate:
        werte[monat]["ig_beitraege"] = je_monat.get(monat, 0) if medien_roh is not None else None

    profil = versuch("Instagram Profil", graph, ig, token, fields="followers_count,media_count") or {}

    grenze = (dt.date.today() - dt.timedelta(days=60)).isoformat()
    juengste = [m for m in medien if (m.get("timestamp") or "")[:10] >= grenze]
    juengste.sort(key=lambda m: (m.get("like_count") or 0) + (m.get("comments_count") or 0), reverse=True)
    top = []
    for m in juengste[:5]:
        einblick = versuch("Instagram Beitrag", graph, f"{m['id']}/insights", token,
                           metric="reach,total_interactions") or {}
        zahlen = {r.get("name"): (r.get("values") or [{}])[0].get("value") for r in einblick.get("data", [])}
        top.append({
            "kanal": "Instagram",
            "datum": (m.get("timestamp") or "")[:10],
            "art": m.get("media_product_type") or m.get("media_type"),
            "text": (m.get("caption") or "")[:200],
            "link": m.get("permalink"),
            "likes": m.get("like_count"),
            "kommentare": m.get("comments_count"),
            "reichweite": zahlen.get("reach"),
            "interaktionen": zahlen.get("total_interactions"),
        })
    return werte, profil, top


def facebook_metrik(token: str, seite: str, kandidaten: list[str], von: dt.date, bis: dt.date):
    letzter = "keine Kandidaten"
    for metrik in kandidaten:
        try:
            antwort = graph(f"{seite}/insights", token, metric=metrik, period="day",
                            since=unix(von), until=unix(bis + dt.timedelta(days=1)))
            return tageswerte_summe(antwort)
        except urllib.error.HTTPError as e:
            letzter = f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}"
        except Exception as e:  # noqa: BLE001
            letzter = f"{type(e).__name__}: {e}"
    fehler.append(f"Facebook {', '.join(kandidaten)}: keine Metrik verfügbar ({letzter})")
    return None


def facebook(token: str, seite: str, monate: list[str]) -> tuple[dict, dict]:
    werte: dict[str, dict] = defaultdict(dict)
    for monat in monate:
        start, ende = grenzen(monat)
        summe_r = summe_i = 0
        ok_r = ok_i = True
        for von, bis in fenster(start, ende):
            r = facebook_metrik(token, seite, FB_REICHWEITE_KANDIDATEN, von, bis)
            i = facebook_metrik(token, seite, FB_INTERAKTION_KANDIDATEN, von, bis)
            ok_r, ok_i = ok_r and r is not None, ok_i and i is not None
            summe_r += r or 0
            summe_i += i or 0
        werte[monat]["fb_reichweite"] = summe_r if ok_r else None
        werte[monat]["fb_interaktionen"] = summe_i if ok_i else None

    start = grenzen(monate[0])[0]
    ende = grenzen(monate[-1])[1]
    beitraege = versuch("Facebook Beiträge", graph_seiten, f"{seite}/posts", token,
                        fields="id,created_time", since=unix(start),
                        until=unix(ende + dt.timedelta(days=1)), limit=100)
    je_monat = zaehle_je_monat(beitraege or [], "created_time")
    for monat in monate:
        werte[monat]["fb_beitraege"] = je_monat.get(monat, 0) if beitraege is not None else None

    profil = versuch("Facebook Seite", graph, seite, token, fields="followers_count,fan_count") or {}
    return werte, profil


# ---------------------------------------------------------------- Follower-Verlauf

def follower_fortschreiben(heute: dt.date, ig: int | None, fb: int | None) -> list[dict]:
    """Meta liefert Follower nur als heutigen Stand. Wir merken uns jeden Tag einen Wert."""
    verlauf = []
    if FOLLOWER_DATEI.exists():
        verlauf = json.loads(FOLLOWER_DATEI.read_text(encoding="utf-8"))
    verlauf = [v for v in verlauf if v.get("datum") != heute.isoformat()]
    if ig is not None or fb is not None:
        verlauf.append({"datum": heute.isoformat(), "ig": ig, "fb": fb})
    verlauf.sort(key=lambda v: v["datum"])
    FOLLOWER_DATEI.write_text(json.dumps(verlauf, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return verlauf


def follower_je_monat(verlauf: list[dict], monate: list[str]) -> dict[str, dict]:
    ergebnis = {}
    for monat in monate:
        im_monat = [v for v in verlauf if v["datum"][:7] == monat]
        letzter = im_monat[-1] if im_monat else {}
        ergebnis[monat] = {"ig_follower": letzter.get("ig"), "fb_follower": letzter.get("fb")}
    return ergebnis


# ---------------------------------------------------------------- Ablauf

def hat(*namen: str) -> bool:
    return all(os.environ.get(n) for n in namen)


def main() -> int:
    heute = dt.date.today()
    monate = monatsliste(heute)
    laufend = monatsschluessel(heute)
    zeilen: dict[str, dict] = {m: {"monat": m, **{f: None for f in FELDER}} for m in monate + [laufend]}
    ausgabe: dict = {"quellen": {}, "suchbegriffe": [], "offene_bewertungen": [], "top_beitraege": []}

    if hat("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GBP_STANDORT"):
        standort = os.environ["GBP_STANDORT"]
        token = versuch("Google Anmeldung", google_token)
        if token:
            start, ende = grenzen(monate[0])[0], heute - dt.timedelta(days=1)
            summen = versuch("Google Leistung", google_leistung, token, standort, start, ende)
            if summen is not None:
                for monat, zeile in zeilen.items():
                    for feld in set(GBP_METRIKEN.values()):
                        zeile[feld] = summen.get((monat, feld), 0)
            for monat in monate[-3:]:
                ausgabe["suchbegriffe"] += versuch(f"Google Suchbegriffe {monat}", google_suchbegriffe,
                                                   token, standort, monat) or []
            if os.environ.get("GBP_KONTO"):
                bewertungen = versuch("Google Bewertungen", google_bewertungen, token,
                                      os.environ["GBP_KONTO"], standort)
                if bewertungen is not None:
                    for monat, werte in bewertungen_je_monat(bewertungen, list(zeilen)).items():
                        zeilen[monat].update(werte)
                    ausgabe["offene_bewertungen"] = offene_bewertungen(bewertungen)
        ausgabe["quellen"]["google"] = "eingerichtet"
    else:
        ausgabe["quellen"]["google"] = "nicht eingerichtet"

    ig_profil, fb_profil = {}, {}
    if hat("META_TOKEN", "IG_KONTO"):
        werte, ig_profil, top = instagram(os.environ["META_TOKEN"], os.environ["IG_KONTO"], monate + [laufend])
        for monat, w in werte.items():
            zeilen[monat].update(w)
        ausgabe["top_beitraege"] += top
        ausgabe["quellen"]["instagram"] = "eingerichtet"
    else:
        ausgabe["quellen"]["instagram"] = "nicht eingerichtet"

    if hat("META_TOKEN", "FB_SEITE"):
        werte, fb_profil = facebook(os.environ["META_TOKEN"], os.environ["FB_SEITE"], monate + [laufend])
        for monat, w in werte.items():
            zeilen[monat].update(w)
        ausgabe["quellen"]["facebook"] = "eingerichtet"
    else:
        ausgabe["quellen"]["facebook"] = "nicht eingerichtet"

    ORDNER.mkdir(exist_ok=True)
    verlauf = follower_fortschreiben(heute, ig_profil.get("followers_count"), fb_profil.get("followers_count"))
    for monat, werte in follower_je_monat(verlauf, list(zeilen)).items():
        zeilen[monat].update(werte)

    ausgabe = {
        "aktualisiert": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "hinweis": "Reichweiten sind Summen der Tageswerte. Follower gibt es erst ab dem Tag, an dem die Abholung startete.",
        "monate": [zeilen[m] for m in monate],
        "laufender_monat": zeilen[laufend],
        **ausgabe,
        "fehler": list(dict.fromkeys(fehler)),
    }
    AUSGABE.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    eingerichtet = [q for q, s in ausgabe["quellen"].items() if s == "eingerichtet"]
    print(f"Geschrieben: {AUSGABE.name}. Quellen: {', '.join(eingerichtet) or 'keine'}. Fehler: {len(fehler)}")
    for f in fehler:
        print(" -", f)
    return 1 if eingerichtet and len(fehler) >= 3 * len(eingerichtet) else 0


if __name__ == "__main__":
    sys.exit(main())
