# 난이도 확인용 시뮬레이션: game.py의 규칙 그대로 여러 판을 자동으로 해 보고
# 하사(4라운드 통과)까지 가는 비율을 센다. 상점 선택 방법 2가지(가장 좋은 것 / 아무거나)로 나눠 본다.
# 실행 (앱 폴더에서): python tests/tools/simulate.py
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

from game import Game  # noqa: E402
from symbols import BULLETS  # noqa: E402


def play_one(rng, strategy):
    """한 판을 끝까지 자동으로 해서 게임 오버된 라운드 번호를 돌려준다."""
    g = Game()
    while True:
        while g.spins_left > 0:
            g.spin(rng)
        if g.finish_round() == "over":
            return g.round_no
        offer = g.shop_offer(rng)
        if strategy == "best":
            g.add_to_deck(max(offer, key=lambda kind: BULLETS[kind]["points"]))
        else:
            g.add_to_deck(rng.choice(offer))


def main():
    """전략마다 10묶음 × 100판을 돌려 비율을 출력한다."""
    for strategy, label in [("best", "상점에서 가장 좋은 총알"), ("random", "상점에서 아무거나")]:
        rates = []
        all_rounds = []
        for seed in range(10):
            rng = random.Random(seed)
            rounds = [play_one(rng, strategy) for _ in range(100)]
            rates.append(sum(1 for r in rounds if r >= 5))
            all_rounds += rounds
        n = len(all_rounds)
        print(label)
        print("  하사 도달(4라운드 통과): 100판마다", min(rates), "~", max(rates), "판, 전체",
              round(100 * sum(1 for r in all_rounds if r >= 5) / n), "%")
        print("  1라운드 탈락:", round(100 * sum(1 for r in all_rounds if r == 1) / n), "%",
              "/ 5라운드 통과:", round(100 * sum(1 for r in all_rounds if r >= 6) / n), "%")


if __name__ == "__main__":
    main()
