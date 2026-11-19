# 박산 키우기

군인 박산, 판타지 세계로 전입 — 슬롯 디펜스 로그라이크

**과제 정보**: 한국폴리텍대학 인천캠퍼스 컴퓨터공학과 / 파이썬 기말과제 / 백준엽

![게임 화면](./images/game.png)

## 과제 제출물 바로가기
| 제출물 | 실제 파일 |
|---|---|
| [1. 기획서](#1-기획서) | [기획서.md](./기획서.md) |
| [2. 코드](#2-코드) | [src 폴더](./src) |
| [3. 실행파일](#3-실행파일) | [Release v1.0.0 (baksan-growing.exe)](https://github.com/junyeop3407/baksan-growing/releases/tag/v1.0.0) |
| [4. DB 연동](#4-db-연동) | [schema.sql](./schema.sql), [src/db.py](./src/db.py) |
| [5. 깃 주소](#5-깃-주소) | https://github.com/junyeop3407/baksan-growing ([커밋 기록](https://github.com/junyeop3407/baksan-growing/commits/main)) |

## 1. 기획서
[기획서.md](./기획서.md)에 프로젝트 개요, 개발 환경, 게임 규칙(스핀·소환·합체·전투·상점·점수), 화면 구성, 기능 목록을 정리했다.
DB 설계(테이블·SQL·실행 시점), 프로그램 구조, 개발 과정(규칙을 바꾼 이유), 개선할 점도 함께 담았다.

## 2. 코드
| 파일 | 역할 | 주요 함수 |
|---|---|---|
| [src/symbols.py](./src/symbols.py) | 총알 5종·병사·계급 정의, 총알 그리기 | [draw_bullet()](./src/symbols.py#L37-L49) |
| [src/game.py](./src/game.py) | 게임 규칙 (화면 없이도 동작) | [spin()](./src/game.py#L168-L192), [summon()](./src/game.py#L194-L211), [start_battle()](./src/game.py#L224-L239), [battle_step()](./src/game.py#L246-L277), [finish_wave()](./src/game.py#L279-L293) |
| [src/db.py](./src/db.py) | sqlite3 연동 (모든 SQL) | [init_db()](./src/db.py#L52-L62), [save_record()](./src/db.py#L88-L104), [get_top10()](./src/db.py#L107-L125) |
| [src/pixel_art.py](./src/pixel_art.py) | 도트 그림 (글자 격자 + 색표 → PhotoImage), 얼굴 부위 바꾸기 | [blend_face()](./src/pixel_art.py#L213-L215), [scene()](./src/pixel_art.py#L850-L933), [photo()](./src/pixel_art.py#L959-L967) |
| [src/character.py](./src/character.py) | 지휘대 위 박산, 춤 순서, 말풍선 | [draw_character()](./src/character.py#L73-L110), [make_dance_steps()](./src/character.py#L119-L135) |
| [src/ui.py](./src/ui.py) | tkinter 화면 5개와 스핀·전투·춤 진행 | [show_game()](./src/ui.py#L286-L309), [on_battle()](./src/ui.py#L554-L569), [battle_tick()](./src/ui.py#L571-L598), [show_gameover()](./src/ui.py#L704-L732) |
| [src/main.py](./src/main.py) | 진입점 | [main()](./src/main.py#L9-L13) |

읽는 순서: symbols.py → game.py → db.py → pixel_art.py → character.py → ui.py → main.py

캐릭터·그래픽은 모두 코드로 그린 도트이며 실제 사진·외부 에셋을 쓰지 않았다.

사용 기술: Python, tkinter, sqlite3, PyInstaller ([build.bat](./build.bat)로 exe 생성)

테스트 실행:
```
py -m pip install -r requirements-dev.txt
py -m pytest tests
```

## 3. 실행파일
### 실행 방법
1. **실행파일**: [Release v1.0.0](https://github.com/junyeop3407/baksan-growing/releases/tag/v1.0.0)에서 `baksan-growing.exe`를 내려받아 실행한다 (Python이 없어도 된다). Windows "PC 보호" 창이 뜨면 **[추가 정보] → [실행]** 을 누른다. 서명하지 않은 개인 과제 프로그램이라 뜨는 경고다.
2. **소스**: Python 3.11 이상(Tk 8.6·9에서 확인)에서 `py src/main.py` (Mac·Linux는 `python3 src/main.py`)

### 게임 방법
1. 이름을 넣고 [게임 시작]. 골드로 [스핀]을 돌려 같은 총알 3개가 한 줄로 맞으면 그 총알의 병사가 소환된다.
2. 같은 병사 2명이 모이면 합체해 별이 오르고 공격력이 2배가 된다 (★3까지).
3. [전투 시작]을 누르면 병사들이 자동으로 쏘고, 바리케이드를 지나간 몬스터만큼 하트가 줄어든다.
4. 웨이브를 막을 때마다 박산이 진급(이병→하사)하며 얼굴이 바뀌고, 상점에서 하나를 무료로 고른다.
5. 하트가 0이 되면 게임 오버. 점수(처치 × 10 + 막은 웨이브 × 100)가 DB에 저장되고 랭킹에 오른다.

## 4. DB 연동
- 사용 DB: SQLite (sqlite3 표준 라이브러리), 파일: `game.db` (실행하면 자동으로 생긴다. exe는 exe와 같은 폴더, 소스 실행은 `src/` 폴더)
- 테이블 생성 SQL: [schema.sql](./schema.sql)

| 테이블 | 컬럼 | 설명 |
|---|---|---|
| players | id, name, created_at | 플레이어 (같은 이름은 같은 플레이어, 빈 이름 불가) |
| records | id, player_id → players.id, round_reached, score, growth_stage, played_at | 게임 오버 때마다 한 줄 (도달한 웨이브, 점수, 계급, 시각) |

| 시점 | 동작 | SQL | 코드 위치 |
|---|---|---|---|
| 프로그램 시작 | 테이블 생성 | CREATE TABLE IF NOT EXISTS | [db.py init_db()](./src/db.py#L52-L62) |
| 게임 시작 | 플레이어 등록/조회 | SELECT / INSERT | [db.py get_or_create_player()](./src/db.py#L78-L85) |
| 게임 오버 | 기록 저장 | INSERT | [db.py save_record()](./src/db.py#L88-L104) |
| 랭킹 화면 | 상위 10개 조회 | SELECT ... ORDER BY ... LIMIT 10 | [db.py get_top10()](./src/db.py#L107-L125) |

모든 SQL은 [src/db.py](./src/db.py)에만 있고 `?` 파라미터 바인딩을 쓴다. DB를 읽거나 쓰지 못해도(잠김, 쓰기 금지 폴더) 게임은 꺼지지 않고 문구로 알린다.

랭킹 화면 (실제로 4판을 해서 쌓인 기록):

![랭킹 화면](./images/ranking.png)

DB Browser for SQLite로 연 game.db (records 테이블):

![DB Browser로 연 game.db](./images/db_browser.png)

## 5. 깃 주소
- 저장소: https://github.com/junyeop3407/baksan-growing
- 단계별 커밋 기록: https://github.com/junyeop3407/baksan-growing/commits/main

## 폴더 구성
| 경로 | 내용 |
|---|---|
| [src/](./src) | 게임 코드 (제출물 2번) |
| [tests/](./tests) | pytest 자동 테스트 |
| [images/](./images) | README·기획서에 쓴 그림 (게임 화면, 랭킹, DB Browser 등) |
| [docs/](./docs) | 개발 과정 기록 (제출물 아님, 참고용) |
| [기획서.md](./기획서.md) | 기획서 (제출물 1번) |
| [schema.sql](./schema.sql) | 테이블 생성 SQL (제출물 4번) |
| [build.bat](./build.bat) | exe 만들기 (PyInstaller) |
| [requirements.txt](./requirements.txt) | exe 빌드에 필요한 패키지 |
| [requirements-dev.txt](./requirements-dev.txt) | 테스트에 필요한 패키지 |
| [.gitignore](./.gitignore) | 커밋하지 않을 파일 (game.db, build/, dist/ 등) |
