# sqlite3로 game.db에 플레이어와 게임 기록을 저장하고 랭킹을 읽는다.
# 이 게임의 SQL은 모두 이 파일에만 있고, 값은 항상 ? 자리표시자로 넘긴다.
# 테이블 구조는 저장소 맨 위 schema.sql과 같다.
import os
import sqlite3
import sys
from datetime import datetime

DB_NAME = "game.db"

CREATE_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE CHECK (name <> ''),
    created_at TEXT    NOT NULL
)"""

CREATE_RECORDS = """
CREATE TABLE IF NOT EXISTS records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id     INTEGER NOT NULL REFERENCES players(id),
    round_reached INTEGER NOT NULL,
    score         INTEGER NOT NULL,
    growth_stage  TEXT    NOT NULL,
    played_at     TEXT    NOT NULL
)"""


def get_db_path():
    """game.db 경로: exe로 실행하면 exe 폴더, 소스로 실행하면 main.py가 있는 src 폴더."""
    if getattr(sys, "frozen", False):
        folder = os.path.dirname(sys.executable)
    else:
        folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(folder, DB_NAME)


def now_text():
    """지금 시각을 'YYYY-MM-DD HH:MM:SS' 글자로 돌려준다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect(path):
    """DB에 연결하고 외래 키 검사를 켠다."""
    # SQL: PRAGMA foreign_keys = ON
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db(path):
    """테이블이 없으면 만든다 (이미 있으면 그대로 둔다)."""
    # SQL: CREATE TABLE IF NOT EXISTS players (...)
    #      CREATE TABLE IF NOT EXISTS records (...)
    con = connect(path)
    try:
        with con:
            con.execute(CREATE_PLAYERS)
            con.execute(CREATE_RECORDS)
    finally:
        con.close()


def find_or_add_player(con, name):
    """열린 연결에서 이름으로 플레이어 번호를 찾고, 없으면 새로 등록해 번호를 돌려준다."""
    # SQL: SELECT id FROM players WHERE name = ?
    #      (없으면) INSERT INTO players (name, created_at) VALUES (?, ?)
    # 이름이 비어 있으면 테이블의 CHECK 규칙 때문에 sqlite3.IntegrityError가 난다.
    # (1~10글자 규칙은 게임을 시작하기 전에 game.clean_name()이 확인한다.)
    row = con.execute("SELECT id FROM players WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row[0]
    cur = con.execute("INSERT INTO players (name, created_at) VALUES (?, ?)", (name, now_text()))
    return cur.lastrowid


def get_or_create_player(path, name):
    """게임을 시작할 때(ui.py) 플레이어를 등록하거나 이미 있으면 그 번호를 돌려준다."""
    con = connect(path)
    try:
        with con:
            return find_or_add_player(con, name)
    finally:
        con.close()


def save_record(path, name, round_reached, score, growth_stage, played_at=None):
    """게임 오버 기록을 저장하고 기록 번호를 돌려준다."""
    # SQL: (플레이어 찾기·등록은 find_or_add_player)
    #      INSERT INTO records (player_id, round_reached, score, growth_stage, played_at)
    #      VALUES (?, ?, ?, ?, ?)
    con = connect(path)
    try:
        with con:
            player_id = find_or_add_player(con, name)
            cur = con.execute(
                "INSERT INTO records (player_id, round_reached, score, growth_stage, played_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (player_id, round_reached, score, growth_stage, played_at or now_text()),
            )
            return cur.lastrowid
    finally:
        con.close()


def get_top10(path):
    """랭킹 상위 10개를 읽는다 (총점 → 라운드 높은 순, 같으면 먼저 플레이한 순)."""
    # played_at은 항상 'YYYY-MM-DD HH:MM:SS' 형식이라 글자 순서가 곧 시간 순서다.
    # SQL: SELECT p.name, r.score, r.round_reached, r.growth_stage, r.played_at
    #      FROM records r JOIN players p ON p.id = r.player_id
    #      ORDER BY r.score DESC, r.round_reached DESC, r.played_at ASC, r.id ASC
    #      LIMIT 10
    con = connect(path)
    try:
        rows = con.execute(
            "SELECT p.name, r.score, r.round_reached, r.growth_stage, r.played_at "
            "FROM records r JOIN players p ON p.id = r.player_id "
            "ORDER BY r.score DESC, r.round_reached DESC, r.played_at ASC, r.id ASC "
            "LIMIT 10"
        ).fetchall()
    finally:
        con.close()
    keys = ("name", "score", "round_reached", "growth_stage", "played_at")
    return [dict(zip(keys, row)) for row in rows]
