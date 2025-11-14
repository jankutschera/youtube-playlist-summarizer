# 📖 Detailed Setup Guide

This guide walks you through every step of setting up the YouTube Playlist Summarizer.

## Prerequisites

- **Docker Desktop** installed and running
- **YouTube account** with a playlist
- **Gmail account** for receiving summaries
- **Credit card** for Claude API (pay-per-use, very cheap)
- **15 minutes** of your time

---

## Step 1: Get Claude API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Click "API Keys" in the sidebar
4. Click "Create Key"
5. Give it a name (e.g., "YouTube Summarizer")
6. Copy the key (starts with `sk-ant-api03-...`)
7. Save it somewhere safe - you'll need it later!

**Cost:** ~$0.01-0.05 per video summary (very cheap!)

---

## Step 2: Get RapidAPI Key

1. Go to https://rapidapi.com/
2. Sign up with Google/GitHub/Email
3. Search for "YT API" in the search bar
4. Find "YT API" by **ytjar**
5. Click "Subscribe to Test"
6. Select the **FREE plan** (500 requests/month)
7. Confirm subscription
8. Copy your API key from the dashboard

**Cost:** FREE (up to 500 videos/month)

---

## Step 3: Setup Gmail App Password

⚠️ **Important:** Don't use your regular Gmail password!

1. Go to https://myaccount.google.com/apppasswords
2. You may need to enable 2-Factor Authentication first
3. Under "Select app", choose "Mail"
4. Under "Select device", choose "Other (Custom name)"
5. Enter "YouTube Summarizer"
6. Click "Generate"
7. Copy the 16-character password (remove spaces)
8. Save it somewhere safe!

**Why?** This is more secure than your real password.

---

## Step 4: Get YouTube OAuth Credentials

This is the most complex step, but I'll guide you through it!

### 4.1 Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Name it "YouTube Summarizer"
4. Click "Create"
5. Wait for the project to be created (~30 seconds)

### 4.2 Enable YouTube Data API

1. In the top search bar, search for "YouTube Data API v3"
2. Click on it
3. Click "Enable"
4. Wait for it to enable (~30 seconds)

### 4.3 Create OAuth Credentials

1. Click "Credentials" in the left sidebar
2. Click "Configure Consent Screen"
3. Select "External" (unless you have Google Workspace)
4. Click "Create"
5. Fill in:
   - App name: "YouTube Summarizer"
   - User support email: Your email
   - Developer contact: Your email
6. Click "Save and Continue"
7. Click "Add or Remove Scopes"
8. Search for "youtube.readonly"
9. Select it
10. Click "Update"
11. Click "Save and Continue"
12. Add yourself as a test user (your email)
13. Click "Save and Continue"

### 4.4 Create OAuth Client ID

1. Go back to "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "YouTube Summarizer Desktop"
5. Click "Create"
6. Click "Download JSON"
7. Rename the file to `credentials.json`

### 4.5 Place credentials.json

```bash
cd youtube-summarizer
mkdir -p data
mv ~/Downloads/credentials.json data/
```

**Important:** Never share this file publicly!

---

## Step 5: Create YouTube Playlist

⚠️ **Watch Later (WL) often doesn't work with the API!**

### Create a Custom Playlist:

1. Go to YouTube
2. Click your profile → "Your channel"
3. Click "Playlists"
4. Click "New playlist"
5. Name it "AI Summaries" (or whatever you like)
6. Privacy: **Unlisted** or **Public** (NOT Private!)
7. Click "Create"

### Get Playlist ID:

1. Open your new playlist
2. Look at the URL: `youtube.com/playlist?list=PLxxxxxxxxx`
3. Copy the part after `list=` (the `PLxxxxxxxxx`)
4. This is your Playlist ID!

---

## Step 6: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer

# Copy environment template
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
code .env
```

### Fill in your .env:

```bash
# Claude API Key (from Step 1)
CLAUDE_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

# RapidAPI Key (from Step 2)
RAPIDAPI_KEY=xxxxxxxxxxxxx

# Gmail (from Step 3)
EMAIL_FROM=your.email@gmail.com
EMAIL_TO=your.email@gmail.com  # Can be the same
EMAIL_PASSWORD=abcd efgh ijkl mnop  # 16-char app password

# Playlist ID (from Step 5)
PLAYLIST_ID=PLxxxxxxxxxxxxxxxxx

# Check interval (optional, default: 30 minutes)
CHECK_INTERVAL_MINUTES=30
```

Save and close.

---

## Step 7: Start the App

```bash
# Make sure Docker Desktop is running!

# Start with setup script (recommended)
./setup.sh

# Or manually
docker compose up -d --build
```

---

## Step 8: First-Run OAuth

On the first run, you need to authenticate with YouTube:

```bash
# Watch the logs
docker logs youtube-summarizer -f
```

You'll see:
```
📋 SCHRITT 1: Öffne diese URL in deinem Browser:
https://accounts.google.com/o/oauth2/auth?client_id=...

📋 SCHRITT 2: Nach der Anmeldung bekommst du einen CODE
```

1. Copy the URL and open it in your browser
2. Sign in with your Google account
3. Click "Continue" when asked for permissions
4. You'll see a code (long string of letters/numbers)
5. Copy the code
6. Attach to the container:
   ```bash
   docker attach youtube-summarizer
   ```
7. Paste the code and press Enter
8. Detach: Press `Ctrl+P` then `Ctrl+Q`

The app will now save the token and run automatically!

---

## Step 9: Test It!

1. Add a video to your playlist
2. Wait up to 30 minutes (or restart: `docker compose restart`)
3. Check your email!

```bash
# Check logs to see what's happening
docker logs youtube-summarizer -f

# Should see:
# ✅ Email gesendet für: [Video Title]
```

---

## Step 10: Verify Everything

```bash
# Check if container is running
docker ps | grep youtube-summarizer

# Check logs
docker logs youtube-summarizer --tail 50

# Check processed videos
cat data/processed_videos.json
```

---

## Troubleshooting

### "No such file: credentials.json"
- Make sure you placed `credentials.json` in the `data/` folder
- Verify the file name is exactly `credentials.json`

### "Invalid client secrets"
- Re-download OAuth credentials from Google Cloud Console
- Make sure you selected "Desktop app" type

### "No emails received"
- Check spam folder
- Verify Gmail App Password is correct (no spaces)
- Check logs: `docker logs youtube-summarizer | grep -i email`

### "Playlist is empty"
- Make sure playlist is NOT private
- Try creating a new unlisted playlist
- Add at least one video with captions

### "Container keeps restarting"
- Check logs: `docker logs youtube-summarizer`
- Verify all API keys are correct in `.env`
- Make sure Docker has enough resources

---

## Next Steps

- ✅ Add more videos to your playlist
- ✅ Customize check interval in `.env`
- ✅ Share summaries with others
- ✅ Star the repo if you like it! ⭐

---

Need more help? Open an issue on GitHub!
