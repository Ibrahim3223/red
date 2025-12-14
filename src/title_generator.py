"""
Title Generator Module
Uses Groq API (Llama 3.1) to generate engaging titles and descriptions.
"""

import os
import requests
from typing import Optional


class TitleGenerator:
    """Generates viral titles and descriptions using Groq LLM."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-8b-instant"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️ GROQ_API_KEY not found, using fallback titles")

    def generate_title(self, joke_setup: str, joke_punchline: str) -> str:
        """
        Generates a viral YouTube Shorts title for the joke.
        """
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
            # Ensure max length
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
        """
        Generates an engaging YouTube description.
        """
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
                    "content": "You are a viral social media content creator. Generate catchy, engaging titles and descriptions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 150,
            "temperature": 0.8
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
        # Truncate and add emoji
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

    title = generator.generate_title(
        "Why don't scientists trust atoms?",
        "Because they make up everything!"
    )
    print(f"Title: {title}")

    desc = generator.generate_description(
        "Why don't scientists trust atoms?",
        "Because they make up everything!",
        "r/Jokes"
    )
    print(f"\nDescription:\n{desc}")
