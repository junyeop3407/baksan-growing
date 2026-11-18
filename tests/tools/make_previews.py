# 확인용 캡처 만들기: 계급 5단계 캐릭터를 나란히 그린 창을 띄우고 그 창만 캡처해
# images/faces_preview.png (컬러)와 images/faces_preview_gray.png (흑백)로 저장한다.
# Windows 전용(PowerShell로 화면 캡처). 실행 (앱 폴더에서): python tests/tools/make_previews.py
import os
import subprocess
import sys
import tkinter as tk

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(APP, "src"))

import character  # noqa: E402
from symbols import RANKS  # noqa: E402

IMAGES = os.path.abspath(os.path.join(APP, "images"))
LABEL_H = 40

CAPTURE = r"""
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap {w}, {h}
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen({x}, {y}, 0, 0, $bmp.Size)
$bmp.Save('{color}', [System.Drawing.Imaging.ImageFormat]::Png)
$gray = New-Object System.Drawing.Bitmap {w}, {h}
$g2 = [System.Drawing.Graphics]::FromImage($gray)
$m = New-Object System.Drawing.Imaging.ColorMatrix(,[single[][]](
  [single[]](0.299, 0.299, 0.299, 0, 0), [single[]](0.587, 0.587, 0.587, 0, 0),
  [single[]](0.114, 0.114, 0.114, 0, 0), [single[]](0, 0, 0, 1, 0), [single[]](0, 0, 0, 0, 1)))
$a = New-Object System.Drawing.Imaging.ImageAttributes
$a.SetColorMatrix($m)
$g2.DrawImage($bmp, (New-Object System.Drawing.Rectangle 0, 0, {w}, {h}), 0, 0, {w}, {h}, [System.Drawing.GraphicsUnit]::Pixel, $a)
$gray.Save('{gray}', [System.Drawing.Imaging.ImageFormat]::Png)
"""


def main():
    """캐릭터 5명을 그린 창을 맨 앞에 띄우고 캡처한 뒤 창을 닫는다."""
    root = tk.Tk()
    root.title("박산 키우기 - 계급별 얼굴")
    root.attributes("-topmost", True)
    width = character.WIDTH * len(RANKS)
    canvas = tk.Canvas(root, width=width, height=character.HEIGHT + LABEL_H, bg="#e9ecef", highlightthickness=0)
    canvas.pack()
    for i, (rank, ratio) in enumerate(RANKS):
        x = i * character.WIDTH
        character.draw_character(canvas, x, 0, ratio, rank, tag="c" + str(i))
        canvas.create_text(x + character.WIDTH / 2, character.HEIGHT + LABEL_H / 2,
                           text=rank + "  " + str(int(ratio * 100)) + "%",
                           font=("Malgun Gothic", -18, "bold"), fill="#1a1a1a")
    root.geometry("+20+20")

    def capture():
        try:
            root.lift()
            root.update()
            save(canvas)
        finally:
            root.destroy()

    def save(canvas):
        script = CAPTURE.format(x=canvas.winfo_rootx(), y=canvas.winfo_rooty(),
                                w=canvas.winfo_width(), h=canvas.winfo_height(),
                                color=os.path.join(IMAGES, "faces_preview.png"),
                                gray=os.path.join(IMAGES, "faces_preview_gray.png"))
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)

    root.after(1500, capture)
    root.mainloop()
    print("저장:", os.path.join(IMAGES, "faces_preview.png"), "/", os.path.join(IMAGES, "faces_preview_gray.png"))


if __name__ == "__main__":
    main()
