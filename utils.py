"""
Utility functions for the subtitle rendering application
"""
import glob
import os
import re
import requests
import yt_dlp
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from constants import TIME_PATTERN, SRT_TIME_PATTERN, URL_PATTERN, SUPPORTED_VIDEO_FORMATS


def validate_file_path(file_path: str, file_type: str = "file") -> bool:
    """Validate if file exists and is accessible"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ {file_type.capitalize()} không tồn tại: {file_path}")
    return True


def safe_int_conversion(value: str, default: int) -> int:
    """Safely convert string to integer with fallback"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_time_to_seconds(time_str: str) -> float:
    """Convert hh:mm:ss format to seconds"""
    h, m, s = map(int, time_str.strip().split(":"))
    return h * 3600 + m * 60 + s


def escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for ffmpeg drawtext"""
    # Escape các ký tự đặc biệt của ffmpeg
    escaped = (text.replace(":", r"\:")
               .replace("'", r"\'")
               .replace("%", r"\%")
               .replace("\\", r"\\"))
    return escaped


def get_template_list(template_dir: str = "subtitle_templates") -> List[str]:
    """Get list of available templates"""
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    templates = [
        os.path.splitext(file)[0]
        for file in os.listdir(template_dir)
        if file.endswith(".json")
    ]
    templates.append("Tùy chỉnh")
    return templates


def ensure_directory(file_path: str) -> None:
    """Ensure directory exists for file path"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def download_video_from_url(url: str, output_dir: str = "downloads") -> str:
    """
    Download video from URL using yt-dlp
    Returns path to downloaded video file
    """
    from datetime import datetime, timedelta

    os.makedirs(output_dir, exist_ok=True)

    # Get current time in UTC+7
    now_utc7 = datetime.utcnow() + timedelta(hours=7)
    timestamp = now_utc7.strftime("%Y%m%d_%H%M%S")

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, f"video_{timestamp}.%(ext)s"),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }

    # YouTube may force SABR streaming, leaving the default clients without
    # downloadable formats ("The page needs to be reloaded"). The android
    # client still works in that case, so retry with it as a fallback.
    fallback_opts = {
        **ydl_opts,
        'format': 'best[ext=mp4]/best',
        'extractor_args': {'youtube': {'player_client': ['android', 'android_vr']}},
    }

    last_error = None
    for opts in (ydl_opts, fallback_opts):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise Exception("Không lấy được thông tin video")
                if info.get('entries'):
                    info = next((entry for entry in info['entries'] if entry), info)
                file_path = ydl.prepare_filename(info)
        except Exception as e:
            last_error = e
            continue

        # Merging streams can change the final extension, so resolve the
        # actual file that yt-dlp wrote to disk.
        if not os.path.exists(file_path):
            base_path = os.path.splitext(file_path)[0]
            candidates = [
                path for path in glob.glob(base_path + ".*")
                if os.path.splitext(path)[1].lower() in SUPPORTED_VIDEO_FORMATS
            ]
            if candidates:
                file_path = max(candidates, key=os.path.getmtime)

        if os.path.exists(file_path):
            return file_path

        last_error = Exception("File video không được tạo sau khi tải")

    raise Exception(f"Lỗi tải video từ URL: {str(last_error)}")


def download_file_from_url(url: str, output_path: str) -> str:
    """
    Download file from direct URL
    """
    ensure_directory(output_path)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path
    except Exception as e:
        raise Exception(f"Lỗi tải file từ URL: {str(e)}")


def extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """
    Extract audio from video using ffmpeg
    """
    import subprocess

    cmd = [
        "ffmpeg", "-i", video_path,
        "-q:a", "0", "-map", "a",
        output_audio_path, "-y"
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_audio_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Lỗi trích xuất audio: {str(e)}")


def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format"""
    if not os.path.exists(file_path):
        return False
    return any(file_path.lower().endswith(fmt) for fmt in SUPPORTED_VIDEO_FORMATS)
