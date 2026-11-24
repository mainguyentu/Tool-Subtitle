"""
Command line interface for subtitle rendering tool
"""
import argparse
import os

from subtitle_parser import SubtitleParser
from video_renderer import VideoRenderer, RenderConfig
from utils import validate_file_path, safe_int_conversion
from constants import DEFAULT_FONT_PATH, DEFAULT_OUTPUT_PATH, DEFAULT_STYLES


class SubtitleCLI:
    """Command line interface handler"""

    def __init__(self):
        self.parser = self._setup_parser()
        self.video_renderer = VideoRenderer()

    def _setup_parser(self) -> argparse.ArgumentParser:
        """Setup argument parser"""
        parser = argparse.ArgumentParser(description="🎬 Tool chèn phụ đề vào video")

        # Required arguments
        parser.add_argument('--video', required=True, help="📹 Đường dẫn file video (.mp4)")
        parser.add_argument('--subtitle', required=True, help="📝 File phụ đề dạng text [.txt]")

        # Optional arguments
        parser.add_argument('--template', help="🎨 Tên template phụ đề (không bắt buộc)")
        parser.add_argument('--output', default=DEFAULT_OUTPUT_PATH, help="📤 Tên file đầu ra (.mp4)")

        # Style overrides
        style_group = parser.add_argument_group('Tùy chọn style (ghi đè template)')
        style_group.add_argument('--font', help="Font TTF")
        style_group.add_argument('--fontsize', type=int, help="Cỡ chữ")
        style_group.add_argument('--color', help="Màu chữ")
        style_group.add_argument('--outline_color', help="Màu viền chữ")
        style_group.add_argument('--outline_width', type=int, help="Độ dày viền")
        style_group.add_argument('--position', help="Vị trí phụ đề (bottom-center, top-left,...)")
        style_group.add_argument('--shadow_color', help="Màu bóng")
        style_group.add_argument('--shadow_x', type=int, help="Độ lệch bóng X")
        style_group.add_argument('--shadow_y', type=int, help="Độ lệch bóng Y")
        style_group.add_argument('--line_spacing', type=int, help="Khoảng cách dòng")

        return parser

    def _load_template(self, template_name: str) -> dict:
        """Load template with error handling"""
        try:
            return self.video_renderer.load_template(template_name)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            raise

    def _get_config(self, args, template: dict) -> RenderConfig:
        """Get render configuration from args and template"""

        def get_value(key, default=None):
            return getattr(args, key, None) or template.get(key, default)

        font_path = get_value("font", DEFAULT_FONT_PATH)
        if not os.path.exists(font_path):
            print("⚠️ Font không tồn tại, dùng font mặc định.")
            font_path = DEFAULT_FONT_PATH

        extra_styles = {
            "shadowcolor": get_value("shadow_color"),
            "shadowx": get_value("shadow_x"),
            "shadowy": get_value("shadow_y"),
            "line_spacing": safe_int_conversion(get_value("line_spacing"), DEFAULT_STYLES["line_spacing"])
        }

        return RenderConfig(
            font_path=font_path,
            font_size=safe_int_conversion(get_value("fontsize"), DEFAULT_STYLES["font_size"]),
            font_color=get_value("color", DEFAULT_STYLES["font_color"]),
            outline_color=get_value("outline_color", DEFAULT_STYLES["outline_color"]),
            outline_width=safe_int_conversion(get_value("outline_width"), DEFAULT_STYLES["outline_width"]),
            position=get_value("position", DEFAULT_STYLES["position"]),
            extra_styles=extra_styles
        )

    def run(self):
        """Run the CLI application"""
        args = self.parser.parse_args()

        try:
            # Validate input files
            validate_file_path(args.video, "video")
            validate_file_path(args.subtitle, "subtitle")

            print("📂 Đang đọc phụ đề...")
            segments = SubtitleParser.parse_file(args.subtitle)

            # Load template if specified
            template = {}
            if args.template:
                print(f"🎨 Đang tải template: {args.template}")
                template = self._load_template(args.template)

            # Prepare configuration
            config = self._get_config(args, template)

            print("🎬 Đang render video...")
            self.video_renderer.render_video(
                input_video=args.video,
                output_video=args.output,
                segments=segments,
                config=config
            )

            print(f"✅ Video đã xuất ra: {args.output}")

        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return 1

        return 0


def main():
    """Main entry point"""
    cli = SubtitleCLI()
    return cli.run()


if __name__ == "__main__":
    exit(main())