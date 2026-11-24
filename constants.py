"""
Constants and configuration for the subtitle rendering application
"""
import re

# File paths
DEFAULT_FONT_PATH = "font/OpenSans-Light.ttf"
DEFAULT_OUTPUT_PATH = "output/output.mp4"
TEMPLATE_DIR = "subtitle_templates"
DOWNLOAD_DIR = "downloads"
AUDIO_DIR = "temp_audio"

# Default styling
DEFAULT_STYLES = {
    "font_size": 48,
    "font_color": "white",
    "outline_color": "black",
    "outline_width": 2,
    "position": "bottom-center",
    "line_spacing": 10
}

# Video settings
PREVIEW_DURATION = 15  # seconds
PREVIEW_QUALITY = {
    "video_preset": "ultrafast",
    "video_crf": 28,
    "audio_bitrate": "128k"
}

# AI Settings
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
DEFAULT_WHISPER_MODEL = "base"

# Regex patterns
TIME_PATTERN = re.compile(r"(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s+(.*)")
SRT_TIME_PATTERN = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
FFMPEG_TIME_PATTERN = re.compile(r"time=(\d+):(\d+):(\d+).(\d+)")
URL_PATTERN = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')

# Position mappings
POSITION_CONFIG = {
    "bottom-center": {
        "x": "(w-text_w)/2",
        "y_base": "h-text_h"
    },
    "top-center": {
        "x": "(w-text_w)/2",
        "y_base": "0"
    },
    "top-left": {
        "x": "10",
        "y_base": "0"
    },
    "bottom-right": {
        "x": "w-text_w-10",
        "y_base": "h-text_h"
    }
}

# Supported video formats
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]