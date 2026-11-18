# 박산 캐릭터를 tkinter Canvas에 코드로 그린다 (사진·이미지 파일 없음).
# 성재 캐릭터와 최산 캐릭터의 부위별 설정값을 계급별 비율만큼 섞어 얼굴을 만든다.
# 몸통·왼팔·오른팔·머리·계급장을 태그로 나눠 그려서 춤출 때 따로 움직일 수 있다.
from symbols import RANKS

# 캐릭터 한 명이 차지하는 영역 (scale=1일 때, px)
WIDTH = 240
HEIGHT = 360
HEAD_Y = 160       # 머리 중심 높이
SHOULDER_Y = 258   # 어깨 높이
BADGE_Y = 30       # 계급장 중심 높이

UNIFORM = "#5d6b3a"
UNIFORM_DARK = "#465327"
UNIFORM_LIGHT = "#7b8452"
LINE = "#2a2420"

# 부위별 설정값. 두 캐릭터는 같은 이름의 설정값을 가진다.
# 숫자는 머리 중심(0, 0) 기준 px, 색은 "#rrggbb", 점 목록은 (x, y) 묶음.
# 0~1 사이 "세기" 값(ear_show, curl, strands, gloss, nose_round)은 있다/없다 부위를 서서히 나타나게 한다.
SEONGJAE = {
    # 얼굴형: 둥글고 볼살 있음, 턱 넓은 편
    "face_top_w": 56, "cheek_w": 64, "jaw_w": 56, "chin_w": 32, "chin_y": 74,
    "skin": "#f7dcc6",
    # 머리: 검정 짧은 머리, 윗머리 볼륨, 살짝 곱슬하게 앞으로, 옆머리 짧음
    "hair": "#151515", "hair_top": 108, "hair_side_w": 64, "hair_side_y": -26, "fringe_y": -38,
    "curl": 1.0, "strands": 0.0, "gloss": 0.0,
    # 귀: 옆으로 잘 보임
    "ear_show": 1.0,
    # 눈썹: 일자, 중간 굵기, 부드러운 인상
    "brow_y": -22, "brow_len": 22, "brow_thick": 5, "brow_tilt": 0,
    # 눈: 작고 둥근 편, 눈꼬리 수평, 차분한 눈빛
    "eye_x": 26, "eye_y": -6, "eye_w": 8, "eye_h": 6.5, "eye_tilt": 0, "pupil_r": 4,
    # 코: 콧망울 둥글고 코끝 도톰
    "nose_y": 22, "nose_w": 11, "nose_round": 1.0,
    # 입: 도톰한 분홍빛 입술, 살짝 다문 온화한 표정
    "lip": "#e58a98",
    "mouth": [(-16, 45), (-8, 39), (0, 41), (8, 39), (16, 45), (8, 52), (0, 54), (-8, 52)],
}

CHOISAN = {
    # 얼굴형: 갸름한 V라인, 날렵한 턱
    "face_top_w": 54, "cheek_w": 52, "jaw_w": 38, "chin_w": 10, "chin_y": 84,
    "skin": "#f3c8a2",
    # 머리: 검정, 젖은 듯한 질감, 이마와 한쪽 눈 위로 흘러내리는 앞머리 가닥
    "hair": "#0c0e14", "hair_top": 100, "hair_side_w": 66, "hair_side_y": 20, "fringe_y": -58,
    "curl": 0.0, "strands": 1.0, "gloss": 1.0,
    # 귀: 머리에 가려 거의 안 보임
    "ear_show": 0.0,
    # 눈썹: 굵은 직선, 바깥쪽 끝이 살짝 올라감
    "brow_y": -24, "brow_len": 28, "brow_thick": 8, "brow_tilt": 6,
    # 눈: 가로로 길고 가늘게, 눈꼬리 위로, 눈동자 작게
    "eye_x": 27, "eye_y": -6, "eye_w": 15, "eye_h": 3.5, "eye_tilt": 5, "pupil_r": 2.4,
    # 코: 곧고 짧은 코 선
    "nose_y": 22, "nose_w": 6, "nose_round": 0.0,
    # 입: 얇은 일자 입 (무표정)
    "lip": "#bf7470",
    "mouth": [(-15, 50), (-8, 49), (0, 49.5), (8, 49), (15, 50), (8, 51.5), (0, 52), (-8, 51.5)],
}

# 춤이 아닌 기본 자세. body_dy·head_dy는 위로 올라가는 px(양수 = 위),
# arm_raise는 팔을 가슴 높이로 든 정도(0~1), hand_drop은 든 손을 아래로 툭 내리는 px,
# body_grow는 몸통을 키우는 비율, squint는 눈을 뜬 정도(1 = 보통, 작을수록 가늘게).
DEFAULT_POSE = {"arm_raise": 0.0, "hand_drop": 0.0, "body_dy": 0.0, "body_grow": 0.0,
                "head_dy": 0.0, "squint": 1.0}


def ratio_for_rank(rank_name):
    """계급 이름으로 얼굴의 최산 비율(0~1)을 찾는다."""
    return dict(RANKS)[rank_name]


def mix_value(a, b, t):
    """숫자 두 개를 t만큼 섞는다 (t=0이면 a, t=1이면 b와 정확히 같다)."""
    return a * (1 - t) + b * t


def mix_color(a, b, t):
    """"#rrggbb" 색 두 개를 빨강·초록·파랑 따로 t만큼 섞는다."""
    parts = []
    for i in (1, 3, 5):
        value = round(mix_value(int(a[i:i + 2], 16), int(b[i:i + 2], 16), t))
        parts.append("%02x" % value)
    return "#" + "".join(parts)


def mix_points(a, b, t):
    """같은 개수의 점 목록 두 개를 점마다 t만큼 섞는다."""
    return [(mix_value(ax, bx, t), mix_value(ay, by, t)) for (ax, ay), (bx, by) in zip(a, b)]


def face_for(t):
    """최산 비율 t(0~1)에 맞게 두 캐릭터 설정값을 섞은 얼굴 설정값을 만든다."""
    face = {}
    for key, a in SEONGJAE.items():
        b = CHOISAN[key]
        if isinstance(a, str):
            face[key] = mix_color(a, b, t)
        elif isinstance(a, list):
            face[key] = mix_points(a, b, t)
        else:
            face[key] = mix_value(a, b, t)
    return face


def midpoint(a, b):
    """두 점의 가운데 점."""
    return mix_points([a], [b], 0.5)[0]


def pupil_radius(f, squint):
    """눈동자 반지름: 설정값과 실제 흰자 높이(설정 높이의 절반쯤) 중 작은 쪽."""
    return min(f["pupil_r"], f["eye_h"] * squint * 0.55)


def mirror(points):
    """오른쪽 반쪽 점 목록을 왼쪽으로 뒤집어 붙여 좌우 대칭 윤곽을 만든다."""
    return points + [(-x, y) for x, y in reversed(points[1:-1])]


def draw_character(canvas, x, y, t, rank_name, pose=None, scale=1.0, tag="char"):
    """(x, y)에서 시작하는 WIDTH×HEIGHT 영역에 캐릭터를 그린다. 부위마다 태그를 따로 붙인다."""
    p = dict(DEFAULT_POSE)
    for key in pose or {}:
        if key not in DEFAULT_POSE:
            raise ValueError("모르는 자세 이름: " + key)
    p.update(pose or {})
    f = face_for(t)
    cx = x + WIDTH / 2 * scale

    def at(px, py, base_y, dy=0.0):
        """부위 기준점(base_y)에서 (px, py)만큼 떨어진 화면 좌표."""
        return cx + px * scale, y + (base_y + py + dy) * scale

    def flat(points, base_y, dy=0.0):
        """점 목록을 create_polygon·create_line에 넣을 화면 좌표 한 줄로 바꾼다."""
        out = []
        for px, py in points:
            out.extend(at(px, py, base_y, dy))
        return out

    draw_body(canvas, f, p, at, flat, scale, (tag, "body"))
    head_dy = -p["head_dy"]
    draw_head(canvas, f, p, at, flat, scale, (tag, "head"), head_dy)
    draw_arm(canvas, f, p, at, scale, (tag, "arm_l"), -1)
    draw_arm(canvas, f, p, at, scale, (tag, "arm_r"), 1)
    draw_rank_badge(canvas, *at(0, BADGE_Y, 0, head_dy), rank_name, scale, (tag, "badge"))


def draw_body(canvas, f, p, at, flat, scale, tags):
    """목과 군복 몸통을 그린다. 춤출 때 위로 튕기고 살짝 커진다."""
    dy = -p["body_dy"]
    grow = 1 + p["body_grow"]
    canvas.create_rectangle(*at(-15, 60, HEAD_Y, dy), *at(15, 100, HEAD_Y, dy),
                            fill=f["skin"], outline="", tags=tags)
    half_top, half_bottom = 60 * grow, 68 * grow
    torso = [(-half_top, 0), (half_top, 0), (half_bottom, HEIGHT - SHOULDER_Y - 6), (-half_bottom, HEIGHT - SHOULDER_Y - 6)]
    canvas.create_polygon(flat(torso, SHOULDER_Y, dy), fill=UNIFORM, outline=LINE, width=2, tags=tags)
    for (bx, by, rx, ry, color) in [(-30, 26, 18, 10, UNIFORM_DARK), (22, 46, 20, 9, UNIFORM_LIGHT),
                                    (-12, 68, 16, 8, UNIFORM_LIGHT), (34, 80, 14, 8, UNIFORM_DARK)]:
        canvas.create_oval(*at(bx - rx, by - ry, SHOULDER_Y, dy), *at(bx + rx, by + ry, SHOULDER_Y, dy),
                           fill=color, outline="", tags=tags)
    collar = [(-24, -2), (0, 22), (24, -2)]
    canvas.create_line(flat(collar, SHOULDER_Y, dy), fill=LINE, width=max(1, 3 * scale), tags=tags)


def draw_arm(canvas, f, p, at, scale, tags, side):
    """팔 하나(side=-1 왼쪽, 1 오른쪽)를 그린다. arm_raise가 1이면 가슴 높이로 든다."""
    raise_ = p["arm_raise"]
    drop = p["hand_drop"] * raise_
    shoulder = (side * 56, 8 - p["body_dy"])
    elbow = (side * mix_value(74, 80, raise_), mix_value(44, 26, raise_) - p["body_dy"])
    hand = (side * mix_value(72, 34, raise_), mix_value(76, 16, raise_) + drop - p["body_dy"])
    points = []
    for px, py in (shoulder, elbow, hand):
        points.extend(at(px, py, SHOULDER_Y))
    canvas.create_line(points, fill=LINE, width=24 * scale, capstyle="round", joinstyle="round", tags=tags)
    canvas.create_line(points, fill=UNIFORM_LIGHT, width=19 * scale, capstyle="round", joinstyle="round", tags=tags)
    hx, hy = at(hand[0], hand[1], SHOULDER_Y)
    r = 9 * scale
    canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill=f["skin"], outline=LINE, tags=tags)


def draw_head(canvas, f, p, at, flat, scale, tags, dy):
    """귀, 얼굴, 머리카락, 눈썹, 눈, 코, 입을 그린다."""
    skin_line = mix_color(f["skin"], LINE, 0.45)

    # 귀 (최산 쪽으로 갈수록 작아져 머리에 가려진다)
    if f["ear_show"] > 0.02:
        for side in (-1, 1):
            inner = side * (f["cheek_w"] - 6)
            outer = side * (f["cheek_w"] + 11 * f["ear_show"])
            canvas.create_oval(*at(min(inner, outer), -16, HEAD_Y, dy), *at(max(inner, outer), 14, HEAD_Y, dy),
                               fill=f["skin"], outline=skin_line, width=2, tags=tags)

    # 얼굴 윤곽
    right_half = [(0, -74), (f["face_top_w"] * 0.8, -70), (f["face_top_w"], -38), (f["cheek_w"], 2),
                  (f["jaw_w"], 40), (f["chin_w"], f["chin_y"] - 10), (0, f["chin_y"])]
    canvas.create_polygon(flat(mirror(right_half), HEAD_Y, dy), fill=f["skin"], outline=skin_line,
                          width=2, smooth=True, tags=tags)

    draw_hair(canvas, f, at, flat, scale, tags, dy)

    # 눈썹
    for side in (-1, 1):
        inner = at(side * 11, f["brow_y"], HEAD_Y, dy)
        outer = at(side * (11 + f["brow_len"]), f["brow_y"] - f["brow_tilt"], HEAD_Y, dy)
        canvas.create_line(*inner, *outer, fill=f["hair"], width=f["brow_thick"] * scale,
                           capstyle="round", tags=tags + ("brow",))

    # 눈 (아몬드 모양 흰자 + 눈동자). squint가 작을수록 가늘게 뜬다.
    eye_h = f["eye_h"] * p["squint"]
    for side in (-1, 1):
        ex, ey = side * f["eye_x"], f["eye_y"]
        almond = [(ex - side * f["eye_w"], ey), (ex, ey - eye_h - f["eye_tilt"] / 2),
                  (ex + side * f["eye_w"], ey - f["eye_tilt"]), (ex, ey + eye_h * 0.8)]
        canvas.create_polygon(flat(almond, HEAD_Y, dy), fill="#ffffff", outline=LINE, width=2,
                              smooth=True, tags=tags)
        r = pupil_radius(f, p["squint"])
        px, py = at(ex + side * 1, ey - f["eye_tilt"] / 3, HEAD_Y, dy)
        canvas.create_oval(px - r * scale, py - r * scale, px + r * scale, py + r * scale,
                           fill="#1b1410", outline="", tags=tags)

    # 코: 둥근 코끝(성재)에서 곧은 콧날(최산)로
    bridge_color = mix_color(f["skin"], skin_line, 1 - f["nose_round"])
    canvas.create_line(*at(1, f["nose_y"] - 20, HEAD_Y, dy), *at(3, f["nose_y"] - 2, HEAD_Y, dy),
                       fill=bridge_color, width=2 * scale, tags=tags)
    tip_h = 4 + 6 * f["nose_round"]
    canvas.create_arc(*at(-f["nose_w"], f["nose_y"] - tip_h, HEAD_Y, dy), *at(f["nose_w"], f["nose_y"] + tip_h / 2, HEAD_Y, dy),
                      start=200, extent=140, style="arc", outline=skin_line, width=2 * scale, tags=tags)

    draw_strands(canvas, f, at, flat, scale, tags, dy)

    # 입 (윗입술·아랫입술 + 가운데 선)
    canvas.create_polygon(flat(f["mouth"], HEAD_Y, dy), fill=f["lip"], outline=mix_color(f["lip"], LINE, 0.4),
                          smooth=True, tags=tags)
    m = f["mouth"]
    # 입 점 8개: 0 왼쪽 끝, 1~3 윗입술, 4 오른쪽 끝, 5~7 아랫입술. 위아래 가운데를 이어 입술 사이 선을 그린다.
    middle = [m[0], midpoint(m[1], m[7]), midpoint(m[2], m[6]), midpoint(m[3], m[5]), m[4]]
    canvas.create_line(flat(middle, HEAD_Y, dy), fill=mix_color(f["lip"], LINE, 0.6), width=max(1, 1.5 * scale),
                       smooth=True, tags=tags)


def draw_hair(canvas, f, at, flat, scale, tags, dy):
    """머리카락: 기본 모양 + 곱슬 볼륨(성재) + 젖은 광택과 앞머리 가닥(최산)."""
    hair = f["hair"]
    side_w, top, side_y, fringe = f["hair_side_w"], f["hair_top"], f["hair_side_y"], f["fringe_y"]
    inner_w = f["face_top_w"] - 4
    outline = [(-side_w, side_y), (-side_w - 4, -40), (-side_w + 4, -82), (-40, -top + 8), (0, -top),
               (40, -top + 8), (side_w - 4, -82), (side_w + 4, -40), (side_w, side_y),
               (inner_w + 2, side_y), (inner_w, fringe + 10), (30, fringe), (0, fringe + 4), (-30, fringe),
               (-inner_w, fringe + 10), (-inner_w - 2, side_y)]
    canvas.create_polygon(flat(outline, HEAD_Y, dy), fill=hair, outline=hair, smooth=True, tags=tags)

    # 곱슬한 윗머리 볼륨과 앞으로 내려온 곱슬 앞머리
    # 크기가 줄면 중심도 머리 안쪽으로 들어가서, 작아진 곱슬이 이마에 점처럼 남지 않는다.
    if f["curl"] > 0.02:
        texture = mix_color(hair, "#4a4a4a", f["curl"])
        for bx, r in [(-34, 15), (0, 17), (34, 15)]:
            rr = r * f["curl"]
            by = -top + 10 + rr * 0.3
            canvas.create_oval(*at(bx - rr, by - rr, HEAD_Y, dy), *at(bx + rr, by + rr, HEAD_Y, dy),
                               fill=hair, outline=hair, tags=tags)
        for bx in (-36, -18, 0, 18, 36):
            rr = 8 * f["curl"]
            by = fringe - 4 + rr
            canvas.create_oval(*at(bx - rr, by - rr, HEAD_Y, dy), *at(bx + rr, by + rr, HEAD_Y, dy),
                               fill=hair, outline=hair, tags=tags)
        for bx, by in [(-30, -top + 22), (-6, -top + 16), (18, -top + 20), (40, -top + 30), (-44, -top + 34)]:
            canvas.create_arc(*at(bx - 6, by - 5, HEAD_Y, dy), *at(bx + 6, by + 5, HEAD_Y, dy),
                              start=20, extent=220, style="arc", outline=texture, width=2 * scale, tags=tags)

    # 젖은 듯한 광택
    if f["gloss"] > 0.02:
        shine = mix_color(hair, "#6f8399", f["gloss"])
        for line in ([(-44, -top + 26), (-24, -top + 12), (-6, -top + 8)], [(14, -top + 10), (34, -top + 16), (48, -top + 30)]):
            canvas.create_line(flat(line, HEAD_Y, dy), fill=shine, width=3 * scale, smooth=True,
                               capstyle="round", tags=tags)


def draw_strands(canvas, f, at, flat, scale, tags, dy):
    """이마에서 시작해 오른쪽 눈썹 위에서 끝나는 가는 앞머리 가닥 2개. 비율만큼 길어지고 진해진다."""
    if f["strands"] <= 0.02:
        return
    color = mix_color(f["skin"], f["hair"], f["strands"])
    root_y = f["fringe_y"] + 2
    for sx, sweep, root_w in [(12, 5, 4), (24, 6, 3.5)]:
        end_x = sx + sweep * f["strands"]
        lowest = f["brow_y"] - f["brow_tilt"] - f["brow_thick"] - 4   # 눈썹 가장 높은 곳보다 넉넉히 위
        end_y = root_y + (lowest - root_y) * f["strands"]
        mid_x = sx + sweep * f["strands"] * 0.4
        mid_y = (root_y + end_y) / 2
        wedge = [(sx - root_w / 2, root_y - 4), (mid_x - root_w / 3, mid_y), (end_x, end_y),
                 (mid_x + root_w / 3, mid_y), (sx + root_w / 2, root_y - 4)]
        canvas.create_polygon(flat(wedge, HEAD_Y, dy), fill=color, outline=color, smooth=True,
                              tags=tags + ("strand",))


def draw_rank_badge(canvas, bx, by, rank_name, scale=1.0, tags=()):
    """(bx, by)를 가운데로 계급장을 그린다. 이병~병장은 막대 1~4개, 하사는 V자와 막대."""
    w, h = 26 * scale, 15 * scale
    canvas.create_rectangle(bx - w, by - h, bx + w, by + h, fill="#2f3a1f", outline="#111111",
                            width=2, tags=tags)
    mark = "#f2f2f2"
    names = [name for name, _ in RANKS]
    level = names.index(rank_name)
    if level < 4:
        count = level + 1
        bar_h, gap = 3.5 * scale, 2.5 * scale
        total = count * bar_h + (count - 1) * gap
        top = by - total / 2
        for i in range(count):
            y0 = top + i * (bar_h + gap)
            canvas.create_rectangle(bx - 17 * scale, y0, bx + 17 * scale, y0 + bar_h, fill=mark,
                                    outline="", tags=tags)
    else:
        canvas.create_line(bx - 15 * scale, by - 9 * scale, bx, by + 2 * scale, bx + 15 * scale, by - 9 * scale,
                           fill="#e8c547", width=4 * scale, tags=tags)
        canvas.create_rectangle(bx - 15 * scale, by + 6 * scale, bx + 15 * scale, by + 9.5 * scale,
                                fill="#e8c547", outline="", tags=tags)


def dance_pose(drop=0.0, bounce=0.0, grow=0.0, head=0.0):
    """가슴 튕기기 춤의 한 자세: 팔은 가슴 높이로 들고 눈은 가늘게 뜬다."""
    return {"arm_raise": 1.0, "squint": 0.5, "hand_drop": drop, "body_dy": bounce,
            "body_grow": grow, "head_dy": head}


def make_dance_steps():
    """춤 순서를 (이 자세로 머무는 ms, 자세) 목록으로 만든다. 모두 약 3.1초."""
    steps = [(400, dance_pose())]                                  # 1. 준비 0.4초
    for _ in range(4):                                             # 2. 튕기기 4번, 박자당 0.4초
        steps += [
            (100, dance_pose(drop=10, bounce=5, grow=0.04)),       #    손을 툭 내리며 몸통이 위로·크게
            (100, dance_pose(drop=10, bounce=5, grow=0.04, head=5)),  # 머리는 반 박자 늦게 따라 올라감
            (100, dance_pose(head=5)),                             #    몸통은 원래대로
            (100, dance_pose()),                                   #    머리도 원래대로
        ]
    steps += [
        (300, dance_pose(drop=20, bounce=10, grow=0.08)),          # 3. 마지막 크게 (폭 2배)
        (300, dance_pose(drop=20, bounce=10, grow=0.08, head=10)),
        (500, dance_pose(drop=20, bounce=10, grow=0.08, head=10)),  #    끝난 자세로 0.5초 멈춤
    ]
    return steps


DANCE_STEPS = make_dance_steps()


def draw_bubble(canvas, x, y, w, h, text, tag="bubble"):
    """(x, y)에서 시작하는 w×h 상자 안에 아래쪽 꼬리가 달린 말풍선을 그린다."""
    tail = 18
    body_bottom = y + h - tail
    r = 18
    outline = [x + r, y, x + w - r, y, x + w, y, x + w, y + r, x + w, body_bottom - r, x + w, body_bottom,
               x + w - r, body_bottom, x + r, body_bottom, x, body_bottom, x, body_bottom - r, x, y + r, x, y]
    canvas.create_polygon(outline, fill="#ffffff", outline=LINE, width=2, smooth=True, tags=tag)
    tip_x = x + w * 0.62
    canvas.create_polygon(tip_x - 14, body_bottom - 2, tip_x + 14, body_bottom - 2, tip_x + 4, y + h,
                          fill="#ffffff", outline=LINE, width=2, tags=tag)
    canvas.create_line(tip_x - 12, body_bottom - 1, tip_x + 12, body_bottom - 1, fill="#ffffff", width=3, tags=tag)
    canvas.create_text(x + w / 2, y + (h - tail) / 2, text=text, width=w - 24,
                       font=("Malgun Gothic", -22, "bold"), fill="#1a1a1a", tags=tag)
