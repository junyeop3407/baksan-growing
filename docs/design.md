# 설계 (2단계)

## 기술 (사장 지정, 팀 기본 기술 대신)
Python + tkinter + sqlite3 + PyInstaller. 웹·React·Spring은 쓰지 않는다(요청서 3번). 외부 라이브러리는 PyInstaller만.
디자인 방향도 사장이 정했다: 군대(연병장·막사 배경, 총알 심볼, 계급장), 모두 Canvas 도형. 참고 서비스가 없어 "참고 디자인 분석"은 건너뛴다.

## 고를 것: Python·Tk 버전 조합
| 안 | 내용 | 설치 | 테스트 도구 |
|---|---|---|---|
| A | 지금 깔린 Python 3.14.7 + Tk 9.0.4 + PyInstaller 6.22.3 | PyInstaller만 (pip) | pytest (이미 있음) |
| B | Python 3.13 + Tk 8.6 + PyInstaller 6.22.3 | Python 3.13 새로 설치 | pytest 다시 설치 |
| C | Python 3.12 + Tk 8.6 + PyInstaller 6.22.3 | Python 3.12 새로 설치 | pytest 다시 설치 |

| 기준 (가중치) | A | B | C |
|---|---|---|---|
| 시작 쉬움 (×3) | 5 | 3 | 3 |
| 고치기·늘리기 쉬움 (×2) | 4 | 4 | 4 |
| 돈 (×2) | 5 | 5 | 5 |
| 꼭 되어야 할 기능 (×3) | 5 | 5 | 5 |
| 합계 (50) | **48** | 42 | 42 |

- 가중치는 기본값 그대로. 돈은 모두 0원.
- A의 기능 5점 근거: 2026-11-18 시험 exe(tkinter Canvas + 한글 글자 + sqlite3, `--onefile --windowed`, 한글 exe 이름)를 빌드해 실행했고, Tk 9.0.4로 돌았으며 exe 옆에 DB 파일이 생겼다.
- **추천: A.** 새로 깔 것이 없고 시험 빌드가 이미 됐다.

### 근거
- PyInstaller 6.15.0 (2025-08-03) "Add Python 3.14 support." — https://pyinstaller.org/en/stable/CHANGES.html
- PyInstaller 6.22.0 (2026-08-08) "Implement support for Tcl/Tk 9 builds with embedded data archives in `tkinter` hooks and the splash screen." — 같은 페이지
- 최신 PyInstaller: 6.22.3 (`pip index versions pyinstaller`, 2026-11-18)

### 주의 (A를 고를 때)
- 교수님이 `python src/main.py`로 돌리면 교수님 PC의 Python(3.11+, 대개 Tk 8.6)으로 돈다. 그래서 Tk 9에만 있는 기능은 쓰지 않는다. Tk 8.6에서 실제로 돌려 보는 것은 **확인 못 함**(이 PC에 Tk 8.6 없음).
- Python이 없는 PC에서 exe가 도는지는 **확인 못 함**. 6단계에서 Windows 샌드박스 등으로 확인한다.

## 정한 것
- 고른 안: (사장 선택 대기)
- 테스트: pytest, `apps/baksan-growing/tests/`에만 둔다(제출 저장소에 복사 안 함). 실행은 `bash tests/run.sh`.
- 화면 테스트도 pytest에서 tkinter 창을 실제로 띄워 확인한다(Playwright는 웹용이라 해당 없음).

## 버린 안
- 웹(React)·Spring: 요청서가 Python만 허용.
