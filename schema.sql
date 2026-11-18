-- 박산 키우기 DB 구조 (SQLite, 파일 이름 game.db)
-- 게임을 처음 실행하면 src/db.py의 init_db()가 이 파일과 같은 구조로 테이블을 자동으로 만든다.

-- 플레이어: 같은 이름은 같은 플레이어로 본다
CREATE TABLE IF NOT EXISTS players (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,                      -- 플레이어 번호 (자동 증가)
    name       TEXT    NOT NULL UNIQUE CHECK (name <> ''),             -- 이름 (빈 이름 불가, 중복 불가)
    created_at TEXT    NOT NULL                                        -- 처음 등록한 시각 (YYYY-MM-DD HH:MM:SS)
);

-- 게임 기록: 게임 오버될 때마다 한 줄씩 쌓인다
CREATE TABLE IF NOT EXISTS records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,             -- 기록 번호 (자동 증가)
    player_id     INTEGER NOT NULL REFERENCES players(id),       -- 누가 플레이했는지 (players.id)
    round_reached INTEGER NOT NULL,                              -- 도달한 웨이브 (게임 오버된 웨이브)
    score         INTEGER NOT NULL,                              -- 점수 (처치 수×10 + 막은 웨이브×100)
    growth_stage  TEXT    NOT NULL,                              -- 게임 오버 때 계급 (이병/일병/상병/병장/하사)
    played_at     TEXT    NOT NULL                               -- 플레이한 시각 (YYYY-MM-DD HH:MM:SS)
);
