# ❓ Frequently Asked Questions

## General Questions

### Q: Is this free to use?

**A:** The code is free (MIT License), but you'll need:
- **Claude API**: Pay-per-use (~$0.01-0.05 per video)
- **RapidAPI**: FREE tier (500 videos/month)
- **Gmail**: FREE
- Total cost: ~$1-5/month for moderate use

### Q: Can I use this with my existing YouTube playlists?

**A:** Yes! Any playlist that you have access to. Best practice: Create a dedicated playlist instead of using "Watch Later" (WL) which often has API limitations.

### Q: How often does it check for new videos?

**A:** Default is every 30 minutes. You can change this in `.env` with `CHECK_INTERVAL_MINUTES`.

### Q: Will it summarize old videos?

**A:** Only videos added AFTER you start the bot. It tracks processed videos to avoid duplicates. If you want to reprocess, delete `data/processed_videos.json`.

---

## Setup Questions

### Q: Do I need a Google Cloud account?

**A:** Yes, for YouTube OAuth credentials. But it's free! You don't need billing enabled.

### Q: Can I use Outlook/Yahoo instead of Gmail?

**A:** Yes, but you'll need to change SMTP settings in `.env`:
```bash
# Outlook
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587

# Yahoo
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

### Q: Why can't I use my regular Gmail password?

**A:** For security! App Passwords are safer because:
- They're app-specific (can be revoked individually)
- They don't expose your main password
- Required if you have 2FA enabled

### Q: Watch Later playlist doesn't work. Why?

**A:** YouTube API has restrictions on the default Watch Later (WL) playlist. **Solution:** Create a custom playlist and use its ID instead.

---

## Usage Questions

### Q: Can I summarize videos in other languages?

**A:** Yes! The transcript API supports multiple languages, and Claude can summarize in any language. The summaries will currently be in German (as configured in the prompt), but you can modify `youtube_summarizer.py` line 298 to change the output language.

### Q: What if a video doesn't have captions?

**A:** The bot will skip it and log: `⏭️ Überspringe (kein Transkript)`. Auto-generated captions work too!

### Q: Can I add multiple email recipients?

**A:** Currently no, but you can:
1. Forward the emails with a Gmail filter
2. Modify the code to support multiple recipients (contribute!)

### Q: How do I stop the bot temporarily?

**A:**
```bash
docker compose stop    # Pause
docker compose start   # Resume
docker compose down    # Stop & remove container
```

---

## Technical Questions

### Q: Does it run on Windows/Mac/Linux?

**A:** Yes! As long as you have Docker installed.

### Q: Can I run this without Docker?

**A:** Yes, but Docker is recommended. To run directly:
```bash
pip install -r requirements.txt
python3 youtube_summarizer.py
```

### Q: How much disk space does it need?

**A:** Very little:
- Docker image: ~500MB
- Data folder: <1MB (tokens + JSON)
- Logs: Minimal

### Q: Can I deploy this to the cloud?

**A:** Yes! Works on:
- Railway.app
- Render.com
- Fly.io
- AWS/GCP/Azure
- Any Docker host

### Q: How do I update to a new version?

**A:**
```bash
git pull origin main
docker compose down
docker compose up -d --build
```

Your `.env` and `data/` will be preserved!

---

## Troubleshooting

### Q: Container keeps restarting

**A:** Check logs: `docker logs youtube-summarizer`

Common causes:
- Invalid API keys in `.env`
- Missing `credentials.json`
- Insufficient Docker resources

### Q: Emails go to spam

**A:** This is normal for the first few emails. To fix:
1. Mark first email as "Not Spam"
2. Add sender to contacts
3. Gmail will learn over time

### Q: "Rate limit exceeded" error

**A:** You're hitting API limits:
- **RapidAPI**: 500/month on free tier (upgrade if needed)
- **Claude API**: Very high limits (unlikely)
- **Solution**: Reduce `CHECK_INTERVAL_MINUTES` or upgrade plans

### Q: OAuth token expired

**A:** The bot auto-refreshes tokens. If it fails:
```bash
rm data/token.pickle
docker compose restart
# Re-authenticate when prompted
```

### Q: Can't find playlist ID

**A:**
1. Go to your playlist on YouTube
2. Look at URL: `youtube.com/playlist?list=PLxxxxx`
3. Copy everything after `list=`

Example:
```
URL: https://www.youtube.com/playlist?list=PLZ0XGediryt6-HLJAIOw3G0gDckqi3wKw
Playlist ID: PLZ0XGediryt6-HLJAIOw3G0gDckqi3wKw
```

---

## API & Costs

### Q: How much does Claude API cost?

**A:** Claude Sonnet 4 pricing (as of 2025):
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens
- **Per video**: ~$0.01-0.05 (very cheap!)

### Q: What if I run out of RapidAPI credits?

**A:** Free tier gives 500 requests/month. If you need more:
1. Upgrade to paid plan ($10/month for 10,000)
2. Or use another transcript API

### Q: Can I use a different AI model?

**A:** Yes! Edit `youtube_summarizer.py` line 359:
```python
model="claude-sonnet-4-20250514"  # Change this
```

Options:
- `claude-sonnet-4-20250514` (current, best)
- `claude-sonnet-4-latest` (always newest)
- `claude-opus-4-latest` (smarter, more expensive)

---

## Privacy & Security

### Q: Where is my data stored?

**A:** All data stays on YOUR machine:
- OAuth tokens: `data/token.pickle`
- Processed videos: `data/processed_videos.json`
- Credentials: `data/credentials.json` & `.env`

Nothing is sent to external servers except API calls.

### Q: Are my API keys secure?

**A:** Yes, if you:
- ✅ Use `.gitignore` (included)
- ✅ Don't share your `.env` file
- ✅ Don't commit secrets to Git

### Q: Can others see my summaries?

**A:** No! Emails are only sent to the address in your `.env` file.

---

## Contributing

### Q: How can I contribute?

**A:** Check [CONTRIBUTING.md](../CONTRIBUTING.md)!

Ways to help:
- Report bugs
- Suggest features
- Improve documentation
- Submit pull requests
- Share the project

### Q: I found a bug, what now?

**A:** Open an issue on GitHub with:
- Description of the problem
- Steps to reproduce
- Error logs
- Your environment (OS, Docker version)

---

## Still have questions?

- 📖 Check the [Setup Guide](SETUP-GUIDE.md)
- 💬 Open a [GitHub Issue](../../issues)
- 🔍 Search [existing issues](../../issues?q=is%3Aissue)

---

*Last updated: 2025-11-07*
