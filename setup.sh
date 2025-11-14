#!/bin/bash

echo "🎥 YouTube Playlist Summarizer - Setup"
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert!"
    echo "   Bitte installiere Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose ist nicht installiert!"
    echo "   Bitte installiere Docker Compose"
    exit 1
fi

echo "✅ Docker ist installiert"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Erstelle .env Datei..."
    cp .env.example .env
    echo "✅ .env Datei erstellt!"
    echo ""
    echo "⚠️  WICHTIG: Bearbeite jetzt die .env Datei mit deinen Credentials:"
    echo "   - CLAUDE_API_KEY"
    echo "   - RAPIDAPI_KEY"
    echo "   - EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD"
    echo "   - PLAYLIST_ID"
    echo ""
    read -p "Drücke Enter wenn du die .env Datei ausgefüllt hast..."
else
    echo "✅ .env Datei existiert bereits"
fi

# Check if credentials.json exists
if [ ! -f data/credentials.json ]; then
    echo ""
    echo "⚠️  YouTube OAuth Credentials fehlen!"
    echo ""
    echo "📋 So bekommst du die credentials.json:"
    echo "   1. Gehe zu https://console.cloud.google.com/"
    echo "   2. Erstelle ein neues Projekt"
    echo "   3. Aktiviere die 'YouTube Data API v3'"
    echo "   4. Erstelle OAuth 2.0 Credentials (Desktop app)"
    echo "   5. Lade die JSON-Datei herunter"
    echo "   6. Benenne sie um zu 'credentials.json'"
    echo "   7. Lege sie in den 'data/' Ordner"
    echo ""
    read -p "Drücke Enter wenn du credentials.json hinzugefügt hast..."

    if [ ! -f data/credentials.json ]; then
        echo "❌ credentials.json nicht gefunden in data/"
        echo "   Setup abgebrochen."
        exit 1
    fi
fi

echo ""
echo "✅ Alle Voraussetzungen erfüllt!"
echo ""
echo "🐳 Starte Docker Container..."
docker compose up -d --build

echo ""
echo "✅ Container gestartet!"
echo ""
echo "📋 Nächste Schritte:"
echo ""
echo "1. Beim ersten Start musst du OAuth authentifizieren:"
echo "   docker logs youtube-summarizer -f"
echo "   Folge den Anweisungen in den Logs"
echo ""
echo "2. Status prüfen:"
echo "   docker ps | grep youtube-summarizer"
echo ""
echo "3. Logs ansehen:"
echo "   docker logs youtube-summarizer -f"
echo ""
echo "4. Stoppen:"
echo "   docker compose down"
echo ""
echo "🎉 Setup abgeschlossen!"
