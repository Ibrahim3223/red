"""
Reddit Video Bot - Main Orchestrator
Generates YouTube Shorts from Reddit jokes/stories automatically.
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from reddit_scraper import RedditScraper, RedditPost
from tts_generator import TTSGenerator, TTSResult
from video_composer import VideoComposer, VideoConfig
from audio_mixer import AudioMixer
from youtube_uploader import YouTubeUploader
from title_generator import TitleGenerator


class RedditVideoBot:
    """Main bot that orchestrates the video generation pipeline."""

    def __init__(
        self,
        output_dir: str = None,
        assets_dir: str = None
    ):
        # Use project root for default paths
        output_dir = output_dir or str(PROJECT_ROOT / "output")
        assets_dir = assets_dir or str(PROJECT_ROOT / "assets")
        self.output_dir = Path(output_dir)
        self.assets_dir = Path(assets_dir)

        # Create directories
        (self.output_dir / "audio").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "videos").mkdir(parents=True, exist_ok=True)
        (self.assets_dir / "backgrounds").mkdir(parents=True, exist_ok=True)
        (self.assets_dir / "sounds" / "punchline").mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.scraper = RedditScraper()
        self.tts = TTSGenerator(
            voice="male_dramatic",
            output_dir=str(self.output_dir / "audio")
        )
        self.composer = VideoComposer(
            backgrounds_dir=str(self.assets_dir / "backgrounds"),
            output_dir=str(self.output_dir / "videos")
        )
        self.mixer = AudioMixer(
            sounds_dir=str(self.assets_dir / "sounds"),
            output_dir=str(self.output_dir / "audio")
        )
        self.uploader = YouTubeUploader()
        self.title_gen = TitleGenerator()

        # Track generated videos to avoid duplicates
        self.history_file = self.output_dir / "history.json"
        self.history = self._load_history()

    def _load_history(self) -> dict:
        """Loads generation history."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return {"generated_posts": [], "uploaded_videos": []}

    def _save_history(self):
        """Saves generation history."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def _is_already_generated(self, post_id: str) -> bool:
        """Checks if post was already used."""
        return post_id in self.history["generated_posts"]

    async def fetch_joke(self) -> Optional[RedditPost]:
        """Fetches a fresh joke from Reddit."""
        print("📥 Fetching joke from Reddit...")

        joke = self.scraper.get_top_joke(
            time_filter="week",  # Look at week for more options
            min_score=50,
            max_length=800,
            min_length=100  # Longer jokes for 10+ second videos
        )

        if not joke:
            print("❌ No suitable joke found")
            return None

        # Skip if already generated
        if self._is_already_generated(joke.post_id):
            print(f"⏭️ Skipping already used post: {joke.post_id}")
            jokes = self.scraper.get_multiple_jokes(count=10)
            for j in jokes:
                if not self._is_already_generated(j.post_id):
                    joke = j
                    break
            else:
                print("❌ All recent jokes already used")
                return None

        print(f"✅ Found joke from r/{joke.subreddit} (score: {joke.score})")
        return joke

    async def generate_audio(self, joke: RedditPost) -> TTSResult:
        """Generates TTS audio for the joke."""
        print("🎙️ Generating speech...")

        # Generate with pause between setup and punchline
        if joke.punchline:
            result = await self.tts.generate_with_pause(
                setup=joke.setup,
                punchline=joke.punchline,
                pause_duration=1.0,  # Longer pause for dramatic effect
                filename=f"{joke.post_id}.mp3"
            )
        else:
            result = await self.tts.generate_speech(
                joke.full_text,
                filename=f"{joke.post_id}.mp3"
            )

        print(f"✅ Audio generated: {result.total_duration:.1f}s")
        return result

    def generate_video(
        self,
        joke: RedditPost,
        tts_result: TTSResult
    ) -> str:
        """Generates the final video."""
        print("🎬 Composing video...")

        # Get sound effect path
        sfx_path = self.mixer.get_sound_effect("punchline")

        # Get punchline time for sound effect
        sfx_time = None
        if tts_result.segments:
            sfx_time = tts_result.segments[-1].start_time

        # Compose video with tweet-style overlay
        video_path = self.composer.compose_video(
            tts_result=tts_result,
            output_filename=f"{joke.post_id}.mp4",
            sound_effect_path=sfx_path,
            sound_effect_time=sfx_time,
            full_text=joke.full_text
        )

        print(f"✅ Video generated: {video_path}")
        return video_path

    def upload_to_youtube(
        self,
        video_path: str,
        joke: RedditPost,
        privacy: str = "public"
    ) -> dict:
        """Uploads video to YouTube."""
        print("📤 Uploading to YouTube...")

        # Authenticate
        try:
            self.uploader.authenticate_with_env()
        except ValueError:
            print("⚠️ YouTube credentials not found in env, trying local auth...")
            self.uploader.authenticate()

        # Generate title and description using Groq AI
        print("🤖 Generating title with AI...")
        title = self.title_gen.generate_title(joke.setup, joke.punchline)
        description = self.title_gen.generate_description(
            joke.setup,
            joke.punchline,
            joke.subreddit
        )

        print(f"📝 Title: {title}")

        # Upload
        result = self.uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=[joke.subreddit, "reddit", "jokes", "funny", "shorts", "comedy"],
            privacy_status=privacy
        )

        print(f"✅ Uploaded: {result['url']}")
        return result

    async def run_pipeline(
        self,
        upload: bool = True,
        privacy: str = "public"
    ) -> Optional[dict]:
        """
        Runs the full video generation pipeline.
        """
        print("\n" + "=" * 50)
        print("🤖 Reddit Video Bot Starting...")
        print("=" * 50 + "\n")

        # Step 1: Fetch joke
        joke = await self.fetch_joke()
        if not joke:
            return None

        print(f"\n📝 Joke:\n{joke.setup}")
        if joke.punchline:
            print(f"👉 {joke.punchline}")
        print()

        # Step 2: Generate audio
        tts_result = await self.generate_audio(joke)

        # Step 3: Generate video
        video_path = self.generate_video(joke, tts_result)

        # Track in history
        self.history["generated_posts"].append(joke.post_id)
        self._save_history()

        result = {
            "post_id": joke.post_id,
            "subreddit": joke.subreddit,
            "video_path": video_path,
            "duration": tts_result.total_duration
        }

        # Step 4: Upload (optional)
        if upload:
            try:
                upload_result = self.upload_to_youtube(video_path, joke, privacy)
                result["youtube_url"] = upload_result["url"]
                result["youtube_id"] = upload_result["video_id"]

                self.history["uploaded_videos"].append({
                    "post_id": joke.post_id,
                    "youtube_id": upload_result["video_id"],
                    "timestamp": datetime.now().isoformat()
                })
                self._save_history()
            except Exception as e:
                print(f"❌ Upload failed: {e}")
                result["upload_error"] = str(e)

        print("\n" + "=" * 50)
        print("✨ Pipeline Complete!")
        print("=" * 50)

        return result


async def main():
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Reddit Video Bot")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Generate video without uploading"
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "private", "unlisted"],
        default="public",
        help="YouTube privacy setting"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of videos to generate"
    )

    args = parser.parse_args()

    bot = RedditVideoBot()

    for i in range(args.count):
        if args.count > 1:
            print(f"\n📹 Generating video {i + 1}/{args.count}")

        result = await bot.run_pipeline(
            upload=not args.no_upload,
            privacy=args.privacy
        )

        if result:
            print(f"\n📊 Result: {json.dumps(result, indent=2)}")
        else:
            print("\n❌ Failed to generate video")


if __name__ == "__main__":
    asyncio.run(main())
