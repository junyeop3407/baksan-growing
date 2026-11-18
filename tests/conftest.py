# 테스트 준비 코드: src/ 폴더의 모듈을 import할 수 있게 하고,
# 그림 테스트에 쓸 tkinter 창(tk_root)을 만들어 준다.
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture
def tk_root():
    """테스트 하나 동안 쓸 tkinter 창을 만들고 끝나면 닫는다."""
    tk = pytest.importorskip("tkinter")
    # 어떤 컴퓨터(Python 3.14.0 + Tk 8.6.15)에서는 창을 많이 만들다 보면 가끔 Tcl 초기화가 실패한다
    # ("Can't find a usable init.tcl"). 앱 문제가 아니라 환경 문제라 몇 번 다시 시도한다 (docs/NOTES.md).
    for attempt in range(5):
        try:
            root = tk.Tk()
            break
        except tk.TclError as error:
            last_error = error
    else:
        pytest.skip("화면(디스플레이)이 없어 tkinter 창을 만들 수 없음: " + str(last_error))
    root.withdraw()
    yield root
    import pixel_art          # 닫는 창의 도트 이미지 캐시를 비워 테스트가 쌓여도 메모리에 남지 않게 한다
    pixel_art.forget(root)
    root.destroy()
