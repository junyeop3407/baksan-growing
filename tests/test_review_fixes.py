# 리뷰에서 나온 지적을 확인하는 회귀 테스트 (승인 목록과 별도).
import os
import random
import sqlite3
import sys

import pytest

import character
import db
import game
import symbols
import ui
from helpers import PatternRng, start, wait_until

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
    """body_dy·head_dy가 양수면 몸통과 머리(계급장 포함)가 모두 위로 움직인다."""
    still = drawn(tk_root)
    bounced = drawn(tk_root, pose={"body_dy": 6, "head_dy": 6})
    for part in ("body", "head", "badge"):
        assert part_top(bounced, part) == part_top(still, part) - 6, part


def test_badge_follows_head_only(tk_root):
    """머리만 움직이면 계급장도 같은 만큼 움직이고 몸통은 그대로다."""
    still = drawn(tk_root)
    moved = drawn(tk_root, pose={"head_dy": 4})
    assert part_top(moved, "head") - part_top(still, "head") == -4
    assert part_top(moved, "badge") - part_top(still, "badge") == -4
    assert part_top(moved, "body") == part_top(still, "body")


BIG_POSE = {"arm_raise": 1.0, "hand_drop": 12, "body_dy": 12, "body_grow": 0.06, "head_dy": 12, "squint": 0.5}


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
    """t=0·1에서도 섞기 계산을 거쳐 원본과 같고, 원본 목록을 그대로 내주지 않는다."""
    zero = character.face_for(0.0)
    assert zero == character.SEONGJAE
    assert zero["mouth"] is not character.SEONGJAE["mouth"]
    assert character.face_for(1.0)["mouth"] is not character.CHOISAN["mouth"]


@pytest.mark.parametrize("squint", [1.0, 0.5])
@pytest.mark.parametrize("ratio", [0.0, 0.5, 1.0])
def test_pupil_fits_inside_eye(ratio, squint):
    """눈동자 반지름은 눈 흰자의 실제 높이(설정 높이의 절반쯤)를 넘지 않는다."""
    f = character.face_for(ratio)
    assert character.pupil_radius(f, squint) <= f["eye_h"] * squint * 0.6


def test_seongjae_brows_below_curly_fringe():
    """성재 눈썹은 곱슬 앞머리 아래로 드러난다 (앞머리 끝보다 아래)."""
    f = character.SEONGJAE
    curl_bottom = f["fringe_y"] - 4 + 2 * 8
    assert f["brow_y"] - f["brow_thick"] / 2 > curl_bottom


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
