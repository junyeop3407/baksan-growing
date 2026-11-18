# 2차 화면 다듬기 테스트 (사장 캡처 검토 결과): 총알 크기·글자, 앞머리 가닥, 빈 판 안내, 랭킹 문구 색.
import tkinter as tk
import tkinter.font as tkfont

import pytest

import character
import symbols
import ui
from helpers import PatternRng, start, wait_until

GRAY = "#6b6b6b"
RED = "#b00020"


@pytest.mark.parametrize("kind", ["보통탄", "예광탄"])
def test_bullet_is_about_60_percent_of_cell(tk_root, kind):
    """기본 총알(보통탄·예광탄)은 100px 칸 높이의 약 60%다."""
    c = tk.Canvas(tk_root, width=200, height=200)
    symbols.draw_bullet(c, kind, 0, 0, 100, tag="b")
    shapes = [i for i in c.find_withtag("b") if c.type(i) != "text"]
    top = min(c.bbox(i)[1] for i in shapes)
    bottom = max(c.bbox(i)[3] for i in shapes)
    assert 55 <= bottom - top <= 68


@pytest.mark.parametrize("size", [80, 100])
def test_bullet_label_big_and_bold(tk_root, size):
    """이름 글자는 굵고, 가장 작은 칸(80px)에서도 14px 이상이다."""
    c = tk.Canvas(tk_root, width=200, height=200)
    symbols.draw_bullet(c, "연습탄", 0, 0, size, tag="b")
    text = [i for i in c.find_withtag("b") if c.type(i) == "text"][0]
    font = tkfont.Font(root=tk_root, font=c.itemcget(text, "font"))
    assert font.actual("weight") == "bold"
    assert abs(font.actual("size")) >= 14 or font.metrics("linespace") >= 18


@pytest.mark.parametrize("ratio", [0.25, 0.5, 0.75, 1.0])
def test_strands_end_above_brows(tk_root, ratio):
    """앞머리 가닥은 이마에서 시작해 눈썹 위에서 끝난다 (눈을 가로지르지 않는다)."""
    c = tk.Canvas(tk_root, width=400, height=500)
    character.draw_character(c, 0, 0, ratio, "상병", tag="x")
    strands = c.find_withtag("x&&strand")
    brows = c.find_withtag("x&&brow")
    assert len(brows) == 2
    if strands:
        assert c.bbox("x&&strand")[3] <= min(c.bbox(b)[1] for b in brows)


def test_two_thin_strands_at_full_ratio(tk_root):
    """100%(하사)에서 앞머리 가닥은 2개다."""
    c = tk.Canvas(tk_root, width=400, height=500)
    character.draw_character(c, 0, 0, 1.0, "하사", tag="x")
    assert len(c.find_withtag("x&&strand")) == 2


def test_empty_board_hint_until_first_spin(tk_root, tmp_path):
    """스핀 전 빈 판에는 옅은 회색 "스핀을 눌러 시작하세요"가 있고, 첫 스핀 때 사라진다."""
    app = ui.App(tk_root, str(tmp_path / "game.db"), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app)
    hints = app.canvas.find_withtag("hint")
    assert [app.canvas.itemcget(i, "text") for i in hints] == ["스핀을 눌러 시작하세요"]
    assert app.canvas.itemcget(hints[0], "fill") == ui.HINT_GRAY
    app.spin_button.invoke()
    wait_until(app, lambda: not app.busy)
    assert app.canvas.find_withtag("hint") == ()


def test_ranking_message_colors(tk_root, tmp_path):
    """"아직 기록이 없습니다"는 회색, 불러오기 실패는 빨간색."""
    app = ui.App(tk_root, str(tmp_path / "game.db"), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    app.ranking_button.invoke()
    assert app.ranking_message["fg"] == GRAY
    broken = tmp_path / "broken.db"
    broken.write_text("DB 아님 " * 40, encoding="utf-8")
    app2 = ui.App(tk_root, str(broken), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    app2.ranking_button.invoke()
    assert app2.ranking_message["text"] == "기록을 불러오지 못했습니다"
    assert app2.ranking_message["fg"] == RED
