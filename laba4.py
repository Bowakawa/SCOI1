import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import numpy as np
from PIL import Image, ImageTk
import math
import time



def quickselect(arr, k):
    if len(arr) == 1: return arr[0]
    pivot = arr[len(arr) // 2]
    lows = [x for x in arr if x < pivot]
    highs = [x for x in arr if x > pivot]
    pivots = [x for x in arr if x == pivot]
    if k < len(lows):
        return quickselect(lows, k)
    elif k < len(lows) + len(pivots):
        return pivots[0]
    else:
        return quickselect(highs, k - len(lows) - len(pivots))


def get_gaussian_kernel(size, sigma):
    kernel = np.fromfunction(
        lambda x, y: (1 / (2 * math.pi * sigma ** 2)) * np.exp(
            -((x - (size - 1) / 2) ** 2 + (y - (size - 1) / 2) ** 2) / (2 * sigma ** 2)
        ), (size, size)
    )
    return kernel / np.sum(kernel)


def apply_filter(img_arr, kernel_or_size, mode='linear'):
    h, w, c = img_arr.shape
    if mode == 'linear':
        kh, kw = kernel_or_size.shape
        pad_h, pad_w = kh // 2, kw // 2
        padded = np.pad(img_arr, ((pad_h, pad_h), (pad_w, pad_w), (0, 0)), mode='reflect')
        output = np.zeros_like(img_arr)
        for ch in range(c):
            for y in range(h):
                for x in range(w):
                    region = padded[y:y + kh, x:x + kw, ch]
                    output[y, x, ch] = np.sum(region * kernel_or_size)
    else:  # Median
        size = kernel_or_size
        pad = size // 2
        padded = np.pad(img_arr, ((pad, pad), (pad, pad), (0, 0)), mode='reflect')
        output = np.zeros_like(img_arr)
        k_idx = (size * size) // 2
        for ch in range(c):
            for y in range(h):
                for x in range(w):
                    region = padded[y:y + size, x:x + size, ch].flatten()
                    output[y, x, ch] = quickselect(region.tolist(), k_idx)
    return np.clip(output, 0, 255).astype(np.uint8)



class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная 4: Фильтрация изображений")
        self.img_original = None
        self.img_display = None

        controls = ttk.Frame(root, padding="10")
        controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(controls, text="Открыть фото", command=self.load_image).pack(side=tk.LEFT, padx=5)


        ttk.Label(controls, text="Sigma:").pack(side=tk.LEFT, padx=2)
        self.sigma_val = ttk.Entry(controls, width=5)
        self.sigma_val.insert(0, "3.0")
        self.sigma_val.pack(side=tk.LEFT, padx=5)

        ttk.Label(controls, text="Ядро (NxN):").pack(side=tk.LEFT, padx=2)
        self.kernel_size = ttk.Entry(controls, width=5)
        self.kernel_size.insert(0, "13")
        self.kernel_size.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Размытие Гаусса", command=self.run_gaussian).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Медианный фильтр", command=self.run_median).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Сохранить", command=self.save_image).pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(root, width=800, height=600, bg="gray")
        self.canvas.pack(expand=True, fill=tk.BOTH)

    def load_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.img_original = Image.open(path).convert("RGB")
            self.show_preview(self.img_original)

    def show_preview(self, img):
        display_img = img.copy()
        display_img.thumbnail((800, 600))
        self.img_display = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(400, 300, image=self.img_display)

    def run_gaussian(self):
        if not self.img_original: return
        try:
            s = float(self.sigma_val.get())
            k_size = int(self.kernel_size.get())
            if k_size % 2 == 0: raise ValueError("Размер должен быть нечетным")

            kernel = get_gaussian_kernel(k_size, s)
            start_time = time.time()
            # Оптимизированная работа через массив байтов
            arr = np.array(self.img_original)
            res_arr = apply_filter(arr, kernel, 'linear')
            self.img_original = Image.fromarray(res_arr)
            self.show_preview(self.img_original)
            print(f"Гаусс выполнен за {time.time() - start_time:.2f} сек")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def run_median(self):
        if not self.img_original: return
        try:
            k_size = int(self.kernel_size.get())
            if k_size % 2 == 0: raise ValueError("Размер должен быть нечетным")

            start_time = time.time()
            arr = np.array(self.img_original)
            res_arr = apply_filter(arr, k_size, 'median')
            self.img_original = Image.fromarray(res_arr)
            self.show_preview(self.img_original)
            print(f"Медиана выполнена за {time.time() - start_time:.2f} сек")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def save_image(self):
        if self.img_original:
            path = filedialog.asksaveasfilename(defaultextension=".jpg")
            if path: self.img_original.save(path)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()