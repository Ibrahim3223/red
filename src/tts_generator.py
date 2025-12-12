"""
Text-to-Speech Generator Module
Uses Edge-TTS (Microsoft) for free, high-quality speech synthesis.
"""

import asyncio
import edge_tts
import json
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class TTSSegment:
    """Represents a segment of speech with timing information."""
    text: str
    start_time: float  # in seconds
    end_time: float  # in seconds
    audio_file: Optional[str] = None


@dataclass
class TTSResult:
    """Result of TTS generation with audio and timing data."""
    audio_file: str
    segments: list[TTSSegment]
    total_duration: float


class TTSGenerator:
    """Generates speech from text using Edge-TTS."""

    # Popular voices for storytelling
    VOICES = {
        "male_us": "en-US-GuyNeural",
        "female_us": "en-US-JennyNeural",
        "male_uk": "en-GB-RyanNeural",
        "female_uk": "en-GB-SoniaNeural",
        "male_dramatic": "en-US-ChristopherNeural",
        "female_dramatic": "en-US-AriaNeural",
    }

    def __init__(
        self,
        voice: str = "male_dramatic",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_dir: str = "output/audio"
    ):
        """
        Initialize TTS generator.

        Args:
            voice: Voice key from VOICES dict or direct voice name
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            pitch: Pitch adjustment (e.g., "+5Hz", "-10Hz")
            output_dir: Directory for audio output
        """
        self.voice = self.VOICES.get(voice, voice)
        self.rate = rate
        self.pitch = pitch
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_speech(
        self,
        text: str,
        filename: str = "speech.mp3"
    ) -> TTSResult:
        """
        Generates speech audio from text with word-level timing.

        Args:
            text: Text to convert to speech
            filename: Output filename

        Returns:
            TTSResult with audio file path and timing data
        """
        output_path = self.output_dir / filename
        subtitle_path = self.output_dir / f"{filename}.json"

        # Create communicate object
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            pitch=self.pitch
        )

        # Collect word timings
        word_timings = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                # Write audio data
                with open(output_path, "ab") as f:
                    f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,  # Convert to seconds
                    "duration": chunk["duration"] / 10_000_000
                })

        # Process word timings into sentence segments
        segments = self._create_segments(text, word_timings)

        # Calculate total duration
        total_duration = 0
        if word_timings:
            last_word = word_timings[-1]
            total_duration = last_word["start"] + last_word["duration"]

        # Save timing data
        timing_data = {
            "words": word_timings,
            "segments": [
                {
                    "text": s.text,
                    "start_time": s.start_time,
                    "end_time": s.end_time
                }
                for s in segments
            ],
            "total_duration": total_duration
        }

        with open(subtitle_path, "w", encoding="utf-8") as f:
            json.dump(timing_data, f, indent=2, ensure_ascii=False)

        # Update segments with audio file reference
        for segment in segments:
            segment.audio_file = str(output_path)

        return TTSResult(
            audio_file=str(output_path),
            segments=segments,
            total_duration=total_duration
        )

    def _create_segments(
        self,
        text: str,
        word_timings: list[dict]
    ) -> list[TTSSegment]:
        """
        Creates sentence-level segments from word timings.
        Splits on sentence boundaries (. ! ?) for natural pacing.
        """
        if not word_timings:
            return []

        segments = []
        current_segment_words = []
        current_segment_text = ""
        segment_start = 0

        # Sentence ending punctuation
        sentence_enders = {'.', '!', '?'}

        for i, word_data in enumerate(word_timings):
            word = word_data["text"]
            current_segment_words.append(word_data)
            current_segment_text += word + " "

            # Check if this word ends a sentence
            is_sentence_end = any(word.endswith(p) for p in sentence_enders)
            is_last_word = i == len(word_timings) - 1

            if is_sentence_end or is_last_word:
                if current_segment_words:
                    segment_end = word_data["start"] + word_data["duration"]

                    segments.append(TTSSegment(
                        text=current_segment_text.strip(),
                        start_time=segment_start,
                        end_time=segment_end
                    ))

                    # Reset for next segment
                    if i + 1 < len(word_timings):
                        segment_start = word_timings[i + 1]["start"]
                    current_segment_words = []
                    current_segment_text = ""

        return segments

    async def generate_with_pause(
        self,
        setup: str,
        punchline: str,
        pause_duration: float = 0.5,
        filename: str = "joke.mp3"
    ) -> TTSResult:
        """
        Generates speech with a pause between setup and punchline.
        Useful for joke delivery timing.

        Args:
            setup: The setup text
            punchline: The punchline text
            pause_duration: Pause duration in seconds between setup and punchline
            filename: Output filename

        Returns:
            TTSResult with combined audio and timing
        """
        # Generate setup audio
        setup_result = await self.generate_speech(setup, "temp_setup.mp3")

        # Generate punchline audio
        punchline_result = await self.generate_speech(punchline, "temp_punchline.mp3")

        # Combine segments with adjusted timing
        all_segments = setup_result.segments.copy()

        # Adjust punchline timing to account for setup duration + pause
        offset = setup_result.total_duration + pause_duration
        for segment in punchline_result.segments:
            all_segments.append(TTSSegment(
                text=segment.text,
                start_time=segment.start_time + offset,
                end_time=segment.end_time + offset
            ))

        total_duration = offset + punchline_result.total_duration

        # Combine audio files using pydub
        from pydub import AudioSegment

        setup_audio = AudioSegment.from_mp3(setup_result.audio_file)
        punchline_audio = AudioSegment.from_mp3(punchline_result.audio_file)

        # Create pause
        pause = AudioSegment.silent(duration=int(pause_duration * 1000))

        # Combine
        combined = setup_audio + pause + punchline_audio

        output_path = self.output_dir / filename
        combined.export(output_path, format="mp3")

        # Clean up temp files
        os.remove(setup_result.audio_file)
        os.remove(punchline_result.audio_file)

        # Update segments
        for segment in all_segments:
            segment.audio_file = str(output_path)

        return TTSResult(
            audio_file=str(output_path),
            segments=all_segments,
            total_duration=total_duration
        )


def generate_speech_sync(
    text: str,
    voice: str = "male_dramatic",
    filename: str = "speech.mp3",
    output_dir: str = "output/audio"
) -> TTSResult:
    """Synchronous wrapper for speech generation."""
    generator = TTSGenerator(voice=voice, output_dir=output_dir)
    return asyncio.run(generator.generate_speech(text, filename))


def generate_joke_sync(
    setup: str,
    punchline: str,
    voice: str = "male_dramatic",
    filename: str = "joke.mp3",
    output_dir: str = "output/audio"
) -> TTSResult:
    """Synchronous wrapper for joke speech generation with pause."""
    generator = TTSGenerator(voice=voice, output_dir=output_dir)
    return asyncio.run(generator.generate_with_pause(setup, punchline, filename=filename))


# For testing
if __name__ == "__main__":
    async def test():
        generator = TTSGenerator(voice="male_dramatic")

        # Test basic speech
        result = await generator.generate_speech(
            "Why don't scientists trust atoms? Because they make up everything!",
            "test_speech.mp3"
        )

        print(f"Audio file: {result.audio_file}")
        print(f"Duration: {result.total_duration:.2f}s")
        print("Segments:")
        for seg in result.segments:
            print(f"  [{seg.start_time:.2f}s - {seg.end_time:.2f}s] {seg.text}")

    asyncio.run(test())
