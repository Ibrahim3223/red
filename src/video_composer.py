"""
Video Composer Module
Creates Reddit story videos with tweet-style text overlays.
"""

import os
import random
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import textwrap

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop, resize
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from tts_generator import TTSResult, TTSSegment


@dataclass
class VideoConfig:
    """Configuration for video generation."""
    width: int = 1080
    height: int = 1920
    fps: int = 30
    # Tweet card settings
    card_width: int = 900
    card_padding: int = 40
    card_radius: int = 30
    card_bg_color: tuple = (255, 255, 255)  # White
    text_color: tuple = (15, 20, 25)  # Twitter dark text
    username_color: tuple = (83, 100, 113)  # Twitter gray
    highlight_color: tuple = (29, 155, 240)  # Twitter blue


class VideoComposer:
    """Composes videos with tweet-style text cards."""

    def __init__(
        self,
        backgrounds_dir: str = "assets/backgrounds",
        output_dir: str = "output/videos",
        config: Optional[VideoConfig] = None
    ):
        self.backgrounds_dir = Path(backgrounds_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or VideoConfig()
        self.font_path = self._find_font()
        self.font_bold_path = self._find_font(bold=True)

    def _find_font(self, bold: bool = False) -> str:
        """Finds a suitable font."""
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
            ]

        for font in candidates:
            if os.path.exists(font):
                return font

        # Return first candidate as fallback (PIL will use default)
        return candidates[0]

    def get_random_background(self) -> str:
        """Gets a random background video."""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        backgrounds = [
            f for f in self.backgrounds_dir.iterdir()
            if f.suffix.lower() in video_extensions
        ]

        if not backgrounds:
            raise FileNotFoundError(
                f"No background videos found in {self.backgrounds_dir}"
            )

        return str(random.choice(backgrounds))

    def create_tweet_card(
        self,
        text: str,
        username: str = "@RedditJokes",
        highlight_last_line: bool = False,
        show_all: bool = True
    ) -> Image.Image:
        """
        Creates a tweet-style card image.

        Args:
            text: The joke text
            username: Display username
            highlight_last_line: Highlight the punchline
            show_all: Show all text or just setup

        Returns:
            PIL Image of the tweet card
        """
        cfg = self.config

        # Load fonts
        try:
            font_large = ImageFont.truetype(self.font_bold_path, 52)
            font_text = ImageFont.truetype(self.font_path, 44)
            font_small = ImageFont.truetype(self.font_path, 32)
        except:
            font_large = ImageFont.load_default()
            font_text = font_large
            font_small = font_large

        # Wrap text
        wrapper = textwrap.TextWrapper(width=35)
        lines = []
        for paragraph in text.split('\n'):
            if paragraph.strip():
                wrapped = wrapper.wrap(paragraph.strip())
                lines.extend(wrapped)
                lines.append('')  # Empty line between paragraphs

        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()

        # Calculate card height
        line_height = 58
        header_height = 100
        footer_height = 80
        text_height = len(lines) * line_height
        card_height = header_height + text_height + footer_height + cfg.card_padding * 2

        # Create card with rounded corners
        card = Image.new('RGBA', (cfg.card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        # Draw rounded rectangle background
        self._draw_rounded_rect(
            draw,
            (0, 0, cfg.card_width, card_height),
            cfg.card_radius,
            cfg.card_bg_color + (250,)  # Slight transparency
        )

        # Draw profile picture placeholder (circle)
        avatar_x, avatar_y = cfg.card_padding, cfg.card_padding
        avatar_size = 60
        draw.ellipse(
            [avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
            fill=(29, 155, 240)  # Twitter blue
        )

        # Draw "R" in avatar
        try:
            avatar_font = ImageFont.truetype(self.font_bold_path, 36)
        except:
            avatar_font = font_large
        draw.text(
            (avatar_x + 18, avatar_y + 10),
            "R",
            font=avatar_font,
            fill=(255, 255, 255)
        )

        # Draw username
        name_x = avatar_x + avatar_size + 15
        draw.text(
            (name_x, avatar_y + 5),
            "Reddit Jokes",
            font=font_large,
            fill=cfg.text_color
        )
        draw.text(
            (name_x, avatar_y + 45),
            username,
            font=font_small,
            fill=cfg.username_color
        )

        # Draw text lines
        text_y = header_height + cfg.card_padding
        for i, line in enumerate(lines):
            if not line:
                continue

            is_last = i == len(lines) - 1 or (i == len(lines) - 2 and not lines[-1])

            if highlight_last_line and is_last:
                # Highlight punchline
                color = cfg.highlight_color
                try:
                    line_font = ImageFont.truetype(self.font_bold_path, 46)
                except:
                    line_font = font_text
            else:
                color = cfg.text_color
                line_font = font_text

            draw.text(
                (cfg.card_padding, text_y),
                line,
                font=line_font,
                fill=color
            )
            text_y += line_height

        # Draw footer (likes, retweets icons as text)
        footer_y = card_height - footer_height + 10
        footer_text = "❤️ 12.5K    🔁 3.2K    💬 892"
        draw.text(
            (cfg.card_padding, footer_y),
            footer_text,
            font=font_small,
            fill=cfg.username_color
        )

        return card

    def _draw_rounded_rect(
        self,
        draw: ImageDraw,
        coords: tuple,
        radius: int,
        fill: tuple
    ):
        """Draws a rounded rectangle."""
        x1, y1, x2, y2 = coords

        # Draw rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

        # Draw corners
        draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill)
        draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill)

    def create_tweet_clips(
        self,
        segments: list[TTSSegment],
        total_duration: float,
        full_text: str
    ) -> list[ImageClip]:
        """
        Creates tweet card clips that reveal text progressively.
        """
        clips = []
        cfg = self.config

        # Build text progressively
        accumulated_text = ""

        for i, segment in enumerate(segments):
            accumulated_text += segment.text + "\n"
            is_last = i == len(segments) - 1

            # Calculate duration
            if i + 1 < len(segments):
                duration = segments[i + 1].start_time - segment.start_time
            else:
                duration = total_duration - segment.start_time

            # Create tweet card
            card_img = self.create_tweet_card(
                text=accumulated_text.strip(),
                highlight_last_line=is_last
            )

            # Convert to numpy array for MoviePy
            card_array = np.array(card_img)

            # Create ImageClip
            clip = ImageClip(card_array)
            clip = clip.set_duration(duration)
            clip = clip.set_start(segment.start_time)

            # Center the card
            card_x = (cfg.width - card_img.width) // 2
            card_y = (cfg.height - card_img.height) // 2
            clip = clip.set_position((card_x, card_y))

            clips.append(clip)

        return clips

    def prepare_background(
        self,
        background_path: str,
        target_duration: float
    ) -> VideoFileClip:
        """Prepares background video: crops to vertical, loops if needed."""
        clip = VideoFileClip(background_path)

        clip_w, clip_h = clip.size
        target_ratio = self.config.width / self.config.height

        if clip_w / clip_h > target_ratio:
            new_width = int(clip_h * target_ratio)
            clip = crop(
                clip,
                x_center=clip_w / 2,
                y_center=clip_h / 2,
                width=new_width,
                height=clip_h
            )
        else:
            new_height = int(clip_w / target_ratio)
            clip = crop(
                clip,
                x_center=clip_w / 2,
                y_center=clip_h / 2,
                width=clip_w,
                height=new_height
            )

        clip = resize(clip, (self.config.width, self.config.height))

        # Loop if needed
        if clip.duration < target_duration:
            n_loops = int(target_duration / clip.duration) + 1
            clip = concatenate_videoclips([clip] * n_loops)

        clip = clip.subclip(0, target_duration)
        clip = clip.without_audio()

        return clip

    def compose_video(
        self,
        tts_result: TTSResult,
        output_filename: str = "output.mp4",
        background_path: Optional[str] = None,
        sound_effect_path: Optional[str] = None,
        sound_effect_time: Optional[float] = None,
        full_text: str = ""
    ) -> str:
        """Composes the final video with tweet-style overlay."""

        # Ensure minimum duration of 10 seconds
        min_duration = 10.0
        audio_duration = tts_result.total_duration

        if audio_duration < min_duration:
            # Add padding at the end
            total_duration = min_duration
        else:
            total_duration = audio_duration + 2.0

        # Get background
        if background_path is None:
            background_path = self.get_random_background()

        background = self.prepare_background(background_path, total_duration)

        # Create tweet card clips
        tweet_clips = self.create_tweet_clips(
            tts_result.segments,
            total_duration,
            full_text
        )

        # Compose layers
        video_layers = [background] + tweet_clips
        final_video = CompositeVideoClip(video_layers)

        # Audio
        tts_audio = AudioFileClip(tts_result.audio_file)
        audio_clips = [tts_audio]

        # Sound effect
        if sound_effect_path and os.path.exists(sound_effect_path):
            sfx = AudioFileClip(sound_effect_path)
            if sound_effect_time is None and tts_result.segments:
                sound_effect_time = tts_result.segments[-1].start_time
            if sound_effect_time is not None:
                sfx = sfx.set_start(sound_effect_time)
                sfx = sfx.volumex(0.5)
                audio_clips.append(sfx)

        final_audio = CompositeAudioClip(audio_clips)
        final_video = final_video.set_audio(final_audio)
        final_video = final_video.set_duration(total_duration)

        # Export
        output_path = self.output_dir / output_filename
        final_video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            threads=4
        )

        # Cleanup
        background.close()
        tts_audio.close()
        final_video.close()

        return str(output_path)


# For testing
if __name__ == "__main__":
    print("Video composer with tweet-style cards loaded!")
