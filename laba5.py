import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import numpy as np
from PIL import Image, ImageTk


class FFTFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная: Частотная фильтрация (50 баллов)")

        self.img_original = None
        self.img_array = None

        # Настройка интерфейса
        self.setup_ui()

    def setup_ui(self):
        # Верхняя панель управления
        control_frame = ttk.Frame(self.root, padding=5)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(control_frame, text="Загрузить изображение", command=self.load_image).pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="Фильтр:").pack(side=tk.LEFT, padx=5)
        self.filter_type = ttk.Combobox(control_frame, values=[
            "НЧФ (Low-pass)",
            "ВЧФ (High-pass)",
            "Режекторный (Band-stop)",
            "Полосовой (Band-pass)",
            "Узкополосный режекторный"
        ], state="readonly", width=22)
        self.filter_type.current(0)
        self.filter_type.pack(side=tk.LEFT, padx=5)
        self.filter_type.bind("<<ComboboxSelected>>", lambda e: self.update_filter())

        ttk.Label(control_frame, text="R1:").pack(side=tk.LEFT, padx=2)
        self.r1_var = tk.DoubleVar(value=30.0)
        ttk.Entry(control_frame, textvariable=self.r1_var, width=5).pack(side=tk.LEFT)

        ttk.Label(control_frame, text="R2:").pack(side=tk.LEFT, padx=2)
        self.r2_var = tk.DoubleVar(value=60.0)
        ttk.Entry(control_frame, textvariable=self.r2_var, width=5).pack(side=tk.LEFT)

        ttk.Label(control_frame, text="Смещение X,Y (для узкополосного):").pack(side=tk.LEFT, padx=10)
        self.dx_var = tk.IntVar(value=50)
        self.dy_var = tk.IntVar(value=50)
        ttk.Entry(control_frame, textvariable=self.dx_var, width=4).pack(side=tk.LEFT)
        ttk.Entry(control_frame, textvariable=self.dy_var, width=4).pack(side=tk.LEFT)

        ttk.Button(control_frame, text="Применить фильтр", command=self.update_filter).pack(side=tk.LEFT, padx=15)
        ttk.Button(control_frame, text="Сохранить результат", command=self.save_result).pack(side=tk.LEFT, padx=5)

        # Панель отображения картинок
        display_frame = ttk.Frame(self.root)
        display_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # 4 канваса для изображений
        self.canvases = {}
        titles = [("Оригинал", 0, 0), ("Фурье-спектр (Амплитуда)", 0, 1),
                  ("Маска фильтра", 1, 0), ("Результат фильтрации", 1, 1)]

        for title, row, col in titles:
            frame = ttk.LabelFrame(display_frame, text=title)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            canvas = tk.Canvas(frame, width=400, height=400, bg="gray")
            canvas.pack(expand=True, fill=tk.BOTH)
            self.canvases[title] = {"canvas": canvas, "image": None}

        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(0, weight=1)
        display_frame.rowconfigure(1, weight=1)

    def load_image(self):
        path = filedialog.askopenfilename()
        if not path: return
        try:
            # Открываем изображение и ограничиваем размер для скорости (как указано в задании)
            img = Image.open(path).convert("RGB")
            img.thumbnail((512, 512))
            self.img_original = img
            self.img_array = np.array(img)
            self.display_img(self.img_array, "Оригинал")
            self.update_filter()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{e}")

    def create_mask(self, shape):
        rows, cols = shape
        center_r, center_c = rows // 2, cols // 2
        Y, X = np.ogrid[:rows, :cols]
        dist_from_center = np.sqrt((X - center_c) ** 2 + (Y - center_r) ** 2)

        mask = np.ones(shape, dtype=np.float32)
        f_type = self.filter_type.get()
        r1 = self.r1_var.get()
        r2 = self.r2_var.get()

        if f_type == "НЧФ (Low-pass)":
            mask[dist_from_center > r1] = 0
        elif f_type == "ВЧФ (High-pass)":
            mask[dist_from_center < r1] = 0
        elif f_type == "Режекторный (Band-stop)":
            mask[(dist_from_center >= r1) & (dist_from_center <= r2)] = 0
        elif f_type == "Полосовой (Band-pass)":
            mask = np.zeros(shape, dtype=np.float32)
            mask[(dist_from_center >= r1) & (dist_from_center <= r2)] = 1
        elif f_type == "Узкополосный режекторный":
            dx, dy = self.dx_var.get(), self.dy_var.get()
            # Симметричные точки для подавления гармоник
            dist1 = np.sqrt((X - (center_c + dx)) ** 2 + (Y - (center_r + dy)) ** 2)
            dist2 = np.sqrt((X - (center_c - dx)) ** 2 + (Y - (center_r - dy)) ** 2)
            mask[dist1 <= r1] = 0
            mask[dist2 <= r1] = 0

        return mask

    def process_channel(self, channel_array):
        # 1. Прямое 2D БПФ
        f_transform = np.fft.fft2(channel_array)
        # 2. Центрирование (сдвиг низких частот в центр)
        f_shifted = np.fft.fftshift(f_transform)

        # Визуализация амплитудного спектра: ln(|G| + 1)
        magnitude_spectrum = np.log(np.abs(f_shifted) + 1)

        # 3. Создание и применение маски
        mask = self.create_mask(channel_array.shape)
        f_filtered = f_shifted * mask

        # 4. Обратное преобразование
        f_ishift = np.fft.ifftshift(f_filtered)
        img_back = np.fft.ifft2(f_ishift)
        img_back = np.abs(img_back)  # Берем модуль

        return magnitude_spectrum, mask, img_back

    def update_filter(self):
        if self.img_array is None: return

        h, w, c = self.img_array.shape
        out_img = np.zeros_like(self.img_array, dtype=np.float64)
        mag_display = np.zeros_like(self.img_array, dtype=np.float64)
        mask_display = None

        # Обработка каждого цветового канала отдельно (Задание на 30/50)
        for i in range(c):
            mag, mask, filtered_channel = self.process_channel(self.img_array[:, :, i])
            out_img[:, :, i] = filtered_channel
            mag_display[:, :, i] = mag
            if i == 0: mask_display = mask  # Маска одинакова для всех каналов

        # Нормализация визуализации спектра для экрана
        mag_display = (mag_display / np.max(mag_display)) * 255

        # Нормализация результата
        out_img = np.clip(out_img, 0, 255).astype(np.uint8)

        # Отображение
        self.display_img(mag_display.astype(np.uint8), "Фурье-спектр (Амплитуда)")
        self.display_img((mask_display * 255).astype(np.uint8), "Маска фильтра", is_gray=True)
        self.display_img(out_img, "Результат фильтрации")
        self.result_img = Image.fromarray(out_img)

    def display_img(self, img_array, canvas_name, is_gray=False):
        if is_gray:
            img = Image.fromarray(img_array, mode='L')
        else:
            img = Image.fromarray(img_array, mode='RGB')

        # Масштабирование для холста 400x400
        img.thumbnail((400, 400))
        photo = ImageTk.PhotoImage(img)

        canvas = self.canvases[canvas_name]["canvas"]
        canvas.delete("all")
        # Центрируем изображение на холсте
        cw, ch = int(canvas['width']), int(canvas['height'])
        canvas.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=photo)
        self.canvases[canvas_name]["image"] = photo  # Сохраняем ссылку, чтобы сборщик мусора не удалил

    def save_result(self):
        if hasattr(self, 'result_img'):
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path:
                self.result_img.save(path)
                messagebox.showinfo("Успех", "Изображение сохранено!")


if __name__ == "__main__":
    root = tk.Tk()
    app = FFTFilterApp(root)
    root.mainloop()