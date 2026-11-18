# 총알(심볼) 5종과 박산 계급 5단계를 정의하고, 총알을 Canvas에 그리는 함수를 둔다.
# tkinter를 import하지 않아 game.py가 화면 없이도 이 파일을 쓸 수 있다.

# 총알 순서 (점수가 낮은 것부터)
BULLET_ORDER = ["연습탄", "보통탄", "예광탄", "철갑탄", "황금탄"]

# 총알마다 점수와 모양
#   length: 칸 안 그림 영역 높이에 대한 총알 길이 비율
#   tip: 탄두 색, tip_end: 탄두 끝 색, case: 탄피 색, pointy: 뾰족한 탄두인지
BULLETS = {
    "연습탄": {"points": 1, "length": 0.6, "tip": "#3a6fd8", "tip_end": "#3a6fd8", "case": "#c9a64a", "pointy": False},
    "보통탄": {"points": 2, "length": 0.8, "tip": "#b8693a", "tip_end": "#b8693a", "case": "#d4b04c", "pointy": False},
    "예광탄": {"points": 3, "length": 0.8, "tip": "#b8693a", "tip_end": "#e02020", "case": "#d4b04c", "pointy": False},
    "철갑탄": {"points": 5, "length": 1.0, "tip": "#7a7f87", "tip_end": "#111111", "case": "#d4b04c", "pointy": True},
    "황금탄": {"points": 8, "length": 0.85, "tip": "#f5c518", "tip_end": "#f5c518", "case": "#e8b923", "pointy": False},
}

# 처음 덱에 들어 있는 총알 개수 (황금탄은 상점에서만 얻는다)
START_DECK = {"연습탄": 4, "보통탄": 3, "예광탄": 2, "철갑탄": 1}

# 박산 계급: (이름, 얼굴의 최산 비율). 라운드를 통과할 때마다 한 칸씩 오른다.
RANKS = [("이병", 0.0), ("일병", 0.25), ("상병", 0.5), ("병장", 0.75), ("하사", 1.0)]

# 같은 총알 3개가 맞은 줄을 강조하는 테두리 두께(px)
HIGHLIGHT_WIDTH = 4
HIGHLIGHT_COLOR = "#ffd60a"
OUTLINE = "#2b2b2b"


def draw_bullet(canvas, kind, x, y, size, tag=""):
    """(x, y)에서 시작하는 size×size 칸 안에 총알 그림과 이름 글자를 그린다."""
    info = BULLETS[kind]
    margin = HIGHLIGHT_WIDTH + 4
    label_px = max(11, size // 8)
    canvas.create_text(x + size / 2, y + size - margin, text=kind, anchor="s",
                       font=("Malgun Gothic", -label_px, "bold"), fill="#1a1a1a", tags=tag)

    area_top = y + margin
    area_bottom = y + size - margin - label_px - 6
    height = (area_bottom - area_top) * info["length"]
    width = max(10, size * 0.2)
    cx = x + size / 2
    left, right = cx - width / 2, cx + width / 2

    case_h = height * (0.45 if info["pointy"] else 0.55)
    case_top = area_bottom - case_h
    tip_h = height - case_h
    top = case_top - tip_h

    # 탄피와 아래쪽 테
    canvas.create_rectangle(left, case_top, right, area_bottom, fill=info["case"], outline=OUTLINE, tags=tag)
    canvas.create_line(left, area_bottom - 3, right, area_bottom - 3, fill=OUTLINE, tags=tag)

    # 탄두: 뾰족한 것은 직선, 나머지는 둥글게
    if info["pointy"]:
        tip_points = [left, case_top, left + width * 0.08, case_top - tip_h * 0.35, cx, top,
                      right - width * 0.08, case_top - tip_h * 0.35, right, case_top]
        canvas.create_polygon(tip_points, fill=info["tip"], outline=OUTLINE, tags=tag)
    else:
        tip_points = [left, case_top, left, case_top - tip_h * 0.45, cx, top,
                      right, case_top - tip_h * 0.45, right, case_top]
        canvas.create_polygon(tip_points, fill=info["tip"], outline=OUTLINE, smooth=True, tags=tag)

    # 탄두 끝 색 (예광탄 빨강, 철갑탄 검정)
    if info["tip_end"] != info["tip"]:
        end_h = tip_h * 0.4
        canvas.create_polygon(cx - width * 0.22, top + end_h, cx, top, cx + width * 0.22, top + end_h,
                              fill=info["tip_end"], outline=info["tip_end"], tags=tag)


def draw_highlight(canvas, x, y, size, tag=""):
    """칸 가장자리에만 노란 테두리를 그려 맞은 줄을 강조한다 (총알 그림은 가리지 않음)."""
    half = HIGHLIGHT_WIDTH / 2
    canvas.create_rectangle(x + half, y + half, x + size - half, y + size - half,
                            outline=HIGHLIGHT_COLOR, width=HIGHLIGHT_WIDTH, tags=tag)
