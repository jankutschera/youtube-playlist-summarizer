"""
SQLite database module for YouTube Summarizer.
Replaces JSON file-based storage with proper database operations.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict

DB_PATH = Path('/data/youtube_summarizer.db')

GERMAN_MONTHS = {
    1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
    5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    title TEXT,
    channel TEXT DEFAULT 'Unknown',
    thumbnail TEXT,
    added_at TEXT,
    processed_at TEXT,
    transcript TEXT,
    summary TEXT,
    playlist_item_id TEXT,
    status TEXT DEFAULT 'active',
    read INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    retry_after TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_read ON videos(read);
CREATE INDEX IF NOT EXISTS idx_added_at ON videos(added_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_connection():
    """Get a SQLite connection with WAL mode for concurrent access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def get_video(video_id):
    """Get a single video by ID. Returns dict or None."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return dict(row) if row else None


def get_videos(status='active', limit=50, offset=0):
    """Get videos filtered by status, sorted by added_at descending."""
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM videos WHERE status = ? ORDER BY COALESCE(added_at, processed_at) DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM videos ORDER BY COALESCE(added_at, processed_at) DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]


def get_videos_grouped_by_date(status='active'):
    """Get videos grouped by date categories (Heute, Gestern, Diese Woche, monthly)."""
    videos = get_videos(status=status, limit=10000, offset=0)

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    groups = OrderedDict()
    groups['Heute'] = []
    groups['Gestern'] = []
    groups['Diese Woche'] = []

    monthly_groups = {}

    for video in videos:
        date_str = video.get('added_at') or video.get('processed_at', '')
        if not date_str or date_str == 'N/A':
            if 'Unbekannt' not in groups:
                groups['Unbekannt'] = []
            groups['Unbekannt'].append(video)
            continue

        try:
            video_date = datetime.fromisoformat(date_str.replace('Z', '+00:00').replace(' ', 'T').split('.')[0]).date()

            if video_date == today:
                groups['Heute'].append(video)
            elif video_date == yesterday:
                groups['Gestern'].append(video)
            elif video_date > week_ago:
                groups['Diese Woche'].append(video)
            else:
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

    for key in ['Heute', 'Gestern', 'Diese Woche']:
        if not groups[key]:
            del groups[key]

    sorted_months = sorted(monthly_groups.items(),
                          key=lambda x: x[1]['sort_key'],
                          reverse=True)
    for month_name, data in sorted_months:
        groups[month_name] = data['videos']

    return groups


def save_video(video_id, **fields):
    """Insert or update a video. Pass only the fields you want to set."""
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM videos WHERE id = ?", (video_id,)).fetchone()

        if existing:
            if not fields:
                return
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [video_id]
            conn.execute(f"UPDATE videos SET {set_clause} WHERE id = ?", values)
        else:
            fields['id'] = video_id
            columns = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            conn.execute(f"INSERT INTO videos ({columns}) VALUES ({placeholders})", list(fields.values()))


def is_processed(video_id):
    """Check if a video has been processed (exists in DB)."""
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM videos WHERE id = ?", (video_id,)).fetchone()
        return row is not None


def count_videos(status=None, read=None):
    """Count videos with optional filters."""
    with get_connection() as conn:
        conditions = []
        params = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if read is not None:
            conditions.append("read = ?")
            params.append(read)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        row = conn.execute(f"SELECT COUNT(*) as cnt FROM videos{where}", params).fetchone()
        return row['cnt']


def search_videos(query, status='active'):
    """Search videos by title, transcript, or summary content."""
    with get_connection() as conn:
        like_query = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM videos
               WHERE status = ?
               AND (title LIKE ? OR transcript LIKE ? OR summary LIKE ?)
               ORDER BY COALESCE(added_at, processed_at) DESC""",
            (status, like_query, like_query, like_query)
        ).fetchall()
        return [dict(r) for r in rows]


def get_retryable_videos():
    """Get videos that are eligible for transcript retry."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM videos
               WHERE retry_count > 0 AND retry_count < 3
               AND retry_after IS NOT NULL AND retry_after < ?
               ORDER BY retry_after ASC""",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_setting(key, default=None):
    """Get a setting value."""
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else default


def set_setting(key, value):
    """Set a setting value."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
