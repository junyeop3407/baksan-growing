# 리뷰에서 나온 지적을 확인하는 회귀 테스트 (승인 목록과 별도).
import random

import pytest

import game
import symbols


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
