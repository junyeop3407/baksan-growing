# 총알(심볼) 5종과 총알마다 소환되는 병사, 박산 계급 5단계를 정의하고, 총알 도트 그림을 Canvas에 놓는 함수를 둔다.
# tkinter를 import하지 않아 game.py가 화면 없이도 이 파일을 쓸 수 있다.

# 총알 순서 (병사 공격력이 낮은 것부터)
BULLET_ORDER = ["연습탄", "보통탄", "예광탄", "철갑탄", "황금탄"]

# 총알마다 모양
#   tip: 탄두 색, tip_end: 탄두 끝 색, case: 탄피 색, pointy: 뾰족한 탄두인지
BULLETS = {
    "연습탄": {"tip": "#3a6fd8", "tip_end": "#3a6fd8", "case": "#c9a64a", "pointy": False},
    "보통탄": {"tip": "#b8693a", "tip_end": "#b8693a", "case": "#d4b04c", "pointy": False},
    "예광탄": {"tip": "#b8693a", "tip_end": "#e02020", "case": "#d4b04c", "pointy": False},
    "철갑탄": {"tip": "#7a7f87", "tip_end": "#111111", "case": "#d4b04c", "pointy": True},
    "황금탄": {"tip": "#f5c518", "tip_end": "#f5c518", "case": "#e8b923", "pointy": False},
}

# 총알마다 소환되는 병사: 이름과 ★1 초당 공격력 (기획서 3) "총알 = 병사")
SOLDIERS = {
    "연습탄": {"name": "훈련병", "dps": 5},
    "보통탄": {"name": "소총병", "dps": 10},
    "예광탄": {"name": "기관총병", "dps": 15},
    "철갑탄": {"name": "저격병", "dps": 25},
    "황금탄": {"name": "특급전사", "dps": 40},
}

# 처음 덱에 들어 있는 총알 개수 (황금탄은 상점에서만 얻는다)
START_DECK = {"연습탄": 4, "보통탄": 3, "예광탄": 2, "철갑탄": 1}

# 박산 계급: (이름, 얼굴의 최산 비율). 웨이브를 막을 때마다 한 칸씩 오른다.
RANKS = [("이병", 0.0), ("일병", 0.25), ("상병", 0.5), ("병장", 0.75), ("하사", 1.0)]

# 같은 총알 3개가 맞은 줄을 강조하는 테두리 두께(px)
HIGHLIGHT_WIDTH = 4
HIGHLIGHT_COLOR = "#ffd60a"


def draw_bullet(canvas, kind, x, y, size, tag=""):
    """(x, y)에서 시작하는 size×size 칸 안에 총알 도트 그림과 이름 글자를 그린다.
    도트 배율은 칸 높이의 약 60%가 되게 고르되, 줄 강조 테두리 안쪽을 넘지 않게 한다."""
    import pixel_art   # 화면을 그릴 때만 불러온다 (game.py는 tkinter 없이 이 파일을 쓴다)
    margin = HIGHLIGHT_WIDTH + 3
    label_px = max(14, size // 7)
    canvas.create_text(x + size / 2, y + size - margin, text=kind, anchor="s",
                       font=("Malgun Gothic", -label_px, "bold"), fill="#1a1a1a", tags=tag)
    area_bottom = y + size - margin - label_px * 1.45 - 2   # 글자 줄 높이만큼 비워 둔다
    room = area_bottom - (y + HIGHLIGHT_WIDTH)              # 강조 테두리 안쪽부터 쓸 수 있는 높이
    scale = max(1, min(round(size * 0.62 / 16), int(room // 16)))
    img = pixel_art.photo(canvas, ("bullet", kind), lambda: pixel_art.bullet_icon(kind), scale)
    canvas.create_image(x + size / 2, area_bottom, image=img, anchor="s", tags=tag)


def draw_highlight(canvas, x, y, size, tag=""):
    """칸 가장자리에만 노란 테두리를 그려 맞은 줄을 강조한다 (총알 그림은 가리지 않음)."""
    half = HIGHLIGHT_WIDTH / 2
    canvas.create_rectangle(x + half, y + half, x + size - half, y + size - half,
                            outline=HIGHLIGHT_COLOR, width=HIGHLIGHT_WIDTH, tags=tag)
