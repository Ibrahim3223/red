"""
YouTube Uploader Module
Handles automated video uploads to YouTube using the YouTube Data API v3.
"""

import os
import json
import time
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    """Uploads videos to YouTube using the Data API v3."""

    # YouTube Shorts hashtags for discoverability
    DEFAULT_HASHTAGS = [
        "#shorts", "#reddit", "#redditstories", "#funny",
        "#joke", "#comedy", "#viral", "#fyp"
    ]

    def __init__(
        self,
        credentials_file: str = "config/client_secrets.json",
        token_file: str = "config/youtube_token.json"
    ):
        """
        Initialize YouTube uploader.

        Args:
            credentials_file: Path to OAuth2 client secrets
            token_file: Path to save/load access token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube = None

    def authenticate(self) -> bool:
        """
        Authenticates with YouTube API.
        Uses saved token if available, otherwise initiates OAuth flow.

        Returns:
            True if authentication successful
        """
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                print(f"Error loading token: {e}")

        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Download OAuth2 credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=creds)
        return True

    def authenticate_with_env(self) -> bool:
        """
        Authenticates using credentials from environment variables.
        Useful for CI/CD environments like GitHub Actions.

        Environment variables needed:
        - YOUTUBE_CLIENT_ID
        - YOUTUBE_CLIENT_SECRET
        - YOUTUBE_REFRESH_TOKEN

        Returns:
            True if authentication successful
        """
        client_id = os.getenv('YOUTUBE_CLIENT_ID', '').strip()
        client_secret = os.getenv('YOUTUBE_CLIENT_SECRET', '').strip()
        refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN', '').strip()

        # Debug: show which credentials are missing
        missing = []
        if not client_id:
            missing.append("YOUTUBE_CLIENT_ID")
        if not client_secret:
            missing.append("YOUTUBE_CLIENT_SECRET")
        if not refresh_token:
            missing.append("YOUTUBE_REFRESH_TOKEN")

        if missing:
            raise ValueError(
                f"Missing YouTube credentials: {', '.join(missing)}\n"
                "Add these as GitHub repository secrets (Settings > Secrets > Actions)"
            )

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        # Refresh to get access token
        creds.refresh(Request())

        self.youtube = build('youtube', 'v3', credentials=creds)
        return True

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        category_id: str = "23",  # Comedy category
        privacy_status: str = "public",
        made_for_kids: bool = False,
        notify_subscribers: bool = True
    ) -> dict:
        """
        Uploads a video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (23 = Comedy)
            privacy_status: 'public', 'private', or 'unlisted'
            made_for_kids: Whether video is made for kids
            notify_subscribers: Whether to notify subscribers

        Returns:
            Dict with video ID and URL
        """
        if not self.youtube:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Truncate title if too long
        if len(title) > 100:
            title = title[:97] + "..."

        # Add hashtags to description for Shorts
        hashtags = " ".join(self.DEFAULT_HASHTAGS)
        full_description = f"{description}\n\n{hashtags}"

        # Prepare tags
        all_tags = tags or []
        all_tags.extend(["reddit", "shorts", "funny", "jokes", "comedy"])
        all_tags = list(set(all_tags))[:500]  # YouTube limit

        body = {
            'snippet': {
                'title': title,
                'description': full_description,
                'tags': all_tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids,
            }
        }

        # Create media upload
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        # Execute upload (notifySubscribers is a separate parameter, not part of body)
        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media,
            notifySubscribers=notify_subscribers
        )

        response = None
        retry_count = 0
        max_retries = 3

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504] and retry_count < max_retries:
                    retry_count += 1
                    sleep_time = random.uniform(1, 5) * retry_count
                    print(f"Server error, retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    raise

        video_id = response['id']
        video_url = f"https://youtube.com/shorts/{video_id}"

        print(f"Upload complete! Video URL: {video_url}")

        return {
            'video_id': video_id,
            'url': video_url,
            'title': title
        }

    def generate_title(
        self,
        joke_setup: str,
        subreddit: str = "Jokes"
    ) -> str:
        """
        Generates an engaging title for YouTube Shorts.

        Args:
            joke_setup: The setup of the joke
            subreddit: Source subreddit

        Returns:
            Generated title
        """
        # Clean and truncate setup
        setup = joke_setup.strip()

        # Title templates
        templates = [
            f"{setup}",
            f"😂 {setup}",
            f"Wait for it... {setup}",
            f"This joke is too good 😂 {setup}",
        ]

        title = random.choice(templates)

        # Ensure title isn't too long
        if len(title) > 100:
            title = setup[:97] + "..."

        return title

    def generate_description(
        self,
        joke_text: str,
        subreddit: str,
        post_url: str = ""
    ) -> str:
        """
        Generates video description.

        Args:
            joke_text: Full joke text
            subreddit: Source subreddit
            post_url: Original Reddit post URL

        Returns:
            Generated description
        """
        description = f"""🎭 Daily Reddit Jokes!

Source: r/{subreddit}

📱 Follow for more funny content!

⚠️ All content is sourced from Reddit. If you're the original author and want credit or removal, please contact us.
"""

        return description


def get_refresh_token(credentials_file: str = "config/client_secrets.json"):
    """
    Helper function to get refresh token for GitHub Actions setup.
    Run this locally once to get the refresh token.
    """
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_file,
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 50)
    print("SAVE THESE VALUES AS GITHUB SECRETS:")
    print("=" * 50)

    # Parse client secrets for IDs
    with open(credentials_file) as f:
        secrets = json.load(f)
        installed = secrets.get('installed', secrets.get('web', {}))

    print(f"\nYOUTUBE_CLIENT_ID={installed.get('client_id')}")
    print(f"YOUTUBE_CLIENT_SECRET={installed.get('client_secret')}")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print("\n" + "=" * 50)

    return creds.refresh_token


# For testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--get-token":
        # Get refresh token for GitHub Actions
        get_refresh_token()
    else:
        print("YouTube Uploader Module")
        print("=" * 30)
        print("\nUsage:")
        print("  python youtube_uploader.py --get-token")
        print("  (Run locally to get refresh token for GitHub Actions)")
