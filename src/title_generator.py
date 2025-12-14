"""
Title Generator Module
Uses Groq API (Llama 3.1) to generate engaging titles, descriptions, and usernames.
"""

import os
import random
import requests
from typing import Optional, Tuple


class TitleGenerator:
    """Generates viral titles, descriptions, and fake usernames using Groq LLM."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-8b-instant"

    # Fallback usernames if API unavailable
    FALLBACK_NAMES = [
        ("DadJokeDave", "@dadjoke_dave"),
        ("ComedyKing", "@comedy_king_"),
        ("JokeMaster3000", "@jokemaster3k"),
        ("PunnyGuy", "@punny_guy_"),
        ("LaughFactory", "@laugh_factory"),
        ("HumorHub", "@humor_hub_"),
        ("JestQueen", "@jest_queen"),
        ("WittyWilson", "@witty_wilson"),
        ("GiggleGuru", "@giggle_guru_"),
        ("ChuckleChamp", "@chuckle_champ"),
        ("SassySteve", "@sassy_steve_"),
        ("QuipQueen", "@quip_queen_"),
        ("BanterBoss", "@banter_boss"),
        ("JokeJunkie", "@joke_junkie_"),
        ("PunchlinePro", "@punchline_pro"),
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️ GROQ_API_KEY not found, using fallback values")

    def generate_username(self) -> Tuple[str, str]:
        """
        Generates a realistic Twitter/X style username.

        Returns:
            Tuple of (display_name, @handle)
        """
        if not self.api_key:
            return random.choice(self.FALLBACK_NAMES)

        prompt = """Generate a realistic, funny Twitter/X username for someone who posts jokes.

Rules:
- Create a display name (like "Comedy Central" or "Dad Joke Dan")
- Create a handle starting with @ (like @comedy_central or @dadjoke_dan)
- Make it sound like a real person or comedy account
- Keep display name under 20 characters
- Keep handle under 15 characters (not counting @)
- Be creative and varied

Return in this exact format (nothing else):
DisplayName
@handle"""

        try:
            response = self._call_groq(prompt)
            lines = response.strip().split('\n')
            if len(lines) >= 2:
                display_name = lines[0].strip()[:20]
                handle = lines[1].strip()
                if not handle.startswith('@'):
                    handle = '@' + handle
                handle = handle[:16]  # @+ 15 chars max
                return (display_name, handle)
        except Exception as e:
            print(f"⚠️ Username generation error: {e}")

        return random.choice(self.FALLBACK_NAMES)

    def generate_title(self, joke_setup: str, joke_punchline: str) -> str:
        """Generates a viral YouTube Shorts title for the joke."""
        if not self.api_key:
            return self._fallback_title(joke_setup)

        prompt = f"""Generate a short, viral YouTube Shorts title for this joke.
The title should be catchy, use emojis, and make people want to watch.
Maximum 60 characters. Don't include the punchline.

Joke setup: {joke_setup}
Punchline: {joke_punchline}

Rules:
- Use 1-2 emojis max
- Create curiosity/suspense
- Don't spoil the punchline
- Keep it under 60 characters

Return ONLY the title, nothing else."""

        try:
            response = self._call_groq(prompt)
            title = response.strip().strip('"').strip("'")
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        except Exception as e:
            print(f"⚠️ Groq API error: {e}")
            return self._fallback_title(joke_setup)

    def generate_description(
        self,
        joke_setup: str,
        joke_punchline: str,
        source: str = "Reddit"
    ) -> str:
        """Generates an engaging YouTube description."""
        if not self.api_key:
            return self._fallback_description(source)

        prompt = f"""Write a short YouTube Shorts description for this joke video.
Include relevant hashtags and a call to action.

Joke: {joke_setup} - {joke_punchline}
Source: {source}

Rules:
- 2-3 sentences max
- Include 5-7 relevant hashtags
- Add a simple call to action (like, follow, etc.)
- Keep it casual and fun

Return ONLY the description, nothing else."""

        try:
            response = self._call_groq(prompt)
            return response.strip()
        except Exception as e:
            print(f"⚠️ Groq API error: {e}")
            return self._fallback_description(source)

    def generate_engagement_stats(self) -> Tuple[str, str, str]:
        """
        Generates realistic looking engagement numbers.

        Returns:
            Tuple of (likes, retweets, comments)
        """
        # Generate realistic viral-ish numbers
        likes = random.randint(5000, 150000)
        retweets = random.randint(int(likes * 0.1), int(likes * 0.4))
        comments = random.randint(int(likes * 0.05), int(likes * 0.15))

        def format_number(n: int) -> str:
            if n >= 1000000:
                return f"{n/1000000:.1f}M"
            elif n >= 1000:
                return f"{n/1000:.1f}K"
            return str(n)

        return (format_number(likes), format_number(retweets), format_number(comments))

    def _call_groq(self, prompt: str) -> str:
        """Makes API call to Groq."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a creative social media expert. Be concise and follow instructions exactly."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 150,
            "temperature": 0.9
        }

        response = requests.post(
            self.GROQ_API_URL,
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _fallback_title(self, joke_setup: str) -> str:
        """Fallback title when API is unavailable."""
        setup = joke_setup[:50] if len(joke_setup) > 50 else joke_setup
        if not setup.endswith("?"):
            setup = setup.rstrip(".!") + "..."
        return f"😂 {setup}"

    def _fallback_description(self, source: str) -> str:
        """Fallback description when API is unavailable."""
        return f"""😂 Daily jokes to brighten your day!

Follow for more funny content!

#shorts #funny #jokes #comedy #humor #viral #fyp #lol"""


# For testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    generator = TitleGenerator()

    # Test username generation
    name, handle = generator.generate_username()
    print(f"Username: {name} ({handle})")

    # Test engagement stats
    likes, rts, comments = generator.generate_engagement_stats()
    print(f"Stats: {likes} likes, {rts} RTs, {comments} comments")

    # Test title
    title = generator.generate_title(
        "Why don't scientists trust atoms?",
        "Because they make up everything!"
    )
    print(f"Title: {title}")
