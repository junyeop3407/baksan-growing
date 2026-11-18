# 게임 규칙 테스트 (docs/tests.md의 A1~A17, B1~B6).
# 화면 없이 game.py와 symbols.py만으로 확인한다. 무작위는 정해진 순서를 내는 가짜로 바꿔 결과를 고정한다.
import random

import pytest

import game
import symbols


class FixedRng:
    """choice()가 정해 둔 총알을 차례로 돌려주는 가짜 무작위."""

    def __init__(self, picks):
        self.picks = list(picks)

    def choice(self, seq):
        return self.picks.pop(0)


def board_of(*rows):
    """'연연보' 같은 줄 3개로 판(9칸 목록)을 만든다. 글자 하나가 총알 하나."""
    short = {"연": "연습탄", "보": "보통탄", "예": "예광탄", "철": "철갑탄", "황": "황금탄"}
    return [short[ch] for row in rows for ch in row]


def points_sum(board):
    return sum(symbols.BULLETS[kind]["points"] for kind in board)


# ---- A. 게임 규칙 ----

def test_a1_start_deck():
    """A1: 처음 덱은 연습탄 4, 보통탄 3, 예광탄 2, 철갑탄 1, 황금탄 0 (모두 10개)."""
    g = game.Game()
    counts = g.deck_counts()
    assert counts == {"연습탄": 4, "보통탄": 3, "예광탄": 2, "철갑탄": 1, "황금탄": 0}
    assert len(g.deck) == 10


def test_bullet_points():
    """총알 점수: 연습탄 1, 보통탄 2, 예광탄 3, 철갑탄 5, 황금탄 8."""
    points = {kind: symbols.BULLETS[kind]["points"] for kind in symbols.BULLET_ORDER}
    assert points == {"연습탄": 1, "보통탄": 2, "예광탄": 3, "철갑탄": 5, "황금탄": 8}


def test_a2_no_line():
    """A2: 맞은 줄이 0개면 스핀 점수 = 9칸 합 × 1."""
    board = board_of("연보예", "철황연", "보예철")
    assert game.count_lines(board) == 0
    assert game.spin_score(board) == points_sum(board) * 1


def test_a3_one_line():
    """A3: 가로 한 줄만 같으면 9칸 합 × 2."""
    board = board_of("보보보", "연예철", "예철연")
    assert game.count_lines(board) == 1
    assert game.spin_score(board) == points_sum(board) * 2


def test_a4_all_eight_lines():
    """A4: 9칸이 모두 연습탄이면 8줄이 다 맞아 9 × 9 = 81점."""
    board = board_of("연연연", "연연연", "연연연")
    assert game.count_lines(board) == 8
    assert game.spin_score(board) == 81


def test_a5_lines_share_cells():
    """A5: 줄이 칸을 겹쳐 써도 줄마다 센다 (십자 2줄, X자 2줄)."""
    cross = board_of("연예연", "예예예", "보예보")
    assert game.count_lines(cross) == 2
    assert game.spin_score(cross) == points_sum(cross) * 3
    x_shape = board_of("철연철", "보철보", "철연철")
    assert game.count_lines(x_shape) == 2
    assert game.spin_score(x_shape) == points_sum(x_shape) * 3


def test_a6_target_scores():
    """A6: 목표 점수는 1~6라운드에 100, 125, 156, 195, 244, 305."""
    assert [game.target_score(r) for r in range(1, 7)] == [100, 125, 156, 195, 244, 305]


def spin_out(g):
    """남은 스핀을 모두 연습탄만 나오는 판으로 돌린다 (값은 테스트에서 덮어씀)."""
    while g.spins_left > 0:
        g.spin(FixedRng(["연습탄"] * 9))


def test_a7_exact_target_passes():
    """A7: 라운드 점수가 목표와 정확히 같으면 통과."""
    g = game.Game()
    spin_out(g)
    g.round_score = game.target_score(1)
    assert g.finish_round() == "pass"


def test_a8_one_short_is_game_over():
    """A8: 목표보다 1점 모자라면 게임 오버."""
    g = game.Game()
    spin_out(g)
    g.round_score = game.target_score(1) - 1
    assert g.finish_round() == "over"


def test_a9_only_five_spins():
    """A9: 스핀은 라운드당 5번까지. 6번째 스핀은 되지 않는다."""
    g = game.Game()
    assert g.spins_left == 5
    for _ in range(5):
        g.spin(random.Random(1))
    assert g.spins_left == 0
    with pytest.raises(ValueError):
        g.spin(random.Random(1))


def test_a10_fail_first_round():
    """A10: 1라운드 탈락이면 도달 라운드 1, 계급 이병, 총점 = 1라운드 점수."""
    g = game.Game()
    for _ in range(5):
        g.spin(FixedRng(board_of("연연보", "보보연", "연연보")))
    round_score = g.round_score
    assert round_score < game.target_score(1)
    assert g.finish_round() == "over"
    assert g.round_no == 1
    assert g.rank == "이병"
    assert g.total_score == round_score


def test_a11_rank_by_passes():
    """A11: 통과 0번 이병, 1번 일병, 2번 상병, 3번 병장, 4번 하사."""
    assert [game.rank_for(n) for n in range(5)] == ["이병", "일병", "상병", "병장", "하사"]


def pass_rounds(g, count):
    """라운드를 count번 통과시킨다."""
    for _ in range(count):
        spin_out(g)
        g.round_score = g.target
        assert g.finish_round() == "pass"


def test_a12_four_passes_makes_hasa():
    """A12: 4라운드를 통과하면 하사, 얼굴 비율 100%."""
    g = game.Game()
    pass_rounds(g, 4)
    assert g.rank == "하사"
    assert g.face_ratio == 1.0


def test_a13_hasa_stays_after():
    """A13: 하사 이후(5·10라운드 통과)에도 계급 하사, 얼굴 비율 100% 유지."""
    g = game.Game()
    pass_rounds(g, 5)
    assert (g.rank, g.face_ratio) == ("하사", 1.0)
    pass_rounds(g, 5)
    assert (g.rank, g.face_ratio) == ("하사", 1.0)
    assert game.face_ratio_for(10) == 1.0


def test_a14_total_includes_failed_round():
    """A14: 총점 = 통과한 라운드 점수 + 마지막(실패한) 라운드 점수."""
    g = game.Game()
    strong = board_of("철철철", "철철철", "철철철")
    for _ in range(5):
        g.spin(FixedRng(strong))
    first = g.round_score
    assert g.finish_round() == "pass"
    weak = board_of("연연보", "보보연", "연연보")
    for _ in range(5):
        g.spin(FixedRng(weak))
    second = g.round_score
    assert g.finish_round() == "over"
    assert g.total_score == first + second


def test_a15_shop_offers_three_different():
    """A15: 상점에 보여 주는 3개는 서로 다르고 5종 안에서 나온다."""
    g = game.Game()
    rng = random.Random(7)
    for _ in range(200):
        offer = g.shop_offer(rng)
        assert len(offer) == 3
        assert len(set(offer)) == 3
        assert set(offer) <= set(symbols.BULLET_ORDER)


def test_a16_pick_existing_bullet():
    """A16: 이미 덱에 있는 총알을 고르면 그 총알만 1개 늘고 나머지는 그대로."""
    g = game.Game()
    before = g.deck_counts()
    g.add_to_deck("보통탄")
    after = g.deck_counts()
    assert after["보통탄"] == before["보통탄"] + 1
    for kind in symbols.BULLET_ORDER:
        if kind != "보통탄":
            assert after[kind] == before[kind]


def test_a17_huge_deck():
    """A17: 덱이 아주 커져도(1000개 추가) 스핀이 정상이고 9칸 모두 덱에 있는 총알이다."""
    g = game.Game()
    for _ in range(1000):
        g.add_to_deck("황금탄")
    assert len(g.deck) == 1010
    g.spin(random.Random(3))
    assert len(g.board) == 9
    assert all(kind in g.deck for kind in g.board)


# ---- B. 이름 ----

def test_b1_empty_name():
    """B1: 빈 이름이면 시작하지 않고 안내 문구를 준다."""
    name, message = game.clean_name("")
    assert name is None and message


def test_b2_spaces_only():
    """B2: 공백만 있으면 시작하지 않고 안내 문구를 준다."""
    name, message = game.clean_name("   ")
    assert name is None and message


def test_b3_one_char():
    """B3: 1글자는 시작한다."""
    assert game.clean_name("박") == ("박", "")


def test_b4_ten_chars():
    """B4: 10글자는 시작한다."""
    assert game.clean_name("가나다라마바사아자차") == ("가나다라마바사아자차", "")


def test_b5_eleven_chars():
    """B5: 11글자면 시작하지 않고 안내 문구를 준다."""
    name, message = game.clean_name("가나다라마바사아자차카")
    assert name is None and message


def test_b6_mixed_and_trimmed():
    """B6: 한글·영어·숫자가 섞인 이름은 앞뒤 공백을 빼고 시작한다."""
    assert game.clean_name("  박산a1  ") == ("박산a1", "")
