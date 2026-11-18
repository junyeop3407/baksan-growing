# 상점 총알 카드 문구 (2026-11-18 사장 수정 지시): 그림 아래 제목(총알 이름)과 겹치지 않게
# 카드의 굵은 줄은 "총알 추가: 보통탄" 대신 "덱에 추가". 콘솔 한 판의 shop_label은 그대로(그림이 없어서).
import game
import ui
from helpers import PatternRng, start


def label_texts(widget):
    """widget 안의 모든 Label 글자."""
    texts = []
    for child in widget.winfo_children():
        if child.winfo_class() == "Label":
            texts.append(child.cget("text"))
        texts.extend(label_texts(child))
    return texts


def test_bullet_card_says_add_to_deck(tk_root, tmp_path):
    app = ui.App(tk_root, str(tmp_path / "game.db"), rng=PatternRng(PatternRng.WEAK), time_scale=0.01)
    start(app)
    app.game.shop_offer = lambda rng: [("총알 추가", "보통탄"), ("하트 +1", None), ("공격력 +10%", None)]
    app.show_shop()
    texts = label_texts(app.frame)
    assert "덱에 추가" in texts
    assert not any(t.startswith("총알 추가:") for t in texts)
    assert "하트 +1" in texts and "공격력 +10%" in texts


def test_console_label_unchanged():
    assert game.shop_label("총알 추가", "철갑탄") == "총알 추가: 철갑탄"
