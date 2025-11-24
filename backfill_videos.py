#!/usr/bin/env python3
"""
Backfill script to re-process all existing videos
Adds summaries and transcripts without sending emails
"""

import sys
from youtube_summarizer import YouTubeSummarizer

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Video Nachbearbeitung")
    print("=" * 60)
    print("Dieses Script verarbeitet alle bereits bekannten Videos erneut")
    print("und fügt Zusammenfassungen + Transkripte hinzu.")
    print("E-Mails werden NICHT erneut versendet!")
    print("=" * 60)

    # Accept --yes flag to skip confirmation
    if "--yes" not in sys.argv:
        response = input("\nMöchtest du fortfahren? (j/n): ")
        if response.lower() not in ['j', 'ja', 'y', 'yes']:
            print("Abgebrochen.")
            exit(0)

    summarizer = YouTubeSummarizer()
    summarizer.backfill_existing_videos()

    print("\n✅ Fertig! Starte die Web-App neu um die Änderungen zu sehen.")
