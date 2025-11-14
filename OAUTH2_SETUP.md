# 🔐 OAuth2 Setup - Schritt für Schritt

Diese Anleitung zeigt dir, wie du die YouTube OAuth2 Credentials einrichtest.

## 🎯 Was ist OAuth2?

OAuth2 gibt dem Bot Zugriff auf **deine private** Watch Later Liste - sicher und ohne Passwörter.

---

## 📋 Schritt-für-Schritt Anleitung

### 1️⃣ Google Cloud Projekt erstellen

1. Gehe zu: https://console.cloud.google.com/
2. Oben links: **"Projekt auswählen"** → **"Neues Projekt"**
3. Name: `YouTube Summarizer` (oder beliebig)
4. Klicke **"Erstellen"**

### 2️⃣ YouTube Data API aktivieren

1. Im Menü: **"APIs & Services"** → **"Library"**
2. Suche: `YouTube Data API v3`
3. Klicke drauf → **"Aktivieren"**

### 3️⃣ OAuth2 Credentials erstellen

1. Im Menü: **"APIs & Services"** → **"Credentials"**
2. Klicke: **"Create Credentials"** → **"OAuth client ID"**

**Falls OAuth-Zustimmungsbildschirm fehlt:**
- Klicke **"Configure Consent Screen"**
- Wähle **"External"** (für persönliche Nutzung)
- App-Name: `YouTube Summarizer`
- Deine Email eintragen
- Scrolle runter → **"Speichern und fortfahren"**
- Bei Scopes: **"Speichern und fortfahren"** (nichts ändern)
- Testnutzer hinzufügen: Deine eigene Email!
- **"Speichern und fortfahren"**

3. Jetzt zurück zu **"Create Credentials"** → **"OAuth client ID"**
4. Application type: **"Desktop app"**
5. Name: `YouTube Summarizer Desktop`
6. Klicke **"Create"**

### 4️⃣ credentials.json herunterladen

1. Nach dem Erstellen erscheint ein Popup
2. Klicke **"Download JSON"**
3. Datei wird heruntergeladen (z.B. `client_secret_xxx.json`)

**WICHTIG:** Benenne die Datei um zu: `credentials.json`

### 5️⃣ credentials.json ins Projekt kopieren

```bash
# Im youtube-summarizer Verzeichnis:
mkdir -p data
cp ~/Downloads/credentials.json data/credentials.json
```

Die Datei muss hier liegen:
```
youtube-summarizer/
├── data/
│   └── credentials.json  ← Hier!
├── docker-compose.yml
├── ...
```

### 6️⃣ .env Datei vorbereiten

```bash
cp .env.example .env
# Trage Claude API Key und Email ein (siehe README.md)
```

### 7️⃣ Starten und Authentifizieren

**WICHTIG:** Beim ersten Start NICHT mit `-d` starten!

```bash
docker-compose up
```

**Was passiert jetzt:**

1. Container startet
2. Du siehst eine **URL** im Terminal
3. **Kopiere die URL** und öffne sie in deinem Browser
4. **Google Login:** Melde dich mit deinem YouTube Account an
5. **Berechtigungen:** Bestätige den Zugriff (nur readonly!)
6. **"This app isn't verified" Warnung:**
   - Klicke **"Advanced"**
   - Klicke **"Go to YouTube Summarizer (unsafe)"**
   - Das ist OK, weil es DEINE App ist!
7. **Allow access**
8. Du wirst zu einer URL weitergeleitet (z.B. `http://localhost/?code=...&scope=...`)
9. **Kopiere die KOMPLETTE URL** aus der Adresszeile
10. **Füge sie im Terminal ein** und drücke Enter
11. Fertig! ✅

**Beispiel Output:**
```
🔐 Erste Authentifizierung erforderlich!
============================================================

📋 SCHRITT 1: Öffne diese URL in deinem Browser:
------------------------------------------------------------
https://accounts.google.com/o/oauth2/auth?client_id=...
------------------------------------------------------------

📋 SCHRITT 2: Nach der Anmeldung wirst du zu einer URL weitergeleitet.
Kopiere die KOMPLETTE URL aus der Adresszeile deines Browsers.
(Sie beginnt mit http://localhost/...)

🔗 Füge die URL hier ein und drücke Enter: _
```

### 8️⃣ Container im Hintergrund laufen lassen

Nach erfolgreicher Authentifizierung:

```bash
# Strg+C zum Stoppen
docker-compose down

# Im Hintergrund starten
docker-compose up -d
```

**Token wird gespeichert!** Beim nächsten Start keine Authentifizierung mehr nötig! 🎉

---

## 🔍 Überprüfung

### Token wurde erstellt?
```bash
ls -la data/
# Sollte zeigen:
# - credentials.json
# - token.pickle  ← Neu erstellt!
```

### Logs checken
```bash
docker-compose logs -f

# Sollte zeigen:
# ✅ Authentifizierung erfolgreich!
# 🚀 YouTube Watch Later Summarizer gestartet!
```

---

## 🐛 Troubleshooting

### "credentials.json nicht gefunden"
→ Stelle sicher, dass die Datei in `./data/credentials.json` liegt

### "webbrowser error" oder "could not locate runnable browser"
→ Das ist normal! Du musst die URL manuell öffnen (siehe Schritt 7)

### "Invalid authorization code"
→ Stelle sicher, dass du die **komplette URL** kopiert hast
→ URL muss mit `http://localhost/?code=...` beginnen

### "Access blocked: This app's request is invalid"
→ Stelle sicher, dass du dich als **Testnutzer** eingetragen hast (Schritt 3)

### Token abgelaufen
→ Lösche `data/token.pickle`
→ Starte Container neu → Neue Authentifizierung

---

## 🔒 Sicherheit

- **credentials.json** enthält sensible Daten → NIEMALS committen!
- **token.pickle** ist dein Zugriffstoken → NIEMALS teilen!
- Beide Dateien sind in `.gitignore` eingetragen ✅

---

## ✅ Fertig!

Wenn alles läuft:
- OAuth2 ist eingerichtet ✅
- Watch Later Zugriff funktioniert ✅
- Zusammenfassungen kommen per Email ✅

Bei Fragen → Schreib mir! 😊
