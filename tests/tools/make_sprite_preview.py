# 도트 그림 미리보기 (사장 검토·README용):
#   images/sprites_preview.png  박산·병사·적·드래곤·총알·하트·바리케이드·버튼·정보판
#   images/faces_preview.png    계급 5단계 도트 얼굴
#   _captures/02_mock.png       새 그래픽을 입힌 준비 화면 시안
#   images/dance_preview.png    춤 도트 자세 3장
# images/의 것은 _captures/에도 복사한다. 키·마우스 입력은 보내지 않고 창만 캡처한다(키 입력 안전 규칙).
# 실행 (앱 폴더에서): python tests/tools/make_sprite_preview.py
import os
import shutil
import subprocess
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(APP_DIR, "src"))

import character  # noqa: E402
import pixel_art as pa  # noqa: E402
from symbols import BULLET_ORDER, RANKS, SOLDIERS  # noqa: E402

OUT = os.path.join(APP_DIR, "_captures")
IMAGES = os.path.join(APP_DIR, "images")
FONT = "Malgun Gothic"
INK = "#2e1d12"


def capture(root, canvas, path):
    """canvas 영역만 화면에서 복사해 png로 저장한다."""
    root.lift()
    root.update()
    root.after(400)
    root.update()
    x, y, w, h = canvas.winfo_rootx(), canvas.winfo_rooty(), canvas.winfo_width(), canvas.winfo_height()
    script = ("Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {w}, {h}; "
              "$g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen({x}, {y}, 0, 0, $b.Size); "
              "$b.Save('{p}', [System.Drawing.Imaging.ImageFormat]::Png)").format(w=w, h=h, x=x, y=y, p=path)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print("저장:", path)


def new_canvas(root, w, h, bg):
    for child in root.winfo_children():
        child.destroy()
    canvas = tk.Canvas(root, width=w, height=h, bg=bg, highlightthickness=0)
    canvas.pack()
    root.geometry("{}x{}+10+10".format(w, h))
    return canvas


def put(canvas, key, build, x, y, scale=pa.DOT, anchor="nw"):
    """캐시한 도트 이미지를 (x, y)에 놓는다."""
    return canvas.create_image(x, y, image=pa.photo(canvas, key, build, scale), anchor=anchor)


def label(canvas, x, y, text, size=11, color=INK, anchor="n", bold=True):
    canvas.create_text(x, y, text=text, font=(FONT, size, "bold" if bold else ""), fill=color, anchor=anchor)


def stars(canvas, x, y, count, scale=2):
    """가운데 x에 별 count개."""
    w = 5 * scale + 2
    left = x - (count * w) / 2
    for i in range(count):
        put(canvas, "star", lambda: (pa.STAR, pa.STAR_COLORS), left + i * w, y, scale)


def frame(canvas, key, x, y, w, h, inner="P"):
    """px 크기 w×h인 나무 테두리 판을 (x, y)에 놓는다 (4px 도트)."""
    put(canvas, key, lambda: pa.wood_frame(w // pa.DOT, h // pa.DOT, inner=inner), x, y)


# ---------------------------------------------------------------- 1. 스프라이트 미리보기

def sprites_sheet(root, path):
    c = new_canvas(root, 1100, 640, "#e9dcb8")
    frame(c, "sheet_bg", 0, 0, 1100, 640)
    label(c, 550, 16, "도트 미리보기 — 군인 박산, 판타지 세계로 전입", 16)

    # 박산 이병·하사
    label(c, 125, 52, "지휘관 박산 (지휘대 위)", 12)
    for i, (name, t) in enumerate([("이병", 0.0), ("하사", 1.0)]):
        x = 24 + i * 112
        put(c, "hero_" + name, lambda n=name, t=t: pa.hero(t, n), x, 76, 3)
        label(c, x + 42, 228, name, 11)

    # 병사 5종 ★1 / ★3(사격 프레임)
    label(c, 590, 52, "병사 5종  (윗줄 ★1 / 아랫줄 ★3·사격 프레임)", 12)
    for i, kind in enumerate(BULLET_ORDER):
        x = 280 + i * 125
        stars(c, x + 44, 78, 1)
        put(c, "s1_" + kind, lambda k=kind: pa.soldier(k), x, 92)
        label(c, x + 44, 176, SOLDIERS[kind]["name"], 10)
        stars(c, x + 44, 200, 3)
        put(c, "s3_" + kind, lambda k=kind: pa.soldier(k, firing=True), x, 214)
        label(c, x + 44, 298, SOLDIERS[kind]["name"] + " 사격", 10)

    # 적 3종 × 걷기 2프레임
    label(c, 230, 322, "적 (걷기 2프레임)", 12)
    for i, kind in enumerate(["slime", "goblin", "skeleton"]):
        for f in (0, 1):
            x = 24 + i * 150 + f * 68
            put(c, "e_" + kind + str(f), lambda k=kind, f=f: pa.enemy(k, f), x, 350)
        waves = {"slime": "1~2웨이브", "goblin": "3~5웨이브", "skeleton": "6웨이브~"}[kind]
        label(c, 24 + i * 150 + 66, 430, pa.ENEMY_NAMES[kind] + " · " + waves, 10)

    # 드래곤 보스 2프레임
    label(c, 610, 322, "보스 드래곤 (5웨이브마다, 날갯짓 2프레임)", 12)
    for f in (0, 1):
        put(c, "dragon" + str(f), lambda f=f: pa.dragon(f), 470 + f * 150, 350, 3)

    # 바리케이드
    label(c, 1030, 52, "바리케이드", 12)
    put(c, "barricade", lambda: pa.barricade(48), 1010, 76)

    # 총알 5종
    label(c, 200, 456, "총알 5종", 12)
    for i, kind in enumerate(BULLET_ORDER):
        x = 30 + i * 74
        put(c, "b_" + kind, lambda k=kind: pa.bullet_icon(k), x, 482)
        label(c, x + 14, 552, kind, 10)

    # 하트
    label(c, 470, 456, "하트", 12)
    put(c, "heart", lambda: (pa.HEART, pa.HEART_COLORS), 420, 486)
    put(c, "heart_empty", lambda: (pa.HEART, pa.HEART_EMPTY_COLORS), 478, 486)
    label(c, 438, 524, "있음", 10)
    label(c, 496, 524, "빈 칸", 10)

    # 버튼·정보판
    label(c, 760, 456, "버튼 · 정보판 테두리", 12)
    frame(c, "btn", 560, 486, 112, 44, inner="W")
    label(c, 616, 508, "스핀", 13, "#fff6dc", "center")
    frame(c, "btn", 560, 540, 112, 44, inner="W")
    label(c, 616, 562, "전투 시작", 13, "#fff6dc", "center")
    frame(c, "info_sample", 700, 486, 340, 100)
    label(c, 720, 500, "웨이브 1    계급 이병", 13, INK, "nw", False)
    label(c, 720, 528, "골드 500    다음 스핀 100", 13, "#8a5a00", "nw")
    capture(root, c, path)


# ---------------------------------------------------------------- 2. 계급별 얼굴

def faces_sheet(root, path):
    c = new_canvas(root, 1000, 300, "#e9dcb8")
    frame(c, "faces_bg", 0, 0, 1000, 300)
    label(c, 500, 18, "계급별 도트 얼굴 (성재 → 최산, 계급마다 부위 하나씩)", 15)
    for i, (name, t) in enumerate(RANKS):
        x = 40 + i * 190
        put(c, "face_" + name, lambda t=t: pa.blend_face(t), x, 56, 8)
        label(c, x + 80, 244, name + " " + str(int(t * 100)) + "%", 14)
    capture(root, c, path)


# ---------------------------------------------------------------- 3. 준비 화면 시안 (ui.py 배치 그대로)

def mock_prepare(root, path):
    c = new_canvas(root, 1000, 600, "#79b84f")
    lanes = tuple(y // pa.DOT for y in (340, 446, 552))
    put(c, "scene", lambda: pa.scene(lanes=lanes, field_x=572 // pa.DOT + 2), 0, 0)
    # 정보판
    frame(c, "info", 20, 12, 340, 112)
    label(c, 38, 26, "웨이브 1   계급 이병   이름 박산", 14, INK, "nw", False)
    label(c, 38, 56, "점수 0     처치 0", 14, INK, "nw", False)
    label(c, 38, 86, "골드 400     다음 스핀 150", 14, "#8a5a00", "nw")
    # 슬롯판
    frame(c, "board", 24, 134, 332, 332)
    board = ["보통탄", "보통탄", "보통탄", "연습탄", "예광탄", "철갑탄", "예광탄", "연습탄", "보통탄"]
    for i, kind in enumerate(board):
        x, y = 40 + (i % 3) * 100, 150 + (i // 3) * 100
        c.create_rectangle(x, y, x + 100, y + 100, fill="#fbf3dc", outline="#cbb07a")
        put(c, "b_" + kind, lambda k=kind: pa.bullet_icon(k), x + 50, y + 8, anchor="n")
        label(c, x + 50, y + 74, kind, 10)
    for x in range(40, 340, 100):                                     # 맞은 줄 강조 (도트 노란 테두리)
        for k in range(0, 100, 8):
            c.create_rectangle(x + k, 150, x + k + 4, 154, fill="#ffd60a", outline="")
            c.create_rectangle(x + k + 4, 246, x + k + 8, 250, fill="#ffd60a", outline="")
        c.create_rectangle(x, 150, x + 4, 250, fill="#ffd60a", outline="")
    c.create_rectangle(336, 150, 340, 250, fill="#ffd60a", outline="")
    # 버튼
    frame(c, "btn", 59, 478, 112, 44, inner="W")
    label(c, 115, 500, "스핀", 13, "#fff6dc", "center")
    frame(c, "btn", 209, 478, 112, 44, inner="W")
    label(c, 265, 500, "전투 시작", 13, "#fff6dc", "center")
    # 안내 문구
    frame(c, "msg", 20, 528, 340, 64)
    label(c, 190, 560, "병사 1명 소환! (소총병)", 12, INK, "center")
    # 지휘관 박산 (계급장 포함)
    put(c, "hero_이병", lambda: pa.hero(0.0, "이병"), 408, 36)
    # 하트
    label(c, 846, 30, "하트", 12, "#fff6dc", "e")
    for i in range(3):
        put(c, "heart", lambda: (pa.HEART, pa.HEART_COLORS), 856 + i * 40, 16)
    # 병사 칸 6개
    soldiers = [("연습탄", 1), ("보통탄", 2)]
    for i in range(6):
        x, y = 392 + (i % 2) * 82, 240 + (i // 2) * 114
        frame(c, "slot", x, y, 76, 108)
        if i < len(soldiers):
            kind, star = soldiers[i]
            stars(c, x + 38, y + 10, star)
            put(c, "s1_" + kind, lambda k=kind: pa.soldier(k), x + 6, y + 22, 3)
            label(c, x + 38, y + 84, SOLDIERS[kind]["name"], 9)
        else:
            label(c, x + 38, y + 46, "빈 칸", 9, "#9c8659", bold=False)
    # 바리케이드와 글자
    put(c, "barricade_tall", lambda: pa.barricade(88), 558, 246)
    label(c, 604, 252, "방어선", 11, "#fff6dc", "nw")
    label(c, 972, 252, "몬스터 출현 ▶", 11, "#fff6dc", "ne")
    capture(root, c, path)


# ---------------------------------------------------------------- 4. 춤 도트 자세

def dance_sheet(root, path):
    """웨이브를 막았을 때 추는 춤의 도트 자세 3장 (가슴 앞 → 손 툭 내리며 튕기기 → 마지막 크게)."""
    c = new_canvas(root, 820, 470, "#e9dcb8")
    frame(c, "dance_bg", 0, 0, 820, 470)
    label(c, 410, 16, "춤 도트 자세 (병장)", 15)
    steps = character.DANCE_STEPS
    poses = [("1. 가슴 앞", steps[0][1]), ("2. 툭 내리며 튕기기", steps[1][1]), ("3. 마지막 크게", steps[-1][1])]
    for i, (name, pose) in enumerate(poses):
        x = 20 + i * 265
        character.draw_character(c, x, 44, 0.75, "병장", pose=pose, scale=1.0, tag="d" + str(i))
        label(c, x + 120, 416, name, 13)
    capture(root, c, path)


def main():
    root = tk.Tk()
    root.overrideredirect(True)          # 제목줄 없이 캔버스만
    root.attributes("-topmost", True)
    os.makedirs(OUT, exist_ok=True)
    try:
        sprites_sheet(root, os.path.join(IMAGES, "sprites_preview.png"))
        faces_sheet(root, os.path.join(IMAGES, "faces_preview.png"))
        mock_prepare(root, os.path.join(OUT, "02_mock.png"))
        dance_sheet(root, os.path.join(IMAGES, "dance_preview.png"))
    finally:
        pa.clear_cache()
        root.destroy()
    for name in ("sprites_preview.png", "faces_preview.png", "dance_preview.png"):
        shutil.copy(os.path.join(IMAGES, name), os.path.join(OUT, name))
        print("복사: _captures/" + name)


if __name__ == "__main__":
    main()
