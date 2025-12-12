"""
Audio Mixer Module
Handles sound effects and background music for videos.
"""

import os
import random
from pathlib import Path
from typing import Optional
from pydub import AudioSegment
from pydub.effects import normalize


class AudioMixer:
    """Mixes audio tracks, adds sound effects and background music."""

    # Default sound effect triggers (words that might indicate punchline)
    PUNCHLINE_TRIGGERS = [
        "because", "but", "then", "so", "actually",
        "turns out", "plot twist", "and then", "suddenly"
    ]

    def __init__(
        self,
        sounds_dir: str = "assets/sounds",
        output_dir: str = "output/audio"
    ):
        self.sounds_dir = Path(sounds_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_sound_effect(self, category: str = "punchline") -> Optional[str]:
        """
        Gets a random sound effect from the specified category.

        Args:
            category: Sound effect category folder name

        Returns:
            Path to sound effect file or None
        """
        category_dir = self.sounds_dir / category
        if not category_dir.exists():
            # Try to find any sound file
            category_dir = self.sounds_dir

        audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a'}
        sounds = [
            f for f in category_dir.iterdir()
            if f.suffix.lower() in audio_extensions
        ]

        if not sounds:
            return None

        return str(random.choice(sounds))

    def add_sound_effect(
        self,
        main_audio_path: str,
        effect_path: str,
        position_ms: int,
        effect_volume_db: float = -6.0,
        output_path: Optional[str] = None
    ) -> str:
        """
        Adds a sound effect to the main audio at a specific position.

        Args:
            main_audio_path: Path to main audio file
            effect_path: Path to sound effect file
            position_ms: Position in milliseconds to insert effect
            effect_volume_db: Volume adjustment for effect in dB
            output_path: Output path (overwrites main if None)

        Returns:
            Path to output audio file
        """
        main_audio = AudioSegment.from_file(main_audio_path)
        effect = AudioSegment.from_file(effect_path)

        # Adjust effect volume
        effect = effect + effect_volume_db

        # Overlay effect at position
        combined = main_audio.overlay(effect, position=position_ms)

        # Normalize to prevent clipping
        combined = normalize(combined)

        output = output_path or main_audio_path
        combined.export(output, format="mp3")

        return output

    def add_background_music(
        self,
        main_audio_path: str,
        music_path: str,
        music_volume_db: float = -15.0,
        fade_in_ms: int = 1000,
        fade_out_ms: int = 1000,
        output_path: Optional[str] = None
    ) -> str:
        """
        Adds background music to the main audio.

        Args:
            main_audio_path: Path to main audio file
            music_path: Path to background music
            music_volume_db: Volume adjustment for music in dB
            fade_in_ms: Fade in duration
            fade_out_ms: Fade out duration
            output_path: Output path

        Returns:
            Path to output audio file
        """
        main_audio = AudioSegment.from_file(main_audio_path)
        music = AudioSegment.from_file(music_path)

        # Adjust music volume
        music = music + music_volume_db

        # Loop music if shorter than main audio
        if len(music) < len(main_audio):
            loops_needed = (len(main_audio) // len(music)) + 1
            music = music * loops_needed

        # Trim music to main audio length
        music = music[:len(main_audio)]

        # Apply fades
        music = music.fade_in(fade_in_ms).fade_out(fade_out_ms)

        # Overlay
        combined = main_audio.overlay(music)

        # Normalize
        combined = normalize(combined)

        output = output_path or main_audio_path
        combined.export(output, format="mp3")

        return output

    def create_punchline_effect(
        self,
        tts_audio_path: str,
        punchline_start_time: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        Adds a punchline sound effect at the appropriate time.

        Args:
            tts_audio_path: Path to TTS audio
            punchline_start_time: When the punchline starts (seconds)
            output_path: Output path

        Returns:
            Path to output audio
        """
        effect_path = self.get_sound_effect("punchline")

        if not effect_path:
            print("Warning: No punchline sound effects found")
            return tts_audio_path

        # Convert to milliseconds and add slight delay for impact
        position_ms = int(punchline_start_time * 1000) - 100

        return self.add_sound_effect(
            main_audio_path=tts_audio_path,
            effect_path=effect_path,
            position_ms=max(0, position_ms),
            effect_volume_db=-3.0,
            output_path=output_path
        )

    def process_video_audio(
        self,
        tts_audio_path: str,
        punchline_time: Optional[float] = None,
        add_music: bool = False,
        music_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Full audio processing pipeline for video.

        Args:
            tts_audio_path: Path to TTS audio
            punchline_time: When punchline occurs (seconds)
            add_music: Whether to add background music
            music_path: Path to background music
            output_path: Output path

        Returns:
            Path to processed audio
        """
        output = output_path or tts_audio_path.replace(".mp3", "_mixed.mp3")

        # Copy original to output
        audio = AudioSegment.from_file(tts_audio_path)
        audio.export(output, format="mp3")

        # Add punchline effect
        if punchline_time is not None:
            self.create_punchline_effect(
                output,
                punchline_time,
                output
            )

        # Add background music
        if add_music and music_path and os.path.exists(music_path):
            self.add_background_music(
                output,
                music_path,
                output_path=output
            )

        return output


def create_default_sound_effects(sounds_dir: str = "assets/sounds"):
    """
    Creates placeholder info for sound effects.
    User needs to add actual sound effect files.
    """
    sounds_path = Path(sounds_dir)
    punchline_dir = sounds_path / "punchline"
    punchline_dir.mkdir(parents=True, exist_ok=True)

    readme = punchline_dir / "README.txt"
    if not readme.exists():
        readme.write_text("""
SOUND EFFECTS DIRECTORY
=======================

Add your punchline sound effects here!

Recommended free sources:
- freesound.org
- pixabay.com/sound-effects
- mixkit.co/free-sound-effects

Good punchline sounds:
- Rimshot / drum hit
- "Bruh" sound effect
- Vine boom
- Record scratch
- Comedy honk

Supported formats: .mp3, .wav, .ogg, .m4a
""")

    return str(punchline_dir)


# For testing
if __name__ == "__main__":
    # Create directories
    create_default_sound_effects()
    print("Audio mixer module loaded successfully!")
    print("Add sound effects to assets/sounds/punchline/")
