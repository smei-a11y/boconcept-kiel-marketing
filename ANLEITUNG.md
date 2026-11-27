# Einrichtung: Zahlen automatisch abholen

Einmalig etwa eine Stunde, verteilt auf drei Teile. Alles kostenlos.
Danach holt GitHub jeden Morgen die Zahlen von Google und Meta und legt sie in `daten/marketing.json` ab.

**Wichtig:** Das Repo muss privat sein. Zugangsschlüssel gehören nur in die GitHub-Secrets (Teil 3), nie in den Chat, nie in eine Datei im Repo.

## Vorbereitung auf deinem Windows-PC

1. Python installieren: <https://www.python.org/downloads/> → „Download Python“. Beim Installieren **„Add python.exe to PATH“** anhaken.
2. Dieses Repo herunterladen: Auf der Repo-Seite **Code → Download ZIP**, entpacken, zum Beispiel nach `C:\boconcept-kiel-marketing`.
3. Eingabeaufforderung öffnen (Windows-Taste, `cmd` tippen) und in den Ordner wechseln:
   `cd C:\boconcept-kiel-marketing`

---

## Teil 1: Google-Unternehmensprofil (ca. 20 Minuten plus Wartezeit)

Google gibt den Zugang zur Schnittstelle erst nach einer Prüfung frei. Diesen Teil deshalb **zuerst** erledigen.

### 1a. Projekt anlegen und Zugang beantragen
1. <https://console.cloud.google.com/> öffnen, mit dem Google-Konto anmelden, das das Profil von BoConcept Kiel verwaltet.
2. Oben links auf die Projektauswahl → **Neues Projekt** → Name `boconcept-kiel-marketing` → Erstellen.
3. Im Projekt-Dashboard die **Projektnummer** notieren (Karte „Projektinfo“).
4. Antrag stellen: <https://developers.google.com/my-business/content/prereqs> → dort das Kontaktformular für den API-Zugang öffnen → **„Application for Basic API Access“** wählen. Projektnummer und die geforderten Angaben eintragen. Mit einer E-Mail-Adresse senden, die im Profil als Inhaber oder Verwalter eingetragen ist.
5. Warten auf die Antwort per E-Mail. Freigegeben ist es, wenn unter **APIs & Dienste → Kontingente** für die Business-Profile-APIs **300** Anfragen pro Minute stehen statt **0**.

Google verlangt: ein bestätigtes Profil, das seit mindestens 60 Tagen aktiv ist, und eine Website im Profil.

### 1b. Schnittstellen einschalten (nach der Freigabe)
Unter **APIs & Dienste → Bibliothek** nacheinander suchen und **Aktivieren**:
- Business Profile Performance API
- My Business Account Management API
- My Business Business Information API
- Google My Business API (für die Bewertungen)

### 1c. Anmeldedaten anlegen (geht schon vor der Freigabe)
1. **APIs & Dienste → OAuth-Zustimmungsbildschirm** (heißt teils „Google Auth Platform“): App-Name `BoConcept Kiel Zahlen`, deine E-Mail, Zielgruppe **Extern**.
2. Unter **Zielgruppe** den Veröffentlichungsstatus auf **In Produktion** stellen.
   Sonst läuft der Zugang nach 7 Tagen ab. Eine Überprüfung durch Google ist für die eigene Nutzung nicht nötig.
3. **Clients → Client erstellen** → Anwendungstyp **Desktop-App** → Name egal → Erstellen.
   **Client-ID** und **Clientschlüssel** bereithalten.

### 1d. Dauerhaften Zugang holen
In der Eingabeaufforderung:

    py werkzeuge\google_zugang.py

Client-ID und Clientschlüssel eingeben. Im Browser mit dem Profil-Konto anmelden.
Kommt „Google hat diese App nicht überprüft“: **Erweitert → Weiter zu BoConcept Kiel Zahlen**. Das ist deine eigene App.
Das Skript zeigt danach `GOOGLE_REFRESH_TOKEN`, `GBP_KONTO` und `GBP_STANDORT`.
Vor der Freigabe fehlen Konto und Standort noch. Dann das Skript nach der Freigabe einfach noch einmal starten.

---

## Teil 2: Instagram und Facebook (ca. 30 Minuten)

Voraussetzung: Das Instagram-Konto ist ein **professionelles Konto** und mit der Facebook-Seite von BoConcept Kiel verknüpft. Du bist Admin der Seite.

1. <https://developers.facebook.com/> → mit deinem Facebook-Konto anmelden → **Meine Apps → App erstellen**.
   Name `BoConcept Kiel Zahlen`. Als Anwendungsfall „Sonstiges“, als App-Typ **Business** wählen.
   Die App bleibt im Entwicklungsmodus. Für die eigene Seite braucht es keine Prüfung durch Meta.
2. In der App unter **App-Einstellungen → Allgemeines**: **App-ID** und **App-Geheimcode** bereithalten.
3. <https://developers.facebook.com/tools/explorer/> öffnen. Rechts deine App wählen, dann **Zugangsschlüssel generieren** (Get User Access Token) mit diesen Berechtigungen, und nur diesen:
   `pages_show_list`, `pages_read_engagement`, `read_insights`, `instagram_basic`, `instagram_manage_insights`, `business_management`
   Im Fenster die Seite **BoConcept Kiel** und das Instagram-Konto auswählen.
   Keine dieser Berechtigungen erlaubt Posten oder Nachrichten.
4. In der Eingabeaufforderung:

        py werkzeuge\meta_zugang.py

   App-ID, App-Geheimcode und den Schlüssel aus dem Explorer eingeben. Das Skript zeigt `META_TOKEN`, `FB_SEITE` und `IG_KONTO`. Der Seiten-Schlüssel läuft nicht ab.

---

## Teil 3: In GitHub eintragen (5 Minuten)

Repo → **Settings → Secrets and variables → Actions → New repository secret**. Je Wert ein Secret, Name genau so:

| Name | Woher |
|---|---|
| `GOOGLE_CLIENT_ID` | Teil 1c |
| `GOOGLE_CLIENT_SECRET` | Teil 1c |
| `GOOGLE_REFRESH_TOKEN` | Teil 1d |
| `GBP_KONTO` | Teil 1d, sieht aus wie `accounts/123…` |
| `GBP_STANDORT` | Teil 1d, sieht aus wie `locations/456…` |
| `META_TOKEN` | Teil 2 |
| `FB_SEITE` | Teil 2 |
| `IG_KONTO` | Teil 2 |

Was noch fehlt, wird einfach übersprungen. Meta kann also schon laufen, während Google noch prüft.

**Testen:** Repo → **Actions → Zahlen abholen → Run workflow**. Nach ein bis zwei Minuten liegt `daten/marketing.json` im Repo. Was nicht geklappt hat, steht darin unter `fehler`.

Danach läuft es jeden Morgen von allein.
