# 자동 한 판 (사장 요청 4번): 무작위를 고정해 버튼을 눌러 끝까지 진행하고 DB 기록을 확인한다.
import db
import ui
from helpers import PatternRng, play_round, start


def test_autoplay_fail_first_round(tk_root, tmp_path):
    """① 1라운드에서 탈락: 오류 없이 게임 오버, DB에 1라운드·이병 기록."""
    path = str(tmp_path / "game.db")
    app = ui.App(tk_root, path, rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app, "자동1")
    play_round(app)
    assert app.screen == "gameover"
    rows = db.get_top10(path)
    assert [(r["name"], r["round_reached"], r["growth_stage"]) for r in rows] == [("자동1", 1, "이병")]


def test_autoplay_reach_hasa_then_fail(tk_root, tmp_path):
    """② 하사 도달 후 탈락: 4번 통과로 하사, 5번째 통과 뒤에도 하사·얼굴 100%, 6라운드 탈락 기록."""
    path = str(tmp_path / "game.db")
    rng = PatternRng(PatternRng.STRONG)
    app = ui.App(tk_root, path, rng=rng, time_scale=0.01)
    start(app, "자동2")
    ranks = []
    for _ in range(5):
        play_round(app)
        assert app.screen == "shop"
        ranks.append(app.game.rank)
        app.shop_buttons[0].invoke()
    assert ranks == ["일병", "상병", "병장", "하사", "하사"]
    assert app.game.face_ratio == 1.0
    rng.pattern = PatternRng.WEAK
    play_round(app)
    assert app.screen == "gameover"
    assert app.game.rank == "하사"
    rows = db.get_top10(path)
    assert [(r["name"], r["round_reached"], r["growth_stage"]) for r in rows] == [("자동2", 6, "하사")]
