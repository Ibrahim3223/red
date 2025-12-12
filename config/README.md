# Configuration Directory

This folder stores OAuth credentials for YouTube API.

## Files (not committed to git)

- `client_secrets.json` - OAuth 2.0 credentials from Google Cloud Console
- `youtube_token.json` - Auto-generated access token (created after first auth)

## Setup Instructions

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3**

### 2. Create OAuth Credentials

1. Go to APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Select "Desktop application"
4. Download JSON and save as `client_secrets.json` in this folder

### 3. Get Refresh Token

Run locally:
```bash
python src/youtube_uploader.py --get-token
```

This will:
1. Open browser for OAuth consent
2. Print the credentials needed for GitHub Secrets

### 4. Add to GitHub Secrets

Go to your repo Settings → Secrets → Actions and add:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

## Security

⚠️ Never commit `client_secrets.json` or `youtube_token.json` to git!

These files are already in `.gitignore`.
