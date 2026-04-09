import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import numpy as np


class Layer:
    def __init__(self, image, filepath):
        self.original_image = image
        self.filepath = filepath
        self.name = filepath.split('/')[-1]
        self.mode = tk.StringVar(value="Нормальный")
        self.opacity = tk.DoubleVar(value=100.0)


class ImageEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SCOI_2 - Градационные преобразования")
        self.geometry("1280x800")

        self.layers = []
        self.base_size = None
        self.result_image = None
        self.original_composite = None
        self.tk_photo_res = None

        # Тоновая кривая
        self.curve_points = [(0, 255), (255, 0)]
        self.lookup_table = np.arange(256, dtype=np.uint8)
        self.selected_point = None

        self.create_widgets()
        self.build_lookup_table()
        self.draw_curve()

    def create_widgets(self):
        # ===== Левая часть =====
        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(left_frame, bg='lightgray', bd=2, relief="sunken")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(250, 300, text="Загрузите первое изображение", fill="gray")

        # ===== Гистограммы  =====
        hist_frame = tk.Frame(left_frame)
        hist_frame.pack(fill=tk.X, pady=10)

        before_frame = tk.Frame(hist_frame)
        before_frame.pack(side=tk.LEFT, padx=10)

        after_frame = tk.Frame(hist_frame)
        after_frame.pack(side=tk.LEFT, padx=10)

        tk.Label(before_frame, text="Гистограмма 1").pack()
        self.hist_before_canvas = tk.Canvas(
            before_frame,
            width=256,
            height=150,
            bg="white"
        )
        self.hist_before_canvas.pack()

        tk.Label(after_frame, text="Гистограмма 2").pack()
        self.hist_after_canvas = tk.Canvas(
            after_frame,
            width=256,
            height=150,
            bg="white"
        )
        self.hist_after_canvas.pack()

        tk.Button(
            left_frame,
            text="Сохранить результат",
            command=self.save_image,
            bg="lightgreen"
        ).pack(pady=10)

        # ===== Правая панель =====
        right_frame = tk.Frame(self, width=400, bd=2, relief="groove")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=1)
        right_frame.pack_propagate(False)

        tk.Label(
            right_frame,
            text="Управление",
            font=("Arial", 12, "bold")
        ).pack(pady=5)

        # Каналы
        channel_frame = tk.Frame(right_frame)
        channel_frame.pack(pady=5, fill=tk.X)

        tk.Label(channel_frame, text="Каналы:").pack(side=tk.LEFT, padx=5)

        self.channel_var = tk.StringVar(value="RGB")

        cb_channels = ttk.Combobox(
            channel_frame,
            textvariable=self.channel_var,
            values=["RGB", "R", "G", "B", "RG", "GB", "RB"],
            state="readonly",
            width=8
        )
        cb_channels.pack(side=tk.LEFT)
        cb_channels.bind("<<ComboboxSelected>>", lambda e: self.render_pipeline())

        # ===== Кривая =====
        tk.Label(
            right_frame,
            text="Тоновая кривая",
            font=("Arial", 10, "bold")
        ).pack(pady=10)

        # Пресеты
        preset_frame = tk.Frame(right_frame)
        preset_frame.pack(pady=5)

        tk.Button(preset_frame, text="Светлее", command=self.preset_bright).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(preset_frame, text="Темнее", command=self.preset_dark).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(preset_frame, text="Контраст", command=self.preset_contrast).pack(
            side=tk.LEFT, padx=2
        )

        self.curve_canvas = tk.Canvas(
            right_frame,
            width=256,
            height=256,
            bg="white",
            bd=2,
            relief="sunken"
        )
        self.curve_canvas.pack(pady=5)

        self.curve_canvas.bind("<Button-1>", self.on_curve_click)
        self.curve_canvas.bind("<B1-Motion>", self.on_curve_drag)
        self.curve_canvas.bind("<ButtonRelease-1>", self.on_curve_release)
        self.curve_canvas.bind("<Button-3>", self.add_curve_point)
        self.curve_canvas.bind("<Double-Button-1>", self.remove_curve_point)

        tk.Label(
            right_frame,
            text="ЛКМ — перемещение\nПКМ — добавить\nДвойной клик — удалить",
            justify="center"
        ).pack(pady=5)

        # ===== Слои =====
        self.layers_canvas = tk.Canvas(right_frame)
        scrollbar = tk.Scrollbar(
            right_frame,
            orient="vertical",
            command=self.layers_canvas.yview
        )

        self.scrollable_layers_frame = tk.Frame(self.layers_canvas)

        self.scrollable_layers_frame.bind(
            "<Configure>",
            lambda e: self.layers_canvas.configure(
                scrollregion=self.layers_canvas.bbox("all")
            )
        )

        self.layers_canvas.create_window(
            (0, 0),
            window=self.scrollable_layers_frame,
            anchor="nw"
        )

        self.layers_canvas.configure(yscrollcommand=scrollbar.set)

        self.layers_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(
            right_frame,
            text="+ Добавить слой",
            command=self.add_layer,
            bg="lightblue"
        ).pack(pady=10, fill=tk.X, padx=5)

    def add_layer(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )

        if not filepath:
            return

        try:
            img = Image.open(filepath).convert("RGB")
            new_layer = Layer(img, filepath)

            if not self.layers:
                self.base_size = img.size

            self.layers.append(new_layer)
            self.build_layer_ui(new_layer)
            self.render_pipeline()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")

    def build_layer_ui(self, layer):
        frame = tk.Frame(
            self.scrollable_layers_frame,
            bd=1,
            relief="solid",
            pady=5,
            padx=5
        )
        frame.pack(fill=tk.X, pady=2, padx=2)

        tk.Label(
            frame,
            text=layer.name,
            font=("Arial", 8, "bold")
        ).pack(anchor="w")

        c_frame = tk.Frame(frame)
        c_frame.pack(fill=tk.X)

        modes = [
            "Нормальный",
            "Сумма",
            "Разность",
            "Умножение",
            "Среднее",
            "Минимум",
            "Максимум",
            "Маска - Круг",
            "Маска - Квадрат",
            "Маска - Прямоугольник"
        ]

        cb = ttk.Combobox(
            c_frame,
            textvariable=layer.mode,
            values=modes,
            state="readonly",
            width=15
        )
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self.render_pipeline())

        scale = tk.Scale(
            c_frame,
            variable=layer.opacity,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda v: self.render_pipeline()
        )
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def build_lookup_table(self):
        points = sorted(self.curve_points, key=lambda p: p[0])

        x = np.array([p[0] for p in points])
        y = np.array([255 - p[1] for p in points])

        lut = np.interp(np.arange(256), x, y)
        self.lookup_table = np.clip(lut, 0, 255).astype(np.uint8)

    def apply_tone_curve(self, image):
        arr = np.array(image)
        arr = self.lookup_table[arr]
        return Image.fromarray(arr)

    def draw_curve(self):
        self.curve_canvas.delete("all")

        for i in range(0, 257, 64):
            self.curve_canvas.create_line(i, 0, i, 256, fill="lightgray")
            self.curve_canvas.create_line(0, i, 256, i, fill="lightgray")

        for i in range(255):
            y1 = 255 - self.lookup_table[i]
            y2 = 255 - self.lookup_table[i + 1]

            self.curve_canvas.create_line(i, y1, i + 1, y2, width=2)

        for x, y in self.curve_points:
            self.curve_canvas.create_oval(
                x - 4,
                y - 4,
                x + 4,
                y + 4,
                fill="red"
            )

    def find_nearest_point(self, x, y):
        for i, (px, py) in enumerate(self.curve_points):
            if abs(px - x) < 8 and abs(py - y) < 8:
                return i
        return None

    def on_curve_click(self, event):
        self.selected_point = self.find_nearest_point(event.x, event.y)

    def on_curve_drag(self, event):
        if self.selected_point is not None:
            x = min(max(event.x, 0), 255)
            y = min(max(event.y, 0), 255)

            self.curve_points[self.selected_point] = (x, y)
            self.update_curve()

    def on_curve_release(self, event):
        self.selected_point = None

    def add_curve_point(self, event):
        x = min(max(event.x, 0), 255)
        y = min(max(event.y, 0), 255)

        if any(abs(px - x) < 3 for px, _ in self.curve_points):
            return

        self.curve_points.append((x, y))
        self.update_curve()

    def remove_curve_point(self, event):
        idx = self.find_nearest_point(event.x, event.y)

        if idx is not None and len(self.curve_points) > 2:
            self.curve_points.pop(idx)
            self.update_curve()

    def update_curve(self):
        self.build_lookup_table()
        self.draw_curve()
        self.render_pipeline()

    # ===== Пресеты =====
    def preset_bright(self):
        self.curve_points = [(0, 255), (128, 80), (255, 0)]
        self.update_curve()

    def preset_dark(self):
        self.curve_points = [(0, 255), (128, 180), (255, 0)]
        self.update_curve()

    def preset_contrast(self):
        self.curve_points = [(0, 255), (64, 220), (192, 40), (255, 0)]
        self.update_curve()

    # ===== Гистограмма =====
    def draw_histogram(self, image, canvas):
        gray = np.mean(np.array(image), axis=2).astype(np.uint8)
        hist = np.bincount(gray.flatten(), minlength=256)

        canvas.delete("all")

        h = 150
        max_val = hist.max() if hist.max() > 0 else 1

        canvas.create_rectangle(0, 0, 255, h)

        for i in range(256):
            line_height = int((hist[i] / max_val) * h)

            canvas.create_line(
                i,
                h,
                i,
                h - line_height,
                fill="black",
                width=1
            )

    def render_pipeline(self):
        if not self.layers:
            return

        w, h = self.base_size
        comp_arr = np.zeros((h, w, 3), dtype=np.float32)

        ch_s = self.channel_var.get()
        acts = [i for i, c in enumerate("RGB") if c in ch_s]

        for layer in self.layers:
            img_res = layer.original_image.resize(
                (w, h),
                Image.Resampling.LANCZOS
            )

            lay_arr = np.array(img_res, dtype=np.float32)

            mode = layer.mode.get()
            alpha = layer.opacity.get() / 100.0

            if "Маска" in mode:
                mask_im = Image.new("L", (w, h), 0)
                draw = ImageDraw.Draw(mask_im)

                cx, cy = w // 2, h // 2
                s = min(w, h) // 3

                if "Круг" in mode:
                    draw.ellipse(
                        [cx - s, cy - s, cx + s, cy + s],
                        fill=255
                    )
                elif "Квадрат" in mode:
                    draw.rectangle(
                        [cx - s, cy - s, cx + s, cy + s],
                        fill=255
                    )
                elif "Прямоугольник" in mode:
                    draw.rectangle(
                        [cx - s * 1.5, cy - s, cx + s * 1.5, cy + s],
                        fill=255
                    )

                m_arr = np.array(mask_im, dtype=np.float32) / 255.0
                m_arr = np.stack([m_arr] * 3, axis=-1)

                blended = lay_arr * m_arr

            elif mode == "Сумма":
                blended = comp_arr + lay_arr
            elif mode == "Разность":
                blended = np.abs(comp_arr - lay_arr)
            elif mode == "Умножение":
                blended = (comp_arr * lay_arr) / 255.0
            elif mode == "Среднее":
                blended = (comp_arr + lay_arr) / 2.0
            elif mode == "Минимум":
                blended = np.minimum(comp_arr, lay_arr)
            elif mode == "Максимум":
                blended = np.maximum(comp_arr, lay_arr)
            else:
                blended = lay_arr

            for c in acts:
                comp_arr[..., c] = (
                    comp_arr[..., c] * (1.0 - alpha)
                    + blended[..., c] * alpha
                )

        self.original_composite = Image.fromarray(
            np.clip(comp_arr, 0, 255).astype(np.uint8)
        )

        self.result_image = self.apply_tone_curve(self.original_composite)

        self.update_canvas_preview()
        self.draw_histogram(
            self.original_composite,
            self.hist_before_canvas
        )
        self.draw_histogram(
            self.result_image,
            self.hist_after_canvas
        )

    def update_canvas_preview(self):
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        if cw < 10:
            cw, ch = 500, 500

        tmp = self.result_image.copy()
        tmp.thumbnail((cw, ch))

        self.tk_photo_res = ImageTk.PhotoImage(tmp)

        self.canvas.create_image(
            cw // 2,
            ch // 2,
            image=self.tk_photo_res
        )

    def save_image(self):
        if not self.result_image:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[
                ("JPEG", "*.jpg"),
                ("PNG", "*.png")
            ]
        )

        if path:
            self.result_image.save(path)


if __name__ == "__main__":
    app = ImageEditor()
    app.mainloop()