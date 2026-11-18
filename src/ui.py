# tkinter 화면 5개(시작·게임·상점·게임 오버·랭킹)와 판타지 배경, 스핀·전투·춤·말풍선 움직임을 맡는다.
# 규칙은 game.py, 그림은 pixel_art.py·symbols.py·character.py, 저장은 db.py에 맡기고 여기서는 화면만 다룬다.
# 게임 화면 왼쪽은 준비 단계(골드·3x3 슬롯판·[스핀][전투 시작]), 오른쪽은 전장(지휘관 박산·병사 6칸·몬스터)이다.
# 그림은 모두 도트 이미지(pixel_art.photo, 처음 한 번 만들어 캐시)이고, 전투 중 움직임은 캔버스 항목을
# 새로 만들지 않고 coords(위치)와 itemconfig(그림 프레임)로 바꾼다.
import random
import sqlite3
import tkinter as tk
from tkinter import ttk

import character
import db
import pixel_art as pa
from game import FIELD, LINES, MAX_HEARTS, Game, clean_name, shop_label
from symbols import SOLDIERS, draw_bullet, draw_highlight

TITLE = "박산 키우기"
FONT = "Malgun Gothic"
TABLE_FONT_SIZE = 12

# 창과 게임 화면 크기 (px)
# 최소 창 1000×620 근거: 1920×1080 화면 150% 배율 = 논리 1280×720. 작업표시줄(약 48)을 빼면 높이 672,
# 창 620 + 제목줄·테두리 약 39 = 659 ≤ 672. 너비 1000 + 테두리 약 16 = 1016 ≤ 1280.
CANVAS_W, CANVAS_H = 1000, 600
MIN_W, MIN_H = 1000, 620
DEFAULT_W, DEFAULT_H = 1100, 620
CELL = 100                         # 슬롯 칸 한 변 (가장 작은 창에서도 이 크기)
BOARD_X, BOARD_Y = 40, 150         # 3x3 판 왼쪽 위

# 전장
HERO_SCALE = 0.6
CHAR_X, CHAR_Y = 392, 8            # 지휘관 박산 영역 왼쪽 위 (character.WIDTH × HEIGHT × 0.6)
BUBBLE_BOX = (548, 18, 250, 124)   # 말풍선 영역 (x, y, 너비, 높이): 지휘관 오른쪽 위, 하트 글자 왼쪽까지
SLOT_X, SLOT_Y = 392, 240          # 병사 칸 6개 (2열 × 3줄) 왼쪽 위
SLOT_W, SLOT_H, SLOT_GAP = 76, 108, 6
LINE_X = 572                       # 방어선(바리케이드) 가운데 x
ENEMY_X0, ENEMY_X1 = 592, 972      # 적 위치 0(방어선 앞)과 FIELD(나오는 곳)의 화면 x
LANE_Y = (340, 446, 552)           # 적이 걷는 세 줄 (발 위치)
HEART_X, HEART_Y = 868, 30         # 하트 첫 칸 가운데

# 도트 배율과 움직임 (틱 = TICK_MS)
SOLDIER_DOT = 3                    # 병사 22×20칸 → 66×60px
DRAGON_DOT = 6                     # 드래곤 40×26칸 → 240×156px (고블린 72px 높이의 약 2배)
BOSS_DROP = 20                     # 드래곤 발을 가운데 줄보다 조금 아래로 (BOSS 글자가 "몬스터 출현"과 안 겹치게)
WALK_TICKS = 4                     # 적 걷기 프레임을 바꾸는 틱 수
DRAGON_TICKS = 6                   # 드래곤 날갯짓
SHOT_TICKS = 6                     # 총알이 총구에서 적까지 날아가는 틱 수
MUZZLE = (21 * SOLDIER_DOT + 4, 11 * SOLDIER_DOT + 18)   # 병사 칸 왼쪽 위에서 총구까지 (px)

# 게임 오버 화면의 캐릭터와 말풍선
OVER_CHAR = (680, 220, 1.0)
OVER_BUBBLE = (620, 40, 340, 150)

# 시간 (ms)
BUBBLE_MS = 2500
ROLL_STEPS, ROLL_MS = 6, 600       # 스핀할 때 굴러가는 그림 6장, 모두 0.6초
TICK_MS = 33                       # 전투 화면을 다시 그리는 간격 (초당 약 30번)
FLASH_MS = 900                     # 소환·합체 표시가 보이는 시간
OVER_PAUSE_MS = 700                # 마지막 적이 지나간 뒤 게임 오버 화면까지

# 문구
BUBBLE_PASS = "난 최산을 닮았다"
BUBBLE_NEXT = "난 섹시해.... ㅋ"
BUBBLE_OVER = "she's so BAD..."
MSG_SAVED = "기록이 DB에 저장되었습니다"
MSG_SAVE_FAIL = "기록을 저장하지 못했습니다"
MSG_LOAD_FAIL = "기록을 불러오지 못했습니다"
MSG_NO_RECORDS = "아직 기록이 없습니다"
MSG_READY = "스핀으로 병사를 모으고 [전투 시작]을 누르세요"

# 색
BG = "#26381f"          # 창이 캔버스보다 클 때 보이는 바깥 (어두운 숲색)
PARCH = "#f3e6c4"       # 양피지 (판 안쪽, 그 위 글자 바탕)
INK = "#1a1a1a"
CREAM = "#fff6dc"       # 나무 판자·풀밭 위 글자
SHADOW = "#2e1d12"      # 풀밭 위 글자 그림자
WOOD_DARK = "#6e4423"
HINT_GRAY = "#a0a0a0"   # 빈 판 안내 글씨
NOTE_GRAY = "#6b6b6b"   # 오류가 아닌 안내 문구
ERROR_RED = "#b00020"   # 오류 문구에만 쓴다
GOOD_GREEN = "#2d6a2d"
GOLD = "#8a5a00"        # 골드 줄 (양피지 위에서 읽히는 진한 금색)
FLASH = "#ffd60a"
CELL_BG = "#fbf3dc"


class App:
    """창 하나에서 화면을 바꿔 가며 한 판을 진행한다."""

    def __init__(self, root, db_path, rng=None, time_scale=1.0):
        self.root = root
        self.db_path = db_path
        self.rng = rng or random.Random()       # 게임 결과용 무작위
        self.roll_rng = random.Random()         # 굴러가는 그림용 무작위 (결과와 상관없음)
        self.time_scale = time_scale            # 테스트에서만 1보다 작게 해 빨리 감는다
        self.after_ids = set()
        self.screen = ""
        self.game = None
        self.player_name = ""
        self.busy = False
        self.dancing = False
        self.bubble_text = ""
        self.bubble_job = None
        self.canvas = None
        self.save_message = ""
        self.result_lines = []
        self.hero_place = (CHAR_X, CHAR_Y, HERO_SCALE)
        self.bubble_box = BUBBLE_BOX
        self.tick_count = 0
        self.enemy_items = {}       # id(적) → (적, 그림, 체력 바탕, 체력 막대, [BOSS 글자]) 캔버스 항목
        self.shot_items = {}        # 병사 칸 번호 → 날아가는 총알 그림 항목
        self.soldier_sprites = []   # [(병사 그림 항목, 총알 종류)] 칸 순서

        try:
            db.init_db(db_path)
            self.db_ok = True
        except sqlite3.Error:
            self.db_ok = False

        root.title(TITLE)
        root.minsize(MIN_W, MIN_H)
        root.geometry(str(DEFAULT_W) + "x" + str(DEFAULT_H))
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.configure("Treeview", font=(FONT, TABLE_FONT_SIZE), rowheight=30, background=CELL_BG,
                        fieldbackground=CELL_BG)
        style.configure("Treeview.Heading", font=(FONT, TABLE_FONT_SIZE, "bold"))
        self.frame = tk.Frame(root, bg=BG)
        self.frame.pack(expand=True)
        self.show_start()

    # ---- 예약(after) 관리 ----

    def later(self, ms, func):
        """ms 뒤에 func를 부르도록 예약하고, 화면을 바꾸거나 창을 닫을 때 취소할 수 있게 기록한다."""
        job = None

        def run():
            self.after_ids.discard(job)
            func()

        job = self.root.after(max(1, int(ms * self.time_scale)), run)
        self.after_ids.add(job)
        return job

    def cancel(self, job):
        """예약 하나를 취소한다."""
        if job in self.after_ids:
            self.root.after_cancel(job)
            self.after_ids.discard(job)

    def cancel_all(self):
        """남은 예약을 모두 취소한다."""
        for job in list(self.after_ids):
            self.cancel(job)

    def close(self):
        """전투·춤·말풍선 예약을 모두 취소하고, 이 창의 도트 이미지 캐시를 비운 뒤 창을 닫는다."""
        self.cancel_all()
        pa.forget(self.root)
        self.root.destroy()

    def clear(self):
        """지금 화면의 위젯과 예약을 모두 지우고 상태를 처음으로 돌린다."""
        self.cancel_all()
        for widget in self.frame.winfo_children():
            widget.destroy()
        self.canvas = None
        self.busy = False
        self.dancing = False
        self.bubble_text = ""
        self.bubble_job = None
        self.enemy_items = {}
        self.shot_items = {}
        self.soldier_sprites = []

    # ---- 도트 그림 도우미 ----

    def new_canvas(self):
        """화면 하나를 그릴 1000×600 캔버스."""
        self.canvas = tk.Canvas(self.frame, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=BG)
        self.canvas.pack()
        return self.canvas

    def scene(self, canvas, lanes=True):
        """판타지 배경(하늘·산·성·숲·풀밭). lanes면 바리케이드 오른쪽에 몬스터가 걷는 흙길 세 줄."""
        cells = tuple(y // pa.DOT for y in LANE_Y) if lanes else ()
        img = pa.photo(canvas, ("scene", lanes), lambda: pa.scene(lanes=cells, field_x=LINE_X // pa.DOT + 2))
        canvas.create_image(0, 0, image=img, anchor="nw", tags="scene")

    def panel(self, canvas, x, y, w, h, inner="P", border=2, tag="panel"):
        """(x, y)에 w×h px 나무 테두리 판을 놓는다 (inner P 양피지, W 나무 판자)."""
        cols, rows = w // pa.DOT, h // pa.DOT
        img = pa.photo(canvas, ("frame", cols, rows, inner, border), lambda: pa.wood_frame(cols, rows, border, inner))
        return canvas.create_image(x, y, image=img, anchor="nw", tags=tag)

    def shadow_text(self, canvas, x, y, text, size=11, anchor="nw", tags=()):
        """풀밭·하늘 위에서도 읽히게 그림자를 깐 크림색 굵은 글자."""
        canvas.create_text(x + 1, y + 1, text=text, anchor=anchor, font=(FONT, size, "bold"), fill=SHADOW, tags=tags)
        canvas.create_text(x, y, text=text, anchor=anchor, font=(FONT, size, "bold"), fill=CREAM, tags=tags)

    def plank(self, widget, px, dark):
        """버튼용 나무 판자 그림 (dark면 눌 수 없을 때의 어두운 판자)."""
        cols = px // pa.DOT

        def build():
            rows, colors = pa.wood_frame(cols, 11, 2, "W")
            if dark:
                colors = {k: pa.mix_color(v, "#3a3a3a", 0.5) for k, v in colors.items()}
            return rows, colors
        return pa.photo(widget, ("plank", cols, dark), build)

    def button(self, parent, text, command, width=12):
        """나무 판자 그림 위에 크림색 글씨 버튼 (width 10 이하 112px, 그보다 크면 136px)."""
        px = 112 if width <= 10 else 136
        b = tk.Button(parent, text=text, command=command, compound="center", font=(FONT, 13, "bold"),
                      fg=CREAM, activeforeground="#ffffff", disabledforeground="#e6dcc0", bg=BG, activebackground=BG,
                      relief="flat", bd=0, highlightthickness=0, padx=0, pady=0, cursor="hand2")
        b.planks = (self.plank(parent, px, False), self.plank(parent, px, True))
        b.config(image=b.planks[0])
        return b

    def set_enabled(self, button, enabled):
        """버튼을 열거나 막고, 막힌 버튼은 어두운 판자로 보여 준다."""
        button.config(state="normal" if enabled else "disabled", image=button.planks[0 if enabled else 1])

    def sprite(self, key, build, scale=pa.DOT):
        """지금 캔버스 창의 캐시된 도트 이미지."""
        return pa.photo(self.canvas, key, build, scale)

    def soldier_img(self, kind, firing=False):
        return self.sprite(("soldier", kind, firing), lambda: pa.soldier(kind, firing), SOLDIER_DOT)

    def enemy_img(self, kind, frame):
        if kind == "dragon":
            return self.sprite(("dragon", frame), lambda: pa.dragon(frame), DRAGON_DOT)
        return self.sprite(("enemy", kind, frame), lambda: pa.enemy(kind, frame))

    def sparkle_img(self, frame):
        return self.sprite(("sparkle", frame), lambda: (pa.SPARKLE[frame], pa.SPARKLE_COLORS), 3)

    # ---- 시작 화면 ----

    def show_start(self):
        """시작 화면: 제목, 지휘대 위 이병 박산, 이름 입력, [게임 시작] [랭킹 보기] [종료]."""
        self.clear()
        self.screen = "start"
        c = self.new_canvas()
        self.scene(c, lanes=False)
        self.panel(c, 260, 16, 480, 568)
        self.title_label = tk.Label(c, text=TITLE, font=(FONT, 28, "bold"), bg=PARCH, fg=INK)
        c.create_window(500, 60, window=self.title_label)
        c.create_text(500, 100, text="군인 박산, 판타지 세계로 전입", font=(FONT, 12), fill=NOTE_GRAY)
        character.draw_character(c, 410, 112, 0.0, "이병", scale=0.75, tag="hero")
        c.create_text(500, 398, text="계급: 이병", font=(FONT, 14), fill=INK)
        c.create_text(500, 428, text="이름 (1~10글자)", font=(FONT, 12), fill=INK)
        self.name_entry = tk.Entry(c, font=(FONT, 14), width=16, justify="center", relief="solid", bd=1)
        self.name_entry.insert(0, self.player_name)
        self.name_entry.bind("<Return>", lambda event: self.start_game())
        c.create_window(500, 456, window=self.name_entry)
        self.name_message = tk.Label(c, text="", font=(FONT, 11), bg=PARCH, fg=ERROR_RED)
        c.create_window(500, 486, window=self.name_message)
        self.start_button = self.button(c, "게임 시작", self.start_game, width=10)
        self.ranking_button = self.button(c, "랭킹 보기", self.show_ranking, width=10)
        self.quit_button = self.button(c, "종료", self.close, width=10)
        for x, b in zip((380, 500, 620), (self.start_button, self.ranking_button, self.quit_button)):
            c.create_window(x, 540, window=b)

    def start_game(self):
        """이름을 확인하고 플레이어를 등록한 뒤 1웨이브 준비 단계를 시작한다."""
        name, message = clean_name(self.name_entry.get())
        if name is None:
            self.name_message.config(text=message)
            return
        self.player_name = name
        try:
            db.get_or_create_player(self.db_path, name)
        except sqlite3.Error:
            pass  # 게임 오버 때 save_record()가 같은 이름을 다시 등록하므로 여기서는 넘어간다
        self.game = Game()
        self.show_game()

    # ---- 게임 화면 ----

    def show_game(self):
        """게임 화면: 왼쪽 준비 단계(정보·3x3 판·버튼), 오른쪽 전장(지휘관·병사 6칸·바리케이드·몬스터)."""
        self.clear()
        self.screen = "game"
        self.hero_place = (CHAR_X, CHAR_Y, HERO_SCALE)
        self.bubble_box = BUBBLE_BOX
        c = self.new_canvas()
        self.scene(c)
        self.draw_battlefield()
        self.panel(c, 20, 12, 340, 112)
        self.panel(c, BOARD_X - 16, BOARD_Y - 16, 3 * CELL + 32, 3 * CELL + 32, tag=("panel", "board"))
        self.panel(c, 20, 528, 340, 64)
        self.spin_button = self.button(c, "스핀", self.on_spin, width=10)
        self.battle_button = self.button(c, "전투 시작", self.on_battle, width=10)
        c.create_window(BOARD_X + 0.75 * CELL, BOARD_Y + 3 * CELL + 52, window=self.spin_button)
        c.create_window(BOARD_X + 2.25 * CELL, BOARD_Y + 3 * CELL + 52, window=self.battle_button)
        self.draw_board(self.game.board, [])
        self.draw_soldiers()
        self.draw_hearts()
        self.draw_enemies()
        self.draw_hero()
        self.update_info()
        self.set_message(MSG_READY, NOTE_GRAY)
        self.update_buttons()

    def draw_battlefield(self):
        """방어선(나무 바리케이드)과 몬스터가 나오는 곳 표시."""
        c = self.canvas
        rows = (CANVAS_H - 246) // pa.DOT
        img = self.sprite(("barricade", rows), lambda: pa.barricade(rows))
        c.create_image(LINE_X - 20, 246, image=img, anchor="nw", tags="barricade")
        self.shadow_text(c, LINE_X + 26, 250, "방어선")
        self.shadow_text(c, ENEMY_X1, 250, "몬스터 출현 ▶", anchor="ne")

    def draw_board(self, board, lines):
        """9칸에 총알 도트를 그리고, 맞은 줄의 칸은 노란 테두리로 강조한다."""
        self.canvas.delete("cell")
        lit = {i for line in lines for i in line}
        for i in range(9):
            x = BOARD_X + (i % 3) * CELL
            y = BOARD_Y + (i // 3) * CELL
            self.canvas.create_rectangle(x, y, x + CELL, y + CELL, fill=CELL_BG, outline="#cbb07a",
                                         tags=("board", "cell"))
            if board:
                draw_bullet(self.canvas, board[i], x, y, CELL, tag=("board", "cell"))
            if i in lit:
                draw_highlight(self.canvas, x, y, CELL, tag=("board", "cell"))
        if not board:
            self.canvas.create_text(BOARD_X + 1.5 * CELL, BOARD_Y + 1.5 * CELL, text="스핀을 눌러 시작하세요",
                                    font=(FONT, 16, "bold"), fill=HINT_GRAY, tags=("board", "cell", "hint"))

    def draw_hero(self, pose=None):
        """지금 계급의 얼굴과 계급장으로 지휘대 위 박산을 다시 그린다 (게임 화면은 지휘관 자리에 0.6배)."""
        x, y, scale = self.hero_place
        self.canvas.delete("hero")
        character.draw_character(self.canvas, x, y, self.game.face_ratio, self.game.rank,
                                 pose=pose, scale=scale, tag="hero")
        self.canvas.tag_raise("bubble")

    def slot_xy(self, i):
        """병사 칸 i(0~5)의 왼쪽 위 좌표. 2열 × 3줄."""
        return SLOT_X + (i % 2) * (SLOT_W + SLOT_GAP), SLOT_Y + (i // 2) * (SLOT_H + SLOT_GAP)

    def draw_soldiers(self):
        """병사 칸 6개(나무 테두리)와 병사(도트 + 별 + 이름)를 그린다. 전투 중 사격 프레임도 처음으로 돌린다."""
        c = self.canvas
        c.delete("soldier")
        self.soldier_sprites = []
        cols, rows = SLOT_W // pa.DOT, SLOT_H // pa.DOT
        slot = self.sprite(("slot", cols, rows), lambda: pa.wood_frame(cols, rows, 1, "P"))
        for i in range(6):
            x, y = self.slot_xy(i)
            c.create_image(x, y, image=slot, anchor="nw", tags=("soldier", "slot_box"))
            if i >= len(self.game.soldiers):
                c.create_text(x + SLOT_W / 2, y + SLOT_H / 2, text="빈 칸", font=(FONT, 10), fill=HINT_GRAY,
                              tags="soldier")
                continue
            kind, star = self.game.soldiers[i]
            self.draw_soldier_figure(x, y, kind, star)

    def draw_soldier_figure(self, x, y, kind, star):
        """칸 하나(왼쪽 위 x, y)에 병사를 그린다: 맨 위 도트 별 개수, 군복 병사 도트, 맨 아래 병사 이름."""
        c = self.canvas
        star_img = self.sprite(("star",), lambda: (pa.STAR, pa.STAR_COLORS), 2)
        for s in range(star):
            sx = x + SLOT_W / 2 + (s - (star - 1) / 2) * 13
            c.create_image(sx, y + 11, image=star_img, tags=("soldier", "star"))
        item = c.create_image(x + 4, y + 18, image=self.soldier_img(kind), anchor="nw",
                              tags=("soldier", "soldier_sprite"))
        self.soldier_sprites.append((item, kind))
        c.create_text(x + SLOT_W / 2, y + SLOT_H - 18, text=SOLDIERS[kind]["name"], font=(FONT, 10, "bold"), fill=INK,
                      tags="soldier")

    def flash_slots(self, before):
        """스핀 전과 달라진 병사 칸에 노란 테두리와 "합체!"·"소환" 글자, 합체면 반짝임 도트를 잠깐 보여 준다."""
        c = self.canvas
        c.delete("flash")
        for i, soldier in enumerate(self.game.soldiers):
            if i < len(before) and before[i] == soldier:
                continue
            x, y = self.slot_xy(i)
            merged = soldier[1] > 1
            c.create_rectangle(x - 2, y - 2, x + SLOT_W + 2, y + SLOT_H + 2, outline=FLASH, width=4, tags="flash")
            c.create_rectangle(x + 4, y + 52, x + SLOT_W - 4, y + 72, fill=FLASH, outline=INK, tags="flash")
            c.create_text(x + SLOT_W / 2, y + 62, text="합체! ★" + str(soldier[1]) if merged else "소환",
                          font=(FONT, 11, "bold"), fill="#8b1a1a" if merged else INK, tags="flash")
            if merged:
                for k, (sx, sy) in enumerate(((x + 10, y + 30), (x + SLOT_W - 10, y + 40), (x + 16, y + 88))):
                    c.create_image(sx, sy, image=self.sparkle_img(k % 2), tags=("flash", "sparkle"))
        if c.find_withtag("sparkle"):
            self.later(FLASH_MS / 3, self.twinkle)
            self.later(FLASH_MS * 2 / 3, self.twinkle)
        self.later(FLASH_MS, lambda: self.canvas is not None and self.canvas.delete("flash"))

    def twinkle(self):
        """반짝임 도트의 큰 별·작은 별 프레임을 맞바꾼다."""
        if self.canvas is None:
            return
        big, small = str(self.sparkle_img(0)), str(self.sparkle_img(1))
        for item in self.canvas.find_withtag("sparkle"):
            now = self.canvas.itemcget(item, "image")
            self.canvas.itemconfig(item, image=small if now == big else big)

    def draw_hearts(self):
        """오른쪽 위에 지금 하트 수만큼 도트 하트를 그린다 (최대 5)."""
        c = self.canvas
        c.delete("hearts")
        c.delete("hearts_label")
        self.shadow_text(c, HEART_X - 22, HEART_Y, "하트", size=12, anchor="e", tags="hearts_label")
        heart = self.sprite(("heart",), lambda: (pa.HEART, pa.HEART_COLORS), 3)
        for i in range(max(0, min(self.game.hearts, MAX_HEARTS))):
            c.create_image(HEART_X - 13 + i * 28, HEART_Y - 12, image=heart, anchor="nw", tags="hearts")

    def enemy_screen_x(self, enemy):
        """적의 거리(0=방어선 ~ FIELD=나오는 곳)를 화면 x로 바꾼다."""
        return ENEMY_X0 + (ENEMY_X1 - ENEMY_X0) * max(0.0, enemy["x"]) / FIELD

    def draw_enemies(self):
        """전장의 몬스터(웨이브에 따라 슬라임·고블린·해골 병사)와 보스 드래곤을 체력 막대와 함께 그린다.
        이미 있는 몬스터는 캔버스 항목을 그대로 두고 위치(coords)와 걷기 프레임(itemconfig)만 바꾼다."""
        c = self.canvas
        seen = set()
        for enemy in self.game.enemies:
            key = id(enemy)
            entry = self.enemy_items.get(key)
            if entry is not None and entry[0] is not enemy:
                self.delete_enemy(key)
                entry = None
            boss = enemy["boss"]
            kind = "dragon" if boss else pa.enemy_kind(self.game.wave)
            lane = 1 if boss else enemy.get("lane", 0) % 3
            frame = (self.tick_count // (DRAGON_TICKS if boss else WALK_TICKS) + lane) % 2
            img = self.enemy_img(kind, frame)
            half = img.width() / 2
            x = min(self.enemy_screen_x(enemy), CANVAS_W - half - 2)        # 나올 때도 화면 안에
            x = max(x, ENEMY_X0 - 32 + half)       # 큰 드래곤도 왼쪽 끝은 바리케이드까지만 (병사 칸을 덮지 않게)
            y = LANE_Y[lane] + (BOSS_DROP if boss else 0)
            top = y - img.height()
            bar_w, bar_h = (120, 10) if boss else (40, 6)
            ratio = max(0.0, enemy["hp"] / enemy["max_hp"])
            if entry is None:
                pic = c.create_image(x, y, image=img, anchor="s", tags=("enemy", kind))
                back = c.create_rectangle(0, 0, 0, 0, fill="#3a3a3a", outline="", tags="enemy")
                bar = c.create_rectangle(0, 0, 0, 0, fill="#e63946", outline="", tags="enemy")
                label = ()
                if boss:                                            # 보스는 막대 위에 "BOSS" (그림자 + 글자)
                    label = tuple(c.create_text(0, 0, text="BOSS", anchor="s", font=(FONT, 14, "bold"), fill=color,
                                                tags="boss_label") for color in (SHADOW, FLASH))
                entry = (enemy, pic, back, bar, label)
                self.enemy_items[key] = entry
            _, pic, back, bar, label = entry
            c.coords(pic, x, y)
            c.itemconfig(pic, image=img)
            c.coords(back, x - bar_w / 2, top - 4 - bar_h, x + bar_w / 2, top - 4)
            c.coords(bar, x - bar_w / 2, top - 4 - bar_h, x - bar_w / 2 + bar_w * ratio, top - 4)
            for n, item in enumerate(label):
                c.coords(item, x + 1 - n, top - 6 - bar_h + 1 - n)
            seen.add(key)
        for key in [k for k in self.enemy_items if k not in seen]:
            self.delete_enemy(key)

    def delete_enemy(self, key):
        """적 하나의 캔버스 항목(그림·체력 막대·BOSS 글자)을 지우고 목록에서 뺀다."""
        _, pic, back, bar, label = self.enemy_items.pop(key)
        self.canvas.delete(pic, back, bar, *label)

    def draw_shots(self):
        """병사마다 총구에서 방어선에 가장 가까운 적까지 작은 도트 총알이 날아가고, 쏘는 순간 병사는 사격 프레임."""
        c = self.canvas
        g = self.game
        target = min(g.enemies, key=lambda e: e["x"]) if g.enemies else None
        entry = self.enemy_items.get(id(target)) if target is not None else None
        if entry is None:                                           # 쏠 적이 없는 틈: 총알을 숨기고 사격 자세를 푼다
            c.itemconfig("shot", state="hidden")
            for item, kind in self.soldier_sprites:
                c.itemconfig(item, image=self.soldier_img(kind))
            return
        x0, y0, x1, y1 = c.bbox(entry[1])
        tx, ty = (x0 + x1) / 2, (y0 + y1) / 2                       # 적 그림 가운데를 겨눈다
        shot_img = self.sprite(("shot",), lambda: (pa.SHOT, pa.SHOT_COLORS), 3)
        for i, (item, kind) in enumerate(self.soldier_sprites):
            x, y = self.slot_xy(i)
            sx, sy = x + MUZZLE[0], y + MUZZLE[1]
            phase = ((self.tick_count + i * 2) % SHOT_TICKS) / SHOT_TICKS
            px, py = sx + (tx - sx) * phase, sy + (ty - sy) * phase
            shot = self.shot_items.get(i)
            if shot is None:
                shot = c.create_image(px, py, image=shot_img, tags="shot")
                self.shot_items[i] = shot
            c.coords(shot, px, py)
            c.itemconfig(shot, state="normal")
            c.itemconfig(item, image=self.soldier_img(kind, firing=phase < 0.34))

    def update_info(self):
        """정보판 글자: 웨이브·계급·이름, 점수·처치, 골드·다음 스핀 비용."""
        g = self.game
        self.canvas.delete("info")
        cost = g.spin_cost()
        lines = [("웨이브 " + str(g.wave) + "    계급 " + g.rank + "    이름 " + self.player_name, ""),
                 ("점수 " + str(g.score) + "    처치 " + str(g.kills), ""),
                 ("골드 " + str(g.gold) + "    다음 스핀 " + ("무료" if cost == 0 else str(cost)), "bold")]
        for n, (text, weight) in enumerate(lines):
            self.canvas.create_text(36, 36 + n * 29, text=text, anchor="w", font=(FONT, 14, weight),
                                    fill=GOLD if n == 2 else INK, tags="info")

    def set_message(self, text, color=INK):
        """판 아래 안내 문구 한 줄."""
        self.canvas.delete("msg")
        self.canvas.create_text(190, 560, text=text, width=300, justify="center", font=(FONT, 12, "bold"), fill=color,
                                tags="msg")

    def update_buttons(self):
        """준비 단계이고 굴러가는 중·춤추는 중이 아닐 때만 버튼을 연다. [스핀]은 골드도 있어야 한다."""
        ready = self.game.phase == "prepare" and not self.busy and not self.dancing
        self.set_enabled(self.spin_button, ready and self.game.can_spin())
        self.set_enabled(self.battle_button, ready)

    # ---- 스핀 ----

    def on_spin(self):
        """[스핀]: 굴러가는 그림을 보여 준 뒤 결과를 낸다. 굴러가는 중·전투 중·춤추는 중 누른 것은 무시한다."""
        if self.busy or self.dancing or not self.game.can_spin():
            return
        self.busy = True
        self.update_buttons()
        self.roll(0)

    def roll(self, step):
        """굴러가는 그림을 한 장 그리고, 다 그렸으면 실제 스핀 결과(소환·합체)를 보여 준다."""
        if step < ROLL_STEPS:
            fake = [self.roll_rng.choice(self.game.deck) for _ in range(9)]
            self.draw_board(fake, [])
            self.later(ROLL_MS / ROLL_STEPS, lambda: self.roll(step + 1))
            return
        before = list(self.game.soldiers)
        self.game.spin(self.rng)
        board = self.game.board
        matched = [line for line in LINES if board[line[0]] == board[line[1]] == board[line[2]]]
        self.draw_board(board, matched)
        self.draw_soldiers()
        self.flash_slots(before)
        self.update_info()
        self.set_message(self.game.message, NOTE_GRAY if not matched else INK)
        self.busy = False
        self.update_buttons()

    # ---- 전투 ----

    def on_battle(self):
        """[전투 시작]: 버튼을 막고 전투를 시작한다. 준비 단계가 아니거나 굴러가는 중이면 무시한다.
        1웨이브를 병사 0명으로 시작하면 지원군(훈련병★1)이 오고 "지원군 도착!"을 보여 준다."""
        if self.busy or self.dancing or self.game.phase != "prepare":
            return
        self.busy = True
        self.game.start_battle()
        self.update_buttons()
        if self.game.reinforced:
            self.draw_soldiers()
            self.flash_slots([])
            self.set_message(self.game.message, GOOD_GREEN)
        else:
            self.set_message("전투 중! 병사들이 자동으로 쏩니다", INK)
        self.tick_count = 0
        self.later(TICK_MS, self.battle_tick)

    def battle_tick(self):
        """전투를 한 틱 진행하고 다시 그린다. 테스트(time_scale < 1)에서는 한 틱에 여러 걸음을 계산한다."""
        g = self.game
        steps = 1 if self.time_scale >= 1 else min(200, int(round(1 / self.time_scale)))
        for _ in range(steps):
            if g.battle_over:
                break
            g.battle_step(TICK_MS / 1000)
        self.tick_count += 1
        self.draw_enemies()
        self.draw_shots()
        self.draw_hearts()
        self.update_info()
        if not g.battle_over:
            self.later(TICK_MS, self.battle_tick)
            return
        self.canvas.delete("shot")
        self.shot_items = {}
        self.draw_soldiers()
        if g.finish_wave() == "clear":
            self.update_info()
            self.set_message("웨이브를 막았습니다! " + g.rank + " 진급", GOOD_GREEN)
            self.draw_hero()
            self.busy = False
            self.start_dance(self.show_shop)
        else:
            self.set_message("방어선이 뚫렸습니다!", ERROR_RED)
            self.later(OVER_PAUSE_MS, self.show_gameover)

    # ---- 말풍선과 춤 ----

    def show_bubble(self, text, ms=BUBBLE_MS):
        """캐릭터 머리 위에 말풍선을 띄운다. 앞의 말풍선은 바로 지운다. ms가 None이면 계속 보인다."""
        self.hide_bubble()
        x, y, w, h = self.bubble_box
        character.draw_bubble(self.canvas, x, y, w, h, text, tag="bubble")
        self.bubble_text = text
        if ms is not None:
            self.bubble_job = self.later(ms, self.hide_bubble)

    def hide_bubble(self):
        """말풍선을 지운다."""
        if self.bubble_job is not None:
            self.cancel(self.bubble_job)
            self.bubble_job = None
        if self.canvas is not None:
            self.canvas.delete("bubble")
        self.bubble_text = ""

    def start_dance(self, on_done):
        """웨이브를 막은 춤을 춘다(도트 자세 프레임을 바꿔 끼움). 춤추는 동안은 말풍선을 유지하고 버튼을 막는다.
        이미 추고 있으면 False."""
        if self.dancing:
            return False
        self.dancing = True
        self.update_buttons()
        self.show_bubble(BUBBLE_PASS, ms=None)
        elapsed = 0
        for ms, pose in character.DANCE_STEPS:
            self.later(elapsed, lambda pose=pose: self.draw_hero(pose))
            elapsed += ms
        self.later(elapsed, lambda: self.finish_dance(on_done))
        return True

    def finish_dance(self, on_done):
        """춤을 끝내고 말풍선을 지운 뒤 다음 일(상점)로 넘어간다."""
        self.dancing = False
        self.hide_bubble()
        self.draw_hero()
        self.update_buttons()
        on_done()

    # ---- 상점 ----

    def show_shop(self):
        """상점: 4가지 중 3개를 나무 테두리 카드로 보여 주고 1개를 무료로 고른다."""
        g = self.game
        self.clear()
        self.screen = "shop"
        c = self.new_canvas()
        self.scene(c, lanes=False)
        self.panel(c, 170, 14, 660, 92)
        c.create_text(500, 42, text="상점 — 하나를 무료로 고르세요", font=(FONT, 20, "bold"), fill=INK)
        c.create_text(500, 80, text="계급 " + g.rank + "    다음 웨이브 " + str(g.wave) + "    하트 " + str(g.hearts)
                      + "    골드 " + str(g.gold), font=(FONT, 13), fill=INK)
        self.shop_buttons = []
        for k, (item, bullet) in enumerate(g.shop_offer(self.rng)):
            card = tk.Frame(c, bg=PARCH, highlightbackground=WOOD_DARK, highlightcolor=WOOD_DARK, highlightthickness=4)
            pic = tk.Canvas(card, width=160, height=150, bg=PARCH, highlightthickness=0)
            pic.pack(padx=10, pady=(10, 0))
            self.draw_shop_icon(pic, item, bullet)
            title = "덱에 추가" if bullet else shop_label(item, bullet)   # 총알 이름은 그림 아래에 이미 있다
            tk.Label(card, text=title, font=(FONT, 14, "bold"), bg=PARCH, fg=INK).pack()
            tk.Label(card, text=self.shop_help(item, bullet), font=(FONT, 11), bg=PARCH, fg=NOTE_GRAY,
                     wraplength=180, height=2).pack()
            b = self.button(card, "고르기", lambda item=item, bullet=bullet: self.choose(item, bullet), width=10)
            b.pack(pady=10)
            self.shop_buttons.append(b)
            c.create_window(270 + k * 230, 316, window=card)
        self.panel(c, 120, 506, 760, 80)
        soldiers = "  ".join(SOLDIERS[k]["name"] + "★" + str(s) for k, s in g.soldiers) or "없음"
        c.create_text(500, 532, text="병사: " + soldiers, font=(FONT, 12), fill=INK, width=720)
        deck_text = "  ".join(kind + " " + str(n) for kind, n in g.deck_counts().items() if n)
        c.create_text(500, 560, text="지금 덱: " + deck_text, font=(FONT, 12), fill=INK, width=720)

    def shop_help(self, item, bullet):
        """상점 항목 설명 한 줄."""
        if item == "총알 추가":
            return "덱에 " + bullet + " 1개 (" + SOLDIERS[bullet]["name"] + " 소환)"
        return {"하트 +1": "하트 1개 회복 (최대 5)",
                "공격력 +10%": "모든 병사 공격력 +10% (쌓임)",
                "첫 스핀 무료": "다음 준비 단계 첫 스핀 0골드"}[item]

    def draw_shop_icon(self, pic, item, bullet):
        """상점 카드 도트 그림: 총알, 하트, 위 화살표, FREE 동전."""
        if item == "총알 추가":
            draw_bullet(pic, bullet, 5, 0, 150)
            return
        art = {"하트 +1": (pa.HEART, pa.HEART_COLORS, 12), "공격력 +10%": (pa.ARROW_UP, pa.ARROW_COLORS, 9),
               "첫 스핀 무료": (pa.COIN, pa.COIN_COLORS, 9)}[item]
        img = pa.photo(pic, ("shop", item), lambda: art[:2], art[2])
        pic.create_image(80, 75, image=img)
        if item == "첫 스핀 무료":
            pic.create_text(80, 75, text="FREE", font=(FONT, 20, "bold"), fill=INK)

    def choose(self, item, bullet):
        """고른 항목을 적용하고 다음 웨이브 준비 단계를 시작한다 (2웨이브부터 말풍선)."""
        self.game.apply_shop(item, bullet)
        self.show_game()
        self.show_bubble(BUBBLE_NEXT)

    # ---- 게임 오버 ----

    def show_gameover(self):
        """게임 오버: 기록을 저장하고 결과, 캐릭터와 말풍선, 저장 결과 문구를 보여 준다."""
        g = self.game
        try:
            db.init_db(self.db_path)  # 시작할 때 실패했어도 지금 다시 준비해 본다
            db.save_record(self.db_path, self.player_name, g.wave, g.score, g.rank)
            self.save_message = MSG_SAVED
        except sqlite3.Error:
            self.save_message = MSG_SAVE_FAIL
        self.clear()
        self.screen = "gameover"
        self.hero_place = OVER_CHAR
        self.bubble_box = OVER_BUBBLE
        c = self.new_canvas()
        self.scene(c)
        self.draw_hero()
        self.panel(c, 60, 60, 500, 460)
        self.result_lines = ["점수 " + str(g.score), "도달한 웨이브 " + str(g.wave),
                             "처치 " + str(g.kills), "계급 " + g.rank]
        c.create_text(310, 110, text="게임 오버", font=(FONT, 30, "bold"), fill="#8b1a1a")
        for n, text in enumerate(self.result_lines):
            c.create_text(310, 175 + n * 44, text=text, font=(FONT, 18), fill=INK)
        color = GOOD_GREEN if self.save_message == MSG_SAVED else ERROR_RED
        c.create_text(310, 375, text=self.save_message, font=(FONT, 14, "bold"), fill=color)
        self.retry_button = self.button(c, "다시하기", self.retry)
        self.menu_button = self.button(c, "메인으로", self.show_start)
        c.create_window(230, 455, window=self.retry_button)
        c.create_window(390, 455, window=self.menu_button)
        self.show_bubble(BUBBLE_OVER, ms=None)

    def retry(self):
        """같은 이름으로 1웨이브부터 다시 한다."""
        self.game = Game()
        self.show_game()

    # ---- 랭킹 ----

    def show_ranking(self):
        """랭킹: DB 상위 10개 기록을 표로 보여 준다. 없거나 못 읽으면 문구로 알린다."""
        self.clear()
        self.screen = "ranking"
        c = self.new_canvas()
        self.scene(c, lanes=False)
        self.panel(c, 110, 20, 780, 560)
        c.create_text(500, 66, text="랭킹 (상위 10)", font=(FONT, 22, "bold"), fill=INK)
        columns = [("rank", "순위", 60), ("name", "이름", 200), ("score", "점수", 100),
                   ("round", "웨이브", 80), ("stage", "계급", 90), ("date", "플레이 날짜", 200)]
        self.ranking_tree = ttk.Treeview(c, columns=[col[0] for col in columns], show="headings", height=10)
        for key, heading, width in columns:
            self.ranking_tree.heading(key, text=heading)
            self.ranking_tree.column(key, width=width, anchor="center")
        c.create_window(500, 274, window=self.ranking_tree)
        try:
            db.init_db(self.db_path)
            rows = db.get_top10(self.db_path)
        except sqlite3.Error:
            rows = None
        if rows is None:
            message = MSG_LOAD_FAIL
        elif not rows:
            message = MSG_NO_RECORDS
        else:
            message = ""
            for n, r in enumerate(rows, 1):
                self.ranking_tree.insert("", "end", values=(n, r["name"], r["score"], r["round_reached"],
                                                            r["growth_stage"], r["played_at"]))
        color = NOTE_GRAY if message == MSG_NO_RECORDS else ERROR_RED
        self.ranking_message = tk.Label(c, text=message, font=(FONT, 13), bg=PARCH, fg=color)
        c.create_window(500, 470, window=self.ranking_message)
        self.ranking_back_button = self.button(c, "뒤로", self.show_start)
        c.create_window(500, 526, window=self.ranking_back_button)
