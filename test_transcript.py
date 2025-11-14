#!/usr/bin/env python3
"""
Test script to check if transcripts are available for specific videos
"""

from youtube_transcript_api import YouTubeTranscriptApi

# Test with the video IDs from your playlist
video_ids = [
    'di3MKU0-xGE',  # Dr. Richard Socher
    '0iWAugxM2ok',  # Go from a Cursor
    's2_hdIXW5UU',  # Best Way To Organize
]

for video_id in video_ids:
    print(f"\n{'='*60}")
    print(f"Testing Video ID: {video_id}")
    print(f"{'='*60}")

    try:
        # Try to get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"✅ SUCCESS! Found transcript with {len(transcript)} entries")
        print(f"First entry: {transcript[0] if transcript else 'None'}")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("Test complete")
