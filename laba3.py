import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, ttk
import os


class BinarizationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система цифровой обработки изображений - Бинаризация")
        self.root.geometry("1000x700")

        # Переменные для хранения данных
        self.original_gray = None
        self.result_image = None
        self.S = None  # Интегральная матрица сумм
        self.S2 = None  # Интегральная матрица квадратов

        self._setup_ui()

    def _setup_ui(self):
        # Панель управления (слева)
        sidebar = tk.Frame(self.root, width=250, bg="#f0f0f0", padx=10, pady=10)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Button(sidebar, text="Открыть изображение", command=self._load_file).pack(fill=tk.X, pady=5)

        tk.Label(sidebar, text="Метод бинаризации:", bg="#f0f0f0").pack(anchor=tk.W, pady=(10, 0))
        self.method_var = tk.StringVar(value="Гаврилов")
        methods = ["Гаврилов", "Отсу", "Ниблек", "Саувола", "Вульф", "Брэдли-Рот"]
        self.method_cb = ttk.Combobox(sidebar, textvariable=self.method_var, values=methods, state="readonly")
        self.method_cb.pack(fill=tk.X, pady=5)

        # Параметры (размер окна и чувствительность)
        tk.Label(sidebar, text="Размер окна (a):", bg="#f0f0f0").pack(anchor=tk.W)
        self.window_size = tk.Scale(sidebar, from_=3, to=101, orient=tk.HORIZONTAL)
        self.window_size.set(15)
        self.window_size.pack(fill=tk.X)

        tk.Label(sidebar, text="Чувствительность (k):", bg="#f0f0f0").pack(anchor=tk.W)
        self.k_param = tk.DoubleVar(value=0.2)
        tk.Entry(sidebar, textvariable=self.k_param).pack(fill=tk.X)

        tk.Button(sidebar, text="Применить", bg="#4caf50", fg="white", command=self._process).pack(fill=tk.X, pady=20)
        tk.Button(sidebar, text="Сохранить результат", command=self._save_file).pack(fill=tk.X)

        # Область просмотра (справа)
        self.canvas = tk.Canvas(self.root, bg="gray")
        self.canvas.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    def _load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.bmp *.jpeg")])
        if path:
            img = Image.open(path).convert('RGB')
            data = np.array(img)
            # Перевод в градации серого по формуле из методички [cite: 38]
            self.original_gray = (0.2125 * data[:, :, 0] + 0.7154 * data[:, :, 1] + 0.0721 * data[:, :, 2]).astype(
                np.uint8)

            # Оптимизация: расчет интегральных матриц сразу при загрузке [cite: 98, 107]
            I = self.original_gray.astype(np.float64)
            self.S = I.cumsum(axis=0).cumsum(axis=1)
            self.S2 = (I ** 2).cumsum(axis=0).cumsum(axis=1)

            self._display(self.original_gray)

    def _get_area_sum(self, mat, x1, y1, x2, y2):
        res = mat[y2, x2]
        if x1 > 0: res -= mat[y2, x1 - 1]
        if y1 > 0: res -= mat[y1 - 1, x2]
        if x1 > 0 and y1 > 0: res += mat[y1 - 1, x1 - 1]
        return res

    def _get_local_stats(self, a):
        h, w = self.original_gray.shape
        r = a // 2
        M = np.zeros_like(self.original_gray, dtype=np.float64)
        Sigma = np.zeros_like(self.original_gray, dtype=np.float64)

        for y in range(h):
            for x in range(w):
                y1, y2, x1, x2 = max(0, y - r), min(h - 1, y + r), max(0, x - r), min(w - 1, x + r)
                count = (y2 - y1 + 1) * (x2 - x1 + 1)
                s = self._get_area_sum(self.S, x1, y1, x2, y2)
                s2 = self._get_area_sum(self.S2, x1, y1, x2, y2)
                m = s / count
                disp = max(0, (s2 / count) - (m ** 2))
                M[y, x] = m
                Sigma[y, x] = np.sqrt(disp)
        return M, Sigma

    def _process(self):
        if self.original_gray is None: return

        method = self.method_var.get()
        a = self.window_size.get()
        k = self.k_param.get()
        I = self.original_gray

        if method == "Гаврилов":
            t = np.mean(I)  # [cite: 47, 50]
            res = np.where(I <= t, 0, 255)

        elif method == "Отсу":
            hist, _ = np.histogram(I, bins=256, range=(0, 256))
            p = hist / I.size  # [cite: 55]
            mu_t = np.sum(np.arange(256) * p)
            max_sigma, threshold, w1, mu1_sum = -1, 0, 0, 0
            for t in range(256):
                w1 += p[t]
                if w1 == 0 or w1 == 1: continue
                mu1_sum += t * p[t]
                mu1 = mu1_sum / w1
                mu2 = (mu_t - mu1_sum) / (1 - w1)
                sigma = w1 * (1 - w1) * (mu1 - mu2) ** 2  # [cite: 59]
                if sigma > max_sigma:
                    max_sigma, threshold = sigma, t
            res = np.where(I <= threshold, 0, 255)

        elif method in ["Ниблек", "Саувола", "Вульф"]:
            M, Sigma = self._get_local_stats(a)
            if method == "Ниблек":
                t = M + k * Sigma  # [cite: 79]
            elif method == "Саувола":
                t = M * (1 + k * (Sigma / 128 - 1))  # [cite: 84]
            else:  # Вульф
                m_min, R_max = np.min(I), np.max(Sigma)
                t = (1 - k) * M + k * m_min + k * (Sigma / R_max) * (M - m_min)  # [cite: 88]
            res = np.where(I <= t, 0, 255)

        elif method == "Брэдли-Рот":
            h, w = I.shape
            r, res = a // 2, np.zeros_like(I)
            for y in range(h):
                for x in range(w):
                    y1, y2, x1, x2 = max(0, y - r), min(h - 1, y + r), max(0, x - r), min(w - 1, x + r)
                    count = (y2 - y1 + 1) * (x2 - x1 + 1)
                    s = self._get_area_sum(self.S, x1, y1, x2, y2)
                    # Формула из методички [cite: 113]
                    res[y, x] = 0 if I[y, x] * count < s * (1 - k) else 255

        self.result_image = res.astype(np.uint8)
        self._display(self.result_image)

    def _display(self, img_array):
        img = Image.fromarray(img_array)
        # Масштабирование для предпросмотра
        img.thumbnail((700, 600))
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(350, 300, image=self.tk_img)

    def _save_file(self):
        if self.result_image is not None:
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path:
                Image.fromarray(self.result_image).save(path)


if __name__ == "__main__":
    root = tk.Tk()
    app = BinarizationApp(root)
    root.mainloop()