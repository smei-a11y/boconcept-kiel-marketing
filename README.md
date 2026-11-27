# BoConcept Kiel Marketing

Holt jeden Morgen die Zahlen von Google-Unternehmensprofil, Instagram und Facebook ab, kostenlos über die offiziellen Schnittstellen, nur lesend.

- `abholen.py`: das Skript (nur Python-Standardbibliothek)
- `.github/workflows/abholen.yml`: täglicher Lauf auf GitHub
- `daten/marketing.json`: das Ergebnis, je Monat und Kanal
- `werkzeuge/`: einmalige Helfer, um die Zugänge zu holen
- [ANLEITUNG.md](ANLEITUNG.md): Einrichtung Schritt für Schritt

## Was in `daten/marketing.json` steht

- `monate`: die letzten 13 vollen Monate mit Profilaufrufen (Suche, Maps), Website-Klicks, Anrufen, Routenanfragen, Bewertungen, Sternen sowie Reichweite, Interaktionen, Beiträgen und Followern für Instagram und Facebook
- `laufender_monat`: der angefangene Monat
- `suchbegriffe`: die häufigsten Google-Suchbegriffe der letzten drei Monate
- `offene_bewertungen`: neueste Bewertungen ohne Antwort (ohne Namen)
- `top_beitraege`: die stärksten Instagram-Beiträge der letzten 60 Tage
- `fehler`: was beim letzten Lauf nicht geklappt hat

Reichweiten sind Summen der Tageswerte und können von den Monatszahlen in der Meta Business Suite abweichen. Follower werden ab dem ersten Lauf täglich mitgeschrieben, ältere Werte gibt es nicht.

## Lokal prüfen

    python3 -m unittest discover -s tests
