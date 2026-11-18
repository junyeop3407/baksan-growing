# 4차 화면 다듬기 (2026-11-19 사장 지시): 보스 드래곤 크기·BOSS 표시, 눈썹과 눈 사이 띄우기, 쓰지 않는 자세 값 삭제.
import character
import pixel_art as pa
import ui
from helpers import PatternRng, start


def battle_with_boss(tk_root, tmp_path):
    """5웨이브 전투에서 보스 드래곤과 일반 적(고블린)이 하나씩 전장에 있는 화면."""
    app = ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.WEAK), time_scale=1.0)
    start(app)
    g = app.game
    g.wave = 5
    g.start_battle()
    g.queue = [q for q in g.queue if q[1]][:1] + [q for q in g.queue if not q[1]][:1]
    g.battle_step(0.01)                 # 보스가 나오고
    g.battle_step(0.31)                 # 0.30초 뒤 일반 적이 나온다
    app.draw_enemies()
    return app


def test_t1_dragon_about_twice_normal_enemy(tk_root, tmp_path):
    """보스 드래곤 그림은 일반 적(고블린)보다 약 2배 크다 (높이 1.8배 이상)."""
    app = battle_with_boss(tk_root, tmp_path)
    dragon = app.enemy_img("dragon", 0)
    goblin = app.enemy_img("goblin", 0)
    assert dragon.height() >= 1.8 * goblin.height()
    app.cancel_all()


def test_t2_boss_bar_big_and_boss_label_follows(tk_root, tmp_path):
    """보스 체력 막대는 일반 적의 2배 이상 넓고 두껍고, 머리 위 "BOSS" 글자가 드래곤과 함께 움직인다."""
    app = battle_with_boss(tk_root, tmp_path)
    c = app.canvas
    boss = next(e for e in app.game.enemies if e["boss"])
    normal = next(e for e in app.game.enemies if not e["boss"])
    b_back = app.enemy_items[id(boss)][2]
    n_back = app.enemy_items[id(normal)][2]
    bx0, by0, bx1, by1 = c.coords(b_back)
    nx0, ny0, nx1, ny1 = c.coords(n_back)
    assert bx1 - bx0 >= 2 * (nx1 - nx0)
    assert by1 - by0 > ny1 - ny0
    labels = c.find_withtag("boss_label")
    assert [c.itemcget(i, "text") for i in labels if c.type(i) == "text"][-1] == "BOSS"
    label_y = c.bbox(labels[-1])[3]
    assert label_y <= by0                                   # 막대 위
    x_before = c.coords(labels[-1])[0]
    boss["x"] -= 30
    app.draw_enemies()
    assert c.coords(labels[-1])[0] < x_before
    assert c.find_withtag("boss_label") == labels           # 새로 만들지 않고 옮긴다
    app.cancel_all()


def test_t3_brows_do_not_touch_eyes():
    """두 얼굴 모두 눈썹 바로 아래 칸에는 눈(E·Y·P)이 없고, 최산 눈썹은 한 줄 두께다."""
    for face in (pa.SEONGJAE, pa.CHOISAN):
        eyes = face["layers"]["eyes"]
        brows = {(x, y) for y, r in enumerate(eyes) for x, ch in enumerate(r) if ch == "B"}
        eye_cells = {(x, y) for y, r in enumerate(eyes) for x, ch in enumerate(r) if ch in "EYP"}
        for x, y in brows:
            assert all((nx, y + 1) not in eye_cells for nx in (x - 1, x, x + 1)), (x, y)
    choisan_brow_rows = {y for y, r in enumerate(pa.CHOISAN["layers"]["eyes"]) if "B" in r}
    assert len(choisan_brow_rows) == 1


def test_t4_no_unused_pose_value():
    """도트 그림에서 쓰지 않는 자세 값(squint)은 없다."""
    assert "squint" not in character.DEFAULT_POSE
    assert all("squint" not in pose for _, pose in character.DANCE_STEPS)
