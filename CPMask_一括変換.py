import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def process_image(image_path, password):
    img = cv2.imread(image_path)
    if img is None:
        return None, "読み込み失敗"

    h, w, _ = img.shape
    x_blocks, y_blocks = w // 8, h // 8
    target_w, target_h = x_blocks * 8, y_blocks * 8
    masu = x_blocks * y_blocks

    if masu == 0:
        return None, "サイズ不足"

    password = password.upper()
    pass_len = len(password)
    
    # 1. 配列作成
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

    # 2. ブロック・スクランブル処理
    res_img = img.copy()
    working_area = img[0:target_h, 0:target_w].copy()
    processed_area = np.zeros_like(working_area)
    
    c = 0
    for y_b in range(y_blocks):
        for x_b in range(x_blocks):
            src_idx = cpm[c]
            x_src, y_src = (src_idx % x_blocks) * 8, (src_idx // x_blocks) * 8
            block = working_area[y_src:y_src+8, x_src:x_src+8]
            
            if (src_idx ^ c) % 2 == 1:
                block = block.transpose(1, 0, 2)
            
            processed_area[y_b*8:y_b*8+8, x_b*8:x_b*8+8] = block
            c += 1

    # 3. 色変換処理 (ネガポジ反転 + RGスワップ)
    processed_area = 255 - processed_area
    green_ch = processed_area[:, :, 1].copy()
    processed_area[:, :, 1] = processed_area[:, :, 2]
    processed_area[:, :, 2] = green_ch

    res_img[0:target_h, 0:target_w] = processed_area
    return res_img, None

class CPMaskBatchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CP-MASK フォルダ一括処理ツール")
        self.root.geometry("500x300")

        # パスワード入力
        tk.Label(root, text="パスワード (半角英大文字 1-16文字):").pack(pady=5)
        self.pass_entry = tk.Entry(root, width=30, justify='center')
        self.pass_entry.insert(0, "SAMPLE")
        self.pass_entry.pack(pady=5)

        # フォルダパス表示
        self.dir_path = tk.StringVar(value="処理するフォルダを選択してください")
        tk.Label(root, textvariable=self.dir_path, fg="blue", wraplength=450).pack(pady=10)
        
        btn_select = tk.Button(root, text="フォルダを選択", command=self.select_dir)
        btn_select.pack(pady=5)

        # 進捗バー
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=15)

        # 実行ボタン
        self.btn_run = tk.Button(root, text="一括処理開始", bg="lightgreen", width=20, command=self.run_batch)
        self.btn_run.pack(pady=10)

    def select_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_path.set(directory)

    def run_batch(self):
        input_dir = self.dir_path.get()
        password = self.pass_entry.get().strip()

        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "有効なフォルダを選択してください。")
            return
        if not password:
            messagebox.showerror("Error", "パスワードを入力してください。")
            return

        # 出力フォルダの作成
        output_dir = os.path.join(input_dir, "output_cp")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 画像ファイルのリストアップ
        extensions = (".png", ".bmp", ".jpg", ".jpeg", ".webp")
        files = [f for f in os.listdir(input_dir) if f.lower().endswith(extensions)]
        
        if not files:
            messagebox.showinfo("Info", "対象となる画像ファイルが見つかりませんでした。")
            return

        self.btn_run.config(state="disabled")
        self.progress["maximum"] = len(files)
        
        success_count = 0
        for i, filename in enumerate(files):
            input_path = os.path.join(input_dir, filename)
            # 出力はすべてPNGまたはBMPを推奨（可逆のため。ここでは元の拡張子を維持）
            output_path = os.path.join(output_dir, filename)
            
            result, error = process_image(input_path, password)
            if result is not None:
                cv2.imwrite(output_path, result)
                success_count += 1
            
            self.progress["value"] = i + 1
            self.root.update_idletasks()

        self.btn_run.config(state="normal")
        messagebox.showinfo("完了", f"一括処理が完了しました！\n\n成功: {success_count} 件\n保存先: {output_dir}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CPMaskBatchGUI(root)
    root.mainloop()