# 총알 그림 테스트 (docs/tests.md의 E2, E3).
# 실제 tkinter Canvas에 그려 보고, 그림과 이름 글자가 칸 안에 있는지, 줄 강조 테두리가 그림을 덮지 않는지 확인한다.
import pytest

import symbols

SIZES = [80, 120, 160]


@pytest.fixture
def canvas(tk_root):
    import tkinter as tk
    c = tk.Canvas(tk_root, width=400, height=400)
    c.pack()
    tk_root.update_idletasks()
    return c


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("kind", ["연습탄", "보통탄", "예광탄", "철갑탄", "황금탄"])
def test_e2_bullet_has_picture_and_name(canvas, kind, size):
    """E2 (3차 도트로 변경): 칸마다 총알 도트 그림(이미지 1장)과 이름 글자가 함께 있다."""
    symbols.draw_bullet(canvas, kind, 10, 10, size, tag="cell")
    items = canvas.find_withtag("cell")
    texts = [i for i in items if canvas.type(i) == "text"]
    pictures = [i for i in items if canvas.type(i) == "image"]
    assert [canvas.itemcget(i, "text") for i in texts] == [kind]
    assert len(pictures) == 1


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("kind", ["연습탄", "보통탄", "예광탄", "철갑탄", "황금탄"])
def test_e3_highlight_does_not_cover_bullet(canvas, kind, size):
    """E3: 줄 강조 테두리가 총알 그림 위를 덮지 않는다 (테두리 안쪽 경계 안에 그림이 있다)."""
    x, y = 20, 20
    symbols.draw_bullet(canvas, kind, x, y, size, tag="bullet")
    symbols.draw_highlight(canvas, x, y, size, tag="hl")
    (hl,) = canvas.find_withtag("hl")
    x0, y0, x1, y1 = canvas.coords(hl)
    half = float(canvas.itemcget(hl, "width")) / 2
    inner = (x0 + half, y0 + half, x1 - half, y1 - half)
    outer = (x0 - half, y0 - half, x1 + half, y1 + half)
    assert outer[0] >= x and outer[1] >= y and outer[2] <= x + size and outer[3] <= y + size
    bx0, by0, bx1, by1 = canvas.bbox("bullet")
    assert bx0 >= inner[0] and by0 >= inner[1]
    assert bx1 <= inner[2] and by1 <= inner[3]
