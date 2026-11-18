# 게임 규칙(스핀, 점수 계산, 라운드, 상점, 계급)을 담당한다.
# 화면(ui.py)과 분리되어 있어 콘솔이나 테스트에서도 그대로 쓸 수 있다.
# 콘솔에서 한 판 해 보기: python src/game.py
import random

from symbols import BULLETS, BULLET_ORDER, RANKS, START_DECK

SPINS_PER_ROUND = 5
NAME_MAX = 10
NAME_MESSAGE = "이름을 1~10글자로 입력해 주세요."

# 9칸 번호         같은 총알 3개를 검사하는 줄 8개
#  0 1 2           가로 3줄, 세로 3줄, 대각선 2줄
#  3 4 5
#  6 7 8
LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


def target_score(round_no):
    """라운드 목표 점수: 1라운드 100점에서 1.25배씩, 소수점은 버린다."""
    return 100 * 5 ** (round_no - 1) // 4 ** (round_no - 1)


def count_lines(board):
    """판(9칸)에서 같은 총알 3개가 맞은 줄 수를 센다. 한 칸이 여러 줄에 속해도 줄마다 센다."""
    return sum(1 for a, b, c in LINES if board[a] == board[b] == board[c])


def spin_score(board):
    """스핀 점수 = 9칸 점수 합 × (1 + 맞은 줄 수)."""
    total = sum(BULLETS[kind]["points"] for kind in board)
    return total * (1 + count_lines(board))


def rank_for(passed_rounds):
    """통과한 라운드 수로 계급 이름을 정한다 (하사가 끝)."""
    return RANKS[min(passed_rounds, len(RANKS) - 1)][0]


def face_ratio_for(passed_rounds):
    """통과한 라운드 수로 얼굴의 최산 비율(0~1)을 정한다."""
    return RANKS[min(passed_rounds, len(RANKS) - 1)][1]


def clean_name(text):
    """이름 앞뒤 공백을 빼고 1~10글자인지 확인해 (이름, 안내 문구)를 돌려준다."""
    name = text.strip()
    if 1 <= len(name) <= NAME_MAX:
        return name, ""
    return None, NAME_MESSAGE


class Game:
    """한 판의 상태(덱, 라운드, 점수, 계급)를 들고 규칙대로 진행한다."""

    def __init__(self):
        self.deck = [kind for kind, count in START_DECK.items() for _ in range(count)]
        self.round_no = 1
        self.spins_left = SPINS_PER_ROUND
        self.round_score = 0
        self.total_score = 0
        self.passed_rounds = 0
        self.board = []
        self.lines = 0

    @property
    def target(self):
        """이번 라운드 목표 점수."""
        return target_score(self.round_no)

    @property
    def rank(self):
        """지금 계급 이름."""
        return rank_for(self.passed_rounds)

    @property
    def face_ratio(self):
        """지금 얼굴의 최산 비율."""
        return face_ratio_for(self.passed_rounds)

    def deck_counts(self):
        """덱에 총알이 종류별로 몇 개 있는지 돌려준다."""
        return {kind: self.deck.count(kind) for kind in BULLET_ORDER}

    def spin(self, rng):
        """덱에서 9칸을 뽑아 점수를 더하고 이번 스핀 점수를 돌려준다."""
        if self.spins_left <= 0:
            raise ValueError("이번 라운드에 남은 스핀이 없다")
        self.board = [rng.choice(self.deck) for _ in range(9)]
        self.lines = count_lines(self.board)
        score = spin_score(self.board)
        self.round_score += score
        self.total_score += score
        self.spins_left -= 1
        return score

    def finish_round(self):
        """스핀을 다 쓴 라운드를 판정한다. 통과면 다음 라운드를 준비하고 "pass", 아니면 "over"."""
        if self.spins_left > 0:
            raise ValueError("스핀이 남아 있어 라운드를 끝낼 수 없다")
        if self.round_score < self.target:
            return "over"
        self.passed_rounds += 1
        self.round_no += 1
        self.spins_left = SPINS_PER_ROUND
        self.round_score = 0
        self.board = []
        self.lines = 0
        return "pass"

    def shop_offer(self, rng):
        """상점에 보여 줄 서로 다른 총알 3개를 고른다."""
        return rng.sample(BULLET_ORDER, 3)

    def add_to_deck(self, kind):
        """상점에서 고른 총알을 덱에 1개 더한다."""
        if kind not in BULLETS:
            raise ValueError("없는 총알: " + kind)
        self.deck.append(kind)


def play_in_console():
    """화면 없이 콘솔에서 한 판을 해 본다 (Enter로 스핀, 숫자로 상점 선택)."""
    rng = random.Random()
    g = Game()
    while True:
        print("\n[" + str(g.round_no) + "라운드] 목표", g.target, "점 / 계급", g.rank)
        while g.spins_left > 0:
            input("Enter를 누르면 스핀 (남은 스핀 " + str(g.spins_left) + ")")
            score = g.spin(rng)
            for row in range(3):
                print("  ".join(g.board[row * 3:row * 3 + 3]))
            print("이번", score, "점 (맞은 줄", g.lines, ") / 라운드", g.round_score, "점")
        if g.finish_round() == "over":
            print("\n게임 오버! 총점", g.total_score, "/ 도달 라운드", g.round_no, "/ 계급", g.rank)
            return
        offer = g.shop_offer(rng)
        print("\n통과! 계급:", g.rank)
        for number, kind in enumerate(offer, 1):
            print(number, kind, "(" + str(BULLETS[kind]["points"]) + "점)")
        choice = input("덱에 넣을 총알 번호 (1~3): ").strip()
        g.add_to_deck(offer[int(choice) - 1] if choice in ("1", "2", "3") else offer[0])


if __name__ == "__main__":
    play_in_console()
