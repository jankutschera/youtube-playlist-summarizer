#!/usr/bin/env python3
"""
YouTube Watch Later Summarizer with OAuth2
Checks your Watch Later playlist and sends email summaries of new videos
"""

import os
import time
import json
import logging
import smtplib
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

import anthropic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import database

# YouTube OAuth2 Scopes - wir brauchen Schreibzugriff um Videos aus Playlist zu entfernen
SCOPES = ['https://www.googleapis.com/auth/youtube']


class YouTubeSummarizer:
    def __init__(self):
        # Load config
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_to = os.getenv('EMAIL_TO')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '30'))
        self.playlist_id = os.getenv('PLAYLIST_ID', 'WL')  # Default: Watch Later
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
        
        # OAuth2 credentials files
        self.credentials_file = Path('/data/credentials.json')
        self.token_file = Path('/data/token.pickle')
        
        # Initialize APIs
        self.youtube = self.get_authenticated_service()
        self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)

        # Initialize SQLite database
        database.init_db()

        # Quota tracking
        self.daily_quota_limit = 10000
        self._init_quota()

    def _init_quota(self):
        """Initialize or reset daily quota counter."""
        today = datetime.now().strftime('%Y-%m-%d')
        stored_date = database.get_setting('quota_date')
        if stored_date != today:
            database.set_setting('quota_date', today)
            database.set_setting('quota_used', '0')

    def _add_quota(self, units):
        """Add quota units and check thresholds."""
        self._init_quota()  # Reset if new day
        current = int(database.get_setting('quota_used', '0'))
        new_total = current + units
        database.set_setting('quota_used', str(new_total))

        pct = new_total / self.daily_quota_limit * 100
        if pct >= 95:
            log.error(f"🚨 YouTube API quota at {pct:.0f}% ({new_total}/{self.daily_quota_limit}) - PAUSING")
            return False  # Signal to stop processing
        elif pct >= 80:
            log.warning(f"⚠️  YouTube API quota at {pct:.0f}% ({new_total}/{self.daily_quota_limit})")
        return True

    def _quota_available(self):
        """Check if we have quota remaining."""
        self._init_quota()
        current = int(database.get_setting('quota_used', '0'))
        return current < (self.daily_quota_limit * 0.95)

    def get_authenticated_service(self):
        """Authenticate with YouTube using OAuth2"""
        creds = None
        
        # Load existing credentials
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                log.info("🔄 Token abgelaufen, erneuere...")
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    log.error("❌ FEHLER: credentials.json nicht gefunden!")
                    log.info("📝 Bitte lade deine OAuth2 credentials.json herunter und lege sie nach /data/credentials.json")
                    log.info("📖 Siehe README für Anleitung!")
                    raise FileNotFoundError("credentials.json fehlt in /data/")
                
                log.info("🔐 Erste Authentifizierung erforderlich!")
                log.info("=" * 60)

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file),
                    SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )

                # Manual OAuth flow (Docker-friendly)
                auth_url, _ = flow.authorization_url(
                    prompt='consent',
                    access_type='offline'
                )

                log.info("\n📋 SCHRITT 1: Öffne diese URL in deinem Browser:")
                log.info("-" * 60)
                log.info(auth_url)
                log.info("-" * 60)

                log.info("\n📋 SCHRITT 2: Nach der Anmeldung bekommst du einen CODE angezeigt.")
                log.info("Kopiere diesen CODE (eine lange Zeichenkette).\n")

                auth_code = input("🔑 Füge den CODE hier ein und drücke Enter: ").strip()

                # Exchange code for credentials
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            
            log.info("✅ Authentifizierung erfolgreich!")
        
        service = build('youtube', 'v3', credentials=creds)

        # Debug: Zeige verbundenen Account
        try:
            channel_request = service.channels().list(
                part='snippet',
                mine=True
            )
            channel_response = channel_request.execute()
            if channel_response.get('items'):
                channel_title = channel_response['items'][0]['snippet']['title']
                log.info(f"✅ Verbunden mit YouTube Account: {channel_title}")
        except Exception as e:
            log.warning(f"⚠️  Konnte Account-Info nicht abrufen: {e}")

        return service
    
    def get_watch_later_videos(self):
        """Get videos from configured playlist"""
        try:
            log.info(f"🔍 Versuche Playlist abzurufen...")
            log.info(f"🔍 Verwende Playlist ID: {self.playlist_id}")

            # Get ALL playlist items with pagination
            all_items = []
            next_page_token = None

            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=self.playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                self._add_quota(1)  # playlistItems.list = 1 unit

                all_items.extend(response.get('items', []))
                next_page_token = response.get('nextPageToken')

                if not next_page_token:
                    break

            log.info(f"🔍 API Response erhalten. Keys: {list(response.keys())}")
            log.info(f"🔍 Total Results: {response.get('pageInfo', {}).get('totalResults', 'unknown')}")
            log.info(f"🔍 Total Videos geholt mit Pagination: {len(all_items)}")

            videos = []
            items = all_items
            log.info(f"🔍 Items in Response: {len(items)}")

            for item in items:
                video_id = item['contentDetails']['videoId']
                title = item['snippet']['title']
                # publishedAt ist das Datum, wann das Video zur Playlist hinzugefügt wurde
                added_at = item['snippet']['publishedAt']
                # playlist_item_id wird benötigt um Videos aus der Playlist zu entfernen
                playlist_item_id = item['id']
                videos.append({
                    'id': video_id,
                    'title': title,
                    'added_at': added_at,
                    'playlist_item_id': playlist_item_id
                })

            log.info(f"📊 API hat {len(videos)} Videos in Watch Later gefunden")
            return videos
        except Exception as e:
            log.error(f"❌ Fehler beim Abrufen der Watch Later Liste: {e}")
            import traceback
            traceback.print_exc()
            return []

    def remove_from_playlist(self, playlist_item_id, title):
        """Remove a video from the playlist after successful processing"""
        try:
            self.youtube.playlistItems().delete(id=playlist_item_id).execute()
            self._add_quota(50)  # playlistItems.delete = 50 units
            log.info(f"🗑️  Video aus Playlist entfernt: {title[:50]}...")
            return True
        except Exception as e:
            log.warning(f"⚠️  Konnte Video nicht aus Playlist entfernen: {e}")
            return False

    def get_transcript_rapidapi(self, video_id):
        """Fallback: Get transcript using RapidAPI YT API (requires API keys)"""
        import requests

        # Support multiple RapidAPI keys (comma-separated in .env)
        rapidapi_keys = os.getenv('RAPIDAPI_KEYS', '').split(',')
        rapidapi_keys = [key.strip() for key in rapidapi_keys if key.strip()]

        if not rapidapi_keys:
            log.error(f"❌ Keine RapidAPI Keys konfiguriert")
            return None

        # Try each API key in rotation
        for i, api_key in enumerate(rapidapi_keys):
            try:
                log.info(f"🔄 Versuche RapidAPI (Key {i+1}/{len(rapidapi_keys)})...")

                # Use YT API endpoint for subtitles/captions
                url = "https://yt-api.p.rapidapi.com/subtitles"

                querystring = {"id": video_id}

                headers = {
                    "x-rapidapi-key": api_key,
                    "x-rapidapi-host": "yt-api.p.rapidapi.com"
                }

                response = requests.get(url, headers=headers, params=querystring, timeout=30)

                if response.status_code == 200:
                    data = response.json()

                    # YT API returns subtitles in different formats
                    # Try to extract text from the response
                    if isinstance(data, dict):
                        # If it has subtitles array
                        if 'subtitles' in data and data['subtitles']:
                            # Get first available subtitle track
                            subtitle_track = data['subtitles'][0]

                            # Check if we have a URL to fetch transcript from
                            if 'url' in subtitle_track:
                                log.info(f"🔄 Lade Transkript von URL...")
                                try:
                                    transcript_response = requests.get(subtitle_track['url'], timeout=30)
                                    if transcript_response.status_code == 200:
                                        # Parse XML format (srv1, srv2, srv3)
                                        import xml.etree.ElementTree as ET
                                        root = ET.fromstring(transcript_response.text)

                                        # Extract text from all <text> elements
                                        texts = []
                                        for text_elem in root.findall('.//text'):
                                            text_content = text_elem.text
                                            if text_content:
                                                texts.append(text_content)

                                        if texts:
                                            full_text = ' '.join(texts)
                                        else:
                                            log.error(f"❌ RapidAPI: Keine Texte in XML gefunden")
                                            continue
                                    else:
                                        log.error(f"❌ RapidAPI: URL request failed: {transcript_response.status_code}")
                                        continue
                                except Exception as url_error:
                                    log.error(f"❌ RapidAPI: Fehler beim Laden von URL: {url_error}")
                                    continue

                            # Fallback: Check for direct text/segments (old format)
                            elif 'text' in subtitle_track:
                                full_text = subtitle_track['text']
                            elif 'segments' in subtitle_track:
                                full_text = ' '.join([seg.get('text', '') for seg in subtitle_track['segments']])
                            else:
                                log.error(f"❌ RapidAPI: Unbekanntes Subtitles Format")
                                log.info(f"Subtitle keys: {list(subtitle_track.keys())}")
                                continue
                        elif 'text' in data:
                            full_text = data['text']
                        else:
                            log.error(f"❌ RapidAPI: Kein Transkript in Response gefunden")
                            log.info(f"Response keys: {list(data.keys())}")
                            continue
                    elif isinstance(data, list) and len(data) > 0:
                        # If it's an array of text segments
                        full_text = ' '.join([item.get('text', str(item)) for item in data])
                    else:
                        log.error(f"❌ RapidAPI: Unexpected response format: {type(data)}")
                        continue

                    # Clean up extra whitespace
                    import re
                    full_text = re.sub(r'\s+', ' ', full_text).strip()

                    if full_text:
                        log.info(f"✅ Transkript via RapidAPI erhalten: {len(full_text)} Zeichen")
                        return full_text
                    else:
                        log.error(f"❌ RapidAPI: Transkript ist leer")
                        continue

                elif response.status_code == 429:
                    log.warning(f"⚠️  RapidAPI Key {i+1} hat Rate Limit erreicht, versuche nächsten...")
                    continue
                elif response.status_code == 403:
                    log.warning(f"⚠️  RapidAPI Key {i+1}: Nicht für diese API subscribed")
                    continue
                else:
                    log.error(f"❌ RapidAPI Error {response.status_code}: {response.text[:100]}")
                    continue

            except Exception as e:
                log.error(f"❌ RapidAPI Fehler mit Key {i+1}: {e}")
                import traceback
                traceback.print_exc()
                continue

        log.error(f"❌ Alle RapidAPI Keys erschöpft")
        return None

    def get_transcript(self, video_id):
        """Get transcript with fallback: youtube-transcript-api -> RapidAPI"""
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

        # PRIMARY: Try youtube-transcript-api (free, no rate limits)
        try:
            log.info(f"🔍 Versuche Transkript für Video {video_id} abzurufen...")

            # Use the NEW API (v1.2+) with proper instantiation
            ytt_api = YouTubeTranscriptApi()

            # Try to fetch transcript in German first, then English
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=['de', 'en'])
                lang_name = fetched_transcript.language
                log.info(f"📥 Transkript gefunden ({lang_name})...")

                # Convert FetchedTranscript to raw data (list of dicts)
                transcript_list = fetched_transcript.to_raw_data()

            except NoTranscriptFound:
                log.warning(f"⚠️  youtube-transcript-api: Kein Transkript in DE/EN gefunden, versuche RapidAPI...")
                return self.get_transcript_rapidapi(video_id)

            # Combine all transcript segments
            full_text = ' '.join([item['text'] for item in transcript_list])

            # Clean up extra whitespace
            import re
            full_text = re.sub(r'\s+', ' ', full_text).strip()

            if not full_text:
                log.warning(f"⚠️  Transkript ist leer, versuche RapidAPI...")
                return self.get_transcript_rapidapi(video_id)

            log.info(f"✅ Transkript verarbeitet: {len(full_text)} Zeichen")
            return full_text

        except TranscriptsDisabled:
            log.warning(f"⚠️  Transkripte deaktiviert via youtube-transcript-api, versuche RapidAPI...")
            return self.get_transcript_rapidapi(video_id)

        except NoTranscriptFound:
            log.warning(f"⚠️  Kein Transkript via youtube-transcript-api, versuche RapidAPI...")
            return self.get_transcript_rapidapi(video_id)

        except Exception as e:
            error_msg = str(e)
            if "no longer available" in error_msg or "VideoUnavailable" in str(type(e)):
                log.warning(f"⚠️  Video nicht verfügbar via youtube-transcript-api, versuche RapidAPI...")
                return self.get_transcript_rapidapi(video_id)
            else:
                log.error(f"❌ Unerwarteter Fehler: {e}")
                import traceback
                traceback.print_exc()
                log.warning(f"⚠️  Versuche RapidAPI als Fallback...")
                return self.get_transcript_rapidapi(video_id)
    
    def calculate_max_tokens(self, title):
        """Berechne max_tokens dynamisch basierend auf Titel"""
        import re

        # Suche nach Zahlen im Titel (z.B. "17 Hacks", "25 Tips")
        numbers = re.findall(r'\b(\d+)\b', title)

        if numbers:
            max_num = max([int(n) for n in numbers])

            # Dynamische Anpassung:
            if max_num >= 25:
                return 10000  # Für "25+ Tips/Hacks"
            elif max_num >= 20:
                return 8000   # Für "20-24 Tips"
            elif max_num >= 15:
                return 6000   # Für "15-19 Tips"
            elif max_num >= 10:
                return 5000   # Für "10-14 Tips"

        # Standard für Videos ohne große Listen
        return 4000

    def create_bullet_summary(self, title, transcript):
        """Create quick bullet-point summary with emojis

        Returns:
            tuple: (success: bool, summary: str)
        """
        import time

        prompt = f"""Fasse das folgende YouTube-Video-Transkript in prägnante Bullet-Points zusammen.
Wähle für jeden Punkt ein passendes Emoji am Anfang.
Antworte auf Deutsch.

Video-Titel: {title}

Transkript:
{transcript[:15000]}

REGELN:
- Jeder Bullet-Point beginnt mit einem passenden Emoji
- Maximal 15-25 Bullet-Points
- Jeder Punkt ist 1 kurzer Satz (max 15 Wörter)
- Fokussiere auf die wichtigsten Erkenntnisse und Takeaways
- Keine Überschriften, nur Bullet-Points
- Format: EMOJI Kurztext

Beispiel-Output:
⏳ Wir haben nicht alle die gleichen "24 Stunden" - Ressourcen und Teams unterscheiden sich.
⚡ Der Schlüssel ist Aktivierungsenergie, nicht Motivation oder Disziplin.
🚀 Der schwierigste Teil ist das Anfangen, nicht das Durchhalten.
☀️ Morgenlicht-Therapie: 10.000-Lux-Lampe innerhalb 30 Min nach dem Aufwachen."""

        max_retries = 3
        base_delay = 10

        for attempt in range(max_retries):
            try:
                message = self.claude_client.messages.create(
                    model=self.claude_model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return (True, message.content[0].text)
            except Exception as e:
                error_str = str(e)
                if "overloaded" in error_str.lower() or "529" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt)
                        log.warning(f"⚠️ Claude API überlastet. Warte {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                log.error(f"❌ Bullet-Summary fehlgeschlagen: {e}")
                return (False, "")

    def summarize_with_claude(self, title, transcript):
        """Create summary using Claude

        Returns:
            tuple: (success: bool, summary: str)
                - success: True if summarization succeeded, False if it failed
                - summary: The summary text (or error message if failed)
        """
        import re

        # STEP 1: Create quick bullet-point summary with emojis
        log.info("📝 Erstelle Quick-Scan (Bullet-Points)...")
        bullet_success, bullet_summary = self.create_bullet_summary(title, transcript)

        # STEP 2: Create detailed summary
        log.info("📄 Erstelle detaillierte Zusammenfassung...")

        # Extrahiere Zahlen aus dem Titel um zu prüfen ob es ein Listen-Video ist
        numbers = re.findall(r'\b(\d+)\b', title)
        is_list_video = False
        required_points = 0

        if numbers:
            # Nimm die größte Zahl (meist die Anzahl der Tipps/Hacks)
            max_num = max([int(n) for n in numbers])
            # Nur Zahlen zwischen 5 und 100 zählen als Listen
            if 5 <= max_num <= 100:
                is_list_video = True
                required_points = max_num

        # Baue spezielle Instruktion für Listen-Videos
        list_instruction = ""
        if is_list_video:
            list_instruction = f"""
⚠️ KRITISCH: Dieses Video ist ein Listen-Video mit {required_points} Punkten!
Du MUSST unter KERNPUNKTE genau {required_points} Punkte auflisten - NICHT WENIGER!
Zähle die Punkte von 1 bis {required_points}.
Wenn du weniger als {required_points} Punkte auflistest, ist die Zusammenfassung UNVOLLSTÄNDIG und FALSCH!
"""

        prompt = f"""Bitte erstelle eine Zusammenfassung dieses YouTube-Videos für eine Email.

Video-Titel: {title}

Transkript:
{transcript[:15000]}  # Limit to avoid token limits

WICHTIG: Formatiere die Zusammenfassung als PLAIN TEXT ohne Markdown!
Nutze nur einfache Textformatierung:
- Für Überschriften: GROSSBUCHSTABEN und Leerzeilen
- Für Listen: Einfache Bindestriche (-)
- Keine #, **, *, ~~, etc.
{list_instruction}

Erstelle eine Zusammenfassung mit:

1. SCHNELLÜBERSICHT (2-3 Sätze)
   → Was LERNE ich konkret in diesem Video?
   → Was sind die wichtigsten ERKENNTNISSE oder TAKEAWAYS?
   → Nicht nur beschreiben, sondern die Kernbotschaft erklären!

2. HAUPTTHEMA (2-3 Sätze)
   → Kontext und Hintergrund ausführlicher erklären
   → Warum ist dieses Thema relevant?

3. KERNPUNKTE{f"   → Dies ist ein Listen-Video! Du musst ALLE {required_points} Punkte einzeln auflisten (1. bis {required_points}.)!" if is_list_video else "   → Bei Listen-Videos: ALLE Punkte! Bei normalen Videos: 5-7 Hauptpunkte"}
   → Jeder Punkt 1-2 Sätze mit Details
   → Verwende Nummerierung (1., 2., 3., ...)

4. FAZIT (2-3 Sätze)
   → Zusammenfassung und praktische Relevanz
   → Was sollte ich als nächstes tun?

Format-Beispiel für Listen-Video:
=================================
SCHNELLÜBERSICHT
In diesem Video lernst du 10 konkrete Strategien, um deine Produktivität zu verdoppeln. Die wichtigsten Erkenntnisse: Zeit-Blocking ist effektiver als To-Do-Listen, und kurze Pausen erhöhen die Konzentration nachweislich.

HAUPTTHEMA
Produktivität ist nicht nur eine Frage der Zeitverwaltung, sondern auch der mentalen Energie...

KERNPUNKTE
1. Zeit-Blocking: Plane feste Zeitblöcke für Aufgaben statt vage To-Do-Listen...
2. Pomodoro-Technik: 25 Minuten fokussierte Arbeit, 5 Minuten Pause...
3. Digital Detox: Handy in den Flugmodus während wichtiger Aufgaben...
[... alle 10 Punkte auflisten ...]

FAZIT
Die Strategien zeigen, dass kleine Änderungen große Wirkung haben können...
================================="""

        import time

        # Dynamische Token-Berechnung basierend auf Titel
        max_tokens = self.calculate_max_tokens(title)
        log.info(f"🎯 Max Tokens für '{title}': {max_tokens}")

        # Retry-Logik mit exponential backoff für Overloaded Errors
        max_retries = 3
        base_delay = 10  # Sekunden

        for attempt in range(max_retries):
            try:
                message = self.claude_client.messages.create(
                    model=self.claude_model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                detailed_summary = message.content[0].text

                # Combine both summaries: Quick Scan first, then detailed
                if bullet_success and bullet_summary:
                    combined_summary = f"""QUICK SCAN
{'=' * 40}
{bullet_summary}

{'=' * 40}
AUSFÜHRLICHE ZUSAMMENFASSUNG
{'=' * 40}

{detailed_summary}"""
                else:
                    combined_summary = detailed_summary

                return (True, combined_summary)

            except Exception as e:
                error_str = str(e)

                # Check if it's an overloaded error (529)
                if "overloaded" in error_str.lower() or "529" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                        log.warning(f"⚠️ Claude API überlastet (529). Warte {wait_time} Sekunden vor Retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        log.error(f"❌ Claude API überlastet nach {max_retries} Versuchen")
                        return (False, f"Zusammenfassung konnte nicht erstellt werden. Claude API ist überlastet. Bitte später erneut versuchen.")

                log.error(f"❌ Fehler bei {self.claude_model}: {e}")
                try:
                    log.info("🔄 Versuche mit 'claude-sonnet-4-latest'...")
                    message = self.claude_client.messages.create(
                        model="claude-sonnet-4-latest",
                        max_tokens=max_tokens,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    detailed_summary = message.content[0].text

                    # Combine both summaries
                    if bullet_success and bullet_summary:
                        combined_summary = f"""QUICK SCAN
{'=' * 40}
{bullet_summary}

{'=' * 40}
AUSFÜHRLICHE ZUSAMMENFASSUNG
{'=' * 40}

{detailed_summary}"""
                    else:
                        combined_summary = detailed_summary

                    return (True, combined_summary)
                except Exception as e2:
                    log.error(f"❌ Fallback fehlgeschlagen: {e2}")
                    return (False, f"Zusammenfassung konnte nicht erstellt werden. API Fehler: {e}")
    
    def is_recently_added(self, added_at_str, days=7):
        """Check if video was added to playlist within the last N days"""
        try:
            # Parse ISO 8601 format from YouTube API (z.B. "2024-11-01T10:30:00Z")
            added_at = datetime.fromisoformat(added_at_str.replace('Z', '+00:00'))
            # Remove timezone info for comparison
            added_at = added_at.replace(tzinfo=None)
            now = datetime.utcnow()
            age = now - added_at
            return age <= timedelta(days=days)
        except Exception as e:
            log.warning(f"⚠️  Konnte Datum nicht parsen: {e}")
            return False

    def markdown_to_html(self, text):
        """Convert simple markdown to HTML"""
        import re

        # Ersetze **text** mit <strong>text</strong>
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

        # Ersetze *text* mit <em>text</em>
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)

        # Ersetze # Überschrift mit <h3>
        text = re.sub(r'^# (.+)$', r'<h3 style="color: #333; margin-top: 20px; margin-bottom: 10px;">\1</h3>', text, flags=re.MULTILINE)

        # Ersetze ## Überschrift mit <h4>
        text = re.sub(r'^## (.+)$', r'<h4 style="color: #555; margin-top: 15px; margin-bottom: 8px;">\1</h4>', text, flags=re.MULTILINE)

        # Ersetze GROSSBUCHSTABEN-Überschriften
        text = re.sub(r'^([A-ZÄÖÜ][A-ZÄÖÜ\s]+)$', r'<h3 style="color: #FF0000; margin-top: 20px; margin-bottom: 10px; font-size: 16px;">\1</h3>', text, flags=re.MULTILINE)

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
                    html_lines.append(f'<p style="margin: 8px 0;">{line}</p>')
                else:
                    html_lines.append(line)

        if in_list:
            html_lines.append('</ul>')

        return '\n'.join(html_lines)

    def send_email(self, video_title, video_id, summary):
        """Send email with summary"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📺 YouTube Zusammenfassung: {video_title}"
            msg['From'] = self.email_from
            msg['To'] = self.email_to

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            # YouTube Thumbnail URL - maxresdefault für beste Qualität
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

            # Konvertiere Markdown zu HTML
            summary_html = self.markdown_to_html(summary)

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                  <h2 style="color: #FF0000; margin-top: 0;">📺 {video_title}</h2>

                  <!-- Video Thumbnail -->
                  <div style="margin: 20px 0;">
                    <a href="{video_url}" style="display: block; text-decoration: none;">
                      <img src="{thumbnail_url}" alt="{video_title}" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                    </a>
                  </div>

                  <p><a href="{video_url}" style="color: #065fd4; text-decoration: none; font-weight: bold; font-size: 16px;">▶️ Video ansehen auf YouTube</a></p>
                  <hr style="border: none; border-top: 2px solid #eee; margin: 20px 0;">
                  <div style="line-height: 1.8; color: #333;">
{summary_html}
                  </div>
                  <hr style="border: none; border-top: 2px solid #eee; margin: 20px 0;">
                  <p style="color: #999; font-size: 12px; text-align: center; margin-bottom: 0;">Automatisch generiert von deinem YouTube Watch Later Bot 🤖</p>
                </div>
              </body>
            </html>
            """

            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)

            log.info(f"✅ Email gesendet für: {video_title}")
            return True

        except Exception as e:
            log.error(f"❌ Fehler beim Email-Versand: {e}")
            return False
    
    def write_worker_status(self, videos_in_queue=0):
        """Write worker status for health endpoint"""
        status = {
            'last_run': datetime.now().isoformat(),
            'videos_in_queue': videos_in_queue,
            'alive': True
        }
        status_file = Path('/data/worker_status.json')
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, 'w') as f:
            json.dump(status, f)

    def process_new_videos(self):
        """Main processing loop"""
        log.info(f"\n🔍 Prüfe Watch Later Liste... ({datetime.now().strftime('%H:%M:%S')})")

        if not self._quota_available():
            log.warning("⚠️  YouTube API quota exhausted for today, skipping processing")
            self.write_worker_status(videos_in_queue=0)
            return

        videos = self.get_watch_later_videos()
        processed_count = database.count_videos()
        log.info(f"📋 Bereits verarbeitete Videos: {processed_count}")

        # Filter videos: Nur noch nicht verarbeitete Videos
        videos_to_process = []
        for v in videos:
            is_new = not database.is_processed(v['id'])
            is_recent = self.is_recently_added(v['added_at'], days=7)

            log.info(f"🔍 Video: {v['title'][:50]}... | Neu: {is_new} | Kürzlich: {is_recent} | Datum: {v['added_at']}")

            if is_new:
                videos_to_process.append(v)
                if not is_recent:
                    log.warning(f"⚠️  Video ist älter als 7 Tage, wird trotzdem verarbeitet: {v['title'][:50]}...")

        if not videos_to_process:
            log.info("✨ Keine neuen oder kürzlich hinzugefügten Videos gefunden")
            self.write_worker_status(videos_in_queue=0)
            return

        log.info(f"📹 {len(videos_to_process)} Videos zu verarbeiten!")
        self.write_worker_status(videos_in_queue=len(videos_to_process))

        for video in videos_to_process:
            video_id = video['id']
            title = video['title']

            log.info(f"\n▶️  Verarbeite: {title}")

            # Get transcript
            transcript = self.get_transcript(video_id)
            if not transcript:
                log.info(f"⏭️  Überspringe (kein Transkript)")
                database.save_video(
                    video_id,
                    title=title,
                    channel=video.get('channel', 'Unknown'),
                    thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
                    processed_at=datetime.now().isoformat(),
                    added_at=video.get('added_at', ''),
                    playlist_item_id=video.get('playlist_item_id', ''),
                    transcript='',
                    summary='Kein Transkript verfuegbar',
                    status='active',
                    retry_count=1,
                    retry_after=(datetime.now() + timedelta(days=7)).isoformat(),
                )
                continue

            # Create summary
            log.info("🤖 Erstelle Zusammenfassung mit Claude...")
            success, summary = self.summarize_with_claude(title, transcript)

            if not success:
                log.warning(f"⚠️  Zusammenfassung fehlgeschlagen. Video wird beim nächsten Durchlauf erneut versucht.")
                log.info("⏳ Warte 45 Sekunden um Rate Limiting zu vermeiden...")
                time.sleep(45)
                continue

            # Send email only if summarization succeeded
            if self.send_email(title, video_id, summary):
                database.save_video(
                    video_id,
                    title=title,
                    channel=video.get('channel', 'Unknown'),
                    thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
                    processed_at=datetime.now().isoformat(),
                    added_at=video.get('added_at', ''),
                    playlist_item_id=video.get('playlist_item_id', ''),
                    transcript=transcript,
                    summary=summary,
                    status='active',
                )
                log.info(f"✅ Video erfolgreich verarbeitet und als 'processed' markiert")

                if video.get('playlist_item_id'):
                    self.remove_from_playlist(video['playlist_item_id'], title)
            else:
                log.warning(f"⚠️  Email-Versand fehlgeschlagen. Video wird beim nächsten Durchlauf erneut versucht.")

            log.info("⏳ Warte 45 Sekunden um Rate Limiting zu vermeiden...")
            time.sleep(45)

        self.write_worker_status(videos_in_queue=0)

        # Process retryable videos (failed transcripts that are due for retry)
        self.process_retryable_videos()

    def process_retryable_videos(self):
        """Retry transcript fetching for videos that previously failed."""
        retryable = database.get_retryable_videos()
        if not retryable:
            return

        log.info(f"🔄 {len(retryable)} Videos für Transcript-Retry gefunden")

        for video in retryable:
            video_id = video['id']
            title = video.get('title', 'Unknown')
            retry_count = video.get('retry_count', 0)

            log.info(f"🔄 Retry {retry_count + 1}/3 für: {title[:50]}...")

            transcript = self.get_transcript(video_id)
            if not transcript:
                new_count = retry_count + 1
                if new_count >= 3:
                    log.warning(f"⚠️  Endgültig kein Transkript nach 3 Versuchen: {title[:50]}")
                    database.save_video(video_id, retry_count=new_count, retry_after=None)
                else:
                    next_retry = (datetime.now() + timedelta(days=7)).isoformat()
                    database.save_video(video_id, retry_count=new_count, retry_after=next_retry)
                continue

            # Got transcript this time - create summary
            log.info("🤖 Erstelle Zusammenfassung mit Claude...")
            success, summary = self.summarize_with_claude(title, transcript)

            if success:
                database.save_video(
                    video_id,
                    transcript=transcript,
                    summary=summary,
                    retry_count=0,
                    retry_after=None,
                )
                log.info(f"✅ Retry erfolgreich für: {title[:50]}")

                # Send email for newly summarized video
                self.send_email(title, video_id, summary)
            else:
                log.warning(f"⚠️  Zusammenfassung fehlgeschlagen bei Retry: {title[:50]}")

            time.sleep(45)

    def backfill_existing_videos(self):
        """Re-process all existing videos to add summaries and transcripts (without sending emails)"""
        log.info("\n🔄 Starte Nachbearbeitung aller bereits verarbeiteten Videos...")
        log.info("📧 E-Mails werden NICHT erneut versendet")
        log.info("-" * 50)

        # Get all videos from playlist
        all_videos = self.get_watch_later_videos()

        # Filter to only videos that are already in the database
        videos_to_backfill = [v for v in all_videos if database.is_processed(v['id'])]

        log.info(f"📹 {len(videos_to_backfill)} Videos gefunden zum Nachbearbeiten")

        for i, video in enumerate(videos_to_backfill, 1):
            video_id = video['id']
            title = video['title']

            # Skip if we already have complete data
            existing = database.get_video(video_id)
            if existing and existing.get('summary') and existing.get('transcript'):
                log.info(f"⏭️  [{i}/{len(videos_to_backfill)}] Überspringe (bereits vollständig): {title[:50]}...")
                continue

            log.info(f"\n▶️  [{i}/{len(videos_to_backfill)}] Verarbeite: {title}")

            transcript = self.get_transcript(video_id)
            if not transcript:
                log.info(f"⏭️  Kein Transkript verfügbar")
                database.save_video(
                    video_id,
                    title=title,
                    channel=video.get('channel', 'Unknown'),
                    thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
                    added_at=video.get('added_at', ''),
                    transcript='',
                    summary='Kein Transkript verfuegbar',
                )
                continue

            log.info("🤖 Erstelle Zusammenfassung mit Claude...")
            success, summary = self.summarize_with_claude(title, transcript)

            if not success:
                log.warning(f"⚠️  Zusammenfassung fehlgeschlagen, überspringe dieses Video")
                time.sleep(45)
                continue

            database.save_video(
                video_id,
                title=title,
                channel=video.get('channel', 'Unknown'),
                thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
                added_at=video.get('added_at', ''),
                transcript=transcript,
                summary=summary,
            )
            log.info(f"✅ Daten gespeichert (keine E-Mail versendet)")

            if i < len(videos_to_backfill):
                log.info("⏳ Warte 45 Sekunden um Rate Limiting zu vermeiden...")
                time.sleep(45)

        log.info("\n✅ Nachbearbeitung abgeschlossen!")

    def run(self):
        """Main run loop"""
        log.info("🚀 YouTube Playlist Summarizer gestartet!")
        log.info(f"📺 Playlist ID: {self.playlist_id}")
        log.info(f"⏰ Prüfintervall: {self.check_interval} Minuten")
        log.info(f"📧 Emails an: {self.email_to}")
        log.info("-" * 50)

        while True:
            try:
                self.process_new_videos()
            except Exception as e:
                log.error(f"❌ Unerwarteter Fehler: {e}")

            log.info(f"\n💤 Warte {self.check_interval} Minuten bis zum nächsten Check...")
            time.sleep(self.check_interval * 60)


if __name__ == "__main__":
    summarizer = YouTubeSummarizer()
    summarizer.run()
