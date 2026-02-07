#!/usr/bin/env python3
"""
One-time migration: processed_videos.json -> SQLite database.
Run inside the container: python3 migrate_to_sqlite.py
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

import database

JSON_FILE = Path('/data/processed_videos.json')
BACKUP_FILE = Path('/data/processed_videos.json.bak')


def migrate():
    if not JSON_FILE.exists():
        print("No processed_videos.json found, nothing to migrate.")
        return

    with open(JSON_FILE, 'r') as f:
        data = json.load(f)

    # Handle old format (list of IDs)
    if isinstance(data, list):
        data = {video_id: {} for video_id in data}

    print(f"Found {len(data)} videos in JSON file.")

    # Initialize database
    database.init_db()

    migrated = 0
    skipped = 0
    for video_id, info in data.items():
        if database.is_processed(video_id):
            skipped += 1
            continue

        database.save_video(
            video_id,
            title=info.get('title', ''),
            channel=info.get('channel', 'Unknown'),
            thumbnail=info.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg'),
            added_at=info.get('added_at', ''),
            processed_at=info.get('processed_at', ''),
            transcript=info.get('transcript', ''),
            summary=info.get('summary', ''),
            status=info.get('status', 'active'),
            read=1 if info.get('read') else 0,
        )
        migrated += 1

    # Verify
    total_in_db = database.count_videos()
    print(f"Migration complete: {migrated} migrated, {skipped} skipped (already existed).")
    print(f"Total videos in SQLite: {total_in_db}")
    print(f"Total videos in JSON:   {len(data)}")

    if total_in_db >= len(data):
        # Backup JSON file
        shutil.copy2(JSON_FILE, BACKUP_FILE)
        print(f"JSON backed up to {BACKUP_FILE}")
    else:
        print("WARNING: Row count mismatch! JSON file NOT backed up.")


if __name__ == '__main__':
    migrate()
