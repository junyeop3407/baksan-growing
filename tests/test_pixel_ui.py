# 픽셀 아트 화면 테스트 (2026-11-19 사장 지시 3차 2단계, QA팀이 더함).
# 그림 픽셀은 비교하지 않고, 도트 이미지가 쓰이는지·참조가 남는지·잘리지 않는지·움직임이 프레임으로 바뀌는지 본다.
import gc

import character
import game
import pixel_art as pa
import ui
from helpers import PatternRng, pump, start, wait_until



def make(tk_root, tmp_path, pattern=PatternRng.STRONG, time_scale=1.0):
    return ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(pattern), time_scale=time_scale)


def images_on(canvas):
    return [canvas.itemcget(i, "image") for i in canvas.find_all() if canvas.type(i) == "image"]


def test_p1_screens_use_pixel_images(tk_root, tmp_path):
    """게임 화면의 배경·정보판·슬롯판·바리케이드·하트·지휘관·지휘대가 도트 이미지다."""
    app = make(tk_root, tmp_path)
    start(app)
    c = app.canvas
    for tag in ("scene", "panel", "barricade", "hearts", "hero", "podium", "slot_box"):
        items = c.find_withtag(tag)
        assert items and all(c.type(i) == "image" for i in items), tag
    assert not [i for i in c.find_all() if c.type(i) in ("polygon", "oval", "arc")]


def test_p2_image_references_survive_gc(tk_root, tmp_path):
    """그린 뒤 가비지 컬렉션을 해도 캔버스의 모든 이미지가 살아 있다 (캐시가 참조를 붙잡음)."""
    app = make(tk_root, tmp_path)
    start(app)
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)
    gc.collect()
    alive = set(tk_root.tk.call("image", "names"))
    names = images_on(app.canvas)
    assert names and all(name in alive for name in names)
    for b in (app.spin_button, app.battle_button):
        assert b["image"] in alive


def inside(app):
    c = app.canvas
    for i in c.find_all():
        if c.itemcget(i, "state") == "hidden":
            continue
        x0, y0, x1, y1 = c.bbox(i)
        assert x0 >= -1 and y0 >= -1 and x1 <= ui.CANVAS_W + 1 and y1 <= ui.CANVAS_H + 1, (c.gettags(i), c.bbox(i))


def test_p3_min_window_nothing_cut(tk_root, tmp_path):
    """가장 작은 창(1000×620)에서 게임·전투·게임 오버 화면이 창 안에 다 들어가고 그림이 캔버스 밖으로 안 나간다."""
    tk_root.deiconify()
    app = make(tk_root, tmp_path, PatternRng.WEAK, time_scale=1.0)
    tk_root.geometry(str(ui.MIN_W) + "x" + str(ui.MIN_H))
    start(app)
    pump(app, 50)
    assert app.canvas.winfo_width() >= ui.CANVAS_W and app.canvas.winfo_height() >= ui.CANVAS_H
    assert app.frame.winfo_reqheight() <= ui.MIN_H
    inside(app)
    app.battle_button.invoke()
    pump(app, 30)
    inside(app)
    app.game.hearts = 0
    wait_until(app, lambda: app.screen == "gameover", timeout=10)
    pump(app, 50)
    assert app.frame.winfo_reqheight() <= ui.MIN_H
    inside(app)


def test_p4_start_shop_ranking_fit_min_window(tk_root, tmp_path):
    """시작·상점·랭킹 화면도 가장 작은 창 높이 안에 들어간다."""
    app = make(tk_root, tmp_path)
    assert app.frame.winfo_reqheight() <= ui.MIN_H
    start(app)
    app.show_shop()
    assert app.frame.winfo_reqheight() <= ui.MIN_H
    app.show_ranking()
    assert app.frame.winfo_reqheight() <= ui.MIN_H


def test_p5_enemy_moves_without_redrawing(tk_root, tmp_path):
    """전투 중 적은 같은 캔버스 항목을 coords로 옮기고, 걷기 그림(프레임)만 바꾼다."""
    app = make(tk_root, tmp_path, PatternRng.WEAK)
    start(app)
    app.game.soldiers = [("연습탄", 1)]
    app.battle_button.invoke()
    wait_until(app, lambda: app.canvas.find_withtag("slime"), timeout=5)
    item = app.canvas.find_withtag("slime")[0]
    x_before = app.canvas.coords(item)[0]
    frames = set()
    for _ in range(20):
        pump(app, 40)
        if item in app.canvas.find_withtag("slime"):
            frames.add(app.canvas.itemcget(item, "image"))
    assert item in app.canvas.find_withtag("slime")
    assert app.canvas.coords(item)[0] < x_before
    assert len(frames) == 2


def test_p6_enemy_kind_and_dragon_by_wave(tk_root, tmp_path):
    """3웨이브 고블린, 6웨이브 해골 병사, 5웨이브 보스는 드래곤."""
    app = make(tk_root, tmp_path, PatternRng.WEAK)
    start(app)
    for wave, tag in ((3, "goblin"), (6, "skeleton")):
        app.game.wave = wave
        app.game.start_battle()
        app.game.battle_step(0.01)
        app.draw_enemies()
        assert app.canvas.find_withtag(tag)
    app.game.wave = 5
    app.game.start_battle()
    app.game.queue = [q for q in app.game.queue if q[1]]
    app.game.battle_step(0.01)
    app.draw_enemies()
    assert app.canvas.find_withtag("dragon")


def test_p7_shots_are_flying_dot_bullets(tk_root, tmp_path):
    """사격선 대신 작은 도트 총알 이미지가 날아가고(위치가 바뀜), 병사는 사격 프레임으로 바뀐다."""
    app = make(tk_root, tmp_path)
    start(app)
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)
    app.battle_button.invoke()
    wait_until(app, lambda: app.canvas.find_withtag("shot"), timeout=5)
    c = app.canvas
    assert all(c.type(i) == "image" for i in c.find_withtag("shot"))
    assert not [i for i in c.find_all() if c.type(i) == "line"]
    shot = c.find_withtag("shot")[0]
    places, soldier_frames = set(), set()
    for _ in range(12):
        pump(app, 35)
        if shot in c.find_withtag("shot"):
            places.add(tuple(c.coords(shot)))
        soldier_frames.update(c.itemcget(i, "image") for i in c.find_withtag("soldier_sprite"))
    assert len(places) >= 2
    assert len(soldier_frames) >= 2


def test_p8_merge_sparkle(tk_root, tmp_path):
    """합체하면 그 칸에 반짝임 도트가 잠깐 보인다."""
    app = make(tk_root, tmp_path)
    start(app)
    app.spin_button.invoke()                      # 철갑탄 8줄 → 합체 연쇄
    wait_until(app, lambda: not app.busy)
    assert app.canvas.find_withtag("sparkle")
    assert all(app.canvas.type(i) == "image" for i in app.canvas.find_withtag("sparkle"))


def test_p9_dance_swaps_pixel_frames(tk_root):
    """춤의 자세마다 팔·몸통 도트 그림이 바뀌어 3장 이상의 서로 다른 프레임이 된다."""
    import tkinter as tk
    c = tk.Canvas(tk_root, width=300, height=400)
    frames = set()
    for _, pose in character.DANCE_STEPS:
        c.delete("all")
        character.draw_character(c, 0, 0, 0.5, "상병", pose=pose, scale=1.0, tag="x")
        frames.add(tuple(c.itemcget(i, "image") for tag in ("arm_l", "arm_r", "body")
                         for i in c.find_withtag("x&&" + tag)))
    assert len(frames) >= 3


def test_p10_hero_stands_on_podium(tk_root):
    """지휘대는 몸통 바로 아래에 붙어 있어 떠 보이지 않는다."""
    import tkinter as tk
    c = tk.Canvas(tk_root, width=300, height=400)
    character.draw_character(c, 0, 0, 0.0, "이병", tag="x")
    body = c.bbox("x&&body")
    podium = c.bbox("x&&podium")
    assert abs(podium[1] - body[3]) <= 2
    assert podium[0] <= body[0] and podium[2] >= body[2]


def test_p11_hearts_and_buttons_are_pixel(tk_root, tmp_path):
    """하트는 도트 이미지 3개, [스핀]·[전투 시작]은 나무 판자 그림 버튼이다."""
    app = make(tk_root, tmp_path)
    start(app)
    hearts = app.canvas.find_withtag("hearts")
    assert len(hearts) == 3 and all(app.canvas.type(i) == "image" for i in hearts)
    assert app.spin_button["image"] and app.battle_button["image"]
    assert game.MAX_HEARTS == 5
    pa.clear_cache()
