# 리뷰에서 나온 지적을 확인하는 회귀 테스트 (승인 목록과 별도).
import os
import random
import sqlite3
import sys

import pytest

import db
import game
import symbols

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
