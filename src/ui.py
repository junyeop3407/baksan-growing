# tkinter 화면 5개(시작·게임·상점·게임 오버·랭킹)와 군대 배경, 스핀·춤·말풍선 움직임을 맡는다.
# 규칙은 game.py, 그림은 symbols.py·character.py, 저장은 db.py에 맡기고 여기서는 화면만 다룬다.
import random
import sqlite3
import tkinter as tk
from tkinter import ttk

import character
import db
from game import LINES, Game, clean_name
from symbols import BULLETS, draw_bullet, draw_highlight

TITLE = "박산 키우기"
FONT = "Malgun Gothic"
TABLE_FONT_SIZE = 12

# 창과 게임 화면 크기 (px)
CANVAS_W, CANVAS_H = 900, 560
MIN_W, MIN_H = 900, 640
CELL = 100                         # 슬롯 칸 한 변 (가장 작은 창에서도 이 크기)
BOARD_X, BOARD_Y = 60, 150         # 3x3 판 왼쪽 위
CHAR_X, CHAR_Y = 610, 190          # 캐릭터 영역 왼쪽 위 (character.WIDTH × HEIGHT)
BUBBLE_BOX = (560, 30, 320, 140)   # 말풍선 영역 (x, y, 너비, 높이): 캐릭터 머리 위

# 시간 (ms)
BUBBLE_MS = 2500
ROLL_STEPS, ROLL_MS = 6, 600       # 스핀할 때 굴러가는 그림 6장, 모두 0.6초
ROUND_PAUSE_MS = 700               # 5번째 스핀 결과를 보여 주고 판정하기까지

# 문구
BUBBLE_PASS = "난 최산을 닮았다"
BUBBLE_NEXT = "난 섹시해.... ㅋ"
BUBBLE_OVER = "she's so BAD..."
MSG_SAVED = "기록이 DB에 저장되었습니다"
MSG_SAVE_FAIL = "기록을 저장하지 못했습니다"
MSG_LOAD_FAIL = "기록을 불러오지 못했습니다"
MSG_NO_RECORDS = "아직 기록이 없습니다"

# 색
BG = "#e8ecdf"
ARMY = "#4b5320"
PANEL = "#fbfbf7"
INK = "#1a1a1a"


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

        try:
            db.init_db(db_path)
            self.db_ok = True
        except sqlite3.Error:
            self.db_ok = False

        root.title(TITLE)
        root.minsize(MIN_W, MIN_H)
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
        """춤·말풍선 예약을 모두 취소하고 창을 닫는다."""
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
        self.name_message = tk.Label(self.frame, text="", font=(FONT, 11), bg=BG, fg="#b00020")
        self.name_message.pack()
        buttons = tk.Frame(self.frame, bg=BG)
        buttons.pack(pady=6)
        self.start_button = self.button(buttons, "게임 시작", self.start_game)
        self.ranking_button = self.button(buttons, "랭킹 보기", self.show_ranking)
        self.quit_button = self.button(buttons, "종료", self.close)
        for b in (self.start_button, self.ranking_button, self.quit_button):
            b.pack(side="left", padx=6)

    def start_game(self):
        """이름을 확인하고 플레이어를 등록한 뒤 1라운드를 시작한다."""
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
        """게임 화면: 군대 배경, 정보판, 3x3 총알판, 캐릭터, [스핀]."""
        self.clear()
        self.screen = "game"
        self.canvas = tk.Canvas(self.frame, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=BG)
        self.canvas.pack()
        self.draw_background()
        self.canvas.create_rectangle(BOARD_X - 20, BOARD_Y - 20, BOARD_X + 3 * CELL + 20, BOARD_Y + 3 * CELL + 20,
                                     fill=PANEL, outline=INK, width=3, tags="board")
        self.canvas.create_rectangle(40, 20, 520, 115, fill=PANEL, outline=INK, width=2)
        self.spin_button = self.button(self.canvas, "스핀", self.on_spin, width=10)
        self.canvas.create_window(BOARD_X + 1.5 * CELL, BOARD_Y + 3 * CELL + 55, window=self.spin_button)
        self.draw_board([], [])
        self.draw_hero()
        self.update_info("")

    def draw_background(self):
        """연병장·막사·국기 게양대 배경을 도형으로 그린다."""
        c = self.canvas
        c.create_rectangle(0, 0, CANVAS_W, 330, fill="#bfe1f2", outline="")
        c.create_polygon(0, 300, 160, 250, 330, 290, 520, 240, 720, 285, 900, 250, 900, 330, 0, 330,
                         fill="#9db58a", outline="")
        for x0 in (430, 680):
            c.create_rectangle(x0, 225, x0 + 220, 330, fill="#8c9a7c", outline="#55604a", width=2)
            c.create_polygon(x0 - 10, 225, x0 + 110, 190, x0 + 230, 225, fill="#5a6650", outline="#3f4838")
            for wx in range(x0 + 18, x0 + 210, 40):
                c.create_rectangle(wx, 250, wx + 22, 270, fill="#dfe8ef", outline="#55604a")
                c.create_rectangle(wx, 290, wx + 22, 310, fill="#dfe8ef", outline="#55604a")
        c.create_line(560, 330, 560, 130, fill="#6b6b6b", width=4)
        c.create_polygon(562, 132, 610, 142, 562, 152, fill="#3d6b35", outline="#2a4a25")
        c.create_rectangle(0, 330, CANVAS_W, CANVAS_H, fill="#d8c38e", outline="")
        for y in range(360, CANVAS_H, 45):
            c.create_line(0, y, CANVAS_W, y, fill="#cbb57e", width=2)

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

    def draw_hero(self, pose=None):
        """지금 계급의 얼굴과 계급장으로 캐릭터를 다시 그린다."""
        self.canvas.delete("hero")
        character.draw_character(self.canvas, CHAR_X, CHAR_Y, self.game.face_ratio, self.game.rank,
                                 pose=pose, tag="hero")
        self.canvas.tag_raise("bubble")

    def update_info(self, last):
        """정보판 글자: 라운드·계급, 라운드 점수/목표, 남은 스핀·총점, 이번 스핀."""
        g = self.game
        self.canvas.delete("info")
        lines = ["라운드 " + str(g.round_no) + "    계급 " + g.rank + "    이름 " + self.player_name,
                 "라운드 점수 " + str(g.round_score) + " / 목표 " + str(g.target),
                 "남은 스핀 " + str(g.spins_left) + "    총점 " + str(g.total_score) + ("    " + last if last else "")]
        for n, text in enumerate(lines):
            self.canvas.create_text(58, 38 + n * 26, text=text, anchor="w", font=(FONT, 14, "bold" if n == 1 else ""),
                                    fill=INK, tags="info")

    def on_spin(self):
        """[스핀]: 굴러가는 그림을 보여 준 뒤 결과를 낸다. 굴러가는 중·춤추는 중 누른 것은 무시한다."""
        if self.busy or self.game.spins_left <= 0:
            return
        self.busy = True
        self.spin_button.config(state="disabled")
        self.roll(0)

    def roll(self, step):
        """굴러가는 그림을 한 장 그리고, 다 그렸으면 실제 스핀 결과를 보여 준다."""
        if step < ROLL_STEPS:
            fake = [self.roll_rng.choice(self.game.deck) for _ in range(9)]
            self.draw_board(fake, [])
            self.later(ROLL_MS / ROLL_STEPS, lambda: self.roll(step + 1))
            return
        score = self.game.spin(self.rng)
        board = self.game.board
        matched = [line for line in LINES if board[line[0]] == board[line[1]] == board[line[2]]]
        self.draw_board(board, matched)
        self.update_info("이번 +" + str(score) + " (맞은 줄 " + str(len(matched)) + ")")
        if self.game.spins_left == 0:
            self.later(ROUND_PAUSE_MS, self.end_round)
        else:
            self.busy = False
            self.spin_button.config(state="normal")

    def end_round(self):
        """5번을 다 돌린 라운드를 판정한다: 통과면 진급 + 춤 → 상점, 아니면 게임 오버."""
        if self.game.finish_round() == "pass":
            self.update_info("통과! " + self.game.rank + " 진급")
            self.draw_hero()
            self.start_dance(self.show_shop)
        else:
            self.show_gameover()

    # ---- 말풍선과 춤 ----

    def show_bubble(self, text, ms=BUBBLE_MS):
        """캐릭터 머리 위에 말풍선을 띄운다. 앞의 말풍선은 바로 지운다. ms가 None이면 계속 보인다."""
        self.hide_bubble()
        x, y, w, h = BUBBLE_BOX
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
        """라운드 통과 춤을 춘다. 춤추는 동안은 말풍선을 유지하고 스핀을 막는다. 이미 추고 있으면 False."""
        if self.dancing:
            return False
        self.dancing = True
        self.busy = True
        self.spin_button.config(state="disabled")
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
        on_done()

    # ---- 상점 ----

    def show_shop(self):
        """상점: 총알 3개 중 1개를 골라 덱에 넣는다."""
        self.clear()
        self.screen = "shop"
        tk.Label(self.frame, text="상점 — 덱에 넣을 총알 하나를 고르세요", font=(FONT, 20, "bold"),
                 bg=BG, fg=INK).pack(pady=(30, 6))
        tk.Label(self.frame, text="계급 " + self.game.rank + "    다음 라운드 " + str(self.game.round_no)
                 + "    목표 " + str(self.game.target), font=(FONT, 13), bg=BG, fg=INK).pack()
        row = tk.Frame(self.frame, bg=BG)
        row.pack(pady=20)
        self.shop_buttons = []
        for kind in self.game.shop_offer(self.rng):
            card = tk.Frame(row, bg=PANEL, highlightbackground=INK, highlightthickness=2)
            card.pack(side="left", padx=14)
            pic = tk.Canvas(card, width=160, height=160, bg=PANEL, highlightthickness=0)
            pic.pack(padx=10, pady=(10, 0))
            draw_bullet(pic, kind, 0, 0, 160)
            tk.Label(card, text=str(BULLETS[kind]["points"]) + "점", font=(FONT, 14, "bold"),
                     bg=PANEL, fg=INK).pack()
            b = self.button(card, "고르기", lambda kind=kind: self.choose(kind), width=10)
            b.pack(pady=10)
            self.shop_buttons.append(b)
        counts = self.game.deck_counts()
        deck_text = "  ".join(kind + " " + str(n) for kind, n in counts.items() if n)
        tk.Label(self.frame, text="지금 덱: " + deck_text, font=(FONT, 12), bg=BG, fg=INK).pack()

    def choose(self, kind):
        """고른 총알을 덱에 넣고 다음 라운드를 시작한다 (2라운드부터 말풍선)."""
        self.game.add_to_deck(kind)
        self.show_game()
        self.show_bubble(BUBBLE_NEXT)

    # ---- 게임 오버 ----

    def show_gameover(self):
        """게임 오버: 기록을 저장하고 결과, 캐릭터와 말풍선, 저장 결과 문구를 보여 준다."""
        g = self.game
        try:
            db.init_db(self.db_path)  # 시작할 때 실패했어도 지금 다시 준비해 본다
            db.save_record(self.db_path, self.player_name, g.round_no, g.total_score, g.rank)
            self.save_message = MSG_SAVED
        except sqlite3.Error:
            self.save_message = MSG_SAVE_FAIL
        self.clear()
        self.screen = "gameover"
        self.canvas = tk.Canvas(self.frame, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=BG)
        self.canvas.pack()
        self.draw_background()
        self.draw_hero()
        self.canvas.create_rectangle(40, 60, 520, 470, fill=PANEL, outline=INK, width=3)
        self.result_lines = ["최종 점수 " + str(g.total_score), "도달한 라운드 " + str(g.round_no),
                             "계급 " + g.rank]
        self.canvas.create_text(280, 110, text="게임 오버", font=(FONT, 30, "bold"), fill="#8b1a1a")
        for n, text in enumerate(self.result_lines):
            self.canvas.create_text(280, 180 + n * 44, text=text, font=(FONT, 18), fill=INK)
        color = "#2d6a2d" if self.save_message == MSG_SAVED else "#b00020"
        self.canvas.create_text(280, 330, text=self.save_message, font=(FONT, 14, "bold"), fill=color)
        self.retry_button = self.button(self.canvas, "다시하기", self.retry)
        self.menu_button = self.button(self.canvas, "메인으로", self.show_start)
        self.canvas.create_window(200, 410, window=self.retry_button)
        self.canvas.create_window(360, 410, window=self.menu_button)
        self.show_bubble(BUBBLE_OVER, ms=None)

    def retry(self):
        """같은 이름으로 1라운드부터 다시 한다."""
        self.game = Game()
        self.show_game()

    # ---- 랭킹 ----

    def show_ranking(self):
        """랭킹: DB 상위 10개 기록을 표로 보여 준다. 없거나 못 읽으면 문구로 알린다."""
        self.clear()
        self.screen = "ranking"
        tk.Label(self.frame, text="랭킹 (상위 10)", font=(FONT, 22, "bold"), bg=BG, fg=INK).pack(pady=(30, 10))
        columns = [("rank", "순위", 60), ("name", "이름", 200), ("score", "점수", 100),
                   ("round", "라운드", 80), ("stage", "계급", 90), ("date", "플레이 날짜", 200)]
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
        self.ranking_message = tk.Label(self.frame, text=message, font=(FONT, 13), bg=BG, fg="#b00020")
        self.ranking_message.pack(pady=6)
        self.ranking_back_button = self.button(self.frame, "뒤로", self.show_start)
        self.ranking_back_button.pack(pady=6)
