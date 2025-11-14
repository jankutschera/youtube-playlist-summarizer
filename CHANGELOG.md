# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-07

### Added
- 🎉 Initial release
- 🤖 Claude Sonnet 4.5 integration for AI summaries
- 📧 Beautiful HTML email notifications with video thumbnails
- 🔄 Automatic playlist checking every 30 minutes
- 🐳 Docker support with auto-restart
- 🔒 OAuth2 authentication for YouTube
- 📝 Smart formatting for list videos ("10 Tips", "25 Tricks", etc.)
- 🎨 Markdown-to-HTML conversion in emails
- 📊 SCHNELLÜBERSICHT (quick overview) section in summaries
- ✅ Duplicate prevention (tracks processed videos)

### Features
- Supports any YouTube playlist (not just Watch Later)
- Configurable check intervals
- Gmail SMTP integration
- RapidAPI for video transcripts
- Persistent OAuth token storage
- Detailed logging and error handling

### Technical
- Python 3.11
- Docker Compose setup
- Environment-based configuration
- Volume mounting for data persistence

---

## [Unreleased]

### Planned Features
- [ ] Support for multiple playlists
- [ ] Web UI for configuration
- [ ] Webhook support
- [ ] Multiple email recipients
- [ ] Summary customization options
- [ ] Language selection for summaries
- [ ] Discord/Slack notifications
- [ ] Statistics dashboard

### Known Issues
- Watch Later playlist (WL) may not work due to YouTube API limitations
- First-run OAuth requires manual code input
- maxresdefault thumbnails may not exist for all videos (fallback needed)

---

## How to Upgrade

When a new version is released:

```bash
# Pull latest code
git pull origin main

# Rebuild container
docker compose down
docker compose up -d --build

# Check logs
docker logs youtube-summarizer -f
```

Your `.env` file and `data/` folder will be preserved.
