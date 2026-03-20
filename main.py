import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import numpy as np


class ImageProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Обработка изображений")
        # Увеличим размер окна, чтобы поместился предпросмотр
        self.geometry("700x750")

        self.img1_pil = None
        self.img2_pil = None
        self.result_image = None

        # Ссылки на фото для tkinter, чтобы их не удалил сборщик мусора
        self.tk_photo1 = None
        self.tk_photo2 = None
        self.tk_photo_res = None

        self.create_widgets()

    def create_widgets(self):
        # --- Холст для отображения картинок ---
        self.canvas = tk.Canvas(self, width=500, height=400, bg='lightgray', bd=2, relief="sunken")
        self.canvas.pack(pady=10)
        self.canvas.create_text(250, 200, text="Здесь будет предпросмотр", fill="gray")

        # --- Кнопки загрузки ---
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Загрузить Изображение 1", command=lambda: self.load_image(1)).grid(row=0,
                                                                                                            column=0,
                                                                                                            padx=5)
        self.lbl_img1 = tk.Label(btn_frame, text="Файл 1 не выбран")
        self.lbl_img1.grid(row=0, column=1, padx=5)

        tk.Button(btn_frame, text="Загрузить Изображение 2", command=lambda: self.load_image(2)).grid(row=1,
                                                                                                               column=0,
                                                                                                               padx=5,
                                                                                                               pady=5)
        self.lbl_img2 = tk.Label(btn_frame, text="Файл 2 не выбран")
        self.lbl_img2.grid(row=1, column=1, padx=5)

        # --- Настройки операций ---
        settings_frame = tk.Frame(self)
        settings_frame.pack(pady=10)

        tk.Label(settings_frame, text="Операция:").grid(row=0, column=0)
        self.operation_var = tk.StringVar(value="Сумма")
        operations = ["Сумма", "Произведение", "Среднее", "Минимум", "Максимум", "Маска - Круг", "Маска - Квадрат",
                      "Маска - Прямоугольник"]
        ttk.Combobox(settings_frame, textvariable=self.operation_var, values=operations, state="readonly").grid(row=0,
                                                                                                                column=1,
                                                                                                                padx=5)

        tk.Label(settings_frame, text="Каналы:").grid(row=0, column=2)
        self.channel_var = tk.StringVar(value="RGB")
        channels = ["RGB", "R", "G", "B", "RG", "GB", "RB"]
        ttk.Combobox(settings_frame, textvariable=self.channel_var, values=channels, state="readonly", width=5).grid(
            row=0, column=3, padx=5)

        # --- Кнопки выполнения и сохранения ---
        tk.Button(self, text="Выполнить операцию", command=self.process_images, bg="lightblue",
                  font=("Arial", 10, "bold")).pack(pady=10)
        tk.Button(self, text="Сохранить результат", command=self.save_image, bg="lightgreen").pack(pady=5)

    def load_image(self, img_num):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            try:
                img = Image.open(filepath).convert('RGB')
                if img_num == 1:
                    self.img1_pil = img
                    self.lbl_img1.config(text=filepath.split('/')[-1])
                else:
                    self.img2_pil = img
                    self.lbl_img2.config(text=filepath.split('/')[-1])

                self.update_preview()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{e}")

    def update_preview(self):
        """Отрисовывает изображения на холсте (второе поверх первого)"""
        self.canvas.delete("all")

        canvas_w, canvas_h = 500, 400

        # Функция для создания превью с сохранением пропорций
        def get_preview(img_pil):
            img_copy = img_pil.copy()
            img_copy.thumbnail((canvas_w, canvas_h))
            return ImageTk.PhotoImage(img_copy)

        # Отрисовка первого изображения (снизу)
        if self.img1_pil:
            self.tk_photo1 = get_preview(self.img1_pil)
            # Размещаем по центру холста
            self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.tk_photo1, anchor="center")

        # Отрисовка второго изображения (сверху)
        if self.img2_pil:
            self.tk_photo2 = get_preview(self.img2_pil)
            self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.tk_photo2, anchor="center")

    def process_images(self):
        if not self.img1_pil:
            messagebox.showerror("Ошибка", "Загрузите хотя бы первое изображение!")
            return

        op = self.operation_var.get()
        needs_second_img = not op.startswith("Маска")

        if needs_second_img and not self.img2_pil:
            messagebox.showerror("Ошибка", "Для этой операции нужно два изображения!")
            return

        # Работаем с копиями оригиналов
        img1 = self.img1_pil.copy()

        if needs_second_img:
            img2 = self.img2_pil.copy()
            # Меньшее изображение растягивается до размеров большего [cite: 17, 18]
            area1 = img1.width * img1.height
            area2 = img2.width * img2.height

            if area1 > area2:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
                target_size = img1.size
            else:
                img1 = img1.resize(img2.size, Image.Resampling.LANCZOS)
                target_size = img2.size
        else:
            target_size = img1.size
            img2 = None

        # Переводим в массивы numpy (float16 для математики)
        arr1 = np.array(img1, dtype=np.float16)
        arr2 = np.array(img2, dtype=np.float16) if img2 else None
        result_arr = np.copy(arr1)

        # Выбор активных каналов (0-R, 1-G, 2-B) [cite: 15]
        ch_str = self.channel_var.get()
        active_channels = []
        if 'R' in ch_str: active_channels.append(0)
        if 'G' in ch_str: active_channels.append(1)
        if 'B' in ch_str: active_channels.append(2)

        # Математические операции над пикселями [cite: 12]
        if op == "Сумма":
            result_arr[..., active_channels] = arr1[..., active_channels] + arr2[..., active_channels]
        elif op == "Произведение":
            result_arr[..., active_channels] = (arr1[..., active_channels] * arr2[..., active_channels]) / 255.0
        elif op == "Среднее":
            result_arr[..., active_channels] = (arr1[..., active_channels] + arr2[..., active_channels]) / 2.0
        elif op == "Минимум":
            result_arr[..., active_channels] = np.minimum(arr1[..., active_channels], arr2[..., active_channels])
        elif op == "Максимум":
            result_arr[..., active_channels] = np.maximum(arr1[..., active_channels], arr2[..., active_channels])
        elif op.startswith("Маска"):
            mask_img = Image.new('L', target_size, 0)
            draw = ImageDraw.Draw(mask_img)
            w, h = target_size
            center_x, center_y = w // 2, h // 2
            size = min(w, h) // 3

            if "Круг" in op:
                draw.ellipse([center_x - size, center_y - size, center_x + size, center_y + size], fill=255)
            elif "Квадрат" in op:
                draw.rectangle([center_x - size, center_y - size, center_x + size, center_y + size], fill=255)
            elif "Прямоугольник" in op:
                draw.rectangle([center_x - size * 1.5, center_y - size, center_x + size * 1.5, center_y + size],
                               fill=255)

            mask_arr = np.array(mask_img, dtype=np.float16) / 255.0
            mask_arr = np.stack([mask_arr] * 3, axis=-1)
            result_arr[..., active_channels] = arr1[..., active_channels] * mask_arr[..., active_channels]

        # Ограничиваем значения от 0 до 255
        result_arr = np.clip(result_arr, 0, 255).astype(np.uint8)
        self.result_image = Image.fromarray(result_arr)

        # Вывод результата на холст предпросмотра
        self.canvas.delete("all")
        res_copy = self.result_image.copy()
        res_copy.thumbnail((500, 400))
        self.tk_photo_res = ImageTk.PhotoImage(res_copy)
        self.canvas.create_image(250, 200, image=self.tk_photo_res, anchor="center")

        messagebox.showinfo("Успех", "Операция выполнена! Результат выведен на экран.")

    def save_image(self):
        if not self.result_image:
            messagebox.showwarning("Внимание", "Сначала выполните операцию!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if filepath:
            self.result_image.save(filepath)
            messagebox.showinfo("Сохранено", f"Изображение успешно сохранено в {filepath}")


if __name__ == "__main__":
    app = ImageProcessorApp()
    app.mainloop()