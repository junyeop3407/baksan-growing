# 확인용 화면 캡처: 무작위를 고정한 게임을 각 화면으로 옮기며 창만 캡처해 _captures/에 저장한다.
# 함께 images/dance_preview.png(춤 핵심 자세 3개)와 images/ranking.png(실제로 4판 한 기록)도 만든다.
# _captures/는 제출하지 않는다(.gitignore). Windows 전용(PowerShell로 화면 캡처).
# 실행 (앱 폴더에서): python tests/tools/capture_screens.py
import os
import random
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(APP_DIR, "src"))
sys.path.insert(0, os.path.join(APP_DIR, "tests"))

import character  # noqa: E402
import db  # noqa: E402
import ui  # noqa: E402
from helpers import PatternRng, play_round, pump, start, wait_until  # noqa: E402

OUT = os.path.join(APP_DIR, "_captures")
IMAGES = os.path.join(APP_DIR, "images")
ONE_LINE = ["보통탄", "보통탄", "보통탄", "연습탄", "예광탄", "철갑탄", "예광탄", "연습탄", "보통탄"]
BIG = "1000x700"


def shot(app, name, folder=OUT):
    """창 안쪽을 그대로 캡처해 <folder>/<name>.png로 저장한다."""
    root = app.root
    root.lift()
    pump(app, 400)
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    path = os.path.join(folder, name + ".png")
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

        real_games(os.path.join(tmp, "real.db"))
    dance_preview()
    shutil.copy(os.path.join(OUT, "02_game.png"), os.path.join(IMAGES, "game.png"))
    print("복사: images/game.png ← _captures/02_game.png")


def real_games(path):
    """규칙 그대로(진짜 무작위) 4판을 끝까지 하고, 쌓인 랭킹을 images/ranking.png로 찍는다."""
    root = tk.Tk()
    root.geometry(BIG + "+20+20")
    root.attributes("-topmost", True)
    app = ui.App(root, path, rng=random.Random(2026), time_scale=0.02)
    for name in ["박산", "이병박산", "하사가될래", "탄피줍기"]:
        start(app, name)
        while True:
            play_round(app)
            if app.screen == "gameover":
                break
            app.shop_buttons[0].invoke()
        app.menu_button.invoke()
    app.ranking_button.invoke()
    shot(app, "ranking", folder=IMAGES)
    shutil.copy(os.path.join(IMAGES, "ranking.png"), os.path.join(OUT, "07_ranking_real.png"))
    root.destroy()


def dance_preview():
    """춤 핵심 자세 3개(준비/튕김/마지막)를 하사 얼굴로 나란히 그려 images/dance_preview.png로 찍는다."""
    root = tk.Tk()
    root.title("춤 핵심 자세")
    root.attributes("-topmost", True)
    root.geometry("+20+20")
    steps = character.DANCE_STEPS
    poses = [("준비", steps[0][1]), ("튕김", steps[1][1]), ("마지막", steps[-1][1])]
    canvas = tk.Canvas(root, width=character.WIDTH * 3, height=character.HEIGHT + 40, bg="#e9ecef",
                       highlightthickness=0)
    canvas.pack()
    for i, (label, pose) in enumerate(poses):
        x = i * character.WIDTH
        character.draw_character(canvas, x, 0, 1.0, "하사", pose=pose, tag="d" + str(i))
        canvas.create_text(x + character.WIDTH / 2, character.HEIGHT + 20, text=label,
                           font=(ui.FONT, -18, "bold"), fill="#1a1a1a")

    shot(SimpleNamespace(root=root), "dance_preview", folder=IMAGES)
    root.destroy()


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
