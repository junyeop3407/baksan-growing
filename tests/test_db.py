# DB 테스트 (docs/tests.md의 C1~C9, B7).
# 실제 game.db 대신 pytest가 만들어 주는 임시 폴더(tmp_path)의 DB로 돌리므로 테스트 뒤 남는 파일이 없다.
import os
import sqlite3
import sys

import db

SCHEMA_SQL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql")


def table_names(path):
    con = sqlite3.connect(path)
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    finally:
        con.close()
    return sorted(r[0] for r in rows)


def count_rows(path, table):
    con = sqlite3.connect(path)
    try:
        return con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    finally:
        con.close()


def test_c1_creates_db_when_missing(tmp_path):
    """C1: game.db가 없을 때 시작하면 파일과 테이블 2개가 생긴다."""
    path = str(tmp_path / "game.db")
    assert not os.path.exists(path)
    db.init_db(path)
    assert os.path.exists(path)
    assert table_names(path) == ["players", "records"]


def test_c2_init_again_keeps_records(tmp_path):
    """C2: 이미 있을 때 다시 시작해도 오류가 없고 기록이 지워지지 않는다."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    db.save_record(path, "박산", 3, 400, "상병")
    db.init_db(path)
    assert count_rows(path, "records") == 1


def test_c3_saved_record_reads_back(tmp_path):
    """C3: 저장한 이름·라운드·총점·계급 이름·날짜가 그대로 읽힌다."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    db.save_record(path, "박산", 5, 1234, "하사", played_at="2026-11-18 10:20:30")
    rows = db.get_top10(path)
    assert len(rows) == 1
    row = rows[0]
    assert (row["name"], row["round_reached"], row["score"], row["growth_stage"], row["played_at"]) == \
        ("박산", 5, 1234, "하사", "2026-11-18 10:20:30")


def test_c3_default_played_at_format(tmp_path):
    """C3: 날짜를 주지 않으면 지금 시각이 YYYY-MM-DD HH:MM:SS 형식으로 저장된다."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    db.save_record(path, "박산", 1, 50, "이병")
    played_at = db.get_top10(path)[0]["played_at"]
    assert len(played_at) == 19 and played_at[4] == "-" and played_at[10] == " " and played_at[13] == ":"


def test_c4_empty_ranking(tmp_path):
    """C4: 기록이 0개면 랭킹 조회는 빈 목록 (화면 부분은 ui 단계에서 확인)."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    assert db.get_top10(path) == []


def test_c5_top10_only_sorted_by_score(tmp_path):
    """C5: 기록이 12개면 랭킹은 10개만, 총점 높은 순."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    scores = [50, 700, 120, 999, 300, 10, 450, 820, 60, 230, 610, 5]
    for i, score in enumerate(scores):
        db.save_record(path, "플레이어" + str(i), 2, score, "일병")
    rows = db.get_top10(path)
    assert [r["score"] for r in rows] == sorted(scores, reverse=True)[:10]


def test_c6_ties(tmp_path):
    """C6: 총점이 같으면 라운드 높은 순, 그것도 같으면 먼저 플레이한 기록이 위."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    db.save_record(path, "늦게", 3, 500, "병장", played_at="2026-11-18 12:00:00")
    db.save_record(path, "라운드높음", 4, 500, "하사", played_at="2026-11-18 13:00:00")
    db.save_record(path, "먼저", 3, 500, "병장", played_at="2026-11-18 09:00:00")
    db.save_record(path, "같은시각_먼저저장", 2, 500, "상병", played_at="2026-11-18 08:00:00")
    db.save_record(path, "같은시각_나중저장", 2, 500, "상병", played_at="2026-11-18 08:00:00")
    names = [r["name"] for r in db.get_top10(path)]
    assert names[:3] == ["라운드높음", "먼저", "늦게"]
    assert names[3:] == ["같은시각_먼저저장", "같은시각_나중저장"]


def test_c7_sql_injection_name_is_just_text(tmp_path):
    """C7: 이름에 SQL 공격 문자열을 넣어도 그대로 저장되고 테이블은 무사하다."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    evil = "'); DROP TABLE players;--"
    db.save_record(path, evil, 1, 10, "이병")
    assert table_names(path) == ["players", "records"]
    assert db.get_top10(path)[0]["name"] == evil


def columns(path):
    con = sqlite3.connect(path)
    try:
        result = {}
        for table in ("players", "records"):
            cols = con.execute("PRAGMA table_info(" + table + ")").fetchall()
            fks = con.execute("PRAGMA foreign_key_list(" + table + ")").fetchall()
            uniques = [row[1] for row in con.execute("PRAGMA index_list(" + table + ")").fetchall() if row[2]]
            unique_cols = sorted(con.execute("PRAGMA index_info(" + name + ")").fetchone()[2] for name in uniques)
            result[table] = {
                "columns": [(c[1], c[2].upper(), c[3], c[5]) for c in cols],
                "foreign_keys": [(f[2], f[3], f[4]) for f in fks],
                "unique": unique_cols,
            }
        return result
    finally:
        con.close()


def test_c8_schema_sql_matches_db_py(tmp_path):
    """C8: schema.sql로 만든 테이블과 db.py가 만든 테이블의 열 이름·형식·제약이 같다."""
    from_schema = str(tmp_path / "from_schema.db")
    con = sqlite3.connect(from_schema)
    with open(SCHEMA_SQL, encoding="utf-8") as f:
        con.executescript(f.read())
    con.close()
    from_code = str(tmp_path / "from_code.db")
    db.init_db(from_code)
    assert columns(from_schema) == columns(from_code)
    assert columns(from_code)["players"]["unique"] == ["name"]
    assert columns(from_code)["records"]["foreign_keys"] == [("players", "player_id", "id")]


def test_c9_db_path_next_to_exe_when_frozen(tmp_path, monkeypatch):
    """C9: exe로 실행할 때(sys.frozen) game.db 위치는 exe가 있는 폴더다."""
    exe = tmp_path / "박산키우기.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert db.get_db_path() == os.path.join(str(tmp_path), "game.db")


def test_c9_db_path_next_to_main_py(monkeypatch):
    """C9: 소스로 실행할 때 game.db 위치는 main.py와 같은 src 폴더다."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    src = os.path.dirname(os.path.abspath(db.__file__))
    assert db.get_db_path() == os.path.join(src, "game.db")


def test_b7_same_name_twice(tmp_path):
    """B7: 같은 이름으로 두 번 시작하면 플레이어는 1명, 기록은 같은 플레이어로 2개."""
    path = str(tmp_path / "game.db")
    db.init_db(path)
    first = db.get_or_create_player(path, "박산")
    db.save_record(path, "박산", 2, 150, "일병")
    second = db.get_or_create_player(path, "박산")
    db.save_record(path, "박산", 3, 300, "상병")
    assert first == second
    assert count_rows(path, "players") == 1
    con = sqlite3.connect(path)
    try:
        owners = con.execute("SELECT DISTINCT player_id FROM records").fetchall()
    finally:
        con.close()
    assert owners == [(first,)]
