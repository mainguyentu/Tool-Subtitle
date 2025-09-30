import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from subtitle_parser import parse_subtitle_file, convert_custom_lines_to_segments
from video_renderer import render_video_with_subtitles, load_template, parse_srt_to_custom_format
import threading
import tempfile
import cv2
from PIL import Image, ImageTk


class SubtitleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Subtitle Renderer Tool")
        self.geometry("1000x600")

        # Biến lưu đường dẫn file
        self.video_path = ctk.StringVar()
        self.sub_path = ctk.StringVar()
        self.template_choice = ctk.StringVar(value="Tùy chỉnh")

        # Extra style khi không dùng template
        self.font_path = ctk.StringVar(value="font/OpenSans-Light.ttf")
        self.font_size = ctk.StringVar(value="40")
        self.font_color = ctk.StringVar(value="white")
        self.outline_color = ctk.StringVar(value="black")
        self.outline_width = ctk.StringVar(value="2")
        self.position = ctk.StringVar(value="bottom-center")
        self.appearance_mode = ctk.StringVar(value="Dark")

        self.output_path = ctk.StringVar(value="output/output.mp4")

        # Biến cho preview video
        self.preview_video_path = None
        self.is_preview_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.cap = None
        self.fps = 30
        self.video_duration = 0

        self.create_widgets()

    def create_widgets(self):
        # === KHUNG TRÁI ===
        left_frame = ctk.CTkScrollableFrame(self, width=450, label_text="🎬 Cài đặt video")
        left_frame.pack(side="left", fill="both", expand=False, padx=20, pady=20)

        row = 0

        def build_file_input_block(label_text, var, command):
            nonlocal row
            ctk.CTkLabel(left_frame, text=label_text, anchor="w").grid(row=row, column=0, sticky="w", pady=(5, 2),
                                                                       columnspan=2)
            row += 1
            frame = ctk.CTkFrame(left_frame, fg_color="transparent")
            frame.grid(row=row, column=0, columnspan=2, sticky="we", pady=5)
            ctk.CTkEntry(frame, textvariable=var, width=300).pack(side="left", padx=(0, 10))
            ctk.CTkButton(frame, text="Chọn", width=80, command=command, fg_color="#2d7cff",
                          hover_color="#1e5fd1").pack(side="left")
            row += 1

        build_file_input_block("🎥 Video đầu vào:", self.video_path, self.browse_video)
        build_file_input_block("📄 File phụ đề:", self.sub_path, self.browse_subtitle)

        ctk.CTkLabel(left_frame, text="🎨 Chọn template", anchor="w").grid(row=row, column=0, sticky="w", pady=(10, 2),
                                                                          columnspan=2)
        row += 1
        self.template_menu = ctk.CTkOptionMenu(
            left_frame,
            values=self.get_template_list(),
            variable=self.template_choice,
            command=self.toggle_custom_style
        )
        self.template_menu.grid(row=row, column=0, columnspan=2, sticky="we", pady=(0, 10))
        row += 1

        self.custom_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.custom_frame.grid(row=row, column=0, columnspan=2, sticky="we", pady=(0, 10))
        self.build_custom_style_form(self.custom_frame)
        row += 1

        ctk.CTkLabel(left_frame, text="📤 File đầu ra", anchor="w").grid(row=row, column=0, sticky="w", pady=(10, 2),
                                                                        columnspan=2)
        row += 1
        out_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        out_frame.grid(row=row, column=0, columnspan=2, sticky="we", pady=(0, 10))
        ctk.CTkEntry(out_frame, textvariable=self.output_path, width=300).pack(side="left", padx=(0, 10))
        ctk.CTkButton(out_frame, text="Chọn", width=80, command=self.browse_output,
                      fg_color="#2d7cff", hover_color="#1e5fd1").pack(side="left")
        row += 1

        # Frame chứa 2 nút Preview và Render
        buttons_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="we")
        row += 1

        self.preview_button = ctk.CTkButton(
            buttons_frame, text="🎬 Preview", command=self.start_preview_thread,
            fg_color="#ff6b35", hover_color="#e55a2b", width=150
        )
        self.preview_button.grid(row=0, column=0, padx=(0, 10), pady=0)

        self.render_button = ctk.CTkButton(
            buttons_frame, text="Render Video", command=self.start_render_thread,
            fg_color="#2d7cff", hover_color="#1e5fd1", width=150
        )
        self.render_button.grid(row=0, column=1, padx=(0, 0), pady=0)

        # Căn giữa 2 nút trong buttons_frame
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)

        # === KHUNG PHẢI (dùng grid co giãn) ===
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        right_frame.grid_columnconfigure(0, weight=1)
        # Các hàng: 0=label sub, 1=textbox, 2=label progress, 3=progress, 4=label video, 5=video, 6=controls
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_rowconfigure(5, weight=2)

        ctk.CTkLabel(right_frame, text="📜 Thời gian & phụ đề", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.preview_box = ctk.CTkTextbox(right_frame)
        self.preview_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        ctk.CTkLabel(right_frame, text="📈 Tiến trình render video", font=ctk.CTkFont(size=16, weight="bold")).grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(right_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(right_frame, text="🎥 Video Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(row=4, column=0, sticky="w", pady=(10, 5))
        
        # Frame chứa video player (co giãn)
        self.video_frame = ctk.CTkFrame(right_frame)
        self.video_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        self.video_frame.grid_columnconfigure(0, weight=1)
        self.video_frame.grid_rowconfigure(0, weight=1)

        # Canvas tự co giãn theo frame
        self.video_canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)
        self.video_canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        # Re-render khi canvas đổi kích thước để luôn fit khung
        self.video_canvas.bind("<Configure>", self.on_video_canvas_resize)

        # Label text khi chưa có video
        self.video_text_label = ctk.CTkLabel(self.video_frame, text="Chọn video và phụ đề để preview", font=ctk.CTkFont(size=14))
        self.video_text_label.grid(row=0, column=0)

        # Controls cho video player
        self.controls_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.controls_frame.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.controls_frame.grid_columnconfigure(2, weight=1)
        
        self.play_button = ctk.CTkButton(self.controls_frame, text="▶️ Play", width=90, command=self.toggle_playback, state="disabled")
        self.play_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ctk.CTkButton(self.controls_frame, text="⏹️ Stop", width=90, command=self.stop_preview, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.seek_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self.seek_video, state="disabled")
        self.seek_slider.grid(row=0, column=2, sticky="ew")

    def browse_output(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            initialfile="output.mp4"
        )
        if file:
            self.output_path.set(file)

    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))

    def change_appearance(self, mode):
        ctk.set_appearance_mode(mode)

    def get_template_list(self, folder="subtitle_templates"):
        if not os.path.exists(folder):
            os.makedirs(folder)
        templates = []
        for file in os.listdir(folder):
            if file.endswith(".json"):
                templates.append(os.path.splitext(file)[0])
        templates.append("Tùy chỉnh")
        return templates

    def toggle_custom_style(self, value):
        if value == "Tùy chỉnh":
            return
        else:
            template = load_template(value)
            self.font_path.set(template.get("font", "font/OpenSans-Light.ttf"))
            self.font_size.set(str(template.get("font_size", 40)))
            self.font_color.set(template.get("font_color", "white"))
            self.outline_color.set(template.get("border_color", "black"))
            self.outline_width.set(str(template.get("border_width", 2)))
            self.position.set(template.get("position", "bottom-center"))

    def build_custom_style_form(self, parent):
        def make_labeled_entry(label_text, var, width=200):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label_text, width=100, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=width).pack(side="left", expand=True, fill="x")
            return row

        make_labeled_entry("Font path:", self.font_path)
        make_labeled_entry("Font size:", self.font_size)
        make_labeled_entry("Font color:", self.font_color)
        make_labeled_entry("Viền màu:", self.outline_color)
        make_labeled_entry("Độ dày viền:", self.outline_width)
        make_labeled_entry("Vị trí:", self.position)

    def browse_video(self):
        file = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file:
            self.video_path.set(file)

    def browse_subtitle(self):
        file_path = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.txt *.srt")])
        if file_path:
            self.sub_path.set(file_path)

            # Nếu là .srt → chuyển đổi
            if file_path.lower().endswith('.srt'):
                converted_lines = parse_srt_to_custom_format(file_path)
                self.subtitle_lines = converted_lines
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.subtitle_lines = f.readlines()

            # Hiển thị preview
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", "\n".join(self.subtitle_lines))

    def show_sub_preview(self, sub_file):
        try:
            segments = parse_subtitle_file(sub_file)
            self.preview_box.delete("0.0", "end")
            for seg in segments:
                self.preview_box.insert("end", f"[{seg.start} - {seg.end}] {seg.text}\n")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc phụ đề: {str(e)}")

    def start_render_thread(self):
        render_thread = threading.Thread(target=self.render_video)
        render_thread.daemon = True
        render_thread.start()

    def start_preview_thread(self):
        preview_thread = threading.Thread(target=self.create_preview_video)
        preview_thread.daemon = True
        preview_thread.start()

    def create_preview_video(self):
        """Tạo video preview với phụ đề để người dùng xem trước"""
        try:
            self.preview_button.configure(state="disabled", text="Đang tạo preview...")
            
            if not os.path.exists(self.video_path.get()) or not os.path.exists(self.sub_path.get()):
                messagebox.showerror("Thiếu file", "Vui lòng chọn video và phụ đề.")
                return

            # Parse phụ đề
            if self.sub_path.get().lower().endswith('.srt'):
                converted_lines = parse_srt_to_custom_format(self.sub_path.get())
                segments = convert_custom_lines_to_segments(converted_lines)
            else:
                segments = parse_subtitle_file(self.sub_path.get())

            # Tạo file preview tạm thời
            temp_dir = tempfile.gettempdir()
            self.preview_video_path = os.path.join(temp_dir, "preview_subtitle.mp4")

            # Render preview với chất lượng thấp để nhanh hơn
            if self.template_choice.get() == "Tùy chỉnh":
                try:
                    font_size = int(self.font_size.get())
                except (ValueError, tk.TclError):
                    font_size = 40
                try:
                    outline_width = int(self.outline_width.get())
                except (ValueError, tk.TclError):
                    outline_width = 2

                self.render_preview_video(
                    input_video=self.video_path.get(),
                    output_video=self.preview_video_path,
                    segments=segments,
                    font_path=self.font_path.get(),
                    font_size=font_size,
                    font_color=self.font_color.get(),
                    outline_color=self.outline_color.get(),
                    outline_width=outline_width,
                    position=self.position.get()
                )
            else:
                template = load_template(self.template_choice.get())
                self.render_preview_video(
                    input_video=self.video_path.get(),
                    output_video=self.preview_video_path,
                    segments=segments,
                    font_path=template["font"],
                    font_size=template["font_size"],
                    font_color=template["font_color"],
                    outline_color=template.get("border_color", "black"),
                    outline_width=template.get("border_width", 2),
                    position=template.get("position", "bottom-center"),
                    extra_styles={
                        "shadowcolor": template.get("shadow_color"),
                        "shadowx": template.get("shadow_x"),
                        "shadowy": template.get("shadow_y"),
                        "line_spacing": template.get("line_spacing", 10)
                    }
                )

            # Kiểm tra file preview có được tạo thành công không
            if os.path.exists(self.preview_video_path) and os.path.getsize(self.preview_video_path) > 0:
                print(f"Preview video created successfully: {os.path.getsize(self.preview_video_path)} bytes")
                # Load video vào player
                self.load_preview_video()
            else:
                raise Exception("Preview video không được tạo thành công")
            
        except Exception as e:
            print(f"Error creating preview: {e}")
            messagebox.showerror("Lỗi khi tạo preview", str(e))
            # Hiển thị thông báo lỗi
            self.video_canvas.grid_remove()
            self.video_text_label.configure(text=f"Lỗi: {str(e)}")
            self.video_text_label.grid(row=0, column=0)
        finally:
            self.preview_button.configure(state="normal", text="🎬 Preview Video")

    def render_preview_video(self, input_video, output_video, segments, font_path, 
                           font_size, font_color, outline_color, outline_width, 
                           position, extra_styles=None):
        """Render preview video với chất lượng thấp để nhanh hơn"""
        import subprocess
        import re
        
        # Lấy thông tin video
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

        # Tạo filter drawtext (sử dụng lại từ video_renderer)
        from video_renderer import generate_drawtext_filter
        drawtext_filter = generate_drawtext_filter(
            segments, font_path, font_size, font_color,
            outline_color, outline_width, width, height,
            position, extra_styles
        )

        # Render với chất lượng thấp để preview nhanh
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-vf", drawtext_filter,
            "-c:a", "aac", "-b:a", "128k",  # Audio chất lượng thấp
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",  # Video chất lượng thấp
            "-t", "15",  # Chỉ render 30 giây đầu để preview
            output_video
        ]

        print(f"Rendering preview video with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Preview video created successfully: {output_video}")
        print(f"File size: {os.path.getsize(output_video) if os.path.exists(output_video) else 'File not found'} bytes")

    def load_preview_video(self):
        """Load video preview vào OpenCV player"""
        try:
            if self.cap:
                self.cap.release()
            
            print(f"Loading preview video: {self.preview_video_path}")
            self.cap = cv2.VideoCapture(self.preview_video_path)
            
            if not self.cap.isOpened():
                raise Exception("Không thể mở video preview")
            
            # Lấy thông tin video
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.video_duration = self.total_frames / self.fps if self.fps > 0 else 0
            self.current_frame = 0
            
            print(f"Total frames: {self.total_frames}")
            print(f"FPS: {self.fps}")
            print(f"Duration: {self.video_duration:.2f}s")
            
            # Enable controls
            self.play_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.seek_slider.configure(state="normal", to=100)
            
            # Hiển thị frame đầu tiên
            self.update_video_frame()
            
        except Exception as e:
            print(f"Error loading video: {e}")
            messagebox.showerror("Lỗi khi load video", str(e))
            # Hiển thị thông báo lỗi (dùng grid)
            self.video_canvas.grid_remove()
            self.video_text_label.configure(text=f"Lỗi load video: {str(e)}")
            self.video_text_label.grid(row=0, column=0)

    def update_video_frame(self):
        """Cập nhật frame hiện tại của video"""
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            
            if ret and frame is not None:
                # Kích thước khung canvas hiện tại (thực tế sau layout)
                canvas_width = max(1, int(self.video_canvas.winfo_width()))
                canvas_height = max(1, int(self.video_canvas.winfo_height()))

                # Resize frame để fit vào canvas, giữ nguyên tỉ lệ
                frame_height, frame_width = frame.shape[:2]
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = max(1, int(frame_width * scale))
                new_height = max(1, int(frame_height * scale))
                if new_width != frame_width or new_height != frame_height:
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

                # Convert BGR to RGB và tạo ảnh PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(pil_image)

                # Xóa canvas, vẽ ảnh căn giữa
                self.video_canvas.delete("all")
                self.video_canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor="center")
                 
                # Ẩn text label và hiển thị canvas (dùng grid)
                self.video_text_label.grid_remove()
                self.video_canvas.grid(row=0, column=0, sticky="nsew")
                 
                # Keep reference để tránh garbage collection
                self.video_canvas.image = photo
                 
                # Update slider
                if self.total_frames > 0:
                    progress = (self.current_frame / self.total_frames) * 100
                    self.seek_slider.set(progress)
            else:
                print(f"Failed to read frame {self.current_frame}")
                # Hiển thị thông báo lỗi (dùng grid)
                self.video_canvas.grid_remove()
                self.video_text_label.configure(text="Không thể đọc frame video")
                self.video_text_label.grid(row=0, column=0)

    def on_video_canvas_resize(self, event):
        """Re-render khung hình hiện tại khi canvas đổi kích thước để luôn khớp khung."""
        try:
            # Chỉ cập nhật ảnh, không thay đổi current_frame
            if self.cap and self.cap.isOpened():
                # Không đọc frame mới, mà vẽ lại frame hiện có bằng cách lùi 1 bước
                current = max(0, self.current_frame - 1)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current)
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # Gọi cùng logic scale như update_video_frame nhưng không đụng đến slider
                    canvas_width = max(1, int(self.video_canvas.winfo_width()))
                    canvas_height = max(1, int(self.video_canvas.winfo_height()))
                    h, w = frame.shape[:2]
                    scale = min(canvas_width / w, canvas_height / h)
                    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                    if nw != w or nh != h:
                        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(pil_image)
                    self.video_canvas.delete("all")
                    self.video_canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor="center")
                    self.video_canvas.image = photo
                    self.video_text_label.grid_remove()
                    self.video_canvas.grid(row=0, column=0, sticky="nsew")
        except Exception:
            pass

    def toggle_playback(self):
        """Toggle play/pause video"""
        if not self.is_preview_playing:
            self.is_preview_playing = True
            self.play_button.configure(text="⏸️ Pause")
            self.play_video()
        else:
            self.is_preview_playing = False
            self.play_button.configure(text="▶️ Play")

    def play_video(self):
        """Play video frame by frame"""
        if self.is_preview_playing and self.cap and self.cap.isOpened():
            self.update_video_frame()
            self.current_frame += 1
            
            if self.current_frame >= self.total_frames:
                self.current_frame = 0  # Loop back to start
            
            # Schedule next frame update
            self.after(int(1000/self.fps), self.play_video)  # Sync với FPS của video

    def stop_preview(self):
        """Stop video playback"""
        self.is_preview_playing = False
        self.play_button.configure(text="▶️ Play")
        self.current_frame = 0
        self.update_video_frame()

    def seek_video(self, value):
        """Seek to specific position in video"""
        if self.cap and self.cap.isOpened():
            self.current_frame = int((value / 100) * self.total_frames)
            self.update_video_frame()

    def render_video(self):
        try:
            self.progress_bar.set(0)
            self.update_idletasks()

            self.render_button.configure(state="disabled")

            if not os.path.exists(self.video_path.get()) or not os.path.exists(self.sub_path.get()):
                messagebox.showerror("Thiếu file", "Vui lòng chọn video và phụ đề.")
                return

            if self.sub_path.get().lower().endswith('.srt'):
                converted_lines = parse_srt_to_custom_format(self.sub_path.get())
                segments = convert_custom_lines_to_segments(converted_lines)
            else:
                segments = parse_subtitle_file(self.sub_path.get())
            self.update_idletasks()

            if self.template_choice.get() == "Tùy chỉnh":
                try:
                    font_size = int(self.font_size.get())
                except (ValueError, tk.TclError):
                    font_size = 40
                try:
                    outline_width = int(self.outline_width.get())
                except (ValueError, tk.TclError):
                    outline_width = 2

                render_video_with_subtitles(
                    input_video=self.video_path.get(),
                    output_video=self.output_path.get(),
                    segments=segments,
                    font_path=self.font_path.get(),
                    font_size=font_size,
                    font_color=self.font_color.get(),
                    outline_color=self.outline_color.get(),
                    outline_width=outline_width,
                    position=self.position.get(),
                    progress_callback=self.update_progress
                )
            else:
                template = load_template(self.template_choice.get())
                render_video_with_subtitles(
                    input_video=self.video_path.get(),
                    output_video=self.output_path.get(),
                    segments=segments,
                    font_path=template["font"],
                    font_size=template["font_size"],
                    font_color=template["font_color"],
                    outline_color=template.get("border_color", "black"),
                    outline_width=template.get("border_width", 2),
                    position=template.get("position", "bottom-center"),
                    extra_styles={
                        "shadowcolor": template.get("shadow_color"),
                        "shadowx": template.get("shadow_x"),
                        "shadowy": template.get("shadow_y"),
                        "line_spacing": template.get("line_spacing", 10)
                    },
                    progress_callback=self.update_progress
                )

            self.update_idletasks()
            messagebox.showinfo("Thành công", f"Video đã xuất ra: {self.output_path.get()}")

        except Exception as e:
            self.progress_bar.set(0)
            self.update_idletasks()
            messagebox.showerror("Lỗi khi render", str(e))
        finally:
            self.render_button.configure(state="normal")

    def cleanup(self):
        """Cleanup resources khi đóng ứng dụng"""
        if self.cap:
            self.cap.release()
        if self.preview_video_path and os.path.exists(self.preview_video_path):
            try:
                os.remove(self.preview_video_path)
            except:
                pass

    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        self.cleanup()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = SubtitleApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
