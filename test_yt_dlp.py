#!/usr/bin/env python3
"""
Test script to check if yt-dlp can download subtitles
"""

import yt_dlp
import tempfile
import os

video_id = 'di3MKU0-xGE'  # Dr. Richard Socher
video_url = f'https://www.youtube.com/watch?v={video_id}'

print(f"Testing video: {video_id}")
print(f"URL: {video_url}")
print("-" * 60)

with tempfile.TemporaryDirectory() as temp_dir:
    subtitle_file = os.path.join(temp_dir, f'{video_id}')

    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['de'],
        'skip_download': True,
        'outtmpl': subtitle_file,
        'subtitlesformat': 'vtt',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        print("Downloading subtitles...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        subtitle_path = f'{subtitle_file}.de.vtt'
        if os.path.exists(subtitle_path):
            print(f"✅ SUCCESS! Subtitle file created: {subtitle_path}")
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Subtitle file size: {len(content)} bytes")
            print(f"First 200 characters:\n{content[:200]}")
        else:
            print(f"❌ Subtitle file not found at: {subtitle_path}")
            print(f"Files in temp dir: {os.listdir(temp_dir)}")

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\nTest complete")
