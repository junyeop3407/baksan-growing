# 캐릭터 테스트 (docs/tests.md의 D1~D6).
# 설정값 섞기(보간)가 정확한지, 그린 결과가 부위별로 나뉘고 캐릭터 영역 안에 들어가는지 확인한다.
import pytest

import character
import symbols

RANK_NAMES = [name for name, _ in symbols.RANKS]


def is_color(value):
    return isinstance(value, str) and value.startswith("#")


def channels(color):
    return [int(color[i:i + 2], 16) for i in (1, 3, 5)]


def test_d1_zero_is_seongjae():
    """D1: 비율 0% 얼굴 설정값은 성재 설정값과 정확히 같다."""
    assert character.face_for(0.0) == character.SEONGJAE


def test_d2_hundred_is_choisan():
    """D2: 비율 100% 얼굴 설정값은 최산 설정값과 정확히 같다."""
    assert character.face_for(1.0) == character.CHOISAN


def test_d3_half_is_exact_middle():
    """D3: 비율 50%면 숫자·색은 두 캐릭터 값의 정확히 중간이고, 모양의 점 개수는 같다."""
    a, b = character.SEONGJAE, character.CHOISAN
    assert set(a) == set(b)
    half = character.face_for(0.5)
    assert set(half) == set(a)
    for key in a:
        if is_color(a[key]):
            # 색은 0~255 정수라 가운데가 .5로 떨어지면 반올림한다
            for got, x, y in zip(channels(half[key]), channels(a[key]), channels(b[key])):
                assert abs(got - (x + y) / 2) <= 0.5, key
        elif isinstance(a[key], list):
            assert len(a[key]) == len(b[key]) == len(half[key]), key
            for (hx, hy), (ax, ay), (bx, by) in zip(half[key], a[key], b[key]):
                assert hx == (ax + bx) / 2 and hy == (ay + by) / 2, key
        else:
            assert half[key] == (a[key] + b[key]) / 2, key


def test_d4_ratio_per_rank():
    """D4: 계급별 비율은 이병 0, 일병 25, 상병 50, 병장 75, 하사 100%."""
    assert dict(symbols.RANKS) == {"이병": 0.0, "일병": 0.25, "상병": 0.5, "병장": 0.75, "하사": 1.0}
    assert [character.ratio_for_rank(name) for name in RANK_NAMES] == [0.0, 0.25, 0.5, 0.75, 1.0]


@pytest.fixture
def canvas(tk_root):
    import tkinter as tk
    c = tk.Canvas(tk_root, width=character.WIDTH + 100, height=character.HEIGHT + 100)
    c.pack()
    return c


@pytest.mark.parametrize("rank", RANK_NAMES)
def test_d5_parts_are_separate(canvas, rank):
    """D5: 그린 결과에 몸통·왼팔·오른팔·머리·계급장이 따로 있다."""
    character.draw_character(canvas, 0, 0, character.ratio_for_rank(rank), rank, tag="hero")
    for part in ("body", "arm_l", "arm_r", "head", "badge"):
        assert canvas.find_withtag("hero&&" + part), part


@pytest.mark.parametrize("ratio", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("rank", RANK_NAMES)
def test_d6_everything_inside_area(canvas, ratio, rank):
    """D6: 0%·50%·100% 모두 그림 전체가 캐릭터 영역(WIDTH×HEIGHT) 안에 있다."""
    x, y = 50, 50
    character.draw_character(canvas, x, y, ratio, rank, tag="hero")
    x0, y0, x1, y1 = canvas.bbox("hero")
    assert x0 >= x and y0 >= y
    assert x1 <= x + character.WIDTH and y1 <= y + character.HEIGHT
