"""
Reddit Scraper Module (No API Key Required)
Fetches top jokes from Reddit using public JSON endpoints.
Falls back to free Joke APIs if Reddit is unavailable.
"""

import random
import re
import time
import requests
from dataclasses import dataclass
from typing import Optional


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
    """
    Scrapes Reddit for jokes using public JSON endpoints.
    No API key required!
    """

    # Reddit JSON endpoint base URL
    BASE_URL = "https://www.reddit.com"

    # User agent (required by Reddit)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Subreddits for short joke content
    SHORT_CONTENT_SUBREDDITS = [
        "Jokes",
        "dadjokes",
        "oneliners",
        "cleanjokes",
        "3amjokes",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT
        })

    def _fetch_subreddit_json(
        self,
        subreddit: str,
        sort: str = "top",
        time_filter: str = "day",
        limit: int = 25
    ) -> list[dict]:
        """
        Fetches posts from a subreddit using JSON endpoint.
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = {
            "limit": limit,
            "t": time_filter
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            return [post["data"] for post in posts]

        except requests.RequestException as e:
            print(f"Error fetching r/{subreddit}: {e}")
            return []

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
        """
        subreddits = subreddits or self.SHORT_CONTENT_SUBREDDITS
        candidates = []

        for subreddit_name in subreddits:
            posts = self._fetch_subreddit_json(
                subreddit_name,
                sort="top",
                time_filter=time_filter,
                limit=25
            )

            # Small delay to avoid rate limiting
            time.sleep(0.5)

            for post in posts:
                # Skip stickied/pinned posts
                if post.get("stickied", False):
                    continue

                # Get clean text
                title = self._clean_text(post.get("title", ""))
                body = self._clean_text(post.get("selftext", ""))
                full_text = f"{title} {body}".strip()

                # Check length constraints
                if len(full_text) < min_length or len(full_text) > max_length:
                    continue

                # Check score
                score = post.get("score", 0)
                if score < min_score:
                    continue

                # Must have a punchline (body text) for joke subreddits
                if subreddit_name in ["Jokes", "dadjokes", "cleanjokes", "3amjokes"]:
                    if not body or body == "[removed]" or body == "[deleted]":
                        continue

                candidates.append(RedditPost(
                    title=title,
                    body=body,
                    subreddit=subreddit_name,
                    score=score,
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    post_id=post.get("id", "")
                ))

        if not candidates:
            print("No jokes found from Reddit, trying backup APIs...")
            return self._get_joke_from_api()

        # Sort by score and pick from top 10 randomly
        candidates.sort(key=lambda x: x.score, reverse=True)
        top_candidates = candidates[:10]

        return random.choice(top_candidates)

    def _get_joke_from_api(self) -> Optional[RedditPost]:
        """
        Backup: Fetches a joke from free Joke APIs.
        """
        apis = [
            self._fetch_from_jokeapi,
            self._fetch_from_official_joke_api,
            self._fetch_from_icanhazdadjoke,
        ]

        random.shuffle(apis)

        for api_func in apis:
            try:
                joke = api_func()
                if joke:
                    return joke
            except Exception as e:
                print(f"API error: {e}")
                continue

        return None

    def _fetch_from_jokeapi(self) -> Optional[RedditPost]:
        """Fetches from JokeAPI (https://jokeapi.dev)"""
        url = "https://v2.jokeapi.dev/joke/Miscellaneous,Pun,Programming"
        params = {
            "blacklistFlags": "nsfw,religious,political,racist,sexist",
            "type": "twopart"
        }

        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return None

        return RedditPost(
            title=data.get("setup", ""),
            body=data.get("delivery", ""),
            subreddit="JokeAPI",
            score=0,
            url="https://jokeapi.dev",
            post_id=f"jokeapi_{random.randint(1000, 9999)}"
        )

    def _fetch_from_official_joke_api(self) -> Optional[RedditPost]:
        """Fetches from Official Joke API"""
        url = "https://official-joke-api.appspot.com/random_joke"

        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        return RedditPost(
            title=data.get("setup", ""),
            body=data.get("punchline", ""),
            subreddit="OfficialJokeAPI",
            score=0,
            url="https://official-joke-api.appspot.com",
            post_id=f"ojapi_{data.get('id', random.randint(1000, 9999))}"
        )

    def _fetch_from_icanhazdadjoke(self) -> Optional[RedditPost]:
        """Fetches from icanhazdadjoke API"""
        url = "https://icanhazdadjoke.com/"
        headers = {"Accept": "application/json"}

        response = self.session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        joke_text = data.get("joke", "")

        # Try to split into setup and punchline
        if "?" in joke_text:
            parts = joke_text.split("?", 1)
            setup = parts[0] + "?"
            punchline = parts[1].strip() if len(parts) > 1 else ""
        else:
            setup = joke_text
            punchline = ""

        return RedditPost(
            title=setup,
            body=punchline,
            subreddit="icanhazdadjoke",
            score=0,
            url="https://icanhazdadjoke.com",
            post_id=data.get("id", f"dad_{random.randint(1000, 9999)}")
        )

    def get_multiple_jokes(
        self,
        count: int = 5,
        **kwargs
    ) -> list[RedditPost]:
        """Fetches multiple unique jokes."""
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

            time.sleep(1)

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
        text = re.sub(r'&#x200B;', '', text)

        # Remove edit notes
        text = re.sub(r'edit:.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Clean whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


# For testing
if __name__ == "__main__":
    scraper = RedditScraper()

    print("Fetching joke (no API key required)...")
    joke = scraper.get_top_joke()

    if joke:
        print(f"\n✅ Found joke!")
        print(f"Source: r/{joke.subreddit}")
        print(f"Score: {joke.score}")
        print(f"\nSetup: {joke.setup}")
        print(f"Punchline: {joke.punchline}")
    else:
        print("❌ No suitable joke found")
