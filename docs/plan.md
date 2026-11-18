# 계획: 박산 키우기 — 저장소 정리 → 게임 로직 → DB → 캐릭터 미리보기

## 배경
- 설계안 A(Python 3.14 + Tk 9)와 테스트 목록 61개가 승인됐다.
- 오늘은 로직·DB·캐릭터를 테스트 먼저 방식으로 만들고, `faces_preview.png`를 만든 뒤 멈춘다. ui.py, 춤, 말풍선은 만들지 않는다.
- 코드는 Python 3.11과 Tk 8.6에서도 돌아가게 쓴다.
- 제출 방식: 작업장의 `apps/baksan-growing/`에서 만들고, 정해진 목록만 스크립트로 제출 저장소에 복사한다.
  - 제출 목록: README.md, 기획서.md, schema.sql, src/, images/, docs/, tests/, build.bat, requirements.txt, requirements-dev.txt, .gitignore
- 앞으로 경로는 모두 `apps/baksan-growing/` 기준이다.

## 0단계 — 저장소 정리 (커밋 "저장소 정리")
- `.gitignore`(앱 폴더용): game.db, *.db, build/, dist/, *.spec, `__pycache__`/
- `requirements.txt`: `pyinstaller==6.22.3`
- `requirements-dev.txt`: `pytest`, `vermin`
- `tests/run.sh`: 작업장 견본을 복사하되, playwright 확인은 빼고 pytest만 확인한다.
- `tests/conftest.py`: `src/`를 import 경로에 넣는다. tkinter 창이 필요한 테스트용 `tk_root` 준비 코드도 둔다.
- `export_submission.py`(앱 폴더, 제출 목록에 없음 = 작업장에만):
  1. **복사 대상**: 제출 목록 안에서 git이 추적하는 파일(`git ls-files`)만 복사한다. 로컬 `src/game.db`나 `__pycache__`는 추적되지 않으므로 애초에 대상이 아니다.
  2. **금지 파일 검사**: 추적 파일 기준으로 한다. `__pycache__`, *.pyc, *.db, HANDOFF.md, .claude, dist/, build/, *.spec, samples가 하나라도 있으면 아무것도 하지 않고 멈춘 뒤 목록을 알린다.
  3. **대상 경로 확인**: 대상 폴더(기본값 `../../../baksan-growing-submission`, 작업장 저장소 바로 옆)의 폴더 이름이 `baksan-growing-submission`이고 안에 `.git`이 있어야 한다. 아니면 멈춘다.
  4. **정리**: 대상 쪽에서 제출 목록에 해당하는 옛 파일 중, 이번 복사 목록에 없는 것만 지운다. `.git` 폴더는 어떤 경우에도 읽기·삭제 대상에서 뺀다.
  5. **`--dry-run`**: 복사할 목록과 지울 목록만 출력하고 아무것도 바꾸지 않는다.
  6. **테스트**: 복사 뒤 대상 폴더에서 `py -m pytest -q`를 실행한다. 테스트가 아직 없으면(종료 코드 5) 통과로 본다. 실패하면 커밋하지 않고 멈춘다.
  7. **커밋**: `--commit "메시지"`를 주면 그곳에서 `git add -A` 후 같은 메시지로 커밋한다. 푸시는 하지 않는다.
- 제출 저장소는 처음 한 번 그 폴더를 만들고 `git init`만 한다. **GitHub에는 만들지 않는다**(사장 OK 전).
- 0단계 보고에는 실제 복사 전에 돌린 `--dry-run` 결과(복사·삭제 목록)를 먼저 적는다.
- docs/ 안의 링크 점검: 문서를 옮기지 않으므로 바뀌는 링크는 없다. grep으로 상대 링크 대상이 실제로 있는지 확인한다.
- HANDOFF의 `리뷰 기준:` 줄 = `ab849d2` (4단계 시작 직전 커밋)

## 1단계 — 게임 로직 (커밋 "게임 로직 구현")
1. 머리 주석만 있는 빈 `src/symbols.py`와 `src/game.py`를 먼저 만든다. 그래야 테스트가 import 오류 한 번이 아니라 하나하나 실패한다.
2. 테스트를 쓴다.
   - `tests/test_game.py`: A1~A17, B1~B6
   - `tests/test_bullets.py`: E2, E3
3. `test-runner`로 돌려 처음 실패 개수를 기록한다.
4. 구현한다.
   - `symbols.py`
     - `BULLETS`: 이름, 점수, 탄두·탄피 길이와 색
     - `START_DECK`
     - `RANKS`: (이름, 최산 비율) 5개
     - `HIGHLIGHT_WIDTH`
     - `draw_bullet(canvas, kind, x, y, size)`: 칸 안쪽 여백 안에 총알 그림과 이름 글자를 그린다. tkinter는 import하지 않는다.
     - `draw_highlight(canvas, x, y, size)`: 칸 가장자리 테두리만 그린다.
   - `game.py`
     - 함수: `target_score(round_no)`, `count_lines(board)`, `spin_score(board)`, `rank_for(passed)`, `face_ratio(passed)`, `clean_name(text)`. `clean_name`은 (이름, 안내 문구)를 돌려준다.
     - 작은 클래스 `Game`: 덱, 라운드, 남은 스핀, 라운드 점수, 총점, 통과 수, 판을 가진다.
     - 메서드: `spin(rng)`(남은 스핀이 없으면 ValueError), `finish_round()`("pass"/"over"), `shop_offer(rng)`, `add_to_deck(kind)`
     - 무작위는 `rng`를 넘겨받는다. 그래야 테스트에서 결과를 고정할 수 있다.
5. 전체 테스트 통과를 확인한다.
6. vermin(`py -m vermin -t=3.11- --no-tips src tests`)으로 최소 Python 버전을 확인한다.
7. `tests/tools/simulate.py`(게임 코드를 그대로 씀)로 1000판 시뮬레이션을 돌리고, 지난번 17~37%와 비교한다.
8. `qa-reviewer`로 리뷰하고, 진짜 문제만 고친다.
9. 커밋·푸시하고 같은 메시지로 제출 저장소에 반영한다. HANDOFF에 `테스트 실행: \`bash tests/run.sh\``를 넣는다.

미루는 것:
- E1(최소 창에서 칸 80px 이상): 창 최소 크기는 ui.py가 정한다. 그래서 ui 단계에서 쓴다.
- B7(같은 이름 두 번): DB가 필요해서 2단계에서 쓴다.

## 2단계 — DB (커밋 "DB 연동")
1. 빈 `src/db.py`를 만든다.
2. `tests/test_db.py`(C1~C9, B7)를 쓴다. 모두 pytest `tmp_path`를 써서 테스트 뒤 남는 파일이 없다.
3. 실패 개수를 기록한다.
4. 구현한다.
   - `schema.sql`: 테이블 생성 SQL과 열마다 주석
   - `db.py` 함수: `get_db_path()`, `init_db(path)`, `get_or_create_player(path, name)`, `save_record(path, name, round, score, rank)`, `get_top10(path)`
     - `get_db_path()`: frozen이면 exe 폴더, 아니면 `src/`
     - `get_top10(path)`: 총점 내림차순 → 라운드 내림차순 → `played_at` 오름차순 → id 오름차순
   - 함수마다 실행하는 SQL을 주석으로 적는다. 모두 `?` 바인딩.
   - 테이블 생성 SQL은 db.py 안에 두고, schema.sql과 같은지는 C8 테스트로 확인한다. schema.sql은 exe에 들어가지 않으므로 db.py가 파일을 읽게 하지 않는다.
5. C4의 화면 부분("빈 표 + 아직 기록이 없습니다")은 ui 단계로 미룬다. 지금은 조회 결과가 빈 목록인지만 확인한다.
6. 통과 → 리뷰 → 커밋·제출 저장소 반영 → HANDOFF 갱신

## 3단계 — 캐릭터 (커밋 "캐릭터 그리기")
1. 빈 `src/character.py`를 만든다.
2. `tests/test_character.py`(D1~D6)를 쓴다.
3. 실패 개수를 기록한다.
4. 구현한다.
   - `SEONGJAE`, `CHOISAN` 설정값
     - 숫자: 얼굴 폭·턱, 눈 길이·높이·눈꼬리·눈동자, 눈썹 굵기·기울기, 코 폭·둥근 정도, 귀 노출, 앞머리 가닥·곱슬·젖은 광택의 세기
     - 색: 피부, 입술
     - 점 목록(개수 같게): 얼굴 윤곽, 머리 윤곽, 입
   - 섞기 함수: `mix_value`(a×(1−t) + b×t, 그래서 t=0과 t=1에서 원본과 정확히 같다), `mix_color`, `mix_points`, `face_for(t)`
   - 그리기 함수
     - `draw_character(canvas, x, y, t, rank_name, pose=None)`: 태그 body / arm_l / arm_r / head / badge로 나눠 그린다. 영역 W×H 안에 들어가게 한다.
     - `draw_rank_badge`: 이병~병장은 가로 막대 1~4개, 하사는 V자 + 막대
     - `pose`는 나중에 춤에 쓴다. 지금은 기본 자세만 그린다.
5. `tests/tools/make_previews.py`로 미리보기 이미지를 만든다. (2026-11-19: 도트 그래픽으로 바뀌며 `tests/tools/make_sprite_preview.py`로 대체하고 이 도구와 흑백본은 삭제) (2026-11-19: 도트 그래픽으로 바뀌며 `tests/tools/make_sprite_preview.py`로 대체하고 이 도구와 흑백본은 삭제)
   - 계급 5개 얼굴을 나란히 그린 창을 맨 앞에 띄운다.
   - 얼굴마다 아래에 "이병 0%"처럼 계급과 비율을 적는다.
   - PowerShell(System.Drawing)로 그 창만 캡처해 `images/faces_preview.png`로 저장한다.
   - 같은 이미지를 흑백으로 바꿔 `images/faces_preview_gray.png`로 저장한다.
   - 캡처 결과를 직접 열어 보고, 다른 창이 찍혔으면 다시 찍는다.
6. 통과 → 리뷰 → 커밋·제출 저장소 반영 → HANDOFF 갱신
7. **여기서 멈추고** 두 이미지 경로를 보고한 뒤 사장 OK를 기다린다.

## 지킬 것
- 승인된 테스트는 커밋한 뒤 바꾸지 않는다. 바꿔야 하면 이유를 적고 사장 OK를 받는다.
- 코드 기준(요청서 10번)
  - 파일 머리에 하는 일 2~3줄
  - 주요 함수에 한국어 docstring 한 줄
  - 디버그 print와 주석 처리된 코드는 남기지 않는다.
- 3.12 이후에만 되는 문법은 쓰지 않는다(예: f-string 안 같은 따옴표, `type` 문). Tk 9에만 있는 기능도 쓰지 않는다.
- 커밋 전마다 `git status`로 game.db, `__pycache__`, 임시 파일이 없는지 확인한다.

## 단계마다 보고에 넣을 것
- 처음 실패 개수 → 최종 N/N
- 커밋 해시: 작업장과 제출 폴더 둘 다
- export 결과: 복사한 수, 지운 수, 제출 폴더 테스트 결과

## 확인 방법
- `bash tests/run.sh`(test-runner)로 단계마다 처음 실패 개수와 최종 N/N을 기록한다.
- vermin 결과, 시뮬레이션 결과(전략 2개 × 1000판), 커밋 해시를 기록한다.
- 미리보기 두 이미지를 직접 열어 확인한다.
- export 스크립트가 제출 저장소 쪽 테스트까지 통과시키는지 확인한다.

## 지금 작업장 저장소 (확인함, 2026-11-18, `gh repo view` + `git ls-files`)
| 항목 | 값 |
|---|---|
| GitHub 저장소 | junyeop3407/baksan-growing |
| 공개 여부 | 공개(PUBLIC) |
| 만든 날 | 2026-11-18, 견본 저장소 junyeop3407/ai-workflow로 만듦 |
| 들어 있는 것 | 작업장 파일(CLAUDE.md, HANDOFF.md, README.md, .claude/, setup/)과 `apps/baksan-growing` 하나뿐. 다른 앱이나 프로젝트는 없음 |
- 이 프로젝트 전용으로 만든 저장소라서 아래 안(이름 바꾸기 + 비공개)을 그대로 제안한다.
- 이름을 바꿔도 견본 저장소 ai-workflow는 영향을 받지 않는다.
- 이번 계획에서는 실행하지 않는다.

## 4번 질문 답 (제안만): 제출 저장소를 GitHub에 언제 만들까
- 추천 시점: README와 exe가 준비된 뒤(작업 순서 8~11번, Release v1.0.0을 붙이기 직전)
- 순서:
  1. 이 작업장 저장소 이름을 바꾸고 비공개로 돌린다(예: baksan-growing-workspace).
  2. 새 공개 저장소 baksan-growing을 만든다.
  3. 로컬 제출 저장소의 단계별 커밋을 한 번에 푸시한다.
- 그때까지 커밋 기록은 로컬 제출 폴더에 단계별로 쌓인다. 푸시할 때 날짜와 메시지가 그대로 올라가므로 교수님은 개발 과정을 볼 수 있다.
- 두 작업 모두 바깥에 내보내는 일이라 사장님이 `!` 한 줄로 실행한다.
