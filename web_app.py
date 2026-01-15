#!/usr/bin/env python3
"""
YouTube Summarizer Web Interface
Provides OAuth authentication and video management dashboard
"""

import os

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import json
import pickle
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import anthropic

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
SCOPES = ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.readonly']
CREDENTIALS_FILE = Path('/data/credentials.json')
TOKEN_FILE = Path('/data/token.pickle')
STATE_FILE = Path('/data/processed_videos.json')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/oauth2callback')

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')


def markdown_to_html(text):
    """Convert simple markdown to HTML"""
    # Ersetze **text** mit <strong>text</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

    # Ersetze *text* mit <em>text</em>
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)

    # Ersetze # Überschrift mit <h3>
    text = re.sub(r'^# (.+)$', r'<h3 style="color: #f1f1f1; margin-top: 20px; margin-bottom: 10px; font-size: 18px;">\1</h3>', text, flags=re.MULTILINE)

    # Ersetze ## Überschrift mit <h4>
    text = re.sub(r'^## (.+)$', r'<h4 style="color: #ccc; margin-top: 15px; margin-bottom: 8px; font-size: 16px;">\1</h4>', text, flags=re.MULTILINE)

    # Ersetze GROSSBUCHSTABEN-Überschriften
    text = re.sub(r'^([A-ZÄÖÜ][A-ZÄÖÜ\s]+)$', r'<h3 style="color: #ff0000; margin-top: 20px; margin-bottom: 10px; font-size: 16px;">\1</h3>', text, flags=re.MULTILINE)

    # Verarbeite Listen (Zeilen die mit - beginnen)
    lines = text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul style="margin: 10px 0; padding-left: 20px;">')
                in_list = True
            html_lines.append(f'<li style="margin: 5px 0;">{stripped[2:]}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if stripped == '':
                html_lines.append('<br>')
            elif not stripped.startswith('<'):  # Nicht bereits HTML
                html_lines.append(f'<p style="margin: 8px 0; line-height: 1.6;">{line}</p>')
            else:
                html_lines.append(line)

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


# Register the filter for use in templates
app.jinja_env.filters['markdown_to_html'] = markdown_to_html


GERMAN_MONTHS = {
    1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
    5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
}


def group_videos_by_date(videos):
    """Group videos by date categories"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    groups = OrderedDict()
    groups['Heute'] = []
    groups['Gestern'] = []
    groups['Diese Woche'] = []

    # For older videos, group by month
    monthly_groups = {}

    for video in videos:
        date_str = video.get('processed_at', '')
        if not date_str or date_str == 'N/A':
            # Put videos without date in "Unbekannt"
            if 'Unbekannt' not in groups:
                groups['Unbekannt'] = []
            groups['Unbekannt'].append(video)
            continue

        try:
            # Parse the date (format: 2024-11-26 10:30:00 or similar)
            video_date = datetime.fromisoformat(date_str.replace(' ', 'T').split('.')[0]).date()

            if video_date == today:
                groups['Heute'].append(video)
            elif video_date == yesterday:
                groups['Gestern'].append(video)
            elif video_date > week_ago:
                groups['Diese Woche'].append(video)
            else:
                # Group by month with German month name
                month_name = GERMAN_MONTHS[video_date.month]
                month_key = f"{month_name} {video_date.year}"
                sort_key = f"{video_date.year}-{video_date.month:02d}"
                if month_key not in monthly_groups:
                    monthly_groups[month_key] = {'videos': [], 'sort_key': sort_key}
                monthly_groups[month_key]['videos'].append(video)
        except (ValueError, AttributeError):
            if 'Unbekannt' not in groups:
                groups['Unbekannt'] = []
            groups['Unbekannt'].append(video)

    # Remove empty default groups
    for key in ['Heute', 'Gestern', 'Diese Woche']:
        if not groups[key]:
            del groups[key]

    # Add monthly groups sorted by date (newest first)
    sorted_months = sorted(monthly_groups.items(),
                          key=lambda x: x[1]['sort_key'],
                          reverse=True)
    for month_name, data in sorted_months:
        groups[month_name] = data['videos']

    return groups


def load_processed_videos():
    """Load the processed videos state"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            # Handle old format (list of IDs) vs new format (dict with details)
            if isinstance(data, list):
                # Convert old format to new format
                return {video_id: {} for video_id in data}
            return data
    return {}


def get_youtube_service():
    """Get authenticated YouTube service"""
    if not TOKEN_FILE.exists():
        return None

    try:
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

        if not creds or not creds.valid:
            return None

        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None


@app.route('/')
def index():
    """Main dashboard"""
    youtube = get_youtube_service()

    if not youtube:
        return render_template('login.html')

    # Load processed videos
    processed = load_processed_videos()

    # Get video details (exclude removed videos)
    videos = []
    for video_id, data in processed.items():
        # Skip removed videos
        if data.get('status') == 'removed':
            continue

        # Skip archived videos (they go to /archive)
        if data.get('status') == 'archived':
            continue

        # If we don't have title, fetch from YouTube
        if not data.get('title'):
            try:
                response = youtube.videos().list(
                    part='snippet',
                    id=video_id
                ).execute()

                if response.get('items'):
                    snippet = response['items'][0]['snippet']
                    data['title'] = snippet.get('title', 'Unknown Title')
                    data['channel'] = snippet.get('channelTitle', 'Unknown Channel')
                    data['thumbnail'] = snippet.get('thumbnails', {}).get('medium', {}).get('url', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg')
            except Exception as e:
                print(f"Error fetching video {video_id}: {e}")
                data['title'] = 'Unknown Title'
                data['channel'] = 'Unknown Channel'

        videos.append({
            'id': video_id,
            'title': data.get('title', 'Unknown Title'),
            'channel': data.get('channel', 'Unknown Channel'),
            'processed_at': data.get('added_at') or data.get('processed_at', 'N/A'),
            'transcript': data.get('transcript', ''),
            'summary': data.get('summary', ''),
            'thumbnail': data.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg'),
            'read': data.get('read', False)
        })

    # Sort by added_at date (newest first), fallback to processed_at
    # Videos without dates go to the end
    def sort_key(video):
        date = video.get('processed_at', '')
        return date if date else '1970-01-01'  # Very old date for videos without timestamp

    videos.sort(key=sort_key, reverse=True)

    # Group videos by date
    grouped_videos = group_videos_by_date(videos)

    # Count unread videos
    unread_count = sum(1 for v in videos if not v.get('read'))

    return render_template('dashboard.html', grouped_videos=grouped_videos, total=len(videos), unread_count=unread_count)


@app.route('/login')
def login():
    """Start OAuth flow"""
    if not CREDENTIALS_FILE.exists():
        return """
        <h1>Error: credentials.json not found</h1>
        <p>Please add your OAuth2 credentials.json to /data/credentials.json</p>
        <p>See README for instructions.</p>
        """

    # Use configured redirect URI from environment
    redirect_uri = REDIRECT_URI

    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    session['state'] = state
    session['redirect_uri'] = redirect_uri  # Store for callback
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback"""
    try:
        state = session.get('state')
        redirect_uri = session.get('redirect_uri', REDIRECT_URI)

        print(f"OAuth callback - state: {state}")
        print(f"OAuth callback - redirect_uri: {redirect_uri}")
        print(f"OAuth callback - request.url: {request.url}")

        flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri
        )

        # Fix HTTPS/HTTP mismatch from reverse proxy
        authorization_response = request.url
        if authorization_response.startswith('http://') and 'localhost' not in authorization_response:
            authorization_response = authorization_response.replace('http://', 'https://', 1)
            print(f"OAuth callback - fixed URL: {authorization_response}")

        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        print(f"OAuth callback - got credentials, scopes: {credentials.scopes}")

        # Save credentials (pickle is used here as it's the existing pattern for OAuth tokens)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)

        print("OAuth callback - saved token successfully")
        return redirect(url_for('index'))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"OAuth callback ERROR: {e}")
        print(f"Traceback: {error_details}")
        return f"""
        <h1>OAuth Error</h1>
        <pre>{error_details}</pre>
        <p><a href="/login">Try again</a></p>
        """, 500


@app.route('/logout')
def logout():
    """Remove authentication"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    session.clear()
    return redirect(url_for('index'))


@app.route('/video/<video_id>')
def video_detail(video_id):
    """Show detailed view of a video"""
    youtube = get_youtube_service()
    if not youtube:
        return redirect(url_for('index'))

    processed = load_processed_videos()

    if video_id not in processed:
        return "Video not found", 404

    video = processed[video_id]

    # Mark video as read
    if not video.get('read'):
        video['read'] = True
        save_processed_videos(processed)

    # Get sorted list of active videos for navigation
    active_videos = []
    for vid, data in processed.items():
        if data.get('status') not in ['archived', 'removed']:
            date = data.get('added_at') or data.get('processed_at', '')
            active_videos.append((vid, date))

    # Sort by date (newest first)
    active_videos.sort(key=lambda x: x[1] if x[1] else '1970-01-01', reverse=True)
    video_ids = [v[0] for v in active_videos]

    # Find prev/next videos
    prev_video = None
    next_video = None
    try:
        current_idx = video_ids.index(video_id)
        if current_idx > 0:
            prev_video = video_ids[current_idx - 1]
        if current_idx < len(video_ids) - 1:
            next_video = video_ids[current_idx + 1]
    except ValueError:
        pass

    # Fetch video details from YouTube if not cached
    if not video.get('title'):
        try:
            response = youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if response.get('items'):
                snippet = response['items'][0]['snippet']
                video['title'] = snippet.get('title', 'Unknown Title')
                video['channel'] = snippet.get('channelTitle', 'Unknown Channel')
                video['thumbnail'] = snippet.get('thumbnails', {}).get('medium', {}).get('url', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg')
        except Exception as e:
            print(f"Error fetching video {video_id}: {e}")
            video['title'] = 'Unknown Title'
            video['channel'] = 'Unknown Channel'

    video['id'] = video_id

    return render_template('video_detail.html', video=video, prev_video=prev_video, next_video=next_video)


@app.route('/api/videos')
def api_videos():
    """API endpoint to get all videos"""
    processed = load_processed_videos()
    return jsonify(processed)


@app.route('/api/search')
def api_search():
    """Search videos by title or content"""
    query = request.args.get('q', '').lower()
    processed = load_processed_videos()

    results = []
    for video_id, data in processed.items():
        title = data.get('title', '').lower()
        transcript = data.get('transcript', '').lower()
        summary = data.get('summary', '').lower()

        if query in title or query in transcript or query in summary:
            results.append({
                'id': video_id,
                'title': data.get('title'),
                'channel': data.get('channel'),
                'processed_at': data.get('processed_at'),
                'thumbnail': data.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg')
            })

    return jsonify(results)


def save_processed_videos(data):
    """Save processed videos to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route('/api/video/<video_id>/archive', methods=['POST'])
def archive_video(video_id):
    """Archive a video"""
    processed = load_processed_videos()

    if video_id not in processed:
        return jsonify({'error': 'Video not found'}), 404

    processed[video_id]['status'] = 'archived'
    save_processed_videos(processed)

    return jsonify({'success': True, 'status': 'archived'})


@app.route('/api/video/<video_id>/remove', methods=['POST'])
def remove_video(video_id):
    """Mark a video as removed"""
    processed = load_processed_videos()

    if video_id not in processed:
        return jsonify({'error': 'Video not found'}), 404

    processed[video_id]['status'] = 'removed'
    save_processed_videos(processed)

    return jsonify({'success': True, 'status': 'removed'})


@app.route('/api/video/<video_id>/restore', methods=['POST'])
def restore_video(video_id):
    """Restore a video to active status"""
    processed = load_processed_videos()

    if video_id not in processed:
        return jsonify({'error': 'Video not found'}), 404

    processed[video_id]['status'] = 'active'
    save_processed_videos(processed)

    return jsonify({'success': True, 'status': 'active'})


@app.route('/archive')
def archive():
    """Show archived videos"""
    youtube = get_youtube_service()

    if not youtube:
        return render_template('login.html')

    # Load processed videos
    processed = load_processed_videos()

    # Get archived videos only
    videos = []
    for video_id, data in processed.items():
        # Filter for archived videos
        if data.get('status') != 'archived':
            continue

        # If we don't have title, fetch from YouTube
        if not data.get('title'):
            try:
                response = youtube.videos().list(
                    part='snippet',
                    id=video_id
                ).execute()

                if response.get('items'):
                    snippet = response['items'][0]['snippet']
                    data['title'] = snippet.get('title', 'Unknown Title')
                    data['channel'] = snippet.get('channelTitle', 'Unknown Channel')
                    data['thumbnail'] = snippet.get('thumbnails', {}).get('medium', {}).get('url', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg')
            except Exception as e:
                print(f"Error fetching video {video_id}: {e}")
                data['title'] = 'Unknown Title'
                data['channel'] = 'Unknown Channel'

        videos.append({
            'id': video_id,
            'title': data.get('title', 'Unknown Title'),
            'channel': data.get('channel', 'Unknown Channel'),
            'processed_at': data.get('added_at') or data.get('processed_at', 'N/A'),
            'transcript': data.get('transcript', ''),
            'summary': data.get('summary', ''),
            'thumbnail': data.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg')
        })

    # Sort by added_at date (newest first)
    def sort_key(video):
        date = video.get('processed_at', '')
        return date if date else '1970-01-01'

    videos.sort(key=sort_key, reverse=True)

    # Group videos by date
    grouped_videos = group_videos_by_date(videos)

    return render_template('archive.html', grouped_videos=grouped_videos, total=len(videos))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
