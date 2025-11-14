# ⚡ OAuth Quick Start

**Docker Container kann keinen Browser öffnen - das ist normal!**

## So funktioniert's:

### 1. Container starten
```bash
docker-compose up
```

### 2. URL kopieren
Im Terminal erscheint:
```
📋 SCHRITT 1: Öffne diese URL in deinem Browser:
------------------------------------------------------------
https://accounts.google.com/o/oauth2/auth?client_id=...
------------------------------------------------------------
```

**Kopiere diese URL!**

### 3. In Browser öffnen
- Füge die URL in deinen Browser ein
- Melde dich mit deinem YouTube Google-Account an
- Bestätige den Zugriff

### 4. "App nicht verifiziert" Warnung
- Klicke **"Erweitert"** / **"Advanced"**
- Klicke **"Zu YouTube Summarizer wechseln (unsicher)"**
- Das ist OK - es ist deine eigene App!

### 5. Redirect URL kopieren
Nach der Bestätigung:
- Browser zeigt eine Fehlerseite (normal!)
- **Kopiere die KOMPLETTE URL** aus der Adresszeile
- Sie sieht so aus: `http://localhost/?code=4/0Adeu5BW...&scope=https://...`

### 6. URL einfügen
Zurück im Terminal:
```
🔗 Füge die URL hier ein und drücke Enter: _
```

**Füge die komplette URL ein + Enter**

### 7. Fertig! 🎉
```
✅ Authentifizierung erfolgreich!
🚀 YouTube Watch Later Summarizer gestartet!
```

Jetzt mit **Strg+C** stoppen und im Hintergrund starten:
```bash
docker-compose down
docker-compose up -d
```

---

## 🐛 Probleme?

### URL funktioniert nicht
→ Stelle sicher, dass du die **komplette URL** kopiert hast
→ Sie muss mit `http://localhost/?code=` beginnen

### "Invalid client"
→ Prüfe ob `data/credentials.json` korrekt ist

### "Access blocked"
→ Hast du dich als Testnutzer eingetragen? (siehe OAUTH2_SETUP.md)

---

## ✅ Token gespeichert?

Nach erfolgreicher Auth sollte existieren:
```bash
ls -la data/
# Sollte zeigen:
# - credentials.json
# - token.pickle  ← Neu!
```

Beim nächsten Start: Keine Authentifizierung mehr nötig! 🎉
