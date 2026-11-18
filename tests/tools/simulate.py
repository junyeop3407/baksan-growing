# 난이도 확인용 시뮬레이션: game.py의 슬롯 디펜스 규칙 그대로 여러 판을 자동으로 해 보고
# 도달한 웨이브 평균과 하사(4웨이브를 막음)까지 가는 비율을 센다. 상점 선택 방법 2가지(아무거나 / 가장 좋은 것).
# 플레이 방법: 준비 단계마다 골드가 되는 만큼 스핀하고 전투를 시작한다.
# 실행 (앱 폴더에서): python tests/tools/simulate.py [판 수, 기본 300]
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

import game  # noqa: E402
from symbols import SOLDIERS  # noqa: E402

MAX_WAVES = 60   # 끝없이 이어지는 판을 막는 안전장치


def best_item(g, offer):
    """가장 좋은 것: 하트가 2 이하면 하트, 아니면 공격력 높은 총알 > 공격력 +10% > 첫 스핀 무료 > 하트."""
    def value(choice):
        item, bullet = choice
        if item == "하트 +1":
            return 100 if g.hearts <= 2 else 1
        if item == "총알 추가":
            return SOLDIERS[bullet]["dps"]
        if item == "공격력 +10%":
            return 20
        return 12
    return max(offer, key=value)


def play_one(rng, strategy):
    """한 판을 끝까지 자동으로 해서 (도달한 웨이브, 막은 웨이브 수)를 돌려준다."""
    g = game.Game()
    while g.wave <= MAX_WAVES:
        while g.can_spin():
            g.spin(rng)
        g.start_battle()
        while not g.battle_over:
            g.battle_step(0.05)
        if g.finish_wave() == "over":
            break
        offer = g.shop_offer(rng)
        g.apply_shop(*(best_item(g, offer) if strategy == "best" else rng.choice(offer)))
    return g.wave, g.cleared


def report(games):
    """전략마다 games판을 돌려 결과를 출력한다."""
    print("적 속도", game.ENEMY_SPEED, "+", game.SPEED_STEP, "× (웨이브-1), 최대", game.SPEED_MAX,
          "/ 적 간격", game.SPAWN_GAP, "초 / 1웨이브 병사 0명이면 지원군 훈련병★1 /", games, "판씩")
    for strategy, label in [("random", "상점에서 아무거나"), ("best", "상점에서 가장 좋은 것")]:
        rng = random.Random(2026)
        results = [play_one(rng, strategy) for _ in range(games)]
        waves = [w for w, _ in results]
        hasa = sum(1 for _, cleared in results if cleared >= 4)
        print(label)
        print("  평균 도달 웨이브", round(sum(waves) / games, 2), "/ 가장 짧게", min(waves), "/ 가장 길게", max(waves))
        print("  하사 도달(4웨이브 막음)", round(100 * hasa / games), "%",
              "/ 1웨이브 탈락", round(100 * sum(1 for w in waves if w == 1) / games), "%")


if __name__ == "__main__":
    report(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
