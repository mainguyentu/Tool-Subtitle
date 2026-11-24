"""
Video rendering functionality with subtitles
"""
import os
import json
import subprocess
import tempfile
import textwrap
from typing import List, Optional, Callable
from dataclasses import dataclass

from subtitle_parser import SubtitleSegment
from utils import validate_file_path, escape_ffmpeg_text, ensure_directory
from constants import *


@dataclass
class RenderConfig:
    """Configuration for video rendering"""
    font_path: str
    font_size: int
    font_color: str
    outline_color: str
    outline_width: int
    position: str
    extra_styles: dict = None

    def __post_init__(self):
        self.extra_styles = self.extra_styles or {}


class VideoRenderer:
    """Handles video rendering with subtitles"""

    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"

    def load_template(self, template_name: str) -> dict:
        """Load subtitle template from JSON file"""
        path = os.path.join(TEMPLATE_DIR, f"{template_name}.json")
        validate_file_path(path, "template")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_video_info(self, video_path: str) -> tuple:
        """Get video duration and dimensions"""
        validate_file_path(video_path, "video")

        # Get duration
        duration_cmd = [
            self.ffprobe_path, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
        total_duration = float(duration_result.stdout.strip())

        # Get dimensions
        size_cmd = [
            self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path
        ]
        size_result = subprocess.run(size_cmd, capture_output=True, text=True)
        width, height = map(int, size_result.stdout.strip().split(','))

        return total_duration, width, height

    def _calculate_text_position(self, position: str, line_index: int, total_lines: int,
                                 line_spacing: int) -> tuple:
        """Calculate x, y coordinates for text based on position"""
        pos_config = POSITION_CONFIG.get(position, POSITION_CONFIG["bottom-center"])
        x_expr = pos_config["x"]

        if position == "bottom-center":
            y_expr = f"h-text_h*{total_lines - line_index} - {(total_lines - line_index - 1) * line_spacing}"
        elif position == "top-center":
            y_expr = f"text_h*{line_index + 1} + {line_index * line_spacing}"
        elif position == "top-left":
            y_expr = f"text_h*{line_index + 1} + {line_index * line_spacing}"
        elif position == "bottom-right":
            y_expr = f"h-text_h*{total_lines - line_index} - {(total_lines - line_index - 1) * line_spacing}"
        else:
            y_expr = f"h-text_h*{total_lines - line_index} - {(total_lines - line_index - 1) * line_spacing}"

        return x_expr, y_expr

    def generate_drawtext_filter(self, segments: List[SubtitleSegment],
                                 config: RenderConfig,
                                 video_width: int,
                                 video_height: int) -> str:
        """Generate ffmpeg drawtext filter for subtitles"""
        filter_lines = []
        max_chars_per_line = max(int(video_width / (config.font_size * 0.6)), 10)

        line_spacing = config.extra_styles.get("line_spacing", 10)
        shadow_color = config.extra_styles.get("shadow_color")
        shadow_x = config.extra_styles.get("shadow_x", 0)
        shadow_y = config.extra_styles.get("shadow_y", 0)

        for segment in segments:
            wrapped_lines = textwrap.wrap(segment.text, width=max_chars_per_line)
            total_lines = len(wrapped_lines)

            for line_index, line_text in enumerate(wrapped_lines):
                safe_text = escape_ffmpeg_text(line_text)
                x_expr, y_expr = self._calculate_text_position(
                    config.position, line_index, total_lines, line_spacing
                )

                # Build drawtext command
                drawtext_cmd = [
                    f"drawtext=text='{safe_text}'",
                    f"enable='between(t,{segment.start},{segment.end})'",
                    f"fontfile='{config.font_path}'",
                    f"fontsize={config.font_size}",
                    f"fontcolor={config.font_color}",
                    f"x={x_expr}",
                    f"y={y_expr}",
                    f"borderw={config.outline_width}",
                    f"bordercolor={config.outline_color}",
                    f"line_spacing={line_spacing}"
                ]

                if shadow_color:
                    drawtext_cmd.extend([
                        f"shadowcolor={shadow_color}",
                        f"shadowx={shadow_x}",
                        f"shadowy={shadow_y}"
                    ])

                filter_lines.append(":".join(drawtext_cmd))

        return ",".join(filter_lines)

    def render_video(self,
                     input_video: str,
                     output_video: str,
                     segments: List[SubtitleSegment],
                     config: RenderConfig,
                     progress_callback: Optional[Callable] = None,
                     is_preview: bool = False) -> None:
        """Render video with subtitles"""
        validate_file_path(input_video, "video")
        ensure_directory(output_video)

        total_duration, width, height = self.get_video_info(input_video)
        drawtext_filter = self.generate_drawtext_filter(segments, config, width, height)

        print(f"🔧 Filter length: {len(drawtext_filter)} characters")

        # Kiểm tra nếu filter quá dài
        if len(drawtext_filter) > 30000:
            print("⚠️ Filter quá dài, sử dụng filter complex...")
            return self._render_with_filter_complex(
                input_video, output_video, segments, config,
                progress_callback, is_preview
            )

        # Build ffmpeg command (code cũ)
        cmd = [self.ffmpeg_path, "-y", "-i", input_video, "-vf", drawtext_filter]

        if is_preview:
            cmd.extend([
                "-c:a", "aac", "-b:a", PREVIEW_QUALITY["audio_bitrate"],
                "-c:v", "libx264", "-preset", PREVIEW_QUALITY["video_preset"],
                "-crf", str(PREVIEW_QUALITY["video_crf"]),
                "-t", str(PREVIEW_DURATION)
            ])
        else:
            cmd.extend(["-c:a", "copy"])

        cmd.append(output_video)

        # Execute với error handling tốt hơn
        try:
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr}")

            if not os.path.exists(output_video) or os.path.getsize(output_video) == 0:
                raise Exception("FFmpeg không tạo được file đầu ra")

        except Exception as e:
            print(f"❌ Lỗi với filter thường, thử filter complex...")
            self._remove_partial_output(output_video)
            return self._render_with_filter_complex(
                input_video, output_video, segments, config,
                progress_callback, is_preview
            )

    @staticmethod
    def _remove_partial_output(output_video: str) -> None:
        """Delete a partially written output so it is never loaded as valid"""
        try:
            if os.path.exists(output_video):
                os.remove(output_video)
        except OSError:
            pass

    def _generate_filter_complex(self, segments: List[SubtitleSegment], config: RenderConfig, input_video: str) -> str:
        """Tạo filter complex content cho file"""
        # Lấy video info
        total_duration, width, height = self.get_video_info(input_video)

        lines = []
        current_stream = "0:v"
        max_chars_per_line = max(int(width / (config.font_size * 0.6)), 10)
        line_spacing = config.extra_styles.get("line_spacing", 10)

        for i, segment in enumerate(segments):
            # Tạo drawtext filter cho mỗi segment
            wrapped_lines = textwrap.wrap(segment.text, width=max_chars_per_line)

            for line_idx, line_text in enumerate(wrapped_lines):
                safe_text = escape_ffmpeg_text(line_text)

                # Tính toán vị trí
                x_expr, y_expr = self._calculate_text_position(
                    config.position, line_idx, len(wrapped_lines), line_spacing
                )

                # Base drawtext filter
                drawtext_filter = (
                    f"drawtext=text='{safe_text}':"
                    f"enable='between(t,{segment.start},{segment.end})':"
                    f"fontfile='{config.font_path}':"
                    f"fontsize={config.font_size}:"
                    f"fontcolor={config.font_color}:"
                    f"x={x_expr}:y={y_expr}:"
                    f"borderw={config.outline_width}:"
                    f"bordercolor={config.outline_color}:"
                    f"line_spacing={line_spacing}"
                )

                # Thêm shadow nếu có
                shadow_color = config.extra_styles.get("shadow_color")
                if shadow_color:
                    drawtext_filter += f":shadowcolor={shadow_color}"
                    drawtext_filter += f":shadowx={config.extra_styles.get('shadow_x', 2)}"
                    drawtext_filter += f":shadowy={config.extra_styles.get('shadow_y', 2)}"

                # Tạo filter chain nối tiếp
                input_stream = current_stream
                output_stream = f"v{i}_{line_idx}"
                lines.append(f"[{input_stream}]{drawtext_filter}[{output_stream}]")
                current_stream = output_stream

        # Output với format chuẩn
        lines.append(f"[{current_stream}]format=yuv420p[v]")
        return ";\n".join(lines)

    def _render_with_filter_complex(self,
                                    input_video: str,
                                    output_video: str,
                                    segments: List[SubtitleSegment],
                                    config: RenderConfig,
                                    progress_callback: Optional[Callable] = None,
                                    is_preview: bool = False) -> None:
        """Render với filter complex để tránh command line quá dài"""
        import tempfile

        # Tạo file filter tạm
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            filter_file = f.name
            filter_content = self._generate_filter_complex(segments, config, input_video)
            print(f"🔧 Filter complex length: {len(filter_content)} characters")
            f.write(filter_content)

        try:
            # Lấy total duration cho progress tracking
            total_duration, _, _ = self.get_video_info(input_video)
            if is_preview:
                total_duration = min(total_duration, PREVIEW_DURATION)

            # Sử dụng Popen để theo dõi tiến trình
            cmd = [
                self.ffmpeg_path, "-y", "-i", input_video,
                "-filter_complex_script", filter_file,
                "-map", "[v]", "-map", "0:a?"
            ]

            if is_preview:
                cmd.extend([
                    "-c:a", "aac", "-b:a", PREVIEW_QUALITY["audio_bitrate"],
                    "-c:v", "libx264", "-preset", PREVIEW_QUALITY["video_preset"],
                    "-crf", str(PREVIEW_QUALITY["video_crf"]),
                    "-t", str(PREVIEW_DURATION)
                ])
            else:
                cmd.extend(["-c:a", "copy"])

            cmd.append(output_video)

            print("🔧 Using filter_complex_script with file...")

            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore'
            )

            # Theo dõi output để cập nhật progress
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break

                if progress_callback:
                    self._update_progress(line, total_duration, progress_callback)

                print(line.strip())  # Debug output

            if process.returncode != 0:
                # Nếu vẫn lỗi, thử cách đơn giản hơn - chia nhỏ segments
                print("⚠️ Filter complex failed, trying simplified approach...")
                self._remove_partial_output(output_video)
                return self._render_simplified_filter(input_video, output_video, segments, config, progress_callback,
                                                      is_preview)

            if not os.path.exists(output_video) or os.path.getsize(output_video) == 0:
                raise Exception("FFmpeg không tạo được file đầu ra")

            print("✅ Render với filter complex thành công!")
            return True

        except Exception as e:
            print(f"❌ Lỗi trong filter complex: {str(e)}")
            # Thử cách đơn giản hơn
            print("🔄 Trying simplified approach...")
            self._remove_partial_output(output_video)
            return self._render_simplified_filter(input_video, output_video, segments, config, progress_callback,
                                                  is_preview)
        finally:
            # Xóa file tạm
            if os.path.exists(filter_file):
                os.remove(filter_file)

    def _render_simplified_filter(self,
                                  input_video: str,
                                  output_video: str,
                                  segments: List[SubtitleSegment],
                                  config: RenderConfig,
                                  progress_callback: Optional[Callable] = None,
                                  is_preview: bool = False) -> None:
        """Cách render đơn giản hơn - chia nhỏ segments nếu cần"""

        # Chia segments thành các nhóm nhỏ hơn
        max_segments_per_batch = 10
        batches = [segments[i:i + max_segments_per_batch] for i in range(0, len(segments), max_segments_per_batch)]

        if len(batches) == 1:
            # Nếu chỉ có 1 batch, dùng cách thông thường
            return self._render_single_batch(input_video, output_video, batches[0], config, progress_callback,
                                             is_preview)
        else:
            # Nếu nhiều batch, render từng batch và nối lại
            print(f"🔧 Chia thành {len(batches)} batches để render...")
            temp_files = []

            try:
                for i, batch in enumerate(batches):
                    temp_output = f"temp_batch_{i}.mp4"
                    temp_files.append(temp_output)
                    # Tính progress cho từng batch
                    batch_progress_callback = None
                    if progress_callback:
                        def make_batch_callback(batch_idx, total_batches):
                            def batch_callback(progress):
                                # Tính progress tổng thể dựa trên batch
                                overall_progress = (batch_idx + progress) / total_batches
                                progress_callback(overall_progress)

                            return batch_callback

                        batch_progress_callback = make_batch_callback(i, len(batches))

                    self._render_single_batch(input_video, temp_output, batch, config, batch_progress_callback,
                                              is_preview)

                # Nối các file tạm lại
                self._concat_videos(temp_files, output_video)
                if progress_callback:
                    progress_callback(1.0)  # Hoàn thành 100%
                print("✅ Render thành công với phương pháp chia batch!")

            except Exception:
                self._remove_partial_output(output_video)
                raise

            finally:
                # Dọn dẹp file tạm
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

    def _render_single_batch(self,
                             input_video: str,
                             output_video: str,
                             segments: List[SubtitleSegment],
                             config: RenderConfig,
                             progress_callback: Optional[Callable] = None,
                             is_preview: bool = False) -> None:
        """Render một batch segments với progress tracking"""
        # Tạo filter đơn giản hơn, chỉ với các segments trong batch này
        filter_parts = []

        for segment in segments:
            wrapped_lines = textwrap.wrap(segment.text, width=30)

            for line_idx, line_text in enumerate(wrapped_lines):
                safe_text = escape_ffmpeg_text(line_text)

                # Tính toán vị trí đơn giản
                if config.position == "bottom-center":
                    y = f"h-text_h*{len(wrapped_lines) - line_idx}-{line_idx * 10}"
                else:
                    y = f"text_h*{line_idx + 1}+{line_idx * 10}"

                drawtext_filter = (
                    f"drawtext=text='{safe_text}':"
                    f"enable='between(t,{segment.start},{segment.end})':"
                    f"fontfile='{config.font_path}':"
                    f"fontsize={config.font_size}:"
                    f"fontcolor={config.font_color}:"
                    f"x=(w-text_w)/2:y={y}:"
                    f"borderw={config.outline_width}:"
                    f"bordercolor={config.outline_color}"
                )

                filter_parts.append(drawtext_filter)

        # Build command
        if filter_parts:
            full_filter = ",".join(filter_parts)
            cmd = [self.ffmpeg_path, "-y", "-i", input_video, "-vf", full_filter]
        else:
            cmd = [self.ffmpeg_path, "-y", "-i", input_video]

        if is_preview:
            cmd.extend(["-t", str(PREVIEW_DURATION)])

        cmd.extend(["-c:a", "copy", output_video])

        # Lấy total duration cho progress tracking
        total_duration, _, _ = self.get_video_info(input_video)
        if is_preview:
            total_duration = min(total_duration, PREVIEW_DURATION)

        # Sử dụng Popen để theo dõi tiến trình real-time
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore'
        )

        # Theo dõi output để cập nhật progress
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if progress_callback:
                self._update_progress(line, total_duration, progress_callback)

        if process.returncode != 0:
            self._remove_partial_output(output_video)
            raise Exception(f"FFmpeg batch render failed with return code {process.returncode}")

    def _concat_videos(self, input_files: List[str], output_file: str) -> None:
        """Nối các video file lại với nhau"""
        # Tạo file list cho concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            list_file = f.name
            for file in input_files:
                f.write(f"file '{os.path.abspath(file)}'\n")

        try:
            cmd = [
                self.ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", output_file
            ]

            process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if process.returncode != 0:
                raise Exception(f"FFmpeg concat failed: {process.stderr}")
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

    def _update_progress(self, line: str, total_duration: float, progress_callback: Callable) -> None:
        """Update rendering progress from ffmpeg output"""
        match = FFMPEG_TIME_PATTERN.search(line)
        if match:
            h, m, s, ms = map(int, match.groups())
            current_time = h * 3600 + m * 60 + s + ms / 100
            progress = min(current_time / total_duration, 1.0)
            progress_callback(progress)


# Backward compatibility functions
def render_video_with_subtitles(input_video: str, output_video: str, segments: List[SubtitleSegment],
                                font_path: str, font_size: int = 48, font_color: str = "white",
                                outline_color: str = "black", outline_width: int = 2,
                                position: str = "bottom-center", extra_styles: dict = None,
                                progress_callback: Optional[Callable] = None):
    """Legacy function for backward compatibility"""
    config = RenderConfig(
        font_path=font_path,
        font_size=font_size,
        font_color=font_color,
        outline_color=outline_color,
        outline_width=outline_width,
        position=position,
        extra_styles=extra_styles
    )

    renderer = VideoRenderer()
    renderer.render_video(
        input_video=input_video,
        output_video=output_video,
        segments=segments,
        config=config,
        progress_callback=progress_callback
    )