#!/usr/bin/env python3
"""Clear the last video entry so it can be reprocessed"""
import json

DATA_FILE = '/Users/jankutschera/dev/youtube-summarizer-oauth2/data/processed_videos.json'
VIDEO_ID = '99UKPcsiKF4'

# Load data
with open(DATA_FILE, 'r') as f:
    data = json.load(f)

# Clear the problematic video
if VIDEO_ID in data:
    print(f"Clearing entry for video: {VIDEO_ID}")
    print(f"Title: {data[VIDEO_ID].get('title', 'Unknown')}")
    data[VIDEO_ID]['transcript'] = ''
    data[VIDEO_ID]['summary'] = ''
    print("✅ Cleared transcript and summary")

    # Save
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Saved changes")
else:
    print(f"❌ Video {VIDEO_ID} not found in data")
