"""
Video Composer Module
Creates Reddit story videos with realistic tweet-style text overlays.
"""

import os
import random
from pathlib import Path
from typing import Optional, Tuple
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
    card_width: int = 980
    card_margin: int = 50
    card_radius: int = 24
    card_bg_color: tuple = (255, 255, 255)
    text_color: tuple = (15, 20, 25)
    secondary_color: tuple = (83, 100, 113)
    accent_color: tuple = (29, 155, 240)  # Twitter blue
    like_color: tuple = (249, 24, 128)  # Pink for likes
    retweet_color: tuple = (0, 186, 124)  # Green for retweets


class VideoComposer:
    """Composes videos with realistic tweet-style text cards."""

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

        # Import title generator for usernames
        try:
            from title_generator import TitleGenerator
            self.title_gen = TitleGenerator()
        except:
            self.title_gen = None

    def _find_font(self, bold: bool = False) -> str:
        """Finds a suitable font."""
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/seguisb.ttf",
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
        return candidates[0]

    def get_random_background(self) -> str:
        """Gets a random background video."""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        backgrounds = [
            f for f in self.backgrounds_dir.iterdir()
            if f.suffix.lower() in video_extensions
        ]
        if not backgrounds:
            raise FileNotFoundError(f"No background videos found in {self.backgrounds_dir}")
        return str(random.choice(backgrounds))

    def _get_user_info(self) -> Tuple[str, str, str, str, str]:
        """Gets user info (name, handle, likes, retweets, comments)."""
        if self.title_gen:
            name, handle = self.title_gen.generate_username()
            likes, rts, comments = self.title_gen.generate_engagement_stats()
        else:
            name, handle = "JokeMaster", "@joke_master"
            likes, rts, comments = "24.5K", "5.2K", "1.8K"
        return name, handle, likes, rts, comments

    def create_tweet_card(
        self,
        text: str,
        display_name: str,
        handle: str,
        likes: str,
        retweets: str,
        comments: str,
        highlight_last: bool = False
    ) -> Image.Image:
        """Creates a realistic tweet-style card."""
        cfg = self.config

        # Load fonts
        try:
            font_name = ImageFont.truetype(self.font_bold_path, 42)
            font_handle = ImageFont.truetype(self.font_path, 36)
            font_text = ImageFont.truetype(self.font_path, 48)
            font_text_bold = ImageFont.truetype(self.font_bold_path, 48)
            font_stats = ImageFont.truetype(self.font_path, 32)
        except:
            font_name = font_handle = font_text = font_text_bold = font_stats = ImageFont.load_default()

        # Wrap text into lines
        wrapper = textwrap.TextWrapper(width=32)
        lines = []
        for paragraph in text.split('\n'):
            if paragraph.strip():
                wrapped = wrapper.wrap(paragraph.strip())
                lines.extend(wrapped)

        # Calculate dimensions
        line_height = 62
        padding = 40
        header_height = 90
        text_height = max(len(lines) * line_height, 120)
        footer_height = 70
        total_height = header_height + text_height + footer_height + padding * 2

        # Create card with shadow
        shadow_offset = 8
        full_width = cfg.card_width + shadow_offset * 2
        full_height = total_height + shadow_offset * 2

        # Create image with transparency
        img = Image.new('RGBA', (full_width, full_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw shadow
        shadow_color = (0, 0, 0, 40)
        self._draw_rounded_rect(
            draw,
            (shadow_offset + 4, shadow_offset + 4,
             cfg.card_width + shadow_offset + 4, total_height + shadow_offset + 4),
            cfg.card_radius,
            shadow_color
        )

        # Draw main card
        card_rect = (shadow_offset, shadow_offset,
                     cfg.card_width + shadow_offset, total_height + shadow_offset)
        self._draw_rounded_rect(draw, card_rect, cfg.card_radius, cfg.card_bg_color + (255,))

        # Starting positions
        x_start = shadow_offset + padding
        y_pos = shadow_offset + padding

        # Draw avatar (gradient circle)
        avatar_size = 56
        avatar_x = x_start
        avatar_y = y_pos

        # Create gradient avatar
        for i in range(avatar_size):
            alpha = int(255 * (1 - i / avatar_size * 0.3))
            color = (
                min(255, cfg.accent_color[0] + i),
                min(255, cfg.accent_color[1] + i // 2),
                min(255, cfg.accent_color[2]),
                alpha
            )
            draw.ellipse(
                [avatar_x + i//4, avatar_y + i//4,
                 avatar_x + avatar_size - i//4, avatar_y + avatar_size - i//4],
                fill=color[:3]
            )

        # Draw letter in avatar
        letter = display_name[0].upper() if display_name else "U"
        try:
            letter_font = ImageFont.truetype(self.font_bold_path, 28)
        except:
            letter_font = font_name
        bbox = draw.textbbox((0, 0), letter, font=letter_font)
        letter_w = bbox[2] - bbox[0]
        letter_h = bbox[3] - bbox[1]
        draw.text(
            (avatar_x + (avatar_size - letter_w) // 2,
             avatar_y + (avatar_size - letter_h) // 2 - 2),
            letter,
            font=letter_font,
            fill=(255, 255, 255)
        )

        # Draw display name and handle
        name_x = avatar_x + avatar_size + 16
        draw.text((name_x, y_pos + 2), display_name, font=font_name, fill=cfg.text_color)

        # Draw verified badge
        badge_x = name_x + draw.textlength(display_name, font=font_name) + 8
        badge_y = y_pos + 8
        badge_size = 22
        draw.ellipse(
            [badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
            fill=cfg.accent_color
        )
        # Checkmark
        draw.text((badge_x + 4, badge_y + 1), "✓", font=ImageFont.truetype(self.font_bold_path, 16) if os.path.exists(self.font_bold_path) else font_stats, fill=(255, 255, 255))

        # Handle
        draw.text((name_x, y_pos + 38), handle, font=font_handle, fill=cfg.secondary_color)

        # Draw text content
        y_pos = shadow_offset + padding + header_height
        for i, line in enumerate(lines):
            is_last_line = i == len(lines) - 1

            if highlight_last and is_last_line:
                draw.text((x_start, y_pos), line, font=font_text_bold, fill=cfg.accent_color)
            else:
                draw.text((x_start, y_pos), line, font=font_text, fill=cfg.text_color)
            y_pos += line_height

        # Draw footer with engagement stats
        footer_y = total_height + shadow_offset - footer_height + 10
        stat_x = x_start

        # Comments icon and count
        draw.text((stat_x, footer_y), "💬", font=font_stats, fill=cfg.secondary_color)
        draw.text((stat_x + 35, footer_y), comments, font=font_stats, fill=cfg.secondary_color)

        # Retweets
        stat_x += 140
        draw.text((stat_x, footer_y), "🔁", font=font_stats, fill=cfg.retweet_color)
        draw.text((stat_x + 35, footer_y), retweets, font=font_stats, fill=cfg.secondary_color)

        # Likes
        stat_x += 140
        draw.text((stat_x, footer_y), "❤️", font=font_stats, fill=cfg.like_color)
        draw.text((stat_x + 35, footer_y), likes, font=font_stats, fill=cfg.secondary_color)

        # Views/Share
        stat_x += 140
        draw.text((stat_x, footer_y), "📊", font=font_stats, fill=cfg.secondary_color)
        views = f"{random.randint(100, 500)}K"
        draw.text((stat_x + 35, footer_y), views, font=font_stats, fill=cfg.secondary_color)

        return img

    def _draw_rounded_rect(self, draw, coords, radius, fill):
        """Draws a rounded rectangle."""
        x1, y1, x2, y2 = coords
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
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
        """Creates tweet card clips that reveal text progressively."""
        clips = []
        cfg = self.config

        # Get user info once for consistency
        name, handle, likes, rts, comments = self._get_user_info()

        accumulated_text = ""
        for i, segment in enumerate(segments):
            accumulated_text += segment.text + "\n"
            is_last = i == len(segments) - 1

            if i + 1 < len(segments):
                duration = segments[i + 1].start_time - segment.start_time
            else:
                duration = total_duration - segment.start_time

            card_img = self.create_tweet_card(
                text=accumulated_text.strip(),
                display_name=name,
                handle=handle,
                likes=likes,
                retweets=rts,
                comments=comments,
                highlight_last=is_last
            )

            card_array = np.array(card_img)
            clip = ImageClip(card_array)
            clip = clip.set_duration(duration)
            clip = clip.set_start(segment.start_time)

            # Center the card
            card_x = (cfg.width - card_img.width) // 2
            card_y = (cfg.height - card_img.height) // 2
            clip = clip.set_position((card_x, card_y))

            clips.append(clip)

        return clips

    def prepare_background(self, background_path: str, target_duration: float) -> VideoFileClip:
        """Prepares background video."""
        clip = VideoFileClip(background_path)
        clip_w, clip_h = clip.size
        target_ratio = self.config.width / self.config.height

        if clip_w / clip_h > target_ratio:
            new_width = int(clip_h * target_ratio)
            clip = crop(clip, x_center=clip_w/2, y_center=clip_h/2, width=new_width, height=clip_h)
        else:
            new_height = int(clip_w / target_ratio)
            clip = crop(clip, x_center=clip_w/2, y_center=clip_h/2, width=clip_w, height=new_height)

        clip = resize(clip, (self.config.width, self.config.height))

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

        # Minimum 10 seconds
        min_duration = 10.0
        audio_duration = tts_result.total_duration
        total_duration = max(min_duration, audio_duration + 2.0)

        if background_path is None:
            background_path = self.get_random_background()

        background = self.prepare_background(background_path, total_duration)
        tweet_clips = self.create_tweet_clips(tts_result.segments, total_duration, full_text)

        video_layers = [background] + tweet_clips
        final_video = CompositeVideoClip(video_layers)

        tts_audio = AudioFileClip(tts_result.audio_file)
        audio_clips = [tts_audio]

        if sound_effect_path and os.path.exists(sound_effect_path):
            sfx = AudioFileClip(sound_effect_path)
            if sound_effect_time is None and tts_result.segments:
                sound_effect_time = tts_result.segments[-1].start_time
            if sound_effect_time is not None:
                sfx = sfx.set_start(sound_effect_time).volumex(0.5)
                audio_clips.append(sfx)

        final_audio = CompositeAudioClip(audio_clips)
        final_video = final_video.set_audio(final_audio)
        final_video = final_video.set_duration(total_duration)

        output_path = self.output_dir / output_filename
        final_video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            threads=4
        )

        background.close()
        tts_audio.close()
        final_video.close()

        return str(output_path)


if __name__ == "__main__":
    print("Video composer with tweet-style cards loaded!")
