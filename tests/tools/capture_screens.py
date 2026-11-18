# 확인용 화면 캡처: 무작위를 고정한 게임을 각 화면으로 옮기며 창만 캡처해 _captures/에 12장 저장한다.
# 함께 images/game.png(전투 화면)와 images/ranking.png(실제 규칙으로 4판 한 기록)도 만든다.
# 키·마우스 입력은 보내지 않는다(위젯 메서드를 직접 부르고 화면만 복사한다, 키 입력 안전 규칙).
# _captures/는 제출하지 않는다(.gitignore). Windows 전용(PowerShell로 화면 캡처).
# 실행 (앱 폴더에서): python tests/tools/capture_screens.py
import os
import random
import shutil
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
IMAGES = os.path.join(APP_DIR, "images")
ONE_LINE = ["보통탄", "보통탄", "보통탄", "연습탄", "예광탄", "철갑탄", "예광탄", "연습탄", "보통탄"]  # 가로 1줄
BIG = str(ui.DEFAULT_W) + "x" + str(ui.DEFAULT_H)


def shot(app, name, folder=OUT, wait=400):
    """창 안쪽을 그대로 캡처해 <folder>/<name>.png로 저장한다."""
    root = app.root
    root.lift()
    pump(app, wait)
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    path = os.path.join(folder, name + ".png")
    script = ("Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {w}, {h}; "
              "$g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen({x}, {y}, 0, 0, $b.Size); "
              "$b.Save('{p}', [System.Drawing.Imaging.ImageFormat]::Png)").format(w=w, h=h, x=x, y=y, p=path)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print("저장:", path)


def new_app(path, pattern, size=BIG, time_scale=1.0):
    """맨 앞에 뜨는 창으로 게임을 하나 만든다."""
    root = tk.Tk()
    root.attributes("-topmost", True)
    app = ui.App(root, path, rng=PatternRng(pattern), time_scale=time_scale)
    root.geometry(size + "+20+20")
    return app


def freeze(app):
    """전투 예약을 멈춰 지금 장면을 그대로 둔다 (캡처용)."""
    app.cancel_all()
    app.tick_count = 0
    app.draw_enemies()
    app.draw_shots()


def spin_once(app):
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)


def main():
    """01~12 화면을 캡처한다."""
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "game.db")

        # 01 시작, 02 준비 단계(첫 스핀 → 소총병 소환), 04 합체(두 번째 스핀 → 소총병 ★2)
        app = new_app(path, ONE_LINE)
        app.name_entry.insert(0, "박산")
        shot(app, "01_start")
        start(app)
        spin_once(app)
        shot(app, "02_prepare")
        spin_once(app)
        shot(app, "04_merge")

        # 03 전투: 훈련병·소총병으로 1웨이브 → 적이 걸어오고 병사가 쏘는 장면에서 멈춤
        app.game.soldiers = [("연습탄", 1), ("보통탄", 1)]
        app.draw_soldiers()
        app.battle_button.invoke()
        pump(app, 5600)
        freeze(app)
        shot(app, "03_battle")

        # 05 웨이브를 막음(춤 + 말풍선), 06 상점, 07 다음 웨이브 준비("난 섹시해.... ㅋ")
        app.later(ui.TICK_MS, app.battle_tick)
        wait_until(app, lambda: app.dancing, timeout=60)
        pump(app, 600)
        shot(app, "05_wave_clear", wait=0)
        wait_until(app, lambda: app.screen == "shop", timeout=10)
        shot(app, "06_shop")
        app.shop_buttons[0].invoke()
        shot(app, "07_next_wave")

        # 09 게임 오버: 병사를 비우고 꽝만 나오게 해서 2웨이브 탈락
        app.time_scale = 0.05
        app.rng.pattern = PatternRng.WEAK
        app.rng.i = 0
        app.game.soldiers = []
        play_round(app)
        shot(app, "09_gameover")

        # 10 랭킹
        for i, (name, score, wave, rank) in enumerate([("최산닮고싶다", 1820, 9, "하사"), ("가나다라마바사아자차", 1210, 7, "하사"),
                                                      ("Player07", 640, 4, "병장"), ("탄피줍기", 230, 2, "일병")]):
            db.save_record(path, name, wave, score, rank, played_at="2026-11-1" + str(i) + " 14:0" + str(i) + ":00")
        app.menu_button.invoke()
        app.ranking_button.invoke()
        shot(app, "10_ranking")
        app.root.destroy()

        # 08 보스: 5웨이브(하사) 전투에서 전차가 나온 순간 멈춤
        boss = new_app(os.path.join(tmp, "boss.db"), ONE_LINE)
        start(boss)
        boss.game.wave, boss.game.cleared = 5, 4
        boss.game.soldiers = [("철갑탄", 2), ("예광탄", 2), ("보통탄", 2), ("연습탄", 1)]
        boss.game.hearts = 5
        boss.show_game()
        boss.battle_button.invoke()
        wait_until(boss, lambda: any(e["boss"] and e["x"] < 90 for e in boss.game.enemies), timeout=40)
        freeze(boss)
        shot(boss, "08_boss")
        boss.root.destroy()

        # 11 가장 작은 창, 12 하사 계급 화면
        small = new_app(os.path.join(tmp, "small.db"), ONE_LINE, size=str(ui.MIN_W) + "x" + str(ui.MIN_H))
        start(small)
        spin_once(small)
        shot(small, "11_min_window")
        small.game.cleared, small.game.wave = 4, 5
        small.show_game()
        shot(small, "12_rank_hasa")
        small.root.destroy()

        real_games(os.path.join(tmp, "real.db"))
    shutil.copy(os.path.join(OUT, "03_battle.png"), os.path.join(IMAGES, "game.png"))
    print("복사: images/game.png ← _captures/03_battle.png")


def real_games(path):
    """규칙 그대로(진짜 무작위) 4판을 끝까지 하고, 쌓인 랭킹을 images/ranking.png로 찍는다."""
    root = tk.Tk()
    root.attributes("-topmost", True)
    app = ui.App(root, path, rng=random.Random(2026), time_scale=0.02)
    root.geometry(BIG + "+20+20")
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
    root.destroy()


if __name__ == "__main__":
    main()
