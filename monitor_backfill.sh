#!/bin/bash

# Monitor the backfill progress by watching the processed_videos.json file

echo "🔄 Backfill-Monitor gestartet"
echo "================================"
echo ""

INITIAL_COUNT=$(docker compose exec -T youtube-summarizer python3 -c "import json; data=json.load(open('/data/processed_videos.json')); print(sum(1 for v in data.values() if isinstance(v, dict) and v.get('summary')))" 2>/dev/null)

echo "Videos mit Zusammenfassung: $INITIAL_COUNT"
echo ""
echo "Überwache Fortschritt (alle 30 Sekunden)..."
echo "Drücke Ctrl+C zum Beenden"
echo ""

while true; do
    sleep 30
    CURRENT_COUNT=$(docker compose exec -T youtube-summarizer python3 -c "import json; data=json.load(open('/data/processed_videos.json')); print(sum(1 for v in data.values() if isinstance(v, dict) and v.get('summary')))" 2>/dev/null)
    DIFF=$((CURRENT_COUNT - INITIAL_COUNT))
    echo "$(date '+%H:%M:%S') - Videos mit Zusammenfassung: $CURRENT_COUNT (+$DIFF)"
done
