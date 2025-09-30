# 🎬 Subtitle Embed Tool  

**Công cụ chèn phụ đề vào video nhanh chóng và dễ sử dụng — hỗ trợ cả giao diện dòng lệnh (CLI) và giao diện người dùng (GUI).**  

---

## 🌟 Giới thiệu  

Bạn có một video ngắn và muốn thêm phụ đề đẹp mắt chỉ trong vài bước? **Subtitle Embed Tool** sẽ giúp bạn:  
- Tự động chèn phụ đề vào video `.mp4`  
- Hỗ trợ cả file phụ đề `.srt` và định dạng `[hh:mm:ss - hh:mm:ss] Nội dung`  
- Tuỳ chỉnh phông chữ, kích thước, màu sắc, vị trí và viền chữ  
- Sử dụng trực tiếp bằng giao diện người dùng (GUI) hoặc chạy nhanh bằng dòng lệnh (CLI)  

---

## ⚡ Tính năng chính  

- ✅ Chèn phụ đề vào video bằng `ffmpeg`  
- ✅ Tự động xuống dòng với phụ đề dài  
- ✅ Tuỳ chỉnh đầy đủ: font, màu chữ, màu viền, bóng đổ, khoảng cách dòng, vị trí hiển thị  
- ✅ Giao diện trực quan (GUI) dễ thao tác  
- ✅ Hiển thị tiến trình render video  
- ✅ Hỗ trợ chạy bằng CLI cho người thích terminal  

---

## 🖥️ Hướng dẫn sử dụng  

### 1. Dùng giao diện GUI  
- Mở công cụ GUI (`main.py`)  
- Chọn video và file phụ đề  
- Tuỳ chỉnh theo ý muốn (font, màu sắc, template...)  
- Nhấn nút **Render** để xuất video hoàn chỉnh  

### 2. Dùng dòng lệnh (CLI)  

**Ví dụ sử dụng template mặc định:**  
```bash
python cli_tools.py --video path/to/input.mp4 --subtitle path/to/subtitles.srt --template default --output path/to/output.mp4
```

**Ví dụ tùy chỉnh chi tiết:**  
```bash
python cli_tools.py --video path/to/input.mp4   --subtitle path/to/subtitles.srt   --font path/to/font.ttf   --fontsize 24   --color white   --outline_color black   --outline_width 2   --position bottom-center   --output path/to/output.mp4
```

---

## ⚙️ Các tùy chọn CLI  

- `--font` → Đường dẫn đến font tuỳ chỉnh (mặc định: font hệ thống)  
- `--fontsize` → Kích thước chữ (mặc định: 24)  
- `--color` → Màu chữ (mặc định: trắng)  
- `--outline_color` → Màu viền (mặc định: đen)  
- `--outline_width` → Độ dày viền (mặc định: 2)  
- `--position` → Vị trí phụ đề: `bottom-center`, `top-center`, `top-left`, `bottom-right`...  
- `--shadow_color`, `--shadow_x`, `--shadow_y` → Tuỳ chỉnh bóng chữ  
- `--line_spacing` → Khoảng cách dòng phụ đề  
- `--output` → Tên file xuất ra (mặc định: `output.mp4`)  

---

## 🔧 Yêu cầu hệ thống  

- Python **3.10+**  
- Thư viện:  
  - `customtkinter`  
  - `ffmpeg` (cần cài đặt sẵn trên máy)  
  - `Pillow`  
  - `whisper` (tùy chọn, nếu muốn tự động tạo phụ đề)  
- Hỗ trợ Windows, macOS, Linux  

---

## 🚀 Cài đặt  

```bash
git clone https://github.com/mainguyentu/tools.git
cd subtitle_tool
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```