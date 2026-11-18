# DB가 실패해도 게임이 꺼지지 않는지 확인한다 (사장 요청: 깨진 game.db, 쓸 수 없는 위치, 잠긴 DB).
import os
import sqlite3
import stat

import pytest

import db
import ui
from helpers import PatternRng, start

SAVE_FAIL = "기록을 저장하지 못했습니다"
LOAD_FAIL = "기록을 불러오지 못했습니다"


def app_at(tk_root, path):
    return ui.App(tk_root, path, rng=PatternRng(PatternRng.WEAK), time_scale=0.01)


def game_over_now(app):
    """게임을 시작하고 바로 게임 오버 화면으로 보낸다."""
    start(app)
    assert app.screen == "game"
    app.show_gameover()
    assert app.screen == "gameover"


def test_broken_db_file(tk_root, tmp_path):
    """깨진 game.db(아무 글자나 쓴 파일): 게임은 시작되고, 저장·랭킹은 실패 문구를 보여 준다."""
    path = tmp_path / "game.db"
    path.write_text("이건 DB가 아니라 그냥 글자입니다 " * 50, encoding="utf-8")
    app = app_at(tk_root, str(path))
    assert app.db_ok is False
    game_over_now(app)
    assert app.save_message == SAVE_FAIL
    app.menu_button.invoke()
    app.ranking_button.invoke()
    assert app.ranking_message["text"] == LOAD_FAIL


def test_missing_folder(tk_root, tmp_path):
    """없는 폴더(쓸 수 없는 위치): 게임은 시작되고, 저장·랭킹은 실패 문구를 보여 준다."""
    app = app_at(tk_root, str(tmp_path / "없는폴더" / "game.db"))
    assert app.db_ok is False
    game_over_now(app)
    assert app.save_message == SAVE_FAIL
    app.menu_button.invoke()
    app.ranking_button.invoke()
    assert app.ranking_message["text"] == LOAD_FAIL


@pytest.fixture
def readonly_db(tmp_path):
    path = str(tmp_path / "game.db")
    db.init_db(path)
    db.save_record(path, "예전기록", 2, 300, "일병")
    os.chmod(path, stat.S_IREAD)
    yield path
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


def test_readonly_db(tk_root, readonly_db):
    """읽기 전용 game.db: 저장은 실패 문구, 랭킹은 예전 기록을 그대로 보여 준다."""
    app = app_at(tk_root, readonly_db)
    game_over_now(app)
    assert app.save_message == SAVE_FAIL
    app.menu_button.invoke()
    app.ranking_button.invoke()
    assert len(app.ranking_tree.get_children()) == 1


def test_locked_db(tk_root, tmp_path):
    """다른 곳에서 잠근 game.db: 저장·랭킹이 실패 문구를 보여 주고 앱은 계속 돈다."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    app = app_at(tk_root, path)
    lock = sqlite3.connect(path)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        game_over_now(app)
        assert app.save_message == SAVE_FAIL
        app.menu_button.invoke()
        app.ranking_button.invoke()
        assert app.ranking_message["text"] == LOAD_FAIL
    finally:
        lock.rollback()
        lock.close()
    app.ranking_back_button.invoke()
    assert app.screen == "start"
