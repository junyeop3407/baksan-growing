# 화면 테스트 (docs/tests.md의 E1, C4 화면 부분, F1~F6, G1~G6, H1~H4).
# 화면 전환·버튼 상태·문구만 확인하고 그림 픽셀은 비교하지 않는다. 시간은 time_scale로 빨리 감는다.
import tkinter as tk
import tkinter.font as tkfont

import pytest

import character
import db
import ui
from helpers import PatternRng, pump, start, play_round, wait_until

FAST = 0.01


@pytest.fixture
def make_app(tk_root, tmp_path):
    def make(pattern=PatternRng.WEAK, time_scale=FAST):
        return ui.App(tk_root, str(tmp_path / "game.db"), rng=PatternRng(pattern), time_scale=time_scale)
    return make


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


# ---- E1, C4 ----

def test_e1_min_window_keeps_cells_big(make_app):
    """E1: 창이 가장 작을 때도 칸이 80px 이상이고 게임 화면이 창 안에 들어간다."""
    app = make_app()
    start(app)
    assert app.root.minsize() == (ui.MIN_W, ui.MIN_H)
    assert ui.CELL >= 80
    assert ui.CANVAS_W <= ui.MIN_W and ui.CANVAS_H <= ui.MIN_H
    assert int(app.canvas["width"]) == ui.CANVAS_W


def test_c4_empty_ranking_screen(make_app):
    """C4: 기록이 0개면 랭킹 화면은 빈 표 + "아직 기록이 없습니다"."""
    app = make_app()
    app.ranking_button.invoke()
    assert app.screen == "ranking"
    assert app.ranking_tree.get_children() == ()
    assert app.ranking_message["text"] == "아직 기록이 없습니다"


# ---- F. 말풍선 ----

def bubble_texts(app):
    return [app.canvas.itemcget(i, "text") for i in app.canvas.find_withtag("bubble")
            if app.canvas.type(i) == "text"]


def test_f1_bubble_disappears(make_app):
    """F1: 말풍선은 약 2.5초 뒤 사라진다."""
    assert ui.BUBBLE_MS == 2500
    app = make_app()
    start(app)
    app.show_bubble("안녕")
    assert bubble_texts(app) == ["안녕"]
    pump(app, ui.BUBBLE_MS * FAST + 100)
    assert bubble_texts(app) == []


def test_f2_new_bubble_replaces_old(make_app):
    """F2: 말풍선 두 개가 연달아 뜨면 앞의 것은 바로 지워지고 하나만 남는다."""
    app = make_app()
    start(app)
    app.show_bubble("첫째")
    app.show_bubble("둘째")
    assert bubble_texts(app) == ["둘째"]


@pytest.mark.parametrize("text", ["난 최산을 닮았다", "난 섹시해.... ㅋ", "she's so BAD..."])
def test_f3_bubble_stays_in_its_area(make_app, text):
    """F3: 말풍선은 창 안에 있고 계급장·슬롯판과 겹치지 않는다 (가장 작은 창 기준 Canvas)."""
    app = make_app()
    start(app)
    app.show_bubble(text)
    bubble = app.canvas.bbox("bubble")
    assert bubble[0] >= 0 and bubble[1] >= 0 and bubble[2] <= ui.CANVAS_W and bubble[3] <= ui.CANVAS_H
    assert not overlaps(bubble, app.canvas.bbox("hero&&badge"))
    assert not overlaps(bubble, app.canvas.bbox("board"))
    for _, pose in character.DANCE_STEPS:
        app.draw_hero(pose)
        assert not overlaps(bubble, app.canvas.bbox("hero&&badge"))


def test_f4_spin_mashing_counts_once(make_app):
    """F4: 말풍선이 떠 있는 동안 스핀을 빠르게 5번 눌러도 한 번만 처리된다."""
    app = make_app()
    start(app)
    app.show_bubble("난 섹시해.... ㅋ")
    for _ in range(5):
        app.spin_button.invoke()
    assert app.spin_button["state"] == "disabled"
    wait_until(app, lambda: not app.busy)
    assert app.game.spins_left == 4
    assert app.spin_button["state"] == "normal"


def test_f5_sexy_bubble_from_round_two(make_app):
    """F5: 1라운드 시작에는 말풍선이 없고, 2라운드 시작 때 "난 섹시해.... ㅋ"."""
    app = make_app(PatternRng.STRONG)
    start(app)
    assert bubble_texts(app) == []
    play_round(app)
    assert app.screen == "shop"
    app.shop_buttons[0].invoke()
    assert app.screen == "game" and app.game.round_no == 2
    assert bubble_texts(app) == ["난 섹시해.... ㅋ"]


def test_f6_gameover_bubble(make_app):
    """F6: 게임 오버 화면에 "she's so BAD..."."""
    app = make_app(PatternRng.WEAK)
    start(app)
    play_round(app)
    assert app.screen == "gameover"
    assert bubble_texts(app) == ["she's so BAD..."]


# ---- G. 춤 ----

def test_g1_pass_starts_dance_and_blocks_spin(make_app):
    """G1: 라운드 통과 → 춤 + "난 최산을 닮았다", 춤 동안 스핀 버튼이 막힌다."""
    app = make_app(PatternRng.STRONG, time_scale=0.2)
    start(app)
    for _ in range(5):
        wait_until(app, lambda: not app.busy)
        app.spin_button.invoke()
    wait_until(app, lambda: app.dancing)
    assert bubble_texts(app) == ["난 최산을 닮았다"]
    assert app.spin_button["state"] == "disabled"


def test_g2_dance_then_shop(make_app):
    """G2: 춤은 약 3초이고, 끝나면 상점 화면으로 넘어간다."""
    total = sum(ms for ms, _ in character.DANCE_STEPS)
    assert 2800 <= total <= 3300
    app = make_app(PatternRng.STRONG)
    start(app)
    play_round(app)
    assert app.screen == "shop"
    assert not app.dancing


def test_g3_close_during_dance(tmp_path):
    """G3: 춤 도중 창을 닫으면 오류 없이 끝나고 남은 예약이 없다."""
    root = tk.Tk()
    root.withdraw()
    app = ui.App(root, str(tmp_path / "game.db"), rng=PatternRng(PatternRng.WEAK), time_scale=1.0)
    start(app)
    app.show_bubble("난 최산을 닮았다")
    assert app.start_dance(lambda: None)
    pump(app, 300)
    assert app.dancing
    app.close()
    assert app.after_ids == set()


def test_g4_no_overlapping_dance(make_app):
    """G4: 춤 도중 다시 춤을 시작하라고 해도 겹치지 않는다."""
    app = make_app(time_scale=0.05)
    start(app)
    done = []
    assert app.start_dance(lambda: done.append(1)) is True
    assert app.start_dance(lambda: done.append(2)) is False
    wait_until(app, lambda: not app.dancing)
    pump(app, 100)
    assert done == [1]


def test_g5_badge_moves_with_head(tk_root):
    """G5: 춤의 모든 자세에서 계급장은 머리와 같은 만큼 움직인다."""
    c = tk.Canvas(tk_root, width=400, height=500)
    character.draw_character(c, 0, 0, 0.5, "상병", tag="still")
    for _, pose in character.DANCE_STEPS:
        c.delete("moved")
        character.draw_character(c, 0, 0, 0.5, "상병", pose=pose, tag="moved")
        head_shift = c.bbox("moved&&head")[1] - c.bbox("still&&head")[1]
        badge_shift = c.bbox("moved&&badge")[1] - c.bbox("still&&badge")[1]
        assert head_shift == badge_shift


def test_g6_resize_during_dance(make_app):
    """G6: 춤 도중 창 크기를 바꿔도 오류가 없다."""
    app = make_app(time_scale=0.1)
    start(app)
    done = []
    app.start_dance(lambda: done.append(1))
    app.root.geometry("1200x800")
    pump(app, 50)
    app.root.geometry(str(ui.MIN_W) + "x" + str(ui.MIN_H))
    wait_until(app, lambda: not app.dancing)
    assert done == [1]


def test_dance_poses_stay_inside_area(tk_root):
    """춤의 모든 자세에서 캐릭터가 자기 영역 안에 있다 (G 보충)."""
    c = tk.Canvas(tk_root, width=400, height=500)
    for _, pose in character.DANCE_STEPS:
        c.delete("all")
        character.draw_character(c, 10, 10, 1.0, "하사", pose=pose, tag="x")
        x0, y0, x1, y1 = c.bbox("x")
        assert x0 >= 10 and y0 >= 10 and x1 <= 10 + character.WIDTH and y1 <= 10 + character.HEIGHT


# ---- H. 화면 흐름 ----

def test_h1_title(make_app):
    """H1: 창 제목과 시작 화면 제목이 "박산 키우기"."""
    app = make_app()
    assert app.root.title() == "박산 키우기"
    assert app.title_label["text"] == "박산 키우기"


def test_h2_one_full_game(make_app, tmp_path):
    """H2: 한 판 끝까지(탈락 고정) → 게임 오버 화면 문구, DB에 1개 저장."""
    app = make_app(PatternRng.WEAK)
    start(app, "한판")
    play_round(app)
    assert app.screen == "gameover"
    text = " ".join(app.result_lines)
    assert "65" in text and "1" in text and "이병" in text
    assert app.save_message == "기록이 DB에 저장되었습니다"
    rows = db.get_top10(str(tmp_path / "game.db"))
    assert [(r["name"], r["score"], r["round_reached"], r["growth_stage"]) for r in rows] == [("한판", 65, 1, "이병")]


def test_h3_ranking_columns(make_app):
    """H3: 랭킹 화면 열은 순위 / 이름 / 점수 / 라운드 / 계급 / 플레이 날짜."""
    app = make_app()
    app.ranking_button.invoke()
    tree = app.ranking_tree
    headings = [tree.heading(col)["text"] for col in tree["columns"]]
    assert headings == ["순위", "이름", "점수", "라운드", "계급", "플레이 날짜"]


def test_h4_retry_same_name(make_app):
    """H4: [다시하기] → 같은 이름, 1라운드, 이병."""
    app = make_app(PatternRng.WEAK)
    start(app, "다시")
    play_round(app)
    app.retry_button.invoke()
    assert app.screen == "game"
    assert app.player_name == "다시"
    assert (app.game.round_no, app.game.rank, app.game.total_score) == (1, "이병", 0)


# ---- 사장 요청 경계값 (이름·랭킹 표·시작 화면) ----

def test_bad_name_stays_on_start(make_app):
    """이름이 비면 시작 화면에 머물고 안내 문구를 보여 준다."""
    app = make_app()
    start(app, "   ")
    assert app.screen == "start"
    assert app.name_message["text"] == "이름을 1~10글자로 입력해 주세요."


def test_ten_char_name_fits_ranking_column(make_app, tmp_path):
    """10글자 한글·영어·숫자 섞인 이름이 랭킹 표 이름 칸에서 잘리지 않는다. 동점은 먼저 한 기록이 위."""
    path = str(tmp_path / "game.db")
    app = make_app()
    names = ["가나다라마바사아자차", "WWWWWWWWWW", "박산a1박산a1박산"]
    for i, name in enumerate(names):
        db.save_record(path, name, 2, 500, "일병", played_at="2026-11-18 10:00:0" + str(i))
    app.ranking_button.invoke()
    tree = app.ranking_tree
    rows = [tree.item(item)["values"] for item in tree.get_children()]
    assert [str(r[1]) for r in rows] == names
    assert [r[0] for r in rows] == [1, 2, 3]
    font = tkfont.Font(family=ui.FONT, size=ui.TABLE_FONT_SIZE)
    width = int(tree.column("name")["width"])
    for name in names:
        assert font.measure(name) + 16 <= width


# ---- 사장 추가 요청 (말풍선 유지 시간, 시작 화면 이름) ----

def test_pass_bubble_lasts_until_dance_ends(make_app):
    """라운드 통과 말풍선은 2.5초가 지나도 춤이 끝날 때까지 남아 있고, 춤이 끝나면 같이 지워진다."""
    app = make_app(time_scale=0.5)
    start(app)
    app.start_dance(lambda: None)
    pump(app, ui.BUBBLE_MS * 0.5 + 150)
    assert app.dancing
    assert bubble_texts(app) == ["난 최산을 닮았다"]
    wait_until(app, lambda: not app.dancing)
    assert bubble_texts(app) == []


def test_gameover_bubble_stays(make_app):
    """게임 오버 말풍선은 사라지지 않고 계속 보이며, 화면을 떠나면 지워진다."""
    app = make_app(PatternRng.WEAK)
    start(app)
    play_round(app)
    pump(app, ui.BUBBLE_MS * FAST + 150)
    assert bubble_texts(app) == ["she's so BAD..."]
    app.menu_button.invoke()
    assert app.screen == "start"
    assert app.bubble_text == ""


@pytest.mark.parametrize("name", ["", "   ", "가나다라마바사아자차카"])
def test_start_rejects_bad_names(make_app, name):
    """빈 이름·공백만·11글자면 안내 문구가 뜨고 게임 화면으로 넘어가지 않는다."""
    app = make_app()
    start(app, name)
    assert app.screen == "start"
    assert app.name_message["text"] == "이름을 1~10글자로 입력해 주세요."


@pytest.mark.parametrize("name", ["박", "가나다라마바사아자차"])
def test_start_accepts_good_names(make_app, name):
    """1글자·10글자 이름은 게임이 시작된다."""
    app = make_app()
    start(app, name)
    assert app.screen == "game"
    assert app.player_name == name
