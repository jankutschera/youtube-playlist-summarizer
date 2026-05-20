#!/usr/bin/env python3
"""
MCP Server for YouTube Summarizer.
Exposes video search, listing, and summary retrieval as MCP tools.
Connects to the YouTube Summarizer API at yt.lucia-allegra.com.
"""

import json
import urllib.request
import urllib.parse
from mcp.server.fastmcp import FastMCP

API_BASE = "https://yt.lucia-allegra.com/api"

mcp = FastMCP("youtube-summarizer")


def _api_get(path, params=None):
    """Make a GET request to the YouTube Summarizer API."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "yt-summarizer-mcp/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


@mcp.tool()
def search_videos(query: str) -> str:
    """Search YouTube video summaries by keyword. Searches in title, summary, and transcript content.
    Returns a list of matching videos with title, channel, date, and a snippet of the summary."""
    results = _api_get("/search", {"q": query})
    if not results:
        return f"No videos found matching '{query}'."

    lines = [f"Found {len(results)} video(s) matching '{query}':\n"]
    for v in results:
        lines.append(f"- **{v['title']}** ({v.get('channel', 'Unknown')})")
        lines.append(f"  ID: {v['id']} | Added: {v.get('added_at', 'N/A')}")
        if v.get('summary_snippet'):
            lines.append(f"  Snippet: {v['summary_snippet']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_video_summary(video_id: str) -> str:
    """Get the full summary and details of a specific YouTube video by its ID.
    Use this after search_videos to read the complete summary of a video."""
    data = _api_get(f"/video/{video_id}")
    if "error" in data:
        return f"Video '{video_id}' not found."

    lines = [
        f"# {data['title']}",
        f"**Channel:** {data.get('channel', 'Unknown')}",
        f"**Added:** {data.get('added_at', 'N/A')}",
        f"**Status:** {data.get('status', 'unknown')}",
        f"**YouTube:** https://youtube.com/watch?v={data['id']}",
        "",
        "## Summary",
        data.get('summary', 'No summary available.'),
    ]
    return "\n".join(lines)


@mcp.tool()
def list_recent_videos(limit: int = 20) -> str:
    """List the most recently added YouTube videos. Returns title, channel, date, and video ID.
    Use get_video_summary(video_id) to read the full summary of any video."""
    videos = _api_get("/videos", {"limit": limit, "status": "active"})
    if not videos:
        return "No videos found."

    lines = [f"Most recent {len(videos)} videos:\n"]
    for v in videos:
        read_marker = "" if v.get('read') else " [UNREAD]"
        lines.append(f"- **{v['title']}** ({v.get('channel', 'Unknown')}){read_marker}")
        lines.append(f"  ID: {v['id']} | Added: {v.get('added_at', 'N/A')}")
    return "\n".join(lines)


@mcp.tool()
def get_stats() -> str:
    """Get YouTube Summarizer statistics: total videos, active count, quota usage, and worker status."""
    data = _api_get("/status")

    lines = [
        "## YouTube Summarizer Stats",
        f"- **Total videos:** {data['videos']['total']}",
        f"- **Active videos:** {data['videos']['active']}",
        f"- **API quota used today:** {data['quota']['used']}/{data['quota']['limit']}",
        f"- **Quota date:** {data['quota']['date']}",
        f"- **Worker alive:** {data['worker'].get('alive', 'unknown')}",
        f"- **Last worker run:** {data['worker'].get('last_run', 'N/A')}",
        f"- **Videos in queue:** {data['worker'].get('videos_in_queue', 0)}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
