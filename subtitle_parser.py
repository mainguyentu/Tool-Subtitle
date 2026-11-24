"""
Subtitle parsing functionality
"""
import re
from dataclasses import dataclass
from typing import List, Optional
from utils import parse_time_to_seconds, TIME_PATTERN, SRT_TIME_PATTERN


@dataclass
class SubtitleSegment:
    start: float  # seconds
    end: float  # seconds
    text: str


class SubtitleParser:
    """Parser for different subtitle formats"""

    @staticmethod
    def parse_subtitle_file(filepath: str) -> List[SubtitleSegment]:
        """Parse custom subtitle format (HH:MM:SS - HH:MM:SS Text)"""
        segments = []

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                segment = SubtitleParser._parse_line(line.strip())
                if segment:
                    segments.append(segment)

        return segments

    @staticmethod
    def parse_srt_file(filepath: str) -> List[SubtitleSegment]:
        """Parse SRT subtitle format"""
        segments = []

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())

        for block in blocks:
            segment = SubtitleParser._parse_srt_block(block)
            if segment:
                segments.append(segment)

        return segments

    @staticmethod
    def _parse_line(line: str) -> Optional[SubtitleSegment]:
        """Parse a single line of custom subtitle format"""
        match = TIME_PATTERN.match(line)
        if match:
            start_str, end_str, text = match.groups()
            start = parse_time_to_seconds(start_str)
            end = parse_time_to_seconds(end_str)
            return SubtitleSegment(start, end, text)
        return None

    @staticmethod
    def _parse_srt_block(block: str) -> Optional[SubtitleSegment]:
        """Parse a single SRT block"""
        lines = block.strip().split('\n')
        if len(lines) < 2:
            return None

        time_range = lines[1]
        match = SRT_TIME_PATTERN.match(time_range)
        if match:
            start_str, end_str = match.groups()
            # Convert SRT format (00:00:01,500) to custom format (00:00:01)
            start = parse_time_to_seconds(start_str.replace(',', '.')[:-4])
            end = parse_time_to_seconds(end_str.replace(',', '.')[:-4])
            text = ' '.join(lines[2:])
            return SubtitleSegment(start, end, text)

        return None

    @staticmethod
    def parse_file(filepath: str) -> List[SubtitleSegment]:
        """Auto-detect format and parse subtitle file"""
        if filepath.lower().endswith('.srt'):
            return SubtitleParser.parse_srt_file(filepath)
        else:
            return SubtitleParser.parse_subtitle_file(filepath)