# 🎥 YouTube Playlist Summarizer

Automatically summarize new videos from your YouTube playlist and get email notifications with AI-powered summaries using Claude.

## ✨ Features

- 🤖 **AI Summaries** powered by Claude Sonnet 4.5
- 📧 **Email Notifications** with beautiful HTML formatting
- 🔄 **Auto-Check** every 30 minutes for new videos
- 🎨 **Video Thumbnails** in emails
- 📝 **Smart Formatting** for list videos ("10 Tips", "25 Tricks", etc.)
- 🐳 **Docker Ready** - runs in the background
- 🔒 **OAuth2** authentication with YouTube

## 📋 Requirements

- Docker & Docker Compose
- Claude API Key (from Anthropic)
- RapidAPI Key (free tier available)
- Gmail account with App Password
- YouTube account with OAuth2 credentials

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer
```

### 2. Get Your API Keys

#### Claude API Key
1. Go to https://console.anthropic.com/
2. Sign up / Log in
3. Create a new API key
4. Copy it

#### RapidAPI Key
1. Go to https://rapidapi.com/
2. Sign up for free
3. Search for "YT API" by ytjar
4. Subscribe to the FREE plan
5. Copy your API key from the dashboard

#### Gmail App Password
1. Go to https://myaccount.google.com/apppasswords
2. Sign in to your Google Account
3. Under "Security" → "App passwords"
4. Generate a new app password
5. Copy the 16-character password

#### YouTube OAuth2 Credentials
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the JSON file
6. Rename it to `credentials.json`
7. Place it in the `data/` folder

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your favorite editor
```

Fill in all the required values in the `.env` file.

### 4. Setup YouTube Playlist

⚠️ **Important:** The default "Watch Later" (WL) often doesn't work with the API!

**Recommended:** Create a custom playlist:
1. Go to YouTube
2. Create a new playlist (e.g., "AI Summaries")
3. Get the playlist ID from the URL: `youtube.com/playlist?list=PLxxxxx`
4. Add it to your `.env` file as `PLAYLIST_ID`

### 5. Start the App

```bash
# Build and start
docker compose up -d

# Check logs
docker logs youtube-summarizer -f
```

### 6. First Run - OAuth Authentication

On the first run, you'll need to authenticate:

```bash
# Check logs for the OAuth URL
docker logs youtube-summarizer

# You'll see:
# 📋 SCHRITT 1: Öffne diese URL in deinem Browser:
# https://accounts.google.com/o/oauth2/auth?...
#
# 📋 SCHRITT 2: Nach der Anmeldung bekommst du einen CODE
# Kopiere diesen CODE

# Enter the code interactively
docker attach youtube-summarizer
# Paste the OAuth code and press Enter
```

After successful authentication, the app will run automatically!

## 📊 Usage

Once running, the app will:
- ✅ Check your playlist every 30 minutes
- ✅ Summarize new videos with Claude AI
- ✅ Send beautiful HTML emails
- ✅ Track processed videos (no duplicates)
- ✅ Auto-restart after system reboot

### Check Status

```bash
# View logs
docker logs youtube-summarizer -f

# Check if running
docker ps | grep youtube-summarizer

# Restart
docker compose restart

# Stop
docker compose down
```

## 🎨 Email Format

Each email includes:
- 📺 Video title
- 🖼️ Thumbnail image
- 🔗 Link to watch on YouTube
- 📝 AI-generated summary with:
  - **SCHNELLÜBERSICHT** (Quick overview)
  - **HAUPTTHEMA** (Main topic)
  - **KERNPUNKTE** (Key points)
  - **FAZIT** (Conclusion)

## 🔧 Configuration Options

Edit `.env` to customize:

```bash
# Check interval (in minutes)
CHECK_INTERVAL_MINUTES=30

# Change playlist
PLAYLIST_ID=PLxxxxxxxxxx

# Email settings
EMAIL_FROM=your@gmail.com
EMAIL_TO=recipient@email.com
```

## 🐛 Troubleshooting

### Container not starting
```bash
docker logs youtube-summarizer
```

### OAuth issues
```bash
# Remove old token
rm data/token.pickle
docker compose restart
```

### No emails received
1. Check spam folder
2. Verify Gmail App Password is correct
3. Check logs: `docker logs youtube-summarizer | grep -i email`

### Videos not being processed
1. Make sure playlist is PUBLIC or UNLISTED
2. Check playlist ID in `.env`
3. Verify videos have transcripts (not all do)

## 📁 Project Structure

```
youtube-summarizer/
├── youtube_summarizer.py   # Main application
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Docker Compose setup
├── requirements.txt         # Python dependencies
├── .env                     # Your configuration (not in git)
├── .env.example            # Template for configuration
├── data/
│   ├── credentials.json    # YouTube OAuth credentials
│   ├── token.pickle        # OAuth token (auto-generated)
│   └── processed_videos.json  # Processed video IDs
└── README.md               # This file
```

## 🔐 Security Notes

- ⚠️ **Never commit `.env` or `credentials.json` to Git!**
- ✅ The `.gitignore` is already configured
- ✅ Use Gmail App Passwords, not your actual password
- ✅ Keep your API keys secure

## 💡 Tips

1. **Create a dedicated playlist** instead of using Watch Later
2. **Add videos in batches** - the app checks every 30 minutes
3. **Check logs regularly** to monitor performance
4. **Free tier limits:**
   - RapidAPI: 500 requests/month (plenty!)
   - Claude API: Pay-per-use (very cheap for summaries)

## 🚢 Deployment Options

### Local Docker (Recommended)
Already set up! Just run `docker compose up -d`

### Cloud Hosting
You can deploy to:
- **Railway** (Easy, free tier)
- **Render** (Easy, free tier)
- **Fly.io** (More complex, free tier)
- **AWS/GCP/Azure** (Most flexible, costs vary)

## 📝 License

MIT License - feel free to modify and share!

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ⚠️ Disclaimer

This tool is for personal use. Make sure to:
- Respect YouTube's Terms of Service
- Stay within API rate limits
- Don't redistribute copyrighted content

## 🆘 Support

Having issues? Check:
1. This README
2. GitHub Issues
3. Stack Overflow

---

Made with ❤️ and Claude AI
