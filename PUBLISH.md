# 📦 Publishing Guide

This guide helps you publish the YouTube Playlist Summarizer to GitHub and Docker Hub.

## ✅ Pre-Publish Checklist

Before publishing, make sure:

- [ ] All sensitive data is in `.gitignore`
- [ ] `.env` file is NOT in the repo
- [ ] `credentials.json` is NOT in the repo
- [ ] Test the app works with Docker
- [ ] README.md is complete
- [ ] LICENSE is included
- [ ] All docs are written

## 🐙 Publishing to GitHub

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `youtube-playlist-summarizer`
3. Description: "🎥 Automatically summarize YouTube videos with AI (Claude) and get beautiful email notifications"
4. Public or Private (your choice)
5. **Don't** initialize with README (we have one)
6. Click "Create repository"

### Step 2: Initialize Git (if not already)

```bash
cd ~/dev/youtube-summarizer-oauth2

# Initialize git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: YouTube Playlist Summarizer v1.0.0

Features:
- Claude Sonnet 4.5 integration
- Beautiful HTML emails with thumbnails
- Docker support with auto-restart
- OAuth2 authentication
- Smart formatting for list videos
- Markdown to HTML conversion"
```

### Step 3: Push to GitHub

```bash
# Add remote (replace 'yourusername' with your GitHub username)
git remote add origin https://github.com/yourusername/youtube-playlist-summarizer.git

# Push to main branch
git branch -M main
git push -u origin main
```

### Step 4: Set Up Repository Settings

On GitHub, go to your repository:

1. **Settings → General**
   - Add topics: `youtube`, `ai`, `claude`, `email`, `automation`, `docker`, `python`
   
2. **Settings → Features**
   - ✅ Enable Issues
   - ✅ Enable Discussions (optional)
   - ✅ Enable Wiki (optional)

3. **About Section** (top right)
   - Description: "🎥 Automatically summarize YouTube videos with AI and get email notifications"
   - Website: Your project URL (if any)
   - Topics: Add relevant tags

## 🐳 Publishing to Docker Hub

### Step 1: Create Docker Hub Account

1. Go to https://hub.docker.com/signup
2. Create free account
3. Verify email

### Step 2: Login to Docker

```bash
docker login
# Enter username and password
```

### Step 3: Build and Tag Image

```bash
cd ~/dev/youtube-summarizer-oauth2

# Build image (replace 'yourusername' with your Docker Hub username)
docker build -t yourusername/youtube-playlist-summarizer:latest .

# Also tag with version
docker tag yourusername/youtube-playlist-summarizer:latest \
           yourusername/youtube-playlist-summarizer:1.0.0
```

### Step 4: Push to Docker Hub

```bash
# Push latest
docker push yourusername/youtube-playlist-summarizer:latest

# Push version tag
docker push yourusername/youtube-playlist-summarizer:1.0.0
```

### Step 5: Update docker-compose.prod.yml

Edit `docker-compose.prod.yml` and replace `yourusername` with your actual username:

```yaml
services:
  youtube-summarizer:
    image: yourusername/youtube-playlist-summarizer:latest
```

Commit and push:
```bash
git add docker-compose.prod.yml
git commit -m "Update Docker Hub image reference"
git push
```

## 📝 Creating a Release

### On GitHub:

1. Go to your repository
2. Click "Releases" → "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `v1.0.0 - Initial Release`
5. Description:
   ```markdown
   ## 🎉 First Release!
   
   Features:
   - 🤖 Claude Sonnet 4.5 AI summaries
   - 📧 Beautiful HTML emails with thumbnails
   - 🔄 Auto-check every 30 minutes
   - 🐳 Docker support
   - 🔒 OAuth2 authentication
   
   [Full Changelog](CHANGELOG.md)
   
   ## Installation
   
   See [README.md](README.md) for setup instructions.
   
   ## Docker Hub
   
   `docker pull yourusername/youtube-playlist-summarizer:1.0.0`
   ```
6. Click "Publish release"

## 🎯 Post-Publish Tasks

### Update README with Badges

Add to the top of README.md:

```markdown
# YouTube Playlist Summarizer

[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/youtube-playlist-summarizer)](https://hub.docker.com/r/yourusername/youtube-playlist-summarizer)
[![GitHub stars](https://img.shields.io/github/stars/yourusername/youtube-playlist-summarizer)](https://github.com/yourusername/youtube-playlist-summarizer/stargazers)
[![License](https://img.shields.io/github/license/yourusername/youtube-playlist-summarizer)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/yourusername/youtube-playlist-summarizer)](https://github.com/yourusername/youtube-playlist-summarizer/issues)
```

### Share the Project

Share on:
- Reddit: r/SelfHosted, r/Python, r/youtube
- Hacker News
- Product Hunt
- Twitter/X
- LinkedIn
- Dev.to

### Monitor

- Watch GitHub for issues
- Check Docker Hub for pulls
- Respond to questions
- Update documentation as needed

## 🔄 Future Updates

When releasing new versions:

```bash
# Update CHANGELOG.md first
git add CHANGELOG.md
git commit -m "Update changelog for v1.1.0"

# Tag new version
git tag v1.1.0
git push origin v1.1.0

# Build and push Docker image
docker build -t yourusername/youtube-playlist-summarizer:1.1.0 .
docker tag yourusername/youtube-playlist-summarizer:1.1.0 \
           yourusername/youtube-playlist-summarizer:latest
docker push yourusername/youtube-playlist-summarizer:1.1.0
docker push yourusername/youtube-playlist-summarizer:latest

# Create GitHub release
# (Go to GitHub → Releases → Draft a new release)
```

## ✅ Verification

After publishing, test as a user:

```bash
# Clone as if you're a new user
git clone https://github.com/yourusername/youtube-playlist-summarizer.git
cd youtube-playlist-summarizer

# Follow setup instructions
./setup.sh

# Verify it works
docker logs youtube-summarizer -f
```

---

**Ready to publish?** Let's go! 🚀
