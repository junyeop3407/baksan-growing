# 게임 규칙 테스트 (docs/tests.md의 A, B. 2차 "슬롯 디펜스" 변경표대로 A2~A5·A10·A12~A16을 바꾸고 A6~A9를 지움).
# 화면 없이 game.py와 symbols.py만으로 확인한다. 무작위는 정해진 순서를 내는 가짜로 바꿔 결과를 고정한다.
import random

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


def run_battle(g, dt=0.1):
    """전투를 끝까지 돌린다."""
    g.start_battle()
    for _ in range(100000):
        if g.battle_over:
            return
        g.battle_step(dt)
    raise AssertionError("전투가 끝나지 않음")


def clear_wave(g):
    """아주 강한 병사로 웨이브를 막는다."""
    g.soldiers = [("황금탄", 3)] * 6
    run_battle(g)
    assert g.finish_wave() == "clear"


# ---- A. 게임 규칙 ----

def test_a1_start_deck():
    """A1: 처음 덱은 연습탄 4, 보통탄 3, 예광탄 2, 철갑탄 1, 황금탄 0 (모두 10개)."""
    g = game.Game()
    assert g.deck_counts() == {"연습탄": 4, "보통탄": 3, "예광탄": 2, "철갑탄": 1, "황금탄": 0}
    assert len(g.deck) == 10


def test_a2_no_line_is_a_miss():
    """A2: 맞은 줄이 0개면 꽝 (병사 0명 소환)."""
    g = game.Game()
    board = board_of("연보예", "철황연", "보예철")
    assert game.count_lines(board) == 0
    assert g.spin(FixedRng(board)) == []
    assert g.soldiers == []


def test_a3_one_line_one_soldier():
    """A3: 가로 한 줄이 맞으면 그 총알의 병사 1명을 소환한다."""
    g = game.Game()
    board = board_of("보보보", "연예철", "예철연")
    assert game.count_lines(board) == 1
    assert g.spin(FixedRng(board)) == ["보통탄"]
    assert g.soldiers == [("보통탄", 1)]


def test_a4_all_eight_lines():
    """A4: 9칸이 모두 연습탄이면 8줄 → 훈련병 8명 소환 → 합체 연쇄로 ★3 훈련병 2명."""
    g = game.Game()
    board = board_of("연연연", "연연연", "연연연")
    assert game.count_lines(board) == 8
    assert g.spin(FixedRng(board)) == ["연습탄"] * 8
    assert g.soldiers == [("연습탄", 3), ("연습탄", 3)]


def test_a5_lines_share_cells():
    """A5: 십자·X자는 2줄로 세어 병사 2명 소환 (같은 종류라 합체해 ★2 1명)."""
    g = game.Game()
    assert g.spin(FixedRng(board_of("연예연", "예예예", "보예보"))) == ["예광탄", "예광탄"]
    assert g.soldiers == [("예광탄", 2)]
    g2 = game.Game()
    assert g2.spin(FixedRng(board_of("철연철", "보철보", "철연철"))) == ["철갑탄", "철갑탄"]
    assert g2.soldiers == [("철갑탄", 2)]


def test_a10_fail_first_wave():
    """A10: 1웨이브 탈락이면 도달 웨이브 1, 이병, 점수 = 처치 수 × 10."""
    g = game.Game()
    run_battle(g)
    assert g.finish_wave() == "over"
    assert g.wave == 1
    assert g.rank == "이병"
    assert g.score == g.kills * 10


def test_a11_rank_by_cleared_waves():
    """A11: 막은 웨이브 0개 이병, 1개 일병, 2개 상병, 3개 병장, 4개 하사."""
    assert [game.rank_for(n) for n in range(5)] == ["이병", "일병", "상병", "병장", "하사"]


def test_a12_four_waves_makes_hasa():
    """A12: 4웨이브를 막으면 하사, 얼굴 비율 100%."""
    g = game.Game()
    for _ in range(4):
        clear_wave(g)
    assert g.rank == "하사"
    assert g.face_ratio == 1.0


def test_a13_hasa_stays_after():
    """A13: 하사 이후(5·10웨이브를 막음)에도 계급 하사, 얼굴 비율 100% 유지."""
    g = game.Game()
    for _ in range(5):
        clear_wave(g)
    assert (g.rank, g.face_ratio) == ("하사", 1.0)
    for _ in range(5):
        clear_wave(g)
    assert (g.rank, g.face_ratio) == ("하사", 1.0)
    assert game.face_ratio_for(10) == 1.0


def test_a14_score_rule():
    """A14: 점수 = 처치 수 × 10 + 막은 웨이브 × 100."""
    g = game.Game()
    clear_wave(g)
    assert g.kills == 7
    assert g.score == 7 * 10 + 1 * 100
    g.soldiers = []
    run_battle(g)
    assert g.finish_wave() == "over"
    assert g.score == 7 * 10 + 1 * 100


def test_a15_shop_offers_three_different_items():
    """A15: 상점 3개는 4가지 항목(총알 추가·하트·공격력·첫 스핀 무료) 중 서로 다른 것."""
    g = game.Game()
    rng = random.Random(7)
    for _ in range(200):
        offer = g.shop_offer(rng)
        names = [item for item, _ in offer]
        assert len(names) == 3 and len(set(names)) == 3
        assert set(names) <= set(game.SHOP_ITEMS)
        for item, bullet in offer:
            assert (bullet in symbols.BULLET_ORDER) if item == "총알 추가" else bullet is None


def test_a16_add_existing_bullet():
    """A16: "총알 추가"로 이미 덱에 있는 총알을 고르면 그 총알만 1개 늘고 나머지는 그대로."""
    g = game.Game()
    before = g.deck_counts()
    g.apply_shop("총알 추가", "보통탄")
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
