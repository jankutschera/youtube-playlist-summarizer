#!/usr/bin/env python3
"""
YouTube Watch Later Summarizer with OAuth2
Checks your Watch Later playlist and sends email summaries of new videos
"""

import os
import time
import json
import smtplib
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube OAuth2 Scopes - wir brauchen readonly für Watch Later
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']


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
        
        # OAuth2 credentials files
        self.credentials_file = Path('/data/credentials.json')
        self.token_file = Path('/data/token.pickle')
        
        # Initialize APIs
        self.youtube = self.get_authenticated_service()
        self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
        
        # Track processed videos
        self.state_file = Path('/data/processed_videos.json')
        self.processed_videos = self.load_state()
    
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
                print("🔄 Token abgelaufen, erneuere...")
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    print("❌ FEHLER: credentials.json nicht gefunden!")
                    print("📝 Bitte lade deine OAuth2 credentials.json herunter und lege sie nach /data/credentials.json")
                    print("📖 Siehe README für Anleitung!")
                    raise FileNotFoundError("credentials.json fehlt in /data/")
                
                print("🔐 Erste Authentifizierung erforderlich!")
                print("=" * 60)

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file),
                    SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )

                # Manual OAuth flow (Docker-friendly)
                auth_url, _ = flow.authorization_url(prompt='consent')

                print("\n📋 SCHRITT 1: Öffne diese URL in deinem Browser:")
                print("-" * 60)
                print(auth_url)
                print("-" * 60)

                print("\n📋 SCHRITT 2: Nach der Anmeldung bekommst du einen CODE angezeigt.")
                print("Kopiere diesen CODE (eine lange Zeichenkette).\n")

                auth_code = input("🔑 Füge den CODE hier ein und drücke Enter: ").strip()

                # Exchange code for credentials
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            
            print("✅ Authentifizierung erfolgreich!")
        
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
                print(f"✅ Verbunden mit YouTube Account: {channel_title}")
        except Exception as e:
            print(f"⚠️  Konnte Account-Info nicht abrufen: {e}")

        return service
    
    def load_state(self):
        """Load list of already processed video IDs"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_state(self):
        """Save list of processed video IDs"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(list(self.processed_videos), f)
    
    def get_watch_later_videos(self):
        """Get videos from configured playlist"""
        try:
            print(f"🔍 Versuche Playlist abzurufen...")
            print(f"🔍 Verwende Playlist ID: {self.playlist_id}")

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

                all_items.extend(response.get('items', []))
                next_page_token = response.get('nextPageToken')

                if not next_page_token:
                    break

            print(f"🔍 API Response erhalten. Keys: {list(response.keys())}")
            print(f"🔍 Total Results: {response.get('pageInfo', {}).get('totalResults', 'unknown')}")
            print(f"🔍 Total Videos geholt mit Pagination: {len(all_items)}")

            videos = []
            items = all_items
            print(f"🔍 Items in Response: {len(items)}")

            for item in items:
                video_id = item['contentDetails']['videoId']
                title = item['snippet']['title']
                # publishedAt ist das Datum, wann das Video zur Playlist hinzugefügt wurde
                added_at = item['snippet']['publishedAt']
                videos.append({
                    'id': video_id,
                    'title': title,
                    'added_at': added_at
                })

            print(f"📊 API hat {len(videos)} Videos in Watch Later gefunden")
            return videos
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Watch Later Liste: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_transcript(self, video_id):
        """Get transcript using RapidAPI YT API"""
        import requests

        try:
            print(f"🔍 Versuche Transkript für Video {video_id} mit RapidAPI abzurufen...")

            # Delay before API call to avoid rate limiting
            import time
            time.sleep(3)

            url = "https://yt-api.p.rapidapi.com/subtitles"
            querystring = {"id": video_id}

            headers = {
                "x-rapidapi-key": os.getenv('RAPIDAPI_KEY'),
                "x-rapidapi-host": "yt-api.p.rapidapi.com"
            }

            response = requests.get(url, headers=headers, params=querystring, timeout=30)

            if response.status_code != 200:
                print(f"❌ RapidAPI Fehler: Status {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None

            data = response.json()

            # Check if subtitles exist
            if not data or 'subtitles' not in data:
                print(f"❌ Keine Untertitel in der Response gefunden")
                return None

            subtitles = data['subtitles']

            # RapidAPI returns subtitles as a list of subtitle objects
            if not isinstance(subtitles, list) or len(subtitles) == 0:
                print(f"❌ Keine Untertitel verfügbar")
                return None

            # Try to find German or English subtitle, otherwise take the first one
            import xml.etree.ElementTree as ET
            import html
            import re

            selected_subtitle = None

            for subtitle in subtitles:
                lang_code = subtitle.get('languageCode', '').lower()
                if 'de' in lang_code:
                    selected_subtitle = subtitle
                    break

            if not selected_subtitle:
                for subtitle in subtitles:
                    lang_code = subtitle.get('languageCode', '').lower()
                    if 'en' in lang_code:
                        selected_subtitle = subtitle
                        break

            # If still nothing, take the first available
            if not selected_subtitle and len(subtitles) > 0:
                selected_subtitle = subtitles[0]

            if not selected_subtitle or 'url' not in selected_subtitle:
                print(f"❌ Keine Transkript-URL gefunden")
                return None

            # Fetch the actual transcript from the URL
            transcript_url = selected_subtitle['url']
            lang_name = selected_subtitle.get('languageName', 'unknown')

            print(f"📥 Lade Transkript herunter ({lang_name})...")

            # Add delay to avoid rate limiting
            import time
            time.sleep(5)  # Wait 5 seconds before downloading

            transcript_response = requests.get(transcript_url, timeout=30)

            if transcript_response.status_code != 200:
                print(f"❌ Fehler beim Laden des Transkripts: Status {transcript_response.status_code}")
                return None

            # Parse the XML transcript
            try:
                root = ET.fromstring(transcript_response.text)
                text_parts = []

                # Extract text from all <text> elements
                for text_elem in root.findall('.//text'):
                    if text_elem.text:
                        # Decode HTML entities
                        decoded = html.unescape(text_elem.text)
                        text_parts.append(decoded)

                full_text = ' '.join(text_parts)

                # Clean up extra whitespace
                full_text = re.sub(r'\s+', ' ', full_text).strip()

                if not full_text:
                    print(f"❌ Transkript ist leer")
                    return None

                print(f"✅ Transkript verarbeitet: {len(full_text)} Zeichen")
                return full_text

            except ET.ParseError as e:
                print(f"❌ Fehler beim Parsen des Transkript-XML: {e}")
                return None

        except requests.exceptions.Timeout:
            print(f"❌ Timeout beim Abrufen des Transkripts")
            return None
        except Exception as e:
            print(f"❌ Fehler beim Abrufen des Transkripts: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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

    def summarize_with_claude(self, title, transcript):
        """Create summary using Claude"""
        import re

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

        try:
            # Dynamische Token-Berechnung basierend auf Titel
            max_tokens = self.calculate_max_tokens(title)
            print(f"🎯 Max Tokens für '{title}': {max_tokens}")

            # Nutze Claude Sonnet 4.5 (neueste Version)
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude Sonnet 4.5
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"❌ Fehler bei Claude Sonnet 4: {e}")
            # Fallback: Versuche mit dem "latest" Alias
            try:
                print("🔄 Versuche mit 'claude-sonnet-4-latest'...")
                max_tokens = self.calculate_max_tokens(title)
                message = self.claude_client.messages.create(
                    model="claude-sonnet-4-latest",
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e2:
                print(f"❌ Fallback fehlgeschlagen: {e2}")
                return f"Zusammenfassung konnte nicht erstellt werden. API Fehler: {e}"
    
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
            print(f"⚠️  Konnte Datum nicht parsen: {e}")
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

            print(f"✅ Email gesendet für: {video_title}")
            return True

        except Exception as e:
            print(f"❌ Fehler beim Email-Versand: {e}")
            return False
    
    def process_new_videos(self):
        """Main processing loop"""
        print(f"\n🔍 Prüfe Watch Later Liste... ({datetime.now().strftime('%H:%M:%S')})")

        videos = self.get_watch_later_videos()
        print(f"📋 Bereits verarbeitete Videos: {len(self.processed_videos)}")

        # Filter videos: Nur noch nicht verarbeitete Videos
        videos_to_process = []
        for v in videos:
            is_new = v['id'] not in self.processed_videos
            is_recent = self.is_recently_added(v['added_at'], days=7)

            print(f"🔍 Video: {v['title'][:50]}... | Neu: {is_new} | Kürzlich: {is_recent} | Datum: {v['added_at']}")

            # Nur Videos verarbeiten die NOCH NICHT verarbeitet wurden
            if is_new:
                videos_to_process.append(v)
                if not is_recent:
                    print(f"⚠️  Video ist älter als 7 Tage, wird trotzdem verarbeitet: {v['title'][:50]}...")

        if not videos_to_process:
            print("✨ Keine neuen oder kürzlich hinzugefügten Videos gefunden")
            return

        print(f"📹 {len(videos_to_process)} Videos zu verarbeiten!")

        for video in videos_to_process:
            video_id = video['id']
            title = video['title']

            print(f"\n▶️  Verarbeite: {title}")

            # Get transcript
            transcript = self.get_transcript(video_id)
            if not transcript:
                print(f"⏭️  Überspringe (kein Transkript)")
                self.processed_videos.add(video_id)
                continue

            # Create summary
            print("🤖 Erstelle Zusammenfassung mit Claude...")
            summary = self.summarize_with_claude(title, transcript)

            # Send email
            if self.send_email(title, video_id, summary):
                self.processed_videos.add(video_id)
                self.save_state()

            # Delay between videos to avoid rate limiting
            print("⏳ Warte 30 Sekunden um Rate Limiting zu vermeiden...")
            time.sleep(30)
    
    def run(self):
        """Main run loop"""
        print("🚀 YouTube Playlist Summarizer gestartet!")
        print(f"📺 Playlist ID: {self.playlist_id}")
        print(f"⏰ Prüfintervall: {self.check_interval} Minuten")
        print(f"📧 Emails an: {self.email_to}")
        print("-" * 50)
        
        while True:
            try:
                self.process_new_videos()
            except Exception as e:
                print(f"❌ Unerwarteter Fehler: {e}")
            
            print(f"\n💤 Warte {self.check_interval} Minuten bis zum nächsten Check...")
            time.sleep(self.check_interval * 60)


if __name__ == "__main__":
    summarizer = YouTubeSummarizer()
    summarizer.run()
