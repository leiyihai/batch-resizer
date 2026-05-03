import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from processor import process_images

PRESET_SIZES = [
    ("1920 × 1080", 1920, 1080),
    ("1280 × 720", 1280, 720),
    ("800 × 600", 800, 600),
    ("400 × 300", 400, 300),
    ("256 × 256", 256, 256),
    ("128 × 128", 128, 128),
    ("64 × 64", 64, 64),
    ("32 × 32", 32, 32),
]


class ResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("批量图片尺寸修改工具")
        self.root.resizable(False, False)

        self._progress_queue = queue.Queue()
        self._running = False

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ── Folder selection ──────────────────────────────────────
        folder_frame = ttk.LabelFrame(self.root, text="文件夹设置", padding=10)
        folder_frame.pack(fill="x", **pad)

        self._build_folder_row(folder_frame, "输入文件夹:", 0, self._browse_input)
        self._build_folder_row(folder_frame, "输出文件夹:", 1, self._browse_output)

        # ── Size selection ────────────────────────────────────────
        size_frame = ttk.LabelFrame(self.root, text="目标尺寸", padding=10)
        size_frame.pack(fill="x", **pad)

        self._size_var = tk.StringVar(value="preset_0")
        self._custom_w = tk.StringVar(value="800")
        self._custom_h = tk.StringVar(value="600")

        for i, (label, w, h) in enumerate(PRESET_SIZES):
            ttk.Radiobutton(
                size_frame, text=label, variable=self._size_var,
                value=f"preset_{i}", command=self._on_size_toggle
            ).grid(row=i, column=0, sticky="w", pady=1)

        custom_row = len(PRESET_SIZES)
        ttk.Radiobutton(
            size_frame, text="自定义尺寸:", variable=self._size_var,
            value="custom", command=self._on_size_toggle
        ).grid(row=custom_row, column=0, sticky="w", pady=1)

        custom_inner = ttk.Frame(size_frame)
        custom_inner.grid(row=custom_row, column=1, sticky="w", padx=(8, 0))
        self._custom_w_entry = ttk.Entry(custom_inner, textvariable=self._custom_w, width=6)
        self._custom_w_entry.pack(side="left")
        ttk.Label(custom_inner, text=" × ").pack(side="left")
        self._custom_h_entry = ttk.Entry(custom_inner, textvariable=self._custom_h, width=6)
        self._custom_h_entry.pack(side="left")
        ttk.Label(custom_inner, text=" 像素").pack(side="left")

        # ── Progress & action ─────────────────────────────────────
        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill="x", **pad)

        self._run_btn = ttk.Button(action_frame, text="开始处理", command=self._on_run)
        self._run_btn.pack(pady=(0, 8))

        self._progress = ttk.Progressbar(action_frame, mode="determinate")
        self._progress.pack(fill="x")

        self._status_label = ttk.Label(action_frame, text="就绪", anchor="center")
        self._status_label.pack(pady=(4, 0))

    def _build_folder_row(self, parent, label_text, row, browse_cmd):
        ttk.Label(parent, text=label_text, width=12).grid(row=row, column=0, sticky="e")
        entry = ttk.Entry(parent, width=52)
        entry.grid(row=row, column=1, padx=(6, 4))
        ttk.Button(parent, text="浏览...", width=8, command=browse_cmd).grid(row=row, column=2)

        attr = "_input_entry" if row == 0 else "_output_entry"
        setattr(self, attr, entry)

    # ── Folder browsing ────────────────────────────────────────────

    def _browse_input(self):
        path = filedialog.askdirectory(title="选择输入文件夹")
        if path:
            self._input_entry.delete(0, "end")
            self._input_entry.insert(0, path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出文件夹")
        if path:
            self._output_entry.delete(0, "end")
            self._output_entry.insert(0, path)

    # ── Size toggle ────────────────────────────────────────────────

    def _on_size_toggle(self):
        is_custom = self._size_var.get() == "custom"
        state = "normal" if is_custom else "disabled"
        self._custom_w_entry.configure(state=state)
        self._custom_h_entry.configure(state=state)

    def _get_target_size(self):
        choice = self._size_var.get()
        if choice == "custom":
            return (int(self._custom_w.get()), int(self._custom_h.get()))
        idx = int(choice.split("_")[1])
        return (PRESET_SIZES[idx][1], PRESET_SIZES[idx][2])

    # ── Run ────────────────────────────────────────────────────────

    def _on_run(self):
        input_dir = self._input_entry.get().strip()
        output_dir = self._output_entry.get().strip()

        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("错误", "请选择一个有效的输入文件夹。")
            return
        if not output_dir:
            messagebox.showerror("错误", "请选择一个输出文件夹。")
            return
        if input_dir == output_dir:
            messagebox.showerror("错误", "输入和输出文件夹不能相同。")
            return

        try:
            target_size = self._get_target_size()
            if target_size[0] <= 0 or target_size[1] <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "请输入有效的正整数尺寸。")
            return

        self._running = True
        self._run_btn.configure(state="disabled")
        self._status_label.configure(text="正在扫描图片文件...")
        self._progress.configure(value=0)

        thread = threading.Thread(
            target=self._worker,
            args=(input_dir, output_dir, target_size),
            daemon=True,
        )
        thread.start()
        self._poll_progress()

    def _worker(self, input_dir, output_dir, target_size):
        def on_progress(current, total):
            self._progress_queue.put(("progress", current, total))

        success, errors_count, errors_list = process_images(
            input_dir, output_dir, target_size, on_progress
        )
        self._progress_queue.put(("done", success, errors_count, errors_list))

    def _poll_progress(self):
        try:
            while True:
                msg = self._progress_queue.get_nowait()
                if msg[0] == "progress":
                    _kind, current, total = msg
                    self._progress.configure(maximum=total, value=current)
                    self._status_label.configure(
                        text=f"处理中... {current}/{total}"
                    )
                elif msg[0] == "done":
                    _kind, success, errors_count, errors_list = msg
                    self._progress.configure(value=self._progress["maximum"])
                    self._status_label.configure(
                        text=f"完成！成功 {success} 张，失败 {errors_count} 张"
                    )
                    self._run_btn.configure(state="normal")
                    self._running = False
                    if errors_list:
                        messagebox.showwarning(
                            "处理完成（有错误）",
                            "\n".join(errors_list[:20]),
                        )
                    else:
                        messagebox.showinfo("完成", f"成功处理 {success} 张图片。")
                    return
        except queue.Empty:
            pass

        if self._running:
            self.root.after(100, self._poll_progress)


def create_app():
    root = tk.Tk()
    ResizerApp(root)
    root.mainloop()
