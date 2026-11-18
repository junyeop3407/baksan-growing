# 슬롯 디펜스 규칙 테스트 (docs/tests.md 2차 N1~N25). 화면 없이 game.py만으로 확인한다.
import pytest

import game
from test_game import FixedRng, board_of, clear_wave, run_battle

MISS = board_of("연보예", "철황연", "보예철")      # 줄 0개
SIX_DIFFERENT = [("연습탄", 1), ("보통탄", 1), ("예광탄", 1), ("철갑탄", 1), ("황금탄", 1), ("연습탄", 2)]


# ---- 준비 단계 ----

def test_n1_start_values():
    """N1: 시작은 골드 500, 하트 3, 병사 0, 웨이브 1."""
    g = game.Game()
    assert (g.gold, g.hearts, g.soldiers, g.wave) == (500, 3, [], 1)


def test_n2_spin_cost_rises_and_resets():
    """N2: 스핀 비용은 100 → 150 → 200, 다음 준비 단계에서 다시 100."""
    g = game.Game()
    g.gold = 10000
    costs = []
    for _ in range(3):
        costs.append(g.spin_cost())
        g.spin(FixedRng(MISS))
    assert costs == [100, 150, 200]
    clear_wave(g)
    assert g.spin_cost() == 100


def test_n3_exact_gold_can_spin():
    """N3: 골드가 스핀 비용과 정확히 같으면 스핀되고 골드 0."""
    g = game.Game()
    g.gold = 100
    assert g.can_spin()
    g.spin(FixedRng(MISS))
    assert g.gold == 0


def test_n4_one_short_cannot_spin():
    """N4: 골드가 1 모자라면 스핀 안 되고 골드는 그대로."""
    g = game.Game()
    g.gold = 99
    assert not g.can_spin()
    with pytest.raises(ValueError):
        g.spin(FixedRng(MISS))
    assert g.gold == 99


def test_n5_eight_lines_eight_summons():
    """N5: 한 스핀에 8줄이 모두 맞으면 8명을 소환한다 (합체 연쇄 뒤 ★3 2명)."""
    g = game.Game()
    summoned = g.spin(FixedRng(board_of("철철철", "철철철", "철철철")))
    assert len(summoned) == 8
    assert g.soldiers == [("철갑탄", 3), ("철갑탄", 3)]


def test_n6_miss_costs_gold():
    """N6: 꽝이면 소환은 없고 골드는 비용만큼 줄어든다."""
    g = game.Game()
    g.spin(FixedRng(MISS))
    assert g.soldiers == [] and g.gold == 400
    assert g.message == "꽝! 맞은 줄이 없습니다"


# ---- 병사와 합체 ----

def test_n7_six_slots():
    """N7: 병사 칸은 6개다."""
    assert game.SLOTS == 6
    g = game.Game()
    g.soldiers = list(SIX_DIFFERENT)
    g.summon("황금탄")
    assert len(g.soldiers) == 6


def test_n8_merge_two_ones():
    """N8: 같은 종류 ★1 + ★1 → ★2 1명."""
    g = game.Game()
    g.summon("보통탄")
    g.summon("보통탄")
    assert g.soldiers == [("보통탄", 2)]


def test_n9_merge_chain():
    """N9: ★2가 있을 때 ★1 + ★1 → ★2가 되고 다시 ★2와 합체해 ★3."""
    g = game.Game()
    g.soldiers = [("예광탄", 2), ("예광탄", 1)]
    assert g.summon("예광탄") == "merged"
    assert g.soldiers == [("예광탄", 3)]


def test_n10_threes_do_not_merge():
    """N10: ★3 + ★3은 합체하지 않는다 (두 명 그대로)."""
    g = game.Game()
    g.soldiers = [("연습탄", 3), ("연습탄", 2), ("연습탄", 1)]
    g.summon("연습탄")
    assert g.soldiers == [("연습탄", 3), ("연습탄", 3)]


def test_n11_full_without_partner_refunds():
    """N11: 칸 6명이 꽉 찼고 짝이 없으면 소환하지 않고 골드 +50, 안내 문구."""
    g = game.Game()
    g.soldiers = [("연습탄", 3), ("보통탄", 1), ("예광탄", 1), ("철갑탄", 1), ("황금탄", 1), ("연습탄", 2)]
    gold = g.gold
    assert g.summon("철갑탄") != "full"     # 철갑탄 ★1 짝이 있어 합체
    g.soldiers = list(SIX_DIFFERENT)
    g.soldiers[0] = ("보통탄", 3)
    assert g.summon("연습탄") == "full"
    assert g.gold == gold + 50
    assert len(g.soldiers) == 6
    assert g.message == "병사 칸이 꽉 찼습니다 (+50골드)"


def test_n12_full_with_partner_merges():
    """N12: 칸이 꽉 찼어도 짝이 있으면 합체해서 들어간다."""
    g = game.Game()
    g.soldiers = list(SIX_DIFFERENT)
    assert g.summon("보통탄") == "merged"
    assert len(g.soldiers) == 6
    assert ("보통탄", 2) in g.soldiers


def test_n13_attack_power():
    """N13: 초당 공격력 5/10/15/25/40, 별 ×1/×2/×4, 공격력 +10% 두 번이면 ×1.2."""
    g = game.Game()
    assert [g.soldier_dps((kind, 1)) for kind in ["연습탄", "보통탄", "예광탄", "철갑탄", "황금탄"]] == [5, 10, 15, 25, 40]
    assert [g.soldier_dps(("보통탄", star)) for star in (1, 2, 3)] == [10, 20, 40]
    g.apply_shop("공격력 +10%")
    g.apply_shop("공격력 +10%")
    assert g.soldier_dps(("보통탄", 1)) == pytest.approx(12)


# ---- 전투 ----

def test_n14_wave_enemies():
    """N14: 웨이브 n 적 수 5 + 2n, 체력 20 × 1.2^(n-1) (소수점 버림)."""
    assert [game.enemy_count(n) for n in (1, 2, 3)] == [7, 9, 11]
    assert [game.enemy_hp(n) for n in (1, 2, 3)] == [20, 24, 28]


def test_n15_boss_every_five():
    """N15: 5웨이브에는 보스 1명이 더 나오고 체력은 일반 적의 10배, 4웨이브엔 없다."""
    g = game.Game()
    g.wave = 4
    g.start_battle()
    assert not any(boss for _, boss in g.queue)
    g.wave = 5
    g.start_battle()
    bosses = [hp for hp, boss in g.queue if boss]
    assert bosses == [game.enemy_hp(5) * 10]
    assert len(g.queue) == game.enemy_count(5) + 1


def single_enemy_battle(g, boss, x=0.5):
    """방어선 바로 앞에 적 한 명만 있는 전투를 만든다."""
    g.start_battle()
    g.queue = []
    g.enemies = [{"hp": 10 ** 6, "max_hp": 10 ** 6, "x": x, "boss": boss}]


def test_n16_boss_leak_at_one_heart():
    """N16: 하트 1에서 보스가 방어선을 지나가면 하트 -1(0 이하) → 게임 오버."""
    g = game.Game()
    g.hearts = 1
    single_enemy_battle(g, boss=True)
    g.battle_step(0.2)
    assert g.hearts == -1
    assert g.battle_over
    assert g.finish_wave() == "over"


def test_n17_normal_leak():
    """N17: 일반 적이 지나가면 하트 -1."""
    g = game.Game()
    single_enemy_battle(g, boss=False)
    g.battle_step(0.2)
    assert g.hearts == 2


def test_n18_shoot_closest_to_line():
    """N18: 병사는 방어선에 가장 가까운 적을 쏜다."""
    g = game.Game()
    g.soldiers = [("보통탄", 1)]
    g.start_battle()
    g.queue = []
    g.enemies = [{"hp": 100, "max_hp": 100, "x": 50.0, "boss": False},
                 {"hp": 100, "max_hp": 100, "x": 30.0, "boss": False}]
    g.battle_step(1.0)
    far, near = g.enemies
    assert near["hp"] == pytest.approx(90) and far["hp"] == 100


def test_n19_no_soldiers_everyone_leaks():
    """N19: 병사 0명으로 전투하면 적이 모두 지나가고(처치 0), 하트가 남으면 웨이브는 끝난다."""
    g = game.Game()
    g.hearts = 9
    run_battle(g)
    assert g.kills == 0 and g.hearts == 2
    assert g.finish_wave() == "clear"


def test_n20_kill_everyone():
    """N20: 적을 모두 처치하면 웨이브가 끝나고 처치 수가 맞다."""
    g = game.Game()
    g.soldiers = [("황금탄", 3)] * 6
    run_battle(g)
    assert g.kills == 7 and g.hearts == 3


def test_n21_step_size_does_not_change_result():
    """N21: battle_step은 화면 없이 돌고, 같은 시간을 더 잘게 나눠도 결과(처치·하트)가 같다."""
    results = []
    for dt in (0.1, 0.05):
        g = game.Game()
        g.soldiers = [("보통탄", 2), ("예광탄", 1)]
        run_battle(g, dt)
        results.append((g.kills, g.hearts))
    assert results[0] == results[1]


# ---- 보상과 상점 ----

def test_n22_wave_reward():
    """N22: 웨이브 끝 골드 +200 + 처치 × 10."""
    g = game.Game()
    gold = g.gold
    clear_wave(g)
    assert g.gold == gold + 200 + 7 * 10


def test_n23_heart_cap():
    """N23: 하트 +1은 최대 5, 5에서 고르면 그대로 5."""
    g = game.Game()
    g.apply_shop("하트 +1")
    assert g.hearts == 4
    g.hearts = 5
    g.apply_shop("하트 +1")
    assert g.hearts == 5


def test_n24_attack_bonus_stacks():
    """N24: 공격력 +10%는 쌓인다."""
    g = game.Game()
    for _ in range(3):
        g.apply_shop("공격력 +10%")
    assert g.soldier_dps(("황금탄", 1)) == pytest.approx(52)


def test_n25_free_first_spin():
    """N25: 첫 스핀 무료 → 다음 준비 단계 첫 스핀 0, 그다음 150."""
    g = game.Game()
    clear_wave(g)
    g.apply_shop("첫 스핀 무료")
    gold = g.gold
    assert g.spin_cost() == 0
    g.spin(FixedRng(MISS))
    assert g.gold == gold
    assert g.spin_cost() == 150
