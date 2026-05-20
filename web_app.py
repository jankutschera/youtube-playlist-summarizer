#!/usr/bin/env python3
"""
YouTube Summarizer Web Interface
Provides OAuth authentication and video management dashboard
"""

import os

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

import json
import logging
import pickle
import re
from pathlib import Path
from flask import Flask, render_template, redirect, url_for, session, request, jsonify, Response
from markupsafe import escape
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

import database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
SCOPES = ['https://www.googleapis.com/auth/youtube']
CREDENTIALS_FILE = Path('/data/credentials.json')
TOKEN_FILE = Path('/data/token.pickle')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/oauth2callback')

# Initialize database on import
database.init_db()


def markdown_to_html(text):
    """Convert simple markdown to HTML (input is escaped first to prevent XSS)"""
    text = str(escape(text))
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
        log.error(f"Error loading credentials: {e}")
        return None


@app.route('/')
def index():
    """Main dashboard"""
    youtube = get_youtube_service()

    if not youtube:
        return render_template('login.html')

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    grouped_videos = database.get_videos_grouped_by_date(status='active')

    total = database.count_videos(status='active')
    unread_count = database.count_videos(status='active', read=0)

    return render_template('dashboard.html',
                         grouped_videos=grouped_videos,
                         total=total,
                         unread_count=unread_count,
                         page=page,
                         per_page=per_page)


@app.route('/login')
def login():
    """Start OAuth flow"""
    if not CREDENTIALS_FILE.exists():
        return """
        <h1>Error: credentials.json not found</h1>
        <p>Please add your OAuth2 credentials.json to /data/credentials.json</p>
        <p>See README for instructions.</p>
        """

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
    session['redirect_uri'] = redirect_uri
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback"""
    try:
        state = session.get('state')
        redirect_uri = session.get('redirect_uri', REDIRECT_URI)

        log.info(f"OAuth callback - state: {state}")
        log.info(f"OAuth callback - redirect_uri: {redirect_uri}")
        log.info(f"OAuth callback - request.url: {request.url}")

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
            log.info(f"OAuth callback - fixed URL: {authorization_response}")

        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        log.info(f"OAuth callback - got credentials, scopes: {credentials.scopes}")

        # Save credentials (pickle is used here as it's the existing pattern for OAuth tokens)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)

        log.info("OAuth callback - saved token successfully")
        return redirect(url_for('index'))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log.error(f"OAuth callback ERROR: {e}")
        log.error(f"Traceback: {error_details}")
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

    video = database.get_video(video_id)
    if not video:
        return "Video not found", 404

    # Mark video as read
    if not video.get('read'):
        database.save_video(video_id, read=1)
        video['read'] = 1

    # Get sorted list of active videos for navigation
    active_videos = database.get_videos(status='active', limit=10000)
    video_ids = [v['id'] for v in active_videos]

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

    return render_template('video_detail.html', video=video, prev_video=prev_video, next_video=next_video)


@app.route('/api/videos')
def api_videos():
    """API endpoint to list videos (without transcript/summary for performance)"""
    status = request.args.get('status', 'active')
    if status == 'all':
        status = None
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    videos = database.get_videos(status=status, limit=limit, offset=offset)
    # Strip heavy fields for list view
    for v in videos:
        v.pop('transcript', None)
        v.pop('summary', None)
    return jsonify(videos)


@app.route('/api/video/<video_id>')
def api_video_detail(video_id):
    """API endpoint to get a single video with full summary and transcript"""
    video = database.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    return jsonify(video)


@app.route('/api/video/<video_id>/download')
def download_video_md(video_id):
    """Download video transcript and summary as Markdown file"""
    video = database.get_video(video_id)
    if not video:
        return "Video not found", 404

    lines = [
        f"# {video['title']}",
        "",
        f"**Channel:** {video.get('channel', 'Unknown')}",
        f"**Added:** {video.get('added_at', 'N/A')}",
        f"**YouTube:** https://youtube.com/watch?v={video['id']}",
        "",
    ]

    if video.get('summary'):
        lines.extend(["---", "", "## Summary", "", video['summary'], ""])

    if video.get('transcript'):
        lines.extend(["---", "", "## Transcript", "", video['transcript'], ""])

    content = "\n".join(lines)
    safe_title = re.sub(r'[^\w\s-]', '', video['title'])[:80].strip()
    filename = f"{safe_title}.md"

    return Response(
        content,
        mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@app.route('/api/status')
def api_status():
    """Health endpoint returning worker status"""
    status_file = Path('/data/worker_status.json')
    worker_status = {}
    if status_file.exists():
        with open(status_file, 'r') as f:
            worker_status = json.load(f)

    quota_used = int(database.get_setting('quota_used', '0'))
    quota_date = database.get_setting('quota_date', '')

    return jsonify({
        'worker': worker_status,
        'videos': {
            'total': database.count_videos(),
            'active': database.count_videos(status='active'),
        },
        'quota': {
            'used': quota_used,
            'limit': 10000,
            'date': quota_date,
        }
    })


@app.route('/api/search')
def api_search():
    """Search videos by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    status = request.args.get('status', 'active')
    results = database.search_videos(query, status=status)
    # Strip heavy fields, add snippet instead
    for v in results:
        v.pop('transcript', None)
        summary = v.pop('summary', '') or ''
        # Include first 200 chars of summary as snippet
        v['summary_snippet'] = summary[:200] + '...' if len(summary) > 200 else summary
    return jsonify(results)


@app.route('/api/video/<video_id>/archive', methods=['POST'])
def archive_video(video_id):
    """Archive a video"""
    video = database.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    database.save_video(video_id, status='archived')
    return jsonify({'success': True, 'status': 'archived'})


@app.route('/api/video/<video_id>/remove', methods=['POST'])
def remove_video(video_id):
    """Mark a video as removed"""
    video = database.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    database.save_video(video_id, status='removed')
    return jsonify({'success': True, 'status': 'removed'})


@app.route('/api/video/<video_id>/restore', methods=['POST'])
def restore_video(video_id):
    """Restore a video to active status"""
    video = database.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    database.save_video(video_id, status='active')
    return jsonify({'success': True, 'status': 'active'})


@app.route('/archive')
def archive():
    """Show archived videos"""
    youtube = get_youtube_service()

    if not youtube:
        return render_template('login.html')

    grouped_videos = database.get_videos_grouped_by_date(status='archived')
    total = database.count_videos(status='archived')

    return render_template('archive.html', grouped_videos=grouped_videos, total=total)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
