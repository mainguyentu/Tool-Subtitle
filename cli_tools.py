import argparse
import os
from subtitle_parser import parse_subtitle_file, convert_custom_lines_to_segments
from video_renderer import render_video_with_subtitles, load_template, parse_srt_to_custom_format


def main():
    parser = argparse.ArgumentParser(description="🎬 Tool chèn phụ đề vào video")

    parser.add_argument('--video', required=True, help="📹 Đường dẫn file video (.mp4)")
    parser.add_argument('--subtitle', required=True, help="📝 File phụ đề dạng text [.txt]")
    parser.add_argument('--template', help="🎨 Tên template phụ đề (không bắt buộc)")
    parser.add_argument('--output', default="output/output.mp4", help="📤 Tên file đầu ra (.mp4)")

    # Các tuỳ chọn ghi đè nếu không dùng template
    parser.add_argument('--font', help="Font TTF")
    parser.add_argument('--fontsize', type=int, help="Cỡ chữ")
    parser.add_argument('--color', help="Màu chữ")
    parser.add_argument('--outline_color', help="Màu viền chữ")
    parser.add_argument('--outline_width', type=int, help="Độ dày viền")
    parser.add_argument('--position', help="Vị trí phụ đề (bottom-center, top-left,...)")
    parser.add_argument('--shadow_color', help="Màu bóng")
    parser.add_argument('--shadow_x', type=int, help="Độ lệch bóng X")
    parser.add_argument('--shadow_y', type=int, help="Độ lệch bóng Y")
    parser.add_argument('--line_spacing', type=int, help="Khoảng cách dòng")

    args = parser.parse_args()

    # Kiểm tra tệp tồn tại
    if not os.path.exists(args.video):
        print("❌ File video không tồn tại.")
        return

    if not os.path.exists(args.subtitle):
        print("❌ File phụ đề không tồn tại.")
        return

    print("📂 Đang đọc phụ đề...")
    if args.subtitle.lower().endswith(".srt"):
        custom_lines = parse_srt_to_custom_format(args.subtitle)
        segments = convert_custom_lines_to_segments(custom_lines)
    else:
        segments = parse_subtitle_file(args.subtitle)

    # Tải template nếu có
    template = {}
    if args.template:
        print(f"🎨 Đang tải template: {args.template}")
        try:
            template = load_template(args.template)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return

    # Ưu tiên các tham số CLI, nếu không có thì dùng trong template, nếu vẫn không có thì dùng mặc định
    def get(key, default=None):
        return getattr(args, key, None) or template.get(key, default)

    font_path = get("font", "font/OpenSans-Light.ttf")
    if not os.path.exists(font_path):
        print("⚠️ Font không tồn tại, dùng font mặc định.")
        font_path = "font/OpenSans-Light.ttf"

    print("🎬 Đang render video...")

    render_video_with_subtitles(
        input_video=args.video,
        output_video=args.output,
        segments=segments,
        font_path=font_path,
        font_size=int(get("fontsize", 48)),
        font_color=get("color", "white"),
        outline_color=get("outline_color", "black"),
        outline_width=int(get("outline_width", 2)),
        position=get("position", "bottom-center"),
        extra_styles={
            "shadowcolor": get("shadow_color"),
            "shadowx": get("shadow_x"),
            "shadowy": get("shadow_y"),
            "line_spacing": int(get("line_spacing", 10))
        }
    )

    print(f"✅ Video đã xuất ra: {args.output}")


if __name__ == "__main__":
    main()
