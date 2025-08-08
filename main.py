import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from subtitle_parser import parse_subtitle_file, convert_custom_lines_to_segments
from video_renderer import render_video_with_subtitles, load_template, parse_srt_to_custom_format
import threading


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

        self.create_widgets()

    def create_widgets(self):
        # === KHUNG TRÁI ===
        left_frame = ctk.CTkScrollableFrame(self, width=450, label_text="🎬 Cài đặt video")
        left_frame.pack(side="left", fill="both", expand=False, padx=20, pady=20)

        appearance_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        appearance_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(appearance_frame, text="🎨 Giao diện:", anchor="w").pack(side="left", padx=(0, 10))
        appearance_menu = ctk.CTkOptionMenu(
            appearance_frame,
            values=["System", "Light", "Dark"],
            variable=self.appearance_mode,
            command=self.change_appearance
        )
        appearance_menu.pack(side="left")

        def build_file_input_block(label_text, var, command):
            ctk.CTkLabel(left_frame, text=label_text, anchor="w").pack(anchor="w", pady=(5, 2))
            frame = ctk.CTkFrame(left_frame, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkEntry(frame, textvariable=var, width=300).pack(side="left", padx=(0, 10))
            ctk.CTkButton(frame, text="Chọn", width=80, command=command, fg_color="#2d7cff",
                          hover_color="#1e5fd1").pack(side="left")

        build_file_input_block("🎥 Video đầu vào:", self.video_path, self.browse_video)
        build_file_input_block("📄 File phụ đề:", self.sub_path, self.browse_subtitle)

        ctk.CTkLabel(left_frame, text="🎨 Chọn template", anchor="w").pack(anchor="w", pady=(10, 2))
        self.template_menu = ctk.CTkOptionMenu(
            left_frame,
            values=self.get_template_list(),
            variable=self.template_choice,
            command=self.toggle_custom_style
        )
        self.template_menu.pack(fill="x", pady=(0, 10))

        self.custom_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.custom_frame.pack(fill="x", pady=(0, 10))
        self.build_custom_style_form(self.custom_frame)

        ctk.CTkLabel(left_frame, text="📤 File đầu ra", anchor="w").pack(anchor="w", pady=(10, 2))
        ctk.CTkEntry(left_frame, textvariable=self.output_path, width=400).pack(pady=(0, 10))

        self.render_button = ctk.CTkButton(
            left_frame, text="Render Video", command=self.start_render_thread,
            fg_color="#2d7cff", hover_color="#1e5fd1"
        )
        self.render_button.pack(pady=10)

        # === KHUNG PHẢI ===
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(right_frame, text="📜 Thời gian & phụ đề", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=(0, 5))
        self.preview_box = ctk.CTkTextbox(right_frame, width=450, height=300)
        self.preview_box.pack(pady=(0, 20))

        ctk.CTkLabel(right_frame, text="📈 Tiến trình render video", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(right_frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

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
            self.custom_frame.pack(fill="x", pady=(10, 0))
        else:
            self.custom_frame.pack_forget()

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

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = SubtitleApp()
    app.mainloop()
