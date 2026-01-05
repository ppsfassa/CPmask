import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

class CPMaskViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("CPMask Image Viewer")
        self.root.geometry("1000x800")

        # 状態保持用
        self.image_list = []
        self.current_idx = 0
        self.password = tk.StringVar(value="SAMPLE")
        self.folder_path = ""

        # UIの構築
        self._setup_ui()

        # キーバインド（左右キーで移動）
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())

    def _setup_ui(self):
        # 上部コントロールパネル
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Button(ctrl_frame, text="フォルダを開く", command=self.open_folder).pack(side=tk.LEFT, padx=5)
        tk.Label(ctrl_frame, text="パスワード:").pack(side=tk.LEFT, padx=5)
        tk.Entry(ctrl_frame, textvariable=self.password, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="適用/更新", command=self.load_image).pack(side=tk.LEFT, padx=5)
        
        self.info_label = tk.Label(ctrl_frame, text="画像を選択してください")
        self.info_label.pack(side=tk.RIGHT, padx=5)

        # 画像表示エリア
        self.canvas = tk.Canvas(self.root, bg="gray20")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def open_folder(self):
        self.folder_path = filedialog.askdirectory()
        if not self.folder_path:
            return
        
        # フォルダ内の画像リスト取得
        exts = (".png", ".jpg", ".jpeg", ".bmp",".webp")
        self.image_list = [f for f in os.listdir(self.folder_path) if f.lower().endswith(exts)]
        self.image_list.sort()
        
        if self.image_list:
            self.current_idx = 0
            self.load_image()
        else:
            messagebox.showwarning("警告", "画像が見つかりません。")

    def process_image(self, img, password):
        """ ご提示のロジックを画像に適用（復元処理） """
        h, w, _ = img.shape
        x_blocks, y_blocks = w // 8, h // 8
        target_w, target_h = x_blocks * 8, y_blocks * 8
        masu = x_blocks * y_blocks

        password = password.upper() 
        pass_len = len(password) if len(password) > 0 else 1
        
        # --- 1. 配列作成 ---
        cpc = "PWSUIHJTFEVBMCADYLONRGKXQZ"
        cpa = np.zeros(masu, dtype=int)
        cpm = np.zeros(masu, dtype=int)
        
        a, b = -1, 1
        for cnt in range(masu):
            char_idx = ord(password[cnt % pass_len]) - ord('A')
            c_val = ord(cpc[char_idx % 26]) - ord('A') + 1
            c_val = c_val + pass_len + (masu % pass_len) + cnt
            a = (a + c_val) % masu
            while cpa[a] != 0:
                a = (a + masu + b) % masu
            cpa[a] = cnt + 1
            b *= -1
            
        for cnt in range((masu // 2) + (masu % 2)):
            idx_a, idx_b = cpa[cnt] - 1, cpa[masu - 1 - cnt] - 1
            cpm[idx_a], cpm[idx_b] = idx_b, idx_a

        # --- 2. ブロック・スクランブル処理 ---
        working_area = img[0:target_h, 0:target_w].copy()
        processed_area = np.zeros_like(working_area)
        
        c = 0
        for y_b in range(y_blocks):
            for x_b in range(x_blocks):
                src_idx = cpm[c]
                x_src, y_src = (src_idx % x_blocks) * 8, (src_idx // x_blocks) * 8
                block = working_area[y_src:y_src+8, x_src:x_src+8]
                
                # 転置の復元（転置は2回行うと元に戻る）
                if (src_idx ^ c) % 2 == 1:
                    block = block.transpose(1, 0, 2)
                
                processed_area[y_b*8:y_b*8+8, x_b*8:x_b*8+8] = block
                c += 1

        # --- 3. 色変換処理の復元 ---
        # A. ネガポジ反転（255-x は2回で元に戻る）
        processed_area = 255 - processed_area
        
        # B. Red と Green の入れ替え（入れ替えは2回で元に戻る）
        green_ch = processed_area[:, :, 1].copy()
        processed_area[:, :, 1] = processed_area[:, :, 2]
        processed_area[:, :, 2] = green_ch

        # 結果を反映
        res_img = img.copy()
        res_img[0:target_h, 0:target_w] = processed_area
        return res_img

    def load_image(self):
        if not self.image_list:
            return

        img_path = os.path.join(self.folder_path, self.image_list[self.current_idx])
        img = cv2.imread(img_path)
        if img is None:
            return

        # パスワード処理適用
        processed_img = self.process_image(img, self.password.get())

        # 表示用に変換 (OpenCV BGR -> RGB -> PIL)
        rgb_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        
        # ウィンドウサイズに合わせてリサイズ（アスペクト比維持）
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w > 10 and canvas_h > 10:
            pil_img.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w//2, canvas_h//2, image=self.tk_img)
        
        self.info_label.config(text=f"[{self.current_idx + 1}/{len(self.image_list)}] {self.image_list[self.current_idx]}")

    def next_image(self):
        if self.image_list:
            self.current_idx = (self.current_idx + 1) % len(self.image_list)
            self.load_image()

    def prev_image(self):
        if self.image_list:
            self.current_idx = (self.current_idx - 1) % len(self.image_list)
            self.load_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = CPMaskViewer(root)
    root.mainloop()