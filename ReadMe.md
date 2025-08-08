# 🎬 Subtitle Embed Tool

**Một công cụ mạnh mẽ giúp bạn chèn phụ đề vào video dễ dàng — hỗ trợ cả giao diện dòng lệnh (CLI) lẫn giao diện người dùng (GUI).**

---

## 📦 Tính năng nổi bật

- ✅ Nhận đầu vào là video `.mp4` và file phụ đề định dạng `[hh:mm:ss - hh:mm:ss] Nội dung`
- ✅ Chèn phụ đề vào video bằng `ffmpeg` với các tuỳ chọn tùy chỉnh: font, màu, vị trí, viền...
- ✅ Tự động ngắt dòng phụ đề dài
- ✅ Giao diện người dùng (GUI) đẹp mắt bằng `customtkinter`
- ✅ Hiển thị tiến trình render video theo phần trăm
- ✅ Có thể chạy trực tiếp bằng lệnh CLI nếu thích dùng terminal

---

## 🖥️ Yêu cầu hệ thống

- Python 3.10 trở lên
- Các thư viện:
  - `customtkinter`
  - `ffmpeg` (đã cài đặt và có trong PATH)
  - `Pillow` (nếu dùng hình ảnh hoặc font tùy chỉnh)
  - `whisper` (nếu bạn thêm chức năng tự tạo sub sau này)
- Hệ điều hành: Windows, macOS hoặc Linux

---

## 🚀 Cách cài đặt

```bash
git clone https://github.com/your-username/subtitle-embed-tool.git
cd subtitle-embed-tool
python -m venv .venv
.venv\Scripts\activate  # Trên Windows
pip install -r requirements.txt
