#!/usr/bin/env python3
"""
MCP Server for Focus Digest.
Exposes the authenticated user's Focus Digest summaries as MCP tools.
"""

import json
import os
import urllib.parse
import urllib.request
from mcp.server.fastmcp import FastMCP


API_BASE = os.getenv(
    "FOCUS_DIGEST_API_BASE",
    "https://adhd-youtube-digest.jan-8ed.workers.dev/api/mcp",
).rstrip("/")
API_TOKEN = os.getenv("FOCUS_DIGEST_MCP_TOKEN", "").strip()

mcp = FastMCP("focus-digest")


def _api_get(path, params=None):
    """Make an authenticated GET request to the Focus Digest MCP API."""
    if not API_TOKEN:
        raise RuntimeError("FOCUS_DIGEST_MCP_TOKEN is not configured.")

    url = f"{API_BASE}{path}"
    if params:
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params)

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {API_TOKEN}",
            "User-Agent": "focus-digest-mcp/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("ok", False):
        raise RuntimeError(data.get("error", "Focus Digest API request failed."))
    return data


def _video_line(video):
    title = video.get("title", "Untitled")
    channel = video.get("channelTitle") or "Unknown channel"
    status = video.get("status", "unknown")
    return f"- **{title}** ({channel}) [{status}]\n  ID: {video.get('id')}"


@mcp.tool()
def list_focus_videos(limit: int = 20, status: str = "") -> str:
    """List the authenticated user's Focus Digest videos.
    Optional status values: pending, processing, summarized, error, archived, all."""
    data = _api_get("/videos", {"limit": limit, "status": status})
    videos = data.get("videos", [])
    if not videos:
        return "No Focus Digest videos found."

    lines = [f"Found {len(videos)} Focus Digest video(s):\n"]
    for video in videos:
        lines.append(_video_line(video))
        if video.get("summarySnippet"):
            lines.append(f"  Snippet: {video['summarySnippet']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def search_focus_summaries(query: str, limit: int = 20, status: str = "") -> str:
    """Search the authenticated user's Focus Digest summaries by title, channel, or summary text."""
    data = _api_get("/search", {"q": query, "limit": limit, "status": status})
    videos = data.get("videos", [])
    if not videos:
        return f"No Focus Digest summaries found matching '{query}'."

    lines = [f"Found {len(videos)} Focus Digest video(s) matching '{query}':\n"]
    for video in videos:
        lines.append(_video_line(video))
        if video.get("summarySnippet"):
            lines.append(f"  Snippet: {video['summarySnippet']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_focus_summary(video_id: str) -> str:
    """Get the full Focus Digest summary for a specific video ID."""
    data = _api_get(f"/videos/{urllib.parse.quote(video_id, safe='')}")
    video = data.get("video", {})

    lines = [
        f"# {video.get('title', 'Untitled')}",
        f"**Channel:** {video.get('channelTitle') or 'Unknown channel'}",
        f"**Status:** {video.get('status', 'unknown')}",
        f"**YouTube:** {video.get('youtubeUrl', 'N/A')}",
        f"**Updated:** {video.get('updatedAt', 'N/A')}",
        "",
        "## Summary",
        video.get("summary") or video.get("error") or "No summary available.",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_focus_stats() -> str:
    """Get Focus Digest stats for the authenticated user."""
    data = _api_get("/stats")
    statuses = data.get("statuses", [])

    lines = [
        "## Focus Digest Stats",
        f"- **User:** {data.get('user', {}).get('email', 'unknown')}",
        f"- **Playlist:** {data.get('playlist') or 'not configured'}",
        f"- **Latest update:** {data.get('latestUpdatedAt') or 'N/A'}",
    ]
    for item in statuses:
        lines.append(f"- **{item.get('status', 'unknown')}:** {item.get('count', 0)}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
