# 🎥 YouTube Summarizer - Quick Start

## ✅ Status: LÄUFT AUTOMATISCH!

Der YouTube Summarizer ist bereits eingerichtet und läuft automatisch im Hintergrund.

---

## 🚀 Was macht diese App?

Die App überwacht **alle 30 Minuten** deine YouTube Playlist und:

1. ✅ Findet neue Videos in deiner Playlist
2. ✅ Lädt automatisch die Transkripte herunter
3. ✅ Lässt Claude AI eine Zusammenfassung erstellen
4. ✅ Sendet dir eine Email mit der Zusammenfassung

**Aktuell überwachte Playlist:**
- ID: `PLZ0XGediryt6-HLJAIOw3G0gDckqi3wKw`
- Check-Intervall: 30 Minuten
- Email an: `jan@truebrew-birdie.com`

---

## 📊 Aktueller Status

```bash
# Container Status prüfen:
docker ps --filter name=youtube-summarizer

# Logs ansehen (live):
docker logs youtube-summarizer -f

# Letzte 50 Zeilen:
docker logs youtube-summarizer --tail 50
```

---

## 🔧 Verwaltung

### Container stoppen
```bash
cd ~/dev/youtube-summarizer-oauth2
docker compose down
```

### Container neu starten
```bash
cd ~/dev/youtube-summarizer-oauth2
docker compose restart
```

### Container komplett neu bauen
```bash
cd ~/dev/youtube-summarizer-oauth2
docker compose down
docker compose up -d --build
```

---

## ⚙️ Einstellungen ändern

Bearbeite die `.env` Datei:

```bash
cd ~/dev/youtube-summarizer-oauth2
nano .env  # oder: code .env
```

**Wichtige Einstellungen:**

```bash
# Prüfintervall in Minuten (Standard: 30)
CHECK_INTERVAL_MINUTES=30

# Playlist ID ändern
PLAYLIST_ID=PLZ0XGediryt6-HLJAIOw3G0gDckqi3wKw

# Email Empfänger ändern
EMAIL_TO=jan@truebrew-birdie.com
```

**Nach Änderungen Container neu starten:**
```bash
docker compose restart
```

---

## 🔄 Auto-Start

Der Container ist mit `restart: always` konfiguriert:

✅ **Startet automatisch beim Mac-Start** (wenn Docker Desktop läuft)
✅ **Startet automatisch nach Crashes**
✅ **Startet automatisch nach Mac-Neustart**

### Docker Desktop Auto-Start einrichten

1. Docker Desktop öffnen
2. Settings (⚙️) → General
3. ✅ **"Start Docker Desktop when you log in"** aktivieren
4. ✅ **"Start Docker containers automatically"** aktivieren

---

## 📋 Logs verstehen

**Typische Log-Ausgabe:**

```
🔍 Prüfe Watch Later Liste... (17:45:03)
📊 API hat 3 Videos in Watch Later gefunden
📋 Bereits verarbeitete Videos: 3
▶️  Verarbeite: Dr. Richard Socher: „KI-Browser sind BESCHEUERT!"
🔍 Versuche Transkript für Video di3MKU0-xGE mit RapidAPI abzurufen...
✅ Transkript mit RapidAPI erfolgreich abgerufen! (12345 Zeichen)
🧠 Claude erstellt Zusammenfassung...
✅ Email erfolgreich versendet!
```

**Wichtige Status-Emojis:**
- 🔍 = Prüfung läuft
- ✅ = Erfolgreich
- ❌ = Fehler
- 📧 = Email-Versand
- 🧠 = Claude verarbeitet
- ⏰ = Warten auf nächsten Check

---

## 🐛 Troubleshooting

### Container läuft nicht?

```bash
# Status prüfen:
docker ps -a --filter name=youtube-summarizer

# Logs ansehen:
docker logs youtube-summarizer

# Neu starten:
cd ~/dev/youtube-summarizer-oauth2
docker compose up -d --build
```

### Keine Emails?

1. Prüfe `.env` Datei:
   ```bash
   cat ~/dev/youtube-summarizer-oauth2/.env | grep EMAIL
   ```

2. Stelle sicher dass Gmail App-Passwort korrekt ist:
   - https://myaccount.google.com/apppasswords

3. Logs prüfen auf Email-Fehler:
   ```bash
   docker logs youtube-summarizer | grep -i email
   ```

### OAuth Token abgelaufen?

```bash
# Alte Token löschen:
rm ~/dev/youtube-summarizer-oauth2/data/token.pickle

# Container neu starten (wird OAuth neu durchführen):
docker compose restart

# Logs folgen:
docker logs youtube-summarizer -f
```

### Neue Videos werden nicht erkannt?

1. Prüfe Playlist ID in `.env`:
   ```bash
   grep PLAYLIST_ID ~/dev/youtube-summarizer-oauth2/.env
   ```

2. Prüfe ob Videos wirklich neu sind (innerhalb der letzten 7 Tage)

3. Prüfe `processed_videos.json`:
   ```bash
   cat ~/dev/youtube-summarizer-oauth2/data/processed_videos.json
   ```

---

## 📁 Wichtige Dateien

```
~/dev/youtube-summarizer-oauth2/
├── .env                          # Konfiguration
├── docker-compose.yml            # Docker Setup
├── youtube_summarizer.py         # Hauptprogramm
└── data/
    ├── credentials.json          # OAuth Credentials
    ├── token.pickle              # OAuth Token
    └── processed_videos.json     # Bereits verarbeitete Videos
```

---

## 💡 Tipps

### Mehrere Playlists überwachen?

Erstelle mehrere Container mit verschiedenen Configs:

```bash
# Kopiere Ordner:
cp -r ~/dev/youtube-summarizer-oauth2 ~/dev/youtube-summarizer-tech

# Ändere Container-Name und Playlist ID in docker-compose.yml:
cd ~/dev/youtube-summarizer-tech
nano docker-compose.yml  # container_name ändern
nano .env                # PLAYLIST_ID ändern

# Starte zweiten Container:
docker compose up -d
```

### Test-Email senden?

Füge ein neues Video zu deiner Playlist hinzu und warte max. 30 Minuten, oder restart den Container für sofortigen Check:

```bash
docker compose restart
docker logs youtube-summarizer -f
```

---

## 🔗 Nützliche Links

- **Playlist verwalten:** https://www.youtube.com/playlist?list=PLZ0XGediryt6-HLJAIOw3G0gDckqi3wKw
- **Gmail App-Passwörter:** https://myaccount.google.com/apppasswords
- **RapidAPI Dashboard:** https://rapidapi.com/ytjar/api/yt-api/
- **Claude API Dashboard:** https://console.anthropic.com/

---

**Status:** ✅ Running
**Letzter Check:** Siehe `docker logs youtube-summarizer --tail 1`
**Nächster Check:** Automatisch in 30 Minuten
