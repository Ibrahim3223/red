# Reddit Video Bot 🎬

Automatically generates YouTube Shorts from Reddit jokes using GitHub Actions.

## Features

- 📥 Fetches top jokes from Reddit (r/Jokes, r/dadjokes, etc.)
- 🎙️ Text-to-speech with natural voices (Edge TTS - free)
- 🎮 Background gameplay videos (Minecraft, Subway Surfer style)
- ✨ Animated text overlays synced with speech
- 🔊 Punchline sound effects
- 📤 Auto-upload to YouTube
- ⏰ Scheduled runs via GitHub Actions (2x daily)

## Quick Setup

### 1. Fork/Clone Repository

```bash
git clone https://github.com/yourusername/reddit-video-bot.git
cd reddit-video-bot
```

### 2. Add Background Videos

Add `.mp4` video files to `assets/backgrounds/`:
- Minecraft parkour
- Subway Surfer gameplay
- GTA gameplay
- Any satisfying/engaging vertical video

> **Tip:** Use royalty-free gameplay from YouTube (search "free to use gameplay footage")

### 3. Add Sound Effects (Optional)

Add punchline sound effects to `assets/sounds/punchline/`:
- Rimshot
- Vine boom
- Bruh sound effect
- etc.

### 4. Get Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script"
4. Fill in name and redirect URI (use `http://localhost:8080`)
5. Copy `client_id` (under app name) and `client_secret`

### 5. Get YouTube API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `client_secrets.json` to `config/` folder

Get refresh token locally:
```bash
pip install -r requirements.txt
python src/youtube_uploader.py --get-token
```

This will output the values you need for GitHub Secrets.

### 6. Configure GitHub Secrets

Add these secrets to your repository (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `REDDIT_CLIENT_ID` | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit app secret |
| `YOUTUBE_CLIENT_ID` | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | Google OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | YouTube refresh token (from step 5) |

### 7. Enable GitHub Actions

The workflow will automatically run twice daily (8:00 and 20:00 UTC).

You can also trigger manually:
1. Go to Actions tab
2. Select "Generate Reddit Video"
3. Click "Run workflow"

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Run locally (without upload)
python src/main.py --no-upload

# Run with upload
python src/main.py --privacy unlisted
```

## Project Structure

```
reddit-video-bot/
├── .github/
│   └── workflows/
│       └── generate-video.yml    # GitHub Actions workflow
├── assets/
│   ├── backgrounds/              # Background videos (.mp4)
│   ├── sounds/
│   │   └── punchline/           # Sound effects
│   └── fonts/                   # Custom fonts (optional)
├── config/
│   └── client_secrets.json      # YouTube OAuth (local only)
├── src/
│   ├── main.py                  # Main orchestrator
│   ├── reddit_scraper.py        # Reddit API integration
│   ├── tts_generator.py         # Text-to-speech (Edge TTS)
│   ├── video_composer.py        # Video generation (MoviePy)
│   ├── audio_mixer.py           # Sound effects
│   └── youtube_uploader.py      # YouTube upload
├── output/                      # Generated files (gitignored)
├── requirements.txt
└── README.md
```

## Configuration

### TTS Voices

Available voices in `tts_generator.py`:
- `male_us` - en-US-GuyNeural
- `female_us` - en-US-JennyNeural
- `male_uk` - en-GB-RyanNeural
- `female_uk` - en-GB-SoniaNeural
- `male_dramatic` - en-US-ChristopherNeural (default)
- `female_dramatic` - en-US-AriaNeural

### Subreddits

Default joke sources in `reddit_scraper.py`:
- r/Jokes
- r/dadjokes
- r/oneliners
- r/cleanjokes
- r/3amjokes

## Costs

**$0** - Everything is free!

| Service | Cost |
|---------|------|
| Reddit API | Free |
| Edge TTS | Free |
| GitHub Actions | Free (2000 min/month) |
| YouTube API | Free |

## Troubleshooting

### "No background videos found"
Add `.mp4` files to `assets/backgrounds/`

### "YouTube upload failed"
1. Check your OAuth credentials
2. Make sure refresh token is valid
3. Re-run `python src/youtube_uploader.py --get-token`

### "No suitable joke found"
Reddit API might be rate-limited. Try again later.

### Video quality issues
- Use 1080x1920 (vertical) background videos
- Ensure backgrounds are at least 30 seconds long

## License

MIT License - feel free to use and modify!

## Disclaimer

- Content is sourced from Reddit and belongs to original authors
- Ensure you comply with Reddit's and YouTube's Terms of Service
- This is for educational purposes
