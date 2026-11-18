# 자동 한 판 (사장 요청 4번, 2차 N29·N30): 무작위를 고정해 버튼을 눌러 끝까지 진행하고 DB 기록을 확인한다.
import db
import ui
from helpers import PatternRng, play_round, start


def test_autoplay_fail_first_wave(tk_root, tmp_path):
    """① 1웨이브에서 탈락(꽝만 나와 병사 0명): 오류 없이 게임 오버, DB round_reached에 웨이브 1·이병 기록."""
    path = str(tmp_path / "game.db")
    app = ui.App(tk_root, path, rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app, "자동1")
    play_round(app)
    assert app.screen == "gameover"
    rows = db.get_top10(path)
    assert [(r["name"], r["round_reached"], r["growth_stage"]) for r in rows] == [("자동1", 1, "이병")]


def test_autoplay_reach_hasa_then_fail(tk_root, tmp_path):
    """② STRONG으로 4웨이브를 막아 하사 → 병사를 비우고 WEAK로 5웨이브 탈락: DB에 웨이브 5·하사 기록."""
    path = str(tmp_path / "game.db")
    rng = PatternRng(PatternRng.STRONG)
    app = ui.App(tk_root, path, rng=rng, time_scale=0.01)
    start(app, "자동2")
    ranks = []
    for _ in range(4):
        play_round(app)
        assert app.screen == "shop"
        ranks.append(app.game.rank)
        app.shop_buttons[0].invoke()
    assert ranks == ["일병", "상병", "병장", "하사"]
    assert app.game.face_ratio == 1.0
    rng.pattern = PatternRng.WEAK
    rng.i = 0                      # 상점에서 choice()를 쓴 만큼 어긋난 순서를 맞춰 9칸이 늘 꽝이 되게 한다
    app.game.soldiers = []
    play_round(app)
    assert app.screen == "gameover"
    assert app.game.rank == "하사"
    rows = db.get_top10(path)
    assert [(r["name"], r["round_reached"], r["growth_stage"]) for r in rows] == [("자동2", 5, "하사")]
