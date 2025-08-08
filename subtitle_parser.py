import re
from dataclasses import dataclass
from typing import List


@dataclass
class SubtitleSegment:
    start: float  # giây
    end: float  # giây
    text: str


def parse_time_to_seconds(time_str: str) -> float:
    """Chuyển từ hh:mm:ss thành số giây"""
    h, m, s = map(int, time_str.strip().split(":"))
    return h * 3600 + m * 60 + s


def parse_subtitle_file(filepath: str) -> List[SubtitleSegment]:
    segments = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pattern = re.compile(r"(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s+(.*)")

    for line in lines:
        match = pattern.match(line.strip())
        if match:
            start_str, end_str, text = match.groups()
            start = parse_time_to_seconds(start_str)
            end = parse_time_to_seconds(end_str)
            segments.append(SubtitleSegment(start, end, text))

    return segments

def convert_custom_lines_to_segments(lines: List[str]) -> List[SubtitleSegment]:
    pattern = re.compile(r"(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s+(.*)")
    segments = []

    for line in lines:
        match = pattern.match(line.strip())
        if match:
            start_str, end_str, text = match.groups()
            start = parse_time_to_seconds(start_str)
            end = parse_time_to_seconds(end_str)
            segments.append(SubtitleSegment(start, end, text))

    return segments