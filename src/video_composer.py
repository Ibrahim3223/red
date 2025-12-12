"""
Video Composer Module
Creates Reddit story videos with background gameplay and animated text overlays.
"""

import os
import random
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    ColorClip
)
from moviepy.video.fx.all import crop, resize
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from tts_generator import TTSResult, TTSSegment


@dataclass
class VideoConfig:
    """Configuration for video generation."""
    width: int = 1080  # YouTube Shorts width
    height: int = 1920  # YouTube Shorts height
    fps: int = 30
    font_size: int = 60
    font_color: str = "white"
    font_stroke_color: str = "black"
    font_stroke_width: int = 3
    text_box_padding: int = 40
    text_box_color: tuple = (0, 0, 0, 180)  # Semi-transparent black
    text_position: str = "center"  # 'center', 'top', 'bottom'


class VideoComposer:
    """Composes videos from background clips, audio, and text overlays."""

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

        # Try to use a good font, fallback to default
        self.font_path = self._find_font()

    def _find_font(self) -> Optional[str]:
        """Finds a suitable font for text rendering."""
        font_candidates = [
            "assets/fonts/Montserrat-Bold.ttf",
            "assets/fonts/Arial-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/impact.ttf",
        ]

        for font in font_candidates:
            if os.path.exists(font):
                return font

        return None  # Will use MoviePy default

    def get_random_background(self) -> str:
        """Gets a random background video from the backgrounds directory."""
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

    def create_text_clip(
        self,
        text: str,
        duration: float,
        start_time: float = 0,
        highlight: bool = False
    ) -> TextClip:
        """
        Creates a styled text clip.

        Args:
            text: Text to display
            duration: Duration in seconds
            start_time: When the clip should appear
            highlight: Whether to highlight (for punchline)

        Returns:
            Styled TextClip
        """
        font_size = self.config.font_size
        color = "yellow" if highlight else self.config.font_color

        # Create text clip
        txt_clip = TextClip(
            text,
            fontsize=font_size,
            color=color,
            font=self.font_path or "Arial-Bold",
            stroke_color=self.config.font_stroke_color,
            stroke_width=self.config.font_stroke_width,
            method='caption',
            size=(self.config.width - 100, None),
            align='center'
        )

        txt_clip = txt_clip.set_duration(duration)
        txt_clip = txt_clip.set_start(start_time)

        return txt_clip

    def create_animated_text_sequence(
        self,
        segments: list[TTSSegment],
        total_duration: float
    ) -> list[TextClip]:
        """
        Creates text clips that appear in sequence with the audio.
        Each segment appears when it's being spoken.

        Args:
            segments: List of TTSSegment with timing info
            total_duration: Total video duration

        Returns:
            List of TextClip objects
        """
        clips = []
        accumulated_text = ""

        for i, segment in enumerate(segments):
            accumulated_text += segment.text + " "
            is_last = i == len(segments) - 1

            # Calculate duration until next segment or end
            if i + 1 < len(segments):
                duration = segments[i + 1].start_time - segment.start_time
            else:
                duration = total_duration - segment.start_time

            # Create clip with accumulated text
            clip = self.create_text_clip(
                text=accumulated_text.strip(),
                duration=duration,
                start_time=segment.start_time,
                highlight=is_last  # Highlight the punchline
            )

            # Position in center
            clip = clip.set_position(('center', 'center'))
            clips.append(clip)

        return clips

    def prepare_background(
        self,
        background_path: str,
        target_duration: float
    ) -> VideoFileClip:
        """
        Prepares background video: crops to vertical, loops if needed.

        Args:
            background_path: Path to background video
            target_duration: Required duration

        Returns:
            Processed VideoFileClip
        """
        clip = VideoFileClip(background_path)

        # Calculate crop for vertical (9:16) aspect ratio
        clip_w, clip_h = clip.size
        target_ratio = self.config.width / self.config.height  # 9:16

        if clip_w / clip_h > target_ratio:
            # Video is too wide, crop width
            new_width = int(clip_h * target_ratio)
            x_center = clip_w / 2
            clip = crop(
                clip,
                x_center=x_center,
                y_center=clip_h / 2,
                width=new_width,
                height=clip_h
            )
        else:
            # Video is too tall, crop height
            new_height = int(clip_w / target_ratio)
            y_center = clip_h / 2
            clip = crop(
                clip,
                x_center=clip_w / 2,
                y_center=y_center,
                width=clip_w,
                height=new_height
            )

        # Resize to target resolution
        clip = resize(clip, (self.config.width, self.config.height))

        # Loop if video is shorter than target duration
        if clip.duration < target_duration:
            # Calculate how many loops needed
            n_loops = int(target_duration / clip.duration) + 1
            clips = [clip] * n_loops
            clip = concatenate_videoclips(clips)

        # Trim to exact duration
        clip = clip.subclip(0, target_duration)

        # Remove original audio (we'll add TTS audio)
        clip = clip.without_audio()

        return clip

    def compose_video(
        self,
        tts_result: TTSResult,
        output_filename: str = "output.mp4",
        background_path: Optional[str] = None,
        sound_effect_path: Optional[str] = None,
        sound_effect_time: Optional[float] = None
    ) -> str:
        """
        Composes the final video with all elements.

        Args:
            tts_result: TTSResult from TTS generator
            output_filename: Output filename
            background_path: Path to background video (random if None)
            sound_effect_path: Path to sound effect for punchline
            sound_effect_time: When to play sound effect (auto if None)

        Returns:
            Path to output video
        """
        # Add small padding to total duration
        total_duration = tts_result.total_duration + 1.5

        # Get background video
        if background_path is None:
            background_path = self.get_random_background()

        background = self.prepare_background(background_path, total_duration)

        # Create text clips
        text_clips = self.create_animated_text_sequence(
            tts_result.segments,
            total_duration
        )

        # Add semi-transparent background box for text
        text_box = ColorClip(
            size=(self.config.width - 60, 400),
            color=(0, 0, 0)
        ).set_opacity(0.7)
        text_box = text_box.set_duration(total_duration)
        text_box = text_box.set_position(('center', 'center'))

        # Compose video layers
        video_layers = [background, text_box] + text_clips
        final_video = CompositeVideoClip(video_layers)

        # Add audio
        tts_audio = AudioFileClip(tts_result.audio_file)
        audio_clips = [tts_audio]

        # Add sound effect at punchline
        if sound_effect_path and os.path.exists(sound_effect_path):
            sfx = AudioFileClip(sound_effect_path)

            # Determine when to play sound effect
            if sound_effect_time is None and tts_result.segments:
                # Play at last segment (punchline)
                sound_effect_time = tts_result.segments[-1].start_time

            if sound_effect_time is not None:
                sfx = sfx.set_start(sound_effect_time)
                # Lower volume of sound effect
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

        # Clean up
        background.close()
        tts_audio.close()
        final_video.close()

        return str(output_path)


def compose_reddit_video(
    tts_result: TTSResult,
    output_filename: str = "reddit_video.mp4",
    backgrounds_dir: str = "assets/backgrounds",
    output_dir: str = "output/videos",
    sound_effect_path: Optional[str] = None
) -> str:
    """
    Convenience function to compose a Reddit video.

    Args:
        tts_result: TTSResult from TTS generation
        output_filename: Output filename
        backgrounds_dir: Directory containing background videos
        output_dir: Output directory
        sound_effect_path: Path to punchline sound effect

    Returns:
        Path to output video
    """
    composer = VideoComposer(
        backgrounds_dir=backgrounds_dir,
        output_dir=output_dir
    )

    return composer.compose_video(
        tts_result=tts_result,
        output_filename=output_filename,
        sound_effect_path=sound_effect_path
    )


# For testing
if __name__ == "__main__":
    # Create dummy TTSResult for testing
    from tts_generator import TTSSegment, TTSResult

    test_segments = [
        TTSSegment("Why don't scientists trust atoms?", 0.0, 2.0),
        TTSSegment("Because they make up everything!", 2.5, 4.5),
    ]

    test_result = TTSResult(
        audio_file="output/audio/test.mp3",
        segments=test_segments,
        total_duration=5.0
    )

    print("Video composer module loaded successfully!")
    print("Use compose_reddit_video() to create videos.")
