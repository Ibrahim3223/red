"""
Reddit Scraper Module
Fetches top jokes/funny posts from Reddit for video generation.
"""

import praw
import random
import re
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class RedditPost:
    """Represents a Reddit post with relevant data for video generation."""
    title: str
    body: str
    subreddit: str
    score: int
    url: str
    post_id: str

    @property
    def full_text(self) -> str:
        """Returns the complete text for TTS."""
        if self.body:
            return f"{self.title}\n\n{self.body}"
        return self.title

    @property
    def setup(self) -> str:
        """Returns the setup part (title or first part)."""
        return self.title

    @property
    def punchline(self) -> str:
        """Returns the punchline (body or second part)."""
        return self.body if self.body else ""


class RedditScraper:
    """Scrapes Reddit for funny/joke content suitable for short videos."""

    # Subreddits optimized for short content (~30 sec videos)
    SHORT_CONTENT_SUBREDDITS = [
        "Jokes",
        "dadjokes",
        "oneliners",
        "cleanjokes",
        "3amjokes",
    ]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "RedditVideoBot/1.0"
    ):
        self.reddit = praw.Reddit(
            client_id=client_id or os.getenv("REDDIT_CLIENT_ID"),
            client_secret=client_secret or os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=user_agent
        )

    def get_top_joke(
        self,
        subreddits: Optional[list[str]] = None,
        time_filter: str = "day",
        min_score: int = 100,
        max_length: int = 500,
        min_length: int = 50
    ) -> Optional[RedditPost]:
        """
        Fetches a top joke suitable for a short video.

        Args:
            subreddits: List of subreddits to search (defaults to SHORT_CONTENT_SUBREDDITS)
            time_filter: Time filter for top posts ('hour', 'day', 'week', 'month', 'year', 'all')
            min_score: Minimum upvote score
            max_length: Maximum character length for the full text
            min_length: Minimum character length

        Returns:
            RedditPost object or None if no suitable post found
        """
        subreddits = subreddits or self.SHORT_CONTENT_SUBREDDITS
        candidates = []

        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                for post in subreddit.top(time_filter=time_filter, limit=25):
                    # Skip stickied/pinned posts
                    if post.stickied:
                        continue

                    # Get clean text
                    title = self._clean_text(post.title)
                    body = self._clean_text(post.selftext) if post.selftext else ""
                    full_text = f"{title} {body}".strip()

                    # Check length constraints
                    if len(full_text) < min_length or len(full_text) > max_length:
                        continue

                    # Check score
                    if post.score < min_score:
                        continue

                    # Must have a punchline (body text) for joke subreddits
                    if subreddit_name in ["Jokes", "dadjokes", "cleanjokes", "3amjokes"]:
                        if not body:
                            continue

                    candidates.append(RedditPost(
                        title=title,
                        body=body,
                        subreddit=subreddit_name,
                        score=post.score,
                        url=post.url,
                        post_id=post.id
                    ))

            except Exception as e:
                print(f"Error fetching from r/{subreddit_name}: {e}")
                continue

        if not candidates:
            return None

        # Sort by score and pick from top 10 randomly (adds variety)
        candidates.sort(key=lambda x: x.score, reverse=True)
        top_candidates = candidates[:10]

        return random.choice(top_candidates)

    def get_multiple_jokes(
        self,
        count: int = 5,
        **kwargs
    ) -> list[RedditPost]:
        """
        Fetches multiple unique jokes.

        Args:
            count: Number of jokes to fetch
            **kwargs: Arguments passed to get_top_joke

        Returns:
            List of RedditPost objects
        """
        jokes = []
        seen_ids = set()
        attempts = 0
        max_attempts = count * 3

        while len(jokes) < count and attempts < max_attempts:
            joke = self.get_top_joke(**kwargs)
            attempts += 1

            if joke and joke.post_id not in seen_ids:
                jokes.append(joke)
                seen_ids.add(joke.post_id)

        return jokes

    def _clean_text(self, text: str) -> str:
        """Cleans Reddit text for TTS and display."""
        if not text:
            return ""

        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Remove Reddit formatting
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'~~([^~]+)~~', r'\1', text)  # Strikethrough
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)

        # Remove edit notes
        text = re.sub(r'edit:.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Clean whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


# For testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    scraper = RedditScraper()
    joke = scraper.get_top_joke()

    if joke:
        print(f"Subreddit: r/{joke.subreddit}")
        print(f"Score: {joke.score}")
        print(f"Setup: {joke.setup}")
        print(f"Punchline: {joke.punchline}")
    else:
        print("No suitable joke found")
