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
        self.ui_frame = None


class ImageEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SCOI_1")
        self.geometry("900x700")

        self.layers = []  # Список слоев
        self.base_size = None  # Размер первого изображения
        self.result_image = None
        self.tk_photo_res = None

        self.create_widgets()

    def create_widgets(self):
        # Предпросмотр
        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(left_frame, bg='lightgray', bd=2, relief="sunken")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(250, 300, text="Загрузите первое изображение", fill="gray", tags="placeholder")

        tk.Button(left_frame, text="Сохранить результат", command=self.save_image, bg="lightgreen").pack(pady=10)

        # Панель слоев
        right_frame = tk.Frame(self, width=320, bd=2, relief="groove")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Управление", font=("Arial", 12, "bold")).pack(pady=5)

        # Выбор каналов (глобально)
        channel_frame = tk.Frame(right_frame)
        channel_frame.pack(pady=5, fill=tk.X)
        tk.Label(channel_frame, text="Каналы:").pack(side=tk.LEFT, padx=5)
        self.channel_var = tk.StringVar(value="RGB")
        cb_channels = ttk.Combobox(channel_frame, textvariable=self.channel_var,
                                   values=["RGB", "R", "G", "B", "RG", "GB", "RB"], state="readonly", width=8)
        cb_channels.pack(side=tk.LEFT)
        cb_channels.bind("<<ComboboxSelected>>", lambda e: self.render_pipeline())

        self.layers_canvas = tk.Canvas(right_frame)
        scrollbar = tk.Scrollbar(right_frame, orient="vertical", command=self.layers_canvas.yview)
        self.scrollable_layers_frame = tk.Frame(self.layers_canvas)

        self.scrollable_layers_frame.bind(
            "<Configure>",
            lambda e: self.layers_canvas.configure(scrollregion=self.layers_canvas.bbox("all"))
        )

        self.layers_canvas.create_window((0, 0), window=self.scrollable_layers_frame, anchor="nw")
        self.layers_canvas.configure(yscrollcommand=scrollbar.set)
        self.layers_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(right_frame, text="+ Добавить слой", command=self.add_layer, bg="lightblue").pack(pady=10, fill=tk.X,
                                                                                                    padx=5)

    def add_layer(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if not filepath: return
        try:
            img = Image.open(filepath).convert('RGB')
            new_layer = Layer(img, filepath)
            if not self.layers: self.base_size = img.size
            self.layers.append(new_layer)
            self.build_layer_ui(new_layer)
            self.render_pipeline()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")

    def build_layer_ui(self, layer):
        frame = tk.Frame(self.scrollable_layers_frame, bd=1, relief="solid", pady=5, padx=5)
        frame.pack(fill=tk.X, pady=2, padx=2)

        tk.Label(frame, text=layer.name, font=("Arial", 8, "bold")).pack(anchor="w")

        c_frame = tk.Frame(frame)
        c_frame.pack(fill=tk.X)

        modes = ["Нормальный", "Сумма", "Разность", "Умножение", "Среднее", "Минимум", "Максимум",
                 "Маска - Круг", "Маска - Квадрат", "Маска - Прямоугольник"]
        cb = ttk.Combobox(c_frame, textvariable=layer.mode, values=modes, state="readonly", width=15)
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self.render_pipeline())

        scale = tk.Scale(c_frame, variable=layer.opacity, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False,
                         command=lambda v: self.render_pipeline())
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def render_pipeline(self):
        if not self.layers: return
        w, h = self.base_size
        comp_arr = np.zeros((h, w, 3), dtype=np.float16)

        # Парсинг каналов
        ch_s = self.channel_var.get()
        acts = [i for i, c in enumerate('RGB') if c in ch_s]

        for layer in self.layers:
            # Масштабирование слоя
            img_res = layer.original_image.resize((w, h), Image.Resampling.LANCZOS)
            lay_arr = np.array(img_res, dtype=np.float16)

            mode = layer.mode.get()
            alpha = layer.opacity.get() / 100.0

            # Логика маски
            if "Маска" in mode:
                mask_im = Image.new('L', (w, h), 0)
                draw = ImageDraw.Draw(mask_im)
                cx, cy = w // 2, h // 2
                s = min(w, h) // 3
                if "Круг" in mode:
                    draw.ellipse([cx - s, cy - s, cx + s, cy + s], fill=255)
                elif "Квадрат" in mode:
                    draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=255)
                elif "Прямоугольник" in mode:
                    draw.rectangle([cx - s * 1.5, cy - s, cx + s * 1.5, cy + s], fill=255)

                m_arr = np.array(mask_im, dtype=np.float16) / 255.0
                m_arr = np.stack([m_arr] * 3, axis=-1)
                blended = lay_arr * m_arr  # Маскируем текущий слой

            # Режимы наложения
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
                blended = lay_arr  # Нормальный

            # Применение прозрачности и каналов
            for c in acts:
                comp_arr[..., c] = comp_arr[..., c] * (1.0 - alpha) + blended[..., c] * alpha

        self.result_image = Image.fromarray(np.clip(comp_arr, 0, 255).astype(np.uint8))
        self.update_canvas_preview()

    def update_canvas_preview(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10: cw, ch = 500, 500

        tmp = self.result_image.copy()
        tmp.thumbnail((cw, ch))
        self.tk_photo_res = ImageTk.PhotoImage(tmp)
        self.canvas.create_image(cw // 2, ch // 2, image=self.tk_photo_res)

    def save_image(self):
        if not self.result_image: return
        path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if path: self.result_image.save(path)


if __name__ == "__main__":
    app = ImageEditor()
    app.mainloop()