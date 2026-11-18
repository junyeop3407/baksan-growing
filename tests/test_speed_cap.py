# 적 속도 상한 (2026-11-18 사장 판단): 어느 웨이브에서도 적이 방어선까지 걸리는 시간이 3초 이상.
# 근거: 전장 길이 FIELD = 100, 3초 이상이려면 속도 ≤ 100 / 3 ≈ 33.3 → 상한 33 (100 / 33 ≈ 3.03초).
# 속도 = 5 + 10 × (웨이브 − 1): 3웨이브 25(4초) → 4웨이브부터 상한 33.
import game


def test_s1_speed_before_cap():
    """S1: 상한 직전(3웨이브)은 25로 상한보다 느리다 → 4초."""
    assert game.enemy_speed(3) == 25
    assert game.FIELD / game.enemy_speed(3) == 4


def test_s2_speed_at_cap():
    """S2: 상한 직후(4·5웨이브)는 33에서 멈춘다."""
    assert game.SPEED_MAX == 33
    assert game.enemy_speed(4) == 33
    assert game.enemy_speed(5) == 33


def test_s3_very_high_wave_still_three_seconds():
    """S3: 아주 높은 웨이브(1000)도 33, 1~1000웨이브 모두 방어선까지 3초 이상."""
    assert game.enemy_speed(1000) == 33
    assert all(game.FIELD / game.enemy_speed(n) >= 3 for n in range(1, 1001))


def test_s4_enemy_takes_three_seconds_in_battle():
    """S4: 실제 전투에서도 높은 웨이브 적이 나온 뒤 2.9초엔 하트 그대로, 3.1초 안에 지나가 하트 -1."""
    g = game.Game()
    g.wave = 99
    g.start_battle()
    g.queue = g.queue[:1]   # 적 1명만
    for _ in range(29):
        g.battle_step(0.1)
    assert g.hearts == game.START_HEARTS
    g.battle_step(0.2)
    assert g.hearts == game.START_HEARTS - 1
