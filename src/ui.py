# tkinter 화면 5개(시작·게임·상점·게임 오버·랭킹)와 군대 배경, 스핀·전투·춤·말풍선 움직임을 맡는다.
# 규칙은 game.py, 그림은 symbols.py·character.py, 저장은 db.py에 맡기고 여기서는 화면만 다룬다.
# 게임 화면 왼쪽은 준비 단계(골드·3x3 슬롯판·[스핀][전투 시작]), 오른쪽은 전장(지휘관 박산·병사 6칸·적)이다.
import random
import sqlite3
import tkinter as tk
from tkinter import ttk

import character
import db
from game import FIELD, LINES, MAX_HEARTS, Game, clean_name, shop_label
from symbols import BULLETS, SOLDIERS, draw_bullet, draw_highlight

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
LINE_X = 572                       # 방어선 x
ENEMY_X0, ENEMY_X1 = 592, 972      # 적 위치 0(방어선 앞)과 FIELD(나오는 곳)의 화면 x
LANE_Y = (340, 446, 552)           # 적이 걷는 세 줄 (발 위치)
HEART_X, HEART_Y = 868, 30         # 하트 첫 칸 가운데

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
BG = "#e8ecdf"
ARMY = "#4b5320"
PANEL = "#fbfbf7"
INK = "#1a1a1a"
HINT_GRAY = "#a0a0a0"   # 빈 판 안내 글씨
NOTE_GRAY = "#6b6b6b"   # 오류가 아닌 안내 문구
ERROR_RED = "#b00020"   # 오류 문구에만 쓴다
HEART_RED = "#d62839"
GOLD = "#b8860b"
FLASH = "#ffd60a"
ENEMY_GRAY = "#7d7f84"
ENEMY_DARK = "#4a4c50"


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
        style.configure("Treeview", font=(FONT, TABLE_FONT_SIZE), rowheight=30)
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
        """전투·춤·말풍선 예약을 모두 취소하고 창을 닫는다."""
        self.cancel_all()
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

    def button(self, parent, text, command, width=12):
        """국방색 바탕에 흰 글씨 버튼을 만든다."""
        return tk.Button(parent, text=text, command=command, width=width, font=(FONT, 13, "bold"),
                         bg=ARMY, fg="white", activebackground="#5f6a2c", activeforeground="white",
                         disabledforeground="#b8bca8", relief="flat", pady=6)

    # ---- 시작 화면 ----

    def show_start(self):
        """시작 화면: 제목, 이병 캐릭터, 이름 입력, [게임 시작] [랭킹 보기] [종료]."""
        self.clear()
        self.screen = "start"
        self.title_label = tk.Label(self.frame, text=TITLE, font=(FONT, 28, "bold"), bg=BG, fg=INK)
        self.title_label.pack(pady=(10, 0))
        scale = 0.75
        face = tk.Canvas(self.frame, width=character.WIDTH * scale, height=character.HEIGHT * scale,
                         bg=BG, highlightthickness=0)
        face.pack()
        character.draw_character(face, 0, 0, 0.0, "이병", scale=scale, tag="hero")
        tk.Label(self.frame, text="계급: 이병", font=(FONT, 14), bg=BG, fg=INK).pack()
        tk.Label(self.frame, text="이름 (1~10글자)", font=(FONT, 12), bg=BG, fg=INK).pack(pady=(8, 0))
        self.name_entry = tk.Entry(self.frame, font=(FONT, 14), width=16, justify="center")
        self.name_entry.insert(0, self.player_name)
        self.name_entry.pack()
        self.name_entry.bind("<Return>", lambda event: self.start_game())
        self.name_message = tk.Label(self.frame, text="", font=(FONT, 11), bg=BG, fg=ERROR_RED)
        self.name_message.pack()
        buttons = tk.Frame(self.frame, bg=BG)
        buttons.pack(pady=6)
        self.start_button = self.button(buttons, "게임 시작", self.start_game)
        self.ranking_button = self.button(buttons, "랭킹 보기", self.show_ranking)
        self.quit_button = self.button(buttons, "종료", self.close)
        for b in (self.start_button, self.ranking_button, self.quit_button):
            b.pack(side="left", padx=6)

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
        """게임 화면: 왼쪽 준비 단계(정보·3x3 판·버튼), 오른쪽 전장(지휘관·병사 6칸·방어선·적)."""
        self.clear()
        self.screen = "game"
        self.hero_place = (CHAR_X, CHAR_Y, HERO_SCALE)
        self.bubble_box = BUBBLE_BOX
        self.canvas = tk.Canvas(self.frame, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=BG)
        self.canvas.pack()
        self.draw_background()
        self.draw_battlefield()
        self.canvas.create_rectangle(20, 12, 360, 122, fill=PANEL, outline=INK, width=2)
        self.canvas.create_rectangle(BOARD_X - 16, BOARD_Y - 16, BOARD_X + 3 * CELL + 16, BOARD_Y + 3 * CELL + 16,
                                     fill=PANEL, outline=INK, width=3, tags="board")
        self.canvas.create_rectangle(20, 528, 360, 590, fill=PANEL, outline=INK, width=2)
        self.spin_button = self.button(self.canvas, "스핀", self.on_spin, width=10)
        self.battle_button = self.button(self.canvas, "전투 시작", self.on_battle, width=10)
        self.canvas.create_window(BOARD_X + 0.75 * CELL, BOARD_Y + 3 * CELL + 52, window=self.spin_button)
        self.canvas.create_window(BOARD_X + 2.25 * CELL, BOARD_Y + 3 * CELL + 52, window=self.battle_button)
        self.draw_board(self.game.board, [])
        self.draw_soldiers()
        self.draw_hearts()
        self.draw_enemies()
        self.draw_hero()
        self.update_info()
        self.set_message(MSG_READY, NOTE_GRAY)
        self.update_buttons()

    def draw_background(self):
        """하늘·막사·국기 게양대·연병장 배경을 도형으로 그린다."""
        c = self.canvas
        c.create_rectangle(0, 0, CANVAS_W, 236, fill="#bfe1f2", outline="")
        c.create_polygon(0, 210, 180, 170, 360, 205, 560, 160, 780, 200, CANVAS_W, 165, CANVAS_W, 236, 0, 236,
                         fill="#9db58a", outline="")
        for x0 in (600, 800):
            c.create_rectangle(x0, 168, x0 + 180, 236, fill="#8c9a7c", outline="#55604a", width=2)
            c.create_polygon(x0 - 8, 168, x0 + 90, 146, x0 + 188, 168, fill="#5a6650", outline="#3f4838")
            for wx in range(x0 + 14, x0 + 170, 34):
                c.create_rectangle(wx, 186, wx + 20, 204, fill="#dfe8ef", outline="#55604a")
        c.create_line(372, 236, 372, 60, fill="#6b6b6b", width=4)
        c.create_polygon(374, 62, 380, 62, 380, 92, 374, 92, fill="#3d6b35", outline="")
        c.create_rectangle(0, 236, CANVAS_W, CANVAS_H, fill="#d8c38e", outline="")
        for y in range(262, CANVAS_H, 44):
            c.create_line(0, y, CANVAS_W, y, fill="#cbb57e", width=2)

    def draw_battlefield(self):
        """방어선(모래주머니 줄)과 적이 나오는 곳 표시를 그린다."""
        c = self.canvas
        c.create_line(LINE_X, 246, LINE_X, CANVAS_H - 6, fill="#8b1a1a", width=4, dash=(10, 6))
        for y in range(252, CANVAS_H - 10, 26):
            c.create_oval(LINE_X - 12, y, LINE_X + 2, y + 20, fill="#a08a5a", outline="#6e5d36")
        c.create_text(LINE_X + 10, 252, text="방어선", anchor="nw", font=(FONT, 11, "bold"), fill="#8b1a1a")
        c.create_text(ENEMY_X1, 252, text="적 출현 ▶", anchor="ne", font=(FONT, 11, "bold"), fill=ENEMY_DARK)

    def draw_board(self, board, lines):
        """9칸에 총알을 그리고, 맞은 줄의 칸은 노란 테두리로 강조한다."""
        self.canvas.delete("cell")
        lit = {i for line in lines for i in line}
        for i in range(9):
            x = BOARD_X + (i % 3) * CELL
            y = BOARD_Y + (i // 3) * CELL
            self.canvas.create_rectangle(x, y, x + CELL, y + CELL, fill="#ffffff", outline="#c8c8c0",
                                         tags=("board", "cell"))
            if board:
                draw_bullet(self.canvas, board[i], x, y, CELL, tag=("board", "cell"))
            if i in lit:
                draw_highlight(self.canvas, x, y, CELL, tag=("board", "cell"))
        if not board:
            self.canvas.create_text(BOARD_X + 1.5 * CELL, BOARD_Y + 1.5 * CELL, text="스핀을 눌러 시작하세요",
                                    font=(FONT, 16, "bold"), fill=HINT_GRAY, tags=("board", "cell", "hint"))

    def draw_hero(self, pose=None):
        """지금 계급의 얼굴과 계급장으로 박산을 다시 그린다 (게임 화면은 지휘관 자리에 0.6배)."""
        x, y, scale = self.hero_place
        self.canvas.delete("hero")
        character.draw_character(self.canvas, x, y, self.game.face_ratio, self.game.rank,
                                 pose=pose, scale=scale, tag="hero")
        self.canvas.tag_raise("bubble")

    def slot_xy(self, i):
        """병사 칸 i(0~5)의 왼쪽 위 좌표. 2열 × 3줄."""
        return SLOT_X + (i % 2) * (SLOT_W + SLOT_GAP), SLOT_Y + (i // 2) * (SLOT_H + SLOT_GAP)

    def draw_soldiers(self):
        """병사 칸 6개와 병사(사람 모양 + 별 + 이름)를 그린다."""
        c = self.canvas
        c.delete("soldier")
        for i in range(6):
            x, y = self.slot_xy(i)
            c.create_rectangle(x, y, x + SLOT_W, y + SLOT_H, fill="#f4efe0", outline="#6e5d36", width=2,
                               dash=() if i < len(self.game.soldiers) else (4, 3), tags=("soldier", "slot_box"))
            if i >= len(self.game.soldiers):
                c.create_text(x + SLOT_W / 2, y + SLOT_H / 2, text="빈 칸", font=(FONT, 10), fill=HINT_GRAY,
                              tags="soldier")
                continue
            kind, star = self.game.soldiers[i]
            self.draw_soldier_figure(x + SLOT_W / 2, y, kind, star)

    def draw_soldier_figure(self, cx, y, kind, star):
        """칸 하나에 병사를 그린다: 맨 위 별(★) 개수, 철모·얼굴·군복·소총, 맨 아래 병사 이름."""
        c = self.canvas
        tags = "soldier"
        for s in range(star):
            sx = cx + (s - (star - 1) / 2) * 16
            c.create_text(sx, y + 12, text="★", font=(FONT, 12, "bold"), fill=GOLD, tags=(tags, "star"))
        band = BULLETS[kind]["tip_end"] if kind == "예광탄" else BULLETS[kind]["tip"]
        c.create_oval(cx - 9, y + 30, cx + 9, y + 48, fill="#f2d3b8", outline=INK, tags=tags)
        c.create_arc(cx - 11, y + 24, cx + 11, y + 44, start=0, extent=180, fill=ARMY, outline=INK, tags=tags)
        c.create_rectangle(cx - 12, y + 48, cx + 12, y + 76, fill=character.UNIFORM, outline=INK, tags=tags)
        c.create_rectangle(cx - 12, y + 54, cx + 12, y + 59, fill=band, outline="", tags=tags)
        c.create_line(cx - 6, y + 76, cx - 7, y + 88, fill=INK, width=4, tags=tags)
        c.create_line(cx + 6, y + 76, cx + 7, y + 88, fill=INK, width=4, tags=tags)
        c.create_line(cx + 2, y + 64, cx + 32, y + 58, fill="#3b2f25", width=4, tags=tags)
        c.create_text(cx, y + SLOT_H - 9, text=SOLDIERS[kind]["name"], font=(FONT, 10, "bold"), fill=INK,
                      tags=tags)

    def flash_slots(self, before):
        """스핀 전과 달라진 병사 칸에 노란 테두리와 "합체!"·"소환" 글자를 잠깐 보여 준다."""
        c = self.canvas
        c.delete("flash")
        for i, soldier in enumerate(self.game.soldiers):
            if i < len(before) and before[i] == soldier:
                continue
            x, y = self.slot_xy(i)
            merged = soldier[1] > 1
            c.create_rectangle(x - 2, y - 2, x + SLOT_W + 2, y + SLOT_H + 2, outline=FLASH, width=5, tags="flash")
            c.create_rectangle(x + 2, y + 50, x + SLOT_W - 2, y + 72, fill=FLASH, outline=INK, tags="flash")
            c.create_text(x + SLOT_W / 2, y + 61, text="합체! ★" + str(soldier[1]) if merged else "소환",
                          font=(FONT, 11, "bold"), fill="#8b1a1a" if merged else INK, tags="flash")
        self.later(FLASH_MS, lambda: self.canvas is not None and self.canvas.delete("flash"))

    def draw_hearts(self):
        """오른쪽 위에 지금 하트 수만큼 빨간 하트를 그린다 (최대 5)."""
        c = self.canvas
        c.delete("hearts")
        c.delete("hearts_label")
        c.create_text(HEART_X - 22, HEART_Y, text="하트", anchor="e", font=(FONT, 12, "bold"), fill=INK,
                      tags="hearts_label")
        for i in range(max(0, min(self.game.hearts, MAX_HEARTS))):
            x = HEART_X + i * 26
            points = [x, HEART_Y + 10, x - 11, HEART_Y - 1, x - 11, HEART_Y - 8, x - 6, HEART_Y - 12,
                      x, HEART_Y - 7, x + 6, HEART_Y - 12, x + 11, HEART_Y - 8, x + 11, HEART_Y - 1]
            c.create_polygon(points, fill=HEART_RED, outline="#7a0f1c", width=2, smooth=True, tags="hearts")

    def enemy_screen_x(self, enemy):
        """적의 거리(0=방어선 ~ FIELD=나오는 곳)를 화면 x로 바꾼다."""
        return ENEMY_X0 + (ENEMY_X1 - ENEMY_X0) * max(0.0, enemy["x"]) / FIELD

    def draw_enemies(self):
        """전장의 적(회색 군복 사람)과 보스(전차)를 체력 막대와 함께 그린다."""
        c = self.canvas
        c.delete("enemy")
        for enemy in sorted(self.game.enemies, key=lambda e: -e["x"]):
            x = self.enemy_screen_x(enemy)
            if enemy["boss"]:
                y = LANE_Y[1]
                self.draw_tank(x, y)
                bar_y, bar_w = y - 64, 70
            else:
                y = LANE_Y[enemy.get("lane", 0) % 3]
                self.draw_enemy_figure(x, y)
                bar_y, bar_w = y - 66, 34
            ratio = max(0.0, enemy["hp"] / enemy["max_hp"])
            c.create_rectangle(x - bar_w / 2, bar_y, x + bar_w / 2, bar_y + 6, fill="#3a3a3a", outline="",
                               tags="enemy")
            c.create_rectangle(x - bar_w / 2, bar_y, x - bar_w / 2 + bar_w * ratio, bar_y + 6, fill="#e63946",
                               outline="", tags="enemy")

    def draw_enemy_figure(self, x, y):
        """적 병사 한 명: 회색 군복, 왼쪽(방어선)을 보고 걷는다. y는 발 위치."""
        c = self.canvas
        c.create_line(x - 5, y - 16, x - 8, y, fill=ENEMY_DARK, width=4, tags="enemy")
        c.create_line(x + 5, y - 16, x + 8, y, fill=ENEMY_DARK, width=4, tags="enemy")
        c.create_rectangle(x - 11, y - 44, x + 11, y - 16, fill=ENEMY_GRAY, outline=INK, tags="enemy")
        c.create_oval(x - 9, y - 60, x + 9, y - 42, fill="#d9c2aa", outline=INK, tags="enemy")
        c.create_arc(x - 11, y - 66, x + 11, y - 46, start=0, extent=180, fill=ENEMY_DARK, outline=INK, tags="enemy")
        c.create_line(x - 2, y - 32, x - 28, y - 28, fill="#2b2b2b", width=4, tags="enemy")

    def draw_tank(self, x, y):
        """보스: 왼쪽으로 포신을 겨눈 전차. y는 바퀴 아래."""
        c = self.canvas
        c.create_rectangle(x - 44, y - 18, x + 44, y, fill="#2f2f2f", outline=INK, width=2, tags="enemy")
        for wx in range(-36, 44, 16):
            c.create_oval(x + wx - 6, y - 15, x + wx + 6, y - 3, fill="#6b6b6b", outline=INK, tags="enemy")
        c.create_rectangle(x - 40, y - 36, x + 40, y - 18, fill="#5b6b3a", outline=INK, width=2, tags="enemy")
        c.create_oval(x - 18, y - 54, x + 20, y - 30, fill="#4b5a2e", outline=INK, width=2, tags="enemy")
        c.create_rectangle(x - 62, y - 46, x - 14, y - 40, fill="#3a4524", outline=INK, tags="enemy")
        c.create_text(x + 2, y - 27, text="BOSS", font=(FONT, 9, "bold"), fill="#ffd60a", tags="enemy")

    def draw_shots(self):
        """병사마다 방어선에 가장 가까운 적에게 노란 탄 궤적을 그린다 (번갈아 깜박여 쏘는 것처럼)."""
        c = self.canvas
        c.delete("shot")
        if not self.game.enemies or self.tick_count % 2:
            return
        target = min(self.game.enemies, key=lambda e: e["x"])
        tx = self.enemy_screen_x(target)
        ty = (LANE_Y[1] - 40) if target["boss"] else LANE_Y[target.get("lane", 0) % 3] - 32
        for i in range(len(self.game.soldiers)):
            x, y = self.slot_xy(i)
            c.create_line(x + SLOT_W / 2 + 32, y + 58, tx, ty, fill=FLASH, width=2, dash=(6, 4), tags="shot")

    def update_info(self):
        """정보판 글자: 웨이브·계급·이름, 점수·처치, 골드·다음 스핀 비용."""
        g = self.game
        self.canvas.delete("info")
        cost = g.spin_cost()
        lines = [("웨이브 " + str(g.wave) + "    계급 " + g.rank + "    이름 " + self.player_name, ""),
                 ("점수 " + str(g.score) + "    처치 " + str(g.kills), ""),
                 ("골드 " + str(g.gold) + "    다음 스핀 " + ("무료" if cost == 0 else str(cost)), "bold")]
        for n, (text, weight) in enumerate(lines):
            self.canvas.create_text(36, 32 + n * 30, text=text, anchor="w", font=(FONT, 14, weight),
                                    fill=GOLD if n == 2 else INK, tags="info")

    def set_message(self, text, color=INK):
        """판 아래 안내 문구 한 줄."""
        self.canvas.delete("msg")
        self.canvas.create_text(190, 559, text=text, width=320, justify="center", font=(FONT, 12, "bold"), fill=color,
                                tags="msg")

    def update_buttons(self):
        """준비 단계이고 굴러가는 중·춤추는 중이 아닐 때만 버튼을 연다. [스핀]은 골드도 있어야 한다."""
        ready = self.game.phase == "prepare" and not self.busy and not self.dancing
        self.spin_button.config(state="normal" if ready and self.game.can_spin() else "disabled")
        self.battle_button.config(state="normal" if ready else "disabled")

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
        """[전투 시작]: 버튼을 막고 전투를 시작한다. 준비 단계가 아니거나 굴러가는 중이면 무시한다."""
        if self.busy or self.dancing or self.game.phase != "prepare":
            return
        self.busy = True
        self.game.start_battle()
        self.update_buttons()
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
        if g.finish_wave() == "clear":
            self.update_info()
            self.set_message("웨이브를 막았습니다! " + g.rank + " 진급", "#2d6a2d")
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
        """웨이브를 막은 춤을 춘다. 춤추는 동안은 말풍선을 유지하고 버튼을 막는다. 이미 추고 있으면 False."""
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
        """상점: 4가지 중 3개를 보여 주고 1개를 무료로 고른다."""
        g = self.game
        self.clear()
        self.screen = "shop"
        tk.Label(self.frame, text="상점 — 하나를 무료로 고르세요", font=(FONT, 20, "bold"),
                 bg=BG, fg=INK).pack(pady=(26, 6))
        tk.Label(self.frame, text="계급 " + g.rank + "    다음 웨이브 " + str(g.wave) + "    하트 " + str(g.hearts)
                 + "    골드 " + str(g.gold), font=(FONT, 13), bg=BG, fg=INK).pack()
        row = tk.Frame(self.frame, bg=BG)
        row.pack(pady=18)
        self.shop_buttons = []
        for item, bullet in g.shop_offer(self.rng):
            card = tk.Frame(row, bg=PANEL, highlightbackground=INK, highlightthickness=2)
            card.pack(side="left", padx=12)
            pic = tk.Canvas(card, width=160, height=150, bg=PANEL, highlightthickness=0)
            pic.pack(padx=10, pady=(10, 0))
            self.draw_shop_icon(pic, item, bullet)
            title = "덱에 추가" if bullet else shop_label(item, bullet)   # 총알 이름은 그림 아래에 이미 있다
            tk.Label(card, text=title, font=(FONT, 14, "bold"), bg=PANEL, fg=INK).pack()
            tk.Label(card, text=self.shop_help(item, bullet), font=(FONT, 11), bg=PANEL, fg=NOTE_GRAY,
                     wraplength=180, height=2).pack()
            b = self.button(card, "고르기", lambda item=item, bullet=bullet: self.choose(item, bullet), width=10)
            b.pack(pady=10)
            self.shop_buttons.append(b)
        soldiers = "  ".join(SOLDIERS[k]["name"] + "★" + str(s) for k, s in g.soldiers) or "없음"
        tk.Label(self.frame, text="병사: " + soldiers, font=(FONT, 12), bg=BG, fg=INK).pack()
        deck_text = "  ".join(kind + " " + str(n) for kind, n in g.deck_counts().items() if n)
        tk.Label(self.frame, text="지금 덱: " + deck_text, font=(FONT, 12), bg=BG, fg=INK).pack(pady=(4, 0))

    def shop_help(self, item, bullet):
        """상점 항목 설명 한 줄."""
        if item == "총알 추가":
            return "덱에 " + bullet + " 1개 (" + SOLDIERS[bullet]["name"] + " 소환)"
        return {"하트 +1": "하트 1개 회복 (최대 5)",
                "공격력 +10%": "모든 병사 공격력 +10% (쌓임)",
                "첫 스핀 무료": "다음 준비 단계 첫 스핀 0골드"}[item]

    def draw_shop_icon(self, pic, item, bullet):
        """상점 카드 그림: 총알, 하트, 위 화살표, FREE 글자."""
        if item == "총알 추가":
            draw_bullet(pic, bullet, 5, 0, 150)
        elif item == "하트 +1":
            pic.create_polygon(80, 120, 30, 70, 30, 45, 52, 30, 80, 50, 108, 30, 130, 45, 130, 70,
                               fill=HEART_RED, outline="#7a0f1c", width=3, smooth=True)
        elif item == "공격력 +10%":
            pic.create_polygon(80, 20, 130, 80, 100, 80, 100, 130, 60, 130, 60, 80, 30, 80,
                               fill="#e67e22", outline=INK, width=3)
        else:
            pic.create_oval(25, 25, 135, 125, fill="#ffd60a", outline=INK, width=3)
            pic.create_text(80, 75, text="FREE", font=(FONT, 22, "bold"), fill=INK)

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
        self.canvas = tk.Canvas(self.frame, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=BG)
        self.canvas.pack()
        self.draw_background()
        self.draw_hero()
        self.canvas.create_rectangle(60, 60, 560, 520, fill=PANEL, outline=INK, width=3)
        self.result_lines = ["점수 " + str(g.score), "도달한 웨이브 " + str(g.wave),
                             "처치 " + str(g.kills), "계급 " + g.rank]
        self.canvas.create_text(310, 110, text="게임 오버", font=(FONT, 30, "bold"), fill="#8b1a1a")
        for n, text in enumerate(self.result_lines):
            self.canvas.create_text(310, 175 + n * 44, text=text, font=(FONT, 18), fill=INK)
        color = "#2d6a2d" if self.save_message == MSG_SAVED else ERROR_RED
        self.canvas.create_text(310, 375, text=self.save_message, font=(FONT, 14, "bold"), fill=color)
        self.retry_button = self.button(self.canvas, "다시하기", self.retry)
        self.menu_button = self.button(self.canvas, "메인으로", self.show_start)
        self.canvas.create_window(230, 455, window=self.retry_button)
        self.canvas.create_window(390, 455, window=self.menu_button)
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
        tk.Label(self.frame, text="랭킹 (상위 10)", font=(FONT, 22, "bold"), bg=BG, fg=INK).pack(pady=(30, 10))
        columns = [("rank", "순위", 60), ("name", "이름", 200), ("score", "점수", 100),
                   ("round", "웨이브", 80), ("stage", "계급", 90), ("date", "플레이 날짜", 200)]
        self.ranking_tree = ttk.Treeview(self.frame, columns=[c[0] for c in columns], show="headings", height=10)
        for key, heading, width in columns:
            self.ranking_tree.heading(key, text=heading)
            self.ranking_tree.column(key, width=width, anchor="center")
        self.ranking_tree.pack()
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
        self.ranking_message = tk.Label(self.frame, text=message, font=(FONT, 13), bg=BG, fg=color)
        self.ranking_message.pack(pady=6)
        self.ranking_back_button = self.button(self.frame, "뒤로", self.show_start)
        self.ranking_back_button.pack(pady=6)
