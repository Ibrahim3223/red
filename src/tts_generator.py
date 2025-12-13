"""
Text-to-Speech Generator Module
Uses Edge-TTS with gTTS fallback for CI/CD environments.
"""

import asyncio
import json
import os
import re
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
    """Generates speech from text using Edge-TTS or gTTS fallback."""

    # Average speaking rate (words per second) for duration estimation
    WORDS_PER_SECOND = 2.5

    def __init__(
        self,
        voice: str = "male_dramatic",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_dir: str = "output/audio"
    ):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._use_gtts = False  # Will switch to True if Edge TTS fails

    async def generate_speech(
        self,
        text: str,
        filename: str = "speech.mp3"
    ) -> TTSResult:
        """
        Generates speech audio from text.
        Tries Edge-TTS first, falls back to gTTS if blocked.
        """
        output_path = self.output_dir / filename

        # Remove existing file if any
        if output_path.exists():
            os.remove(output_path)

        # Try Edge TTS first (better quality)
        if not self._use_gtts:
            try:
                return await self._generate_edge_tts(text, filename)
            except Exception as e:
                print(f"⚠️ Edge TTS failed: {e}")
                print("🔄 Switching to gTTS fallback...")
                self._use_gtts = True

        # Fallback to gTTS
        return self._generate_gtts(text, filename)

    async def _generate_edge_tts(
        self,
        text: str,
        filename: str
    ) -> TTSResult:
        """Generate speech using Edge TTS."""
        import edge_tts

        output_path = self.output_dir / filename

        # Voice mapping
        voices = {
            "male_us": "en-US-GuyNeural",
            "female_us": "en-US-JennyNeural",
            "male_uk": "en-GB-RyanNeural",
            "female_uk": "en-GB-SoniaNeural",
            "male_dramatic": "en-US-ChristopherNeural",
            "female_dramatic": "en-US-AriaNeural",
        }
        voice = voices.get(self.voice, self.voice)

        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=self.rate,
            pitch=self.pitch
        )

        word_timings = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                with open(output_path, "ab") as f:
                    f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000
                })

        segments = self._create_segments_from_timings(text, word_timings)
        total_duration = 0
        if word_timings:
            last_word = word_timings[-1]
            total_duration = last_word["start"] + last_word["duration"]

        for segment in segments:
            segment.audio_file = str(output_path)

        return TTSResult(
            audio_file=str(output_path),
            segments=segments,
            total_duration=total_duration
        )

    def _generate_gtts(
        self,
        text: str,
        filename: str
    ) -> TTSResult:
        """Generate speech using gTTS (Google Text-to-Speech)."""
        from gtts import gTTS
        from pydub import AudioSegment

        output_path = self.output_dir / filename

        # Generate speech with gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(str(output_path))

        # Get actual duration from audio file
        audio = AudioSegment.from_mp3(str(output_path))
        total_duration = len(audio) / 1000.0  # Convert ms to seconds

        # Estimate segments based on sentences
        segments = self._estimate_segments(text, total_duration)

        for segment in segments:
            segment.audio_file = str(output_path)

        return TTSResult(
            audio_file=str(output_path),
            segments=segments,
            total_duration=total_duration
        )

    def _create_segments_from_timings(
        self,
        text: str,
        word_timings: list[dict]
    ) -> list[TTSSegment]:
        """Creates segments from Edge TTS word timings."""
        if not word_timings:
            return self._estimate_segments(text, 5.0)

        segments = []
        current_segment_words = []
        current_segment_text = ""
        segment_start = 0
        sentence_enders = {'.', '!', '?'}

        for i, word_data in enumerate(word_timings):
            word = word_data["text"]
            current_segment_words.append(word_data)
            current_segment_text += word + " "

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
                    if i + 1 < len(word_timings):
                        segment_start = word_timings[i + 1]["start"]
                    current_segment_words = []
                    current_segment_text = ""

        return segments

    def _estimate_segments(
        self,
        text: str,
        total_duration: float
    ) -> list[TTSSegment]:
        """Estimate segments when no timing data available (gTTS fallback)."""
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if s]

        if not sentences:
            return [TTSSegment(text=text, start_time=0, end_time=total_duration)]

        # Count words in each sentence for proportional timing
        word_counts = [len(s.split()) for s in sentences]
        total_words = sum(word_counts)

        if total_words == 0:
            total_words = 1

        segments = []
        current_time = 0

        for sentence, word_count in zip(sentences, word_counts):
            # Duration proportional to word count
            duration = (word_count / total_words) * total_duration
            segments.append(TTSSegment(
                text=sentence,
                start_time=current_time,
                end_time=current_time + duration
            ))
            current_time += duration

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
        """
        from pydub import AudioSegment

        # Generate setup audio
        setup_result = await self.generate_speech(setup, "temp_setup.mp3")

        # Generate punchline audio
        punchline_result = await self.generate_speech(punchline, "temp_punchline.mp3")

        # Combine segments with adjusted timing
        all_segments = setup_result.segments.copy()

        offset = setup_result.total_duration + pause_duration
        for segment in punchline_result.segments:
            all_segments.append(TTSSegment(
                text=segment.text,
                start_time=segment.start_time + offset,
                end_time=segment.end_time + offset
            ))

        total_duration = offset + punchline_result.total_duration

        # Combine audio files
        setup_audio = AudioSegment.from_mp3(setup_result.audio_file)
        punchline_audio = AudioSegment.from_mp3(punchline_result.audio_file)
        pause = AudioSegment.silent(duration=int(pause_duration * 1000))

        combined = setup_audio + pause + punchline_audio

        output_path = self.output_dir / filename
        combined.export(output_path, format="mp3")

        # Clean up temp files
        try:
            os.remove(setup_result.audio_file)
            os.remove(punchline_result.audio_file)
        except:
            pass

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
    """Synchronous wrapper for joke speech generation."""
    generator = TTSGenerator(voice=voice, output_dir=output_dir)
    return asyncio.run(generator.generate_with_pause(setup, punchline, filename=filename))


# For testing
if __name__ == "__main__":
    async def test():
        generator = TTSGenerator(voice="male_dramatic")

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
