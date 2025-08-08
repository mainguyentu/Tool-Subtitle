import os
import json
import re
import subprocess
from typing import List
from subtitle_parser import SubtitleSegment
import textwrap


def split_subtitle_into_lines(text: str, max_chars_per_line: int) -> List[str]:
    """
    Ngắt văn bản thành nhiều dòng nhỏ nếu dài quá.
    """
    return textwrap.wrap(text, width=max_chars_per_line)


def load_template(template_name: str) -> dict:
    """
    Tải template định dạng phụ đề từ file JSON.
    """
    path = os.path.join("subtitle_templates", f"{template_name}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Template '{template_name}' không tồn tại tại {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_srt_to_custom_format(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Tách block phụ đề
    blocks = re.split(r'\n\s*\n', content.strip())
    result = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            time_range = lines[1]
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_range)
            if match:
                start = match.group(1).replace(',', '.')[:-4]
                end = match.group(2).replace(',', '.')[:-4]
                text = ' '.join(lines[2:])
                result.append(f"{start} - {end} {text}")
    return result

def generate_drawtext_filter(segments: List[SubtitleSegment],
                             font_path: str,
                             font_size: int,
                             font_color: str,
                             outline_color: str,
                             outline_width: int,
                             video_width: int,
                             video_height: int,
                             position: str = "bottom-center",
                             extra_styles: dict = None) -> str:
    """
    Tạo filter drawtext cho từng dòng subtitle riêng biệt.
    """
    filter_lines = []
    extra_styles = extra_styles or {}

    shadow_color = extra_styles.get("shadow_color")
    shadow_x = extra_styles.get("shadow_x", 0)
    shadow_y = extra_styles.get("shadow_y", 0)
    line_spacing = extra_styles.get("line_spacing", 10)

    max_chars_per_line = max(int(video_width / (font_size * 0.6)), 10)

    for seg in segments:
        wrapped_lines = split_subtitle_into_lines(seg.text, max_chars_per_line)
        total_lines = len(wrapped_lines)

        for idx, line in enumerate(wrapped_lines):
            safe_text = line.replace(":", r"\:").replace("'", r"\'")

            # Vị trí dòng
            if position == "bottom-center":
                x_expr = "(w-text_w)/2"
                y_expr = f"h-(text_h*{total_lines - idx + 1})-{(total_lines - idx - 1) * line_spacing}"
            elif position == "top-center":
                x_expr = "(w-text_w)/2"
                y_expr = f"text_h*{idx + 1} + {idx * line_spacing}"
            elif position == "top-left":
                x_expr = "10"
                y_expr = f"text_h*{idx + 1} + {idx * line_spacing}"
            elif position == "bottom-right":
                x_expr = "w-text_w-10"
                y_expr = f"h-(text_h*{total_lines - idx + 1})-{(total_lines - idx - 1) * line_spacing}"
            else:
                x_expr = "(w-text_w)/2"
                y_expr = f"h-(text_h*{total_lines - idx + 1})-{(total_lines - idx - 1) * line_spacing}"

            # Xây dựng dòng drawtext
            line_text = (
                f"drawtext=text='{safe_text}':"
                f"enable='between(t,{seg.start},{seg.end})':"
                f"fontfile='{font_path}':"
                f"fontsize={font_size}:"
                f"fontcolor={font_color}:"
                f"x={x_expr}:y={y_expr}:"
                f"borderw={outline_width}:"
                f"bordercolor={outline_color}:"
                f"line_spacing={line_spacing}"
            )

            if shadow_color:
                line_text += f":shadowcolor={shadow_color}:shadowx={shadow_x}:shadowy={shadow_y}"

            filter_lines.append(line_text)

    return ",".join(filter_lines)


def render_video_with_subtitles(input_video: str,
                                output_video: str,
                                segments: List[SubtitleSegment],
                                font_path: str,
                                font_size: int = 48,
                                font_color: str = "white",
                                outline_color: str = "black",
                                outline_width: int = 2,
                                position: str = "bottom-center",
                                extra_styles: dict = None,
                                progress_callback=None):
    """
    Render video với phụ đề bằng ffmpeg và template style.
    """
    probe_duration_cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_video
    ]
    duration_result = subprocess.run(probe_duration_cmd, capture_output=True, text=True)
    total_duration = float(duration_result.stdout.strip())

    probe_size_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", input_video
    ]
    size_result = subprocess.run(probe_size_cmd, capture_output=True, text=True)
    width, height = map(int, size_result.stdout.strip().split(','))

    drawtext_filter = generate_drawtext_filter(
        segments, font_path, font_size, font_color,
        outline_color, outline_width, width, height,
        position, extra_styles
    )

    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vf", drawtext_filter,
        "-c:a", "copy",
        output_video
    ]

    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+).(\d+)")
    for line in process.stderr:
        match = time_pattern.search(line)
        if match:
            h, m, s, ms = map(int, match.groups())
            current_time = h * 3600 + m * 60 + s + ms / 100
            progress = min(current_time / total_duration, 1.0)
            if progress_callback:
                progress_callback(progress)

    process.wait()
