# 박산 캐릭터를 tkinter Canvas에 도트 그림(pixel_art)으로 그린다 (사진·이미지 파일 없음).
# 얼굴은 계급마다 성재 → 최산으로 부위 하나씩 바뀐다 (pixel_art.blend_face).
# 몸통·왼팔·오른팔·머리·계급장·지휘대를 따로 놓고 태그를 붙여, 춤출 때 도트 프레임을 바꿔 끼운다.
import pixel_art as pa
from symbols import RANKS

# 캐릭터 한 명이 차지하는 영역 (scale=1일 때, px)
WIDTH = 240
HEIGHT = 360

# 춤이 아닌 기본 자세. body_dy는 몸통(팔 포함), head_dy는 머리(계급장 포함)가 위로 올라가는 px(scale=1 기준,
# 도트 칸 단위로 반올림). 머리는 head_dy만큼만 움직인다(몸통이 올라가도 머리는 반 박자 늦게 따라온다).
# 팔 그림(도트 프레임): arm_raise < 0.5 내림 / 가슴 앞 / hand_drop > 0이면 툭 내림 / body_grow ≥ 0.08이면 크게.
# body_grow > 0이면 가슴을 넓힌 몸통 그림.
DEFAULT_POSE = {"arm_raise": 0.0, "hand_drop": 0.0, "body_dy": 0.0, "body_grow": 0.0,
                "head_dy": 0.0}

TOP_MARGIN = 2      # 춤으로 위로 올라갈 자리 (칸)
ROWS = {"badge": 2, "head": 10, "body": 32, "arm": 33, "podium": 45}
GRID_W, GRID_H = 28, 51


def ratio_for_rank(rank_name):
    """계급 이름으로 얼굴의 최산 비율(0~1)을 찾는다."""
    return dict(RANKS)[rank_name]


def dot_size(scale):
    """배율에 맞는 도트 크기(px). 그림 전체(28×51칸)가 WIDTH×HEIGHT×scale 안에 들어가는 가장 큰 정수."""
    return max(1, min(round(6.7 * scale), int(HEIGHT * scale // GRID_H), int(WIDTH * scale // GRID_W)))


def tight(rows):
    """투명 칸만 있는 가장자리를 잘라낸 (격자, 왼쪽 x, 위 y). 다 투명하면 None."""
    cells = [(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != pa.CLEAR]
    if not cells:
        return None
    x0 = min(x for x, _ in cells)
    x1 = max(x for x, _ in cells) + 1
    y0 = min(y for _, y in cells)
    y1 = max(y for _, y in cells) + 1
    return pa.crop(rows, x0, y0, x1, y1), x0, y0


def only(rows, keep, x0, y0, x1, y1):
    """격자에서 (x0, y0)~(x1, y1) 안의 keep 글자만 남기고 나머지는 투명으로 (크기는 그대로)."""
    return ["".join(ch if ch in keep and x0 <= x < x1 and y0 <= y < y1 else pa.CLEAR for x, ch in enumerate(r))
            for y, r in enumerate(rows)]


def face_pieces(t):
    """얼굴을 따로 놓을 조각 [(태그, 키, 격자, 색표, x칸, y칸)]: 얼굴(형·입), 눈, 눈썹 2개, 머리, 앞머리 가닥."""
    sources = pa.part_sources(t)
    names = {part: ("c" if sources[part] is pa.CHOISAN else "s") for part in pa.PART_ORDER}
    base_rows, colors = pa.compose(sources, parts=["shape", "skin"])
    eyes = sources["eyes"]["layers"]["eyes"]
    hair = sources["hair"]["layers"]["hair"]
    pieces = [("face", ("face", names["shape"], names["skin"]), base_rows, 0, 0)]
    pieces.append(("eye", ("eye", names["eyes"]), pa.crop(eyes, 0, 0, pa.FACE_W, pa.FACE_H, keep="EYP"), 0, 0))
    for side, (x0, x1) in (("l", (0, 10)), ("r", (10, 20))):
        pieces.append(("brow", ("brow", side, names["eyes"]), only(eyes, "B", x0, 0, x1, pa.FACE_H), 0, 0))
    pieces.append(("hair", ("hair", names["hair"]), pa.crop(hair, 0, 0, pa.FACE_W, pa.FACE_H, keep="Hhg"), 0, 0))
    for n, (x0, y0, x1, y1) in enumerate(pa.strand_pieces(hair)):
        pieces.append(("strand", ("strand", n, names["hair"]), only(hair, "z", x0, y0, x1, y1), 0, 0))
    out = []
    for tag, key, rows, _, _ in pieces:
        cut = tight(rows)
        if cut is not None:
            out.append((tag, key, cut[0], colors, cut[1], cut[2]))
    return out


def draw_character(canvas, x, y, t, rank_name, pose=None, scale=1.0, tag="char"):
    """(x, y)에서 시작하는 WIDTH×HEIGHT×scale 영역 아래쪽에 지휘대 위의 박산을 도트로 그린다.
    부위마다 태그(body, arm_l, arm_r, head, badge, podium, 머리 안의 face·eye·brow·hair·strand)를 붙인다."""
    p = dict(DEFAULT_POSE)
    for key in pose or {}:
        if key not in DEFAULT_POSE:
            raise ValueError("모르는 자세 이름: " + key)
    p.update(pose or {})
    d = dot_size(scale)
    left = x + int((WIDTH * scale - GRID_W * d) // 2)
    top = y + int(HEIGHT * scale - GRID_H * d)
    body_up = min(TOP_MARGIN, round(p["body_dy"] * scale / d))
    head_up = min(TOP_MARGIN, round(p["head_dy"] * scale / d))
    grow = 2 if p["body_grow"] >= 0.08 else (1 if p["body_grow"] > 0 else 0)
    if p["arm_raise"] < 0.5:
        arm_name, arm = "down", pa.ARM_DOWN
    elif grow == 2:
        arm_name, arm = "flex", pa.ARM_FLEX
    elif p["hand_drop"] > 0:
        arm_name, arm = "drop", pa.ARM_DROP
    else:
        arm_name, arm = "chest", pa.ARM_CHEST
    skin = pa.hero_colors(t)

    def put(key, build, col, row, tags):
        img = pa.photo(canvas, key, build, d)
        canvas.create_image(left + col * d, top + row * d, image=img, anchor="nw", tags=(tag,) + tags)

    put(("podium",), lambda: (pa.PODIUM, pa.WOOD_COLORS), 0, ROWS["podium"], ("podium",))
    put(("torso", grow, skin["S"]), lambda: (pa.torso(grow), skin), 6 - grow, ROWS["body"] - body_up, ("body",))
    for tag_name, key, rows, colors, cx, cy in face_pieces(t):
        put(("head",) + key, lambda rows=rows, colors=colors: (rows, colors), 4 + cx,
            ROWS["head"] - head_up + cy, ("head", tag_name))
    put(("badge", rank_name), lambda: (pa.badge(rank_name), pa.BADGE_COLORS), 8, ROWS["badge"] - head_up, ("badge",))
    arm_row = ROWS["arm"] - body_up
    right_col = 25 - len(arm[0])
    put(("arm_l", arm_name, skin["S"]), lambda: (arm, skin), 3, arm_row, ("arm_l",))
    put(("arm_r", arm_name, skin["S"]), lambda: (pa.flip(arm), skin), right_col, arm_row, ("arm_r",))


def dance_pose(drop=0.0, bounce=0.0, grow=0.0, head=0.0):
    """가슴 튕기기 춤의 한 자세: 팔은 가슴 높이로 든다."""
    return {"arm_raise": 1.0, "hand_drop": drop, "body_dy": bounce,
            "body_grow": grow, "head_dy": head}


def make_dance_steps():
    """춤 순서를 (이 자세로 머무는 ms, 자세) 목록으로 만든다. 모두 약 3.1초.
    도트 프레임: 팔 들기 / 손 툭 내리며 가슴 튕기기 / 머리 따라 올라감 / 제자리 (+ 마지막 크게)."""
    steps = [(400, dance_pose())]                                  # 1. 준비 0.4초
    for _ in range(4):                                             # 2. 튕기기 4번, 박자당 0.4초
        steps += [
            (100, dance_pose(drop=10, bounce=5, grow=0.04)),       #    손을 툭 내리며 몸통이 위로·크게
            (100, dance_pose(drop=10, bounce=5, grow=0.04, head=5)),  # 머리는 반 박자 늦게 따라 올라감
            (100, dance_pose(head=5)),                             #    몸통은 원래대로
            (100, dance_pose()),                                   #    머리도 원래대로
        ]
    steps += [
        (300, dance_pose(drop=20, bounce=10, grow=0.08)),          # 3. 마지막 크게
        (300, dance_pose(drop=20, bounce=10, grow=0.08, head=10)),
        (500, dance_pose(drop=20, bounce=10, grow=0.08, head=10)),  #    끝난 자세로 0.5초 멈춤
    ]
    return steps


DANCE_STEPS = make_dance_steps()


def draw_bubble(canvas, x, y, w, h, text, tag="bubble"):
    """(x, y)에서 시작하는 w×h 상자 안에 아래쪽 꼬리가 달린 도트 말풍선을 그린다."""
    cols, rows = w // pa.DOT, h // pa.DOT
    img = pa.photo(canvas, ("bubble", cols, rows), lambda: pa.bubble(cols, rows, int(cols * 0.62)))
    canvas.create_image(x, y, image=img, anchor="nw", tags=tag)
    body_h = (rows - pa.BUBBLE_TAIL) * pa.DOT
    canvas.create_text(x + w / 2, y + body_h / 2, text=text, width=w - 24,
                       font=("Malgun Gothic", -22, "bold"), fill="#1a1a1a", tags=tag)
