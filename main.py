import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
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
        self.geometry("900x650")

        self.layers = []  # Список слоев
        self.base_size = None  # Размер первого загруженного изображения
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
        right_frame = tk.Frame(self, width=300, bd=2, relief="groove")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Слои", font=("Arial", 12, "bold")).pack(pady=5)

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

        tk.Button(right_frame, text="+ Добавить изображение", command=self.add_layer, bg="lightblue").pack(pady=10,
                                                                                                           fill=tk.X,
                                                                                                           padx=5)

    def add_layer(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if not filepath:
            return

        try:
            img = Image.open(filepath).convert('RGB')
            new_layer = Layer(img, filepath)

            if not self.layers:
                self.base_size = img.size

            self.layers.append(new_layer)
            self.build_layer_ui(new_layer)
            self.render_pipeline()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{e}")

    def build_layer_ui(self, layer):
        frame = tk.Frame(self.scrollable_layers_frame, bd=1, relief="solid", pady=5, padx=5)
        frame.pack(fill=tk.X, pady=2, padx=2)
        layer.ui_frame = frame

        # Имя файла
        tk.Label(frame, text=layer.name, font=("Arial", 9, "bold")).pack(anchor="w")

        # Настройки: Режим и Прозрачность
        controls_frame = tk.Frame(frame)
        controls_frame.pack(fill=tk.X)

        modes = ["Нормальный", "Сумма", "Разность", "Умножение", "Среднее", "Минимум", "Максимум"]
        cb = ttk.Combobox(controls_frame, textvariable=layer.mode, values=modes, state="readonly", width=12)
        cb.pack(side=tk.LEFT, padx=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.render_pipeline())

        scale = tk.Scale(controls_frame, variable=layer.opacity, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False,
                         command=lambda v: self.render_pipeline())
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Label(controls_frame, textvariable=layer.opacity).pack(side=tk.LEFT)

    def render_pipeline(self):
        if not self.layers:
            return

        w, h = self.base_size
        composite_arr = np.zeros((h, w, 3), dtype=np.float16)

        # Проходим по всем слоям снизу вверх
        for layer in self.layers:
            # Подгоняем размер под базовый холст
            img_resized = layer.original_image.resize((w, h), Image.Resampling.LANCZOS)
            layer_arr = np.array(img_resized, dtype=np.float16)

            mode = layer.mode.get()
            opacity = layer.opacity.get() / 100.0

            # Применяем режим наложения
            if mode == "Нормальный":
                blended = layer_arr
            elif mode == "Сумма":
                blended = composite_arr + layer_arr
            elif mode == "Разность":
                blended = np.abs(composite_arr - layer_arr)
            elif mode == "Умножение":
                blended = (composite_arr * layer_arr) / 255.0
            elif mode == "Среднее":
                blended = (composite_arr + layer_arr) / 2.0
            elif mode == "Минимум":
                blended = np.minimum(composite_arr, layer_arr)
            elif mode == "Максимум":
                blended = np.maximum(composite_arr, layer_arr)
            else:
                blended = layer_arr

            # Применяем прозрачность (Alpha blending)
            # composite = старый_пиксель * (1 - alpha) + новый_пиксель * alpha
            composite_arr = composite_arr * (1.0 - opacity) + blended * opacity

        # Ограничиваем значения и переводим в картинку
        composite_arr = np.clip(composite_arr, 0, 255).astype(np.uint8)
        self.result_image = Image.fromarray(composite_arr)

        self.update_canvas_preview()

    def update_canvas_preview(self):
        self.canvas.delete("all")

        # Размеры холста
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 10: canvas_w, canvas_h = 500, 500  # Fallback если окно еще не отрисовалось

        res_copy = self.result_image.copy()
        res_copy.thumbnail((canvas_w, canvas_h))
        self.tk_photo_res = ImageTk.PhotoImage(res_copy)

        self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.tk_photo_res, anchor="center")

    def save_image(self):
        if not self.result_image:
            messagebox.showwarning("Внимание", "Нет изображений для сохранения!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if filepath:
            self.result_image.save(filepath)
            messagebox.showinfo("Сохранено", f"Изображение успешно сохранено!")


if __name__ == "__main__":
    app = ImageEditor()
    app.mainloop()