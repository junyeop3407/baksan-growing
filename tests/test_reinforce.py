# 1웨이브 지원군 (2026-11-19 사장 승인 D안): 1웨이브를 병사 0명으로 시작하면 훈련병★1 한 명이 온다.
# 경계: 1웨이브에 병사가 1명 이상이면 지원군 없음 / 2웨이브 이후에는 0명이어도 지원군 없음. 적 간격 0.30초.
import game
import ui
from helpers import PatternRng, start, spin_all, wait_until


def test_r1_wave1_no_soldiers_gets_reinforcement():
    g = game.Game()
    g.start_battle()
    assert g.soldiers == [("연습탄", 1)]
    assert g.message.startswith("지원군 도착!")
    assert g.reinforced is True


def test_r2_wave1_with_soldier_no_reinforcement():
    g = game.Game()
    g.soldiers = [("보통탄", 1)]
    g.start_battle()
    assert g.soldiers == [("보통탄", 1)]
    assert "지원군" not in g.message and g.reinforced is False


def test_r3_wave2_no_soldiers_no_reinforcement():
    g = game.Game()
    g.wave = 2
    g.start_battle()
    assert g.soldiers == [] and g.reinforced is False


def test_r4_spawn_gap():
    assert game.SPAWN_GAP == 0.30


def test_r5_reinforcement_shown_on_screen(tk_root, tmp_path):
    """화면: 꽝만 나와 병사 0명으로 [전투 시작] → 안내 문구 "지원군 도착!"과 훈련병 칸이 보인다."""
    app = ui.App(tk_root, str(tmp_path / "g.db"), rng=PatternRng(PatternRng.WEAK), time_scale=1.0)
    start(app)
    spin_all(app)
    app.battle_button.invoke()
    texts = [app.canvas.itemcget(i, "text") for i in app.canvas.find_withtag("msg")]
    assert any(t.startswith("지원군 도착!") for t in texts)
    assert len(app.canvas.find_withtag("soldier_sprite")) == 1
    app.cancel_all()
