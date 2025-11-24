#!/bin/bash

echo "=================================="
echo "YouTube Video Nachbearbeitung"
echo "=================================="
echo ""
echo "Dieses Script verarbeitet alle Videos aus deiner Watch Later Liste"
echo "und fügt Zusammenfassungen + Transkripte zur Datenbank hinzu."
echo ""
echo "⚠️  WICHTIG:"
echo "  - E-Mails werden NICHT erneut versendet"
echo "  - Es werden 84 Videos verarbeitet (ca. 1 Stunde bei 45s pro Video)"
echo "  - Claude API wird verwendet (kostenpflichtig)"
echo ""
read -p "Möchtest du fortfahren? (j/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[JjYy]$ ]]
then
    echo "Abgebrochen."
    exit 1
fi

echo ""
echo "🚀 Starte Nachbearbeitung im Docker Container..."
echo ""

docker compose exec youtube-summarizer python3 backfill_videos.py
