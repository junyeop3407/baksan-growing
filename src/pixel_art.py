# 도트(픽셀 아트) 그림을 파이썬 코드로 직접 찍는다. 외부 이미지·에셋 파일·AI 생성 그림은 쓰지 않는다.
# 스프라이트 = 글자 격자(같은 길이의 문자열 목록) + 색표(dict). "."은 찍지 않는 칸(투명).
# 그림 데이터(격자·색표·얼굴 섞기·배경)는 tkinter 없이 만들고, tk.PhotoImage는 photo()에서만 만든다.
# 만든 이미지는 _CACHE에 붙잡아 둔다(참조가 없으면 가비지 컬렉션으로 그림이 사라진다).
from symbols import BULLETS, RANKS

DOT = 4                       # 기본 배율: 도트 1칸 = 화면 4px
CLEAR = "."

# ---------------------------------------------------------------- 공통 도구


def check_sprite(rows, palette):
    """격자 줄 길이가 모두 같고 색표에 없는 글자가 없는지 확인한다. 문제가 있으면 ValueError."""
    if not rows:
        raise ValueError("빈 스프라이트")
    width = len(rows[0])
    for n, row in enumerate(rows):
        if len(row) != width:
            raise ValueError("줄 길이가 다름: " + str(n) + "줄 " + str(len(row)) + " != " + str(width))
        for ch in row:
            if ch != CLEAR and ch not in palette:
                raise ValueError("색표에 없는 글자: " + repr(ch))
    return width, len(rows)


def pad(rows, width, left=0):
    """왼쪽에 left칸, 오른쪽은 width가 되게 투명 칸을 붙인다."""
    return [(CLEAR * left + r).ljust(width, CLEAR) for r in rows]


def stamp(base, top, dx, dy):
    """base 위의 (dx, dy)에 top을 겹친다. top의 투명 칸은 base를 그대로 둔다. 새 목록을 돌려준다."""
    out = [list(r) for r in base]
    for y, row in enumerate(top):
        for x, ch in enumerate(row):
            if ch != CLEAR and 0 <= dy + y < len(out) and 0 <= dx + x < len(out[0]):
                out[dy + y][dx + x] = ch
    return ["".join(r) for r in out]


def flip(rows):
    """좌우를 뒤집는다."""
    return [r[::-1] for r in rows]


def mix_color(a, b, t):
    """두 색 "#rrggbb"를 t(0~1)만큼 섞는다. t=0이면 a, t=1이면 b 그대로."""
    if t <= 0:
        return a
    if t >= 1:
        return b
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join("%02x" % round(x + (y - x) * t) for x, y in zip(ca, cb))


# 4×4 Bayer 행렬 (하늘 그러데이션을 도트로 섞을 때 쓴다)
BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def noise(x, y, seed=0):
    """칸마다 늘 같은 0~99 값 (무작위 모듈 없이 무늬를 고정)."""
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return (n ^ (n >> 16)) % 100


# ---------------------------------------------------------------- 얼굴: 성재·최산을 부위별로 하나씩 바꾸기
# 얼굴은 20×22칸 부위 4개를 겹쳐 그린다 (아래 순서로 위에 덮음): 얼굴형 → 입·피부 → 눈썹·눈 → 머리.
# 두 얼굴의 부위는 크기·자리(눈 10~11줄, 코 13~14줄, 입 16~17줄)가 같아 서로 바꿔 끼울 수 있다.
# 계급이 오를 때마다 최산 부위가 하나씩 늘어난다: 일병 머리, 상병 +눈썹·눈, 병장 +얼굴형·턱, 하사 +입·피부.
# 글자: K 윤곽, S 피부, s 볼, R 귀(얼굴형) / N 코, L 입술, l 입술 그늘(입·피부)
#       B 눈썹, E 눈·눈꺼풀, Y 흰자·빛, P 눈동자(눈썹·눈) / H 머리, h 곱슬 결, g 윤기, z 앞머리 가닥(머리)

FACE_W, FACE_H = 20, 22
PART_ORDER = ["hair", "eyes", "shape", "skin"]     # 최산으로 바뀌는 순서
DRAW_ORDER = ["shape", "skin", "eyes", "hair"]     # 겹쳐 그리는 순서 (뒤가 위)
PART_COLORS = {"shape": "K", "skin": "SsRNLl", "eyes": "BEYP", "hair": "Hhgz"}   # 부위마다 색을 가져올 글자


def _blank():
    return [[CLEAR] * FACE_W for _ in range(FACE_H)]


def _shape(bounds, ears=False, blush=False):
    """얼굴형 칸: bounds = {줄: (왼쪽 윤곽 x, 오른쪽 윤곽 x)}. 첫 줄·끝 줄은 윤곽만, 사이는 피부로 채운다."""
    g = _blank()
    rows = sorted(bounds)
    for y in rows:
        lo, hi = bounds[y]
        for x in range(lo, hi + 1):
            g[y][x] = "K" if y in (rows[0], rows[-1]) or x in (lo, hi) else "S"
    if ears:                                          # 귀: 옆으로 한 칸 나온 피부색 + 바깥 윤곽
        for y in (9, 10, 11):
            g[y][1], g[y][2], g[y][17], g[y][18] = "K", "R", "R", "K"
    if blush:                                         # 볼살
        for x, y in ((4, 14), (4, 15), (5, 15), (15, 14), (15, 15), (14, 15)):
            g[y][x] = "s"
    return ["".join(r) for r in g]


def _dots(points):
    """{(x, y): 글자}를 20×22 격자로."""
    g = _blank()
    for (x, y), ch in points.items():
        g[y][x] = ch
    return ["".join(r) for r in g]


def _rows(top):
    """위에서부터 몇 줄만 적은 격자를 22줄로 채운다."""
    return top + [CLEAR * FACE_W] * (FACE_H - len(top))


SEONGJAE = {
    "layers": {
        # 얼굴형: 둥글고 볼살 있음, 턱 넓은 편, 귀가 옆으로 잘 보임
        "shape": _shape({2: (4, 15), 3: (3, 16), **{y: (2, 17) for y in range(4, 17)},
                         17: (3, 16), 18: (3, 16), 19: (4, 15), 20: (5, 14), 21: (7, 12)}, ears=True, blush=True),
        # 입·피부: 둥근 코, 도톰한 분홍 입술
        "skin": _dots({(9, 13): "N", (10, 13): "N", (9, 14): "N", (10, 14): "N",
                       (8, 16): "L", (9, 16): "L", (10, 16): "L", (11, 16): "L",
                       (8, 17): "l", (9, 17): "L", (10, 17): "L", (11, 17): "l"}),
        # 눈썹·눈: 일자 눈썹, 작고 둥근 눈 (빛 한 점)
        "eyes": _dots({**{(x, 8): "B" for x in (5, 6, 7, 12, 13, 14)},
                       **{(x, y): "E" for x in (5, 6, 13, 14) for y in (10, 11)},
                       (6, 10): "Y", (14, 10): "Y"}),
        # 머리: 검정 짧은 머리, 윗머리 볼륨, 곱슬하게 앞으로, 옆머리 짧아 귀가 보임
        "hair": _rows([
            "......HhHHhHHh......",
            "....hHHHhHHHhHHh....",
            "...HHhHHHhHHHhHHH...",
            "..HHHHhHHHHhHHHhHH..",
            "..HhHHHHhHHHHHhHHH..",
            "..HHHhHHHHhHHHHhHH..",
            "..HH..h.H..h.H..HH..",
            "..H..............H..",
        ]),
    },
    "colors": {"K": "#6a4a3a", "S": "#f7dcc6", "s": "#efb9a6", "R": "#eac3a8", "N": "#d9a98a", "L": "#e58a98",
               "l": "#c46a7a", "B": "#1a1a1a", "E": "#141414", "Y": "#ffffff", "P": "#141414",
               "H": "#151515", "h": "#3a3a3a", "g": "#3a3a3a", "z": "#151515"},
}

CHOISAN = {
    "layers": {
        # 얼굴형: 갸름한 V라인, 날렵한 턱, 귀는 머리에 가려 안 보임
        "shape": _shape({2: (4, 15), 3: (3, 16), **{y: (2, 17) for y in range(4, 12)},
                         **{y: (3, 16) for y in range(12, 15)}, 15: (4, 15), 16: (4, 15), 17: (5, 14),
                         18: (6, 13), 19: (7, 12), 20: (8, 11), 21: (9, 10)}),
        # 입·피부: 곧고 짧은 코 선, 얇은 일자 입
        "skin": _dots({(10, 13): "N", (10, 14): "N", (11, 14): "N",
                       (8, 16): "l", (9, 16): "l", (10, 16): "l", (11, 16): "l"}),
        # 눈썹·눈: 길고 곧은 눈썹, 가로로 긴 눈(눈꼬리 위로)과 눈동자 점
        "eyes": _dots({**{(x, 7): "B" for x in (4, 5, 6, 7, 8, 11, 12, 13, 14, 15)},  # 길고 곧은 눈썹 (한 줄,
                                                                                    #  눈과 한 줄 띄움)
                       **{(x, 10): "E" for x in (5, 6, 7, 8, 11, 12, 13, 14)},       # 긴 윗눈꺼풀
                       (4, 10): "E", (15, 10): "E", (3, 9): "E", (16, 9): "E",       # 눈꼬리가 위로
                       (5, 11): "Y", (6, 11): "P", (7, 11): "P", (8, 11): "Y",       # 흰자와 눈동자 점
                       (11, 11): "Y", (12, 11): "P", (13, 11): "P", (14, 11): "Y"}),
        # 머리: 젖은 듯한 검정 머리(윤기), 옆머리가 귀를 덮고, 앞머리 2가닥은 눈썹(7~8줄) 위 6줄에서 끝남
        "hair": _rows([
            "......HHHHHHHH......",
            "....HHHHHHHHHHHH....",
            "...HHHgHHHHHHgHHH...",
            "..HHHHHgHHHHHHgHHH..",
            ".HHHHHHHHHHHHHHHHHH.",
            ".HHH...z...z....HHH.",
            ".HH....z....z....HH.",
            ".HH..............HH.",
            ".HH..............HH.",
            ".HH..............HH.",
            ".HH..............HH.",
            ".HH..............HH.",
            "..H..............H..",
        ]),
    },
    "colors": {"K": "#5e3f30", "S": "#f3c8a2", "s": "#f3c8a2", "R": "#e0b08e", "N": "#cf9a76", "L": "#bf7470",
               "l": "#a65d5a", "B": "#0f0f12", "E": "#0d0d0d", "Y": "#f2f2f2", "P": "#3b2a22",
               "H": "#0c0e14", "h": "#0c0e14", "g": "#4a5872", "z": "#0c0e14"},
}


def choisan_parts(t):
    """비율 t(0, 0.25, 0.5, 0.75, 1)에서 최산 것으로 바뀐 부위 목록 (PART_ORDER 순서)."""
    return PART_ORDER[:round(t * len(PART_ORDER))]


def part_sources(t):
    """부위마다 어느 얼굴(성재/최산) 것을 쓰는지."""
    chosen = choisan_parts(t)
    return {part: CHOISAN if part in chosen else SEONGJAE for part in PART_ORDER}


def compose(sources, parts=DRAW_ORDER):
    """부위마다 고른 얼굴로 겹쳐 그린 (격자, 색표). 색은 그 글자를 가진 부위의 얼굴 색을 쓴다."""
    rows = [CLEAR * FACE_W] * FACE_H
    colors = {}
    for part in parts:
        rows = stamp(rows, sources[part]["layers"][part], 0, 0)
    for part in PART_ORDER:
        for ch in PART_COLORS[part]:
            colors[ch] = sources[part]["colors"][ch]
    return rows, colors


def blend_face(t):
    """계급 비율 t의 도트 얼굴 (격자, 색표): 부위별로 성재 또는 최산."""
    return compose(part_sources(t))


def whole_face(face):
    """한 사람 얼굴 전체 (격자, 색표)."""
    return compose({part: face for part in PART_ORDER})


def strand_pieces(hair_rows):
    """머리 격자에서 앞머리 가닥(z)을 이어진 덩어리로 나눠 [(x0, y0, x1, y1)] (끝 칸 다음 좌표)로 돌려준다."""
    cells = {(x, y) for y, r in enumerate(hair_rows) for x, ch in enumerate(r) if ch == "z"}
    pieces = []
    while cells:
        stack = [cells.pop()]
        group = set(stack)
        while stack:
            x, y = stack.pop()
            for nx in (x - 1, x, x + 1):
                for ny in (y - 1, y, y + 1):
                    if (nx, ny) in cells:
                        cells.discard((nx, ny))
                        group.add((nx, ny))
                        stack.append((nx, ny))
        xs = [x for x, _ in group]
        ys = [y for _, y in group]
        pieces.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
    return sorted(pieces)


def crop(rows, x0, y0, x1, y1, keep=None):
    """격자의 (x0, y0)~(x1, y1) 부분. keep을 주면 그 글자만 남기고 나머지는 투명."""
    out = [r[x0:x1] for r in rows[y0:y1]]
    if keep is not None:
        out = ["".join(ch if ch in keep else CLEAR for ch in r) for r in out]
    return out


# ---------------------------------------------------------------- 박산(지휘관): 계급장·얼굴·군복·팔·지휘대

BADGE_COLORS = {"K": "#111111", "G": "#2f3a1f", "W": "#f2f2f2", "O": "#e8c547"}


def badge(rank_name):
    """계급장 12×7. 이병~병장은 흰 막대 1~4개, 하사는 금색 V와 막대."""
    names = [name for name, _ in RANKS]
    level = names.index(rank_name)
    rows = ["KKKKKKKKKKKK"] + ["KGGGGGGGGGGK"] * 5 + ["KKKKKKKKKKKK"]
    if level < 4:
        bars = {0: [3], 1: [2, 4], 2: [1, 3, 5], 3: [1, 2, 4, 5]}[level]
        for y in bars:
            rows = stamp(rows, ["WWWWWWWW"], 2, y)
    else:
        rows = stamp(rows, ["O......O", ".O....O.", "..O..O..", "...OO...", "........"], 2, 1)
        rows = stamp(rows, ["OOOOOOOO"], 2, 5)
    return rows


# 몸통(16칸 폭): 목, 군복(얼룩무늬), 허리띠, 다리, 군화
HERO_TORSO = [
    "......SSSS......",
    "....UUcUUUUU....",
    "..UUUUUYYUUUcU..",
    ".UUcUUUYYUUUUUU.",
    "UUUUUUcUUUUUUcUU",
    "UUcUUUUUUUcUUUUU",
    "UUUUUUUUcUUUUUUU",
    "uUUUcUUUUUUcUUUu",
    "uUUUUUUUUUUUUcUu",
    "uDDDDDDDDDDDDDDu",
    ".UUUUUU..UUUUUU.",
    ".uUUUUu..uUUUUu.",
    "DDDDDDD..DDDDDDD",
]
# 왼팔 (화면 왼쪽). 오른팔은 좌우를 뒤집는다
ARM_DOWN = [
    "UUU",
    "UcU",
    "UUU",
    "UUU",
    "UcU",
    "UUU",
    "uUu",
    "uUu",
    "SSS",
    ".S.",
]
ARM_CHEST = [                                   # 춤 1: 팔을 가슴 높이로 굽혀 주먹을 가슴 앞에
    "UUU.....",
    "UcU.....",
    "UUUUUUSS",
    "uUUUcUSS",
    "........",
    "........",
]
ARM_DROP = [                                    # 춤 2: 가슴 앞 주먹을 툭 내림
    "UUU.....",
    "UcU.....",
    "UUU.....",
    "uUUUU...",
    "..UUUUSS",
    "......SS",
]
ARM_FLEX = [                                    # 춤 3: 마지막 크게 — 주먹을 어깨 위로
    "......SS",
    "......SS",
    "UUU..UU.",
    "UcUUUUU.",
    "UUUUcU..",
    "uUu.....",
]
HERO_COLORS = {"U": "#5d6b3a", "u": "#465327", "c": "#7b8452", "Y": "#3e4a24", "D": "#2e2a1e"}

PODIUM = [                                      # 박산이 서 있는 작은 나무 지휘대 (28칸)
    "KKKKKKKKKKKKKKKKKKKKKKKKKKKK",
    "KVVVVVVVVVVVVVVVVVVVVVVVVVVK",
    "KWWnWWWWWWWWWWWWWWWWWWWWnWWK",
    "KwwwwwwwwwwwwwwwwwwwwwwwwwwK",
    "..KWK..................KWK..",
    "..KwK..................KwK..",
]


def torso(level=0):
    """몸통 격자 (16 + 2×level칸 폭). level 1·2면 가슴을 양쪽으로 그만큼 넓힌다(춤의 가슴 튕기기)."""
    level = int(level)
    return [(r[0] * level + r + r[-1] * level) if 1 <= y <= 9 else (CLEAR * level + r + CLEAR * level)
            for y, r in enumerate(HERO_TORSO)]


def hero_colors(t):
    """군복 색 + 그 계급 얼굴의 피부색(목·손)."""
    colors = dict(HERO_COLORS)
    colors["S"] = part_sources(t)["skin"]["colors"]["S"]
    return colors


def hero(t, rank_name):
    """미리보기용 박산 한 장 (28칸 폭): 계급장 + 얼굴 + 몸통·팔 + 지휘대. (격자, 색표)."""
    face, face_colors = blend_face(t)
    colors = dict(face_colors)
    badge_swap = {"K": "a", "G": "b", "W": "d", "O": "e"}
    for k, v in badge_swap.items():
        colors[v] = BADGE_COLORS[k]
    body_colors = hero_colors(t)
    # 같은 글자가 다른 색을 쓰지 않게 몸 쪽 글자를 바꿔 끼운다 (U→1 u→2 c→3 Y→4 D→5, 피부는 얼굴 S 그대로)
    swap = {"U": "1", "u": "2", "c": "3", "Y": "4", "D": "5"}
    for k, v in swap.items():
        colors[v] = body_colors[k]
    wood = {"K": "6", "V": "7", "W": "8", "w": "9", "n": "0"}
    for k, v in wood.items():
        colors[v] = WOOD_COLORS[k]

    def recolor(rows, table):
        return ["".join(table.get(ch, ch) for ch in r) for r in rows]
    grid = [CLEAR * 28] * 51
    grid = stamp(grid, recolor(badge(rank_name), badge_swap), 8, 0)
    grid = stamp(grid, face, 4, 8)
    grid = stamp(grid, recolor(torso(), swap), 6, 30)
    grid = stamp(grid, recolor(ARM_DOWN, swap), 3, 31)
    grid = stamp(grid, recolor(flip(ARM_DOWN), swap), 22, 31)
    grid = stamp(grid, recolor(PODIUM, wood), 0, 43)
    return grid[:49], colors



# ---------------------------------------------------------------- 병사 5종 (군복 그대로, 오른쪽을 보고 쏜다)

SOLDIER_BASE = [
    "......GGGGG...........",
    "....GGgGGGGGG.........",
    "...GGGGGGGGGGG........",
    "...KKKKKKKKKKK........",
    "....SSSSSSSSS.........",
    "....SSSSSESSE.........",
    "....sSSSSSSSS.........",
    ".....SSSSsSS..........",
    "......SSSSS...........",
    "....UUUUUUUUU.........",
    "...UUcUUUUUcUU........",
    "...UUAAAAAAAUU........",
    "...UUUUcUUUUUU........",
    "...UUUUUUUUcUS........",
    "....UUUUUUUUU.........",
    "....DDDDDDDDD.........",
    "....UUUU.UUUU.........",
    "....UUUU.UUUU.........",
    "....uuuu.uuuu.........",
    "...DDDDD.DDDDD........",
]
SOLDIER_COLORS = {
    "G": "#4b5320", "g": "#6b7440", "K": "#1e1a1d", "S": "#f2cfae", "s": "#d9a987", "E": "#141414",
    "U": "#5d6b3a", "u": "#465327", "c": "#7b8452", "D": "#2e2a1e",
    "T": "#7a5230", "M": "#4a4f57", "m": "#8c939b", "O": "#f5c518", "o": "#b8860b",
    "F": "#fff3a0", "f": "#ff9f1c",
}
# 총알마다 무기 모양 (12줄 9칸째부터 오른쪽으로)과 총구 끝 x
WEAPONS = {
    "연습탄": (["TTTTTTT", "T......"], 16),
    "보통탄": (["TTMMMMMMMM", "T..M......"], 19),
    "예광탄": (["TTMMMMMMMMm", "TMMMMm.....", ".M.M......."], 20),
    "철갑탄": (["TTMMMMMMMMMMM", "T..Mm........"], 22),
    "황금탄": (["ooOOOOOOOO", "o..O......"], 19),
}
FLASH_DOTS = ["F.", "fF", "F."]


def soldier(kind, firing=False):
    """병사 도트 22×20 (격자, 색표). 팔띠 A는 그 총알의 탄두 색. firing이면 총구에 불꽃."""
    shape, muzzle = WEAPONS[kind]
    rows = stamp(SOLDIER_BASE, shape, 9, 12)
    if kind == "황금탄":
        rows = stamp(rows, ["OOOOOOOOOOO"], 3, 3)       # 특급전사: 금색 철모 테
    if firing:
        rows = stamp(rows, FLASH_DOTS, min(muzzle, 20), 11)
    colors = dict(SOLDIER_COLORS)
    colors["A"] = BULLETS[kind]["tip_end"] if kind == "예광탄" else BULLETS[kind]["tip"]
    return rows, colors


STAR = [
    "..O..",
    ".OOO.",
    "OOOOO",
    ".OOO.",
    "O...O",
]
STAR_COLORS = {"O": "#f5c518"}

SHOT = ["fFF"]               # 날아가는 작은 총알
SHOT_COLORS = {"F": "#fff3a0", "f": "#ff9f1c"}

SPARKLE = [                     # 합체 반짝임 (2프레임: 큰 별, 작은 별)
    [
        "...O...",
        "...O...",
        "..OwO..",
        "OOwwwOO",
        "..OwO..",
        "...O...",
        "...O...",
    ],
    [
        ".......",
        ".......",
        "...O...",
        "..OwO..",
        "...O...",
        ".......",
        ".......",
    ],
]
SPARKLE_COLORS = {"O": "#ffd60a", "w": "#fffbe6"}

ARROW_UP = [                    # 상점: 공격력 +10%
    ".....KK.....",
    "....KOOK....",
    "...KOOOOK...",
    "..KOOOOOOK..",
    ".KOOOOOOOOK.",
    "KKKKOOOOKKKK",
    "...KOOOOK...",
    "...KOOOOK...",
    "...KOooOK...",
    "...KOooOK...",
    "...KKKKKK...",
]
ARROW_COLORS = {"K": "#2e1d12", "O": "#e67e22", "o": "#b85c12"}

COIN = [                        # 상점: 첫 스핀 무료
    "...KKKKKK...",
    ".KKOOOOOOKK.",
    ".KOOwOOOOOK.",
    "KOOwOOOOOOoK",
    "KOOOOOOOOOoK",
    "KOOOOOOOOOoK",
    "KOOOOOOOOOoK",
    "KOOOOOOOOooK",
    ".KOOOOOOooK.",
    ".KKooooooKK.",
    "...KKKKKK...",
]
COIN_COLORS = {"K": "#5c3d00", "O": "#ffd60a", "o": "#c99700", "w": "#fff6c2"}

# ---------------------------------------------------------------- 적: 슬라임·고블린·해골 병사 (왼쪽을 보고 걷는다)

SLIME = [
    [
        "................",
        "......KKKK......",
        "....KKGGGGKK....",
        "...KGYYGGGGGK...",
        "..KGYYGGGGGGGK..",
        "..KGGEGGGEGGGK..",
        ".KGGGEGGGEGGGGK.",
        ".KGGGGGGGGGGGGK.",
        ".KGgGGGggGGGgGK.",
        "KGggGGGGGGGGggGK",
        "KggggggggggggggK",
        ".KKKKKKKKKKKKKK.",
    ],
    [
        "................",
        "................",
        ".......KKKK.....",
        ".....KKGGGGKK...",
        "...KKGYYGGGGGKK.",
        "..KGGYYGGGGGGGGK",
        ".KGGGEGGGEGGGGGK",
        ".KGGGEGGGEGGGGGK",
        "KGGgGGGggGGGGgGK",
        "KGggGGGGGGGGGggK",
        "KgggggggggggggggK"[:16],
        "KKKKKKKKKKKKKKKK",
    ],
]
SLIME_COLORS = {"K": "#1d3b2a", "G": "#5fd16b", "g": "#3a9a4c", "Y": "#d8ffd8", "E": "#10241a"}

GOBLIN = [
    [
        "......KKKK......",
        "....KKGGGGK.....",
        ".KK.KGGGGGGK.KK.",
        "KGGKGEYGGEYGKGGK",
        ".KGGGGGGGGGGGGK.",
        "...KGGgGGGGGK...",
        "....KGwwwwGK....",
        ".....KGGGGK.....",
        "...KKBBBBBBKK...",
        "TT.KBBBbBBBBGK..",
        "TTKGBBBBBBBBGK..",
        ".TKGKBBBBbBKK...",
        ".T..KbbbbbbK....",
        "....KBB.KBBK....",
        "...KBBK..KBBK...",
        "...KGGK...KGGK..",
        "..KGGGK...KGGGK.",
        "..KKKK.....KKKK.",
    ],
    [
        "......KKKK......",
        "....KKGGGGK.....",
        ".KK.KGGGGGGK.KK.",
        "KGGKGEYGGEYGKGGK",
        ".KGGGGGGGGGGGGK.",
        "...KGGgGGGGGK...",
        "....KGwwwwGK....",
        ".....KGGGGK.....",
        "...KKBBBBBBKK...",
        "...KBBBbBBBBGK..",
        "TTKGBBBBBBBBGK..",
        "TTKGKBBBBbBKK...",
        ".T..KbbbbbbK....",
        ".T...KBBBBK.....",
        ".....KBBBK......",
        ".....KGGK.......",
        "....KGGGK.......",
        "....KKKK........",
    ],
]
GOBLIN_COLORS = {"K": "#1e1a1d", "G": "#7cae3e", "g": "#4f7a22", "E": "#1e1a1d", "Y": "#ffe14d",
                 "w": "#f2f2e6", "B": "#7a5230", "b": "#55391f", "T": "#a0703c"}

SKELETON = [
    [
        ".....KKKKK......",
        "....KWWWWWK.....",
        "...KWWWWWWWK....",
        "...KWEEWEEWK....",
        "...KWEEWEEWK....",
        "....KWWnWWK.....",
        ".....KwWwK......",
        "......KWK.......",
        "....KWWWWWK.....",
        "M..KWKWWWKWK....",
        "MM.KWKwWwKWK....",
        ".MMWKWWWWWKWK...",
        "..MWK.KWK..KW...",
        "......KWK.......",
        ".....KW.WK......",
        "....KW...WK.....",
        "....KW...WK.....",
        "...KWW...WWK....",
    ],
    [
        ".....KKKKK......",
        "....KWWWWWK.....",
        "...KWWWWWWWK....",
        "...KWEEWEEWK....",
        "...KWEEWEEWK....",
        "....KWWnWWK.....",
        ".....KwWwK......",
        "......KWK.......",
        "....KWWWWWK.....",
        "...KWKWWWKWK....",
        "M..KWKwWwKWK....",
        "MMMWKWWWWWKWK...",
        "..MWK.KWK..KW...",
        "......KWK.......",
        "......KWWK......",
        "......KW.WK.....",
        ".....KW..WK.....",
        ".....KWW.WWK....",
    ],
]
SKELETON_COLORS = {"K": "#2a2a33", "W": "#efeadb", "w": "#bdb6a3", "E": "#1a1a22", "n": "#2a2a33",
                   "M": "#9a6a3a"}

ENEMIES = {"slime": (SLIME, SLIME_COLORS), "goblin": (GOBLIN, GOBLIN_COLORS),
           "skeleton": (SKELETON, SKELETON_COLORS)}
ENEMY_NAMES = {"slime": "슬라임", "goblin": "고블린", "skeleton": "해골 병사"}


def enemy_kind(wave):
    """웨이브에 따라 바뀌는 적: 1~2 슬라임, 3~5 고블린, 6부터 해골 병사."""
    if wave <= 2:
        return "slime"
    if wave <= 5:
        return "goblin"
    return "skeleton"


def enemy(kind, frame):
    """적 도트 (격자, 색표). frame 0/1은 걷기 2프레임."""
    frames, colors = ENEMIES[kind]
    return frames[frame % 2], colors


# ---------------------------------------------------------------- 보스: 드래곤 (5웨이브마다)

DRAGON_BODY = [
    "........................................",
    "........................................",
    "........................................",
    "........................................",
    "........................................",
    "........................................",
    "........................................",
    "...KK...................................",
    "..KYYK..................................",
    ".KRRRRKK................................",
    "KRREYRRRK...............................",
    "KRRRRRRRRK..............................",
    "KWRWRRRRRRK.............................",
    ".KKKKRRRRRK...KKKKKKKKKKK...............",
    "....KRRRRRRKKKRRRRRRRRRRRKK.............",
    ".....KRRRRRRRRRRRRRRRRRRRRRKK...........",
    "......KKRRRRRRRRRRRRRRRRRRRRRKK.....KK..",
    "........KOOOOOOORRRRRRRRRRRRRRRK...KRRK.",
    "........KOOOOOOOORRRRRRRRRRRRRRRKKKRRK..",
    ".........KOOOOOOORRRRRRRRRRRRRRRRRRRK...",
    "..........KKOOOOORRRRRKKRRRRRKKKKKKK....",
    "............KKRRRRRK..KRRRRK............",
    ".............KRRRK....KRRRK.............",
    "............KRrRK....KRrRK..............",
    "............KWKWK....KWKWK..............",
    "............KKKKK....KKKKK..............",
]
WING_UP = [
    "..........K.....",
    ".........KPK....",
    "........KPPK..K.",
    ".......KPPPK.KPK",
    "......KPPpPK.KPK",
    ".....KPPpPPKKPPK",
    "....KPPpPPPPPPPK",
    "...KPPpPPPPpPPK.",
    "..KPPPPPPPpPPK..",
    ".KPPPPPPPpPPK...",
    "KKKKKKKKKKKK....",
]
WING_DOWN = [
    "KKKKKKKKKKKKKK..",
    ".KPPPPPPPPPPPPK.",
    "..KPPpPPPPpPPPK.",
    "...KPPpPPPpPPK..",
    "....KPPpPPpPK...",
    ".....KPPPpPK....",
    "......KPPPK.....",
    ".......KPK......",
    "........K.......",
]
DRAGON_COLORS = {"K": "#2a1020", "R": "#c0392b", "r": "#7d1f1a", "O": "#f2c14e", "Y": "#f4e9c8",
                 "E": "#ffe14d", "W": "#f4f1e6", "P": "#7b3fa0", "p": "#4f2470"}


def dragon(frame):
    """드래곤 보스 40×26 (격자, 색표). frame 0 날개 위, 1 날개 아래."""
    if frame % 2 == 0:
        rows = stamp(DRAGON_BODY, WING_UP, 14, 3)
    else:
        rows = stamp(DRAGON_BODY, WING_DOWN, 13, 14)
    return rows, DRAGON_COLORS


# ---------------------------------------------------------------- 총알 아이콘 5종, 하트, 바리케이드

def bullet_icon(kind):
    """총알 아이콘 7×16 (격자, 색표). 탄두 T·끝 E·탄피 C, 철갑탄은 뾰족하게."""
    info = BULLETS[kind]
    if info["pointy"]:
        tip = ["...E...", "...E...", "..ETE..", "..TTT..", ".TTTTT.", ".TtTTT.", ".TtTTT."]
    else:
        tip = ["..KEK..", ".KEEEK.", ".KTTTK.", "KTtTTTK", "KTtTTTK", "KTtTTTK", "KTTTTTK"]
    if info["tip_end"] == info["tip"]:
        tip = [r.replace("E", "T") for r in tip]
    case = ["KCCCCCK", "KCcCCCK", "KCcCCCK", "KCcCCCK", "KCcCCCK", "KCCCCCK", "KkkkkkK", "KCCCCCK", "KKKKKKK"]
    short = 2 if kind == "연습탄" else 0                 # 연습탄은 짧다
    rows = [CLEAR * 7] * short + tip[short:] + case
    rows = rows[:16] if len(rows) >= 16 else [CLEAR * 7] * (16 - len(rows)) + rows
    colors = {"K": "#2b2b2b", "T": info["tip"], "t": mix_color(info["tip"], "#ffffff", 0.35),
              "E": info["tip_end"], "C": info["case"], "c": mix_color(info["case"], "#ffffff", 0.4),
              "k": mix_color(info["case"], "#000000", 0.3)}
    return rows, colors


HEART = [
    ".KK...KK.",
    "KRRK.KRRK",
    "KRhRKRRRK",
    "KRRRRRRRK",
    ".KRRRRRK.",
    "..KRRRK..",
    "...KRK...",
    "....K....",
]
HEART_COLORS = {"K": "#5a0f1a", "R": "#d62839", "h": "#ff9aa5"}
HEART_EMPTY_COLORS = {"K": "#5a4a3a", "R": "#c9b48a", "h": "#d8c79f"}


BARRICADE_TILE = [
    "...K......",
    "..KVK..K..",
    "..KWK.KVK.",
    "..KWK.KWK.",
    "KVVVVVVVVK",
    "KWnWWWWnWK",
    "KwwwwwwwwK",
    "..KwK.KWK.",
    "..KWK.KwK.",
    "..KWK.KWK.",
    "..KwK.KWK.",
    "..KKK.KKK.",
]


def barricade(height):
    """나무 바리케이드 10칸 폭 × height줄: 뾰족한 말뚝과 못 박은 가로 판자를 위아래로 잇는다. (격자, 색표)."""
    return [BARRICADE_TILE[y % len(BARRICADE_TILE)] for y in range(height)], WOOD_COLORS


# ---------------------------------------------------------------- 나무 테두리·양피지 판 (정보판·버튼·상점 카드)

WOOD_COLORS = {"K": "#2e1d12", "W": "#9a6534", "w": "#6e4423", "V": "#c78f52", "n": "#d9d2c0",
               "P": "#f3e6c4", "p": "#e6d3a3", "q": "#cbb07a"}


def wood_frame(width, height, border=2, inner="P"):
    """width×height칸 판: 바깥 윤곽 1칸 + 나무 border칸 + 안쪽 inner(양피지 P, 나무 판자 W).
    네 귀퉁이에 못. 나뭇결·양피지 얼룩은 noise로 늘 같은 자리에. (격자, 색표)."""
    rows = []
    edge = 1 + border
    for y in range(height):
        row = []
        for x in range(width):
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                ch = "K"
            elif x < edge or y < edge or x >= width - edge or y >= height - edge:
                if (x in (edge - 1, width - edge) and y >= edge - 1 and y <= height - edge) or \
                        (y in (edge - 1, height - edge) and x >= edge - 1 and x <= width - edge):
                    ch = "w"                                            # 안쪽 그늘선
                elif y == 1 or x == 1:
                    ch = "V"                                            # 빛 받는 바깥 가장자리
                else:
                    ch = "w" if noise(x // 3, y, 7) < 18 else "W"       # 나뭇결
            elif inner == "P":
                ch = "q" if noise(x, y, 3) < 3 else ("p" if noise(x, y, 5) < 10 else "P")
            else:
                ch = "w" if (y - edge) % 5 == 4 else ("V" if noise(x // 4, y, 9) < 8 else "W")
            row.append(ch)
        rows.append(row)
    for cx, cy in ((1, 1), (width - 2, 1), (1, height - 2), (width - 2, height - 2)):
        if border >= 1:
            rows[cy][cx] = "n"
    return ["".join(r) for r in rows], WOOD_COLORS


# ---------------------------------------------------------------- 말풍선

BUBBLE_TAIL = 4                 # 꼬리 줄 수
BUBBLE_COLORS = {"K": "#2a2420", "W": "#ffffff", "w": "#e8eef2"}


def bubble(width, height, tail_x):
    """width×height칸 도트 말풍선: 모서리를 깎은 흰 상자 + 아래 꼬리(tail_x 근처). (격자, 색표)."""
    body_h = height - BUBBLE_TAIL
    g = [[CLEAR] * width for _ in range(height)]
    for y in range(body_h):
        for x in range(width):
            edge = x in (0, width - 1) or y in (0, body_h - 1)
            g[y][x] = "K" if edge else ("w" if y == body_h - 2 else "W")
    for cx, cy in ((0, 0), (width - 1, 0), (0, body_h - 1), (width - 1, body_h - 1)):
        g[cy][cx] = CLEAR                                       # 둥근 모서리
        g[cy + (1 if cy == 0 else -1)][cx + (1 if cx == 0 else -1)] = "K"
    for k in range(BUBBLE_TAIL):                                # 꼬리: 아래로 갈수록 좁아짐
        x0, x1 = tail_x - 3 + k, tail_x + 3 - k
        for x in range(x0, x1 + 1):
            g[body_h - 1 + k][x] = "K" if x in (x0, x1) or k == BUBBLE_TAIL - 1 else "W"
    return ["".join(r) for r in g], BUBBLE_COLORS


# ---------------------------------------------------------------- 판타지 배경 (하늘·산·성·숲·풀밭)

SKY_TOP, SKY_MID, SKY_LOW = "#5b8fd9", "#8fc0ee", "#cfe8f7"
SCENE_COLORS = {
    "A": SKY_TOP, "B": SKY_MID, "C": SKY_LOW, "c": "#ffffff", "d": "#dbe7f2",
    "M": "#7d7fb3", "m": "#5f6194", "s": "#f2f4fb",                    # 먼 산·그늘·눈
    "H": "#8fae6a",                                                    # 언덕
    "X": "#9a9aa6", "x": "#6f6f7c", "o": "#2d2d3a", "r": "#c0392b", "R": "#e2574c", "y": "#5b4636",  # 성
    "T": "#2f6b3a", "t": "#1f4d2a", "u": "#3f8a4a",                    # 숲
    "G": "#79b84f", "g": "#5f9c3c", "f": "#f2e46b", "w": "#ffffff", "e": "#c56bd1",  # 풀밭·꽃
    "P": "#c9a76b", "p": "#b08d55",                                    # 흙길
}
HORIZON = 59                   # 풀밭이 시작하는 줄 (화면 236px / 4)


def _mountain_height(x):
    """먼 산 높이(줄): 봉우리 몇 개를 직선으로 이은 모양."""
    peaks = [(0, 40), (22, 26), (45, 42), (70, 22), (98, 38), (125, 28), (150, 44), (178, 24), (205, 40),
             (232, 30), (260, 44)]
    for (x0, h0), (x1, h1) in zip(peaks, peaks[1:]):
        if x0 <= x <= x1:
            return h0 + (h1 - h0) * (x - x0) // (x1 - x0)
    return 44


def scene(width=250, height=150, lanes=(), field_x=0):
    """판타지 배경 격자 (격자, 색표). lanes는 흙길 줄(발 위치, 칸), field_x부터 오른쪽에만 흙길을 깐다."""
    grid = [[CLEAR] * width for _ in range(height)]
    # 하늘: 세 가지 색을 Bayer로 섞어 그러데이션
    for y in range(HORIZON):
        for x in range(width):
            level = y * 32 // HORIZON                                   # 0~31
            band = level // 16
            ch = ("A", "B", "C")[band] if BAYER4[y % 4][x % 4] >= level % 16 else ("A", "B", "C")[min(band + 1, 2)]
            grid[y][x] = ch
    # 구름
    for cx, cy, w in ((18, 8, 16), (70, 14, 12), (150, 6, 18), (215, 16, 12)):
        for y in range(cy, cy + 4):
            shrink = abs(y - cy - 1.5) * 2
            for x in range(int(cx + shrink), int(cx + w - shrink)):
                if 0 <= x < width:
                    grid[y][x] = "d" if y == cy + 3 else "c"
    # 먼 산 (눈 덮인 봉우리)
    for x in range(width):
        top = _mountain_height(x)
        for y in range(top, HORIZON):
            if y < top + 2 and top < 30:
                grid[y][x] = "s"
            else:
                grid[y][x] = "m" if (x + y) % 7 == 0 or y > HORIZON - 6 else "M"
    # 성 (오른쪽 언덕 위): 성벽, 탑 셋, 깃발, 문
    hill = lambda x: 50 + abs(x - 205) // 8                             # noqa: E731
    for x in range(160, 250):
        for y in range(max(hill(x), 44), HORIZON):
            grid[y][x] = "H"
    walls = [(185, 228, 38, 50)]
    towers = [(180, 188, 26), (202, 211, 20), (225, 233, 28)]
    for x0, x1, y0, y1 in walls:
        for y in range(y0, y1):
            for x in range(x0, x1):
                grid[y][x] = "x" if (y - y0) % 4 == 3 or (x + (y // 4) * 2) % 6 == 0 else "X"
        for x in range(x0, x1, 3):
            grid[y0 - 1][x] = "X"
    for x0, x1, top in towers:
        for y in range(top, 50):
            for x in range(x0, x1):
                grid[y][x] = "x" if x in (x0, x1 - 1) or (y - top) % 5 == 4 else "X"
        for x in range(x0 - 1, x1 + 1):                                 # 뾰족 지붕
            pass
        mid = (x0 + x1 - 1) / 2
        for k in range(6):
            for x in range(x0 - 1, x1 + 1):
                if abs(x - mid) <= 5 - k:
                    grid[top - 1 - k][x] = "r" if x < mid else "R"
        grid[top + 4][int(mid)] = "o"                                   # 창
        grid[top + 5][int(mid)] = "o"
        pole = int(mid)
        for y in range(top - 11, top - 6):
            grid[y][pole] = "y"
        for y in range(top - 11, top - 8):
            for x in range(pole + 1, pole + 4):
                grid[y][x] = "R"
    for y in range(43, 50):                                             # 성문
        for x in range(203, 210):
            if y > 44 or 205 <= x <= 207:
                grid[y][x] = "o"
    # 숲 (지평선 앞 나무 띠)
    for x in range(width):
        base = HORIZON
        tree = (x * 7) % 11
        top = base - 5 - (tree % 4)
        for y in range(top, base):
            grid[y][x] = "t" if (x % 4 == 0 and y > top + 1) else ("u" if y == top else "T")
    # 풀밭: 결과 작은 꽃
    for y in range(HORIZON, height):
        for x in range(width):
            v = noise(x, y, 1)
            grid[y][x] = "g" if v < 14 else "G"
            if v == 99 and y > HORIZON + 4:
                grid[y][x] = ("f", "w", "e")[noise(x, y, 2) % 3]
    # 흙길 (적이 걷는 줄)
    for lane in lanes:
        for y in range(lane - 3, lane + 2):
            for x in range(field_x, width):
                if 0 <= y < height:
                    edge = y in (lane - 3, lane + 1)
                    if not edge or noise(x, y, 4) < 60:
                        grid[y][x] = "p" if (edge or noise(x, y, 6) < 15) else "P"
    return ["".join(r) for r in grid], SCENE_COLORS


# ---------------------------------------------------------------- tkinter 이미지 (캐시)
# Tk 창(인터프리터)마다 이미지가 따로라서, 캐시는 (그 창, 이름, 배율)로 나눈다.
_CACHE = {}


def to_photo(master, rows, colors, scale=DOT):
    """격자를 master 창의 tk.PhotoImage로 찍고 scale배로 키운다(zoom, 흐림 없음). 투명 칸은 찍지 않는다."""
    import tkinter as tk
    width, height = check_sprite(rows, colors)
    img = tk.PhotoImage(master=master, width=width, height=height)
    for y, row in enumerate(rows):
        x = 0
        while x < width:
            if row[x] == CLEAR:
                x += 1
                continue
            start = x
            while x < width and row[x] != CLEAR:
                x += 1
            img.put("{" + " ".join(colors[ch] for ch in row[start:x]) + "}", to=(start, y))
    return img.zoom(scale, scale) if scale != 1 else img


def photo(widget, key, build, scale=DOT):
    """widget이 속한 창에서 key로 캐시한 이미지. 없으면 build()가 돌려준 (격자, 색표)로 한 번만 만든다.
    참조는 _CACHE가 붙잡아 가비지 컬렉션으로 그림이 사라지지 않는다."""
    root = widget._root()
    full = (root.tk, key, scale)            # root.tk = 그 창의 Tcl 인터프리터 (창마다 다르다)
    if full not in _CACHE:
        rows, colors = build()
        _CACHE[full] = to_photo(root, rows, colors, scale)
    return _CACHE[full]


def forget(widget):
    """widget이 속한 창의 이미지만 캐시에서 버린다 (창을 닫을 때 부른다)."""
    interp = widget._root().tk
    for key in [k for k in _CACHE if k[0] is interp]:
        del _CACHE[key]


def clear_cache():
    """모든 창의 이미지를 캐시에서 버린다 (테스트용)."""
    _CACHE.clear()


def all_sprites():
    """확인용: 고정된 모든 스프라이트 {이름: (격자, 색표)}."""
    out = {"성재 얼굴": whole_face(SEONGJAE), "최산 얼굴": whole_face(CHOISAN),
           "별": (STAR, STAR_COLORS), "총알": (SHOT, SHOT_COLORS), "하트": (HEART, HEART_COLORS),
           "반짝임0": (SPARKLE[0], SPARKLE_COLORS), "반짝임1": (SPARKLE[1], SPARKLE_COLORS),
           "화살표": (ARROW_UP, ARROW_COLORS), "말풍선": bubble(62, 31, 38), "동전": (COIN, COIN_COLORS), "지휘대": (PODIUM, WOOD_COLORS),
           "몸통": (torso(), hero_colors(0)), "몸통 튕기기": (torso(1), hero_colors(0)),
           "몸통 크게": (torso(2), hero_colors(0)), "팔": (ARM_DOWN, hero_colors(0)),
           "팔 가슴": (ARM_CHEST, hero_colors(0)), "팔 툭": (ARM_DROP, hero_colors(0)),
           "팔 크게": (ARM_FLEX, hero_colors(0)),
           "드래곤0": dragon(0), "드래곤1": dragon(1), "바리케이드": barricade(40),
           "나무판": wood_frame(20, 10), "판자": wood_frame(20, 10, inner="W")}
    for name, _ in RANKS:
        out["박산 " + name] = hero(dict(RANKS)[name], name)
    for kind in BULLETS:
        out["병사 " + kind] = soldier(kind)
        out["병사 사격 " + kind] = soldier(kind, firing=True)
        out["총알 " + kind] = bullet_icon(kind)
    for kind in ENEMIES:
        for f in (0, 1):
            out[kind + str(f)] = enemy(kind, f)
    return out
