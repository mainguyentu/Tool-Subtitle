"""
AI-powered subtitle generation using Whisper
"""
import os
import tempfile
import whisper
from typing import List, Tuple
from subtitle_parser import SubtitleSegment
from utils import extract_audio_from_video, ensure_directory


class AISubtitleGenerator:
    """Generate subtitles from audio using OpenAI Whisper"""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load Whisper model"""
        try:
            print(f"🔄 Đang tải mô hình Whisper {self.model_size}...")
            self.model = whisper.load_model(self.model_size)
            print("✅ Tải mô hình thành công!")
        except Exception as e:
            raise Exception(f"Lỗi tải mô hình Whisper: {str(e)}")

    def generate_subtitles_from_video(self, video_path: str,
                                      language: str = "vi") -> List[SubtitleSegment]:
        """
        Generate subtitles from video file
        Returns list of SubtitleSegment objects
        """
        # Extract audio from video
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            audio_path = temp_audio.name

        try:
            extract_audio_from_video(video_path, audio_path)
            return self.generate_subtitles_from_audio(audio_path, language)
        finally:
            # Cleanup temporary audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def generate_subtitles_from_audio(self, audio_path: str,
                                      language: str = "vi") -> List[SubtitleSegment]:
        """
        Generate subtitles from audio file
        """
        if not self.model:
            self._load_model()

        try:
            # Transcribe audio
            print("🎤 Đang nhận diện giọng nói...")
            result = self.model.transcribe(audio_path, language=language, task="transcribe")

            # Convert to SubtitleSegment format
            segments = []
            for segment in result["segments"]:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"].strip()

                # Filter out very short segments or empty text
                if text and (end - start) > 0.5:
                    segments.append(SubtitleSegment(start, end, text))

            print(f"✅ Đã tạo {len(segments)} đoạn phụ đề")
            return segments

        except Exception as e:
            raise Exception(f"Lỗi tạo phụ đề AI: {str(e)}")

    def generate_subtitle_file(self, video_path: str, output_path: str,
                               language: str = "vi") -> List[SubtitleSegment]:
        """
        Generate subtitle file from video and save to custom format
        """
        ensure_directory(output_path)

        segments = self.generate_subtitles_from_video(video_path, language)

        # Save to custom subtitle format
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                start_str = self._seconds_to_time(segment.start)
                end_str = self._seconds_to_time(segment.end)
                f.write(f"{start_str} - {end_str} {segment.text}\n")

        return segments

    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Singleton instance
_ai_generator = None


def get_ai_generator(model_size: str = "base") -> AISubtitleGenerator:
    """Get singleton AI generator instance"""
    global _ai_generator
    if _ai_generator is None:
        _ai_generator = AISubtitleGenerator(model_size)
    return _ai_generator


def generate_subtitles_ai(video_path: str, model_size: str = "base",
                          language: str = "vi") -> List[SubtitleSegment]:
    """Convenience function to generate subtitles using AI"""
    generator = get_ai_generator(model_size)
    return generator.generate_subtitles_from_video(video_path, language)