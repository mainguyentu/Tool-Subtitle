"""
GUI application for subtitle rendering tool with AI features
"""
import glob
import os
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import tempfile
import cv2
from PIL import Image, ImageTk

from subtitle_parser import SubtitleParser
from video_renderer import VideoRenderer, RenderConfig
from ai_subtitle_generator import generate_subtitles_ai, get_ai_generator
from utils import (get_template_list, safe_int_conversion, ensure_directory,
                  is_valid_url, download_video_from_url, download_file_from_url,
                  is_video_file)
from constants import *


class VideoPlayer:
    """Handles video playback functionality"""

    def __init__(self, canvas, controls):
        self.canvas = canvas
        self.controls = controls
        self.cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30

    def load_video(self, video_path):
        """Load video for playback"""
        self.cleanup()

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise Exception("Không thể mở video")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0

        self.controls.enable_controls()
        self.update_frame()

    def update_frame(self):
        """Update current video frame"""
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()

            if ret and frame is not None:
                self._display_frame(frame)
                self.controls.update_progress(self.current_frame, self.total_frames)
            else:
                self.stop()

    def _display_frame(self, frame):
        """Display frame on canvas"""
        canvas_width = max(1, int(self.canvas.winfo_width()))
        canvas_height = max(1, int(self.canvas.winfo_height()))

        # Resize frame to fit canvas while maintaining aspect ratio
        frame_height, frame_width = frame.shape[:2]
        scale = min(canvas_width / frame_width, canvas_height / frame_height)
        new_width = max(1, int(frame_width * scale))
        new_height = max(1, int(frame_height * scale))

        if new_width != frame_width or new_height != frame_height:
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Convert and display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(pil_image)

        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor="center")
        self.canvas.image = photo

    def play(self):
        """Start or resume video playback"""
        if not self.is_playing and self.cap:
            self.is_playing = True
            self._play_next_frame()

    def pause(self):
        """Pause playback, keeping the current position"""
        self.is_playing = False

    def _play_next_frame(self):
        """Play next frame in sequence"""
        if self.is_playing and self.cap:
            self.update_frame()
            self.current_frame += 1

            if self.current_frame >= self.total_frames:
                self.current_frame = 0  # Loop

            if self.is_playing:
                self.canvas.after(int(1000/self.fps), self._play_next_frame)

    def stop(self):
        """Stop video playback"""
        self.is_playing = False
        self.current_frame = 0
        if self.cap:
            self.update_frame()

    def seek(self, progress):
        """Seek to specific position"""
        if self.cap:
            self.current_frame = int(progress * self.total_frames)
            self.update_frame()

    def cleanup(self):
        """Clean up resources"""
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None


class VideoControls:
    """Manages video player controls"""

    def __init__(self, play_button, stop_button, seek_slider, text_label, canvas):
        self.play_button = play_button
        self.stop_button = stop_button
        self.seek_slider = seek_slider
        self.text_label = text_label
        self.canvas = canvas

    def enable_controls(self):
        """Enable all controls"""
        self.play_button.configure(state="normal")
        self.stop_button.configure(state="normal")
        self.seek_slider.configure(state="normal")
        self.text_label.grid_remove()
        self.canvas.grid()

    def disable_controls(self):
        """Disable all controls"""
        self.play_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.seek_slider.configure(state="disabled")

    def update_progress(self, current_frame, total_frames):
        """Update progress slider"""
        if total_frames > 0:
            progress = (current_frame / total_frames) * 100
            self.seek_slider.set(progress)


class SubtitleApp(ctk.CTk):
    """Main application window with AI features"""

    def __init__(self):
        super().__init__()
        self.title("Subtitle Renderer Tool - AI Enhanced")
        self.geometry("1000x500")

        # Initialize components
        self.video_renderer = VideoRenderer()
        self._setup_variables()
        self._setup_video_player()
        self._create_widgets()

    def _setup_variables(self):
        """Setup application variables"""
        self.video_path = ctk.StringVar()
        self.sub_path = ctk.StringVar()
        self.video_url = ctk.StringVar()
        self.template_choice = ctk.StringVar(value="Tùy chỉnh")
        self.output_path = ctk.StringVar(value=DEFAULT_OUTPUT_PATH)
        self.ai_model = ctk.StringVar(value=DEFAULT_WHISPER_MODEL)
        self.language = ctk.StringVar(value="vi")

        # Video source selection
        self.video_source = ctk.StringVar(value="local")

        # Style variables
        self.font_path = ctk.StringVar(value=DEFAULT_FONT_PATH)
        self.font_size = ctk.StringVar(value=str(DEFAULT_STYLES["font_size"]))
        self.font_color = ctk.StringVar(value=DEFAULT_STYLES["font_color"])
        self.outline_color = ctk.StringVar(value=DEFAULT_STYLES["outline_color"])
        self.outline_width = ctk.StringVar(value=str(DEFAULT_STYLES["outline_width"]))
        self.position = ctk.StringVar(value=DEFAULT_STYLES["position"])

    def _setup_video_player(self):
        """Setup video player components"""
        # Create controls first (sẽ được khởi tạo sau khi tạo widgets)
        self.video_controls = None
        self.video_player = None
        self._preview_running = False

    def _create_widgets(self):
        """Create application widgets"""
        # Left frame - Controls
        left_frame = self._create_left_frame()
        left_frame.pack(side="left", fill="both", expand=False, padx=20, pady=20)

        # Right frame - Preview and progress
        right_frame = self._create_right_frame()
        right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # Setup video player after widgets are created
        self._setup_video_player_after_widgets()

    def _setup_video_player_after_widgets(self):
        """Setup video player after all widgets are created"""
        self.video_controls = VideoControls(
            self.play_button, self.stop_button, self.seek_slider,
            self.video_text_label, self.video_canvas
        )
        self.video_player = VideoPlayer(self.video_canvas, self.video_controls)

    def _create_left_frame(self):
        """Create left control frame"""
        frame = ctk.CTkScrollableFrame(self, width=450, label_text="🎬 Cài đặt video & AI")

        row = 0
        self._create_video_source_section(frame, row)
        row += 4

        self._create_subtitle_file_section(frame, row)
        row += 2

        self._create_ai_subtitle_section(frame, row)
        row += 3

        self._create_template_selector(frame, row)
        row += 2

        self._create_custom_style_section(frame, row)
        row += 2

        self._create_output_section(frame, row)
        row += 2

        self._create_action_buttons(frame, row)

        return frame

    def _create_video_source_section(self, parent, start_row):
        """Create video source selection section"""
        ctk.CTkLabel(parent, text="🎥 Nguồn video", anchor="w",
                    font=ctk.CTkFont(weight="bold")).grid(
            row=start_row, column=0, sticky="w", pady=(5, 2), columnspan=2
        )

        # Radio buttons for video source
        source_frame = ctk.CTkFrame(parent, fg_color="transparent")
        source_frame.grid(row=start_row+1, column=0, columnspan=2, sticky="we", pady=5)

        ctk.CTkRadioButton(source_frame, text="Video cục bộ", variable=self.video_source,
                          value="local", command=self._toggle_video_source).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(source_frame, text="URL Video", variable=self.video_source,
                          value="url", command=self._toggle_video_source).pack(side="left")

        # Local file input
        self.local_video_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.local_video_frame.grid(row=start_row+2, column=0, columnspan=2, sticky="we", pady=5)

        ctk.CTkLabel(self.local_video_frame, text="Chọn video:", anchor="w").pack(anchor="w")
        local_input_frame = ctk.CTkFrame(self.local_video_frame, fg_color="transparent")
        local_input_frame.pack(fill="x", pady=5)

        ctk.CTkEntry(local_input_frame, textvariable=self.video_path, width=300).pack(side="left", padx=(0, 10))
        ctk.CTkButton(local_input_frame, text="Chọn", width=80, command=self.browse_video,
                     fg_color="#2d7cff", hover_color="#1e5fd1").pack(side="left")

        # URL input
        self.url_video_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.url_video_frame.grid(row=start_row+3, column=0, columnspan=2, sticky="we", pady=5)

        ctk.CTkLabel(self.url_video_frame, text="URL Video:", anchor="w").pack(anchor="w")
        url_input_frame = ctk.CTkFrame(self.url_video_frame, fg_color="transparent")
        url_input_frame.pack(fill="x", pady=5)

        ctk.CTkEntry(url_input_frame, textvariable=self.video_url, width=300).pack(side="left", padx=(0, 10))
        self.download_button = ctk.CTkButton(url_input_frame, text="Tải về", width=80, command=self.start_download_thread,
                     fg_color="#ff6b35", hover_color="#e55a2b")
        self.download_button.pack(side="left")

        # Hide URL frame by default
        self.url_video_frame.grid_remove()

    def _create_subtitle_file_section(self, parent, row):
        """Create subtitle file input section"""
        ctk.CTkLabel(parent, text="📄 File phụ đề:", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(5, 2), columnspan=2
        )

        sub_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sub_frame.grid(row=row+1, column=0, columnspan=2, sticky="we", pady=5)

        ctk.CTkEntry(sub_frame, textvariable=self.sub_path, width=300).pack(side="left", padx=(0, 10))
        ctk.CTkButton(sub_frame, text="Chọn", width=80, command=self.browse_subtitle,
                     fg_color="#2d7cff", hover_color="#1e5fd1").pack(side="left")

    def _create_ai_subtitle_section(self, parent, start_row):
        """Create AI subtitle generation section"""
        ctk.CTkLabel(parent, text="🤖 Tạo phụ đề AI", anchor="w",
                    font=ctk.CTkFont(weight="bold")).grid(
            row=start_row, column=0, sticky="w", pady=(10, 5), columnspan=2
        )

        ai_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ai_frame.grid(row=start_row+1, column=0, columnspan=2, sticky="we", pady=5)

        # Model selection
        model_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        model_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(model_frame, text="Mô hình AI:", width=80, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(model_frame, variable=self.ai_model,
                         values=WHISPER_MODELS, width=120).pack(side="left", padx=(10, 20))

        # Language selection
        lang_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        lang_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(lang_frame, text="Ngôn ngữ:", width=80, anchor="w").pack(side="left")
        ctk.CTkEntry(lang_frame, textvariable=self.language, width=80).pack(side="left", padx=(10, 20))

        # Generate button
        self.ai_button = ctk.CTkButton(
            ai_frame, text="🎤 Tạo phụ đề AI", command=self.start_ai_generation_thread,
            fg_color="#8a2be2", hover_color="#6a1cb2", width=150
        )
        self.ai_button.pack(pady=10)

    def _create_template_selector(self, parent, row):
        """Create template selection widget"""
        ctk.CTkLabel(parent, text="🎨 Chọn template", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(10, 2), columnspan=2
        )

        self.template_menu = ctk.CTkOptionMenu(
            parent,
            values=get_template_list(),
            variable=self.template_choice,
            command=self._on_template_change
        )
        self.template_menu.grid(row=row+1, column=0, columnspan=2, sticky="we", pady=(0, 10))

    def _create_custom_style_section(self, parent, row):
        """Create custom style section"""
        self.custom_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.custom_frame.grid(row=row, column=0, columnspan=2, sticky="we", pady=(0, 10))

        # Create style inputs
        self._create_style_inputs(self.custom_frame)

    def _create_style_inputs(self, parent):
        """Create style input fields"""
        style_configs = [
            ("Font path:", self.font_path, 200),
            ("Font size:", self.font_size, 100),
            ("Font color:", self.font_color, 100),
            ("Viền màu:", self.outline_color, 100),
            ("Độ dày viền:", self.outline_width, 100),
            ("Vị trí:", self.position, 150)
        ]

        for i, (label, var, width) in enumerate(style_configs):
            self._create_labeled_entry(parent, label, var, width, i)

    def _create_labeled_entry(self, parent, label, variable, width, row):
        """Create labeled entry widget"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)

        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(frame, textvariable=variable, width=width).pack(side="left", expand=True, fill="x")

    def _create_output_section(self, parent, row):
        """Create output file section"""
        ctk.CTkLabel(parent, text="📤 File đầu ra", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(10, 2), columnspan=2
        )

        out_frame = ctk.CTkFrame(parent, fg_color="transparent")
        out_frame.grid(row=row+1, column=0, columnspan=2, sticky="we", pady=(0, 10))

        ctk.CTkEntry(out_frame, textvariable=self.output_path, width=300).pack(side="left", padx=(0, 10))
        ctk.CTkButton(out_frame, text="Chọn", width=80, command=self.browse_output,
                     fg_color="#2d7cff", hover_color="#1e5fd1").pack(side="left")

    def _create_action_buttons(self, parent, row):
        """Create action buttons"""
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="we")

        # Configure grid weights for centering
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self.preview_button = ctk.CTkButton(
            buttons_frame, text="🎬 Preview", command=self.start_preview_thread,
            fg_color="#ff6b35", hover_color="#e55a2b", width=140
        )
        self.preview_button.grid(row=0, column=0, padx=(0, 5), pady=2)

        self.render_button = ctk.CTkButton(
            buttons_frame, text="Render Video", command=self.start_render_thread,
            fg_color="#2d7cff", hover_color="#1e5fd1", width=140
        )
        self.render_button.grid(row=0, column=1, padx=(5, 0), pady=2)

    def _create_right_frame(self):
        """Create right preview frame"""
        frame = ctk.CTkFrame(self)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(5, weight=2)

        # Subtitle preview
        ctk.CTkLabel(frame, text="📜 Thời gian & phụ đề",
                    font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self.preview_box = ctk.CTkTextbox(frame)
        self.preview_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Progress section
        ctk.CTkLabel(frame, text="📈 Tiến trình",
                    font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Video preview section
        ctk.CTkLabel(frame, text="🎥 Video Preview",
                    font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=4, column=0, sticky="w", pady=(10, 5)
        )

        self.video_frame = self._create_video_player_section(frame)
        self.video_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))

        # Controls
        self.controls_frame = self._create_video_controls(frame)
        self.controls_frame.grid(row=6, column=0, sticky="ew", pady=(0, 10))

        return frame

    def _create_video_player_section(self, parent):
        """Create video player section"""
        video_frame = ctk.CTkFrame(parent)
        video_frame.grid_columnconfigure(0, weight=1)
        video_frame.grid_rowconfigure(0, weight=1)

        # Canvas for video display
        self.video_canvas = tk.Canvas(video_frame, bg="black", highlightthickness=0)
        self.video_canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.video_canvas.bind("<Configure>", self._on_video_canvas_resize)

        # Text label when no video is loaded
        self.video_text_label = ctk.CTkLabel(
            video_frame,
            text="Chọn video và phụ đề để preview",
            font=ctk.CTkFont(size=14)
        )
        self.video_text_label.grid(row=0, column=0)

        return video_frame

    def _create_video_controls(self, parent):
        """Create video controls"""
        controls_frame = ctk.CTkFrame(parent, fg_color="transparent")
        controls_frame.grid_columnconfigure(2, weight=1)

        self.play_button = ctk.CTkButton(
            controls_frame, text="▶️ Play", width=90,
            command=self._toggle_playback, state="disabled"
        )
        self.play_button.grid(row=0, column=0, padx=(0, 10))

        self.stop_button = ctk.CTkButton(
            controls_frame, text="⏹️ Stop", width=90,
            command=self._stop_preview, state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 10))

        self.seek_slider = ctk.CTkSlider(
            controls_frame, from_=0, to=100,
            command=self._seek_video, state="disabled"
        )
        self.seek_slider.grid(row=0, column=2, sticky="ew")

        return controls_frame

    def _toggle_video_source(self):
        """Toggle between local and URL video source"""
        if self.video_source.get() == "local":
            self.local_video_frame.grid()
            self.url_video_frame.grid_remove()
        else:
            self.local_video_frame.grid_remove()
            self.url_video_frame.grid()

    def _on_template_change(self, value):
        """Handle template change"""
        if value != "Tùy chỉnh":
            try:
                template = self.video_renderer.load_template(value)
                self.font_path.set(template.get("font", DEFAULT_FONT_PATH))
                self.font_size.set(str(template.get("font_size", DEFAULT_STYLES["font_size"])))
                self.font_color.set(template.get("font_color", DEFAULT_STYLES["font_color"]))
                self.outline_color.set(template.get("border_color", DEFAULT_STYLES["outline_color"]))
                self.outline_width.set(str(template.get("border_width", DEFAULT_STYLES["outline_width"])))
                self.position.set(template.get("position", DEFAULT_STYLES["position"]))
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tải template: {str(e)}")

    def _on_video_canvas_resize(self, event):
        """Handle video canvas resize"""
        try:
            if hasattr(self, 'video_player') and self.video_player:
                self.video_player.update_frame()
        except Exception:
            pass

    def _toggle_playback(self):
        """Toggle video playback between play and pause"""
        if not self.video_player or not self.video_player.cap:
            return

        if self.video_player.is_playing:
            # Pause must keep the current position, not reset the video
            self.video_player.pause()
            self.play_button.configure(text="▶️ Play")
        else:
            self.video_player.play()
            self.play_button.configure(text="⏸️ Pause")

    def _stop_preview(self):
        """Stop video preview"""
        if hasattr(self, 'video_player') and self.video_player:
            self.video_player.stop()
            self.play_button.configure(text="▶️ Play")

    def _seek_video(self, value):
        """Seek video to position"""
        if hasattr(self, 'video_player') and self.video_player:
            self.video_player.seek(value / 100.0)

    def browse_video(self):
        """Browse for video file"""
        file = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm")]
        )
        if file:
            self.video_path.set(file)

    def browse_subtitle(self):
        """Browse for subtitle file"""
        file_path = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.txt *.srt")])
        if file_path:
            self.sub_path.set(file_path)
            self._load_subtitle_preview(file_path)

    def browse_output(self):
        """Browse for output file"""
        file = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            initialfile="output.mp4"
        )
        if file:
            self.output_path.set(file)

    def download_video(self):
        """Download video from URL"""
        url = self.video_url.get().strip()
        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL video")
            return

        if not is_valid_url(url):
            messagebox.showerror("Lỗi", "URL không hợp lệ")
            return

        try:
            self.ai_button.configure(state="disabled", text="Đang tải video...")
            self.download_button.configure(state="disabled", text="Đang tải")
            downloaded_path = download_video_from_url(url)
            self.video_path.set(downloaded_path)
            messagebox.showinfo("Thành công", f"Đã tải video: {os.path.basename(downloaded_path)}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tải video: {str(e)}")
        finally:
            self.ai_button.configure(state="normal", text="🎤 Tạo phụ đề AI")
            self.download_button.configure(state="normal", text="Tải về")

    def start_download_thread(self):
        """Start video download in a separate thread"""
        thread = threading.Thread(target=self.download_video, daemon=True)
        thread.start()

    def start_ai_generation_thread(self):
        """Start AI subtitle generation in separate thread"""
        thread = threading.Thread(target=self.generate_ai_subtitles, daemon=True)
        thread.start()

    def generate_ai_subtitles(self):
        """Generate subtitles using AI"""
        video_path = self.video_path.get()

        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn video trước")
            return

        try:
            self.ai_button.configure(state="disabled", text="🔄 Đang xử lý...")
            self.progress_bar.set(0.1)

            # Generate subtitles using AI
            segments = generate_subtitles_ai(
                video_path,
                model_size=self.ai_model.get(),
                language=self.language.get()
            )

            if not segments:
                messagebox.showwarning("Cảnh báo", "Không thể tạo phụ đề từ video này")
                return

            # Save generated subtitles to temporary file
            temp_dir = tempfile.gettempdir()
            ai_subtitle_path = os.path.join(temp_dir, "ai_generated_subtitles.txt")

            with open(ai_subtitle_path, 'w', encoding='utf-8') as f:
                for segment in segments:
                    start_str = self._seconds_to_time(segment.start)
                    end_str = self._seconds_to_time(segment.end)
                    f.write(f"{start_str} - {end_str} {segment.text}\n")

            self.sub_path.set(ai_subtitle_path)
            self._load_subtitle_preview(ai_subtitle_path)

            self.progress_bar.set(1.0)
            messagebox.showinfo("Thành công", f"Đã tạo {len(segments)} đoạn phụ đề bằng AI")

        except Exception as e:
            messagebox.showerror("Lỗi AI", f"Lỗi tạo phụ đề AI: {str(e)}")
        finally:
            self.ai_button.configure(state="normal", text="🎤 Tạo phụ đề AI")
            self.progress_bar.set(0)

    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _load_subtitle_preview(self, file_path):
        """Load and preview subtitle file"""
        try:
            segments = SubtitleParser.parse_file(file_path)
            self.preview_box.delete("1.0", "end")

            preview_text = "\n".join([f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}" for seg in segments])
            self.preview_box.insert("1.0", preview_text)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc phụ đề: {str(e)}")

    def start_preview_thread(self):
        """Start preview in separate thread"""
        if self._preview_running:
            return

        # Prevent double clicks from launching two renders at the same time
        self._preview_running = True
        self.preview_button.configure(state="disabled", text="Đang tạo preview...")

        thread = threading.Thread(target=self.create_preview_video, daemon=True)
        thread.start()

    def create_preview_video(self):
        """Create preview video with subtitles"""
        preview_path = None
        try:
            # Validate inputs
            if not all([self.video_path.get(), self.sub_path.get()]):
                messagebox.showerror("Thiếu file", "Vui lòng chọn video và phụ đề.")
                return

            # Release the player so the previous preview file is not kept open
            self.after(0, self._release_preview_player)

            # Parse subtitles
            segments = SubtitleParser.parse_file(self.sub_path.get())
            config = self._get_render_config()

            # Use a unique file per render. Reusing a fixed name makes ffmpeg
            # overwrite the file the player is still reading, which corrupts
            # the H.264 stream (Invalid NAL unit size / Error splitting NAL).
            temp_dir = tempfile.gettempdir()
            preview_path = os.path.join(
                temp_dir, f"preview_subtitle_{time.time_ns()}.mp4"
            )
            ensure_directory(preview_path)

            self.video_renderer.render_video(
                input_video=self.video_path.get(),
                output_video=preview_path,
                segments=segments,
                config=config,
                is_preview=True
            )

            # Load preview
            if not (os.path.exists(preview_path) and os.path.getsize(preview_path) > 0):
                raise Exception("Preview video không được tạo thành công")

            # Make sure the produced file is actually decodable before showing it
            cap = cv2.VideoCapture(preview_path)
            try:
                is_valid = cap.isOpened() and cap.read()[0]
            finally:
                cap.release()

            if not is_valid:
                raise Exception("File preview bị lỗi, vui lòng thử tạo lại")

            # Tkinter widgets must be updated from the main thread
            self.after(0, self._load_preview_video, preview_path)

        except Exception as e:
            # Never leave a broken preview file behind
            if preview_path and os.path.exists(preview_path):
                try:
                    os.remove(preview_path)
                except OSError:
                    pass
            error_message = str(e)
            self.after(0, lambda: messagebox.showerror("Lỗi khi tạo preview", error_message))
        finally:
            self.after(0, self._finish_preview)

    def _finish_preview(self):
        """Reset preview button state (main thread)"""
        self._preview_running = False
        self.preview_button.configure(state="normal", text="🎬 Preview Video")

    def _release_preview_player(self):
        """Stop playback and release the current video file (main thread)"""
        if self.video_player:
            self.video_player.cleanup()

    def _load_preview_video(self, preview_path):
        """Load rendered preview video into the player (main thread)"""
        try:
            if not self.video_player:
                self._setup_video_player_after_widgets()
            self.video_player.load_video(preview_path)
            self._remove_old_previews(preview_path)
        except Exception as e:
            messagebox.showerror("Lỗi khi tạo preview", f"Không thể hiển thị preview: {str(e)}")

    @staticmethod
    def _remove_old_previews(keep_path):
        """Delete preview files from previous runs (best effort)"""
        keep = os.path.abspath(keep_path)
        pattern = os.path.join(tempfile.gettempdir(), "preview_subtitle*.mp4")
        for path in glob.glob(pattern):
            if os.path.abspath(path) == keep:
                continue
            try:
                os.remove(path)
            except OSError:
                pass

    def _get_render_config(self) -> RenderConfig:
        """Get render configuration from current settings"""
        if self.template_choice.get() == "Tùy chỉnh":
            return RenderConfig(
                font_path=self.font_path.get(),
                font_size=safe_int_conversion(self.font_size.get(), DEFAULT_STYLES["font_size"]),
                font_color=self.font_color.get(),
                outline_color=self.outline_color.get(),
                outline_width=safe_int_conversion(self.outline_width.get(), DEFAULT_STYLES["outline_width"]),
                position=self.position.get(),
                extra_styles={}
            )
        else:
            template = self.video_renderer.load_template(self.template_choice.get())
            return RenderConfig(
                font_path=template["font"],
                font_size=template["font_size"],
                font_color=template["font_color"],
                outline_color=template.get("border_color", DEFAULT_STYLES["outline_color"]),
                outline_width=template.get("border_width", DEFAULT_STYLES["outline_width"]),
                position=template.get("position", DEFAULT_STYLES["position"]),
                extra_styles={
                    "shadowcolor": template.get("shadow_color"),
                    "shadowx": template.get("shadow_x", 0),
                    "shadowy": template.get("shadow_y", 0),
                    "line_spacing": template.get("line_spacing", DEFAULT_STYLES["line_spacing"])
                }
            )

    def start_render_thread(self):
        """Start render in separate thread"""
        thread = threading.Thread(target=self.render_video, daemon=True)
        thread.start()

    def render_video(self):
        """Render final video"""
        try:
            self.progress_bar.set(0)
            self.render_button.configure(state="disabled")

            # Validate inputs
            if not all([self.video_path.get(), self.sub_path.get()]):
                messagebox.showerror("Thiếu file", "Vui lòng chọn video và phụ đề.")
                return

            print(f"Rendering video: {self.video_path.get()} with subtitles: {self.sub_path.get()}")
            # Parse and render
            segments = SubtitleParser.parse_file(self.sub_path.get())
            print(f"Segments: {segments}")
            config = self._get_render_config()

            ensure_directory(self.output_path.get())

            self.video_renderer.render_video(
                input_video=self.video_path.get(),
                output_video=self.output_path.get(),
                segments=segments,
                config=config,
                progress_callback=self.update_progress
            )

            messagebox.showinfo("Thành công", f"Video đã được xuất ra: {self.output_path.get()}")

        except Exception as e:
            messagebox.showerror("Lỗi khi render", str(e))
        finally:
            self.progress_bar.set(0)
            self.render_button.configure(state="normal")

    def update_progress(self, value):
        """Update progress bar"""
        self.after(0, lambda: self.progress_bar.set(value))

    def on_closing(self):
        """Handle application closing"""
        if hasattr(self, 'video_player') and self.video_player:
            self.video_player.cleanup()
        self.destroy()


def main():
    """Main entry point for GUI application"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = SubtitleApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()

