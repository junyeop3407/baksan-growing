# 리뷰에서 나온 지적을 확인하는 회귀 테스트 (승인 목록과 별도).
import os
import random
import sqlite3
import sys

import pytest

import character
import db
import game
import pixel_art
import symbols
import ui
from helpers import PatternRng, pump, start, wait_until

SCHEMA_SQL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql")


# ---- 1단계 게임 로직 리뷰 ----

@pytest.mark.parametrize("kind", symbols.BULLET_ORDER)
def test_label_does_not_overlap_bullet_at_smallest_cell(tk_root, kind):
    """가장 작은 칸(80px)에서 이름 글자와 총알 그림이 겹치지 않는다."""
    import tkinter as tk
    c = tk.Canvas(tk_root, width=200, height=200)
    c.pack()
    symbols.draw_bullet(c, kind, 0, 0, 80, tag="cell")
    items = c.find_withtag("cell")
    text = [i for i in items if c.type(i) == "text"][0]
    shapes = [i for i in items if c.type(i) != "text"]
    shape_bottom = max(c.bbox(i)[3] for i in shapes)
    assert c.bbox(text)[1] >= shape_bottom


def test_huge_deck_really_draws_from_deck():
    """덱에 황금탄이 1000개 더 있으면 9칸 대부분이 황금탄으로 나온다 (덱에서 뽑는지 확인)."""
    g = game.Game()
    for _ in range(1000):
        g.add_to_deck("황금탄")
    g.spin(random.Random(3))
    assert g.board.count("황금탄") >= 7


# ---- 2단계 DB 리뷰 ----

@pytest.mark.parametrize("bad_name", [None, ""])
def test_db_rejects_bad_names(tmp_path, bad_name):
    """이름이 없거나 빈 글자면 DB에 저장되지 않는다 (1~10글자 규칙은 game.clean_name이 맡는다)."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    with pytest.raises(sqlite3.IntegrityError):
        db.save_record(path, bad_name, 1, 10, "이병")


def test_schema_sql_also_rejects_empty_name(tmp_path):
    """schema.sql로 만든 테이블도 빈 이름을 막는다 (db.py와 같은 규칙)."""
    con = sqlite3.connect(str(tmp_path / "s.db"))
    with open(SCHEMA_SQL, encoding="utf-8") as f:
        con.executescript(f.read())
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO players (name, created_at) VALUES (?, ?)", ("", "2026-11-18 00:00:00"))
    con.close()


def test_foreign_key_is_checked(tmp_path):
    """없는 플레이어 번호로는 기록을 넣을 수 없다 (외래 키 검사가 켜져 있다)."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    con = db.connect(path)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO records (player_id, round_reached, score, growth_stage, played_at) "
                    "VALUES (?, ?, ?, ?, ?)", (999, 1, 1, "이병", "2026-11-18 00:00:00"))
    con.close()


def test_frozen_ignores_onefile_temp_folder(tmp_path, monkeypatch):
    """onefile exe의 임시 폴더(_MEIPASS)가 아니라 exe 옆에 game.db를 둔다."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "temp"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "박산키우기.exe"))
    assert db.get_db_path() == os.path.join(str(tmp_path / "app"), "game.db")


def test_both_use_autoincrement(tmp_path):
    """schema.sql과 db.py 모두 AUTOINCREMENT를 쓴다 (C8이 비교하지 않는 부분)."""
    with open(SCHEMA_SQL, encoding="utf-8") as f:
        assert f.read().count("AUTOINCREMENT") == 2
    assert "AUTOINCREMENT" in db.CREATE_PLAYERS and "AUTOINCREMENT" in db.CREATE_RECORDS


# ---- 3단계 캐릭터 리뷰 ----

def drawn(tk_root, pose=None, scale=1.0, ratio=0.5, rank="상병"):
    """캐릭터를 하나 그린 Canvas를 돌려준다."""
    import tkinter as tk
    c = tk.Canvas(tk_root, width=600, height=900)
    character.draw_character(c, 10, 10, ratio, rank, pose=pose, scale=scale, tag="x")
    return c


def part_top(c, part):
    return c.bbox("x&&" + part)[1]


def test_body_and_head_move_up_together(tk_root):
    """body_dy·head_dy가 양수면 몸통과 머리(계급장 포함)가 모두 같은 만큼 위로 움직인다.
    (3차 도트: 움직임은 도트 한 칸 단위라 px 대신 "도트 칸 수만큼"으로 확인)"""
    dot = character.dot_size(1.0)
    still = drawn(tk_root)
    bounced = drawn(tk_root, pose={"body_dy": dot, "head_dy": dot})
    for part in ("body", "head", "badge"):
        assert part_top(bounced, part) == part_top(still, part) - dot, part


def test_badge_follows_head_only(tk_root):
    """머리만 움직이면 계급장도 같은 만큼 움직이고 몸통은 그대로다. (3차 도트: 도트 한 칸 단위)"""
    dot = character.dot_size(1.0)
    still = drawn(tk_root)
    moved = drawn(tk_root, pose={"head_dy": dot})
    assert part_top(moved, "head") - part_top(still, "head") == -dot
    assert part_top(moved, "badge") - part_top(still, "badge") == -dot
    assert part_top(moved, "body") == part_top(still, "body")


BIG_POSE = {"arm_raise": 1.0, "hand_drop": 12, "body_dy": 12, "body_grow": 0.06, "head_dy": 12}


@pytest.mark.parametrize("pose", [None, {"arm_raise": 1.0}, {"hand_drop": 12}, BIG_POSE])
@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
def test_dance_poses_stay_inside(tk_root, pose, scale):
    """춤 자세와 크기 배율에서도 그림이 WIDTH×HEIGHT×배율 영역 안에 있다."""
    c = drawn(tk_root, pose=pose, scale=scale)
    x0, y0, x1, y1 = c.bbox("x")
    assert x0 >= 10 and y0 >= 10
    assert x1 <= 10 + character.WIDTH * scale + 1 and y1 <= 10 + character.HEIGHT * scale + 1


def test_unknown_pose_key_is_an_error(tk_root):
    """자세 이름에 오타가 있으면 조용히 무시하지 않고 오류를 낸다."""
    with pytest.raises(ValueError):
        drawn(tk_root, pose={"armraise": 1.0})


def test_face_for_uses_mixing_path_at_ends():
    """(3차 도트로 변경) t=0·1에서도 부위를 겹치는 계산을 거쳐 원본과 같고, 원본 목록·색표를 그대로 내주지 않는다."""
    rows, colors = pixel_art.blend_face(0.0)
    assert (rows, colors) == pixel_art.whole_face(pixel_art.SEONGJAE)
    assert colors is not pixel_art.SEONGJAE["colors"]
    rows[0] = "x"
    assert pixel_art.blend_face(0.0)[0][0] != "x"


@pytest.mark.parametrize("ratio", [0.0, 0.5, 1.0])
def test_pupil_fits_inside_eye(ratio):
    """(3차 도트로 변경) 눈동자 점은 눈썹 아래, 눈 줄(10~11줄) 안에 있다."""
    rows, _ = pixel_art.blend_face(ratio)
    pupil_rows = {y for y, r in enumerate(rows) if "P" in r or "E" in r}
    brow_rows = {y for y, r in enumerate(rows) if "B" in r}
    assert pupil_rows and pupil_rows <= {9, 10, 11}
    assert max(brow_rows) < min(pupil_rows)


def test_seongjae_brows_below_curly_fringe():
    """(3차 도트로 변경) 성재 눈썹은 곱슬 앞머리 아래로 드러난다 (눈썹 칸 위쪽에서 앞머리가 끝난다)."""
    hair = pixel_art.SEONGJAE["layers"]["hair"]
    brows = pixel_art.SEONGJAE["layers"]["eyes"]
    brow_cells = {(x, y) for y, r in enumerate(brows) for x, ch in enumerate(r) if ch == "B"}
    for x, y in brow_cells:
        assert all(hair[yy][x] == pixel_art.CLEAR for yy in range(y, len(hair)))


# ---- GUI 리뷰 ----

def test_db_recovers_after_startup_lock(tk_root, tmp_path):
    """시작할 때 DB가 잠겨 준비에 실패해도, 잠금이 풀리면 랭킹 조회와 기록 저장이 된다."""
    path = str(tmp_path / "game.db")
    lock = sqlite3.connect(path)
    lock.execute("BEGIN EXCLUSIVE")
    app = ui.App(tk_root, path, rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    lock.rollback()
    lock.close()
    assert app.db_ok is False
    app.ranking_button.invoke()
    assert app.ranking_message["text"] == "아직 기록이 없습니다"
    app.ranking_back_button.invoke()
    start(app)
    app.show_gameover()
    assert app.save_message == "기록이 DB에 저장되었습니다"


def test_on_spin_guard_without_button(tk_root, tmp_path):
    """버튼이 아니라 on_spin()을 직접 여러 번 불러도 굴러가는 동안은 한 번만 처리된다."""
    app = ui.App(tk_root, str(tmp_path / "game.db"), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app)
    for _ in range(5):
        app.on_spin()
    wait_until(app, lambda: not app.busy)
    assert app.game.gold == 400


# ---- 2차(슬롯 디펜스) 리뷰 ----

class FixedBoard:
    """spin이 뽑는 9칸을 정해 둔다."""
    def __init__(self, board):
        self.board = list(board)

    def choice(self, deck):
        return self.board.pop(0)


def test_spin_message_keeps_summons_when_some_slots_full():
    """한 스핀에서 1명은 들어가고 1명은 칸이 꽉 차 돌려받으면, 문구에 소환과 반환이 둘 다 보인다."""
    g = game.Game()
    g.soldiers = [("연습탄", 1), ("보통탄", 1), ("예광탄", 1), ("철갑탄", 1), ("연습탄", 2)]
    g.deck.append("황금탄")
    g.soldiers.append(("황금탄", 3))   # 6칸 꽉 참. 황금탄 ★1 짝은 없음
    # 첫 줄 보통탄 → ★1 짝과 합체(들어감), 둘째 줄 황금탄 → 짝 없음·칸 꽉 참(+50골드)
    board = ["보통탄", "보통탄", "보통탄", "황금탄", "황금탄", "황금탄", "연습탄", "예광탄", "철갑탄"]
    summoned = g.spin(FixedBoard(board))
    assert summoned == ["보통탄", "황금탄"]
    assert g.soldiers.count(("보통탄", 2)) == 1           # 보통탄은 짝과 합체
    assert "소환" in g.message and "+50골드" in g.message


# ---- 4차(화면 다듬기) 리뷰 ----

def test_big_dragon_at_line_does_not_cover_soldier_slots(tk_root, tmp_path):
    """2배 커진 드래곤이 방어선(거리 0)까지 와도 병사 칸 오른쪽 끝보다 오른쪽에 그려진다."""
    app = ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.WEAK), time_scale=1.0)
    start(app)
    g = app.game
    g.wave = 5
    g.start_battle()
    g.queue = [q for q in g.queue if q[1]]
    g.battle_step(0.01)
    boss = g.enemies[0]
    boss["x"] = 0.0
    app.draw_enemies()
    slots_right = ui.SLOT_X + 2 * ui.SLOT_W + ui.SLOT_GAP
    assert app.canvas.bbox(app.enemy_items[id(boss)][1])[0] >= slots_right
    app.cancel_all()


# ---- 3차(픽셀 아트) 리뷰 ----

def test_photo_cache_separate_per_window_and_freed_on_close():
    """창(Tk)마다 이미지를 따로 만들고, 창을 닫으면(App.close) 그 창의 캐시만 비운다."""
    import tkinter as tk
    a, b = tk.Tk(), tk.Tk()
    try:
        build = lambda: (["K"], {"K": "#000000"})   # noqa: E731
        img_a = pixel_art.photo(a, "same", build)
        img_b = pixel_art.photo(b, "same", build)
        assert img_a is not img_b
        assert str(img_a) in a.tk.call("image", "names") and str(img_b) in b.tk.call("image", "names")
        pixel_art.forget(a)
        assert all(key[0] is not a.tk for key in pixel_art._CACHE)
        assert any(key[0] is b.tk for key in pixel_art._CACHE)
    finally:
        pixel_art.forget(b)
        a.destroy()
        b.destroy()


def test_app_close_frees_its_images(tmp_path):
    """게임 창을 닫으면 그 창의 도트 이미지 캐시가 남지 않는다."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    interp = root.tk
    app = ui.App(root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app)
    assert any(key[0] is interp for key in pixel_art._CACHE)
    app.close()
    assert not any(key[0] is interp for key in pixel_art._CACHE)


def test_soldiers_stop_firing_when_no_enemy(tk_root, tmp_path):
    """적이 하나도 없는 틈에는 총알을 숨기고 병사도 사격 프레임에서 보통 그림으로 돌아온다."""
    app = ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.STRONG), time_scale=1.0)
    start(app)
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)
    app.battle_button.invoke()
    wait_until(app, lambda: app.canvas.find_withtag("shot"), timeout=5)
    app.cancel_all()
    app.game.enemies = []
    for tick in range(ui.SHOT_TICKS):          # 어느 틱이든 (쏘는 순간 포함)
        app.tick_count = tick
        app.draw_enemies()
        app.draw_shots()
        normal = {str(app.soldier_img(kind)) for _, kind in app.soldier_sprites}
        shown = {app.canvas.itemcget(item, "image") for item, _ in app.soldier_sprites}
        assert shown <= normal
        assert all(app.canvas.itemcget(i, "state") == "hidden" for i in app.canvas.find_withtag("shot"))


def test_enemy_items_match_enemies_during_battle(tk_root, tmp_path):
    """전투 중 캔버스의 적 항목 수는 늘 (그림 + 체력 바탕 + 막대) × 지금 적 수다 (죽은 적 항목이 남지 않음)."""
    app = ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.STRONG), time_scale=0.2)
    start(app)
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)
    app.battle_button.invoke()
    kills_seen = False
    for _ in range(60):
        pump(app, 20)
        if app.screen != "game" or app.game.phase != "battle":
            break
        assert len(app.canvas.find_withtag("enemy")) == 3 * len(app.game.enemies)
        assert len(app.enemy_items) == len(app.game.enemies)
        kills_seen = kills_seen or app.game.kills > 0
    assert kills_seen
