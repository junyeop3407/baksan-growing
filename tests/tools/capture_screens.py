# 확인용 화면 캡처: 무작위를 고정한 게임을 각 화면으로 옮기며 창만 캡처해 _captures/에 저장한다.
# _captures/는 제출하지 않는다(.gitignore). Windows 전용(PowerShell로 화면 캡처).
# 실행 (앱 폴더에서): python tests/tools/capture_screens.py
import os
import subprocess
import sys
import tempfile
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(APP_DIR, "src"))
sys.path.insert(0, os.path.join(APP_DIR, "tests"))

import db  # noqa: E402
import ui  # noqa: E402
from helpers import PatternRng, play_round, pump, start, wait_until  # noqa: E402

OUT = os.path.join(APP_DIR, "_captures")
ONE_LINE = ["보통탄", "보통탄", "보통탄", "연습탄", "예광탄", "철갑탄", "예광탄", "연습탄", "보통탄"]
BIG = "1000x700"


def shot(app, name):
    """창 안쪽을 그대로 캡처해 _captures/<name>.png로 저장한다."""
    root = app.root
    root.lift()
    pump(app, 400)
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    path = os.path.join(OUT, name + ".png")
    script = ("Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {w}, {h}; "
              "$g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen({x}, {y}, 0, 0, $b.Size); "
              "$b.Save('{p}', [System.Drawing.Imaging.ImageFormat]::Png)").format(w=w, h=h, x=x, y=y, p=path)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print("저장:", path)


def new_app(path, pattern, size=BIG):
    """맨 앞에 뜨는 창으로 게임을 하나 만든다."""
    root = tk.Tk()
    root.geometry(size + "+20+20")
    root.attributes("-topmost", True)
    return ui.App(root, path, rng=PatternRng(pattern), time_scale=0.05)


def main():
    """01~10 화면을 차례로 캡처한다."""
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "game.db")
        app = new_app(path, ONE_LINE)
        app.name_entry.insert(0, "박산")
        shot(app, "01_start")

        start(app)
        for _ in range(2):
            wait_until(app, lambda: not app.busy)
            app.spin_button.invoke()
        wait_until(app, lambda: not app.busy)
        shot(app, "02_game")

        app.rng.pattern = PatternRng.STRONG
        play_round_until_dance(app)
        shot(app, "03_dance")
        wait_until(app, lambda: app.screen == "shop", timeout=10)
        shot(app, "04_shop")

        app.time_scale = 1.0
        app.shop_buttons[0].invoke()
        shot(app, "05_next_round")

        app.time_scale = 0.05
        app.rng.pattern = PatternRng.WEAK
        play_round(app)
        shot(app, "06_gameover")

        for i, (name, score, rnd, rank) in enumerate([("최산닮고싶다", 1820, 6, "하사"), ("가나다라마바사아자차", 1210, 5, "하사"),
                                                     ("Player07", 640, 4, "병장"), ("박산", 640, 4, "병장"),
                                                     ("탄피줍기", 230, 2, "일병")]):
            db.save_record(path, name, rnd, score, rank, played_at="2026-11-1" + str(i) + " 14:0" + str(i) + ":00")
        app.menu_button.invoke()
        app.ranking_button.invoke()
        shot(app, "07_ranking")
        app.root.destroy()

        empty = new_app(os.path.join(tmp, "empty.db"), PatternRng.WEAK)
        empty.ranking_button.invoke()
        shot(empty, "08_ranking_empty")
        empty.root.destroy()

        small = new_app(os.path.join(tmp, "small.db"), ONE_LINE, size=str(ui.MIN_W) + "x" + str(ui.MIN_H))
        start(small)
        small.spin_button.invoke()
        wait_until(small, lambda: not small.busy)
        shot(small, "09_min_window")

        small.game.passed_rounds = 4
        small.game.round_no = 5
        small.show_game()
        shot(small, "10_rank_hasa")
        small.root.destroy()


def play_round_until_dance(app):
    """라운드를 다 돌리고, 춤이 시작되면 실제 속도로 바꿔 첫 튕김 자세에서 멈춘다."""
    for _ in range(app.game.spins_left):
        wait_until(app, lambda: not app.busy)
        app.spin_button.invoke()
    wait_until(app, lambda: app.game.spins_left == 0)
    app.time_scale = 1.0
    wait_until(app, lambda: app.dancing, timeout=10)
    pump(app, 420)


if __name__ == "__main__":
    main()
