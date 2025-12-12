"""
Reddit Video Bot
Automatically generates YouTube Shorts from Reddit jokes.
"""

from .reddit_scraper import RedditScraper, RedditPost
from .tts_generator import TTSGenerator, TTSResult, TTSSegment
from .video_composer import VideoComposer, VideoConfig
from .audio_mixer import AudioMixer
from .youtube_uploader import YouTubeUploader
from .main import RedditVideoBot

__all__ = [
    "RedditScraper",
    "RedditPost",
    "TTSGenerator",
    "TTSResult",
    "TTSSegment",
    "VideoComposer",
    "VideoConfig",
    "AudioMixer",
    "YouTubeUploader",
    "RedditVideoBot",
]

__version__ = "1.0.0"
